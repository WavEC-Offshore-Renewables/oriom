import math
import random
import logging
from copy import deepcopy
from datetime import timedelta, datetime
import pandas as pd

from oriom.utils.aux_functions import safe_getattr
from oriom.core.functions.logs_timeseries import logs_timeseries_func
from oriom.core.functions.logs_timeseries.BaseCorrection import CorrectionImmediate, CorrectionDeferred, CorrectionTowPort, CorrectionTowSite


def _map_failure_indices(failure_df: pd.DataFrame, oper_sched: pd.DataFrame) -> pd.Series:
    """Map failure datetimes to schedule indices using a dict for O(1) lookups."""
    idx_map = {dt: i for i, dt in enumerate(oper_sched['datetime'].tolist())}
    return failure_df['datetime'].map(idx_map)


def compute_operation_datetimes(df_filtered_start, oper_stat):
    """
    Calculate dates of the various phases of an operations.

    Args:
        df_filtered_start (pd.DataFrame): DataFrame with temporal data of operation.
        oper_stat (object): objects :class:`OperationsCorrectiveStat`

    Returns:
        dict: Dict with all dates.
    """
    date_end_leadtime = df_filtered_start.iat[0]

    date_end_wait_start = logs_timeseries_func.create_data(df_filtered_start, 'wait_start', date_end_leadtime)
    date_end_dur_net_work_port = logs_timeseries_func.create_data(df_filtered_start, 'dur_net_port', date_end_wait_start)
    date_end_dur_net_port = logs_timeseries_func.create_data(df_filtered_start, 'wait_port', date_end_dur_net_work_port)
    date_end_transit_ts = logs_timeseries_func.create_data(df_filtered_start, 'transit_to_site', date_end_dur_net_port)
    date_end_wait_site = logs_timeseries_func.create_data(df_filtered_start, 'wait_site', date_end_transit_ts)
    date_end_dur_net_site = logs_timeseries_func.create_data(df_filtered_start, 'dur_net_site', date_end_wait_site)
    date_end_transit_tp = logs_timeseries_func.create_data(df_filtered_start, 'transit_to_port', date_end_dur_net_site)
    date_end_stat_chart = date_end_leadtime + timedelta(hours=oper_stat.dur_total_dict[str(date_end_leadtime.month)])
    date_end = date_end_transit_tp

    dur_tot_tow = df_filtered_start['dur_total']

    return {
        'date_end_leadtime': date_end_leadtime,
        'date_end_wait_start': date_end_wait_start,
        'date_end_dur_net_port': date_end_dur_net_port,
        'date_end_transit_ts': date_end_transit_ts,
        'date_end_wait_site': date_end_wait_site,
        'date_end_dur_net_site': date_end_dur_net_site,
        'date_end_transit_tp': date_end_transit_tp,
        'date_end': date_end,
        'date_end_stat_chart': date_end_stat_chart,
        'dur_total': dur_tot_tow
    }


def _check_index_row_validity(
            idx_end_leadtime:int,
            last_valid_idx: int,
            row: pd.Series,
            oper_sched: pd.DataFrame
    ):
        """ Check first if index leadtime and df_filtered are valid"""

        # Check if the opeartion can be conducted before the end of lifetime of the farm
        if idx_end_leadtime > last_valid_idx:
            try:
                date_failed = oper_sched.iat[idx_end_leadtime,0]
            except IndexError:
                date_failed = {'idx': idx_end_leadtime}
            logging.warning(f"Log_dates: Shift not available for {row['id']} at date {date_failed}, failure remain uncorrected")
            return pd.DataFrame()

        df_filtered_start = oper_sched.iloc[idx_end_leadtime]

        # Check if exist any NaN value on the oper_schedule file filtered
        if df_filtered_start.iloc[1:-4].isna().any().any():
            raise ValueError(f"Log_dates: NaN row in oper_schedul {row['id']} at index {idx_end_leadtime}, last valid index: {last_valid_idx}")

        return df_filtered_start


def _take_vessel_data(find_element_class, op):
    """ Take vessel data """
    vessel = op.vessel1
    mob_time = math.ceil(getattr(vessel, 'mobilisation_time', 0))
    ves_2 = None
    if op.vessel2_id:
        ves_2 = op.vessel2_qt

    return vessel, ves_2, mob_time


def create_logs_corrective_file(
        COLS: list,
        CUTOFF_DATE: datetime,
        dates_failures: pd.DataFrame,
        operation_log_file_stats: list,
        time_fail_op_immediately: float,
        vessel_to_merge: list,
        find_element_class: object,
)->pd.DataFrame:
    """Based on the dates of the failures and the periodicity of the
    inspections a dataframe is created logging all the events.

    Note:
        For each corrective operation event the following dates are defined based on the operation schedule of the operation:
            - date trigger
            - date end leadtime: d_trigger + leadtime (procurement for component)/vessel mobilisation
            - date end waiting on weather: d_end_leadtime + wait_start (hours)
            - date end wait at port: d_wait_start + dur_wait_port (hours)
            - date end transit to site: d_end_dur_net_port + transit_to_site (hours)
            - date end waiting on weather at site: d_end_transit_ts + wait_site (hours)
            - date end net work at site: d_end_wait_site + dur_net_site (hours)
            - date end trasit to port: d_end_dur_net_site + transit_to_port (hours)
            - date end: d_end_transit_tp + dur_net_port (hours)

        Failure event only have the trigger date representing the time of occurrence.
        Vessel mobilisation is also logged defined by the trigger date in which the mobilisation starts.

    Args:
        COLS (list): List of columns of the log dataframe
        CUTOFF_DATE (datetime): last date of possible creation for log corrective on last month
        dates_failures (:obj:`pd.DataFrame`): Log of all the events (failure,
            operation, inspection_port, inspection_site).
        operation_log_file_stats (:obj:`list`): List of objects :class:`OperationsCorrectiveStat`.
        time_fail_op_immediately (:obj:`float`): Time between failure and
            immediate operations.
        vessel_to_merge (list): List of vessel that op can be merged when is possible to merge operations
        find_element_class (object): Object from class :class:`FindElementClass`

    Raises:
        ValueError: "preferred_months" in a inspection of periodicity lower than 1 year
            should be at least as many times as the occurences per year.
        FileNotFoundError: LogDates: "oper.ts_data" or "oper.ts_data.oper_sched" is missing for operation
        KeyError: Maintenance strategy not found: "failure.maintenance_strategy")
    Returns:
        pd.DataFrame: dataframe with all the events of the farm.
    """

    log_events = pd.DataFrame(columns=COLS)
    if dates_failures.empty:
        return log_events

    # creations of failures line for log events
    log_events = logs_timeseries_func.failure_df_to_logevent_df(dates_failures = dates_failures, cols = COLS)

    # Consider only repairable failures and no consider last month of operation
    dates_failures = dates_failures[dates_failures['maintenance_strategy'] != 'never repair']
    dates_failures = dates_failures[dates_failures['datetime'] < CUTOFF_DATE]

    ### EVALUATE FOR EACH OPERATION ###
    # creation of operations line, it is made for each failure in failure_events file
    for oper_stat in operation_log_file_stats:
        oper = oper_stat.op_class
        tow_op_flag = False
        row_mob_line=None

        # TAKE TOW DATA
        if getattr(oper, 'tow_to_port', None):
            tow_op_flag = True
            tow_op_port = find_element_class.find_operation(getattr(oper, 'op_tow_port'))
            tow_op_site = find_element_class.find_operation(getattr(oper, 'op_tow_site'))
            tow_op_port_stat = find_element_class.find_operation_stats_pmax(tow_op_port.id)
            tow_op_site_stat = find_element_class.find_operation_stats_pmax(tow_op_site.id)
            tow_port_op_oper_sched = safe_getattr(tow_op_port, ['ts_data','oper_sched'])
            tow_site_oper_sched = safe_getattr(tow_op_site, ['ts_data','oper_sched'])
            last_valid_idx_tow_port = safe_getattr(tow_op_port, ['ts_data','last_valid_index'])
            last_valid_idx_tow_site = safe_getattr(tow_op_site, ['ts_data','last_valid_index'])

        #take operation_schedule file
        oper_sched = safe_getattr(oper, ['ts_data','oper_sched'])
        last_valid_idx = safe_getattr(oper, ['ts_data','last_valid_index'])

        if oper_sched is None:
            raise FileNotFoundError(f'LogDates: oper.ts_data or oper.ts_data.oper_sched is missing for operation {oper.id}')

        #Filter the failure_event file for each operation corrispondent
        failure_filter = deepcopy(dates_failures)
        failure_filter = failure_filter[failure_filter['operation_triggered'] == oper.id.lower()]

        if failure_filter.empty:
            continue

        failure_filter['matching_indices'] = _map_failure_indices(failure_filter, oper_sched)

        ### FOR EACH FAILURE ###
        for _, row in failure_filter.iterrows():
            row_tow_port = None
            row_tow_site = None
            row_dates = pd.DataFrame(columns=COLS)
            failure = find_element_class.find_failure_from_id(row['id'].split('.')[0])
            date_failure = row['datetime']
            operation_trig = row['operation_triggered']
            fail_index = row['matching_indices']

            ves_1 = oper.vessel1_qt
            component_lead_time = failure.lead_time

            #------------------------
            # TOWING PORT CREATION
            #------------------------
            if tow_op_flag:
                vessel, ves_2, mob_time = _take_vessel_data(find_element_class = find_element_class, op = tow_op_port)

                towing_port = CorrectionTowPort(
                    date_failure = date_failure,
                    vessel = vessel,
                    oper = tow_op_port,
                    failure = failure,
                    time_fail_op_immediately = time_fail_op_immediately
                )

                # Evaluate differently for deferred and immediate towing
                if not towing_port.tow_deferred:
                    if mob_time != 0:
                        row_mob_line = towing_port.mobilitate_vessel(log_events = log_events, row = row)

                    towing_port.add_hours_for_noon_shift(
                            fail_index = fail_index,
                            lead_mob_time = mob_time,
                            oper_sched = tow_port_op_oper_sched,
                        )
                else:
                    # mobilisation in deferred_merged
                    towing_port.leadtime_evaluation(lead_mob_time = mob_time)
                    index_found = towing_port.check_leadtime_index(oper_sched = tow_port_op_oper_sched, CUTOFF_DATE = CUTOFF_DATE)
                    if not index_found:
                        continue

                # Create row_tow with data
                date_op = towing_port.date_op

                df_filtered_start_tow = _check_index_row_validity(
                    idx_end_leadtime = towing_port.idx_end_leadtime,
                    last_valid_idx= last_valid_idx_tow_port,
                    row = row,
                    oper_sched = tow_port_op_oper_sched
                )

                if df_filtered_start_tow.empty:
                    continue

                dates_tow_port = compute_operation_datetimes(df_filtered_start_tow, tow_op_port_stat)
                date_end_wait_start = dates_tow_port['date_end_wait_start']
                row_tow_port = pd.DataFrame([[
                    date_op,
                    dates_tow_port['date_end_leadtime'],
                    dates_tow_port['date_end_wait_start'],
                    dates_tow_port['date_end_dur_net_port'],
                    dates_tow_port['date_end_transit_ts'],
                    dates_tow_port['date_end_wait_site'],
                    dates_tow_port['date_end_dur_net_site'],
                    dates_tow_port['date_end_transit_tp'],
                    dates_tow_port['date_end'],
                    dates_tow_port['date_end_stat_chart'],
                    'tow',
                    tow_op_port.id,
                    vessel.id,
                    tow_op_port.vessel1_qt,
                    tow_op_port.vessel2_id,
                    tow_op_port.vessel2_qt,
                    'tow_' + row['id']
                ]],columns=COLS)

                # Check if tow ends before lead_time_compontent
                diff = (dates_tow_port['date_end'] - (date_failure + timedelta(hours=time_fail_op_immediately))).total_seconds() / 3600
                lead_mob_time_tow = int(max(component_lead_time - diff, 0))

                # Sledge all the dates for the operation start at port to end of tow
                date_failure = dates_tow_port['date_end'] + timedelta(hours=lead_mob_time_tow)
                # Find index of end_tow
                fail_index = towing_port.idx_end_leadtime + int(dates_tow_port['dur_total'])
                mob_time = 0
                lead_mob_time = lead_mob_time_tow
                vessel1_id, vessel2_id, ves_1, ves_2 = None, None, None, None


            #------------------------
            # SITE CREATION
            #------------------------
            else:
                # find the data needed for such operation
                vessel, ves_2, mob_time = _take_vessel_data(find_element_class = find_element_class, op = oper)
                lead_mob_time = math.ceil(max(mob_time,component_lead_time))
                vessel1_id = oper.vessel1_id
                vessel2_id = oper.vessel2_id

            #------------------------
            # OPERATION CREATION
            #------------------------
            if operation_trig is not None:
                # Find the start of the vessel use
                if failure.maintenance_strategy == 'immediately':
                    immediate_correction = CorrectionImmediate(
                        date_failure = date_failure,
                        vessel = vessel,
                        oper = oper,
                        time_fail_op_immediately = time_fail_op_immediately,
                        tow_op = tow_op_flag
                    )
                    # No mobilisation for operations with vessel to merge as considered in merge_funct
                    if mob_time != 0 and vessel.type not in vessel_to_merge:            # NOTE Mobilisation of merging vessel is considered in create_logs_merge
                        row_mob_line = immediate_correction.mobilitate_vessel(log_events = log_events, row = row)
                    # Row at operation schedule with idx at 5 AM
                    immediate_correction.add_hours_for_noon_shift(
                        fail_index = fail_index,
                        lead_mob_time = lead_mob_time,
                        oper_sched = oper_sched,
                    )
                    date_op = immediate_correction.date_op
                    idx_end_leadtime = immediate_correction.idx_end_leadtime

                elif failure.maintenance_strategy == 'specific month':
                    deferred_correction = CorrectionDeferred(
                        date_failure = date_failure,
                        vessel = vessel,
                        oper = oper,
                        preferred_month = failure.preferred_month,
                        tow_op = tow_op_flag
                    )

                    # Evaluate end of leadtime date
                    if not tow_op_flag:
                        deferred_correction.leadtime_evaluation(lead_mob_time = lead_mob_time)
                    else:
                        deferred_correction.add_leadtime_tow(
                            lead_mob_time = lead_mob_time,
                        )

                    index_found = deferred_correction.check_leadtime_index(oper_sched = oper_sched, CUTOFF_DATE = CUTOFF_DATE)
                    if not index_found:
                        continue
                    date_op = deferred_correction.date_op
                    idx_end_leadtime = deferred_correction.idx_end_leadtime
                else:
                    raise KeyError(f'Maintenance strategy not found: {failure.maintenance_strategy}')
            else:
                logging.error(f"LogDates: Operation trigger not found for failure {row['id']}")
                raise KeyError

            df_filtered_start = _check_index_row_validity(
                idx_end_leadtime = idx_end_leadtime,
                last_valid_idx= last_valid_idx,
                row = row,
                oper_sched = oper_sched
            )

            if df_filtered_start.empty:
                continue

            dates_op = compute_operation_datetimes(df_filtered_start, oper_stat)

            if not tow_op_flag:
                date_end_wait_start = dates_op['date_end_wait_start']

            row_dates = pd.DataFrame([[
                date_op,
                dates_op['date_end_leadtime'],
                dates_op['date_end_wait_start'],
                dates_op['date_end_dur_net_port'],
                dates_op['date_end_transit_ts'],
                dates_op['date_end_wait_site'],
                dates_op['date_end_dur_net_site'],
                dates_op['date_end_transit_tp'],
                dates_op['date_end'],
                dates_op['date_end_stat_chart'],
                'operation',
                oper.id,
                vessel1_id,
                ves_1,
                vessel2_id,
                ves_2,
                'oper_' + row['id']
            ]],columns=COLS)

            #------------------------
            # TOWING SITE CREATION
            #------------------------
            if tow_op_flag:
                vessel_tow_site, ves_2, mob_time = _take_vessel_data(find_element_class = find_element_class, op = tow_op_site)

                towing_site = CorrectionTowSite(
                    date_failure = date_failure,
                    vessel = vessel_tow_site,
                    oper = tow_op_site,
                    date_start = dates_op['date_end']
                )

                if not towing_port.tow_deferred and mob_time != 0:
                    if row_mob_line is None:
                        row_mob_line = towing_site.mobilitate_vessel(log_events=log_events, row=row, date_start=dates_op['date_end'])
                    else:
                        row_mob_line = pd.concat([
                            row_mob_line,
                            towing_site.mobilitate_vessel(log_events=log_events, row=row, date_start=dates_op['date_end'] - timedelta(hours = mob_time))
                        ], ignore_index=True)

                index_found = towing_site.check_leadtime_index(oper_sched = tow_site_oper_sched, CUTOFF_DATE = CUTOFF_DATE)
                if not index_found:
                    continue

                # Create row_tow with data
                date_op = dates_op['date_end'] - timedelta(hours = mob_time)

                df_filtered_start_tow = _check_index_row_validity(
                    idx_end_leadtime = towing_site.idx_end_leadtime,
                    last_valid_idx= last_valid_idx_tow_site,
                    row = row,
                    oper_sched = tow_site_oper_sched
                )

                if df_filtered_start_tow.empty:
                    continue

                dates_tow_site = compute_operation_datetimes(df_filtered_start_tow, tow_op_port_stat)

                row_tow_site = pd.DataFrame([[
                    dates_op['date_end'],
                    dates_tow_site['date_end_leadtime'],
                    dates_tow_site['date_end_wait_start'],
                    dates_tow_site['date_end_dur_net_port'],
                    dates_tow_site['date_end_transit_ts'],
                    dates_tow_site['date_end_wait_site'],
                    dates_tow_site['date_end_dur_net_site'],
                    dates_tow_site['date_end_transit_tp'],
                    dates_tow_site['date_end'],
                    dates_tow_site['date_end_stat_chart'],
                    'tow',
                    tow_op_site.id,
                    vessel_tow_site.id,
                    tow_op_site.vessel1_qt,
                    tow_op_site.vessel2_id,
                    ves_2,
                    'tow_' + row['id']
                ]],columns=COLS)

            ### CONCAT TO THE LOG_EVENTS
            if row_tow_port is not None:
                row_dates = pd.concat([row_dates,row_tow_port], axis=0, ignore_index=True)
            if row_tow_site is not None:
                row_dates = pd.concat([row_dates,row_tow_site], axis=0, ignore_index=True)
            if row_mob_line is not None:
                # Overwrite d_end in first mobilisation line with end wait of weather for operation for future mobilisation reduction (KPI_FINAL_COSTS)
                row_mob_line.loc[0, 'd_end'] = date_end_wait_start
                row_dates = pd.concat([row_dates,row_mob_line], axis=0, ignore_index=True)

            log_events = pd.concat([log_events,row_dates], axis=0, ignore_index=False)

    return log_events

if __name__ == '__main__':
    pass
