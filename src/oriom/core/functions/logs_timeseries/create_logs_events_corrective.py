import math
import random
import logging
from copy import deepcopy
from datetime import timedelta, datetime
import pandas as pd

from oriom.classes.TowData import TowData
from oriom.utils.aux_functions import safe_getattr
from oriom.utils.read_dataframe_value import approximate_hourly_data
from oriom.core.functions.logs_timeseries import logs_timeseries_func
from oriom.core.functions.logs_timeseries.BaseCorrection import CorrectionTowPort, CorrectionTowSite
from oriom.core.functions.logs_timeseries.logs_corrective_aux import create_operation_site, _check_index_row_validity, compute_operation_datetimes

def _map_failure_indices(failure_df: pd.DataFrame, oper_sched: pd.DataFrame) -> pd.Series:
    """Map failure datetimes to schedule indices using a dict for O(1) lookups."""
    idx_map = {dt: i for i, dt in enumerate(oper_sched['datetime'].tolist())}
    return failure_df['datetime'].map(idx_map)


def _take_vessel_data(find_element_class, op):
    """ Take vessel data """
    if getattr(op, 'tow_to_port', None):
        return None, None, 0
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
        operation_log_file_stats (:obj:`list`): List of objects :class:`OperationsCorrectiveStat` with max percentile.
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

        # TAKE TOW DATA
        if getattr(oper, 'tow_to_port', None):
            tow_op_flag = True
            oper.tow_data = TowData.from_operation(find_element_class, oper)

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
            row_mob_line=None
            row_tow_port = None
            row_add_op_tow_port = None
            row_add_op_tow_site = None
            row_tow_site = None
            row_recommissioning = None
            deferred_tow = None
            tow_stat_chart_month = None
            double = False
            double_add = False
            row_dates = pd.DataFrame(columns=COLS)
            failure = find_element_class.find_failure_from_id(row['id'].split('.')[0])
            date_failure = row['datetime']
            operation_trig = row['operation_triggered']
            fail_index = row['matching_indices']
            op_chart_month = oper_stat.dur_total_dict[str(date_failure.month)]
            date_failure_tow = None

            ves_1 = oper.vessel1_qt
            component_lead_time = failure.lead_time

            #------------------------
            # TOWING PORT CREATION
            #------------------------
            if tow_op_flag:
                #------------------------
                # ADDITIONAL OP CREATION
                if oper.tow_data.add_op_tow_port:
                    tow_stat_chart_month = oper.tow_data.tow_op_port_stat.dur_total_dict[str(date_failure.month)]
                    op_sched_add_tow_port = safe_getattr(oper.tow_data.add_op_tow_port, ['ts_data','oper_sched'])
                    vessel, ves_2, mob_time = _take_vessel_data(find_element_class = find_element_class, op = oper.tow_data.add_op_tow_port)
                    if failure.maintenance_strategy == "specific month":
                        deferred_tow = True
                    if op_chart_month < mob_time:
                        double_add = True

                    row_add_op_tow_port, row_mob_line_op_tow_port = create_operation_site(
                        failure_ = {
                            'failure': failure,
                            'date_failure': date_failure, 
                        },
                        vessel_ = {'vessel': vessel, 'vessel_to_merge': vessel_to_merge},
                        vessels_ = {'vessel1_id': vessel.id, 'ves_1': oper.tow_data.add_op_tow_port.vessel1_qt, 'vessel2_id': oper.tow_data.add_op_tow_port.vessel2_id, 'ves_2': ves_2},
                        oper_ = {
                            'oper': oper.tow_data.add_op_tow_port, 
                            'oper_stat': oper.tow_data.oper_stat_op_tow_port, 
                            'oper_sched': op_sched_add_tow_port, 
                            'tow_stat_chart_month':  tow_stat_chart_month if double_add else True
                        },
                        mobilisation = {'mob_time': mob_time, 'lead_mob_time': mob_time, 'double': double_add},
                        row_ = {'log_events': log_events,'row': row, 'tow_op_flag': tow_op_flag},
                        index = {'fail_index': fail_index, 'last_valid_idx': safe_getattr(oper.tow_data.add_op_tow_port, ['ts_data','last_valid_index'])},
                        CONST = {'COLS': COLS, 'CUTOFF_DATE': CUTOFF_DATE, 'time_fail_op_immediately': time_fail_op_immediately},
                    )

                    if row_add_op_tow_port is None or row_add_op_tow_port.empty:
                        continue
                    if row_mob_line_op_tow_port is not None:
                        if not deferred_tow:
                            if row_mob_line is None:
                                row_mob_line = row_mob_line_op_tow_port
                            else:
                                row_mob_line = pd.concat([
                                    row_mob_line,
                                    row_mob_line_op_tow_port
                                ], ignore_index=True)
                    end_add_op_time = approximate_hourly_data(row_add_op_tow_port['d_end_dur_net_site'].iloc[0])
                    fail_index = op_sched_add_tow_port.index[op_sched_add_tow_port['datetime'] == end_add_op_time][0]
                else:
                    if failure.maintenance_strategy == 'specific month':
                        deferred_tow = True
                        deferred_tow_correction = CorrectionDeferred(
                            date_failure = date_failure,
                            vessel = vessel,
                            oper = oper,
                            preferred_month = failure.preferred_month,
                        )
                        deferred_tow_correction.leadtime_evaluation(lead_mob_time = mobilisation['lead_mob_time'])
                        index_found = deferred_tow_correction.check_leadtime_index(oper_sched = oper_['oper_sched'], CUTOFF_DATE = CONST['CUTOFF_DATE'])
                
                if oper.tow_data.add_op_tow_port:
                    date_failure_tow = row_add_op_tow_port['d_trigger'][0]
                    date_start = row_add_op_tow_port['d_end_dur_net_site'][0]
                elif deferred_tow:
                    date_failure_tow = deferred_tow_correction.date_op
                    date_start = date_failure_tow + timedelta(hours=time_fail_op_immediately)

                vessel, ves_2, mob_time = _take_vessel_data(find_element_class = find_element_class, op = oper.tow_data.tow_op_port)
                towing_port = CorrectionTowPort(
                    date_failure = date_failure_tow if date_failure_tow else date_failure,
                    vessel = vessel,
                    oper = oper.tow_data.tow_op_port,
                    failure = failure,
                    time_fail_op_immediately = time_fail_op_immediately,
                    date_start = date_start if deferred_tow else None
                )
                
                # Evaluate differently for deferred and immediate towing
                if not deferred_tow:
                    if mob_time != 0:
                        if row_mob_line is None:
                            row_mob_line = towing_port.mobilitate_vessel(log_events = log_events, row = row)
                        else:
                            row_mob_line = pd.concat([
                                row_mob_line,
                                towing_port.mobilitate_vessel(log_events = log_events, row = row)
                            ], ignore_index=True)

                    towing_port.add_hours_for_noon_shift(
                            fail_index = fail_index if not deferred_tow else deferred_tow_correction.idx_end_leadtime,
                            lead_mob_time = mob_time,
                            oper_sched = oper.tow_data.tow_port_oper_sched,
                        )
                else:
                    # mobilisation in deferred_merged
                    towing_port.leadtime_evaluation(lead_mob_time = mob_time, date_original = row_add_op_tow_port['d_trigger'][0])
                    index_found = towing_port.check_leadtime_index(oper_sched = oper.tow_data.tow_port_oper_sched, CUTOFF_DATE = CUTOFF_DATE)
                    if not index_found:
                        continue

                # Create row_tow with data
                date_op = towing_port.date_op

                df_filtered_start_tow = _check_index_row_validity(
                    idx_end_leadtime = towing_port.idx_end_leadtime,
                    last_valid_idx= oper.tow_data.last_valid_idx_tow_port,
                    r = row,
                    oper_sched = oper.tow_data.tow_port_oper_sched
                )

                if df_filtered_start_tow.empty:
                    continue
                if op_chart_month < mob_time:
                    double = True

                dates_tow_port = compute_operation_datetimes(
                    df_filtered_start = df_filtered_start_tow,
                    oper_stat = oper.tow_data.tow_op_port_stat,
                    add_op_end = end_add_op_time if oper.tow_data.add_op_tow_port else None,
                    tow_stat_chart_month = True,
                    double = double
                )

                # if operations is delayed reaggiast the df_filtered_start_tow by the difference time
                if 'diff_time' in dates_tow_port:
                    df_filtered_start_tow = _check_index_row_validity(
                        idx_end_leadtime = towing_port.idx_end_leadtime + dates_tow_port['diff_time'],
                        last_valid_idx= oper.tow_data.last_valid_idx_tow_port,
                        r = row,
                        oper_sched = oper.tow_data.tow_port_oper_sched
                    )

                    if df_filtered_start_tow.empty:
                        continue

                    dates_tow_port = compute_operation_datetimes(
                        df_filtered_start = df_filtered_start_tow,
                        oper_stat = oper.tow_data.tow_op_port_stat,
                        tow_stat_chart_month = True,
                        double = double
                    )

                date_end_wait_start = dates_tow_port['date_end_wait_start']
                row_tow_port = pd.DataFrame([[
                    date_op if not deferred_tow else date_failure_tow,
                    dates_tow_port['date_end_leadtime'] if not oper.tow_data.add_op_tow_port else date_failure_tow + timedelta(hours=mob_time),
                    dates_tow_port['date_end_wait_start'],
                    dates_tow_port['date_end_dur_net_port'],
                    dates_tow_port['date_end_transit_ts'],
                    dates_tow_port['date_end_wait_site'],
                    dates_tow_port['date_end_dur_net_site'],
                    dates_tow_port['date_end_transit_tp'],
                    dates_tow_port['date_end'],
                    dates_tow_port['date_end_stat_chart'],
                    'tow',
                    oper.tow_data.tow_op_port.id,
                    vessel.id,
                    oper.tow_data.tow_op_port.vessel1_qt,
                    oper.tow_data.tow_op_port.vessel2_id,
                    oper.tow_data.tow_op_port.vessel2_qt,
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
            # find the data needed for such operation
            vessel, ves_2, mob_time = _take_vessel_data(find_element_class = find_element_class, op = oper)
            lead_mob_time = math.ceil(max(mob_time,component_lead_time))
            vessel1_id = oper.vessel1_id if not getattr(oper, 'tow_to_port', None) else None
            vessel2_id = oper.vessel2_id if not getattr(oper, 'tow_to_port', None) else None

            #------------------------
            # OPERATION CREATION
            #------------------------
            if operation_trig is not None:
                row_dates, row_mob_line_op = create_operation_site(
                    failure_ = {
                        'failure': failure, 
                        'date_failure': date_failure, 
                        'tow_op_previous': deferred_tow,
                        'original_date_fail': row_tow_port['d_trigger'][0] if tow_op_flag else None
                    },
                    vessel_ = {'vessel': vessel, 'vessel_to_merge': vessel_to_merge},
                    vessels_ = {'vessel1_id': vessel1_id, 'ves_1': ves_1, 'vessel2_id': vessel2_id, 'ves_2': ves_2},
                    oper_ = {'oper': oper, 'oper_stat': oper_stat, 'oper_sched': oper_sched},
                    mobilisation = {'mob_time': mob_time, 'lead_mob_time': lead_mob_time},
                    row_ = {'log_events': log_events, 'row': row, 'tow_op_flag': tow_op_flag},
                    index = {'fail_index': fail_index, 'last_valid_idx': last_valid_idx},
                    CONST = {'COLS': COLS, 'CUTOFF_DATE': CUTOFF_DATE, 'time_fail_op_immediately': time_fail_op_immediately},
                )
                
                if row_dates is None or row_dates.empty:
                    continue
                if not tow_op_flag:
                    date_end_wait_start = row_dates['d_end_wait_start'][0]
                if row_mob_line_op is not None:
                    if row_mob_line is None:
                        row_mob_line = row_mob_line_op
                    else:
                        row_mob_line = pd.concat([
                            row_mob_line,
                            row_mob_line_op
                        ], ignore_index=True)
            else:
                logging.error(f"LogDates: Operation trigger not found for failure {row['id']}")
                raise KeyError

            #------------------------
            # TOWING SITE CREATION
            #------------------------
            if tow_op_flag:
                vessel_tow_site, ves_2, mob_time = _take_vessel_data(find_element_class = find_element_class, op = oper.tow_data.tow_op_site)

                towing_site = CorrectionTowSite(
                    date_failure = date_failure,
                    vessel = vessel_tow_site,
                    oper = oper.tow_data.tow_op_site,
                    date_start = row_dates['d_end'][0],
                )

                if mob_time != 0 and not deferred_tow:
                    if row_mob_line is None:
                        row_mob_line = towing_site.mobilitate_vessel(log_events=log_events, row=row, date_start=row_dates['d_end'][0])
                    else:
                        row_mob_line = pd.concat([
                            row_mob_line,
                            towing_site.mobilitate_vessel(log_events=log_events, row=row, date_start=row_dates['d_end'][0] - timedelta(hours = mob_time))
                        ], ignore_index=True)

                index_found = towing_site.check_leadtime_index(oper_sched = oper.tow_data.tow_site_oper_sched, CUTOFF_DATE = CUTOFF_DATE)
                if not index_found:
                    continue

                # Create row_tow with data
                date_op = row_dates['d_end'][0] - timedelta(hours = mob_time)

                df_filtered_start_tow = _check_index_row_validity(
                    idx_end_leadtime = towing_site.idx_end_leadtime,
                    last_valid_idx= oper.tow_data.last_valid_idx_tow_site,
                    r = row,
                    oper_sched = oper.tow_data.tow_site_oper_sched
                )

                if df_filtered_start_tow.empty:
                    continue

                dates_tow_site = compute_operation_datetimes(df_filtered_start_tow, oper.tow_data.tow_op_site_stat)

                row_tow_site = pd.DataFrame([[
                    row_dates['d_end'][0],
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
                    oper.tow_data.tow_op_site.id,
                    vessel_tow_site.id,
                    oper.tow_data.tow_op_site.vessel1_qt,
                    oper.tow_data.tow_op_site.vessel2_id,
                    ves_2,
                    'tow_' + row['id']
                ]],columns=COLS)

                #------------------------
                # ADDITIONAL OPERATION TO TOWING SITE
                if oper.tow_data.add_op_tow_site:
                    tow_stat_chart_month = oper.tow_data.tow_op_site_stat.dur_total_dict[str(row_tow_site['d_end_leadtime'].iloc[0].month)]

                    # Update the fail_index
                    end_tow_site_date = approximate_hourly_data(row_dates['d_end'][0])
                    end_add_op_time_site = approximate_hourly_data(row_tow_site['d_end_dur_net_site'].iloc[0])
                    fail_index = oper.tow_data.tow_site_oper_sched.index[oper.tow_data.tow_site_oper_sched['datetime'] == end_tow_site_date][0]

                    vessel, ves_2, mob_time = _take_vessel_data(find_element_class = find_element_class, op = oper.tow_data.add_op_tow_site)
                    op_sched_add_tow_site = safe_getattr(oper.tow_data.add_op_tow_site, ['ts_data','oper_sched'])
                    row_add_op_tow_site, row_mob_line_op_tow_site = create_operation_site(
                        failure_ = {
                            'failure': failure, 
                            'date_failure': row_dates['d_end'][0] + timedelta(hours=time_fail_op_immediately), 
                            'end_add_op_time': end_add_op_time_site,
                            'tow_op_previous': deferred_tow,
                            'original_date_fail': row_dates['d_trigger'][0] if deferred_tow else None
                        },
                        vessel_ = {'vessel': vessel, 'vessel_to_merge': vessel_to_merge},
                        vessels_ = {'vessel1_id': vessel.id, 'ves_1': oper.tow_data.add_op_tow_site.vessel1_qt, 'vessel2_id': oper.tow_data.add_op_tow_site.vessel2_id, 'ves_2': ves_2},
                        oper_ = {
                            'oper': oper.tow_data.add_op_tow_site,
                            'oper_stat': oper.tow_data.oper_stat_op_site,
                            'oper_sched': op_sched_add_tow_site,
                            'tow_stat_chart_month': tow_stat_chart_month
                        },
                        mobilisation = {'mob_time': mob_time, 'lead_mob_time': mob_time},
                        row_ = {'log_events': log_events, 'row': row, 'tow_op_flag': tow_op_flag},
                        index = {'fail_index': fail_index, 'last_valid_idx': safe_getattr(oper.tow_data.add_op_tow_site, ['ts_data','last_valid_index'])},
                        CONST = {'COLS': COLS, 'CUTOFF_DATE': CUTOFF_DATE, 'time_fail_op_immediately': time_fail_op_immediately},
                    )
                    
                    if row_add_op_tow_site is None or row_add_op_tow_site.empty:
                        continue
                    if row_mob_line_op_tow_site is not None and not deferred_tow:
                        if row_mob_line is None:
                            row_mob_line = row_mob_line_op_tow_site
                        else:
                            row_mob_line = pd.concat([
                                row_mob_line,
                                row_mob_line_op_tow_site
                            ], ignore_index=True)
                    # Create row for recommissioning
                    if getattr(oper.tow_data.tow_op_site, 'recommissioning_time', None):
                        row_recommissioning = row_add_op_tow_site.copy()
                        row_recommissioning['event'] = 'recommissioning'
                        row_recommissioning[["vessel_1", "n_vessel_1", "vessel_2", "n_vessel_2"]] = None                        
                        modified_date = row_add_op_tow_site['d_end_dur_net_site'] + timedelta(hours=oper.tow_data.tow_op_site.recommissioning_time)                  
                        for ev in ['d_end_dur_net_site', 'd_end_transit_tp', 'd_end']:
                            row_recommissioning[ev] = modified_date

            ### CONCAT TO THE LOG_EVENTS
            for rows_df in [row_tow_port, row_tow_site, row_add_op_tow_port, row_add_op_tow_site, row_recommissioning]:
                if rows_df is not None:
                    row_dates = pd.concat([row_dates, rows_df], axis=0, ignore_index=True)
            if row_mob_line is not None:
                # Overwrite d_end in first mobilisation line with end wait of weather for operation for future mobilisation reduction (KPI_FINAL_COSTS)
                row_mob_line.loc[0, 'd_end'] = date_end_wait_start
                row_dates = pd.concat([row_dates, row_mob_line], axis=0, ignore_index=True)
            
            log_events = pd.concat([log_events, row_dates], axis=0, ignore_index=False)

    return log_events

if __name__ == '__main__':
    pass
