import pandas as pd
import networkx as nx
import random
import logging
from datetime import datetime
import numpy as np

from oriom.core.functions.layout_power import aux_layout_power_func
from oriom.core.functions.layout_power.corrective_location import logs_corrective_locations, choose_spec_loc_string
from oriom.core.functions.layout_power.layout_energy_manager import shut, fix



COLS = ['Date','Event','id','Comments','Name','Loc','Shutdown','Shut/Fix','Perc_availability','Power_loss_kW']


def return_percentage(
    log_events: pd.DataFrame,
    prefix_list: list,
    operations_corrective_stat: list,
    G: nx.DiGraph,
    shut_attribute: str,
    start_year: int,
    start_month: int,
    n_lifetime: int,
    n_devices: int,
    tech: str,
    find_element_class: object,
    n_strings_per_inv: int = None,
    n_pv_per_string: int = None,
    max_failure_module: int = None
) -> pd.DataFrame:


    """
    It calls :func:log_corrective_locations and created a DataFrame with all the dates of each event
    that lead to a shutdown the location and the percentage of the farm.

    From log_events dates procede row by row to evaluate the failure/operation. If is a failure it
    assign a location through :func:log_corrective_locations and store this location in a list
    in order to not repeat the failure location in a failed component. Than consider if the device need to be
    shutted down or if is restored. Evaluate so the percentage available of power output at that
    timestep. Returns a df with all these information per timesteps

    Args:
        log_events (:obj:pd.DataFrame): log of all the events (failure,
            operation, inspection_port, inspection_site)
        failures (:obj:list): list of obcjects class Failures.
        prefix_list: (:obj:list): contains the prefix to study the log_events
            for each technolog y['opv','oce'] or ['ofw', 'oce'] or ['owc', 'oce'].
        operations_corrective_stat (:obj:list): list of obcjects class
            OperationsCorrectiveStat.
        G (:obj:nx.DiGraph): Graph of tech farm.
        start_year (:obj:int): start_year of the project.
        start_month (:obj:int): start_month of the project
        n_lifetime (:obj:int): lifetime of the project in years.
        n_device (:obj:int): number of devices.
        tech (:obj:str): name of technology analyzed
        find_element_class (Find_element_class): Initialized instance that provides fast access to operations,
            vessels and failures via internal dictionaries.
        n_strings_per_inv (:obj:int, *optional*): number of string each inverter
        n_pv_per_strings (:obj:int, *optional*): number of modules each string
        max_failure_module (:obj:int, *optional*): number of failed module allowed each string

    Raises:
        ValueError: "shut/fix" not recognized.

    Returns:
        pd.DataFrame: dataframe with all the events, percentage farm available.
    """


    def update_string_PV_shutdown(
            loc: int,
            device_string_level: dict,
            device_shutted_string_level: dict,
            max_failure_module: int,
            string_inverter: set
        ):

        """
        This function is used to manage the PV failure dictionary to count a resolution lower than string level

        Args:
            loc (int): node of the inverter selected
            device_string_level (dict): nested dictionary with 1st key:node inverter, 2nd key:nº string, value:nº PV failed
            device_shutted_string_level (dict): nested dictionary with 1st key:node inverter, 2nd key:position of string closed, value True
            n_strings_per_inv (int): number of string per inverter
            max_failure_module: maximum PV module that can fail on a string before than shutdown the string
            string_inverter (set): Set of string for the inverter

        Return:
            bool: return if a string must be closed due to insufficient voltage
        """

        if loc not in device_string_level:
            device_string_level[loc] = {}
        # Check if this inverter has already some string failed
        try:
            failed_strings = set(device_shutted_string_level[loc].keys())
        except KeyError:
            failed_strings = set()

        k = aux_layout_power_func.string_location(failed_strings = failed_strings, string_inverter = string_inverter)

        device_string_level[loc][k] = device_string_level[loc].get(k, 0) + 1

        if device_string_level[loc][k] >= max_failure_module:
            device_shutted_string_level[loc] = {}
            device_shutted_string_level[loc][k] = True

            return True
        return False


    # Create commissioning/decommissioning and monthly markers
    def make_row(date, event):
        return [date, event, '-', '-', '-', '-', '-', '-', 100.0, None]


    COMPONENT_LEVEL_POWER = aux_layout_power_func.find_highest_power_node(G)
    LEVELS_NO_POWER = {data.get("level") for _, data in G.nodes(data=True)}
    LEVELS_NO_POWER.discard(COMPONENT_LEVEL_POWER)

    # Create list of operations id to consider for shut down or fix strategy
    op_corr_excl_tow = [op.id for op in operations_corrective_stat if not getattr(op.op_class, "tow_to_port", None)]
    op_corr_tow = {}
    op_add_tow = {}
    events_total = []
    percentage = []

    device_shutted = set()
    device_failed = set()
    device_shutted_string_level = {}
    device_string_level = {}
    dict_locations = {}
    recommissioning = False

    for op in operations_corrective_stat:
        if getattr(op.op_class, "tow_to_port", None) or getattr(op.op_class, "op_tow_site", None):
            tow_port_op = getattr(op.op_class, "op_tow_port", None)
            tow_site_op = getattr(op.op_class, "op_tow_site", None)

            for op_tow, type_op in zip([tow_port_op, tow_site_op], ['TTP', 'TTS']):
                found_op = find_element_class.find_operation(op_tow)
                if type_op == 'TTS':
                    recommissioning = True if found_op.recommissioning_time > 0 else False

                op_corr_tow[found_op.id] = found_op
                if found_op.addition_op_tow:
                    op_add_tow[found_op.addition_op_tow.id] = {'string':found_op.string_disconnection, 'type': type_op}

    if tech == 'PV':
        string_inverter = set(range(1, n_strings_per_inv + 1))
        string_closed = 0
    else:
        string_inverter = None
        string_closed = None

    # Filter for the technology selected
    log = log_events[log_events['id'].str[:3].isin(prefix_list)].rename(columns={'d_trigger': 'Date'})
    if not log.empty:
        for _, r in log.iterrows():
            rows, dict_locations = logs_corrective_locations(
                    r,
                    op_corr_excl_tow,
                    shut_attribute,
                    find_element_class,
                    dict_locations,
                    op_corr_tow,
                    op_add_tow
            )

            for row in rows:
                events_total.append(row)

        # riorder date first, then for events, finally for shut/fix
        event_order = {"failure": 0, "tow": 1, "operation": 2}
        shutfix_order = {"shut": 0, "fix": 1}
        events_total.sort(key=lambda r: (r["date"], event_order.get(r["event"], 99), shutfix_order.get(r["shut_fix"], 99)))

        for r in events_total:
            date = r["date"]
            event = r["event"]
            name = r["name"]
            loc = r["loc"]
            shutdown = r["shutdown"]
            shut_fix = r["shut_fix"]
            failure_id = r["failure_id"]
            r_id = r["id"]
            shut_downstream_device = False
            # LOCATION SELECTION
            # ------------------
            if loc is None:
                # failure location
                if event == "failure":
                    tech2 = 'PV' if prefix_list == ['opv', 'oce'] else None

                    loc = aux_layout_power_func.choose_loc(
                        level=r["level"],
                        G=G,
                        component_level_power=COMPONENT_LEVEL_POWER,
                        date=date,
                        list_failed=device_shutted,
                        tech=tech2
                    )

                    r["loc"] = loc
                    dict_locations[failure_id] = loc

                # operation / tow: take location from failure
                else:
                    loc = dict_locations.get(failure_id)
                    if loc is None:
                        raise RuntimeError(f"Location not resolved for event {r['id']} at {date}")
                    r["loc"] = loc


            # ACTION SELECTION
            # ------------------
            # Store the shutdown of the device and evaluate the power of the farm
            if shut_fix == 'shut':
                # Analyze PV technology components below last component defined (inverter)
                # NOTE: This need to be modified in case we select other layout resolution
                if event == 'failure':
                    if tech == 'PV':
                        # PV module failure (device) store it in a dictionary, do not store the loc on device_failed as only reduce its power
                        if 'device' in name and shutdown:
                            close_device = False  # Do not close the device if only power reduction
                            closed = update_string_PV_shutdown(
                                loc = loc,
                                device_string_level = device_string_level,
                                device_shutted_string_level = device_shutted_string_level,
                                max_failure_module = max_failure_module,
                                string_inverter = string_inverter
                            )
                            if closed:
                                string_closed += 1
                                name = 'opv_fail_INV_V_min_exceded'
                        # String failure close a string of the inverter, do not store the loc on device_failed as only reduce its power
                        elif 'string' in name:
                            close_device = False
                        else:
                            device_failed.add(loc)
                            close_device = True
                    else:
                        device_failed.add(loc)
                        close_device = True

                # Shutdown the component if is a failure that requires it or the op require shutdown and was not already shutted
                if loc not in device_shutted or event == 'tow' or r_id in op_add_tow.keys():
                    if op_add_tow.get(r_id, {}).get('string', False):
                        loc = choose_spec_loc_string(G,loc)
                        # Add to do electrical discontinuity
                        if getattr(G, 'graph', {}).get('tow_string_shutdown', False):
                            shut_downstream_device = r["loc"]

                    G, power_farm = shut(
                        loc,
                        shutdown if loc not in device_shutted else False, # Manage case device failed but need tow and create string disconn
                        G,
                        COMPONENT_LEVEL_POWER,
                        LEVELS_NO_POWER,
                        tech,
                        name,
                        n_pv_per_string,
                        max_failure_module,
                        device_shutted_string_level,
                        list_failed = device_shutted,
                        string_inverter = string_inverter,
                        event = event,
                        op_add_tow = op_add_tow,
                        r_id = r_id,
                        shut_downstream_device = shut_downstream_device
                    )

                    perc = power_farm / n_devices * 100

                    # Store the closed device if lead to a shutdown and is a component that can be closed or the event
                    if shutdown and close_device:
                        device_shutted.add(loc)

            # Store the fix of the device and evaluate the power of the farm
            elif shut_fix == 'fix':
                if op_add_tow.get(r_id, {}).get('string', False):
                    loc = choose_spec_loc_string(G,loc)
                G, power_farm = fix(
                    loc,
                    G,
                    COMPONENT_LEVEL_POWER,
                    LEVELS_NO_POWER,
                    tech,
                    name,
                    n_pv_per_string,
                    event = event,
                    op_corr_tow = op_corr_tow,
                    op_add_tow = op_add_tow,
                    r = r,
                    recommissioning = recommissioning
                )
                device_failed.discard(loc)
                device_shutted.discard(loc)
                perc = power_farm / n_devices * 100

            # Raise an error if there is no indication specific of the shutdown/restoration
            else:
                raise ValueError(f"Unknown shut/fix value: {shut_fix}")
            percentage.append(perc)

        df = pd.DataFrame(
            [
                [
                    e.get("date"),
                    e.get("event"),
                    e.get("id"),
                    e.get("comments"),
                    e.get("name"),
                    e.get("loc"),
                    e.get("shutdown"),
                    e.get("shut_fix"),
                ]
                for e in events_total
            ],
            columns=COLS[:-2]
        )

        if tech == 'PV':
            logging.info(f"Strings closed due to PV failures: {string_closed}")

        # Create the dataframe of the availability
        df['Perc_availability'] = percentage
        df['Power_loss_kW'] = None

        date_commission = datetime(start_year, start_month, 1, 0, 0, 0)
        date_decommission = datetime(start_year + n_lifetime, start_month, 1, 23, 59, 0)

        # Add the dates at start and end of each months
        extra_rows = [
            make_row(date_commission, 'commissioning_project'),
            make_row(date_decommission, 'decomissioning_project')
        ]

        date_first = pd.date_range(start=date_commission, periods=n_lifetime*12, freq='MS')
        date_last = (date_first + pd.offsets.MonthEnd(0)).normalize() + pd.Timedelta(hours=23, minutes=59, seconds=59)
        for d in date_first:
            extra_rows.append(make_row(d, 'First Day of month'))
        for d in date_last:
            extra_rows.append(make_row(d, 'Last Day of month'))
        df_extra = pd.DataFrame(extra_rows, columns=COLS)
        # Sort and reset index
        df_extra.sort_values(by='Date', inplace=True)
        df_extra.reset_index(drop=True, inplace=True)
        df = aux_layout_power_func.add_markers_month_year(df = df, df_extra = df_extra)

        # correct percentage for monthly markers dates
        df = aux_layout_power_func.fix_percentage_markers_dates(df)

        df['Perc_availability'] = df['Perc_availability'].fillna(method='ffill')
    else:
        df =pd.DataFrame(columns=COLS[:-2])

    return df


if __name__ == '__main__':
    pass