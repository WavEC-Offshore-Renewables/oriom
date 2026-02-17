import pandas as pd
import logging
import os

from tqdm import tqdm

from oriom.classes.OperationTimeSeriesData import OperationTimeSeriesData

from oriom.core.timeseries_analysis import workability
from oriom.core.timeseries_analysis.startability import startability
from oriom.core.functions.operation_scheduler.meaningful_timesteps import get_meaningful_timesteps
from oriom.core.functions.operation_scheduler.define_operation import define_operation_values
from oriom.core.functions.operation_scheduler.reduce_distance_to_site import modify_distance
from oriom.core.timeseries_analysis.operation_managers.operation_recycler import recycle_major_other_oper_scheduler

try:
    from oriom.core.functions.private import check_files
except ImportError:
    check_files = None


def operation_tow_manager(
        operation_dir: str,
        df_metocean: pd.DataFrame,
        max_wait: float,
        operations_tow: list,
        timesteps: pd.DataFrame,
        Config: object,
        inputs_tseries: object,
        metocean_tow: dict = {}
    ):

    """ 
    Check if the operation_tow is already existing
    If it exist assign ts_data attribute to the OperationTow object
    If does not exist create the operation_schedule and assign it to the OperationTow object
    
    Args:
        operation_dir (string): Path of operation directory
        df_metocean (pd.Dataframe): Dataframe of timeseries weather data
        max_wait (float): Maximum wait of time between operations activities
        operations_tow (list): List of class `OperationTow`
        timesteps (pd.DataFrame): Timestep to consider in the analysis (not used)`
        Config (object): Object class `Config_run`
        inputs_tseries (object): Object class `Input.TimeSeries`  
        metocean_tow (dictionary, *Optional*): dictionary with key int value and value Metocean object of
            weather data for towing operations (metocean data of point from site to port). Default to {}
        
    Raise:
        InterruptedError: 'The operation can never occur. OLCs may be to resctric.'
    """
    i = -1
    for operation in tqdm(operations_tow, desc='Looping through Towing Operations.', position=0):
        logging.info('OperationTow: %s - %s.' % (operation.id, operation.name))
        op_dir = os.path.join(operation_dir, operation.id)
        i+=1

        # Check if there is already an operation_schedule file
        file_name_schedule = 'operation_schedule.csv'
        
        if check_files:
            file_exist = check_files.reuse_file_exist(
                op_dir = op_dir, 
                file_name_schedule = file_name_schedule, 
                operation = operation
            )
            if file_exist:
                continue
        
        transit_duration = modify_distance(
            Config = Config,
            operation = operation,
            default_distance = inputs_tseries.distance["value"]
        )

        # Create workability file considering various timestep
        if metocean_tow:
            df_workability = workability.workability_tow(
                df_metocean = df_metocean, 
                metocean_tow = metocean_tow, 
                operation = operation,
                op_dir = op_dir
            )

        # Consider only site metocean timeseries 
        else:
            df_workability = workability.workability(
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
                operations = operations_tow, 
                actual_oper = operation, 
                df_startability = df_startability,
                counter_op = i,
                operation_dir = operation_dir,
        )

        # Check when this operation will happen based on operation.months
        op_timesteps = get_meaningful_timesteps(
                timeseries=df_metocean,
                timesteps=timesteps
        )
        if len(op_timesteps) < 1 and len(operation.months) < 12:
            _w = 'The considered timeseries does not have timestamps '
            _w += 'for the months when this operation should take place'
            logging.info(_w)

        try:
            oper_sched = define_operation_values(
                            ts_analyse = op_timesteps,
                            operation = operation,
                            df_startability = df_startability,
                            MAX_WAIT = max_wait,
                            out_dir = os.path.join(op_dir, file_name_schedule)
            )

            operation.ts_data = OperationTimeSeriesData.create_timeseries_data(operation, oper_sched, op_dir)

        except InterruptedError as _e:
            if str(_e) != 'The operation can never occur. OLCs may be to resctric.':
                raise
            logging.error('Operation %s can never occur. OLCs may be to resctric.' % operation.id)
        logging.info('----------------------------------------------------')