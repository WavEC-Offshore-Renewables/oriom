import pandas as pd
import logging
import os

from tqdm import tqdm

from oriom.classes.OperationTimeSeriesData import OperationTimeSeriesData

from oriom.core.timeseries_analysis.workability import workability
from oriom.core.timeseries_analysis.startability import startability
from oriom.core.functions.operation_scheduler.reduce_distance_to_site import modify_distance
from oriom.core.functions.operation_scheduler.meaningful_timesteps import get_meaningful_timesteps
from oriom.core.functions.operation_scheduler.define_operation import define_operation_values
from oriom.core.timeseries_analysis.operation_managers.operation_recycler import recycle_major_other_oper_scheduler

try:
    from oriom.core.functions.private import check_files
except ImportError:
    check_files = None


def operation_major_manager(
    operation_dir: str,
    df_metocean: pd.DataFrame,
    operations_corr_major: list,
    Config: object,
    inputs_tseries: object,
    timesteps: pd.DataFrame
):
    """ 
    Check if the operations_inspect_site is already existing
    If it exist assign ts_data attribute to the InspectSite object and pass to other inp
    If exist a similar inspection with all ATTRIBUTE_LIST_REUSE equal assign ts_data and pass to other inp
    If does not exist create the operation_schedule and assign it to the CorrectiveMajor object
    
    Args:
        operation_dir (string): Path of operation directory
        df_metocean (pd.Dataframe): Dataframe of timeseries weather data
        operations_corr_major (list): List of class `CorrectiveMajor`
        Config (object): Object class `Config_run`
        inputs_tseries (object): Object class `Input.TimeSeries`      
        timesteps (pd.DataFrame): Timestep to consider in the analysis (not used)


    Raise:
        InterruptedError: 'The operation can never occur. OLCs may be to resctric.'

    """
    i = -1
    for operation in tqdm(operations_corr_major, desc='Looping through Major Corrective Operations.', position=0):
        logging.info('CorrectiveMajor: %s - %s.' % (operation.id, operation.name))
        op_dir = os.path.join(operation_dir, operation.id)
        i+=1

        # Check if there is already an operation_schedule file
        if check_files:
            if check_files.check_file_exists(path=op_dir, file_name='operation_schedule.csv'):
                operation.ts_data = OperationTimeSeriesData.create_timeseries_data(operation, 'operation_schedule.csv', op_dir)
                continue

        _ = modify_distance(            
            Config = Config,
            operation = operation,
            default_distance = inputs_tseries.distance["value"]
        )

        df_workability = workability(
                activities=operation.activities,
                df_metocean=df_metocean,
                out_dir=op_dir
        )
        df_startability = startability(
                activities=operation.activities,
                df_workability=df_workability,
                out_dir=op_dir
        )
        
        # Check if exist a operation scheduler equal that can be recicled for the operation under analysis
        file_exist = recycle_major_other_oper_scheduler(
                operations = operations_corr_major, 
                actual_oper = operation, 
                df_startability = df_startability,
                counter_op = i,
                operation_dir = operation_dir,
        )
        
        if file_exist:
            continue

        op_timesteps = get_meaningful_timesteps(timeseries = df_metocean, timesteps = timesteps)

        if len(op_timesteps) < 1 and len(operation.months) < 12:
            _w = 'The considered timeseries does not have timestamps '
            _w += 'for the months when this operation should take place'
            logging.info(_w)

        try:
            oper_sched = define_operation_values(
                    ts_analyse=op_timesteps,
                    operation=operation,
                    df_startability=df_startability,
                    MAX_WAIT=inputs_tseries.max_wait["value"],
                    out_dir=os.path.join(op_dir, 'operation_schedule.csv')
            )

            operation.ts_data = OperationTimeSeriesData.create_timeseries_data(operation, oper_sched, op_dir)

        except InterruptedError as _e:
            if str(_e) != 'The operation can never occur. OLCs may be to resctric.':
                raise
            logging.error('Operation %s can never occur. OLCs may be to resctric.' % operation.id)

        logging.info('----------------------------------------------------')