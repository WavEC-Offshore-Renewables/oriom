import numpy as np
from copy import deepcopy
from datetime import timedelta, datetime
import pandas as pd
import numpy as np

from oriom.utils.read_dataframe_value import approximate_hourly_data


def manage_recommissioning(log_events_tow: pd.DataFrame, substitute = False):
    """ Manage recommissioning event modifying the date of operation end and removing recomm row"""
    if substitute:
        values_overwrite = ['d_end_dur_net_site', 'd_end_transit_tp', 'd_end']

        # look for recommissiong event
        recom = log_events_tow[log_events_tow['event'] == 'recommissioning']
        if not recom.empty:
            for col in values_overwrite:
                log_events_tow.loc[recom.index, col] = recom[col]

    return log_events_tow[log_events_tow['event'] != 'recommissioning']


def create_stat_chart_campaign_operation(
        df:pd.DataFrame,
        vessels: list,
        percentile: float = 0.9,
    ) -> tuple[pd.DataFrame, dict]:

    """
    Create the statistic chart date for the 'operation_deferred_merged' or 'inspection_site'
        that are inside mother vessel campaign. Considering statistical durations
        of the entire campaign operations insthead of single operations.

    Args:
        df (:obj:`pd.DataFrame`): Dataframe of log_events_merged
        vessels (list): list of class `~oriom.classes.Vessel.Vessel`
        percentile (:obj:`float`): percentile value to calculate the statistic
        month_year_calculate (:obj:`bool`): boolean to evaluate

    Returns:
        pd.DataFrame: dataframe with all the failures.
        dict: dictionary with monthly percentiles for each vessel.
    """
    vessel_month_percentiles_dict = {}
    
    if percentile > 1:
        percentile = percentile / 100

    # Filter the df for deferred_merged_operation
    df_deferred = deepcopy(df[df['event'] != 'mobilisation_merged'])

    # Extract month for grouping
    df_deferred['year'] = df_deferred['d_trigger'].dt.year
    df_deferred['month'] = df_deferred['d_trigger'].dt.month

    # iterate for vessel used
    for vessel in vessels:
        df_deferred_vessel = df_deferred[df_deferred['vessel_1'] == vessel.id]
        if df_deferred_vessel.empty:
            continue
        # Regroup by year and month, evaluate start and end of deferred op for each month, year
        grouped = df_deferred_vessel.groupby(['year', 'month']).agg(
            min_trigger=('d_end_leadtime', 'min'),
            max_end=('d_end', 'max')
        ).reset_index()

        # Evaluate duration of deferred operations in days for each deferred month
        grouped['duration_days'] = (grouped['max_end'] - grouped['min_trigger']).dt.total_seconds() / 86400  # in days

        # monthly percentile calculation
        month_percentiles = np.ceil(grouped.groupby('month')['duration_days'].quantile(percentile)).reset_index()

        # Create dictionary with montlhy duration percentile
        month_percentiles_dict = {int(row['month']): int(np.ceil(row['duration_days'])) for _, row in month_percentiles.iterrows()}
        vessel_month_percentiles_dict = {vessel.id: month_percentiles_dict}

        # Add the monthly percentiles to the d_trigger only for the deferred operations
        mask = (df['event'] != 'mobilisation_merged') & (df['vessel_1'] == vessel.id)

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

    return df, vessel_month_percentiles_dict


def manage_chart(df: pd.DataFrame, vessels: list, percentile: float = 0.9):

    """ Manage d_trigger, event and chart_vessel of the deferred tow merged"""

    # Modify event name
    df['event'] = np.where(
        df['event'] != 'mobilisation_merged',
        'operation_deferred_merged',  # value if True
        df['event']                   # value if False (keep the same)
    )

    # Uniform d_trigger and d_end_leadtime
    df[['d_trigger', 'd_end_leadtime']] = (
        df.groupby('year_month')[['d_trigger', 'd_end_leadtime']]
        .transform('min')
    )
    
    # Manage deferred chart for campaign tow
    df = df.drop(columns=['year_month'])
    df, vessel_month_percentiles_dict = create_stat_chart_campaign_operation(
        df = df,
        vessels = vessels,
        percentile = percentile
    )
        
    return df, vessel_month_percentiles_dict


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
    log_events,
    failures,
    find_element_class,
    oper_per_vessel,
    deferred_failures_correction,
    deferred_failures_correction_tow,
    failures_correction_tow,
):
    """Create dict vessel -> operations and classify failures."""

    # -------------------------------
    # 1) Build towing_op dictionary
    # -------------------------------
    towing_op = {}

    for failure in failures:
        oper = find_element_class.find_operation(failure.operation_triggered)

        # Check if towing
        tow_op = getattr(oper, "tow_to_port", False)

        # Save by base id (before '.')
        base_id = failure.id.split(".")[0]
        towing_op[base_id] = tow_op

        # Populate oper_per_vessel (no tow_operation)
        if not tow_op:
            if oper.vessel1_id in oper_per_vessel:
                if oper.id not in oper_per_vessel[oper.vessel1_id]:
                    oper_per_vessel[oper.vessel1_id].append(oper.id)
            else:
                oper_per_vessel[oper.vessel1_id] = [oper.id]

    # -------------------------------
    # 2) Filter failures from dataframe
    # -------------------------------
    df_fail = log_events[log_events["event"] == "failure"].copy()

    if df_fail.empty:
        return

    # -------------------------------
    # 3) Vectorized classification
    # -------------------------------
    df_fail["base_id"] = df_fail["id"].str.split(".").str[0]

    df_fail["is_tow"] = df_fail["base_id"].map(towing_op).fillna(False)

    # Conditions
    mask_tow = df_fail["is_tow"]
    mask_specific_month = df_fail["comments"] == "specific month"

    # -------------------------------
    # 4) Fill output lists
    # -------------------------------
    deferred_failures_correction_tow.extend(
        df_fail.loc[mask_tow & mask_specific_month, "id"].tolist()
    )

    failures_correction_tow.extend(
        df_fail.loc[mask_tow & ~mask_specific_month, "id"].tolist()
    )

    deferred_failures_correction.extend(
        df_fail.loc[~mask_tow & mask_specific_month, "id"].tolist()
    )


def remove_single_mobilisation(log_mobilisation: pd.DataFrame, failures_list: list) -> pd.DataFrame:
    """ Remove single mobilisation operation from id_failure"""
    failure_suffixes = {f.split('_', 1)[1] for f in failures_list if '_' in f}
    try:
        mask = ~log_mobilisation['_suffix'].isin(failure_suffixes)
    except KeyError:
        return log_mobilisation
    return log_mobilisation.loc[mask]
    

if __name__ == '__main__':
    pass