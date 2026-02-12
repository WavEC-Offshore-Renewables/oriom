import logging
import random
import datetime
import math

import pandas as pd
import numpy as np
import networkx as nx

from logistic_tools.utils.read_dataframe_value import approximate_hourly_data, get_inspections_date
from logistic_tools.core.functions.layout_power import aux_layout_power_func


DICT_DAYS = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}


def find_highest_power_node(G):

    '''
    Take the Graph of the farm and give back as string the level of the component on which the power is implemented

    Args:
        G (:obj:`nx.DiGraph`): DiGraph.

    Return:
        str: of the component level
    '''
    max_power = float('-inf')  # Lowest value
    
    for node in G.nodes():
        power = G.nodes[node].get('power', 0)  # Get power, 0 if not max
        if power > max_power:
            max_power = power
            component_level_power = G.nodes[node]['level']

    return component_level_power


def get_nearest_month_value(month: int, month_dict: dict):
    """
    Take the month or the closest month to the shutdown dict

    Args:
        month (int): Month required (1-12)
        month_dict (dict): Shutdown dict

    Returns:
        closest month to month in the shutdown dict
    """
    if month in month_dict:
        return month
    
    available_months = sorted(month_dict.keys())
    nearest_month = min(available_months, key=lambda m: abs(m - month))
    return nearest_month

    
def create_end_start_lifetime(
    date: datetime, 
    event: str, 
    cols: list
):
    
    """ 
    Function to create last and first row of the lifetime for the energy availability dataframe 

    Args:
        date (datetime): dates of the row 
        event (string): event of the row (decommissioning or commissioning)
        cols (list): name of the columns of the dataframe
    """
    date_row = pd.DataFrame([[
        date,
        event,
        '-',
        '-',
        '-',
        '-',
        '-',
        '-',
        100.00,
        None
    ]], columns=cols)

    return date_row


def choose_loc(
    level: str,
    G: nx.DiGraph,
    component_level_power: str,
    date: datetime,
    list_failed: set = (),
    tech: str = None
):
    '''
    Chooses the location of device that fail in the farm.
    Based on the how the failure or operation is defined, it chooses randomly a node or an edge.
    IMPORTANT NOTE: the edge must be in a "visible"=True path to be choosen.
    Take component that is not already failed (not present in list_failed) if the list is not empty

    Args:
        level (:obj:`str`): Level of the failure (node/edge).
        G (:obj:`nx.DiGraph`): Graph of tech farm.
        component_level_power (str): level where the power is implemented in the layout farm (usually lowest level implemented)
        list_failed (:obj:`set`): set of already failed component
        tech (:obj:`str`): technology analyzed
        

    Raises:
        ValueError: if the level of failure is not recognized.

    Returns:
        location of the event, node (int) /edge (tuple).
    '''

    if any([
        level == 'device',
        level == 'string',
        level == 'substation',
        level == 'mv_transformer',
        level == 'inverter',
        level == 'circuit_braker',
        level == 'switcher'
    ]):

        
        if tech == 'PV':
            if any(keyword in level for keyword in ['device', 'string']):
                level = component_level_power

        #list_nG = list(n for n, attr in G.nodes(data=True) if attr['level'] == level) 
        list_nG = [n for n, attr in G.nodes(data='level') if attr == level]

        if list_failed is None:
            list_failed = set()

        #list_nG_not_failed = [x for x in list_nG if x not in set_2]    
        list_nG_not_failed = set(list_nG) - list_failed

        if not list_nG_not_failed:
            logging.error(f"At {date} all {level} has failed, an already failed {level} has been selected for the failure")
            list_nG_not_failed = list_nG

        loc = random.choice(list(list_nG_not_failed))

    elif any([
        level == 'array_cable',
        level == 'string_cable',
        level == 'exp_cable',
        level == 'exp_cable_island',
        level == 'dyn_cable-sub',
        level == 'dyn_cable-transf',
        level == 'dyn_cable-cb'
    ]) is True:
        
        list_eG = [(s, e) for s, e, attr in G.edges(data=True) if attr.get('level') == level and attr.get('visible') is True]
        if list_failed is None:
            list_failed = set()
        list_eG_not_failed = set(list_eG) - list_failed

        if not list_eG_not_failed and list_eG:
            logging.error(f"At {date} all the components {level} has failed, an already failed {level} has been selected for the failure")
            list_eG_not_failed = list_eG

        if list_eG_not_failed:
            (s, e) = random.choice(list(list_eG_not_failed))
            loc = (s, e)
        else:
            if tech == 'PV' and level == 'string_cable':
                # No edge found for this failure cause tech not implemented
                loc = ('x', 'x')        # TODO manage better this case
            else:
                e_ = (f"At {date} all the edges {level} has failed")
                raise KeyError(e_)
    else:
        logging.info(level)
        logging.error(f'{level} Layout perc: "device/edge" not recognized')
        raise ValueError(f'{level} Layout perc: "device/edge" not recognized')
    return loc


def fix_percentage_markers_dates(
        df:pd.DataFrame
    )-> pd.DataFrame:

    """
    This function copy the percentage of the First Day of month', 'Last Day of month' with the last
    perventage value known.

    Args:
        df (pd.Dataframe): Dataframe of energy availability

    Returns:
        df (pd.Dataframe): Dataframe of energy availability with percentage corrected on target_events
    """

    perc = df['Perc_availability'].copy()

    # Events to update
    target_events = ['First Day of month', 'Last Day of month', 'decomissioning_project']

    # Target df
    is_target = df['Event'].isin(target_events)

    # Non target event put NAN
    perc[is_target] = np.nan

    # Propagate forward
    perc = perc.ffill()

    # Apply only at target row
    df.loc[is_target, 'Perc_availability'] = perc[is_target]
   
    return df

def fix_percentage_simultaneousy_op(
        df:pd.DataFrame,
        find
    )-> pd.DataFrame:

    """
    This function copy the percentage of the First Day of month', 'Last Day of month' with the last
    perventage value known.

    Args:
        df (pd.Dataframe): Dataframe of energy availability

    Returns:
        df (pd.Dataframe): Dataframe of energy availability with percentage corrected on target_events
    """
    df_op = df[df['Event'] == 'operation'].copy()


def string_location(
    failed_strings: dict, 
    string_inverter: set,
    )-> int:

    """ 
    Find a random string location that is not already closed in the inverter location

    Args:
        device_shutted_string_level_inverter (dict): nested dictionary with 1st key:node inverter, 2nd key:position of string closed, value True
        string_inverter (set): Set of string for the inverter   
        
    Returns:
        int: a random string location that is not already closed in the inverter location
    
    """

    valid_k_string = list(string_inverter - failed_strings)

    if not valid_k_string:
        logging.warning("E availability: All strings are failed for the inverter. An already closed string is selected.")

    k = random.choice(valid_k_string)

    return k


def add_markers_month_year(
        df: pd.DataFrame, 
        df_extra: pd.DataFrame
    ):

    """
    Add end month/year marker to the DataFrame without modifying the order of the original DataFrame.

    Args:
        df (pd.DataFrame): Original DataFrame with 'Date'
        df_extra (pd.DataFrame): Dataframe with extra markers to insert in order based on 'Date'

    Returns:
        pd.DataFrame: New DataFrame with markers inserted at the correct positions

    """

    # Evaluate index of insert
    insert_indices = np.searchsorted(df['Date'].values, df_extra['Date'].values)

    df_parts = []
    last_idx = 0

    for extra_idx, insert_idx in enumerate(insert_indices):
        # Add df between last_idx and insert_idx
        if insert_idx > last_idx:
            df_parts.append(df.iloc[last_idx:insert_idx])
        # Add row extra as single DataFrame
        df_parts.append(df_extra.iloc[[extra_idx]])
        last_idx = insert_idx

    # Add eventual finals rows 
    if last_idx < len(df):
        df_parts.append(df.iloc[last_idx:])

    df_final = pd.concat(df_parts, ignore_index=True)

    return df_final


def find_power_at_node(G_tech: nx.DiGraph, level: str):
    """Find the average power of all nodes connected to the given level (node or edge)."""

    power_list_level = []

    # Node case
    if any(data.get("level") == level for _, data in G_tech.nodes(data=True)):
        for node, data in G_tech.nodes(data=True):
            if data.get("level") == level:
                if data.get("power", 0) == 0:
                    connected_nodes = nx.ancestors(G_tech, node) | {node}
                    power_list_level.append(
                        sum(G_tech.nodes[n].get("power", 0) for n in connected_nodes)
                    )
                else:
                    power_list_level.append(data.get("power", 0))
                    break

    # Edge case
    elif any(data.get("level") == level for _, _, data in G_tech.edges(data=True)):
        for u, v, data in G_tech.edges(data=True):
            if data.get("level") == level:
                # scegli un nodo di riferimento, ad es. quello "a valle" (v)
                node = u
                if G_tech.nodes[node].get("power", 0) == 0:
                    connected_nodes = nx.ancestors(G_tech, node) | {node}
                    power_list_level.append(
                        sum(G_tech.nodes[n].get("power", 0) for n in connected_nodes)
                    )
                else:
                    power_list_level.append(G_tech.nodes[node].get("power", 0))
                    break

    return sum(power_list_level) / len(power_list_level)


def take_date_inspection_oper_scheduler(
        log_aux: pd.DataFrame, 
        oper_schedule: pd.DataFrame
)->list:
    """
    Take all the d_dtrigger dates, approximate them to h and obtain all the days inspected
        from the operation schedule of the inspection considered
    Args:
        log_aux (pd.DataFrame): DataFrame with log events of the inspection considered.
        oper_schedule (pd.DataFrame): DataFrame with operation schedule of the inspection considered.
    Returns:
        list: of inspection dates.
    """

    log_aux_d_trigger = log_aux['d_trigger'].tolist()
    log_aux_d_trigger = [approximate_hourly_data(d) for d in log_aux_d_trigger]
    try:
        oper_schedule_effective = oper_schedule.loc[log_aux_d_trigger]
    except KeyError:
        oper_schedule_effective = oper_schedule.loc[oper_schedule['datetime'].isin(log_aux_d_trigger)]
    inspection_dates = get_inspections_date(oper_schedule_effective)
    return inspection_dates


def timeseries_power_preventive_evaluation(
    insp: object,
    inspection_dates: list,
    metocean_timeseries: pd.DataFrame,
    power_level: float,
    tech1: str
)->tuple[list[list[float]], list[list[float]]]:
    """Calculate energy loss for preventive inspection using timeseries power data.

    Extrapolates all the dates of start and end of the inspections
    Filter the metocean timeseries data for each inspection.
    Evaluate the energy losses considering possible multiple operations in a shift and last shift opeartion.
    
    Args:
        insp (:obj:`Inspection`): Inspection object.
        inspection_dates (list): List of inspection dates.
        metocean_timeseries (:obj:`pd.DataFrame`): DataFrame with metocean timeseries data and power ORE production.
        power_level (:obj:`float`): Power level percentage during the inspection.
        tech1 (:obj:`str`): Technology type (e.g., 'pV', 'wind', 'wave').

    Returns:
        tuple[list[list[float]], list[list[float]]]: Energy loss and shutdown hours lists.
    """
    energy_list, shutdown_hour_list = [], []
    power_col = 'p_' + tech1 + '_per_device'

    towing_inspection = getattr(insp, 'op_tow_port', False)
    # Towing inspections dates evaluation
    if towing_inspection:
        if getattr(insp, 'towing_log', pd.DataFrame()).empty:
            e_ = f'Towing log not found in the inspection class for "{insp.id}".\n'
            e_ += "Please if reusing previous log_event_file make sure to reuse the operation_schedule too for inspection at port"
            raise ValueError(f"Timeseries power preventive evaluation:\n{e_}")
        inspection_date_starts, inspection_date_ends = create_list_date_port(insp.towing_log)
        coeff_main = 1
        base_factor_main = power_level
        coeff_last = 1
        base_factor_last = power_level

    # Site inspections dates evaluation
    else:
        inspection_date_starts, inspection_date_ends = create_list_date(insp, inspection_dates)
        if insp.days_main != 0:
            crew_main = insp.n_crew_main if insp.n_crew_main > 0 else 1
            coeff_main = math.ceil(insp.n_dev_done_main_shift/crew_main) if crew_main > 0 else 1
            base_factor_main = power_level * insp.n_vessel_main * math.ceil(insp.n_dev_done_main_shift/coeff_main)
        if insp.days_last != 0:
            crew_last = insp.n_crew_last if insp.n_crew_last > 0 else 1
            # Calculate exact number of device left for last shift
            device_total_insp = sum([insp.intervened_wtg, insp.intervened_wec, insp.intervened_pv])
            device_left = device_total_insp - (insp.n_dev_done_main_shift * insp.n_vessel_main * insp.days_main)
            n_parallel = min(crew_last * insp.n_vessel_last, device_left)
            coeff_last = math.ceil(insp.n_dev_done_last_shift/crew_last) if crew_last > 0 else 1
            n_dev_last = device_left % n_parallel if device_left % n_parallel !=0 else n_parallel
            # Consider more consecutive device operated in one shift, all shift n_ves*n_dev_done_last_shift except last
            base_factor_last = power_level * math.ceil(n_parallel)
            base_factor_last_last = power_level * math.ceil(n_dev_last)

    # for each inspection planned evaluate energy loss and shutdown hours
    for insp_start, insp_end in zip(inspection_date_starts, inspection_date_ends):
        energy, hour_shut = 0, 0
        for i, (date_start, date_end) in enumerate(zip(insp_start, insp_end)):
            # filter power data
            mask = (metocean_timeseries.index >= date_start) & (metocean_timeseries.index < date_end)
            power_data = metocean_timeseries.loc[mask, power_col]
            if power_data.empty:
                continue
            # divide the hours in different group if consecutive op have been done (n_device_shift>n_crew)
            if (i+1) == len(insp_start) and insp.days_last != 0:
                power_data_groups = np.array_split(power_data, coeff_last)
                for jj, group in enumerate(power_data_groups):
                    if (jj+1) == len(power_data_groups):
                        energy += group.sum() * base_factor_last_last
                        hour_shut += len(group) * base_factor_last_last
                    else:
                        energy += group.sum() * base_factor_last
                        hour_shut += len(group) * base_factor_last
            else:
                power_data_groups = np.array_split(power_data, coeff_main)
                for group in power_data_groups:
                    energy += group.sum() * base_factor_main
                    hour_shut += len(group) * base_factor_main
        energy_list.append(energy)
        shutdown_hour_list.append(hour_shut)

    if not energy_list:
        energy_list.append(0)
    if not shutdown_hour_list:
        shutdown_hour_list.append(0)
        
    return energy_list, shutdown_hour_list


def create_list_date(insp: object, inspection_dates: list)->tuple[list[list[pd.Timestamp]],list[list[pd.Timestamp]]]:
    """ Manage different duration for last shift if present and obtain end of inspections"""
    inspection_date_starts, inspection_date_ends = [], []

    # manage different duration for last shift if present and obtain end of inspections
    for sub in inspection_dates:
        group_start, group_end = [], []
        if insp.days_last != 0:
            for i, d in enumerate(sub):
                group_start.append(d)
                if i == len(sub)-1:
                    group_end.append(d + pd.Timedelta(hours=math.ceil(insp.duration_last)))
                else:
                    group_end.append(d + pd.Timedelta(hours=math.ceil(insp.duration_main)))
        else:
            for d in sub:
                group_start.append(d)
                group_end.append(d + pd.Timedelta(hours=math.ceil(insp.duration_main)))

        inspection_date_starts.append(group_start)
        inspection_date_ends.append(group_end)

    return (inspection_date_starts, inspection_date_ends)


def create_list_date_port(towing_log: pd.DataFrame,)->tuple[list[list[pd.Timestamp]],list[list[pd.Timestamp]]]:
    """Take start and end of each towing of the device for preventive inspection at port.

    Args:
        towing_log (:obj:`pd.DataFrame`): DataFrame with metocean timeseries data and power ORE production.

    Returns:
        tuple[list[list[float]], list[list[float]]]: Energy loss and shutdown hours lists.
    """   

    inspection_date_starts, inspection_date_ends = [], []
    for _, group in towing_log.groupby("d_trigger"):
        inspection_date_starts.append(group["d_TTP_start"].tolist())
        inspection_date_ends.append(group["d_TTP_end"].tolist())

    return (inspection_date_starts, inspection_date_ends)



def statistical_power_preventive_evaluation(
    dict_power: dict, 
    shutdown_hours_dict: dict, 
    date: datetime, 
    n_device_tot: int, 
    power_level: float,
    degradation_rate: float,
    start_year: int,
    double_shift : bool,
    selected_month: int
)-> float:
    """ 
    Evaluate energy loss for the preventive inspection
    - PV tech:
        The power dict is averaged in month and hour of the mont
        For each hour of the shutdown_hours dict count the energy loss in that hour
            Consider only day hour if cannot be worked in the night
    - Wind-Wave tech:
        Take power production per device and power level of the component and multiply 
            per h shutted

    Args:
        dict_power (:obj:`dict`): Dictionary of monthly power.
        shutdown_hours_dict (:obj:`float`): Tot hours of shutdown for start month inspection
        n_device_tot (:obj:´int´): Number of devices total.
        power_level (:obj:´float´): nº Power of devices at the component level.
        degradation_rate (:obj:`float`, optional): Degradation rate of the PV power,
        start_year (:obj:´int´): Start year of the simulation.
        double_shift (:obj:bool): Night shift available.
        selected_month (:obj:int): Month of the inspection to consider in dict_power

    Return:
        float: Energy losses
        """

    # For PV the is a dict of months has values as dict of hours
    if any(isinstance(v, dict) for v in dict_power.values()) is True:
        energy = 0
        hours_counted = 0
        i = date.hour
        y = date.year
        shutdown = math.ceil(shutdown_hours_dict[selected_month])

        while hours_counted < shutdown:
            if dict_power[selected_month][i] > 0 or double_shift:
                p = dict_power[selected_month][i] / (n_device_tot * power_level)
                for y_ in range(y - start_year):
                    p *= (1 - degradation_rate / 100)
                energy += p
                hours_counted += 1
            # next hour
            i = (i + 1) % 24
        return energy
    # For wave and wind tech
    else:
        energy = (shutdown_hours_dict[selected_month]*(dict_power[selected_month]/n_device_tot)*power_level)
        return energy


def take_power_level_inspections(G_tech: nx.DiGraph, inspections_port_stat: list, inspections_site_stat: list)->dict:
    """Take the power at different levels of the layout graph.
    Return: (dict) a dictionary with power at different levels.
    """
    power_level_dict = {}
    component_level_power = aux_layout_power_func.find_highest_power_node(G_tech)
    power_level_dict[component_level_power] = aux_layout_power_func.find_power_at_node(G_tech = G_tech, level = component_level_power)
    for inspection in inspections_port_stat+inspections_site_stat:
        level = getattr(inspection.insp_class,'level',None)
        if level and level != component_level_power and level not in power_level_dict:
            power_level_dict[level] = aux_layout_power_func.find_power_at_node(G_tech = G_tech, level = level)
    return power_level_dict


def take_month_inspection(start_insp_date: datetime, row: pd.Series, shutdown_hours_dict: dict):
    """Take the month to select the power dict."""
    # Find month to select for power dict
    date_range = pd.date_range(start=start_insp_date, end=row['d_end'], freq='MS')
    months_list = [date.month for date in date_range]

    if len(months_list) == 0:
        selected_month = start_insp_date.month
    else:
        selected_month = int(math.ceil(np.mean(months_list)))
    selected_month = aux_layout_power_func.get_nearest_month_value(selected_month, shutdown_hours_dict)
    return selected_month

if __name__ == '__main__':
    pass