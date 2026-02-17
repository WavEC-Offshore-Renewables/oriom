import os
import pandas as pd
from copy import deepcopy
from oriom.utils import aux_functions

from oriom.core.functions.vessels_manager.VesselDayCount import VesselDayCounter
from oriom.core.functions.kpi_final.kpi_vessel_total import create_lifetime_cost, kpi_cost_vessel_internal
from oriom.core.functions.kpi_final import kpi_extra


def kpi_final_total_cost(
    log_events: pd.DataFrame,
    log_events_merged: pd.DataFrame,
    vessels: list,
    inputs: object,
    vessel_day_counter: object,
    find_element_class: object,
    operations_corr_stat: list,
    operations_tow_stat: list,
    inspections_site_stat:list,
    inspections_port_stat:list,
    fuel_cost_hfo: float,
    fuel_cost_mgo: float,
    fuel_cost_mdo: float,
    duration_shift: float,
    n_lifetime: int,
    port_cost_annual: float,
    insurance_cost_annual: float,
    technician_cost_annual: float,
    mother_vessels: list,
)->pd.DataFrame:
    
    """
    Auxiliary Function: 
    Based on the log of events it calculates the direct costs for corrective
        operations.

     Args:
        log_events (:obj:`pd.DataFrame`): Log of all the events (failure,
            operation, inspection_port, inspection_site).
        log_events_merged: (:obj:`pd.DataFrame`): Log of all the events merged (failure,
            operation, inspection_port, inspection_site).
        vessels (:obj:`list`): List of objects :class:`Vessel`
        inputs (object): object of class `Inputs` that contains all the input data from input file,
        find_element_class (Find_element_class): Initialized instance that provides fast access to operations, 
            vessels and failures via internal dictionaries.
        operations_corrective_stat (:obj:`list`): List of obejcts :class:`OperationsCorrectiveStat`.
        operations_tow_stat (:obj:`list`): List of objects :class:`OperationsTowStat`.
        inspections_site_stat(:obj:`list`): list of objects :class:`InspectionsSiteStat`
        inspections_port_stat(:obj:`list`): list of objects :class:`InspectionsTowStat`
        fuel_cost_hfo (:obj:`int`): Fuel cost €/ton.
        fuel_cost_mdo (:obj:`int`): Fuel cost €/ton.
        fuel_cost_mgo (:obj:`int`): Fuel cost €/ton.
        n_lifetime (:obj:`int`): Year lifetime of the case study
        port_cost_annual (:obj:`float`): Annual port costs.
        insurance_cost_annual (:obj:`float`): Annual insurance costs.
        technician_cost_annual (:obj:`float`): Annual technician costs.
        mother_vessels (list): list of object from class ´´Vessels´´ considered for mother vessel campaign

    Returns:
        :obj:`pd.DataFrame`: dataframe lifetime directs costs for all the operations divided by vessels . 
        :obj:`pd.DataFrame`: dataframe yearly directs costs for all the operations divided by vessels . 
    """

    def restructure_df_year(kpi_om_year_final: pd.DataFrame) -> pd.DataFrame:
        """
        Create multiIndex for yearly kpi
        """
        vessel_ids = kpi_om_year_final['vessel_id']
        data = kpi_om_year_final.drop(columns='vessel_id')

        # Create multiindex for the columns
        multi_cols = pd.MultiIndex.from_tuples(
            [(int(col.split('_')[0]), col.split('_', 1)[1]) for col in data.columns],
            names=['year', 'metric']
        )

        data.columns = multi_cols
        data = data.sort_index(axis=1, level=0)
        data.insert(0, 'vessel_id', vessel_ids)

        return data
    
    

    def consider_other_fixed_annual_cost(kpi_om, kpi_om_year_final, port_cost_annual, insurance_cost_annual, technician_cost_annual, n_lifetime):
        """
        This function adds to the cost the port, insurance, and technician costs
        """
        
        # Fixed costs for kpi_om
        df_cost = pd.Series(0, index=kpi_om.columns)
        for name, annual_cost in zip (['port', 'technician', 'insurance'],[port_cost_annual,technician_cost_annual,insurance_cost_annual]):
            df_cost['vessel_id'] = name
            df_cost['tot_other_costs'] = annual_cost * n_lifetime
            df_cost['av_other_costs'] = annual_cost

            kpi_om = pd.concat([kpi_om, df_cost.to_frame().T], ignore_index=True)

        # Fixed costs for kpi_om_year_final (yearly costs)
        fixed_row = pd.Series(0, index=kpi_om_year_final.columns)
        n_years = len([col for col in kpi_om_year_final.columns if col[1] == 'direct_costs'])
        if n_years == n_lifetime or n_years == n_lifetime+1:
            for col in kpi_om_year_final.columns:
                if col[1] == 'direct_costs':
                    fixed_row[col] = port_cost_annual + insurance_cost_annual + technician_cost_annual

        fixed_row[('vessel_id', '')] = 'fixed_annual_cost'
        kpi_om_year_final = pd.concat([kpi_om_year_final, fixed_row.to_frame().T], ignore_index=True)

        return kpi_om, kpi_om_year_final
    
    
    def filter_log_file_per_operations(log_events,log_events_merged):
        """ Function to create filtered dataframes of log events for cost evaluations"""
        log_events_op = log_events[log_events['event'].isin(['operation', 'inspection_port', 'inspection_site', 'tow'])].copy()
        log_events_op_ST = log_events_merged[log_events_merged["ST_contract_1"] | log_events_merged["ST_contract_2"]].copy()
        log_events_op_merged = log_events_merged[log_events_merged['event'] =='operation_merged'].copy()
        log_events_op_def_merged = log_events_merged[log_events_merged['event'] == 'operation_deferred_merged'].copy()
        log_events_op_merged_oper = log_events_merged[log_events_merged['event']=='operation'].copy()
        log_events_insp_merged = log_events_merged[log_events_merged['event'].isin(['inspection_site', 'inspection_port'])].copy()
        log_events_mobi_merged = log_events_merged[log_events_merged['event'].isin(['mobilisation', 'mobilisation_merged'])].copy()
        log_events_tow = log_events_merged[log_events_merged['event'].isin(['tow'])].copy()
        log_event_op_port = log_events_merged[
            (~log_events_merged['event'].str.contains('fail|mobi', na=False))
            & (log_events_merged['vessel_1'].isna())
        ]
        
        return (
            log_events_op, log_events_op_ST, log_events_op_merged, 
            log_events_op_def_merged, log_events_op_merged_oper, 
            log_events_insp_merged, log_events_mobi_merged, 
            log_events_tow, log_event_op_port
        )


    def create_total_row(df):
        tot_columns = [col for col in df.columns if 'tot' in col]
        total_row = {col: '' for col in df.columns}

        # Sum only total column
        for col in tot_columns:
            total_row[col] = df[col].sum()
        total_row['lifetime_direct_costs'] = df['lifetime_direct_costs'].sum()

        total_row['vessel_id'] = 'total'

        df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
        return df


    #____________________________SCRIPT BELOW______________________________________

    tech_per_oper_dict, rov_cost_dict, insp_port_data, dict_vess_long_term = {},{},{},{}
    ctv = None
    total_operations = operations_corr_stat + inspections_site_stat + inspections_port_stat  + operations_tow_stat
    
    log_events_merged = aux_functions.log_event_convert_stringtime(log_events_merged)
    
    # Dataframe preparations
    (log_events_op, log_events_op_ST, log_events_op_merged, 
    log_events_op_def_merged, log_events_op_merged_oper, 
    log_events_insp_merged, log_events_mobi_merged, 
    log_events_tow, log_event_op_port ) = filter_log_file_per_operations(log_events, log_events_merged)

    vessel_day_count_ST = VesselDayCounter(log_events_merged = log_events_op_ST, vessels=vessels)
    _ = vessel_day_count_ST.allocate_vessels(log_events_merged = log_events_merged, contract_evaluation = False)

    # Create boolean dictionary for vessel long term contract
    for v in vessels:
        dict_vess_long_term[v.id] = bool(getattr(v, 'n_ves_annual_contract', False))
        if v.type.lower() == 'ctv':
            ctv = v

    # Dictionaries creation with timeseries_data for inspections at port
    for inspe in inspections_port_stat:
        insp_port_data[inspe.insp_class.id] = {}

        data_insp_port = find_element_class.find_operation(inspe.insp_class.id)
        data_red_rem = find_element_class.find_operation(inspe.insp_class.op_tow_site_port)
        data_tow_port = find_element_class.find_operation(inspe.insp_class.op_tow_port)
        data_tow_site = find_element_class.find_operation(inspe.insp_class.op_tow_site)

        insp_port_data[inspe.insp_class.id][inspe.insp_class.op_tow_port] = data_tow_port
        insp_port_data[inspe.insp_class.id][inspe.insp_class.op_tow_site] = data_tow_site
        insp_port_data[inspe.insp_class.id][inspe.insp_class.op_tow_site_port] = data_red_rem
        insp_port_data[inspe.insp_class.id][inspe.insp_class.id] = data_insp_port

    for op in operations_corr_stat + operations_tow_stat:
        tech_per_oper_dict[op.id] = op.op_class.tech_required * op.op_class.tech_cost
        rov_cost_dict[op.id] = getattr(getattr(op.op_class, "rov_drone", None), "daily_charter", 0)
    
    # Total lifetime costs
    kpi_om, kpi_om_type_cost = kpi_cost_vessel_internal(
        log_events_op_orig = log_events_op,
        log_events_op_merged_orig = log_events_op_merged,
        log_events_op_def_merged_orig = log_events_op_def_merged,
        log_events_op_merged_oper_orig = log_events_op_merged_oper,
        log_events_insp_merged_orig = log_events_insp_merged,
        log_events_mobi_merged_orig = log_events_mobi_merged,
        log_events_tow_orig = log_events_tow,
        log_events_op_port_orig = log_event_op_port,
        vessel_day_count = vessel_day_counter,
        vessel_day_count_ST = vessel_day_count_ST,
        tech_per_oper_dict = tech_per_oper_dict,
        rov_cost_dict = rov_cost_dict,
        insp_port_data = insp_port_data,
        vessels = vessels,
        duration_shift = duration_shift,
        total_operations = total_operations,
        operations_tow_stat = operations_tow_stat,
        inspections_site_stat = inspections_site_stat,
        inspections_port_stat = inspections_port_stat,
        fuel_cost_hfo = fuel_cost_hfo,
        fuel_cost_mgo = fuel_cost_mgo,
        fuel_cost_mdo = fuel_cost_mdo,
        find_element_class = find_element_class,
        years = inputs.stats.lifetime["value"]
    )

    # Extract years
    log_events['year'] = log_events['d_end'].dt.year
    log_events_merged['year'] = log_events_merged['d_end'].dt.year
    years = range(inputs.stats.start_year["value"], inputs.stats.start_year["value"] + inputs.stats.lifetime["value"])
    kpi_om_year = None
    kpi_om_year_called = None

    # Loop through each year and calculate costs
    for year in years:
        log_events_year = log_events[log_events['d_end'].dt.year == year].copy()
        log_events_merged_year = log_events_merged[log_events_merged['d_end'].dt.year == year].copy()
        vessel_day_count_year = deepcopy(vessel_day_counter)
        vessel_day_count_ST_year = deepcopy(vessel_day_count_ST)

        # Filter only desired year
        vessel_day_count_year.vessels_calendar = vessel_day_count_year.vessels_calendar[
            vessel_day_count_year.vessels_calendar.index.year == year
        ]
        vessel_day_count_ST_year.vessels_calendar = vessel_day_count_ST_year.vessels_calendar[
            vessel_day_count_ST_year.vessels_calendar.index.year == year
        ]

        if not log_events_merged_year.empty:
            (log_events_op_y, log_events_op_ST, log_events_op_merged_y, 
            log_events_op_def_merged_y, log_events_op_merged_oper_y, 
            log_events_insp_merged_y, log_events_mobi_merged_y, 
            log_events_tow_y, log_event_op_port_y) = filter_log_file_per_operations(log_events_year,log_events_merged_year)

            kpi_year, kpi_om_type_cost_year = kpi_cost_vessel_internal(
                log_events_op_orig = log_events_op_y,
                log_events_op_merged_orig = log_events_op_merged_y,
                log_events_op_def_merged_orig = log_events_op_def_merged_y,
                log_events_op_merged_oper_orig = log_events_op_merged_oper_y,
                log_events_insp_merged_orig = log_events_insp_merged_y,
                log_events_mobi_merged_orig = log_events_mobi_merged_y,
                log_events_tow_orig = log_events_tow_y,
                log_events_op_port_orig = log_event_op_port_y,
                vessel_day_count = vessel_day_count_year,
                vessel_day_count_ST = vessel_day_count_ST_year,
                tech_per_oper_dict = tech_per_oper_dict,
                rov_cost_dict = rov_cost_dict,
                insp_port_data = insp_port_data,
                vessels = vessels,
                duration_shift = duration_shift,
                total_operations = total_operations,
                operations_tow_stat = operations_tow_stat,
                inspections_site_stat = inspections_site_stat,
                inspections_port_stat = inspections_port_stat,
                fuel_cost_hfo = fuel_cost_hfo,
                fuel_cost_mgo = fuel_cost_mgo,
                fuel_cost_mdo = fuel_cost_mdo,
                find_element_class = find_element_class
            )

            df_costs = kpi_year[['vessel_id', 'lifetime_direct_costs']].copy()
            df_days = kpi_year[['vessel_id', 'n_chart_days']].copy()
            
        else:
            df_costs = pd.DataFrame({
                'vessel_id': [v.id for v in vessels],
                f'{year}_direct_costs': [0 for _ in vessels]
            })

            df_days = pd.DataFrame({
                'vessel_id': [v.id for v in vessels],
                f'{year}_n_days': [0 for _ in vessels]
            })

        df_costs.columns = ['vessel_id', f'{year}_direct_costs']
        df_days.columns = ['vessel_id', f'{year}_n_days']

        if kpi_om_year is None:
            kpi_om_year = df_costs
            kpi_om_year_called = df_days
        else:
            kpi_om_year = pd.merge(kpi_om_year, df_costs, on='vessel_id', how='outer')
            kpi_om_year_called = pd.merge(kpi_om_year_called, df_days, on='vessel_id', how='outer')

    kpi_om_year_final = pd.merge(kpi_om_year, kpi_om_year_called, on='vessel_id', how='outer')
    
    kpi_om_year_final = restructure_df_year(kpi_om_year_final)

    daily_vessel = vessel_day_count_ST.vessels_calendar
    
    kpi_om, kpi_om_year_final = consider_other_fixed_annual_cost(
            kpi_om = kpi_om, 
            kpi_om_year_final = kpi_om_year_final, 
            port_cost_annual = port_cost_annual, 
            insurance_cost_annual = insurance_cost_annual, 
            technician_cost_annual = technician_cost_annual, 
            n_lifetime = n_lifetime
        )

    kpi_om = create_lifetime_cost(df = kpi_om)

    kpi_om = create_total_row(df = kpi_om)
    
    #Create dict for strategy of nº long_term_ctv
    if ctv:
        ctv_dict = kpi_extra.data_ctv_long_term_strategy(
            v = ctv, 
            log_events_merged = log_events_merged,
            n_lifetime = n_lifetime,
        )
    else:
        ctv_dict = {}

    return kpi_om, kpi_om_year_final, ctv_dict, daily_vessel, kpi_om_type_cost


if __name__ == '__main__':
    pass