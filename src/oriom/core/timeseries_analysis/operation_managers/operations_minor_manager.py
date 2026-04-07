import logging
import os
import numpy as np
import pandas as pd

from tqdm import tqdm

from oriom.utils import yaml_manager
from oriom.utils import aux_functions

from oriom.classes.OperationTimeSeriesData import OperationTimeSeriesData

from oriom.core.timeseries_analysis.working_shifts import working_shifts
from oriom.core.timeseries_analysis.workability import workability
from oriom.core.functions.operation_scheduler.define_shift_operation import define_shift_operation_values
from oriom.core.functions.operation_scheduler.reduce_distance_to_site import modify_distance
from oriom.core.timeseries_analysis.operation_managers.operation_recycler import recycle_other_oper_scheduler

try:
    from oriom.core.functions.private import check_files
except ImportError:
    check_files = None


def opeartion_minor_manager(
    operation_dir: str,
    df_metocean: pd.DataFrame,
    operations_corr_minor: list,
    inputs_tseries: object,
    Config: object
):
    """
    Check if the operations_inspect_site is already existing
    If it exist assign ts_data attribute to the InspectSite object and pass to other inp
    If exist a similar inspection with all ATTRIBUTE_LIST_REUSE equal assign ts_data and pass to other inp
    If does not exist create the operation_schedule and assign it to the CorrectiveMinor object

    Args:
        operation_dir (string): Path of operation directory
        df_metocean (pd.Dataframe): Dataframe of timeseries weather data
        operations_corr_minor (list): List of class `CorrectiveMinor`
        inputs_tseries (object): Object class `Input.TimeSeries`
        Config (object): Object class `Config_run`

    Raise:
        InterruptedError: 'The operation can never occur. OLCs may be to resctric.'
        RuntimeError: 'operation too long, consider defining as CorrectiveMajor'
    """

    dict_minor_oper, hash_to_key = {}, {}
    ATTRIBUTE_LIST = ['duration_net', 'hs', 'tp', 'ws', 'ws_hub', 'cs', 'light', 'vessel1_id', 'vessel2_id', 'shutdown', 'technology', 'rov']

    for operation in tqdm(operations_corr_minor, desc='Looping through Minor Corrective Operations.', position=0):
        logging.info('CorrectiveMinor: %s - %s.' % (operation.id, operation.name))

        # Check if there is an equivalent operation_schedule already calculated for another operation
        similar_operation_id = recycle_other_oper_scheduler(
            minor_oper_dict = dict_minor_oper,
            hash_to_key = hash_to_key,
            operation = operation,
            attribute_list = ATTRIBUTE_LIST
        )

        op_dir_other = os.path.join(operation_dir, similar_operation_id)
        op_dir = os.path.join(operation_dir, operation.id)

        if check_files:
            file_exist = check_files.reuse_file_exist(
                op_dir = op_dir,
                file_name_schedule = 'operation_schedule.csv',
                operation = operation,
                similar_inspection_id = similar_operation_id,
                op_dir_other = op_dir_other,
            )

            if file_exist:
                continue

        transit_duration = modify_distance(
            Config = Config,
            operation = operation,
            default_distance = inputs_tseries.distance["value"]
        )

        shutdown_wtg = shutdown_wec = shutdown_pv = np.nan

        # Get how many working shifts are required to preform this operation
        if operation.device_shutdown:
            if 'opv' in operation.id:
                shutdown_pv = operation.duration_net
            elif 'ofw' in operation.id:
                shutdown_wtg = operation.duration_net
            elif 'owc' in operation.id:
                shutdown_wec = operation.duration_net

        time_between_devices = inputs_tseries.find_time_between_devices(operation_obj_id = operation.id)

        op_working_shifts, data_working_shifts = working_shifts(
            operation=operation,
            duration_shift=inputs_tseries.shift_duration["value"],
            transit=transit_duration,
            transit_between_devices=time_between_devices,
            operation_to_group_with=None,
            minor_op = True
        )

        # Check if the operation require more than a shift. If yes, means this corrective operation
        # is taking more than it should and maybe it should be considered
        # as a Major Corrective opertaion
        if op_working_shifts['number_shifts_last'] + op_working_shifts['number_shifts_main']> 1:
            _e = 'operation too long, consider defining as CorrectiveMajor '
            raise RuntimeError('CorrectiveMinor:' +_e + '%s - %s.' % (operation.id, operation.name))

        df_workability = workability(
                operation = operation,
                df_metocean = df_metocean,
                out_dir = op_dir
        )

        yaml_manager.update_yaml_each_attribute(
            file_dir=op_dir,
            file_name='attributes.yaml',
            data=op_working_shifts,
            operation_id=operation.id
        )
        yaml_manager.update_yaml(
                file_dir=op_dir,
                file_name='attributes.yaml',
                data=data_working_shifts,
                operation_id=operation.id
        )

        try:
            oper_sched = define_shift_operation_values(
                    df_metocean = df_metocean,
                    operation = operation,
                    df_workability = df_workability,
                    shift_data = op_working_shifts,
                    transit_duration = transit_duration,
                    shutdown_wtg = shutdown_wtg,
                    shutdown_wec = shutdown_wec,
                    shutdown_pv = shutdown_pv,
                    out_dir = os.path.join(op_dir, 'operation_schedule.csv')
            )
            oper_sched = aux_functions.convert_stringtime(oper_sched)

            operation.ts_data = OperationTimeSeriesData.create_timeseries_data(operation, oper_sched, op_dir)

        except InterruptedError as _e:
            if str(_e) != 'The operation can never occur. OLCs may be to resctric.':
                raise
            logging.error('Operation %s can never occur. OLCs may be to resctric.' % operation.id)
        logging.info('----------------------------------------------------')