
import logging
import pandas as pd
from datetime import timedelta

from oriom.utils import aux_functions

from oriom.core.functions.logs_timeseries import logs_timeseries_func
from oriom.core.functions.logs_timeseries import logs_preventive_aux
from oriom.core.functions.logs_timeseries.InspectionPortOrganizer import InspectionPortCreation
from oriom.core.functions.logs_timeseries.InspectionSiteOrganizer import InspectionSiteCreation

def define_dates(
    COLS: list,
    inspection,
    event: str,
    start_year: int,
    start_month: int,
    n_lifetime: int,
    percentile: int,
    find_element_class: object,
    mother_vessel_inspection_campaign: dict = {}
)->pd.DataFrame:
    
    """Auxiliary function: It defines the dates for the inspection called based on the periodicity.

    For inspection at port evaluates the tow to port, inspection at port and tow to site time
    from the respective operation_schedule file. A maximum number of device can be inspected 
    at port simultaneously and towing operation that require a specific vessel are considered
    with only one (for now) available vessel (no intersection of shifts).

    Args:
        COLS (list): List of columns of the log dataframe
        inspections (:class:`~oriom.classes.Operations.InspectionPort/Site`)
        event (:obj:`str`): String of the type of event.
        start_year (int): Year of the start of the simulation
        start_month (int): Month of the start of the simulation
        n_lifetime (int): Number of years of the lifetime of the farm
        percentile (float): Percentile of the weather window to consider for the operations
        find_element_class (object): Object from class :class:`FindElementClass`
        mother_vessel_inspection_campaign (dict): Dictionary with mother vessel_id as first key year as second key and date of end of last inspection campaign as value.
            Only inspection with vessel 2 as mother vessel that have a periodicity > 1 year will be added to this dict

    Returns:
        pd.DataFrame: dataframe with all the inspection event.
    """            
            
    df_dates_inspection = pd.DataFrame(columns=COLS)
    df_port_inspection_log = pd.DataFrame(columns=['d_trigger', 'd_TTP_start', 'd_TTP_end', 'n_device'])

    comment = event
    # Evaluation of data of the inspections analyzed
    n_device_at_port = aux_functions.safe_getattr(inspection, ['insp_class', 'n_device_at_port'])
    n_device_stored_at_port = aux_functions.safe_getattr(inspection, ['insp_class', 'n_device_stored_at_port'])
    duration_shift_main = aux_functions.safe_getattr(inspection, ['insp_class', 'duration_main'])
    days_main = aux_functions.safe_getattr(inspection, ['insp_class', 'days_main'])                                  
    days_last = aux_functions.safe_getattr(inspection, ['insp_class', 'days_last'])                                  
    
    if max(days_main,days_last) == 0:
        return df_dates_inspection
    
    if aux_functions.safe_getattr(inspection, ['insp_class', 'op_tow_port']):
        port_inspection_flag = True
    else: port_inspection_flag = False
    
    datetimes = logs_preventive_aux.start_date_inspection(
        inspection = inspection,
        start_year = start_year,
        start_month = start_month,
        n_lifetime = n_lifetime,
    )

    # This list will have all the shutdown of the towing operations
    duration_shutdown_month = {str(k):0 for k in range(1,13)}
    duration_shutdown_month_counter = {str(k):0 for k in range(1,13)}

    valid_datetimes, end_datetimes, end_stat_chart_datetimes = [], [], []

    # Find which tech is being analyzed
    shutdown_col = next(
        (v for k, v in {"owc": "dur_shutdown_wec", "ofw": "dur_shutdown_wtg", "opv": "dur_shutdown_pv"}.items()
        if k in inspection.id), None)

    for ii, d in enumerate(datetimes):
        month_insp = str(d.month)
        duration_shutdown_month_counter[month_insp] += 1

        # TODO add device store at port
        # If oper_schedule need to combine tow to port, tow to site, insp at port and consider n_device at port
        if port_inspection_flag:
            # Find n_vessel
            n_vessel = inspection.n_vessel_1 
            if n_vessel > n_device_at_port:
                n_vessel = n_device_at_port

            port_inspection = InspectionPortCreation(inspection, n_device_at_port, n_device_stored_at_port, find_element_class, shutdown_col)
            df_port_inspection_log = port_inspection.preventive_port_inspection(
                month_insp = month_insp,
                duration_shutdown_month = duration_shutdown_month,
                end_datetimes = end_datetimes,
                end_stat_chart_datetimes = end_stat_chart_datetimes,
                valid_datetimes = valid_datetimes,
                d = d,
                df_port_inspection_log = df_port_inspection_log
            )

            # save the towing log at the end of the inspection at port and assign it as attribute
            if ii == len(datetimes) - 1:
                df_port_inspection_log = aux_functions.log_event_convert_stringtime(df_port_inspection_log)
                inspection.insp_class.towing_log = df_port_inspection_log
                aux_functions.save_file_csv(df_port_inspection_log, aux_functions.safe_getattr(inspection, ['insp_class', 'insp_port_dir']), 'towing_inspection_log.csv')

            if not port_inspection.operation_completed:
                break

        # If inspection at site
        else:
            # Find n_vessel
            n_vessel = (aux_functions.safe_getattr(inspection,['insp_class', 'n_vessel_last']) 
                if days_main == 0 
                else aux_functions.safe_getattr(inspection,['insp_class', 'n_vessel_main'])
            )

            shutdown_col = None
            site_inspection = InspectionSiteCreation(inspection)
            site_inspection.preventive_site_inspection(
                mother_vessel_inspection_campaign = mother_vessel_inspection_campaign,
                find_element_class = find_element_class,
                end_datetimes = end_datetimes,
                end_stat_chart_datetimes = end_stat_chart_datetimes,
                valid_datetimes = valid_datetimes,
                d = d
            )

            if site_inspection.inspection_campaign_flag:
                comment = event + '_campaign'
            if not site_inspection.operation_completed:
                break


    
    # Create the dataframe with the results obtained
    df_dates_inspection = pd.DataFrame(columns=COLS)
    df_dates_inspection['d_trigger'] = valid_datetimes
    df_dates_inspection['d_end_wait_start'] = [None] * len(valid_datetimes)
    df_dates_inspection['d_end_dur_net_port'] = [None] * len(valid_datetimes)
    df_dates_inspection['d_end_transit_ts'] = [None] * len(valid_datetimes)
    df_dates_inspection['d_end_wait_site'] = [None] * len(valid_datetimes)
    df_dates_inspection['d_end_dur_net_site'] = [None] * len(valid_datetimes)
    df_dates_inspection['d_end_transit_tp'] = [None] * len(valid_datetimes)
    df_dates_inspection['d_end'] = end_datetimes
    df_dates_inspection['d_end_stat_chart'] = end_stat_chart_datetimes
    df_dates_inspection['event'] = [event] * len(valid_datetimes)
    df_dates_inspection['id'] = [inspection.id] * len(valid_datetimes)
    df_dates_inspection['vessel_1'] = [inspection.insp_class.vessel1_id] * len(valid_datetimes)
    df_dates_inspection['n_vessel_1'] = [n_vessel] * len(valid_datetimes)
    df_dates_inspection['vessel_2'] = [inspection.insp_class.vessel2_id] * len(valid_datetimes)
    if inspection.insp_class.vessel2_id is not None:
        df_dates_inspection['n_vessel_2'] = [1] * len(valid_datetimes)
    else:
        df_dates_inspection['n_vessel_2'] = [None] * len(valid_datetimes)              
    df_dates_inspection['comments'] = [comment] * len(valid_datetimes)

    # Create inspection statistical chart for port inspection
    df_dates_inspection = logs_timeseries_func.create_stat_chart_inspection_port(df_dates_inspection, percentile)

    # Overwrite the shutdown with the actual device shutdown duration for inspection at port only
    if port_inspection_flag:
        if shutdown_col:
            duration_shutdown_month = {k: v for k, v in duration_shutdown_month.items() if v != 0}
            duration_shutdown_month_counter = {k: v for k, v in duration_shutdown_month_counter.items() if v != 0}

            # Divide each value for the number of month evaluated in datetimes and for the number of year of lifetime
            duration_shutdown_month = {
                k: duration_shutdown_month[k] / duration_shutdown_month_counter[k]
                for k in duration_shutdown_month
            }

            inspection.shutdown_dict = {
                k: inspection.shutdown_dict[k] + duration_shutdown_month[k]
                for k in duration_shutdown_month
            }

    return df_dates_inspection


if __name__ == '__main__':
    pass