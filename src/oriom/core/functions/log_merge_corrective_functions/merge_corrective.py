import pandas as pd
from copy import deepcopy

from oriom.classes.TowData import TowData
from oriom.core.functions.log_merge_corrective_functions.OperationDeferredPortOrganizer import OperationDeferredPortCreation
from oriom.core.functions.log_merge_corrective_functions import merged_deferred_aux
from oriom.core.functions.log_merge_corrective_functions.merge_corrective_deferred import merge_deferred_operations
from oriom.core.functions.log_merge_corrective_functions.merge_corrective_immediate import merge_operation
from oriom.core.functions.log_merge_corrective_functions.group_merging_immediate import mergeble_operation


FILTER_EVENT = ['failure', 'inspection_site', 'inspection_port']
OLC_LIST = ['hs', 'cs', 'ws', 'ws_hub', 'tp', 'light']
COLS = [
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
    'comments',
    'shutdown',
    'ST_contract_1',
    'ST_contract_2',
]


def filter_tow_op(log_events: pd.DataFrame, comments_failure_id_tow: pd.Series, list_fail: list, recom: bool = False):
    """ Filter log_events file related to the towing operation"""
    if list_fail:
        comments_tow = set(comments_failure_id_tow[comments_failure_id_tow.isin(list_fail)])
        pattern_tow = "|".join(comments_tow)
        l_events_tow = log_events[log_events["comments"].str.contains(pattern_tow, case=False, na=False)]
        return l_events_tow, comments_tow
    else:
        return pd.DataFrame(), []


def comment_filtering(log_event_op):
    """ Extrapolate comments for failures"""
    if not log_event_op.empty:
        comments_failure_id = log_event_op['comments'].str.split('_', n=1, expand=True)[1].fillna('')
    else:
        comments_failure_id = pd.DataFrame()

    return comments_failure_id


def create_logs_merge(
    log_events_original: pd.DataFrame,
    failures: list,
    operation_log_file_stats: list,
    result_dir_r: str,
    vessels: list,
    find_element_class,
    time_between_devices: dict,
    percentile: float,
    vessel_to_merge: list,
    time_fail_op_immediately: float,
    duration_shift: float
)->pd.DataFrame:

    """
    This function it runs after that the log_event file is created. It will merge only CORERCTIVE operations that can be conducted
    together considering the OLC.
    Merge dividing the DEFERRED OPERATION and the IMMEDIATE OPERATION.
    It use the number_ves function to obtain the number of vessels out
    For each day it check if another operation is made and analyze the share of vessel is possible
    Only merge the operation conducted with the specific_vessel. Merge only operation that do not require a tow to port and do not use an ROV
    On id save the index and operation merged taken from the log_event file, on comment show the failure correted

    Args:
        log_events (:obj:`pd.DataFrame`): Log of all the events (failure,operation, inspection_port, inspection_site).
        failures (:obj:`list`): List of objects :class:`failures`
        operation_log_file_stats (:obj:`list`): List of objectts :class:`OperationsCorrectiveStat` + `OperationsTowStat`.
        result_dir_r (:obj;`str`): Directory of results files
        vessels (:obj:`list`): List of objects :class:`Vessel`
        find_element_class (Find_element_class): Initialized instance that provides fast access to operations, vessels and failures via internal dictionaries.
        time_between_devices (:obj:`dict`): Dictionary of time between devices for the various tech
        percentile (:obj:`float`, *optional*): Percentile value to calculate the statistic for inspection_port. Default to 0.9
        vessel_to_merge (:obj;`list`): list of vessel that are considered for the immediate merge
        time_fail_op_immediately (:obj:`float`): Time between failure and immediate operations.
        duration_shift (:obj:`float`): Maximum hours of working shift.

    Raises:
        ValueError: "preferred_months" in a inspection of periodicity lower than 1 year
            should be at least as many times as the occurences per year.

    Returns:
        pd.DataFrame: dataframe with all the events of the farm with corrective operation merged.

    """

    def open_oper_schedule(oper, operation_scheduler_dict):
        """
        Open the file operation_schedule of the operation under analysis append it on a dictionary with key as the operation name


        Args:
            oper (:obj:`object`): The operation object to be analyzed.
        Returns:
            dict: A dictionary with the operation id as key and a list of the operation schedule and the last valid index as value.
        """
        operation_scheduler_dict[oper.id] = [oper.ts_data.oper_sched]
        operation_scheduler_dict[oper.id].append(oper.ts_data.last_valid_index)
        return operation_scheduler_dict

    def op_to_dict(oper, OLC_LIST, oper_dict):
        """
        Create a dictionary of the operations to merge with their values only if they:
         - do not require tow to port
         - do not require a use of drone
         - are immediate operations
         - are vessel_to_merge
        """

        def olc_act(op, activity, olc):
            """
            Function to obtain olc values from the operations. None Values are converted with 100 (high number)

            Args:
                op (:obj:`object`): The operation object to be analyzed.
                activity (:obj:`object`): The activity object to be analyzed.
                olc (:obj:`str`): The OLC to be analyzed.
            Returns:
                float: The value of the OLC, or 100 if it is None or 0.
            """

            try:
                if olc == 'light':
                    luce = float(getattr(op, olc, None))
                    if luce == 0:
                        luce = 100
                    return luce if luce else 100
                else:
                    attr = getattr(op, olc, None)
                    attr_int = float(attr)
                    return attr_int
            except (ValueError, TypeError, AttributeError):
                try:
                    if olc == 'light':
                        luce = float(getattr(activity, olc, None))
                        if luce == 0:
                            luce = 100
                        return luce if luce else 100
                    else:
                        attr = getattr(activity, olc, None)
                        attr_int = float(attr)
                        return attr_int
                except (ValueError, TypeError, AttributeError):
                        return 100

        op = oper.id
        duration = oper.ts_data.dur_net_site

        tech_required = getattr(oper, 'tech_required', None)
        tech_cost = getattr(oper, 'tech_cost', None)

        oper_dict[op] = {
            'vess_1': getattr(oper, 'vessel1_id', None),
            'vess_2': getattr(oper, 'vessel2_id', None),
            'duration': duration if duration is not None else getattr(oper, 'duration_net', None),
            'technician': tech_required,
            'technician_cost': (tech_required or 0) * (tech_cost or 0)
        }

        for olc in OLC_LIST:
            try:
                olc_value = [olc_act(oper, activity, olc) for activity in oper.activities]
                olc_value = [v for v in olc_value if v is not None]
            except AttributeError:
                olc_value = [(olc_act(oper, 'activity', olc))]
            if olc_value:
                minor_olc = min(olc_value)
                oper_dict[op][olc] = minor_olc

        return oper_dict
    

    #-------------------------------------------------
    # CODE
    #-------------------------------------------------

    log_events = deepcopy(log_events_original)
    log_events['ST_contract_1'] = False
    log_events['ST_contract_2'] = False
    log_events_merged = pd.DataFrame(columns=log_events.columns)
    df_port_operation_def_log, df_events_return = pd.DataFrame(),  pd.DataFrame()
    deferred_failures_correction, deferred_failures_correction_tow, failures_correction_tow, index_overwrite_log_ev = [], [], [], []
    oper_per_vessel, oper_dict, operation_scheduler_dict, oper_dict_tow = {}, {}, {}, {}


    # ALL OTHER LOG
    #------------------
    # Copy all log_files that is not going to be merged
    log_mobilisation = log_events[log_events['event'] == 'mobilisation']
    log_event_filt = log_events.loc[log_events['event'].isin(FILTER_EVENT)]
    log_event_to_merge = log_events.loc[~log_events['event'].isin(FILTER_EVENT)]

    log_events_merged = pd.concat([log_events_merged, log_event_filt],ignore_index=True)

    # Deferred operation merging, create a dict with 1st key vessel used and value deferred operation
    merged_deferred_aux.creation_oper_vessel_dict(
        log_events = log_events,
        failures = failures,
        find_element_class = find_element_class,
        oper_per_vessel = oper_per_vessel,
        deferred_failures_correction = deferred_failures_correction,
        deferred_failures_correction_tow = deferred_failures_correction_tow,
        failures_correction_tow = failures_correction_tow
    )

    #------------------
    # TOW OPERATION DEFERRED
    #------------------
    log_event_tow = log_event_to_merge.loc[log_event_to_merge['event'] == 'tow']

    if not log_event_tow.empty:
        comments_failure_id_tow = comment_filtering(log_event_tow)
        log_events_tow_def, deferred_comments_tow = filter_tow_op(
            log_events = log_event_tow, 
            comments_failure_id_tow = comments_failure_id_tow, 
            list_fail = deferred_failures_correction_tow
        )
        log_events_tow_imm = log_event_to_merge.loc[
            log_events['comments'].str.split('_', n=1, expand=True)[1].fillna('').isin(failures_correction_tow)
        ]

        # DEFERRED TOW
        #------------------
        if not log_events_tow_def.empty and deferred_comments_tow:
            # Create unique set of deferred tow failure
            unique_failures = {f.split('.')[0] for f in deferred_comments_tow}
            oper_port_dict = {}
            # fill oper_port tow data attributes
            for failure_id in unique_failures:
                failure = find_element_class.find_failure_from_id(failure_id)
                oper_port = find_element_class.find_operation(failure.operation_triggered)
                oper_port_dict[oper_port.id] = oper_port
                oper_port.tow_data = TowData.from_operation(find_element_class, oper_port)
                oper_port.tow_data.id_dict_oper(oper_dict_tow, oper_port)

            oper_ids_tow = set(oper_dict_tow.keys())

            # Take all events that regard a tow deferred (TOW, OP & RECOMMISSIONING events)
            log_events_tow_def = log_events.loc[
                (log_events['id'].isin(oper_ids_tow)) &
                (log_events['comments'].str.split('_', n=1, expand=True)[1].fillna('').isin(deferred_comments_tow))
            ]
            index_overwrite_log_ev = log_events_tow_def.index.tolist()
            log_events_tow_def = merged_deferred_aux.manage_recommissioning(log_events_tow_def)

            port_operation_deferred = OperationDeferredPortCreation(
                log_events_tow_def,
                oper_port_dict,
                oper_dict_tow,
                find_element_class
            )
            df_port_operation_def_log = port_operation_deferred.deferred_port_manager(
                time_fail_op_immediately = time_fail_op_immediately
            )
            df_port_operation_def_log.reset_index(drop=True, inplace=True)
            df_events_return = deepcopy(df_port_operation_def_log.drop(columns=['year_month']))
            df_port_operation_def_log = merged_deferred_aux.manage_recommissioning(df_port_operation_def_log, True)
            df_port_operation_def_log = merged_deferred_aux.manage_chart(
                df = df_port_operation_def_log,
                vessels = vessels,
                percentile = percentile
            )
            log_events_merged = pd.concat([log_events_merged, df_port_operation_def_log], ignore_index=False)

        # IMMEDIATE TOW
        #------------------
        if not log_events_tow_imm.empty:
            # Simply copy all events that regard a tow immediate (TOW, OP & RECOMMISSIONING events)
            log_events_merged = pd.concat([log_events_merged, log_events_tow_imm], ignore_index=False)

    #------------------
    # DEFERRED OPERATION
    #------------------
    # Filter log_events by the failure that require deferred intervention (failure extrapolated from 'comments' column)
    log_event_op = log_event_to_merge.loc[
        (~log_event_to_merge['id'].isin(set(oper_dict_tow.keys())))
    ]
    comments_failure_id = comment_filtering(log_event_op)

    log_events_def = log_event_op[comments_failure_id.isin(deferred_failures_correction)]

    if not log_events_def.empty:
        log_events_merged_def = merge_deferred_operations(
            log_events_def = log_events_def,
            vessels = vessels,
            time_between_devices = time_between_devices,
            oper_per_vessel = oper_per_vessel,
            time_fail_op_immediately = time_fail_op_immediately,
            percentile = percentile,
            COLS = COLS,
            find_element_class = find_element_class,
            duration_shift = duration_shift
        )
        log_events_merged = pd.concat([log_events_merged, log_events_merged_def],ignore_index=False)

    #------------------
    # IMMEDIATE OPERATION
    #------------------
    # From only that comply a tow filter avoiding deferred failures and tow failures
    failure_avoid = deferred_failures_correction + failures_correction_tow + deferred_failures_correction_tow
    mask = (
        (log_event_to_merge['event'].isin(['operation'])) &
        (~comments_failure_id.isin(failure_avoid))
    )
    log_events_oper_imm = log_event_to_merge[mask]

    if not log_events_oper_imm.empty:
        if vessel_to_merge:
            # Create oper_dict (list of operations and OLC to evaluate merging corrective groups)
            for oper_stat in operation_log_file_stats:
                # Analyze only operations that do not require a ROV, TOW to port or specific (deferred) month
                oper = oper_stat.op_class
                failure_id = getattr(getattr(oper, 'failure', None), 'id', None)
                if (
                    oper.vessel1.id in vessel_to_merge
                    and not getattr(oper, 'rov_drone', False)
                    and not getattr(oper, 'tow_to_port', False)
                    and not getattr(oper, 'tow_operation', False)
                    and (failure_id is None or failure_id not in deferred_failures_correction)
                ):
                    oper_dict = op_to_dict(oper, OLC_LIST, oper_dict)
                    operation_scheduler_dict = open_oper_schedule(oper, operation_scheduler_dict)

            # Create the groups of mergeble operations
            grouped_operations = mergeble_operation(oper_dict, result_dir_r, OLC_LIST)

            # Separate the log_event file to merge and to copy (not to merge)
            keys_dict_oper = set(oper_dict.keys())
            log_events_to_merge = log_events_oper_imm[log_events_oper_imm['id'].isin(keys_dict_oper)]
            log_events_not_to_merge = log_events_oper_imm[~log_events_oper_imm['id'].isin(keys_dict_oper)]

            if not log_mobilisation.empty:
                log_mobilisation['_suffix'] = log_mobilisation['id'].str.split('_', n=1).str[1]

            if not log_events_to_merge.empty:
                # Merge immediate corrective operations
                log_events_merged_immediate, log_mobilisation = merge_operation(
                    log_events_oper_imm=log_events_to_merge,
                    log_mobilisation = log_mobilisation,
                    vessels=vessels,
                    find_element_class=find_element_class,
                    time_between_devices=time_between_devices,
                    grouped_operations=grouped_operations,
                    oper_dict=oper_dict,
                    COLS = COLS
                )

                log_events_merged = pd.concat([log_events_merged, log_events_merged_immediate],ignore_index=False)

            if not log_mobilisation.empty:
                log_mobilisation = log_mobilisation.drop(columns=['_suffix'])

            # copy non mergeble operations
            if not log_events_not_to_merge.empty:
                log_events_merged = pd.concat([log_events_merged, log_events_not_to_merge],ignore_index=False)
        else:
            log_events_merged = pd.concat([log_events_merged, log_events_oper_imm],ignore_index=False)

    if not log_mobilisation.empty:
        log_events_merged = pd.concat([log_events_merged, log_mobilisation],ignore_index=False)
    
    log_events_merged = merged_deferred_aux.manage_recommissioning(log_events_merged)
    log_events_merged = log_events_merged.sort_values(by='d_trigger').reset_index(drop=True)

    return log_events_merged, index_overwrite_log_ev, df_events_return


if __name__ == '__main__':
    pass