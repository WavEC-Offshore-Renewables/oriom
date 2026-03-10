import random
import logging
import pandas as pd
from datetime import timedelta,datetime
import numpy as np
from copy import deepcopy


def create_mobilisation(
        df: pd.DataFrame,
        mobilisation_date: datetime,
        end_mobi: datetime,
        event: str,
        vessel: object,
        oper_list: list,
        count_fail: str = None,
        concat: bool = True
    )->pd.DataFrame:

    """
    Create mobilisation row to add to log_events_merged

    Args:
        df (:obj:`pd.DataFrame`): Is the dataframe on which the mobilisation needs to be added
        mobilisation_date (:obj:`pd.datetime`): The start date of the mobilisation.
        end_mobi (:obj:`pd.datetime`): The date on wich start effectively the operation related to the mobilisation.
            This date will be used to evaluate in KPI_FINAL_COSTS.PY to evaluate how many vessels are used while mobilise the vessel
        event (:obj:`str`): The event description.
        vessel (:obj:`class`): The vessel class that needs to be mobilitate
        oper_list (:obj:`list`): List of operations that called the mobilisation
        count_fail (:obj:`str`): The counter of the failure mobilized. Defaul to None
        concat (:obj:`bool`): Boolean to return the concatenated dataframe or the single row. Defaul to True
    Returns:
        pd.DataFrame: The dataframe with the new row added or the row itself if concat is False
    """

    if count_fail:
        if isinstance(count_fail, list):
            id_mobilisation = ['mobi_' + str(x) for x in count_fail]
        else:
            id_mobilisation = 'mobi_' + str(count_fail)
    else: id_mobilisation = None

    row_values = [
        mobilisation_date,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        end_mobi,
        None,
        event,
        id_mobilisation,
        vessel.id,
        vessel.n_vessels,
        None,
        None,
        [oper_list] if isinstance(oper_list, str) else list(oper_list),
        False,
        False,
        False
    ]

    # Manage the case of 16 columns in the dataframe (missing "shutdown", "ST_contract_1", "ST_contract_2" column in log_event that is added consecutevly)
    if len(df.columns) == len(row_values) - 3:
        row_values = row_values[:-3]

    # Create the row to add to the dataframe
    row_mob_line = pd.DataFrame([row_values], columns=df.columns)
    if concat:
        df = pd.concat([df,row_mob_line], axis=0, ignore_index=False)
        return df
    else:
        return row_mob_line


def count_failures(df):

    """
    Count the number of failure that occure and return the df with failure id counted

    Args:
        df (pd.DataFrame): is the log_event dataframe with only failure
    Return:
        pd.DataFrame: log_events of only failure with id failure counted for type
    """

    df['id'] = df['id'].astype(str) + '.' + (df.groupby('id').cumcount() + 1).astype(str)

    return df


def create_data(df, col_name, date):
    """ Create a new date adding hours to the previous date taken from a column of the dataframe"""
    try:
        time = float(round(df[col_name],2))
    except KeyError:
        time = 0
    new_date = date + timedelta(hours=time)
    return new_date



def failure_df_to_logevent_df(
    dates_failures: pd.DataFrame,
    cols: list
    )->pd.DataFrame:

    """
    Creates the DataFrame only populated with the failures.
    Use count_failures function to count the failures

    Args:
        dates_failures (:obj:`pd.DataFrame`): Dataframe of failure occurred.
        cols (:obj:`list`): List of column of log_dates_event

    Returns:
        pd.DataFrame: dataframe with all the failures.
    """

    dates_failures = dates_failures
    dates_failures = count_failures(dates_failures)

    log_dates_event = pd.DataFrame(columns=cols)

    log_dates_event['d_trigger'] = dates_failures['datetime']
    log_dates_event['event'] = 'failure'
    log_dates_event['id'] = dates_failures['id']
    log_dates_event['comments'] = dates_failures['maintenance_strategy']

    return log_dates_event


def create_stat_chart_inspection_port(df, percentile = 0.9):
    """
    Create the statistic chart for the inspection port

    Args:
        df (:obj:`pd.DataFrame`): Dataframe of log_events_merged
        df (:obj:`float`): percentile value to calculate the statistic

    Returns:
        pd.DataFrame: dataframe with all the failures.
    """
    if percentile > 1:
        percentile = percentile / 100

    # Filter only event 'inspection_port'
    df_inspection = df[df['event'] == 'inspection_port'].copy()
    # Calculate the hours duration and its percentile for each operation
    df_inspection['duration_hours'] = (df_inspection['d_end'] - df_inspection['d_trigger']).dt.total_seconds() / 3600
    p90_per_id = df_inspection.groupby('id')['duration_hours'].quantile(percentile)

    # Maps the values for each operation, add the statistic time to the dataframe and overwrite it
    df_inspection[str(percentile)] = df_inspection['id'].map(p90_per_id)
    df_inspection['d_end_stat_chart'] = df_inspection['d_trigger'] + pd.to_timedelta(df_inspection[str(percentile)], unit='h')
    df.loc[df_inspection.index, 'd_end_stat_chart'] = df_inspection['d_end_stat_chart']

    return df



def inspection_statistic_duration(oper_schedule, date_continuous, inspection):

    """
    This function calculates the P90 duration of inspection for the given date.
    It is used to avoid extreme values in the statistics.

    The P90 duration of inspection is too extreeme if considered a month that is a limit in seasonal weather change.
    This is cause if an inspection start at the end of the month
    most likely will end in the next month, and the statistics is influenced by this P90
    """

    month = date_continuous.month
    month_prev = 12 if month == 1 else month - 1
    month_next = 1 if month == 12 else month + 1

    dur_month = inspection.dur_total_dict[str(month)]
    dur_month_prev = inspection.dur_total_dict[str(month_prev)]
    dur_month_next = inspection.dur_total_dict[str(month_next)]

    if (
        dur_month/dur_month_prev > 2 or
        dur_month/dur_month_next > 2 or
        dur_month/dur_month_prev < 0.5 or
        dur_month/dur_month_next < 0.5
    ):

        df_sept = oper_schedule[oper_schedule['datetime'].dt.month == month ]
        dur_total_perc = np.nanpercentile(df_sept['dur_total'], 75, interpolation='nearest')

    else:
        dur_total_perc = dur_month

    return dur_total_perc


def shutdown_evaluation(
    log_events: pd.DataFrame,
    failures: list,
    operation_log_file_stats: list,
    inspections_port_stat: list,
    inspections_site_stat: list,
):
    """
    Add the shutdown parameter to the dataframe due to failures and operations

    Args:
        log_events (:obj:`pd.DataFrame`): Log of all the events
            (failure,operation, inspection_port, inspection_site, mobilisation).
        failures (:obj:`list`): List of objects :class:`failures`
        operation_log_file_stats (:obj:`list`): List of objectts :class:`OperationsCorrectiveStat` + `OperationsTowStat`.
        inspections_port_stat (:obj:`list`): List of object :class:`InspectionsPortStat`.
        inspections_site_stat (:obj:`list`): List of object :class:`InspectionsSiteStat`.

    Return:
        pd.DataFrame: log_events with shutdown parameters modified
    """
    log_events['shutdown'] = False

    if failures:
        # Shutdown failures
        dict_failures_shutdown = {}
        for f in failures:
            if f.potential_shutdown:
                dict_failures_shutdown[f.id.lower()] = f.perc_shutdown
        if len(dict_failures_shutdown) == 0:
            logging.warning('LogDates: with "percentage_shutdown", all failures do not lead to shutdown')

        df_failures_shutdown = log_events[log_events['event'] == 'failure']
        df_failures_shutdown['id_'] = df_failures_shutdown['id'].str.split('.').str[0].str.lower()

        df_failures_shutdown = df_failures_shutdown[
            df_failures_shutdown['id_'].isin(dict_failures_shutdown.keys())
        ]

        # Use perc shutdown for each failure
        for f_id in dict_failures_shutdown:
            perc_fail = dict_failures_shutdown[f_id]
            perc_fail_adjusted = perc_fail / 100
            df_specific_failure = df_failures_shutdown[df_failures_shutdown['id_'] == f_id]
            idxs = df_specific_failure.index.tolist()
            n = int(np.ceil(len(idxs) * (perc_fail_adjusted)))
            if n > 0:
                sample = random.sample(idxs, min(n, len(idxs)))
                log_events.loc[sample, 'shutdown'] = True

    # Shutdown operations
    op_shutdown = {}
    # Find if the operations/inspections have a shutdown and map them in a dict
    for op in operation_log_file_stats + inspections_site_stat + inspections_port_stat:
        try:
            op_shutdown[op.id] = (
                any(op.wtg_shutdown_dict.values()) or
                any(op.pv_shutdown_dict.values()) or
                any(op.wec_shutdown_dict.values())
            )
        except AttributeError:
            op_shutdown[op.id] = op.shutdown_dict

    op_shutdown = {op: v for op, v in op_shutdown.items() if v}
    # Overwrite the shutdown column in log_events
    mask = log_events['id'].isin(op_shutdown.keys())
    log_events.loc[mask, 'shutdown'] = True

    return log_events


if __name__ == "__main__":
    pass