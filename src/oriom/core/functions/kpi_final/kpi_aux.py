import pandas as pd
import numpy as np
import math as mt
import ast

from oriom.utils.read_dataframe_value import compute_rov_cost


def store_fuel_data(
    vessel_usage,
    ves,
    transit_cost,
    maneuver_cost,
    standby_cost,
    fuel_cost_times_density,
):
    vessel_key = f"{ves.id}_{ves.type}"
    vessel_usage[vessel_key] = {}
    for fuel_use, value_fuel in zip(['transit', 'maneuver', 'standby'], [transit_cost, maneuver_cost, standby_cost]):
        if fuel_cost_times_density != 0:
            vessel_usage[vessel_key][fuel_use] = value_fuel/fuel_cost_times_density
        else:
            vessel_usage[vessel_key][fuel_use] = 0

    return vessel_usage


def calculate_cost(
        transit_time_merged: float,
        maneuver_time_merged: float,
        standby_time_merged: float,
        vessel: float,
        fuel_cost_times_density: float
):
    """
    Calculate transit fuel costs

    Args:
        transit_time_merged (float): time of transit in hours [h]
        maneuver_time_merged (float): time of manuver in hours [h]
        standby_time_merged (float): time of stand_by at port in hours [h]
        vessel (class: ´Vessel´): object of the class ´Vessel´ considered
        fuel_cost_times_density (float): fuel cost*density of fuel [euros/l]

    Return:
        float: cost of transitfuel
        float: cost of manuver fuel
        float: cost of stand_by fuel
    """
    transit_cost = transit_time_merged*vessel.fuel_cons_transit*fuel_cost_times_density
    maneuver_cost = maneuver_time_merged*vessel.fuel_cons_maneuver*fuel_cost_times_density
    standby_cost = standby_time_merged*vessel.fuel_cons_standby*fuel_cost_times_density

    return transit_cost, maneuver_cost, standby_cost



def count_day(
        df: pd.DataFrame,
)->int:
    """
    This function create a new column on the dataframe indicating for each row the nº days that a ROV is used

    Args:
    df (pd.DataFrame): Log of events file
    ves (:obj:`object`): object of class `Vessel`

    Returns:
        int: days of ROV use
    """

    df = df.copy()
    df['start'] = np.where(
        df['d_end_leadtime'].notna(),
        df['d_end_leadtime'],
        df['d_trigger']
    )
    df['days_used'] = ((df['d_end'].dt.normalize() - df['start'].dt.normalize())/np.timedelta64(1, 'D')).astype(int) + 1
    df['days_used'] = df['days_used'] * df['n_vessel']
    days_vessel = mt.ceil(df['days_used'].sum())

    return days_vessel


def safe_get_tech_tot(
    x
):
    """
    This function take the technician cost from the log_events_merged file
    It is needed as for merged function is difficult to reestablish che cost of tech
    """
    if isinstance(x, dict):
        return x.get('tech_cost')
    elif isinstance(x, str) and x.strip().startswith('{'):
        try:
            return ast.literal_eval(x).get('tech_cost')
        except (ValueError, SyntaxError):
            return None
    return None


def n_technicians(
    device_inspected: int,
    n_tech_inps: int,
    n_shifts: int,
    n_vess: int
):

    """
    This function evaluate if technicians used in the inspections conduct consecutive inspections in one day.
    If consecutive inspections are done, the TOT number of technicians needed is divided by the number of devices
    inspected in 1 day.
    This is an appriximate number of tech needed cause the last shift is not considered, there could be less tech
    in last shift (negligible).

    Example:
        With no consecutive inspections
            device_inspected = 75, n_tech_inps = 4, n_shifts_main = 25, n_vess_main = 3
            n_tech_inps = 4*75 = 300
        With consecutive inspections
            device_inspected = 75, n_tech_inps = 4, n_shifts_main = 12, n_vess_main = 3, n_shifts_last = 1
            consecutive_inspections = 75/(3*12) = 2.08 (2 devices consecutively inspected)
            n_tech_inps = 4*75/2 = ~150 (150 technicians needed more or less, considering last shift would be 152 technicians)

    Args:
        device_inspected (int): number of devices inspected,
        n_tech_inps (int): number of technicians needed for each devices,
        n_shifts (int): number of shift conducted,
        n_vess (int): number of vessels used

    """
    n_tech_inps_tot = device_inspected * n_tech_inps
    # Evaluate if technicians used in the inspections conduct consecutive inspections in one day
    consecutive_inspections = int(round(device_inspected/(n_vess*n_shifts),0))
    if consecutive_inspections < 1:
        # in case long operation that requires more than one shift to be concluded
        consecutive_inspections = 1
    # if so, reduce the tech need for the inspection
    return n_tech_inps_tot/consecutive_inspections


def filter_df_events_per_vessel(
    df: pd.DataFrame,
    vessel_id: str,
    second_vessel: bool = True
) -> pd.DataFrame:

    """
    This function filters the dataframe for the given vessel_id and creates a column 'n_vessel'
    that corresponds to 'n_vessel_1' if vessel_id == vessel_1, or 'n_vessel_2' if vessel_id == vessel_2.

    Args:
        df (pd.DataFrame): Log of events dataframe.
        vessel_id (str): The vessel ID to filter by.
        second_vessel (bool): If True, include events where the vessel is vessel_2 as well.

    NOTE: 
        Using n_vessel_1_effective as we are calculating the number of charting vessel, and they could
        be less than n_vessel_1 due to the reuse of the vessel

    Returns:
        pd.DataFrame: Filtered dataframe with a new 'n_vessel' column.
    """
    df = df.copy()

    if second_vessel:
        vessel_1_column = 'n_vessel_1_effective'
        mask = (df['vessel_1'] == vessel_id) | (df['vessel_2'] == vessel_id)
    else:
        vessel_1_column = 'n_vessel_1'
        mask = df['vessel_1'] == vessel_id

    df_filtered = df[mask].copy()

    # Fill NaNs with 0 and ensure int
    df[vessel_1_column] = df[vessel_1_column].fillna(0).astype(int)
    df['n_vessel_2'] = df['n_vessel_2'].fillna(0).astype(int)

    # Use np.where to set n_vessel correctly without summing
    df_filtered['n_vessel'] = np.where(
        df_filtered['vessel_1'] == vessel_id,
        df_filtered[vessel_1_column],
        df_filtered['n_vessel_2']
    )

    return df_filtered


def remove_row_vessel_double(
        df: pd.DataFrame,
        ves: object,
        rov_tech_vessel_count: dict = {}
    ):

    """ Filter operation row for tech and ROV that have already been accounted for other vessels"""

    if rov_tech_vessel_count:
        # Filter if the df only if 2 different vessels are used
        mask_double_vessel = (
            ((df['vessel_1'] == ves.id) | (df['vessel_2'] == ves.id)) &
            ((df['vessel_1'].isin(rov_tech_vessel_count.keys())) | (df['vessel_2'].isin(rov_tech_vessel_count.keys())))
        )

        df.drop(df[mask_double_vessel].index, inplace=True)

    return df


def define_fuel_cost(
    vessel1_id,
    fuel_cost_hfo: float,
    fuel_cost_mdo: float,
    fuel_cost_mgo: float
)->float:
    """
    Auxiliary Function:
    Calculate the cost of fuel based on the vessel's fuel type, density, and fuel costs.

    Args:
        vessel1_id (:class:`~oriom.domain.Vessels`):
            Vessel class object.
        fuel_cost_hfo (int): Fuel cost €/ton.
        fuel_cost_mdo (int): Fuel cost €/ton.
        fuel_cost_mgo (int): Fuel cost €/ton.

    Returns:
        :obj:`float`: Density time cost -> €/l
    """
    fuel_type = vessel1_id.fuel_type
    if any([
        fuel_type == 'HFO',
        fuel_type == 'hfo'
    ]) is True:
        d = vessel1_id.density * 10**-6
        fuel_cost = fuel_cost_hfo
    elif any([
        fuel_type == 'MGO',
        fuel_type == 'mgo'
    ]) is True:
        d = vessel1_id.density * 10**-6
        fuel_cost = fuel_cost_mgo
    elif any([
        fuel_type == 'MDO',
        fuel_type == 'mdo'
    ]) is True:
        d = vessel1_id.density * 10**-6
        fuel_cost = fuel_cost_mdo

    fuel_cost_times_density = d * fuel_cost

    return fuel_cost_times_density


def tech_rov_cost(
        df: pd.DataFrame,
        rov_dict_cost: dict,
        duration_shift: float,
        oper_dict_tech: dict
):
    """
    Calculate the technicians costs and ROV costs for corrective operations

    Args:
        df (pd.DataFrame): Dataframe of Log_events for the operation type analysed
        rov_cost_dict (dict): Dict of rov per operations
        duration_shift (float):
        oper_dict_tech (dict): Dict of technicians costs per operations

    Returns:
        float: Total cost of technician for the operation type analysed
        float: Total cost of ROV for the operation type analysed
    """

    # Rov cost # IMPORTANT NOTE: the ROV cost are taken only from the operations and are multiplied by the number of vessel_1. Cost account are used only one day not rented more days
    df['rov_cost'] = df.apply(lambda row: compute_rov_cost(row['id'], row['n_vessel_1'], rov_dict_cost), axis=1)
    rov_cost = mt.ceil(df['rov_cost'].sum())

    # Days of technician
    df['days_tech'] = np.ceil((df['d_end']-df['d_end_wait_start']).dt.total_seconds() / 86400).astype(int)
    df['hours_tech'] = np.ceil((df['d_end']-df['d_end_wait_start']).dt.total_seconds() / 3600).astype(int)
    # Check if there is the need of a double shift (exchange of personnel)
    df['n_shift_tech'] = np.where(df['hours_tech'] > duration_shift, 2, 1)

    # Cost of tot tech on each operation in case merged operation
    df['tech_cost'] = df['comments'].apply(safe_get_tech_tot)

    # In case is single operation, fill the tech_cost with the value from oper_dict_tech
    if oper_dict_tech:
        mask_none = df['tech_cost'].isna()
        df.loc[mask_none, 'tech_cost'] = df.loc[mask_none, 'id'].map(oper_dict_tech).fillna(0)
    tot_tech_cost = mt.ceil((df['days_tech'] * df['tech_cost'] * df['n_shift_tech']).sum())

    return tot_tech_cost, rov_cost

if __name__ == '__main__':
    pass




    