import pandas as pd

from oriom.core.functions.logs_timeseries.BaseCorrection import CorrectionImmediate, CorrectionDeferred


def create_operation_site(
    failure_: dict,
    vessel_: dict,
    vessels_: dict,
    oper_: dict,
    mobilisation: dict,
    df: dict,
    index: dict,
    CONST: dict
):
    """
    Create the corrective operation under analysis
    
    Args:
        failure_ (dict): Dictionary with failure variables
        vessel_ (dict): Dictionary with vessel variables
        vessels_ (dict): Dictionary with vessels id and qt
        oper_ (dict): Dictionary with operation variables
        mobilisation (dict): Dictionary with mobilisation variables
        df (dict): Dictionary with dataframe variables
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
            time_fail_op_immediately = time_fail_op_immediately,
            tow_op = tow_op_flag
        )
        # No mobilisation for operations with vessel to merge as considered in merge_funct
        if mobilisation['mob_time'] != 0 and vessel_['vessel'].type not in vessel_['vessel_to_merge']:            # NOTE Mobilisation of merging vessel is considered in create_logs_merge
            row_mob_line = immediate_correction.mobilitate_vessel(log_events = log_events, row = row)
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
            tow_op = tow_op_flag
        )

        # Evaluate end of leadtime date
        if not tow_op_flag:
            deferred_correction.leadtime_evaluation(lead_mob_time = mobilisation['lead_mob_time'])
        else:
            deferred_correction.add_leadtime_tow(
                lead_mob_time = mobilisation['lead_mob_time'],
            )

        index_found = deferred_correction.check_leadtime_index(oper_sched = oper_['oper_sched'], CUTOFF_DATE = CONST['CUTOFF_DATE'])
        if not index_found:
            return
        date_op = deferred_correction.date_op
        idx_end_leadtime = deferred_correction.idx_end_leadtime
    else:
        raise KeyError(f'Maintenance strategy not found: {failure_['failure'].maintenance_strategy}')


    df_filtered_start = _check_index_row_validity(
        idx_end_leadtime = idx_end_leadtime,
        last_valid_idx = index['last_valid_idx'],
        row = row,
        oper_sched = oper_['oper_sched']
    )

    if df_filtered_start.empty:
        return

    dates_op = compute_operation_datetimes(df_filtered_start, oper_['oper_stat'])

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
        'oper_' + row['id']
    ]],columns=CONST['COLS'])

    return row_dates, row_mob_line