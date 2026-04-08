import pandas as pd
import logging
import os

from oriom.utils import aux_functions

from oriom.core.functions.vessels_manager.VesselDayCount import VesselDayCounter
from oriom.core.functions.vessels_manager import vessel_mobilisation_manager
from oriom.core.functions.graphs import report_graphs
from oriom.core.functions.log_merge_corrective_functions.merge_corrective import create_logs_merge
from oriom.core.functions.layout_power.layout_power import energy_availability, config_energy_availability
from oriom.core.functions.kpi_final.kpi_final_costs import kpi_final_total_cost
from oriom.core.functions.logs_timeseries.failures import failures_event
from oriom.core.functions.logs_timeseries.create_logs_timeseries import create_logs_timeseries_file
from oriom.core.functions.logs_timeseries.logs_corrective_aux import manage_def_to_log_events
try:
    from oriom.core.functions.private.VesselMobilisationScheduler import VesselMobilisationScheduler
except ImportError:
    VesselMobilisationScheduler = None


def results_block(
    result_dir_r: str,
    r: int,
    inputs: object,
    Config: object,
    find_element: object,
    farm_technologies: object,
    results_dict: dict,
    failures: list,
    operations_tow_stats: list,
    inspections_port_stats: list,
    inspections_site_stats: list,
    operations_corrective_stats: list,
    vessels: list,
    mother_vessels: list,
    G_layouts: dict,
    dict_power_wind: dict,
    dict_power_wave: dict,
    metocean_timeseries: pd.DataFrame
):

    """
    Create for each iteration failures, log_events and KPIs

    Is the creation of a simulation block that includes:
        - Failure scenario
        - Log events creation
        - Log events merge
        - Energy availability calculation
        - KPI calculation
        - Report graphs creation

    Args:
        result_dir_r (str): string of the folder on which the results are stored,
        r (int): number of the simulation,
        inputs (object): object of class `Inputs` that contains all the input data from input file,
        Config (object): object of class `ConfigRun` that contains all the configuration data from config file,
        find_element (Find_Element): Initialized instance that provides fast access to operations,
            vessels and failures via internal dictionaries.
        farm_technologies (object): object of class `FarmTechnologies`
            that contains all the technologies data from input file,
        results_dict (object): Object of class `Results`
        failures (:obj: `list`): List of object for class `Failures`
        operations_tow_stats (:obj: `list`): List of object for class `OperationTowStat`
            with Pmain and pmax for towing operations,
        inspections_port_stats (:obj: `list`): List of object for class `InspectionPortStat`
            with Pmain and pmax stats for port inspections operations,
        inspections_site_stats (:obj: `list`): List of object for class `InspectionSiteStat`
            with Pmain and pmax stats for inspections site operations,
        operations_corrective_stats (:obj: `list`): List of object for class `Corrective_Stats`
            with Pmain and pmax stats for port inspections operations,
        vessels (:obj: `list`): List of object with attribute `id` for class `Vessels`
        mother_vessels (:obj: `list`): List with the id of the mother vessels
        G_layouts (dict): dictionary with the graph of the layouts for wind, wave and pv
        dict_power_wind (dict): dictionary with the average hourly power production [kW of wind farm
        dict_power_wave (dict): dictionary with the average hourly power production [kW] of wave farm
        metocean_timeseries (pd.DataFrame): Timeseries dataframe with power column
        """

    dates_failures_OLD = pd.DataFrame ()

    try:
        failure_dir = os.path.join(inputs.general.failureevent_file["value"], f"{'result_'}{r}", 'dates_failures.csv')
        dates_failures = pd.read_csv(failure_dir, sep=',')
        dates_failures = aux_functions.convert_stringtime(dates_failures)
        dates_failures['preferred_month'] = pd.to_numeric(
            dates_failures['preferred_month'], errors='coerce'
        ).astype('Int64')
        logging.info('Uploading Failure file from previous run %d folder', r)
        aux_functions.save_file_csv(dates_failures, result_dir_r,'dates_failures.csv')

    except (TypeError, FileNotFoundError):
        logging.info(f'Creating a failure scenario for run {r}')
        dates_failures = failures_event(
            s = inputs.tseries.failure_scenario["value"],
            scenarios = inputs.tseries.scenario,
            failures = failures,
            N_LIFETIME = inputs.stats.lifetime["value"],
            START_YEAR = inputs.stats.start_year["value"],
            START_MONTH = inputs.stats.start_month["value"],
            infant_mortality = inputs.stats.period_infant_mortality["value"],
            wear_out = inputs.stats.period_wear_out["value"],
            fail_ratio = inputs.stats.failure_ratio["value"],
            fixed_seed = False,
            dates_failures_OLD = dates_failures_OLD,
        )

        aux_functions.save_file_csv(dates_failures, result_dir_r,'dates_failures.csv')


    # Creating logs directly in the main.py file
    logging.info('--------------------\tLog events and kpis\t----------------')

    try:
        log_events_dir = os.path.join(inputs.general.logevents_file["value"], f"{'result_'}{r}", 'log_events.csv')
        log_events = pd.read_csv(log_events_dir, sep=',')
        logging.info('Uploading Log events csv file file from previous folder')

    except (TypeError, FileNotFoundError) as e_:
        log_events = create_logs_timeseries_file(
            inputs = inputs,
            dates_failures = dates_failures,
            failures = failures,
            operation_log_file_stats = operations_corrective_stats['pmax'],
            inspections_port_stat = inspections_port_stats['pmain'],
            inspections_site_stat = inspections_site_stats['pmain'],
            time_fail_op_immediately = Config.TIME_FAIL_OP_IMMEDIATELY,
            vessels = vessels,
            find_element_class = find_element,
            vessel_to_merge = inputs.tseries.merge_vessel["value"],
            mother_vessels_list = mother_vessels
        )
    if log_events.empty:
        raise Exception("Result Block: The log_events dataframe is empty. No operation have been created")

    aux_functions.save_file_csv(log_events, result_dir_r, 'log_events.csv')
    log_events = aux_functions.log_event_convert_stringtime(log_events)

    try:
        log_events_dir_merged = os.path.join(inputs.general.logevents_file["value"], f"{'result_'}{r}", 'log_events_merged.csv')
        log_events_merged = pd.read_csv(log_events_dir_merged, sep=',')
        logging.info('Uploading Log events merged file from previous folder')
        log_events_merged = aux_functions.log_event_convert_stringtime(log_events_merged)
        # Find the Short Term Vessel used and create usage_record and find ST_contract vessel
        vessel_day_count = VesselDayCounter(log_events_merged = log_events_merged, vessels=vessels)
        log_events_merged = vessel_day_count.allocate_vessels(log_events_merged = log_events_merged, ST = True)

    except (TypeError, FileNotFoundError) as e_:
        log_events_merged, index_overwrite_log_ev, df_port_operation_def_log = create_logs_merge(
            log_events_original = log_events,
            failures = failures,
            operation_log_file_stats = operations_tow_stats['pmax'] + operations_corrective_stats['pmax'],
            result_dir_r=result_dir_r,
            vessels = vessels,
            find_element_class = find_element,
            time_between_devices = inputs.tseries.time_between_devices_dict,
            percentile = inputs.stats.percentile_max["value"],
            vessel_to_merge = inputs.tseries.merge_vessel["value"],
            time_fail_op_immediately = Config.TIME_FAIL_OP_IMMEDIATELY,
            duration_shift = inputs.tseries.shift_duration["value"],
        )

        if index_overwrite_log_ev:
            log_events = manage_def_to_log_events(
                log_events = log_events,
                log_def_tow = df_port_operation_def_log,
                list_idx_remove = index_overwrite_log_ev,
                result_dir_r = result_dir_r
            )

        # Find the Short Term Vessel used and create usage_record and find ST_contract vessel
        vessel_day_count = VesselDayCounter(log_events_merged = log_events_merged, vessels=vessels)
        log_events_merged = vessel_day_count.allocate_vessels(log_events_merged = log_events_merged, ST = True)

        log_events_merged = aux_functions.log_event_convert_stringtime(log_events_merged)

        log_events_merged = vessel_mobilisation_manager.create_yearly_mobilisation_mother_vessel(
                log_events_merged = log_events_merged,
                mother_vessel_list = mother_vessels,
            )

        log_events_merged = vessel_mobilisation_manager.reduce_redundant_mobilisations_inspection(
                log_events_merged = log_events_merged,
                vessels = vessels
            )

        if Config.STATISTICAL_CHART and VesselMobilisationScheduler is not None:
            # Consider statistical charting contract time
            vessel_analyser = VesselMobilisationScheduler()

            log_events_merged = vessel_analyser.charts_manager(
                    log_events_merged = log_events_merged,
                    vessels = vessels,
                    find_element = find_element
                )

            # Recreate the usage_record considering the reused vessels
            vessel_day_count = VesselDayCounter(log_events_merged = log_events_merged, vessels=vessels)
            _ = vessel_day_count.allocate_vessels(log_events_merged = log_events_merged)

        else:
            log_events_merged['d_end_stat_chart'] = log_events_merged['d_end']
            log_events_merged['d_end_stat_chart_orig'] = log_events_merged['d_end_stat_chart']
            log_events_merged['n_vessel_1_effective'] = log_events_merged['n_vessel_1']

    aux_functions.save_file_csv(log_events_merged,result_dir_r,'log_events_merged.csv')


    logging.info('----------------------------------------------------')
    logging.info('----------------------------------------------------')
    logging.info('--------------------\tGraphs and power availability\t----------------')
    graph_dir_r = os.path.join(result_dir_r,'graph_dir')
    os.makedirs(graph_dir_r)

    if Config.ENERGY_AVAILABILITY_CALCULATION:
        energy_config = config_energy_availability(G_layouts, farm_technologies)

        availability_total = energy_availability(
            log_events_energy = log_events,
            operations_corrective_stat = operations_corrective_stats["pmain"],
            inspections_site_stat = inspections_site_stats["pmain"],
            inspections_port_stat = inspections_port_stats["pmain"],
            start_year = inputs.stats.start_year["value"],
            start_month = inputs.stats.start_month["value"],
            n_lifetime = inputs.stats.lifetime["value"],
            find_element_class = find_element,
            power_wind = dict_power_wind,
            power_wave = dict_power_wave,
            power_pv = farm_technologies.power.pv_farm_prod,
            degradation_rate = farm_technologies.power.degradation_rate,
            n_device_wtg = farm_technologies.power.wtg_number_devices,
            n_device_wec = farm_technologies.power.wec_number_devices,
            n_device_pv = farm_technologies.power.pv_number_devices,
            G_wind = energy_config['G_wind_copy'],
            G_wave = energy_config['G_wave_copy'],
            G_pv = energy_config['G_pv_copy'],
            n_strings_per_inv = energy_config['n_strings_per_inv'],
            n_modules_per_strings = energy_config['n_modules_per_strings'],
            max_failure_module = energy_config['max_failure_module'],
            metocean_timeseries = metocean_timeseries,
            ENERGY_STATISTICAL_CALCULATION = Config.ENERGY_STATISTICAL_CALCULATION,
            result_dir_r = result_dir_r
        )

        log_events = log_events[log_events['event'] != 'recommissioning']
        log_events_merged = log_events_merged[log_events_merged['event'] != 'recommissioning']

        combined = {}
        for k in availability_total.keys():
            if availability_total[k].empty is False:
                df = availability_total[k]
                name = k
                aux_functions.save_file_csv(df,result_dir_r,name +'.csv')

                if 'month' in name:
                    results_dict.dfs_energy_yearly_month_dict[k].append(df)
                    combined.update({k:df})
                    report_graphs.energy_yield(df = df, name_file = name[18:], save_dir = graph_dir_r)

                elif 'year' in name:
                    results_dict.dfs_energy_yearly_dict[k].append(df)
                    if 'pv' in k:
                        electricity_cost_tech = inputs.cost.electricity_price_dict['pv']
                    elif 'wind' in k:
                        electricity_cost_tech = inputs.cost.electricity_price_dict['wt']
                    elif 'wave' in k:
                        electricity_cost_tech = inputs.cost.electricity_price_dict['wec']
                    report_graphs.farm_availability(df = df, name_file = name[17:], save_dir = graph_dir_r)
                    report_graphs.indirect_costs_per_year(df = df, electricity_price = electricity_cost_tech, name_file = name[17:], save_dir = graph_dir_r)

        if len(combined.keys())>1:
            report_graphs.energy_yield_combined(dfs = combined, save_dir = graph_dir_r)

    logging.info('----------------------------------------------------')
    logging.info('----------------------------------------------------')
    logging.info('--------------------\tKPIs\t----------------')

    kpi_total_timeseries, kpi_yearly_timeseries, ctv_dict, daily_vessel, kpi_om_type_cost = kpi_final_total_cost(
        log_events=log_events,
        log_events_merged=log_events_merged,
        vessels=vessels,
        inputs = inputs,
        vessel_day_counter = vessel_day_count,
        find_element_class=find_element,
        operations_corr_stat=operations_corrective_stats['pmain'],
        operations_tow_stat=operations_tow_stats['pmain'],
        inspections_site_stat=inspections_site_stats['pmain'],
        inspections_port_stat=inspections_port_stats['pmain'],
        fuel_cost_hfo=inputs.cost.fuel_cost_hfo["value"],
        fuel_cost_mgo=inputs.cost.fuel_cost_mgo["value"],
        fuel_cost_mdo=inputs.cost.fuel_cost_mdo["value"],
        duration_shift = inputs.tseries.shift_duration["value"],
        n_lifetime=inputs.stats.lifetime["value"],
        port_cost_annual=inputs.cost.port_cost_year["value"],
        insurance_cost_annual=inputs.cost.insurance_cost_year["value"],
        technician_cost_annual=inputs.cost.technicians_year["value"],
        mother_vessels = mother_vessels,
    )

    aux_functions.save_file_csv(kpi_total_timeseries,result_dir_r,'kpi_total_final.csv')
    aux_functions.save_file_csv(kpi_yearly_timeseries,result_dir_r,'kpi_yearly_final.csv')
    aux_functions.save_file_csv(daily_vessel,result_dir_r,'daily_vessel_ST.csv', indexing = True)

    if ctv_dict:
        ctv_df = pd.DataFrame.from_dict(ctv_dict, orient='index')
        aux_functions.save_file_csv(ctv_df,result_dir_r,'ctv_df.csv', True)
        results_dict.dfs_ctv_list.append(ctv_df)

    # total cost
    results_dict.dfs_tot_cost_list.append(kpi_total_timeseries)
    results_dict.dfs_tot_yearly_cost_list.append(kpi_yearly_timeseries)
    results_dict.kpi_om_type_cost_list.append(kpi_om_type_cost)
    results_dict.dfs_log_events.append(log_events)
    results_dict.dfs_log_events_merged.append(log_events_merged)

    logging.info('----------------------------------------------------')
    logging.info('----------------------------------------------------')
    logging.info('--------------------\tReport Graphs\t----------------')

    if not dates_failures.empty:
        report_graphs.distribution_failures(df = dates_failures, save_dir = graph_dir_r)


if __name__ == '__main__':
    pass
