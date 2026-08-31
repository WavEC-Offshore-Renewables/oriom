import pandas as pd

from oriom.utils.read_dataframe_value import approximate_hourly_data


def manual_isolation(date_start: pd.Timestamp, op_sched_oper_recover_hub: pd.DataFrame) -> pd.Timedelta:
    """
    Function to calculate the delay for manual isolation based on the start date.
    
    Args:
        date_start (pd.Timestamp): The start date of the event.
        op_sched_oper_recover_hub (pd.DataFrame): Scheduled operations for hub recovery.

    Returns:
        pd.Timedelta: The calculated delay for manual isolation.
    """

    date_start_approx = approximate_hourly_data(date_start)
    delay = op_sched_oper_recover_hub.loc[op_sched_oper_recover_hub['datetime'] == date_start_approx, 'dur_total']
    date_end_restore = date_start + pd.Timedelta(hours=delay.values[0]) if not delay.empty else None

    return date_end_restore




