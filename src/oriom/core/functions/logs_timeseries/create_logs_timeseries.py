import pandas as pd
import numpy as np

from oriom.core.functions.logs_timeseries import logs_timeseries_func
from oriom.core.functions.logs_timeseries import create_logs_events_preventive
from oriom.core.functions.logs_timeseries import create_logs_events_corrective
from oriom.core.functions.vessels_manager.VesselChartInspCampaign import Stat_chart_inspection_campaign
from oriom.common.constants import DICT_DAYS



COLS =  [
    'd_trigger',
    'd_end_leadtime',
    'd_end_wait_start',
    'd_end_dur_net_port',
    'd_end_transit_ts',
    'd_end_wait_site',
    'd_end_dur_net_site',
    'd_end_transit_tp',
    'd_end',
    'd_end_stat_chart',
    'event',
    'id',
    'vessel_1',
    'n_vessel_1',
    'vessel_2',
    'n_vessel_2',
    'comments'
]


def create_logs_timeseries_file(
        inputs: object,
        dates_failures: pd.DataFrame,
        failures: list,
        operation_log_file_stats: list,
        inspections_port_stat: list,
        inspections_site_stat: list,
        time_fail_op_immediately: float,
        vessels: list,
        find_element_class,
        vessel_to_merge: list=None,
        mother_vessels_list: list = []
)->pd.DataFrame:
    """Based on the dates of the failures and the periodicity of the
    inspections a dataframe is created logging all the events. This is done using the timeseries analysis

    Note:
        For each corrective operation event the following dates are defined based on the operation_scheduler.loc[d_trigger]:
            - date trigger
            - date end leadtime: d_trigger + leadtime (procurement for component)/vessel mobilisation
            - date end waiting on weather: d_end_leadtime + operation_scheduler[wait_start] (hours)
            - date end wait at port: d_wait_start + operation_scheduler[dur_wait_port] (hours)
            - date end transit to site: d_end_dur_net_port + operation_scheduler[transit_to_site] (hours)
            - date end waiting on weather at site: d_end_transit_ts + operation_scheduler[wait_site] (hours)
            - date end net work at site: d_end_wait_site + operation_scheduler[dur_net_site] (hours)
            - date end trasit to port: d_end_dur_net_site + operation_scheduler[transit_to_port] (hours)
            - date end: d_end_transit_tp + operation_scheduler[dur_net_port] (hours)
            - date end statistical chart: date end leadtime + operation_statistic[wait_start] (hours)

        Failure event only have the trigger date representing the time of occurrence.
        Inspections only have the trigger date and end date since the statistical analysis returns an overall duration.
        Vessel mobilisation is also logged defined by the trigger date in which the mobilisation starts.
        The shutdown of a component is set True base on the % probability of its shutdown


    Args:
        inputs (object): Object from class `Inputs` that contains all the inputs of the simulation
        dates_failures (pd.DataFrame): Log of all the dates_failures
        failures (list): List of object :class:`Failures`.
        operation_log_file_stats (list): List of objectts :class:`OperationsCorrectiveStat` + `OperationsTowStat`.
        inspections_port_stat (list): List of object :class:`InspectionsPortStat`.
        inspections_site_stat (list): List of object :class:`InspectionsSiteStat`.
        time_fail_op_immediately (float): Time between failure and immediate operations.
        vessels (list): List of objectts :class:`Vessel`
        find_element_class (Find_element_class): Initialized instance that provides fast access to operations, vessels and failures via internal dictionaries.
        vessel_to_merge (:obj;`list`): list of vessel that are considered for the merge. Default to None
        percentile (:obj:`float`, *optional*): Percentile value to calculate the statistic for inspection_port. Default to 0.9

    Raises:
        ValueError: "preferred_months" in a inspection of periodicity lower than 1 year
            should be at least as many times as the occurences per year.

    Returns:
        pd.DataFrame: dataframe with all the events of the farm.

    """
    if vessel_to_merge == None:
        vessel_to_merge = []

    end_year = inputs.stats.start_year["value"] + inputs.stats.lifetime["value"]

    if inputs.stats.start_month["value"] == 1:
        end_month = 12
        end_year -=1
    else:
        end_month = inputs.stats.start_month["value"] - 1

    # NOTE: Avoid to consider event and failure on the last month for maintenance
    CUTOFF_DATE = pd.to_datetime(f"{end_year}-{end_month}-{DICT_DAYS[end_month]} 23:59:59")

    log_corrective = create_logs_events_corrective.create_logs_corrective_file(
        COLS = COLS,
        CUTOFF_DATE = CUTOFF_DATE,
        dates_failures=dates_failures,
        operation_log_file_stats = operation_log_file_stats,
        time_fail_op_immediately_original=time_fail_op_immediately,
        vessel_to_merge = vessel_to_merge,
        find_element_class = find_element_class,
    )

    log_preventive = create_logs_events_preventive.create_logs_preventive(
        COLS = COLS,
        inputs = inputs,
        inspections_port_stat = inspections_port_stat,
        inspections_site_stat = inspections_site_stat,
        find_element_class = find_element_class,
        percentile = inputs.stats.percentile_max["value"],
        mother_vessels_list = mother_vessels_list
    )

    if not log_preventive.empty:
        inspection_campaign_stat = Stat_chart_inspection_campaign(inspections_site_stat = inspections_site_stat)
        log_preventive = inspection_campaign_stat.create_stat_chart_inspection_campaign(
            df = log_preventive,
            vessels = vessels,
            percentile = inputs.stats.percentile_max["value"]
        )

    log_events = pd.concat([log_corrective,log_preventive], axis=0, ignore_index=True)

    log_events = logs_timeseries_func.shutdown_evaluation(
        log_events = log_events,
        failures = failures,
        operation_log_file_stats = operation_log_file_stats,
        inspections_port_stat = inspections_port_stat,
        inspections_site_stat = inspections_site_stat,
    )

    log_events = log_events[log_events['d_trigger'] < CUTOFF_DATE]

    log_events = log_events.sort_values(by='d_trigger').reset_index(drop=True)

    return log_events


if __name__ == '__main__':
    pass    