import pandas as pd
import logging
from datetime import timedelta, datetime

from oriom.core.functions.logs_timeseries.BaseCorrection import CorrectionImmediate, CorrectionDeferred
from oriom.core.functions.logs_timeseries import logs_timeseries_func


def _check_index_row_validity(
        idx_end_leadtime:int,
        last_valid_idx: int,
        r: pd.Series,
        oper_sched: pd.DataFrame
):
    """ Check first if index leadtime and df_filtered are valid"""

    # Check if the opeartion can be conducted before the end of lifetime of the farm
    if idx_end_leadtime > last_valid_idx:
        try:
            date_failed = oper_sched.iat[idx_end_leadtime,0]
        except IndexError:
            date_failed = {'idx': idx_end_leadtime}
        logging.warning(f"Log_dates: Shift not available for {r['id']} at date {date_failed}, failure remain uncorrected")
        return pd.DataFrame()

    df_filtered_start = oper_sched.iloc[idx_end_leadtime]

    # Check if exist any NaN value on the oper_schedule file filtered
    if df_filtered_start.iloc[1:-4].isna().any().any():
        raise ValueError(f"Log_dates: NaN row in oper_schedul {r['id']} at index {idx_end_leadtime}, last valid index: {last_valid_idx}")

    return df_filtered_start


def compute_operation_datetimes(df_filtered_start, oper_stat, add_op_end=None):
    """
    Calculate dates of the various phases of an operations.

    Args:
        df_filtered_start (pd.DataFrame): DataFrame with temporal data of operation.
        oper_stat (object): objects :class:`OperationsCorrectiveStat`
        add_op_end (timestamp): timestamp of the end of the additional operation

    Returns:
        dict: Dict with all dates.
    """
    date_end_leadtime = df_filtered_start.iat[0]

    date_end_wait_start = logs_timeseries_func.create_data(df_filtered_start, 'wait_start', date_end_leadtime)
    date_end_dur_net_work_port = logs_timeseries_func.create_data(df_filtered_start, 'dur_net_port', date_end_wait_start)
    date_end_dur_net_port = logs_timeseries_func.create_data(df_filtered_start, 'wait_port', date_end_dur_net_work_port)
    date_end_transit_ts = logs_timeseries_func.create_data(df_filtered_start, 'transit_to_site', date_end_dur_net_port)
    date_end_wait_site = logs_timeseries_func.create_data(df_filtered_start, 'wait_site', date_end_transit_ts)

    # Evaluate if other operations delay the schedule if does exist additional op
    if add_op_end:
        diff_time = int((add_op_end - date_end_wait_site).total_seconds() / 3600)
        # If delay is higher than 0 return difference
        if diff_time > 0:
            diff_time = int((add_op_end - date_end_wait_site).total_seconds() / 3600)
            return {'diff_time': diff_time} if float(round(df_filtered_start['wait_start'],2)) == 0 else {'diff_time': diff_time + int(round(df_filtered_start['wait_start'],2))}

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


def create_operation_site(
    failure_: dict,
    vessel_: dict,
    vessels_: dict,
    oper_: dict,
    mobilisation: dict,
    row_: dict,
    index: dict,
    CONST: dict,
):
    """
    Create the corrective operation under analysis
    
    Args:
        failure_ (dict): Dictionary with failure variables
        vessel_ (dict): Dictionary with vessel variables
        vessels_ (dict): Dictionary with vessels id and qt
        oper_ (dict): Dictionary with operation variables
        mobilisation (dict): Dictionary with mobilisation variables
        row_ (dict): Dictionary with row variables of the df
        index (dict): Dictionary with index variables
        CONST (dict): Dictionary with constant variables

    """
    row_mob_line = None

    # Find the start of the vessel use
    if failure_['failure'].maintenance_strategy == 'immediately':
        immediate_correction = CorrectionImmediate(
            date_failure = failure_['date_failure'],
            vessel = vessel_['vessel'],
            oper = oper_['oper'],
            time_fail_op_immediately = CONST['time_fail_op_immediately'],
            tow_op = row_['tow_op_flag']
        )
        # No mobilisation for operations with vessel to merge as considered in merge_funct
        if mobilisation['mob_time'] != 0 and vessel_['vessel'].type not in vessel_['vessel_to_merge']:            # NOTE Mobilisation of merging vessel is considered in create_logs_merge
            row_mob_line = immediate_correction.mobilitate_vessel(log_events = row_['log_events'], r = row_['row'])
        # Row at operation schedule with idx at 5 AM
        immediate_correction.add_hours_for_noon_shift(
            fail_index = index['fail_index'],
            lead_mob_time = mobilisation['lead_mob_time'],
            oper_sched = oper_['oper_sched'],
        )
        date_op = immediate_correction.date_op
        idx_end_leadtime = immediate_correction.idx_end_leadtime

    elif failure_['failure'].maintenance_strategy == 'specific month':
        deferred_correction = CorrectionDeferred(
            date_failure = failure_['date_failure'],
            vessel = vessel_['vessel'],
            oper = oper_['oper'],
            preferred_month = failure_['failure'].preferred_month,
            tow_op = row_['tow_op_flag']
        )

        # Evaluate end of leadtime date
        if not row_['tow_op_flag']:
            deferred_correction.leadtime_evaluation(lead_mob_time = mobilisation['lead_mob_time'])
        else:
            deferred_correction.add_leadtime_tow(
                lead_mob_time = mobilisation['lead_mob_time'],
            )

        index_found = deferred_correction.check_leadtime_index(oper_sched = oper_['oper_sched'], CUTOFF_DATE = CONST['CUTOFF_DATE'])
        if not index_found:
            return None, None
        date_op = deferred_correction.date_op
        idx_end_leadtime = deferred_correction.idx_end_leadtime
    else:
        raise KeyError(f'Maintenance strategy not found: {failure_["failure"].maintenance_strategy}')

    df_filtered_start = _check_index_row_validity(
        idx_end_leadtime = idx_end_leadtime,
        last_valid_idx = index['last_valid_idx'],
        r = row_['row'],
        oper_sched = oper_['oper_sched']
    )

    if df_filtered_start.empty:
        return None, None

    dates_op = compute_operation_datetimes(df_filtered_start, oper_['oper_stat'], failure_.get('end_add_op_time') if failure_.get('end_add_op_time') else None)
    # if operations is delayed reaggiast the df_filtered_start_tow by the difference time
    if 'diff_time' in dates_op:
        df_filtered_start_tow = _check_index_row_validity(
            idx_end_leadtime = idx_end_leadtime + dates_op['diff_time'],
            last_valid_idx= index['last_valid_idx'],
            r = row_['row'],
            oper_sched = oper_['oper_sched']
        )

        if df_filtered_start_tow.empty:
            return None, None
        dates_op = compute_operation_datetimes(df_filtered_start_tow, oper_['oper_stat'])

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
        oper_['oper'].id,
        vessels_['vessel1_id'],
        vessels_['ves_1'],
        vessels_['vessel2_id'],
        vessels_['ves_2'],
        'oper_' + row_['row']['id']
    ]],columns=CONST['COLS'])

    return row_dates, row_mob_line