import pandas as pd
import logging
import os

from tqdm import tqdm

from oriom.utils import yaml_manager
from oriom.common.constants import ATTRIBUTE_LIST_REUSE_INSPECTION
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


def inspect_site_manager(
    operation_dir: str,
    df_metocean: pd.DataFrame,
    operations_inspect_site: list,
    inputs_tseries: object,
    Config: object
):
    """
    Check if the operations_inspect_site is already existing
    If it exist assign ts_data attribute to the InspectSite object and pass to other inp
    If exist a similar inspection with all ATTRIBUTE_LIST_REUSE equal assign ts_data and pass to other inp
    If does not exist create the operation_schedule and assign it to the OperationTow object

    Args:
        operation_dir (string): Path of operation directory
        df_metocean (pd.Dataframe): Dataframe of timeseries weather data
        max_wait (float): Maximum wait of time between operations activities
        operations_inspect_site (list): List of class `InspectionSite`
        inputs_tseries (object): Object class `Input.TimeSeries`
        Config (object): Object class `Config_run`

    Raise:
        InterruptedError: 'The operation can never occur. OLCs may be to resctric.'
    """

    dict_insp_oper, hash_to_key_insp = {}, {}

    for operation in tqdm(operations_inspect_site, desc='Looping through Inspections at Site.', position=0):
        logging.info('InspectionSite: %s - %s.' % (operation.id, operation.name))

        # Check if is possible to recicle a similar inspection
        similar_inspection_id = recycle_other_oper_scheduler(
            dict_insp_oper,
            hash_to_key_insp,
            operation,
            ATTRIBUTE_LIST_REUSE_INSPECTION
        )

        op_dir_other = os.path.join(operation_dir, similar_inspection_id)
        op_dir = os.path.join(operation_dir, operation.id)
        file_name_schedule = 'operation_schedule.csv'

        if check_files:
            # Check if there is a file to reuse
            file_exist = check_files.reuse_file_exist(
                op_dir = op_dir,
                file_name_schedule = file_name_schedule,
                operation = operation,
                similar_inspection_id = similar_inspection_id,
                op_dir_other = op_dir_other,
                shift_op = True
            )

            if file_exist:
                continue

        transit_duration = modify_distance(
            Config = Config,
            operation = operation,
            default_distance = inputs_tseries.distance["value"]
        )

        # Get how many working shifts are required to preform this operation
        time_between_devices = inputs_tseries.find_time_between_devices(operation_obj_id = operation.id)

        op_working_shifts, data_working_shifts = working_shifts(
                operation=operation,
                duration_shift=inputs_tseries.shift_duration["value"],
                transit=transit_duration,
                transit_between_devices=time_between_devices,
                operation_to_group_with=operation.to_group_with
        )

        # Add attribute of shift to inspection_site
        operation.assign_shift_attributes(op_working_shifts)

        # Update operation attributes.yaml file
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
            data_key='working_shifts',
            operation_id=operation.id
        )

        # Devices shutdown duration
        shutdown_wtg = operation.dur_per_device * operation.intervened_wtg if operation.device_shutdown else 0
        shutdown_wec = operation.dur_per_device * operation.intervened_wec if operation.device_shutdown else 0
        shutdown_pv = operation.dur_per_device * operation.intervened_pv if operation.device_shutdown else 0

        # Schedule this(ese) operation(s) throughout the timeseries
        # As before. The operation workability is its workability
        df_workability = workability(
                operation = operation,
                df_metocean = df_metocean,
                out_dir = op_dir
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
                duration_shift = inputs_tseries.shift_duration["value"],
                out_dir = os.path.join(op_dir, file_name_schedule)
            )

            operation.ts_data = OperationTimeSeriesData.create_timeseries_data(operation, oper_sched, op_dir)

        except InterruptedError as _e:
            if str(_e) != 'The operation can never occur. OLCs may be to resctric.':
                raise
            logging.error('Operation %s can never occur. OLCs may be to resctric.' % operation.id)
