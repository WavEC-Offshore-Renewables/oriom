import pandas as pd
import logging
import os

from tqdm import tqdm

from oriom.utils import yaml_manager

from oriom.domain.OperationTimeSeriesData import OperationTimeSeriesData

from oriom.core.timeseries_analysis.workability import workability
from oriom.core.functions.operation_scheduler.define_shift_operation import define_shift_operation_values

try:
    from oriom.core.functions.private import check_files
except ImportError:
    check_files = None


def creation_data_working_shift_port(
    operation: object,
    shift_duration: float
)->dict:
    """
    Create a dictionary with the main and last shift details

    Args:
        operation (object): Object of the class OperationTow
        shift_duration (float): duration of the working shift

    Return:
        dict: Dictionary of the working shift at port
    """

    n_devices = 1

    # Get how many working shifts are required to preform this operation
    total_hours = n_devices * operation.dur_per_device
    n_shifts = total_hours / shift_duration
    number_shifts_main, h = divmod(n_shifts, 1)

    duration_shifts_main = shift_duration if number_shifts_main != 0 else 0
    number_shifts_last = 1 if h != 0 else 0
    duration_shifts_last = round(h * duration_shifts_main, 1) if h != 0 else 0

    data_working_shifts_port = {
        "number_shifts_main": int(number_shifts_main),
        "number_shifts_last": int(number_shifts_last),
        "duration_shift_main": duration_shifts_main,
        "duration_shift_last": duration_shifts_last,
    }

    return data_working_shifts_port


def operation_inspect_port_manager(
    operation_dir: str,
    df_metocean: pd.DataFrame,
    duration_shift: float,
    operations_inspect_port: list,
):
    """
    Check if the operations_inspect_site is already existing
    If it exist assign ts_data attribute to the InspectPort object and pass to other inp
    If exist a similar inspection with all ATTRIBUTE_LIST_REUSE equal assign ts_data and pass to other inp
    If does not exist create the operation_schedule and assign it to the OperationTow object

    Args:
        operation_dir (string): Path of operation directory
        df_metocean (pd.Dataframe): Dataframe of timeseries weather data
        duration_shift (float): Duration of one working shift
        operations_inspect_port (list): List of class `InspectionPort`

    Raise:
        InterruptedError: 'The operation can never occur. OLCs may be to resctric.'

    """

    for operation in tqdm(operations_inspect_port, desc='Looping through Inspections at Port.', position=0):
        logging.info('InspectionPort: %s - %s.' % (operation.id, operation.name))
        op_dir = os.path.join(operation_dir, operation.id)
        operation.insp_port_dir = op_dir

        # For the inspections at port, the timeseries analysis is done for a single device

        data_working_shifts_port = creation_data_working_shift_port(
            operation = operation,
            shift_duration = duration_shift
        )

        # Check if there is already an operation_schedule file
        file_name_schedule = 'operation_schedule.csv'

        if check_files:
            file_exist = check_files.reuse_file_exist(
                op_dir = op_dir,
                file_name_schedule = file_name_schedule,
                operation = operation,
                shift_op = True
            )
            logging.info(f'file {file_name_schedule} reused, {operation.id}')


            if file_exist:
                file_name_schedule = 'towing_inspection_log.csv'
                file_exist = check_files.reuse_file_exist(
                    op_dir = op_dir,
                    file_name_schedule = file_name_schedule,
                    operation = operation,
                    shift_op = True,
                    tow_log_op = True
                )
                logging.info(f'file {file_name_schedule} reused {operation.id}')
                continue

        df_workability = workability(
                operation=operation,
                df_metocean=df_metocean,
                out_dir=op_dir
        )

        # Devices shutdown duration
        if operation.id[0:3] == 'ofw':
            shutdown_wtg = operation.dur_per_device * operation.intervened_devices
        else:
            shutdown_wtg=0
        if operation.id[0:3] == 'owc':
            shutdown_wec = operation.dur_per_device * operation.intervened_devices
        else:
            shutdown_wec=0
        if operation.id[0:3] == 'opv':
            shutdown_pv = operation.dur_per_device * operation.intervened_devices
        else:
            shutdown_pv=0

        # Update operation attributes.yaml file
        data_new = {
            "shift": {
                "number": data_working_shifts_port["number_shifts_main"],
                "duration": data_working_shifts_port["duration_shift_main"]
            },
            "last_shift": {
                "number": data_working_shifts_port["number_shifts_last"],
                "duration": data_working_shifts_port["duration_shift_last"]
            }
        }

        # Add attribute of shift to inspection_site
        operation.assign_shift_attributes(data_working_shifts_port)
        # Update operation attributes.yaml file
        yaml_manager.update_yaml_each_attribute(file_dir=op_dir,file_name='attributes.yaml',data=data_working_shifts_port)
        yaml_manager.update_yaml(
                file_dir=op_dir,
                file_name='attributes.yaml',
                data=data_new,
                data_key='working_shifts'
        )

        try:
            oper_sched = define_shift_operation_values(
                    df_metocean = df_metocean,
                    operation = operation,
                    df_workability = df_workability,
                    shift_data = data_working_shifts_port,
                    transit_duration = 0,
                    shutdown_wtg = shutdown_wtg,
                    shutdown_wec = shutdown_wec,
                    shutdown_pv = shutdown_pv,
                    out_dir = os.path.join(op_dir, file_name_schedule)
            )

            operation.ts_data = OperationTimeSeriesData.create_timeseries_data(operation, oper_sched, op_dir)

        except InterruptedError as _e:
            if str(_e) != 'The operation can never occur. OLCs may be to resctric.':
                raise
            logging.error('Operation %s can never occur. OLCs may be to resctric.' % operation.id)
        logging.info('----------------------------------------------------')