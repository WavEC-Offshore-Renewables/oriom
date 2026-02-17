import numpy as np
from copy import deepcopy
from datetime import timedelta, datetime
import pandas as pd
import numpy as np

from oriom.utils.read_dataframe_value import approximate_hourly_data


def create_stat_chart_campaign_operation(
        df:pd.DataFrame,
        vessels: list,
        percentile: float = 0.9
    )->pd.DataFrame:
    
    """
    Create the statistic chart date for the 'operation_deferred_merged' or 'inspection_site' 
        that are inside mother vessel campaign. Considering statistical durations 
        of the entire campaign operations insthead of single operations.

    Args:
        df (:obj:`pd.DataFrame`): Dataframe of log_events_merged
        vessels (list): list of class `~oriom.classes.Vessel.Vessel`
        percentile (:obj:`float`): percentile value to calculate the statistic

    Returns:
        pd.DataFrame: dataframe with all the failures.
    """

    if percentile > 1:
        percentile = percentile / 100

    # Filter the df for deferred_merged_operation
    df_deferred = deepcopy(df[df['event'] == 'operation_deferred_merged'])
    
    # Extract month for grouping
    df_deferred['year'] = df_deferred['d_trigger'].dt.year
    df_deferred['month'] = df_deferred['d_trigger'].dt.month 
    
    # iterate for vessel used
    for vessel in vessels:
        df_deferred_vessel = df_deferred[df_deferred['vessel_1'] == vessel.id]

        # Regroup by year and month, evaluate start and end of deferred op for each month, year
        grouped = df_deferred_vessel.groupby(['year', 'month']).agg(
            min_trigger=('d_trigger', 'min'),
            max_end=('d_end', 'max')
        ).reset_index()

        # Evaluate duration of deferred operations in days for each deferred month
        grouped['duration_days'] = (grouped['max_end'] - grouped['min_trigger']).dt.total_seconds() / 86400  # in days
        # monthly percentile calculation
        month_percentiles = np.ceil(grouped.groupby('month')['duration_days'].quantile(percentile)).reset_index()

        # Create dictionary with montlhy duration percentile
        month_percentiles_dict = {int(row['month']): int(np.ceil(row['duration_days'])) for _, row in month_percentiles.iterrows()}

        # Add the monthly percentiles to the d_trigger only for the deferred operations
        mask = (df['event'] == 'operation_deferred_merged') & (df['vessel_1'] == vessel.id)
        
        stat_end_dict = {
            (row['year'], row['month']): row['min_trigger'] + timedelta(
                days=month_percentiles_dict.get(row['month'], 0)
            )
            for _, row in grouped.iterrows()
        }

        # apply to the mask
        df.loc[mask, 'd_end_stat_chart'] = df.loc[mask].apply(
            lambda row: stat_end_dict.get((row['d_trigger'].year, row['d_trigger'].month)),
            axis=1
        )

    return df



def vessel_reuse(
    vessel_n: int, 
    n_vessel_used: int, 
    day_start_idx_previous: int,
    day_start_idx_next: int,
    vessel_busy: int
) -> tuple[int, int]:
    
    """
    This function check if all the vessels have been used for this deferred shift. 
    If not, there are some vessel available to conduct other deferred operations, so return nº of
    vessels that are not used and the start index date of the shift on which such vessel can 
    be used for other deferred maintenances.

    Args:
        vessel_n (int): Total number of vessel, taken from vessel.n_vessels
        n_vessel_used (int): The number of vessel used for the last shift
        day_start_idx_previous (int): The starting time and date of the last shift
        day_start_idx_next (int): The ending time and date of the last shift
        vessel_busy (int): The number of vessel already used for the period under analysis

    Return:
        vessel_available (int): The number of vessel that have not been used for this shift
        day_start_idx (int): The time and date to consider for the next shift
    """
    
    # Check if used all the vessel
    if n_vessel_used < vessel_n:
        vessel_available = vessel_n - n_vessel_used

        # Add the used vessel to the already busy one in this period
        vessel_busy += n_vessel_used

        # If all vessel are busy, wait next period with resetting the vessel busy and vessel available
        if vessel_busy >= vessel_n:
            vessel_available = vessel_n
            day_start_idx = day_start_idx_next
            vessel_busy = 0

        else:
            day_start_idx = day_start_idx_previous
    else: 
        vessel_available = vessel_n
        day_start_idx = day_start_idx_next


    return vessel_available, day_start_idx, vessel_busy


def find_start_time(
    day_start_oper: datetime, 
    day_start_oper_single_op: datetime,
    day_start_idx: int, 
    oper_sched: pd.DataFrame, 
    index_wait_at_site_col: int | None,
    index_wait_to_start_col:int | None
)->pd.DataFrame:
    
    """
    Function to find in the operation schedule the next day of work.

    It looks for the first day different from the original on which the operation have wait at site equal to zero.

    # NOTE if there is a wait at site the operation will be conducted alone

    Args:
        day_start_oper (pd.Timestamp): The date on which the operation should start.
        day_start_oper_single_op (pd.Timestamp): The date on which the single operation should start.
        day_start_idx (int): The index of the operation schedule to start from.
        oper_sched (pd.DataFrame): The operation schedule dataframe.
        index_wait_at_site_col (int | None): The index of the wait at site column.
        index_wait_to_start_col (int | None): The index of the wait to start column.
        
    Returns:
        day_start_oper (pd.Timestamp): The date on which the operation can start.
        day_start_idx (int): The index of the operation schedule on which the operation can start.
        wait_to_start (int): The wait to start time in hours.  
    """

    # Find first time on which wait_to_start = 0 
    while True:
        # Try to see if there is a wait_at_site < 1
        wait_to_start = int(round(oper_sched.iat[day_start_idx, index_wait_to_start_col]))
        if wait_to_start == 0:
            if index_wait_at_site_col is not None:
                wait_at_site = float(oper_sched.iat[day_start_idx, index_wait_at_site_col])
            else:
                wait_at_site = 0
            break

        day_start_idx += 1 

    day_start_oper = oper_sched.iat[day_start_idx, 0]
    day_start_oper = approximate_hourly_data(day_start_oper)

    return day_start_oper, day_start_idx, wait_to_start, wait_at_site


def creation_oper_vessel_dict(
        failures: list, 
        find_element_class: object, 
        oper_per_vessel: dict, 
        deferred_failures_correction:list
):
    """ Create list of failures and dict vess: deferred_op"""
    for failure in failures:
        if failure.maintenance_strategy == 'specific month':
            oper = find_element_class.find_operation(failure.operation_triggered)
            deferred_failures_correction.append(failure.id)
            # Avoid to take for towing opeartion as there are no failure connected
            if 'tow' not in oper.id:
                # If site operation take the vessel
                if not getattr(oper, "tow_to_port", None):
                    if oper.vessel1_id in oper_per_vessel:
                        oper_per_vessel[oper.vessel1_id].append(oper.id)
                    else:
                        oper_per_vessel[oper.vessel1_id] = [oper.id]
                # If port opeartion create tow key instead of vessel.id
                else:
                    if 'tow' in oper_per_vessel:
                        oper_per_vessel['tow'].append(oper.id)
                    else:
                        oper_per_vessel['tow'] = [oper.id]



if __name__ == '__main__':
    pass