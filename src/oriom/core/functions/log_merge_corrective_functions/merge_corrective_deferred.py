import numpy as np
import pandas as pd
from copy import deepcopy
import math
from datetime import timedelta
import logging

from oriom.utils import aux_functions
from oriom.utils.read_dataframe_value import approximate_hourly_data
from oriom.core.functions.operation_scheduler.define_shift import merge_shift_deferred
from oriom.core.functions.logs_timeseries.logs_timeseries_func import create_mobilisation
from oriom.core.functions.log_merge_corrective_functions import merged_deferred_aux


def merge_deferred_operations(
        log_events_def: pd.DataFrame,
        vessels: list,
        time_between_devices: dict,
        oper_per_vessel: dict,
        time_fail_op_immediately: float,
        percentile: float,
        COLS: list,
        find_element_class: object,
        duration_shift: float
):
    """
    This function merge the deferred operations similarly as inspection at site are conducted.
    Merge only same deferred operations togheter, and consider the fact that more operations can be done consecutevely or
    even simultaneously (drop off personnel). To conduct the next shift must wait the vessel that return to port from the previous
    shift done.

    Workflow:
    1. Regroup the log events by month and vessel
    2. For each operation deferred conducted with such vessel, check if it is a tow or an operation
        2.1. If it is a tow, copy the data from the log events file (need to be modified)
        2.2. Start a while loop with nº of correction to do of that specific operation
            2.2.1. If it is the first operation of the month and if so, add the mobilisation time
            2.2.2. Find how many hours of delay can start the operation excluding wait at site
            2.2.3. Merge the operations if possible with merge_shift_deferred(), otherwise conduct the operation as a single operation
            2.2.4. Create the rows and check if all vessel were used, if not, use the free vessel for the next operation on the same day
            2.2.5 Update the operation number analysed, if exceed the number of operations to do, exit the while loop and change operation
    3. Create the statistical chart date for the merged deferred operations


    Args:
        log_events_def  (pd.DataFrame): Dataframe with the deferred corrective log events.
        vessels (list): list of class `~oriom.classes.Vessel.Vessel`
        time_between_devices (dict): Dictionary with the time between devices.
        oper_per_vessel (dict): Dictionary with the operations for each vessels.
        time_fail_op_immediately (:obj:`float`): Time between failure and immediate operations.
        percentile (:obj:`int`, *optional*): Percentile considered for campaign charting strategy
        COLS (:obj:`list`): List of the column name for the log_events file.
        find_element_class (Find_element_class): Initialized instance that provides fast access to operations, vessels and failures via internal dictionaries.
        duration_shift (:obj:`float`): Maximum hours of working shift.

    """

    def cont_shift_lenght(df, column, initial_index):
        """
        Auxiliary function that return the number of hours that an operation can delay its starts from the operation_schedule.
        This represents the possible hours of work that can be added on the original shift conducted
        """
        val = df[column].to_numpy()[initial_index+1:]

        # Find the first value different from zero
        mask_zero = (val == 0)
        if not np.any(~mask_zero):  # all zeros
            return len(val)

        first_not_zero = np.argmax(~mask_zero)
        return first_not_zero


    log_events_df = deepcopy(log_events_def)

    row_merged_def = pd.DataFrame(columns=COLS)

    # Create col year_month to regroup easier
    log_events_df['year_month'] = log_events_df['d_trigger'].dt.to_period('M')

    # Regroup for year_month
    for period, df_group in log_events_df.groupby('year_month'):
        # Regroup for vessel
        for vessel_id, ops in oper_per_vessel.items():
            # If vessel tow is port operation and copy the line simply
            if vessel_id == 'tow':
                df_ops = df_group[df_group['id'].isin(ops)]
                for op_id, op_row in df_ops.groupby('id'):
                    row_merged_def = pd.concat([row_merged_def, op_row.drop(columns=['year_month'])], axis=0, ignore_index=False)
                continue

            # Flag to track when operations change
            operation_number_analysed = 0
            # Filter for the operations
            df_ops = df_group[df_group['id'].isin(ops)]
            # Take vessel1 data
            vessel = find_element_class.find_vessel(vessel_id)
            mob_time = vessel.mobilisation_time
            vessel_available = vessel.n_vessels
            vessel_busy = 0

            # Regroup for same operation and loop on them
            for op_id, op_row in df_ops.groupby('id'):
                op_row = op_row.sort_values(by='d_end_leadtime', ascending=True)

                # Take all the parameters of the operation
                (oper_stat, oper, tech_cost, vessel_2,
                    ves_2, oper_sched, index_wait_to_start_col, index_wait_port_col
                ) = aux_functions.take_attribute(op_id = op_id, find_element_class = find_element_class)

                try:
                    index_wait_at_site_col =  oper_sched.columns.get_loc('wait_site')
                except KeyError:
                    # Minor correction does not have wait at site
                    index_wait_at_site_col = None
                    wait_site_single_op = 0

                if mob_time is None:
                    mob_time = 0

                # Create a list of indexes for the end of leadtime for every correction to do
                end_wait_start_list = list(map(approximate_hourly_data, op_row['d_end_wait_start']))
                end_wait_start_list_idx = [oper_sched.loc[oper_sched['datetime'] == lead_time_end].index[0] for lead_time_end in end_wait_start_list]

                operation_concluded = 0
                n_oper = len(op_row)

                # Start analyze the operations until all failures are corrected
                while operation_concluded < n_oper:
                    wait_site_restriction = False
                    actual_row = op_row.iloc[operation_concluded]
                    # Find the first operation and the time shift of that day and its effective durations

                    # If the deferred operation is the first one done
                    if operation_concluded == 0 and operation_number_analysed == 0:
                        day_start_oper = op_row['d_end_wait_start'].iloc[0]
                        day_start_oper = approximate_hourly_data(day_start_oper)
                        day_start_oper_single_op = day_start_oper
                        date_wait_to_start_single_op = day_start_oper_single_op
                        operation_total_duration = (op_row['d_end_transit_tp'] - op_row['d_end_wait_start']).iloc[0].total_seconds() / 3600  # NOTE In this way take into consideration wait at site for first operation in case is present
                        count_fail = op_row['comments'].iloc[0].split("_", 1)[1]
                        n_vessel_used = 0

                        if mob_time !=0:
                            mobilisation_date = op_row['d_trigger'].iloc[0] + timedelta(hours=time_fail_op_immediately)
                            row_merged_def = create_mobilisation(
                                df = row_merged_def,
                                mobilisation_date = mobilisation_date,
                                end_mobi = op_row['d_end_wait_start'].iloc[0],
                                event = 'mobilisation_merged',
                                vessel = vessel,
                                oper_list = [oper.id],
                                count_fail = count_fail
                            )

                    # If is not first operation to be conducted consider the end of previous operation, delay of wait to start and wait to site
                    else:
                        # Original start is the time on which we try to start the operation
                        day_start_idx_original = day_start_idx

                        # Find the datetime of the index considered
                        day_start_oper_single_op = oper_sched.iat[day_start_idx_original, 0]
                        day_start_oper_single_op = approximate_hourly_data(day_start_oper_single_op)
                        day_start_oper = oper_sched.iat[day_start_idx, 0]

                        # Find the next day of work that can be conducted
                        try:
                            day_start_oper, day_start_idx, wait_to_start, wait_at_site = merged_deferred_aux.find_start_time(
                                day_start_oper = day_start_oper,
                                day_start_oper_single_op = day_start_oper_single_op,
                                day_start_idx = day_start_idx,
                                oper_sched = oper_sched,
                                index_wait_at_site_col = index_wait_at_site_col,
                                index_wait_to_start_col = index_wait_to_start_col
                            )
                        except ValueError as e_:
                            logging.warning(f'Merged_deferred:{e_}\n  Shift not available for {op_id} at date {oper_sched.iat[day_start_idx, index_wait_to_start_col]}\n failure remain uncorrected')
                            break

                        if wait_at_site != 0:
                            wait_site_restriction = True

                        operation_total_duration = oper.ts_data.dur_net_site + oper.ts_data.dur_net_port + oper.ts_data.transit_ts + oper.ts_data.transit_tp + wait_at_site
                        day_start_oper = day_start_oper + timedelta(hours=(wait_to_start))

                        # Confront if the next operation have the components ready. IMPORTANT NOTE should only check comp not vess leadtime
                        if day_start_oper < end_wait_start_list[operation_concluded]:
                            day_start_oper = end_wait_start_list[operation_concluded]

                        # Check if the operation is done in the same day of the previous, if not reset vessel_available to the maximum vessel
                        if day_start_oper.date() != day_start_oper_previous.date():
                            vessel_available = vessel.n_vessels

                    day_start_oper_previous = day_start_oper

                    # Create the time for the case operations will be merged
                    day_start_idx = oper_sched.loc[oper_sched['datetime'] == day_start_oper].index[0]
                    date_wait_to_start = day_start_oper
                    date_end_dur_net_port = date_wait_to_start + timedelta(hours=oper.ts_data.dur_net_port)
                    date_end_transit_site = date_end_dur_net_port + timedelta(hours=oper.ts_data.transit_ts)
                    date_end_wait_site = date_end_transit_site             # no wait at site
                    wait_port = round(oper_sched.iat[day_start_idx, index_wait_port_col], 2)

                    # Create the time for the case operations will not be be merged and only one op will be conducted
                    day_start_idx_single_op = oper_sched.loc[oper_sched['datetime'] == day_start_oper_single_op].index[0]

                    if index_wait_at_site_col:
                        wait_site_single_op = round(oper_sched.iat[day_start_idx_single_op, index_wait_at_site_col], 2)
                    wait_port_single_op = round(oper_sched.iat[day_start_idx_single_op, index_wait_port_col], 2)
                    wait_start_single_op = round(oper_sched.iat[day_start_idx_single_op, index_wait_to_start_col], 2)

                    if operation_concluded != 0 or operation_number_analysed != 0:
                        date_wait_to_start_single_op = day_start_oper_single_op + timedelta(hours=wait_start_single_op)

                    if not wait_site_restriction:
                        # Count how many hours of delay can start the operation
                        duration_shift_wait_start = cont_shift_lenght(oper_sched, 'wait_start', day_start_idx)
                        try:
                            duration_shift_wait_site = cont_shift_lenght(oper_sched, 'wait_site', day_start_idx)
                        except KeyError:
                            duration_shift_wait_site = duration_shift_wait_start

                        # Exclude the cases on which there is a wait to site # TODO MODIFY Consider more in case the vessel can stay out longer (along the night)
                        duration_shift_weather = min(duration_shift_wait_start, duration_shift_wait_site)
                        duration_shift_actual = min(duration_shift, duration_shift_weather)    # TODO Consider more in case the vessel can stay out longer (along the night)
                        day_start_idx_of_shift = day_start_idx     # This value is stored in case we'll use after remaining vessels from this shift in the same day

                        operation_concluded, day_start_idx, day_shift_end, total_device_this_shift, number_technicians, n_vessel_used = merge_shift_deferred(
                            duration_shift = duration_shift_actual,
                            duration_inspection = oper.ts_data.dur_net_site + oper.ts_data.dur_net_port,
                            transit_between_devices = time_between_devices[oper.id[:3]],
                            operation_total_duration = operation_total_duration,
                            n_vessel = vessel_available,
                            n_oper = n_oper,
                            operation_concluded = operation_concluded,
                            end_wait_start_list_idx = end_wait_start_list_idx,
                            day_start_idx = day_start_idx,
                            N_technicians_on_vessel = vessel.crew_capacity,
                            N_technicians_per_inspection = oper.tech_required,
                            vessel_type = vessel.type,
                            rov = oper.rov_drone,
                            day_start_oper = day_start_oper
                        )
                    else:
                        operation_concluded += 1
                        total_device_this_shift = 1
                        number_technicians = oper.tech_required
                        n_vessel_used = oper.vessel1_qt

                    # id and comments of merged operations
                    subset = op_row.iloc[operation_concluded - total_device_this_shift : operation_concluded]
                    group_def_id = list(zip(subset.index, subset['id']))
                    group_def_comm_failures = subset['comments'].tolist()
                    group_def_comm = {'tech_tot': number_technicians*n_vessel_used, 'tech_cost': tech_cost*number_technicians*n_vessel_used, 'failures': group_def_comm_failures} #NOTE and in case of second vessel are we counting tech cost?

                    # If no operations have been merged or they have a wait at site, only a single operation is conducted, insert single_op variables
                    if len(group_def_id) == 1:
                        # Create data for single operation
                        date_end_dur_net_port_single_op = date_wait_to_start_single_op + timedelta(hours=oper.ts_data.dur_net_port)
                        date_end_transit_site_single_op = date_end_dur_net_port_single_op + timedelta(hours=oper.ts_data.transit_ts)
                        date_end_wait_site_single_op = date_end_transit_site_single_op + timedelta(hours=wait_site_single_op)
                        date_end_dur_net_site_single_op = date_end_wait_site_single_op + timedelta(hours=oper.ts_data.dur_net_site)
                        date_end_transit_port_single_op = date_end_dur_net_site_single_op + timedelta(hours=oper.ts_data.transit_tp)
                        date_end_single_op = date_end_transit_port_single_op + timedelta(hours=wait_port_single_op)
                        day_end_idx_single_op = day_start_idx_single_op + math.ceil(
                            wait_start_single_op + oper.ts_data.transit_ts + wait_site_single_op +
                            oper.ts_data.dur_net_site + oper.ts_data.dur_net_port + oper.ts_data.transit_tp + wait_port_single_op
                        )
                        date_end_stat_chart_single_op = date_end_single_op + timedelta(
                            hours = oper_stat.dur_total_dict[str(day_start_oper_single_op.month)])

                        # Store the data
                        row_dates = pd.DataFrame([[
                                actual_row[0],
                                actual_row[1],
                                date_wait_to_start_single_op,
                                date_end_dur_net_port_single_op,
                                date_end_transit_site_single_op,
                                date_end_wait_site_single_op,
                                date_end_dur_net_site_single_op,
                                date_end_transit_port_single_op,
                                date_end_single_op,
                                date_end_stat_chart_single_op,
                                'operation_deferred_merged',
                                group_def_id,
                                vessel.id,
                                n_vessel_used,
                                vessel_2,
                                ves_2,
                                group_def_comm,
                                actual_row['shutdown'],
                                False,
                                False
                            ]], columns = COLS
                        )

                        day_start_idx = day_end_idx_single_op

                        # Check if used all the vessel, in case
                        vessel_available, day_start_idx, vessel_busy = merged_deferred_aux.vessel_reuse(
                            vessel_n = vessel.n_vessels,
                            n_vessel_used = n_vessel_used,
                            day_start_idx_previous = day_start_idx_single_op,
                            day_start_idx_next = day_end_idx_single_op,
                            vessel_busy = vessel_busy
                        )

                    else:
                        date_end_transit_tp = day_shift_end - timedelta(hours = wait_port)
                        date_end_dur_net_site = day_shift_end - timedelta(hours = (oper.ts_data.transit_tp + wait_port))
                        # Statistical chart date end from the end of last shift
                        try:
                            last_date_vessel_used = row_dates.iloc[-1]['d_end']  # d_end_shift_last_op
                        except UnboundLocalError:
                            last_date_vessel_used = actual_row[1]  # d_end_leadtime_first_op

                        date_end_stat_chart = last_date_vessel_used + timedelta(
                            hours = oper_stat.dur_total_dict[str(day_shift_end.month)])

                        row_dates = pd.DataFrame([[
                                actual_row[0],
                                actual_row[1],
                                date_wait_to_start,
                                date_end_dur_net_port,
                                date_end_transit_site,
                                date_end_wait_site,
                                date_end_dur_net_site,
                                date_end_transit_tp,
                                day_shift_end,
                                date_end_stat_chart,
                                'operation_deferred_merged',
                                group_def_id,
                                vessel.id,
                                n_vessel_used,
                                vessel_2,
                                ves_2,
                                group_def_comm,
                                True,
                                False,
                                False
                            ]], columns = COLS
                        )

                        vessel_available, day_start_idx, vessel_busy = merged_deferred_aux.vessel_reuse(
                            vessel_n = vessel.n_vessels,
                            n_vessel_used = n_vessel_used,
                            day_start_idx_previous = day_start_idx_of_shift,
                            day_start_idx_next = day_start_idx,
                            vessel_busy = vessel_busy
                        )

                    row_merged_def = pd.concat([row_merged_def,row_dates], axis=0, ignore_index=False)
                # Update the operation number analysed
                operation_number_analysed += 1

    # Add the statistical chart date for the merged deferred operations
    row_merged_def = merged_deferred_aux.create_stat_chart_campaign_operation(
        df = row_merged_def,
        vessels = vessels,
        percentile = percentile
    )

    return row_merged_def


if __name__ == '__main__':
    pass