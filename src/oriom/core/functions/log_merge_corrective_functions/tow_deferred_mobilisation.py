from copy import deepcopy
import pandas as pd

from oriom.core.functions.logs_timeseries.logs_timeseries_func import create_mobilisation


def tow_deferred_mobi(
        COLS: list, 
        log_events_tow_def: pd.DataFrame,
        find_element_class: object
):
    """ 
    Create one mobilisation for deferred tow each campaign

    Args:
        log_events_def  (pd.DataFrame): Dataframe with the deferred corrective log events.
        COLS (:obj:`list`): List of the column name for the log_events file.
        find_element_class (Find_element_class): Initialized instance that provides fast access to operations, vessels and failures via internal dictionaries.

    Returns
        pd.DataFrame: dataframe of mobilisation
    """
    
    row_merged_def_tow = pd.DataFrame(columns=COLS) 

    log_events_tow_deferred = deepcopy(log_events_tow_def)
    log_events_tow_deferred['year_month'] = log_events_tow_deferred['d_trigger'].dt.to_period('M')
    # Regroup for year_month
    for period, df_group in log_events_tow_deferred.groupby('year_month'):
        df_ops = df_group[df_group['id'].str.contains('removal', na=False)]
        vessels_tow = list(df_ops['vessel_1'])
        vessels_tow = set(vessels_tow)

        for vessel_id in vessels_tow:
            vessel = find_element_class.find_vessel(vessel_id)
            operation_number_analysed = 0  

            if vessel.mobilisation_time != 0:
                for op_id, op_row in df_ops.groupby('id'):
                    count_fail = op_row['comments'].iloc[0].split("_", 1)[1]

                    if operation_number_analysed == 0:
                        for _ in range(0, op_row['n_vessel_1'].iloc[0]):
                            mobilisation_date = op_row['d_trigger'].iloc[0]
                            row_merged_def_tow = create_mobilisation(
                                df = row_merged_def_tow,
                                mobilisation_date = mobilisation_date,
                                end_mobi = op_row['d_end_wait_start'].iloc[0],
                                event = 'mobilisation_merged',
                                vessel = vessel,
                                oper_list = [op_id],
                                count_fail = count_fail
                            )
                        operation_number_analysed += 1

    return row_merged_def_tow