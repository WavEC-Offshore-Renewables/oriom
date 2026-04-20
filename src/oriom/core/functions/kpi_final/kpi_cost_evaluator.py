import pandas as pd
import math as mt

from oriom.utils.read_dataframe_value import approximate_hourly_data
from oriom.core.functions.kpi_final import kpi_aux


def inspection_data(insp):
    """
    Extrapolate data of inspection from insp class

    Args:
        insp (:obj:`list`): List of objects :class:`InspectionsSiteStat` or :class:`InspectionsPortStat`.
    Returns:
        data of the inspections
    """

    insp_id = insp.id
    rov_cost_insp = getattr(getattr(insp.insp_class, "rov_drone", None), "daily_charter", 0)
    n_tech_inps = getattr(insp.insp_class, "tech_per_device",0)
    c_tech_inps = getattr(insp.insp_class, "tech_cost",0)
    n_shifts_main = getattr(insp.insp_class, "days_main",0)
    n_shifts_last = getattr(insp.insp_class, "days_last",0)
    n_vess_main = getattr(insp.insp_class, "n_vessel_main",0)
    n_vess_last = getattr(insp.insp_class, "n_vessel_last",0)
    n_crew_main = getattr(insp.insp_class, "n_crew_main",0)
    n_crew_last = getattr(insp.insp_class, "n_crew_last",0)

    try:
        # port inspection
        device_inspected = insp.insp_class.intervened_devices
        n_device_port = getattr(insp.insp_class, "n_device_at_port", None)
        n_device_store_port = getattr(insp.insp_class, "n_device_stored_at_port", None)
        n_tech_inps_tot = n_tech_inps * device_inspected

        return insp_id, rov_cost_insp, device_inspected, n_tech_inps_tot, c_tech_inps, n_device_port, n_device_store_port

    except AttributeError:
        # site inspection
        device_inspected = max(getattr(insp.insp_class, attr, 0) or 0
                                for attr in ['intervened_wtg', 'intervened_pv', 'intervened_wec'])

        n_tech_inps_tot = kpi_aux.n_technicians(
            device_inspected = device_inspected,
            n_tech_inps = n_tech_inps,
            n_shifts = n_shifts_last if n_shifts_main == 0 else n_shifts_main+n_shifts_last,
            n_vess = n_vess_last if n_shifts_main == 0 else n_vess_main
        )

        return insp_id, rov_cost_insp, device_inspected, n_tech_inps_tot, c_tech_inps


def values_from_log_file(
    df: pd.DataFrame,
    ves: object,
    duration_shift: float,
    oper_dict_tech: dict = None,
    rov_dict_cost: dict = None,
    rov_tech_vessel_count = None

):
    """
    This function calculates the time of transit, standby and maneuver for each operation. Furtermore,
    it calculates the days of vessel use and the cost of ROV and technicians.
    """

    # Time calculation of vessel use
    df['transit_ts'] = (df['d_end_transit_ts'] - df['d_end_dur_net_port']).dt.total_seconds()/3600
    df['transit_tp'] = (df['d_end_transit_tp'] - df['d_end_dur_net_site']).dt.total_seconds()/3600
    transit_time = df['transit_ts'].sum() + df['transit_tp'].sum()

    df['standby_p_start'] = (df['d_end_dur_net_port']-df['d_end_leadtime']).dt.total_seconds()/3600
    df['standby_p_end'] = (df['d_end']-df['d_end_transit_tp']).dt.total_seconds()/3600
    standby_time = df['standby_p_start'].sum() + df['standby_p_end'].sum()

    df['maneuvre'] = (df['d_end_dur_net_site']-df['d_end_transit_ts']).dt.total_seconds()/3600
    maneuver_time = df['maneuvre'].sum()

    df = kpi_aux.remove_row_vessel_double(df = df, ves = ves, rov_tech_vessel_count = rov_tech_vessel_count)

    if not df.empty:
        tot_tech_cost, rov_cost = kpi_aux.tech_rov_cost(
            df = df,
            rov_dict_cost = rov_dict_cost,
            duration_shift = duration_shift,
            oper_dict_tech = oper_dict_tech
        )
    else:
        tot_tech_cost = 0
        rov_cost = 0

    return transit_time, standby_time, maneuver_time, tot_tech_cost, rov_cost


def find_time_log_events_insp(
        log_events_merged_insp,
        operations_inspect_site,
        operations_inspect_port,
        duration_shift,
        ves: object,
        insp_port_data,
        rov_tech_vessel_count: dict = None
    ):

    """
    Function to calculate time and cost for inspections

    Args:
    log_events_merged_insp (:obj:`pd.DataFrame`): Log of inspections events from log_events_merged
    operations_inspect_site(:obj:`list`): list of objects :class:`InspectionsSiteStat`
    operations_inspect_port(:obj:`list`): list of objects :class:`InspectionsTowStat`
    duration_shift(:obj:`int`): duration of the shift
    ves (:obj:`object`): object of class `Vessel`
    insp_port_data (:obj:`dict`): Dict with first key tech InspectionsPort.id, values with class with `OperationTow` or `InspectionsPort`
    rov_tech_vessel_count(:obj:`dict`): Dictionary of Vessels and operation that already account for ROV and tech cost

    Returns:
        :obj:`float`:floats that represents the transit_time_insp, standby_time_insp,
                    maneuver_time_insp, days_vessel_insp, tot_rov_cost_insp, tot_tech_cost_insp
    """

    transit_time_insp, standby_time_insp, maneuver_time_insp, tot_rov_cost_insp, tot_tech_cost_insp = 0, 0, 0, 0, 0

    for insp in operations_inspect_site:
        insp_id, rov_cost_insp, device_inspected, n_tech_inps_tot, c_tech_inps = inspection_data(insp)

        log_events_merged_insp_sing = log_events_merged_insp[log_events_merged_insp['id'] == insp_id].copy()
        if log_events_merged_insp_sing.empty:
            continue

        # Check if the inspection costs for ROV and technician it has already been accounted for other vessels
        if any(insp.id in lst for lst in rov_tech_vessel_count.values()):
            rov_insp_day = 0
            c_tech_inps = 0
        else:
            rov_insp_day = kpi_aux.count_day(df = log_events_merged_insp_sing)

        rov_c_insp = rov_insp_day*rov_cost_insp
        oper_sched = insp.insp_class.ts_data.oper_sched
        if oper_sched.columns[0] is not None and oper_sched.columns[0] != 'datetime' and oper_sched.columns[0] != 'dur_total':
            oper_sched.rename(columns={oper_sched.columns[0]: 'datetime'}, inplace=True)

        # Days that this inspection is done
        try:
            # If the oper_sched is taken from pre-existing file is a str
            days_shift = len(oper_sched['days_inspected'].iloc[0].split(','))
        except AttributeError:
            # If the oper_sched is created is a list
            days_shift = len(oper_sched['days_inspected'])

        for _, row in log_events_merged_insp_sing.iterrows():
            start_day = row['d_trigger']
            n_ves = row['n_vessel']
            start_day = approximate_hourly_data(start_day)
            row_oper_sched = oper_sched.loc[oper_sched['datetime'] == start_day]

            # Take the hour of travel and net site
            transit_time_insp += (row_oper_sched['transit_to_port'].values[0]+row_oper_sched['transit_to_site'].values[0]) * n_ves           #important NOTE, approximation in case last shift, might be less vessel
            standby_time_insp += (row_oper_sched['wait_start'].values[0]+row_oper_sched['wait_port'].values[0]) * n_ves
            maneuver_time_insp += (row_oper_sched['dur_net_site'].values[0]) * n_ves
            tot_tech_cost_insp += n_tech_inps_tot*c_tech_inps

        tot_rov_cost_insp += rov_c_insp
        rov_tech_vessel_count[ves.id].append(insp.id)

    for insp in operations_inspect_port:
        insp_id, rov_cost_insp, device_inspected, n_tech_inps_tot, c_tech_inps, n_device_port, n_device_store_port = inspection_data(insp)

        # Technician need * technician cost for towing operations
        tech_rem = insp_port_data[insp_id][insp.insp_class.op_tow_port].tech_required * insp_port_data[insp_id][insp.insp_class.op_tow_port].tech_cost
        tech_red = insp_port_data[insp_id][insp.insp_class.op_tow_site].tech_required * insp_port_data[insp_id][insp.insp_class.op_tow_site].tech_cost
        tech_rem_red = insp_port_data[insp_id][insp.insp_class.op_tow_site_port].tech_required * insp_port_data[insp_id][insp.insp_class.op_tow_site_port].tech_cost
        tech_tow_cost = (device_inspected-n_device_port)*tech_rem_red + n_device_port*(tech_rem+tech_red)

        log_events_merged_insp_sing_port = log_events_merged_insp[log_events_merged_insp['id'] == insp_id]

        # Check if the inspection costs for ROV and technician it has already been accounted for other vessels
        if any(insp.id in lst for lst in rov_tech_vessel_count.values()):
            rov_insp_day = 0
            c_tech_inps = 0
        else:
            rov_insp_day = kpi_aux.count_day(log_events_merged_insp_sing_port)

        rov_c_insp_port = rov_insp_day*rov_cost_insp

        # Take the total hour of the inspection at port and divide for duration shift time to obtain the n_shift to pay
        dur_net_port_days = mt.ceil(insp_port_data[insp_id][insp_id].ts_data.dur_net_site/duration_shift)
        # Take the durations_net_site disconnecting one device, connecting/disconnecting and only connecting
        manuv_rem = insp_port_data[insp_id][insp.insp_class.op_tow_port].ts_data.dur_net_site
        manuv_rem_red = insp_port_data[insp_id][insp.insp_class.op_tow_site_port].ts_data.dur_net_site
        manuv_red = insp_port_data[insp_id][insp.insp_class.op_tow_site].ts_data.dur_net_site
        # Take the transit with device towing and without the device
        trans_without_dev = insp_port_data[insp_id][insp.insp_class.op_tow_port].ts_data.transit_ts
        trans_with_dev = insp_port_data[insp_id][insp.insp_class.op_tow_site_port].ts_data.transit_ts

        for _, row in log_events_merged_insp_sing_port.iterrows():
            start_day = row['d_trigger']

            end_day = row['d_end']
            time_total_tow = (end_day-start_day).total_seconds() / 3600

            transit_devices_tow = (device_inspected-n_device_port)*trans_with_dev*2 + n_device_port*trans_without_dev*2
            manuver_devices_tow = (device_inspected-n_device_port)*manuv_rem_red + n_device_port*manuv_rem + n_device_port*manuv_red
            stand_by_tow = time_total_tow - transit_devices_tow - manuver_devices_tow

            transit_time_insp += transit_devices_tow
            standby_time_insp += stand_by_tow
            maneuver_time_insp += manuver_devices_tow

            tot_tech_cost_insp += n_tech_inps_tot*dur_net_port_days*c_tech_inps + tech_tow_cost

        tot_rov_cost_insp += rov_c_insp_port

    return transit_time_insp, standby_time_insp, maneuver_time_insp, tot_tech_cost_insp, tot_rov_cost_insp


def calculate_event_costs(
    log_df: pd.DataFrame,
    ves: object,
    duration_shift: float,
    fuel_cost_density: float,
    rov_dict_cost: dict = None,
    oper_dict_tech: dict  = None,
    insp_params: dict  = None,
    rov_tech_vessel_count: dict = None
):
    """
    Calculate costs for specific events
    """
    if not log_df.empty:
        if insp_params:
            transit_time, standby_time, maneuver_time, days_tech, rov_cost = find_time_log_events_insp(
                log_events_merged_insp = log_df,
                rov_tech_vessel_count = rov_tech_vessel_count,
                **insp_params
            )

        else:
            transit_time, standby_time, maneuver_time, days_tech, rov_cost = values_from_log_file(
                df = log_df,
                ves = ves,
                duration_shift = duration_shift,
                oper_dict_tech=oper_dict_tech,
                rov_dict_cost=rov_dict_cost,
                rov_tech_vessel_count = rov_tech_vessel_count
            )

        transit_cost, maneuver_cost, standby_cost = kpi_aux.calculate_cost(
            transit_time,
            maneuver_time,
            standby_time,
            ves,
            fuel_cost_density
        )
    else:
        transit_cost, maneuver_cost, standby_cost, days_tech, rov_cost = zero_variables()

    return transit_cost, maneuver_cost, standby_cost, days_tech, rov_cost


def part_other_cost(
        df: pd.DataFrame,
        total_operations: list,
        find_element_class: object
):
    """ Calculate costs for part components and other costs occurred"""
    def get_parts_cost(fail_id):
        failure = find_element_class.find_failure_from_id(fail_id)
        return getattr(failure, 'parts_cost', 0)
    
    # Prepare dataframe of operations
    ops_df = pd.DataFrame([{
        'op_id': getattr(op_stat.op_class if hasattr(op_stat, 'op_class') else op_stat.insp_class, 'id'),
        'parts_cost': 0 if hasattr(op_stat, 'op_class') else getattr(op_stat.insp_class, 'parts_cost', 0),
        'other_costs': getattr(op_stat.op_class if hasattr(op_stat, 'op_class') else op_stat.insp_class, 'other_costs'),
        'port_costs': getattr(op_stat.op_class if hasattr(op_stat, 'op_class') else op_stat.insp_class, 'port_costs', 0)
    } for op_stat in total_operations])

    # Merge with log dataframe
    merged = df.merge(ops_df, left_on='id', right_on='op_id', how='inner')

    # select only operation operation and extract the failures that trigger them
    mask = merged['event'] == 'operation'
    fail_ids = (
        merged.loc[mask, 'comments']
        .astype(str)
        .str.split('.').str[0]
        .str.split('_')
        .apply(lambda x: '_'.join(x[1:]))
    )

    # Update parts_cost related to the failure
    merged.loc[mask, 'parts_cost'] = fail_ids.apply(get_parts_cost)

    # Total cost calculation
    part_cost = merged['parts_cost'].sum()
    try:
        other_cost = (
            merged['other_costs'].sum()
            + (merged['port_costs']* (
                    merged['d_end']
                    - merged['d_end_leadtime'].fillna(merged['d_trigger'])
                ).dt.days).sum()
        )
    except AttributeError:
        merged.to_csv(r'C:\Users\rmeda\Desktop\Temporary\temp.csv')
        raise AttributeError()

    return part_cost, other_cost


def zero_variables():
    return 0, 0, 0, 0, 0