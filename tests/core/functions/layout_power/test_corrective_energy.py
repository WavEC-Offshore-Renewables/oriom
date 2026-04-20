# tests/test_corrective_layout.py

import unittest
from unittest.mock import patch
from datetime import datetime

import pandas as pd
import networkx as nx

from oriom.core.functions.layout_power import corrective_energy


DUMMY_OPERATIONS_STATS = [object()]


class TestEnergyCalculation(unittest.TestCase):
    """
    Unit tests for energy_calculation helper.
    """

    @patch(
        "oriom.core.functions.layout_power.corrective_energy.approximate_hourly_data",
        side_effect=lambda dt: dt,  # identity: do not change the timestamp
    )
    def test_energy_calculation_sums_between_rows_and_repeats_last(self, _mock_approx):
        """
        energy_calculation must:
        - sum power between consecutive Date rows using metocean_timeseries
        - append the last value again at the end
        """
        # df_wave has two timestamps → 1 interval
        df_wave = pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    ["2025-01-01 00:00:00", "2025-01-01 01:00:00"]
                )
            }
        )

        # timeseries with power values in the interval [00:00, 01:00)
        times = pd.to_datetime(
            [
                "2025-01-01 00:00:00",
                "2025-01-01 00:15:00",
                "2025-01-01 00:30:00",
                "2025-01-01 00:45:00",
            ]
        )
        metocean = pd.DataFrame({"p_wave": [10.0, 10.0, 10.0, 10.0]}, index=times)

        energy_list = corrective_energy.timeseries_energy_calculation(
        df_wave, metocean, tech1="wave"
        )

        # Only one interval → sum of 4 points = 40. Last value repeated
        self.assertEqual(energy_list, [40.0, 40.0])

    @patch(
        "oriom.core.functions.layout_power.corrective_energy.approximate_hourly_data",
        side_effect=lambda dt: dt,  # identity
    )
    def test_energy_calculation_multiple_intervals(self, _mock_approx):
        """
        With three dates → 2 intervals.
        Check that we get 3 entries: two sums + last repeated.
        """
        df_wave = pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 01:00:00",
                        "2025-01-01 03:00:00",
                    ]
                )
            }
        )

        # p_wave = 5.0 every 30 minutes from 00:00 to 03:00
        times = pd.date_range("2025-01-01 00:00:00", periods=6, freq="30min")
        metocean = pd.DataFrame({"p_wave": [5.0] * len(times)}, index=times)

        energy_list = corrective_energy.timeseries_energy_calculation(
            df_wave, metocean, tech1="wave"
        )

        # Intervals:
        # [00:00, 01:00) → times: 00:00, 00:30 → 2 * 5 = 10
        # [01:00, 03:00) → times: 01:00, 01:30, 02:00, 02:30 → 4 * 5 = 20
        # Result list: [10, 20, 20]
        self.assertEqual(energy_list, [10.0, 20.0, 20.0])


class TestCorrectiveLayoutBasicChecks(unittest.TestCase):
    """
    Basic validation checks for corrective_layout.
    """

    def setUp(self):
        # Minimal log_events with required columns
        self.log_events = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2025-01-01 00:00:00"]),
                "event": ["failure"],
            }
        )

    def test_error_when_wtg_devices_but_no_graph(self):
        """
        If n_device_wtg is defined and G_wind is None → ValueError.
        """
        with self.assertRaises(ValueError):
            corrective_energy.corrective_layout(
                log_events=self.log_events,
                start_year=2025,
                start_month=1,
                n_lifetime=1,
                operations_corrective_stat=DUMMY_OPERATIONS_STATS,
                find_element_class=lambda *args, **kwargs: None,
                n_device_wtg=10,  # defined
                G_wind=None,      # missing
            )

    def test_error_when_wec_devices_but_no_graph(self):
        """
        If n_device_wec is defined and G_wave is None → ValueError.
        """
        with self.assertRaises(ValueError):
            corrective_energy.corrective_layout(
                log_events=self.log_events,
                start_year=2025,
                start_month=1,
                n_lifetime=1,
                operations_corrective_stat=DUMMY_OPERATIONS_STATS,
                find_element_class=lambda *args, **kwargs: None,
                n_device_wec=5,
                G_wave=None,
            )

    def test_error_when_pv_devices_but_no_graph(self):
        """
        If n_device_pv is defined and G_pv is None → ValueError.
        """
        with self.assertRaises(ValueError):
            corrective_energy.corrective_layout(
                log_events=self.log_events,
                start_year=2025,
                start_month=1,
                n_lifetime=1,
                operations_corrective_stat=DUMMY_OPERATIONS_STATS,
                find_element_class=lambda *args, **kwargs: None,
                n_device_pv=100,
                G_pv=None,
            )

    def test_returns_empty_dfs_when_no_devices_defined(self):
        """
        If no n_device_* is defined, all output DataFrames must be empty.
        """
        data_result = corrective_energy.corrective_layout(
            log_events=self.log_events,
            start_year=2025,
            start_month=1,
            n_lifetime=1,
            operations_corrective_stat=DUMMY_OPERATIONS_STATS,
            find_element_class=lambda *args, **kwargs: None,
        )

        self.assertTrue(data_result['wind'].empty)
        self.assertTrue(data_result['wave'].empty)
        self.assertTrue(data_result['pv'].empty)

    @patch(
        "oriom.core.functions.layout_power.corrective_energy.return_percentage"
    )
    def test_log_events_filter_excludes_inspections_and_mobilisations(
        self, mock_return_percentage
    ):
        """
        log_events must be filtered to exclude:
        'inspection_site', 'inspection_port', 'mobilisation', 'mobilisation_merged'
        before calling return_percentage.
        """
        log_events = pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-01 01:00:00",
                        "2025-01-01 02:00:00",
                        "2025-01-01 03:00:00",
                        "2025-01-01 04:00:00",
                        "2025-01-01 05:00:00",
                    ]
                ),
                "event": [
                    "failure",
                    "inspection_site",
                    "mobilisation",
                    "mobilisation_merged",
                    "inspection_port",
                    "failure",
                ],
            }
        )

        G_wind = nx.DiGraph()
        G_wind.add_node(1)

        dict_power_wind = {1: 1000.0}  # January average farm power [kW]

        # return_percentage will just echo back a minimal df so that the rest runs
        mock_return_percentage.return_value = pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    ["2025-01-01 00:00:00", "2025-01-01 05:00:00"]
                ),
                "Perc_availability": [100.0, 100.0],
            }
        )

        corrective_energy.corrective_layout(
            log_events=log_events,
            start_year=2025,
            start_month=1,
            n_lifetime=1,
            operations_corrective_stat=DUMMY_OPERATIONS_STATS,
            find_element_class=lambda *args, **kwargs: None,
            n_device_wtg=10,
            G_wind=G_wind,
            dict_power_wind=dict_power_wind,
            STATISTIC_ENERGY=True,
        )

        # Check what log_events is passed to return_percentage
        args, kwargs = mock_return_percentage.call_args
        filtered_log = kwargs.get("log_events")
        self.assertListEqual(
            filtered_log["event"].tolist(),
            ["failure", "failure"],
        )


class TestCorrectiveLayoutWind(unittest.TestCase):
    """
    Tests for wind branch inside corrective_layout.
    """

    def setUp(self):
        self.log_events = pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    ["2025-01-10 00:00:00", "2025-01-20 00:00:00"]
                ),
                "event": ["failure", "repair"],
            }
        )
        self.G_wind = nx.DiGraph()
        self.G_wind.add_node(1)

    @patch(
        "oriom.core.functions.layout_power.corrective_energy.return_percentage"
    )
    def test_wind_statistic_energy_uses_monthly_power_and_percentage(
        self, mock_return_percentage
    ):
        """
        STATISTIC_ENERGY=True:
        Power_loss_KW = (100 - Perc_availability) * P_month / 100
        """
        # return_percentage will return this small df
        df_wind = pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    ["2025-01-10 00:00:00", "2025-01-20 00:00:00"]
                ),
                "Perc_availability": [100.0, 50.0],
            }
        )
        mock_return_percentage.return_value = df_wind

        dict_power_wind = {1: 1000.0}  # January average farm power [kW]

        data_result = corrective_energy.corrective_layout(
            log_events=self.log_events,
            start_year=2025,
            start_month=1,
            n_lifetime=1,
            operations_corrective_stat=DUMMY_OPERATIONS_STATS,
            find_element_class=lambda *args, **kwargs: None,
            n_device_wtg=10,
            G_wind=self.G_wind,
            dict_power_wind=dict_power_wind,
            STATISTIC_ENERGY=True,
        )

        # Wave / PV are not requested
        self.assertTrue(data_result['wave'].empty)
        self.assertTrue(data_result['pv'].empty)

        # Check Power_loss_kW formula
        # row 0: (100-100)*1000/100 = 0
        # row 1: (100-50) *1000/100 = 50*10 = 500
        self.assertIn("Power_loss_kW", data_result['wind'].columns)
        self.assertListEqual(
            data_result['wind']["Power_loss_kW"].tolist(), [0.0, 500.0]
        )

    @patch(
        "oriom.core.functions.layout_power.corrective_energy.approximate_hourly_data",
        side_effect=lambda dt: dt,  # identity to simplify
    )
    @patch(
        "oriom.core.functions.layout_power.corrective_energy.return_percentage"
    )
    def test_wind_non_statistic_energy_uses_metocean_timeseries(
        self, mock_return_percentage, _mock_approx
    ):
        """
        STATISTIC_ENERGY=False:
        - energy_calculation uses metocean_timeseries 'p_wind'
        - Power_loss_kW = energy_list * (100 - Perc_availability)/100
        """
        df_wind = pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    ["2025-01-01 00:00:00", "2025-01-01 01:00:00"]
                ),
                "Perc_availability": [0.0, 50.0],
            }
        )
        mock_return_percentage.return_value = df_wind

        # metocean timeseries with p_wind
        times = pd.to_datetime(
            [
                "2025-01-01 00:00:00",
                "2025-01-01 00:15:00",
                "2025-01-01 00:30:00",
                "2025-01-01 00:45:00",
            ]
        )
        metocean_timeseries = pd.DataFrame(
            {"p_wind": [10.0, 10.0, 10.0, 10.0]}, index=times
        )

        dict_power_wind = {1: 500.0}  # not used when STATISTIC_ENERGY=False

        data_result = corrective_energy.corrective_layout(
            log_events=self.log_events,
            start_year=2025,
            start_month=1,
            n_lifetime=1,
            operations_corrective_stat=DUMMY_OPERATIONS_STATS,
            find_element_class=lambda *args, **kwargs: None,
            n_device_wtg=5,
            G_wind=self.G_wind,
            dict_power_wind=dict_power_wind,
            metocean_timeseries=metocean_timeseries,
            STATISTIC_ENERGY=False,
        )

        # Wave / PV not requested
        self.assertTrue(data_result['wave'].empty)
        self.assertTrue(data_result['pv'].empty)

        # energy_list from metocean: sum of 4 points of 10 = 40
        # Power_loss_kW:
        #  row 0: 40 * (100-0)/100 = 40
        #  row 1: 40 * (100-50)/100 = 20
        self.assertIn("Power_loss_kW", data_result['wind'].columns)
        self.assertListEqual(
            data_result['wind']["Power_loss_kW"].tolist(), [40.0, 20.0]
        )

class TestCorrectiveLayoutWave(unittest.TestCase):
    """
    Tests for wave branch inside corrective_layout.
    """

    def setUp(self):
        # We keep only one corrective event pair in log_events
        self.log_events = pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    ["2025-01-01 00:00:00", "2025-01-01 01:00:00"]
                ),
                "event": ["failure", "repair"],
            }
        )
        self.G_wave = nx.DiGraph()
        self.G_wave.add_node(1)

        # metocean_timeseries with p_wave in [00:00, 01:00)
        times = pd.to_datetime(
            [
                "2025-01-01 00:00:00",
                "2025-01-01 00:15:00",
                "2025-01-01 00:30:00",
                "2025-01-01 00:45:00",
            ]
        )
        self.metocean_timeseries = pd.DataFrame(
            {"p_wave": [10.0, 10.0, 10.0, 10.0]}, index=times
        )

    @patch(
        "oriom.core.functions.layout_power.corrective_energy.approximate_hourly_data",
        side_effect=lambda dt: dt,  # identity to simplify
    )
    @patch(
        "oriom.core.functions.layout_power.corrective_energy.return_percentage"
    )
    def test_wave_non_statistic_energy_uses_metocean_timeseries(
        self, mock_return_percentage, _mock_approx
    ):
        """
        STATISTIC_ENERGY=False:
        - energy_calculation produces energy_list from metocean_timeseries
        - Power_loss_kW = energy_list * (100 - Perc_availability)/100
        """
        # return_percentage produces the layout dataframe for wave
        df_wave = pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    ["2025-01-01 00:00:00", "2025-01-01 01:00:00"]
                ),
                "Perc_availability": [0.0, 50.0],
            }
        )
        mock_return_percentage.return_value = df_wave

        dict_power_wave = {1: 500.0}  # not used in non-STATISTIC_ENERGY

        data_result = corrective_energy.corrective_layout(
            log_events=self.log_events,
            start_year=2025,
            start_month=1,
            n_lifetime=1,
            operations_corrective_stat=DUMMY_OPERATIONS_STATS,
            find_element_class=lambda *args, **kwargs: None,
            n_device_wec=5,
            G_wave=self.G_wave,
            dict_power_wave=dict_power_wave,
            metocean_timeseries=self.metocean_timeseries,
            STATISTIC_ENERGY=False,
        )

        # Wind / PV not requested
        self.assertTrue(data_result['wind'].empty)
        self.assertTrue(data_result['pv'].empty)

        # energy_list from metocean: sum of 4 points of 10 = 40
        # Power_loss_kW:
        #  row 0: 40 * (100-0)/100 = 40
        #  row 1: 40 * (100-50)/100 = 20
        self.assertIn("Power_loss_kW", data_result['wave'].columns)
        self.assertListEqual(
            data_result['wave']["Power_loss_kW"].tolist(), [40.0, 20.0]
        )

    @patch(
        "oriom.core.functions.layout_power.corrective_energy.return_percentage"
    )
    def test_wave_statistic_energy_uses_monthly_power(self, mock_return_percentage):
        """
        STATISTIC_ENERGY=True:
        Power_loss_kW = (100 - Perc_availability) * P_month / 100
        """
        df_wave = pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    ["2025-01-15 00:00:00", "2025-01-16 00:00:00"]
                ),
                "Perc_availability": [90.0, 50.0],
            }
        )
        mock_return_percentage.return_value = df_wave

        dict_power_wave = {1: 2000.0}

        data_result = corrective_energy.corrective_layout(
            log_events=self.log_events,
            start_year=2025,
            start_month=1,
            n_lifetime=1,
            operations_corrective_stat=DUMMY_OPERATIONS_STATS,
            find_element_class=lambda *args, **kwargs: None,
            n_device_wec=10,
            G_wave=self.G_wave,
            dict_power_wave=dict_power_wave,
            STATISTIC_ENERGY=True,
        )

        self.assertTrue(data_result['wind'].empty)
        self.assertTrue(data_result['pv'].empty)

        # row 0: (100-90)*2000/100 = 10*20 = 200
        # row 1: (100-50)*2000/100 = 50*20 = 1000
        self.assertIn("Power_loss_kW", data_result['wave'].columns)
        self.assertListEqual(
            data_result['wave']["Power_loss_kW"].tolist(), [200.0, 1000.0]
        )


class TestCorrectiveLayoutPV(unittest.TestCase):
    """
    Tests for PV branch inside corrective_layout.
    """

    def setUp(self):
        self.log_events = pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    ["2025-01-10 00:00:00", "2025-01-20 00:00:00"]
                ),
                "event": ["failure", "repair"],
            }
        )
        self.G_pv = nx.DiGraph()
        self.G_pv.add_node(1)

    @patch(
        "oriom.core.functions.layout_power.corrective_energy.calculate_energy_loss_pv"
    )
    @patch(
        "oriom.core.functions.layout_power.corrective_energy.aux_functions.convert_stringtime"
    )
    @patch(
        "oriom.core.functions.layout_power.corrective_energy.return_percentage"
    )
    def test_pv_branch_calls_calculate_energy_loss_and_sets_power_loss(
        self,
        mock_return_percentage,
        mock_convert_stringtime,
        mock_calc_energy_loss_pv,
    ):
        """
        PV branch:
        - must call calculate_energy_loss_pv for each row/month
        - df_pv['Power_loss_kW'] must be updated with that value
        """
        # Layout df_pv from return_percentage
        df_pv = pd.DataFrame(
            {
                "Date": ["2025-01-10 00:00:00", "2025-01-20 00:00:00"],
                "Perc_availability": [100.0, 80.0],
            }
        )
        mock_return_percentage.return_value = df_pv

        # convert_stringtime: simply convert Date to datetime and return df
        def fake_convert_stringtime(df, dt_column):
            df[dt_column] = pd.to_datetime(df[dt_column])
            return df

        mock_convert_stringtime.side_effect = fake_convert_stringtime

        # calculate_energy_loss_pv: fixed value for each row
        mock_calc_energy_loss_pv.return_value = 50.0

        dict_power_pv = {
            i: {
                h: (
                    50.0 if (6 <= h <= 10 or 15 <= h <= 18)
                    else 100.0 if (11 <= h <= 15)
                    else 0.0
                )
                for h in range(24)
            }
            for i in range(1, 13)
        }

        # Convert to DataFrame (hours as rows, months as columns)
        dict_power_pv = pd.DataFrame(dict_power_pv)
        dict_power_pv.index.name = "hour"

        data_result = corrective_energy.corrective_layout(
            log_events=self.log_events,
            start_year=2025,
            start_month=1,
            n_lifetime=1,
            operations_corrective_stat=DUMMY_OPERATIONS_STATS,
            find_element_class=lambda *args, **kwargs: None,
            n_device_pv=20,
            G_pv=self.G_pv,
            dict_power_pv=dict_power_pv,
            degradation_rate=0.5,
            n_strings_per_inv=1,
            n_modules_per_strings=1,
            max_failure_module=1,
        )

        # Wind / wave not requested
        self.assertTrue(data_result['wind'].empty)
        self.assertTrue(data_result['wave'].empty)

        # Power_loss_kW updated via calculate_energy_loss_pv
        self.assertIn("Power_loss_kW", data_result['pv'].columns)
        self.assertListEqual(
            data_result['pv']["Power_loss_kW"].tolist(), [50.0, 50.0]
        )

        # calculate_energy_loss_pv must be called twice (two rows)
        self.assertEqual(mock_calc_energy_loss_pv.call_count, 2)

        # convert_stringtime must be called once with dt_column='Date'
        mock_convert_stringtime.assert_called_once()
        args, kwargs = mock_convert_stringtime.call_args
        self.assertIn("Date", kwargs['df'].columns)


if __name__ == "__main__":
    unittest.main(verbosity=2)
