import pandas as pd
import math
import logging
from datetime import timedelta
from collections import defaultdict

from oriom.core.functions.logs_timeseries.logs_timeseries_func import create_data, create_mobilisation
from oriom.core.functions.vessels_manager.vessels_merge_day import df_vessel_merge_use
from oriom.utils.read_dataframe_value import approximate_hourly_data


def merge_operation(
        log_events_oper_imm: pd.DataFrame,
        vessels: list,
        find_element_class,
        time_between_devices,
        grouped_operations: dict,
        oper_dict: dict,
        COLS: list
    )->pd.DataFrame:

    """
    This function concatenate rows creating a dataframe of the corrective operations that can be merged.
    Exclude all the deferred operations from the analysis. Use the predifined groups of operations to merge the operations
    previously calculated in the function mergeble_operation. Returns the dataframe with the merged operations.

    Args:
        log_events_oper_imm (pd.DataFrame): Dataframe with the immediate corrective log events.
        vessels (list):List of objectts :class:`Vessel`.
        find_element_class (Find_element_class): Initialized instance that provides fast access to operations, vessels and failures via internal dictionaries.
        time_between_devices (dict): Dictionary with the time between devices.
        grouped_operations (dict): Dictionary with the mergeble operations divided by vessel and group. Ranked by less restrictive
            to most restrictive
        oper_dict (dict): Dictionary with the operations.
        COLS (list): List of columns to be used in the dataframe.

    Returns:
        pd.DataFrame: Dataframe with the immediate corrective merged operations.
    """

    def merge_operation_row(
            log_events: pd.DataFrame,
            day_oper,
            vessels: list,
            time_between_devices,
            grouped_operations: dict,
            oper_dict: dict,
            COLS: list,
            operation_already_merged: set
    ):
        """
        This function evaluate each row of the log_event file filtered only by immediate correction, each time that more operation
        are conducted in the same day, evaluates if the ops are present in the same mergeble group. If so, evaluate how many operation
        can be merged considering the crew member limit of the vessel and the availability of the weather condition (if the most
        restrictive operation is conducted all the other should be conducted, usually longer operations are the first to start)
        rows creating a dataframe of the corrective operations that can be merged.

        NOTE: For now only operations that use CTV vessel can be merged for immediate corrections as usually the other operations require
            the vessel present at the site on which the O&M is conducted, so no drop off is available

        NOTE: merging of operations do not use more than 1 CTV vessel, do not use other type of vessel

        NOTE: If a vessel is full it will be called a new vessel to conduct the operation, the operation will be conducted in the same day

        TODO: For this analysis no optimization is done to try to distribute in an optimal way the number of crew members in the vessel.
            The call of the vessels are considering the cronological time on which the failures are reported. So if after 5 failure a new
            vessel need to be called it represent this charting time (similar to reality). 
        
        TODO: In this code if there are 10 operation in a group to conduct in the same day and the hours to add of this 10 op exceed the n amount of hour
            available to work it will not merged. Meanwhile it should divide the 10 op in smaller group in order that do not exceed the
            amount of workable hours available. So insthead of using only one vesse with 10 op regrouped it shoul count example 3 vessel
            with 3 groups of operation merged insthead of 10 vessel. This do not happen many times.
        Args:
            log_events (:obj: `pd.DataFrame`): Dataframe with the log events.
            day_oper (:obj:`pd.Series`): Row of days_vessel DataFrame that show how many vessel are used and which are the ops on the day under
                analysis.
            vessels (:obj:`list`):List of objectts :class:`Vessel`.
            time_between_devices (:obj:`dict`): Dictionary with the time between devices.
            grouped_operations (:obj:`dict`): Dictionary with the mergeble operations divided by vessel and group. Ranked by less restrictive
                to most restrictive
            oper_dict (:obj:`dict`): Dictionary with the operations.
            COLS (:obj:`list`): List of columns to be used in the dataframe.
            operation_already_merged (set): set of index of operation already merged or passed

        Returns:
            pd.DataFrame: Dataframe with the immediate corrective merged operations.
        """
        def find_operation_groups(
            operations: dict[int, str], 
            oper_dict: dict, 
            vessel_groups: dict
        ) -> list[list[tuple[int, str]]]:
            """
            Find the minimum number of groups for the given operations based on vessel and predefined groups.
            Returns:
                list of groups, where each group is a list of tuples (key, operation).
            """
            oper_not_to_group = {}

            # Handle empty operations dict
            if not operations:
                return []
            
            # Handle missing operations filtering them
            if not all(op in oper_dict for op in operations.values()):
                oper_not_to_group = {k: v for k, v in operations.items() if v not in oper_dict}
                operations = {k: v for k, v in operations.items() if v in oper_dict}
            
            # Create a copy of operations to track remaining ones
            remaining_ops = operations.copy()
            
            # First, group operations by vessel
            vessel_ops = defaultdict(list)
            for key, op in operations.items():
                vessel = oper_dict[op]['vess_1']
                vessel_ops[vessel].append((key, op))
            
            # For each vessel, try to find predefined groups that can contain its operations
            result_groups = []
            for vessel, vessel_operations in vessel_ops.items():
                # Get unique operations for this vessel
                unique_ops = []
                seen_ops = set()
                for key, op in vessel_operations:
                    if op not in seen_ops:
                        unique_ops.append((key, op))
                        seen_ops.add(op)
                
                # Try to find predefined groups that can contain these operations
                found_groups = False
                
                # Check each predefined group in the vessel
                for group_name, group_ops in vessel_groups[vessel].items():
                    # Check if all unique operations in this vessel can be in this group
                    if all(op in group_ops for _, op in unique_ops):
                        result_groups.append(unique_ops)
                        found_groups = True
                        # Remove these operations from remaining_ops
                        for key, op in unique_ops:
                            del remaining_ops[key]
                        break
                
                # If no predefined group found, try to find minimum number of groups
                if not found_groups:
                    # Split operations into groups based on predefined groups
                    current_group = []
                    for key, op in unique_ops:
                        # Check if this operation can be added to the current group
                        can_add = True
                        for _, existing_op in current_group:
                            # Check if these operations can be in the same group
                            can_be_together = False
                            for group_name, group_ops in vessel_groups[vessel].items():
                                if op in group_ops and existing_op in group_ops:
                                    can_be_together = True
                                    break
                            if not can_be_together:
                                can_add = False
                                break
                        
                        if can_add:
                            current_group.append((key, op))
                        else:
                            if current_group:
                                result_groups.append(current_group)
                            current_group = [(key, op)]
                    
                    if current_group:
                        result_groups.append(current_group)
                    
                    # Remove these operations from remaining_ops
                    for key, op in unique_ops:
                        del remaining_ops[key]
            
            # Now handle remaining operations (duplicates)
            while remaining_ops:
                key, op = next(iter(remaining_ops.items()))
                vessel = oper_dict[op]['vess_1']
                
                # Try to find a group for this vessel that can contain this operation
                found_group = False
                for group in result_groups:
                    if group and oper_dict[group[0][1]]['vess_1'] == vessel:
                        # Check if this operation can be added to this group
                        can_add = True
                        for _, existing_op in group:
                            can_be_together = False
                            for group_name, group_ops in vessel_groups[vessel].items():
                                if op in group_ops and existing_op in group_ops:
                                    can_be_together = True
                                    break
                            if not can_be_together:
                                can_add = False
                                break
                        if can_add:
                            group.append((key, op))
                            del remaining_ops[key]
                            found_group = True
                            break
                
                if not found_group:
                    # Create a new group for this operation
                    result_groups.append([(key, op)])
                    del remaining_ops[key]

            # Add missing operations as single element's group
            if oper_not_to_group:
                for k, v in oper_not_to_group.items():
                    result_groups.append([(k, v)])
            
            return result_groups
        

        def remove_op_already_merged(groups: list, operation_already_merged: set)->list:
            """ 
            Filter operations from groups that have already been analysed
            Add the index of the filtered groups

            Args:
                groups (list): list of tuple (idx of log_event, oper_id) of op simultaneously
                operation_already_merged (set): set of index of op already analysed/merged

            Returns:
                set: filtered groups
            """

            filtered_data = []
            for sublist in groups:
                new_sublist = [t for t in sublist if t[0] not in operation_already_merged]
                if new_sublist:
                    filtered_data.append(new_sublist)
                    operation_already_merged.update(t[0] for t in new_sublist)  # aggiunge gli ID rimasti

            return filtered_data
        

        def group_merge_data(group, log_events):

            """ This function evaluate the data for the group of merged operations """
            idx_group = [item[0] for item in group]
            selected_rows = log_events.loc[idx_group]
            oper_group_comments_failures =  selected_rows['comments'].tolist()
            date_end_stat_chart = selected_rows.sort_values('d_trigger')['d_end_stat_chart'].iloc[0]

            return selected_rows, oper_group_comments_failures, date_end_stat_chart
        
        def merge_group_operation(group, time_between_devices, crew_capacity, oper_dict):
            """ This function evaluate how many crew member are on board considering the operation to group and the hours to add required"""

            count_oper = {
                'opv': time_between_devices['opv']*sum(1 for _, value in group if value.startswith('opv')), 
                'ofw': time_between_devices['ofw']*sum(1 for _, value in group if value.startswith('ofw')),
                'owc': time_between_devices['owc']*sum(1 for _, value in group if value.startswith('owc'))
            }

            crew_on_board = 0
            crew_on_board_cost = 0
            longest_dur = 0

            o = 0
            for op in group:
                if crew_on_board + oper_dict[op[1]]['technician'] > crew_capacity:
                    break
                crew_on_board += oper_dict[op[1]]['technician']
                crew_on_board_cost += oper_dict[op[1]]['technician_cost']

                dur = oper_dict[op[1]]['duration']
                if dur > longest_dur:
                    longest_dur = dur
                    op_longest_dur = op
                o += 1

            tech = op_longest_dur[1][:3]
            hours_to_add = round(sum(count_oper.values()) - time_between_devices[tech], 2)
            hours_to_add_rounded = math.ceil(hours_to_add)

            return crew_on_board, crew_on_board_cost, op_longest_dur, hours_to_add, hours_to_add_rounded, o
        
        ### MERGE OPERATION CODE
        ### MERGE OPERATION CODE
        operations_conducted = []
        seen_ops = set()

        row_merged = pd.DataFrame(columns=COLS)

        operation_day = day_oper['operations'].copy()
        # Avoid to duplicate merging with operations that have lenght for more than 1 day
        operations_day_keys = list(operation_day.keys())  
        for op in operations_day_keys:
            if op in seen_ops:
                operation_day.pop(op, None)
            else:
                seen_ops.add(op)

        operations_conducted.append(operation_day)

        # Find the minimum number of groups
        groups = find_operation_groups(operation_day, oper_dict, grouped_operations)

        groups = remove_op_already_merged(groups = groups, operation_already_merged = operation_already_merged)

        # Find now the operation merged, vessel and max duration, Check if max crew reached on the vessel
        for group in groups:
            group = sorted(group, key=lambda x: x[0])
            selected_rows, oper_group_comments_failures, date_end_stat_chart = group_merge_data(group, log_events)

            # If the group has more than 1 operation count the various time_between devices
            if len(group) != 1:
                operaz=group[0][1]
                vess_group = oper_dict[operaz]['vess_1']
                vess_group = find_element_class.find_vessel(vess_group)
                crew_capacity = vess_group.crew_capacity
                
                crew_on_board, crew_on_board_cost, op_longest_dur, hours_to_add, hours_to_add_rounded, o = merge_group_operation(group, time_between_devices, crew_capacity, oper_dict)

                # If max crew is reached split the group in two operations
                if o != len(group):
                    valid_group = group[:o]  
                    remaining_group = group[o:]  
                    group[:] = valid_group

                    crew_on_board, crew_on_board_cost, op_longest_dur, hours_to_add, hours_to_add_rounded, o = merge_group_operation(group, time_between_devices, crew_capacity, oper_dict)

                    # Recalculate for the new group                    
                    selected_rows, oper_group_comments_failures, date_end_stat_chart = group_merge_data(group, log_events)

                    if remaining_group:
                        groups.append(remaining_group)
                
                # Take the time at which the longest duration start and check from the operation schedule if can start "hours_to_add" after
                start_operation = log_events.at[op_longest_dur[0],'d_end_dur_net_port']
                start_operation = approximate_hourly_data(start_operation)

                op_longest_dur_ts_data = find_element_class.find_oper_schedule(op_longest_dur[1])

                df = op_longest_dur_ts_data.oper_sched
                start_operation_scheduler = df.loc[df['datetime'] == start_operation]
        
                idx_start_oper_after = start_operation_scheduler.index
                duration_total = math.ceil(op_longest_dur_ts_data.dur_total)
                
                try:
                    duration_total_merged = start_operation_scheduler['dur_total'].iloc[0] + hours_to_add
                except IndexError:
                    raise IndexError
                # If the wait to start is 0 delaying the start of the longest operation, the merged operation can be conducted
                if duration_total_merged<=duration_total:
                    # if the duration_total_merged is equal to the rounded hour of duration_total
                    merge = True
                    start_operation_after_scheduler = start_operation_scheduler
                else:
                    # if the longest operation can start hours_to_add_rounded after
                    start_oper_after = start_operation_scheduler.iat[0,0] + timedelta(hours=hours_to_add_rounded) 
                    start_operation_after_scheduler = df.loc[df['datetime'] == start_oper_after]
                    idx_start_oper_after = start_operation_after_scheduler.index
                    wait_to_start = start_operation_after_scheduler['wait_start'].iloc[0]
                    
                    if wait_to_start == 0:
                        merge = True
                    else: merge = False
                if merge:
                    # If the index is over the last valid index in oper_schedule do not merge
                    if idx_start_oper_after > op_longest_dur_ts_data.last_valid_index:
                        merge = False
                        
                    else:
                        date_end_dur_net_port = start_operation_scheduler.iat[0,0]
                        date_end_transit_ts = create_data(start_operation_scheduler, 'transit_to_site', date_end_dur_net_port)
                        date_end_wait_site = create_data(start_operation_scheduler, 'wait_site', date_end_transit_ts)
                        date_end_dur_net_site = create_data(start_operation_after_scheduler, 'dur_net_site', date_end_wait_site)
                        date_end_transit_tp = create_data(start_operation_after_scheduler, 'transit_to_port', date_end_dur_net_site)
                        date_end  = create_data(start_operation_after_scheduler, 'wait_port', date_end_transit_tp)

                        min_values = selected_rows.iloc[:, :3].min()
                        event = 'operation_merged'
                        
                        oper_group_comments = {'tech_tot': crew_on_board, 'tech_cost': crew_on_board_cost, 'failures': oper_group_comments_failures}

                        row_dates = pd.DataFrame([[
                            min_values[0],
                            min_values[1],
                            min_values[2],
                            date_end_dur_net_port,
                            date_end_transit_ts,
                            date_end_wait_site,
                            date_end_dur_net_site,
                            date_end_transit_tp,
                            date_end,
                            date_end_stat_chart,
                            event,
                            group,
                            vess_group.id,
                            1,
                            None,
                            None,                     # IMPORTANT NOTE: merging of operations do not use more than 1 vessel
                            oper_group_comments,
                            None,
                            False, 
                            False
                        ]],columns=COLS)

                        if vess_group.mobilisation_time != 0:
                            row_dates = create_mobilisation(
                                df = row_dates, 
                                mobilisation_date = min_values[0],
                                end_mobi = min_values[2],
                                event = 'mobilisation_merged', 
                                vessel = vess_group, 
                                oper_list = group, 
                                count_fail = oper_group_comments, 
                                concat = True
                                )
        
                        row_merged = pd.concat([row_merged,row_dates], axis=0, ignore_index=False)

                # If cannot start at the same day return the log_event rows
                if not merge:
                    row_merged = pd.concat([row_merged, selected_rows], axis=0, ignore_index=False)

                    if vess_group.mobilisation_time != 0:
                        for row in selected_rows.iterrows():
                            row_merged = create_mobilisation(
                                df = row_merged, 
                                mobilisation_date = row['d_trigger'],
                                end_mobi = row['d_end_wait_start'],
                                event = 'mobilisation', 
                                vessel = row['vessel_1'], 
                                oper_list = row['id'], 
                                count_fail = row['comments'], 
                                concat=True
                            )
                
            # If only one operation, do not merge
            else:
                row_merged = pd.concat([row_merged, selected_rows], axis=0, ignore_index=False)
            
        return row_merged
    

    ############### MAIN CODE ###############
    ############### MAIN CODE ###############
    ############### MAIN CODE ###############

    operation_already_merged = set()
    row_merged_imm = pd.DataFrame(columns=COLS)
    # Create the number_vessel files and the daily_vessel use file
    daily_vessel = df_vessel_merge_use(log_events = log_events_oper_imm, col_to_count = 'd_end_dur_net_port')
    daily_vessel = daily_vessel[daily_vessel['operations'].apply(lambda x: bool(x))]

    # Merge the operations for each day that operations are conducted
    for idx, day_oper in daily_vessel.iterrows():
        row_merged = merge_operation_row(
            log_events=log_events_oper_imm,
            day_oper=day_oper,
            vessels=vessels,
            time_between_devices=time_between_devices,
            grouped_operations=grouped_operations,
            oper_dict=oper_dict,
            COLS = COLS,
            operation_already_merged = operation_already_merged
        )

        if not row_merged.empty:
            row_merged_imm = pd.concat([row_merged_imm, row_merged], axis=0, ignore_index=False)

    return row_merged_imm
