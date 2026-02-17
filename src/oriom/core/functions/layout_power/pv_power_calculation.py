import pandas as pd
import logging
import numpy as np


def calculate_energy_loss_pv(
    r,
    series_power_pv,
    start_year,
    degradation_rate
):

    """
    Based on the pv_df for each event evaluate the days between one event and the other
    Take into consideration the energy production along the hours of the day of the previous event after that event occur
    Take into consideration the energy production along the hours of the day of the actual event considered before that event occur
    Evaluate then the energy losses of the previous event overwriting the df

    Args:
        r (pd.Series): row of the dataframe.
        series_power_pv (pd.Series): Series of the power_pv
        start_year (int): Project start year.
        pv_degradation_rate (float): Annual degradation in %.

    Return:
        float: Estimated energy loss due to shutdown between the two events.

    Raises:
        ValueError: On missing data or calculation errors.
        float: on valid data
    """

    try:
        # last row does not have losses
        if pd.isna(r['Date_next']):
            return 0

        date_start = r['Date']
        date_end = r['Date_next']
        month = date_start.month
        hour_start = date_start.hour
        hour_end = date_end.hour
        shutdown_duration = (date_end.day - date_start.day) - 1

        if month not in series_power_pv:
            logging.error(f"pv_power_availability: Month {month} not found in series_power_pv")
            return np.nan

        # Degradation coefficient
        degrad_coeff = (1 - degradation_rate / 100) ** (date_start.year - start_year)

        power_pv_month = series_power_pv[month]

        # Production from full days between events
        full_days_power = power_pv_month.sum() * max(shutdown_duration, 0)
        # Power from day of previous event (post-failure time)
        power_day_start = power_pv_month.iloc[hour_start:].sum()
        # Power from day of current event (pre-failure time)
        power_day_end = power_pv_month.iloc[:hour_end].sum()
        # Special case: same-day shutdown
        if shutdown_duration == -1:
            power_day_start  = power_pv_month.iloc[hour_start:hour_end].sum()
            power_day_end = 0

        tot_power = (power_day_start + power_day_end + full_days_power) * degrad_coeff

        perc_loss = 100 - r['Perc_availability']
        return perc_loss * tot_power / 100

    except Exception as e:
        logging.error(f"pv_power_availability: Error in row {r['Name']}: {e}")
        return np.nan

