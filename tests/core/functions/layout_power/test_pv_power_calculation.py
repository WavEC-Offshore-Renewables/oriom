#test_pv_power_calculation
import unittest
from datetime import datetime

import numpy as np
import pandas as pd

from oriom.core.functions.layout_power import pv_power_calculation


class TestCalculateEnergyLossPVBasic(unittest.TestCase):
    """
    Basic behavioural tests for calculate_energy_loss_pv.
    """

    def setUp(self):
        # Simple monthly PV profile: constant 10 kW for each hour in the day
        hourly = pd.Series([10.0] * 24, index=range(24))
        # series_power_pv: month -> hourly Series
        self.series_power_pv = pd.Series({6: hourly})

    def test_last_row_with_nan_next_returns_zero(self):
        """
        If Date_next is NaT, function must return 0 (no loss for last row).
        """
        r = pd.Series(
            {
                "Date": pd.Timestamp(datetime(2025, 6, 1, 10, 0, 0)),
                "Date_next": pd.NaT,
                "Perc_availability": 80.0,
                "Name": "row_last",
            }
        )

        result = pv_power_calculation.calculate_energy_loss_pv(
            r=r,
            series_power_pv=self.series_power_pv,
            start_year=2020,
            degradation_rate=0.0,
        )
        self.assertEqual(result, 0.0)

    def test_missing_month_in_series_power_returns_nan(self):
        """
        If the month of Date is not present in series_power_pv, the function
        must log an error and return NaN.
        """
        # Date in July (7), but series_power_pv only has month 6
        r = pd.Series(
            {
                "Date": pd.Timestamp(datetime(2025, 7, 1, 8, 0, 0)),
                "Date_next": pd.Timestamp(datetime(2025, 7, 2, 8, 0, 0)),
                "Perc_availability": 50.0,
                "Name": "row_missing_month",
            }
        )

        result = pv_power_calculation.calculate_energy_loss_pv(
            r=r,
            series_power_pv=self.series_power_pv,
            start_year=2020,
            degradation_rate=0.0,
        )
        self.assertTrue(np.isnan(result))

    def test_multi_day_shutdown_without_degradation(self):
        """
        Multi–day shutdown case, degradation=0:
        - Date: 2025-06-01 06:00
        - Date_next: 2025-06-04 10:00
        - shutdown_duration = (4 - 1) - 1 = 2 days
        - power_per_hour = 10
          * full_days_power = 2 * 24 * 10 = 480
          * power_day_start = hours[6..23] = 18 * 10 = 180
          * power_day_end = hours[0..9] = 10 * 10 = 100
          => tot_power = 480 + 180 + 100 = 760
        - Perc_availability = 80 -> 20% loss
          => expected_loss = 0.2 * 760 = 152
        """
        r = pd.Series(
            {
                "Date": pd.Timestamp(datetime(2025, 6, 1, 6, 0, 0)),
                "Date_next": pd.Timestamp(datetime(2025, 6, 4, 10, 0, 0)),
                "Perc_availability": 80.0,
                "Name": "row_multi_day",
            }
        )

        result = pv_power_calculation.calculate_energy_loss_pv(
            r=r,
            series_power_pv=self.series_power_pv,
            start_year=2020,
            degradation_rate=0.0,
        )
        self.assertAlmostEqual(result, 152.0, places=6)


class TestCalculateEnergyLossPVSameDayAndDegradation(unittest.TestCase):
    """
    Tests for same–day shutdown and degradation effects.
    """

    def setUp(self):
        # Constant 10 kW for each hour for month 6
        hourly = pd.Series([10.0] * 24, index=range(24))
        self.series_power_pv = pd.Series({6: hourly})

    def test_same_day_shutdown_no_degradation(self):
        """
        Same–day shutdown:
        - Date: 2025-06-01 06:00
        - Date_next: 2025-06-01 10:00
        - shutdown_duration = (1 - 1) - 1 = -1 -> special case
          power_day_start = hours[6..10) = 4 * 10 = 40
          power_day_end = 0
          full_days_power = 0
          tot_power = 40
        - Perc_availability = 50 -> 50% loss
          expected = 0.5 * 40 = 20
        """
        r = pd.Series(
            {
                "Date": pd.Timestamp(datetime(2025, 6, 1, 6, 0, 0)),
                "Date_next": pd.Timestamp(datetime(2025, 6, 1, 10, 0, 0)),
                "Perc_availability": 50.0,
                "Name": "row_same_day",
            }
        )

        result = pv_power_calculation.calculate_energy_loss_pv(
            r=r,
            series_power_pv=self.series_power_pv,
            start_year=2020,
            degradation_rate=0.0,
        )
        self.assertAlmostEqual(result, 20.0, places=6)

    def test_degradation_factor_applied(self):
        """
        Degradation factor:
        - Same–day case like above, but:
          * start_year = 2020
          * Date.year = 2023 -> exponent = 3
          * degradation_rate = 10% -> degrad_coeff = 0.9^3 = 0.729
          * base tot_power (no degradation) = 40
          * Perc_availability = 0 -> 100% energy loss
          expected = 40 * 0.729 = 29.16
        """
        r = pd.Series(
            {
                "Date": pd.Timestamp(datetime(2023, 6, 1, 6, 0, 0)),
                "Date_next": pd.Timestamp(datetime(2023, 6, 1, 10, 0, 0)),
                "Perc_availability": 0.0,
                "Name": "row_degradation",
            }
        )

        result = pv_power_calculation.calculate_energy_loss_pv(
            r=r,
            series_power_pv=self.series_power_pv,
            start_year=2020,
            degradation_rate=10.0,
        )
        self.assertAlmostEqual(result, 29.16, places=5)


class TestCalculateEnergyLossPVErrorPath(unittest.TestCase):
    """
    Tests for error handling inside calculate_energy_loss_pv.
    """

    def setUp(self):
        hourly = pd.Series([10.0] * 24, index=range(24))
        self.series_power_pv = pd.Series({6: hourly})

    def test_missing_perc_availability_returns_nan(self):
        """
        If Perc_availability is missing, a KeyError is raised inside the try
        and the function must catch it and return NaN.
        """
        r = pd.Series(
            {
                "Date": pd.Timestamp(datetime(2025, 6, 1, 6, 0, 0)),
                "Date_next": pd.Timestamp(datetime(2025, 6, 2, 6, 0, 0)),
                # 'Perc_availability' is intentionally missing
                "Name": "row_missing_perc",
            }
        )

        result = pv_power_calculation.calculate_energy_loss_pv(
            r=r,
            series_power_pv=self.series_power_pv,
            start_year=2020,
            degradation_rate=0.0,
        )
        self.assertTrue(np.isnan(result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
