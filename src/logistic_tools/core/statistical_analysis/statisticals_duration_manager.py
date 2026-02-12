import os
import logging
import pandas as pd

from logistic_tools.utils import aux_functions
from logistic_tools.core.statistical_analysis.operation_stats import operation_stats
from logistic_tools.utils.aux_functions import safe_getattr


def statistical_duration_manager(
    operation_dir: str,
    total_operations :list,
    inputs_stats: object
):
    """ 
    Create for each opeartion a statistical analysis for the duration from its operation_schedule
    
    Args:
        operation_dir (string): Path of operation directory
        df_metocean (pd.Dataframe): Dataframe of timeseries weather data
        total_operations (list): List of class 
            `CorrectiveMinor`, `CorrectiveMajorr`,  `InspectionSite`,  `InspectionPort`, `OperationTow`
        inputs_tseries (object): Object class `Input.TimeSeries`
    """
    
    # Initizalize a DataFrame to save operations sttistical analysis
    df_stat_analysis_duration = pd.DataFrame()

    # Create the statistical analysis file
    for percent in inputs_stats.percentiles["value"]:
        try:
            perc_max = max(percent, perc_max, 0)
        except NameError:
            perc_max = percent

        for op in total_operations:
            logging.info('Operation: %s - %s.' % (op.id, op.name))
            op_dir = os.path.join(operation_dir, op.id)
            oper_sched = safe_getattr(op, ['ts_data', 'oper_sched'], False)
            if isinstance(oper_sched, pd.DataFrame) and not oper_sched.empty:
                df_stat_analysis_duration = operation_stats(
                        df_operation_schedule = oper_sched,
                        percentile = percent,
                )
                df_stat_analysis_duration.loc[:, 'operation_id'] = op.id

                aux_functions.save_file_csv(df_stat_analysis_duration, op_dir,'statistical_analysis_P' + str(percent) + '.csv')

            else:
                logging.warning(f'Could not find a timeseries analysis for {op.id} operation.')
            logging.info('----------------------------------------------------')

    inputs_stats.percentile_max = {"value": int(perc_max), "units": None}
