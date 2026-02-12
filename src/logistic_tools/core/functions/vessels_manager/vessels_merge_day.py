import pandas as pd
from copy import deepcopy
import math as mt


def vessel_day_func(
        n_ves: pd.DataFrame,
    ):

    """
    This function take the vessel file and evaluate the maximum amount of each vessel that we have each day 
    showing all the operations made per day as dict where key = idx of log_event and value is oper.id.
    
    Arguments:
        n_ves: {pd.DataFrame} Dataframe of hourly vessel used

    Returns:
        {pd.DataFrame}
    """

    def combine_operations(row):
        combined_operations = {}
        for col in operation_columns:
            if isinstance(row[col], dict):
                combined_operations.update(row[col])  
        
        return combined_operations

    n_ves['date'] = pd.to_datetime(n_ves['date']).dt.date  
    daily_vessel = pd.DataFrame(index=pd.to_datetime(n_ves['date'].unique()))  

    # Identify vessel columns
    v_columns = [col for col in n_ves.columns if col.startswith('v')]

    for vessel in v_columns:
        # Extract relevant columns
        numb_vessels = n_ves[['date', 'operations', vessel]].copy()
        op_col = f"operations_{vessel}"
        numb_vessels.rename(columns={"operations": op_col}, inplace=True)


        # Compute max vessel count per day (excluding zero values)
        filtered_days_TOT_vessel = numb_vessels.groupby('date').apply(lambda g: g.loc[g[vessel].idxmax(), [vessel, op_col]])

        filtered_days_TOT_vessel.index = pd.to_datetime(filtered_days_TOT_vessel.index)

        daily_vessel = daily_vessel.join(filtered_days_TOT_vessel, how='left')

    daily_vessel.fillna(0, inplace=True)

    # For each day create a dict that represent the operations made for that day and the idx of the operation in log_event
    operation_columns = [col for col in daily_vessel.columns if col.startswith('operations_')]

    daily_vessel['operations'] = daily_vessel.apply(combine_operations, axis=1)

    daily_vessel = daily_vessel.drop(columns=operation_columns)

    return daily_vessel


def number_vessels_func_with_oper(
    log_events: pd.DataFrame, 
    col_to_count: str ='d_end_wait_start',
    mobilisation: bool = False
)->pd.DataFrame:

    """
    This function calculates the number of vessel type charted per day 
    to obtain a dataframe with vessel used and opeartion conducted along same day 
    It also add the operation.id conducted and the index of it which appears on the log_event file.

    Take into consideration also mobilisation of the vessel to merge operation

    Args:
        log_events (:obj:`pd.DataFrame`): Log of all the events (failure,
            operation, inspection_port, inspection_site).
        col_to_count (:obj:`str`): The column on which should start the count of date of the charting vessel
        mobilisation (bool): Boolean to evaluate only the mobilisation. Defaults to False

    Returns:
        pd.DataFrame: Number of vessel charted per day.
    """


    logs = deepcopy(log_events)

    if not mobilisation:
        log_op = logs[logs['event'].str.startswith(('operation', 'inspection'))]

    # Add mobilisation
    else:
        log_op = logs[logs['event'].str.startswith('mobi')]
        log_op['d_end_stat_chart'] = log_op['d_end']

    # Generate hourly time series
    log_op['d_end_stat_chart'] = pd.to_datetime(log_op['d_end_stat_chart'], dayfirst=True, errors='coerce')
    date_rng = pd.date_range(start=log_op['d_trigger'].min(), end=log_op['d_end_stat_chart'].max(), freq='h')

    # Create a new DataFrame with hourly time series
    new_df = pd.DataFrame(index=date_rng)
    new_df['operations'] = [{} for _ in range(len(new_df))]

    # Iterate over rows in the original DataFrame
    for _, row in log_op.iterrows():
        code_1 = row['vessel_1']
        code_2 = row['vessel_2']
        operation = row['id']
        # Here take for operation the actual day that a vessel is used
        if 'inspection' in row['event']:
            start_date =  row['d_trigger'].floor('h')
        else:
            start_date = row[col_to_count].floor('h')
        end_date = row['d_end'].floor('h')

        # Create a mask for the current identification code and time range
        mask = (new_df.index >= start_date) & (new_df.index <= end_date)

        if code_1 not in new_df.columns:
            new_df[code_1] = 0 
        new_df.loc[mask, code_1] += row['n_vessel_1']

        new_df.loc[mask, 'operations'] = new_df.loc[mask, 'operations'].apply(lambda x: {
                **x, row.name: operation} if isinstance(x, dict) else {row.name: operation}
            )

        if code_2 is not None:
            try: 
                mt.isnan(float(code_2))
            except ValueError:
                if code_2 not in new_df.columns:
                    new_df[code_2] = 0
                new_df.loc[mask, code_2] += row['n_vessel_2']
        else: continue


    # Fill NaN values with 0
    new_df = new_df.fillna(0)

    # Convert counts to integers
    columns_to_convert = new_df.columns.difference(['operations'])
    new_df[columns_to_convert] = new_df[columns_to_convert].astype(int)

    new_df.reset_index(drop=False,inplace=True)

    new_df.rename(columns={"index": "date"}, inplace=True)

    return new_df


#########################################
############## CALL CODE ################
#########################################


def df_vessel_merge_use(
            log_events: pd.DataFrame,
            col_to_count: str = 'd_end_wait_start',
    )->pd.DataFrame:

        df_vessel_mobi = number_vessels_func_with_oper(
            log_events = log_events, 
            col_to_count = col_to_count, 
        )

        # Create date vessel log
        daily_vessel = vessel_day_func(df_vessel_mobi)

        return daily_vessel



if __name__ == '__main__':
    pass