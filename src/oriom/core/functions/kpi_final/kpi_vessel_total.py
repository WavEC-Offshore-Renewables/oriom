import pandas as pd
import numpy as np
import math as mt

from oriom.utils.aux_functions import safe_copy_df, save_file_csv

from oriom.core.functions.vessels_manager.VesselDayCount import VesselDayCounter
from oriom.core.functions.kpi_final import kpi_aux
from oriom.core.functions.kpi_final.kpi_cost_evaluator import calculate_event_costs, part_other_cost


COLS = [
    'vessel_id',
    'vessel type',
    'n_chart_days',
    'av_vessel_costs',
    'tot_vessel_costs',
    'av_mobilization_costs',
    'tot_mobilization_costs',
    'av_technicians_costs',
    'tot_technicians_costs',
    'av_part_costs',
    'tot_part_costs',
    'av_rov_costs',
    'tot_rov_costs',
    'av_other_costs',
    'tot_other_costs',
]


def create_lifetime_cost(df):
    """
    This function creates the lifetime cost of the operations and inspections.
    Args:
        df (:obj:`pd.DataFrame`): Dataframe with the costs of the operations and inspections.
    Returns:
        :obj:`pd.DataFrame`: Dataframe with the added cols of lifetime cost of the operations and inspections.
    """
    df['average_direct_costs'] = df['av_vessel_costs'] + df['av_part_costs'] + df['av_technicians_costs'] + df['av_technicians_costs'] + df['av_other_costs'] + df['av_rov_costs']
    df['lifetime_direct_costs'] = df['tot_vessel_costs'] + df['tot_part_costs'] + df['tot_technicians_costs'] + df['tot_mobilization_costs'] + df['tot_other_costs'] + df['tot_rov_costs']

    return df


def averaged_res(value, days):
    if days>0:
        return value/days
    else:
        return 0


def kpi_cost_vessel_internal(
    log_events_op_orig: pd.DataFrame,
    log_events_op_merged_orig: pd.DataFrame,
    log_events_op_def_merged_orig: pd.DataFrame,
    log_events_op_merged_oper_orig: pd.DataFrame,
    log_events_insp_merged_orig: pd.DataFrame,
    log_events_mobi_merged_orig: pd.DataFrame,
    log_events_tow_orig: pd.DataFrame,
    log_events_op_port_orig: pd.DataFrame,
    vessel_day_count: object,
    vessel_day_count_ST: object,
    tech_per_oper_dict: dict,
    rov_cost_dict: dict,
    insp_port_data: dict,
    vessels: list,
    duration_shift: float,
    total_operations: list,
    operations_tow_stat: list,
    inspections_site_stat:list,
    inspections_port_stat:list,
    fuel_cost_hfo: float,
    fuel_cost_mgo: float,
    fuel_cost_mdo: float,
    find_element_class: object,
    years: int = 1,
)->tuple[pd.DataFrame,pd.DataFrame]:

    """
    Here are calculated all the costs sustained for the lifetime separating the various operations conducted
    (single operations, merged operations, deferred merged operations, site inspections and tow inspections)

    Args:
        log_events_op_orig (:obj:`pd.DataFrame`): Log of all operations events not merged used for other costs and parts costs
        log_events_op_merged_orig (:obj:`pd.DataFrame`): Log of all operations events merged used for immediate merged
        log_events_op_def_merged_orig (:obj:`pd.DataFrame`): Log of all operations events deferred merged used for deferred merged
        log_events_op_merged_oper_orig (:obj:`pd.DataFrame`): Log of all operations events that cannot be merged used for not merged ops costs
        log_events_insp_merged_orig (:obj:`pd.DataFrame`): Log of all inspections events used for inspections costs
        log_events_mobi_merged_orig (:obj:`pd.DataFrame`): Log of all mobilisations events used for mobilisation costs
        log_events_tow_orig (:obj:`pd.DataFrame`): Log of all tow events for corrective operations
        log_events_op_port_orig (:obj:`pd.DataFrame`): Log of all corrective operations at port
        vessel_day_count (obj ´VesselDayCounter´): object of class ´VesselDayCounter´
        vessel_day_count_ST (obj ´VesselDayCounter´): object of class ´VesselDayCounter´ for only ST vessel
        tech_per_oper_dict (:obj:`dict`): Dict of technicians per operations
        rov_cost_dict (:obj:`dict`): Dict of rov per operations
        insp_port_data (:obj:`dict`): Dict with first key tech InspectionsPort.id, values with class with `OperationTow` or `InspectionsPort`
        vessels (:obj:`list`): List of objects :class:`Vessel`
        duration_shift(:obj: float): Number of hours of duration of the working shift by law
        total_operations (:obj:`list`): List of objects that comprehend the whole oeprations and inspections
        operations_tow_stat (:obj:`list`): List of objects :class:`OperationsTowStat`.
        inspections_site_stat(:obj:`list`): list of objects :class:`InspectionsSiteStat`
        inspections_port_stat(:obj:`list`): list of objects :class:`InspectionsTowStat`
        fuel_cost_hfo (:obj:`int`): Fuel cost €/ton.
        fuel_cost_mdo (:obj:`int`): Fuel cost €/ton.
        fuel_cost_mgo (:obj:`int`): Fuel cost €/ton.
        find_element_class (Find_element_class): Initialized instance that provides fast access to operations,
            vessels and failures via internal dictionaries.
        years (:obj:`int`): lifetime of the project. Default = 1

    Returns:
        :obj:`pd.DataFrame`: dataframe directs costs for all the operations divided by vessels .
    """
    vessel_fuel_usage = {}
    kpi_om = pd.DataFrame(columns=COLS)
    rov_tech_vessel_count = {}
    failure_corrected_port = []

    op_cost = 0 ## VALUE NOT RETURNED, USEFULL FOR A DEBUG AND CHECK THE INSPECTION vs CORRECTION COST
    insp_cost = 0   ## VALUE NOT RETURNED, USEFULL FOR A DEBUG AND CHECK THE INSPECTION vs CORRECTION COST

    # Start of the code
    log_events_op = safe_copy_df(log_events_op_orig, ['id', 'comments'])
    log_events_op_merged = safe_copy_df(log_events_op_merged_orig, ['id', 'comments'])
    log_events_op_def_merged = safe_copy_df(log_events_op_def_merged_orig, ['id', 'comments'])
    log_events_op_merged_oper = safe_copy_df(log_events_op_merged_oper_orig, ['id', 'comments'])
    log_events_insp_merged = safe_copy_df(log_events_insp_merged_orig, ['id', 'comments'])
    log_events_mobi_merged = safe_copy_df(log_events_mobi_merged_orig, ['id', 'comments'])
    log_events_tow = safe_copy_df(log_events_tow_orig, ['id', 'comments'])
    log_events_op_port = safe_copy_df(log_events_op_port_orig, ['id', 'comments'])

    # Cost for port operation with no vessel defined
    if not log_events_op_port.empty:
        n_oper_at_port = len(log_events_op_port)

        # Tech and ROV costs
        tot_tech_cost_port, rov_cost_port = kpi_aux.tech_rov_cost(
            df = log_events_op_port,
            rov_dict_cost = rov_cost_dict,
            duration_shift = duration_shift,
            oper_dict_tech = tech_per_oper_dict
        )
        # Part and Other costs
        part_cost_port, other_cost_port = part_other_cost(
            df = log_events_op_port,
            total_operations = total_operations,
            find_element_class = find_element_class
        )
        
        # List of failures corrected at port to do not count double part costs
        failure_corrected_port = (
            log_events_op_port.loc[
                log_events_op_port['comments'].str.startswith('oper', na=False),
                'comments'
            ]
            .unique()
            .tolist()
        )

        tech_cost_avg_port = averaged_res(tot_tech_cost_port, n_oper_at_port)
        rov_cost_avg_port = averaged_res(rov_cost_port, n_oper_at_port)
        part_cost_avg_port = averaged_res(part_cost_port, n_oper_at_port)
        other_cost_avg_port = averaged_res(other_cost_port, n_oper_at_port)

        kpi = pd.DataFrame([[
            'oper_port',
            'port oper',
            n_oper_at_port,
            0,
            0,
            0,
            0,
            round(tech_cost_avg_port, 2),
            round(tot_tech_cost_port, 2),
            round(part_cost_avg_port, 2),
            round(part_cost_port, 2),
            round(rov_cost_avg_port, 2),
            round(rov_cost_port, 2),
            round(other_cost_avg_port, 2),
            round(other_cost_port, 2),
        ]], columns=COLS)

        kpi_om = pd.concat([kpi_om, kpi], ignore_index=True)

    # cost durations for merged operations by vessels
    for ves in vessels:
        # Find fuel cost
        fuel_cost_times_density = kpi_aux.define_fuel_cost(ves, fuel_cost_hfo, fuel_cost_mdo, fuel_cost_mgo)

        # Prepare the datasets
        log_o = kpi_aux.filter_df_events_per_vessel(log_events_op, ves.id, False)
        log_o_m = kpi_aux.filter_df_events_per_vessel(log_events_op_merged, ves.id)
        log_o_m_o = kpi_aux.filter_df_events_per_vessel(log_events_op_merged_oper, ves.id)
        log_o_m_d = kpi_aux.filter_df_events_per_vessel(log_events_op_def_merged, ves.id)
        log_i_m = kpi_aux.filter_df_events_per_vessel(log_events_insp_merged, ves.id)
        log_m_m = kpi_aux.filter_df_events_per_vessel(log_events_mobi_merged, ves.id)
        log_o_t = kpi_aux.filter_df_events_per_vessel(log_events_tow, ves.id)

        charter_days_ST = vessel_day_count_ST.count_day_vessel(ves_id = ves.id)
        charter_days = vessel_day_count.count_day_vessel(ves_id = ves.id)

        # Calculate for merged corrective operations
        transit_cost_1, maneuver_cost_1, standby_cost_1, days_tech_merged, rov_cost_merged = calculate_event_costs(
            log_df = log_o_m,
            ves = ves,
            duration_shift = duration_shift,
            fuel_cost_density = fuel_cost_times_density,
            rov_dict_cost = rov_cost_dict,
            oper_dict_tech = None,
            insp_params = None,
            rov_tech_vessel_count = rov_tech_vessel_count
        )

        # Calculate for merged deferred corrective operations
        transit_cost_1_def, maneuver_cost_1_def, standby_cost_1_def, days_tech_merged_def, rov_cost_def = calculate_event_costs(
            log_df = log_o_m_d,
            ves = ves,
            duration_shift = duration_shift,
            fuel_cost_density = fuel_cost_times_density,
            rov_dict_cost=rov_cost_dict,
            oper_dict_tech=None,
            insp_params=None,
            rov_tech_vessel_count = rov_tech_vessel_count
        )

        # Calculate for single corrective operations that are not merged
        transit_cost_1_op, maneuver_cost_1_op, standby_cost_1_op, days_tech_merged_op, rov_cost_merged_op = calculate_event_costs(
            log_df = log_o_m_o,
            ves = ves,
            duration_shift = duration_shift,
            fuel_cost_density = fuel_cost_times_density,
            rov_dict_cost=rov_cost_dict,
            oper_dict_tech=tech_per_oper_dict,
            insp_params=None,
            rov_tech_vessel_count = rov_tech_vessel_count
        )

        # Calculate for tow operations
        transit_cost_tow, maneuver_cost_tow, standby_cost_tow, days_tech_tow, rov_cost_tow = calculate_event_costs(
            log_df = log_o_t,
            ves = ves,
            duration_shift = duration_shift,
            fuel_cost_density = fuel_cost_times_density,
            rov_dict_cost=rov_cost_dict,
            oper_dict_tech=tech_per_oper_dict,
            insp_params=None,
            rov_tech_vessel_count = rov_tech_vessel_count
        )

        # Calculate for operations other costs, parts costs and daily port costs
        if not log_o.empty:
            log_o = kpi_aux.remove_row_vessel_double(df = log_o, ves = ves, rov_tech_vessel_count = rov_tech_vessel_count)
            if not log_o.empty:
                part_cost, other_cost = part_other_cost(
                    df = log_o,
                    total_operations = total_operations,
                    find_element_class = find_element_class
                )
                # Reduce the part cost that were already counted in the port operations
                log_o_cost_reduce = log_o[log_o['comments'].isin(failure_corrected_port)]
                if not log_o_cost_reduce.empty:
                    part_cost_reduce, _ = part_other_cost(
                        df = log_o_cost_reduce,
                        total_operations = total_operations,
                        find_element_class = find_element_class
                    )
                    part_cost -= part_cost_reduce

        else:
            part_cost = 0
            other_cost = 0

        rov_tech_vessel_count[ves.id] = []

        # Calculate for inspections
        transit_cost_insp, maneuver_cost_insp, standby_cost_insp, tech_net_insp, rov_insp = calculate_event_costs(
            log_df = log_i_m,
            ves = ves,
            duration_shift = duration_shift,
            fuel_cost_density = fuel_cost_times_density,
            rov_tech_vessel_count = rov_tech_vessel_count,
            insp_params={
                'operations_inspect_site': inspections_site_stat,
                'operations_inspect_port': inspections_port_stat,
                'ves': ves,
                'insp_port_data': insp_port_data,
                'duration_shift': duration_shift
            }
        )
        vessel_day_count_insp = VesselDayCounter(log_events_merged = log_i_m, vessels = vessels)
        days_vessel_insp = vessel_day_count_insp.count_day_vessel(ves_id = ves.id)

        # Calculate for mobilisations
        if not log_m_m.empty:
            mobilisation_days = log_m_m['n_vessel_1'].sum()
        else:mobilisation_days = 0

        # Transit Cost
        transit_cost = transit_cost_1 + transit_cost_1_def + transit_cost_1_op + transit_cost_insp + transit_cost_tow
        op_cost += transit_cost - transit_cost_insp
        insp_cost += transit_cost_insp

        # Maneuver Cost
        maneuver_cost = maneuver_cost_1 + maneuver_cost_1_def + maneuver_cost_1_op + maneuver_cost_insp + maneuver_cost_tow
        op_cost += maneuver_cost - maneuver_cost_insp
        insp_cost += maneuver_cost_insp

        # Standby Cost
        standby_cost = standby_cost_1 + standby_cost_1_def + standby_cost_1_op + standby_cost_insp + standby_cost_tow
        op_cost += standby_cost - standby_cost_insp
        insp_cost += standby_cost_insp

        # Charter Days
        op_cost += (charter_days - days_vessel_insp)* getattr(ves, "charter", 0)
        insp_cost += days_vessel_insp* getattr(ves, "charter", 0)

        # Charter Cost
        ST_charter_cost = charter_days_ST * getattr(ves, "charter", 0)
        LT_yearly_charter_cost = getattr(ves, "annual_contract", 0)*getattr(ves, 'n_ves_annual_contract', 0)
        LT_monthly_charter_cost = getattr(ves, 'monthly_contract_cost', 0)*getattr(ves, 'n_ves_monthly_contract', 0)*len(getattr(ves, 'months_contract', []))
        charter_cost = ST_charter_cost + (LT_yearly_charter_cost + LT_monthly_charter_cost)*years

        # Tech Cost
        tech_cost = days_tech_merged + days_tech_merged_def + days_tech_merged_op + tech_net_insp + days_tech_tow
        op_cost += tech_cost - tech_net_insp
        insp_cost += tech_net_insp

        rov_cost = rov_cost_merged + rov_cost_def + rov_cost_merged_op + rov_insp + rov_cost_tow
        op_cost += rov_cost - rov_insp
        insp_cost += rov_insp

        vessel_fuel_usage = kpi_aux.store_fuel_data(
            vessel_usage = vessel_fuel_usage,
            ves = ves,
            transit_cost = transit_cost,
            maneuver_cost = maneuver_cost,
            standby_cost = standby_cost,
            fuel_cost_times_density = fuel_cost_times_density,
        )

        vessel_cost = charter_cost+transit_cost+maneuver_cost+standby_cost

        vessel_cost_avg = averaged_res(vessel_cost,charter_days)
        tech_cost_avg = averaged_res(tech_cost,charter_days)
        part_cost_avg = averaged_res(part_cost,charter_days)
        other_cost_avg = averaged_res(other_cost,charter_days)
        rov_cost_avg = averaged_res(rov_cost,charter_days)

        kpi = pd.DataFrame([[
            ves.id,
            ves.type,
            charter_days,
            round(vessel_cost_avg, 2),
            round(charter_cost+transit_cost+maneuver_cost+standby_cost, 2),
            round(getattr(ves,"mobilisation_cost",0), 2),
            round(getattr(ves,"mobilisation_cost",0) * mobilisation_days, 2),
            round(tech_cost_avg, 2),
            round(tech_cost, 2),
            round(part_cost_avg, 2),
            round(part_cost, 2),
            round(rov_cost_avg, 2),
            round(rov_cost, 2),
            round(other_cost_avg, 2),
            round(other_cost, 2),
        ]], columns=COLS)

        kpi_om = pd.concat([kpi_om, kpi], ignore_index=True)
    
    kpi_om_type_cost = pd.DataFrame({
        'description': ['corrective', 'preventive'],
        'values': [op_cost,  insp_cost]
    })

    kpi_om = create_lifetime_cost(kpi_om)

    return kpi_om, kpi_om_type_cost, vessel_fuel_usage

if __name__ == '__main__':
    pass