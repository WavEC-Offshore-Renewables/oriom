import unittest
from unittest.mock import patch
from datetime import datetime

import pandas as pd
import numpy as np
import networkx as nx

from oriom.core.functions.layout_power import layout_power as ea

class DummyPower():
    def __init__(self, pv_dev, max_fail_mode):
        self.pv_number_devices = pv_dev
        self.pv_max_failure_module = max_fail_mode

class DummyPV:
    def __init__(self, n_strings, n_inv):
        self.number_strings = n_strings
        self.number_inverters = n_inv

class DummyFarm():
    def __init__(self, dummy_pv, dummy_power):
        self.pv = dummy_pv
        self.power = dummy_power
        


class TestFixValues(unittest.TestCase):
    def test_fix_values_clamps_above_100_and_below_0_1(self):
        df = pd.DataFrame(
            {
                "En_availability": [120.0, 100.0, 0.05, 50.0, -10.0]
            }
        )

        ea.fix_values(df, "En_availability")

        # >100 -> 100
        self.assertEqual(df.loc[0, "En_availability"], 100.0)
        self.assertEqual(df.loc[1, "En_availability"], 100.0)
        # <0.1 -> 0
        self.assertEqual(df.loc[2, "En_availability"], 0.0)
        self.assertEqual(df.loc[4, "En_availability"], 0.0)
        # Internal value remains unchanged
        self.assertEqual(df.loc[3, "En_availability"], 50.0)


class TestSumByMonthYear(unittest.TestCase):
    def test_sum_by_month_year_filters_correct_year_and_month(self):
        times = pd.to_datetime(
            [
                "2025-01-01 00:00:00",
                "2025-01-15 00:00:00",
                "2025-02-01 00:00:00",
                "2024-01-01 00:00:00",
            ]
        )
        ts = pd.DataFrame({"p_wind": [10.0, 20.0, 30.0, 40.0]}, index=times)

        total_jan_2025 = ea.sum_by_month_year(ts, 2025, 1, "p_wind")
        self.assertEqual(total_jan_2025, 10.0 + 20.0)

        total_feb_2025 = ea.sum_by_month_year(ts, 2025, 2, "p_wind")
        self.assertEqual(total_feb_2025, 30.0)

        total_jan_2024 = ea.sum_by_month_year(ts, 2024, 1, "p_wind")
        self.assertEqual(total_jan_2024, 40.0)


class TestCalculateEnergy(unittest.TestCase):
    def test_calculate_energy_pv_dict_of_dicts_with_degradation(self):
        """
        dict_power with dict values → PV-style branch.
        p0 = sum(power)*days*hour_energy
        then apply iterative degradation for (y-start_year) years.
        """
        dict_power = {
            1: {0: 1.0, 1: 2.0}  # sum=3
        }
        dict_days = {1: 30}
        hour_energy = 1.0
        degradation_rate = 10.0  # 10%
        start_year = 2020
        y = 2022  # 2 degradation steps

        p0 = 3.0 * 30 * 1.0  # 90
        expected = p0 * (0.9 ** 2)  # two years

        result = ea.calculate_energy(
            dict_power=dict_power,
            dict_days=dict_days,
            key=1,
            y=y,
            start_year=start_year,
            hour_energy=hour_energy,
            degradation_rate=degradation_rate,
            ENERGY_STATISTICAL_CALCULATION=True,
        )
        self.assertAlmostEqual(result, expected, places=7)

    def test_calculate_energy_non_pv_statistical(self):
        """
        dict_power scalar and ENERGY_STATISTICAL_CALCULATION=True:
        energy = power * days * hour_energy
        """
        dict_power = {1: 10.0}
        dict_days = {1: 31}
        hour_energy = 24.0

        result = ea.calculate_energy(
            dict_power=dict_power,
            dict_days=dict_days,
            key=1,
            y=2025,
            start_year=2020,
            hour_energy=hour_energy,
            degradation_rate=0.0,
            ENERGY_STATISTICAL_CALCULATION=True,
        )
        self.assertEqual(result, 10.0 * 31 * 24.0)

    def test_calculate_energy_non_pv_from_metocean(self):
        """
        dict_power scalar and ENERGY_STATISTICAL_CALCULATION=False:
        uses sum_by_month_year(metocean_timeseries, ...)
        """
        times = pd.to_datetime(
            [
                "2025-01-01 00:00:00",
                "2025-01-01 01:00:00",
                "2025-02-01 00:00:00",
            ]
        )
        metocean = pd.DataFrame({"p_wind": [5.0, 5.0, 100.0]}, index=times)

        dict_power = {1: 999.0}  # ignored in this branch
        dict_days = {1: 31}

        result = ea.calculate_energy(
            dict_power=dict_power,
            dict_days=dict_days,
            key=1,
            y=2025,
            start_year=2020,
            hour_energy=24.0,
            degradation_rate=0.0,
            ENERGY_STATISTICAL_CALCULATION=False,
            metocean_timeseries=metocean,
            power_col="p_wind",
        )
        # Should be 5 + 5 = 10 (only January 2025)
        self.assertEqual(result, 10.0)


class TestGetEnergyData(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-15 00:00:00",
                        "2025-02-01 00:00:00",
                    ]
                ),
                "En_loss_kWh": [10.0, 20.0, 30.0],
                "Time_shutdown": [1.0, 2.0, 3.0],
                "Time_operation": [4.0, 5.0, 6.0],
                "hour_diff_next": [1.0, 2.0, 3.0],
            }
        )

    def test_get_energy_data_preventive_year(self):
        months, loss, shutdown, time_op = ea.get_energy_data(
            self.df, year=2025, mode="preventive"
        )
        self.assertListEqual(sorted(list(months)), [1, 1, 2])
        self.assertEqual(loss, 10.0 + 20.0 + 30.0)
        self.assertEqual(shutdown, 1.0 + 2.0 + 3.0)
        self.assertIsNone(time_op)

    def test_get_energy_data_corrective_month(self):
        months, loss, shutdown, time_op = ea.get_energy_data(
            self.df, year=2025, month=1, mode="corrective"
        )
        # Only the first two rows (month=1)
        self.assertListEqual(sorted(list(months)), [1, 1])
        self.assertEqual(loss, 10.0 + 20.0)
        self.assertEqual(shutdown, 4.0 + 5.0)
        self.assertEqual(time_op, 1.0 + 2.0)

    def test_get_energy_data_missing_columns_returns_fallback(self):
        df_bad = pd.DataFrame({"foo": [1, 2, 3]})  # no 'Date'
        months, loss, shutdown, time_op = ea.get_energy_data(
            df_bad, year=2025, mode="preventive"
        )
        self.assertEqual(list(months), [])
        self.assertEqual(loss, 0)
        self.assertEqual(shutdown, 0)
        self.assertIsNone(time_op)


class DummyOp:
    def __init__(self, id, tow_to_port=False):
        self.id = id
        self.tow_to_port = tow_to_port

class DummyStats:
    def __init__(self, start_year, start_month, lifetime):
        self.start_year = start_year
        self.start_month = start_month
        self.lifetime = lifetime

class DummyGen:
    def __init__(self, energy_path):
        self.powerevent_file = energy_path

class DummyInput:
    def __init__(self, start_year, start_month, lifetime, energy_path):
        self.stats = DummyStats(start_year, start_month, lifetime)
        self.general = DummyGen(energy_path)



class TestEnergyAvailabilityWindIntegration(unittest.TestCase):
    """
    Simplified integration test for energy_availability, wind branch.
    """

    @patch("oriom.core.functions.layout_power.layout_power.preventive_energy")
    @patch("oriom.core.functions.layout_power.layout_power.corrective_layout")
    def test_energy_availability_wind_single_year(
        self, mock_corrective_layout, mock_preventive_energy
    ):
        # --- minimal log_events (used only for ordering) ---
        log_events_energy = pd.DataFrame(
            {
                "event": ["failure"],
                "d_end_transit_ts": [pd.Timestamp("2025-01-01 00:00:00")],
            }
        )

        corrective_res = {}
        preventive_res = {}

        df_wind_corr = pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    [
                        "2025-01-01 00:00:00",
                        "2025-01-02 00:00:00",
                        "2025-01-03 00:00:00",
                    ]
                ),
                "Perc_availability": [100.0, 50.0, 100.0],
                "Power_loss_kW": [0.0, 10.0, 0.0],
            }
        )
        df_wind_prev = pd.DataFrame(
                {
                    "Date": pd.to_datetime(["2025-01-15 00:00:00"]),
                    "En_loss_kWh": [100.0],
                    "Time_shutdown": [5.0]
                }
        )

        corrective_res['wind'] = df_wind_corr.copy()
        corrective_res['wave'] = pd.DataFrame()
        corrective_res['pv'] = pd.DataFrame()

        preventive_res['wind'] = df_wind_prev.copy()
        preventive_res['wave'] = pd.DataFrame()
        preventive_res['pv'] = pd.DataFrame()

        # --- df_corrective for wind (3 rows for time_op>0) ---
        mock_corrective_layout.return_value = (corrective_res)
        # --- df_preventive for wind ---
        mock_preventive_energy.return_value = (preventive_res)

        # power_wind as dict: only January
        power_wind = {1: 10.0}
        n_device_wtg = 10

        # Dummy operations_corrective_stat not empty
        ops_corr_stats = [DummyOp("op_corr_001", tow_to_port=False)]

        inputs = DummyInput({'value': 2025}, {'value': 1}, {'value': 1}, {'value': 'path'})

        result = ea.energy_availability(
            inputs=inputs,
            r=1,
            log_events_energy=log_events_energy,
            operations_corrective_stat=ops_corr_stats,
            inspections_site_stat=[],
            inspections_port_stat=[],
            find_element_class=lambda *args, **kwargs: None,
            power_wind=power_wind,
            power_wave=None,
            power_pv=None,
            degradation_rate=None,
            n_device_wtg=n_device_wtg,
            n_device_wec=None,
            n_device_pv=None,
            G_wind=None,
            G_wave=None,
            G_pv=None,
            metocean_timeseries=pd.DataFrame(),
            ENERGY_STATISTICAL_CALCULATION=True,
        )

        self.assertIn("Availability_year_wind", result)
        self.assertIn("Availability_month_wind", result)

        df_y = result["Availability_year_wind"]
        df_m = result["Availability_month_wind"]

        # Single year: 2025
        self.assertEqual(df_y["Years"].tolist(), [2025])

        # Expected total energy:
        # power_wind[1]=10 kW, 31 days, 24h/day → 10*31*24 = 7440 kWh
        en_total_expected = 10.0 * 31 * 24
        self.assertAlmostEqual(df_y.loc[0, "En_max_kWh"], en_total_expected, places=6)

        # df_corrective → En_loss_kWh = 240 (see analysis below)
        # df_preventive → 100
        # TOT loss = 340
        self.assertAlmostEqual(df_y.loc[0, "En_loss_kWh"], 340.0, places=6)

        # Expected energy availability:
        # (7440 - 340)/7440 * 100
        en_av_expected = (en_total_expected - 340.0) / en_total_expected * 100.0
        self.assertAlmostEqual(df_y.loc[0, "En_availability"], en_av_expected, places=5)

        # Check that January monthly is also populated
        self.assertTrue(
            ((df_m["Years"] == 2025) & (df_m["Months"] == 1)).any()
        )
        row_m = df_m[(df_m["Years"] == 2025) & (df_m["Months"] == 1)].iloc[0]
        self.assertAlmostEqual(row_m["En_max_kWh"], en_total_expected, places=6)
        self.assertAlmostEqual(row_m["En_loss_kWh"], 340.0, places=6)
        # Monthly En_availability same as annual in this simple case
        self.assertAlmostEqual(row_m["En_availability"], en_av_expected, places=5)


class TestEnergyAvailabilityPVErrors(unittest.TestCase):
    """
    Test of associated error at power_pv_df without degradation_rate.
    """

    @patch("oriom.core.functions.layout_power.layout_power.preventive_energy")
    @patch("oriom.core.functions.layout_power.layout_power.corrective_layout")
    def test_pv_power_without_degradation_raises_value_error(
        self, mock_corrective_layout, mock_preventive_energy
    ):
        # minimal log_events
        log_events_energy = pd.DataFrame(
            {
                "event": ["failure"],
                "d_end_transit_ts": [pd.Timestamp("2025-01-01 00:00:00")],
            }
        )

        # Stub: we will never reach here because error occurs earlier,
        # but for safety return empty DataFrames
        mock_corrective_layout.return_value = (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )
        mock_preventive_energy.return_value = (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )

        # PV DataFrame 24x12 (hours x months)
        months = list(range(1, 13))
        power_pv_df = pd.DataFrame({m: [1.0] * 24 for m in months})

        inputs = DummyInput({'value': 2025}, {'value': 1}, {'value': 1}, {'value': 'path'})
        
        with self.assertRaises(ValueError):
            ea.energy_availability(
                inputs= inputs,
                r = 1,
                log_events_energy=log_events_energy,
                operations_corrective_stat=[DummyOp("op_corr_001")],
                inspections_site_stat=[],
                inspections_port_stat=[],
                find_element_class=lambda *args, **kwargs: None,
                power_wind=None,
                power_wave=None,
                power_pv=power_pv_df,   # defined
                degradation_rate=None,  # missing → should raise ValueError
                n_device_wtg=None,
                n_device_wec=None,
                n_device_pv=10,
                G_wind=None,
                G_wave=None,
                G_pv=None,
            )


class TestConfigEnergyAvailability(unittest.TestCase):
    """Test to the configuration of energy availability"""

    def test_config_energy_availability(self):
        # Arrange
        G_lay = {name_G: nx.DiGraph() for name_G in ['G_wind', 'G_wave', 'G_pv']}

        pv = DummyPV(10, 2)
        power = DummyPower(100, 5)
        farm_tech = DummyFarm(pv, power)

        # Act
        result = ea.config_energy_availability(
            G_layouts=G_lay,
            farm_technologies=farm_tech
        )

        # Assert graph
        self.assertIsNotNone(result['G_wind_copy'])
        self.assertIsNotNone(result['G_wave_copy'])
        self.assertIsNotNone(result['G_pv_copy'])

        self.assertIsInstance(result['G_wind_copy'], nx.DiGraph)
        self.assertIsInstance(result['G_wave_copy'], nx.DiGraph)
        self.assertIsInstance(result['G_pv_copy'], nx.DiGraph)
        self.assertIsNot(result['G_wind_copy'], G_lay['G_wind'])
        self.assertIsNot(result['G_wave_copy'], G_lay['G_wave'])
        self.assertIsNot(result['G_pv_copy'], G_lay['G_pv'])

        # Assert PV
        expected_modules_per_string = 100 / (10 * 2)
        self.assertEqual(result['n_modules_per_strings'], expected_modules_per_string)
        self.assertEqual(result['n_strings_per_inv'], 10)
        self.assertEqual(result['max_failure_module'], 5)

    def test_config_energy_availability_no_pv(self):
        G_lay = {'G_wind': nx.DiGraph(), 'G_wave': nx.DiGraph(), 'G_pv': nx.DiGraph()}

        pv = DummyPV(0, 0)
        power = DummyPower(None, None)
        farm_tech = DummyFarm(pv, power)

        result = ea.config_energy_availability(
            G_layouts=G_lay,
            farm_technologies=farm_tech
        )

        self.assertIsNone(result['n_modules_per_strings'])
        self.assertIsNone(result['n_strings_per_inv'])
        self.assertIsNone(result['max_failure_module'])


class TestRecicleFile(unittest.TestCase):
    """
    Tests for recicle_file: checks reuse of corrective/preventive CSV files
    when available, and recompute flag when files are missing or path is invalid.
    """

    def _make_inputs(self, powerevent_path):
        """Helper to build a DummyInput with a given powerevent_file path."""
        return DummyInput(
            {'value': 2025},   # start_year
            {'value': 1},      # start_month
            {'value': 1},      # lifetime
            {'value': powerevent_path}  # powerevent_file
        )

    # ------------------------------------------------------------------
    # Scenario 1: all CSV files exist → data loaded, need_recompute=False
    # ------------------------------------------------------------------
    @patch("oriom.core.functions.layout_power.layout_power.aux_functions.convert_stringtime")
    @patch("pandas.read_csv")
    @patch("os.path.exists")
    def test_all_files_exist_returns_data_no_recompute(
        self, mock_exists, mock_read_csv, mock_convert
    ):
        df_corr = pd.DataFrame({'Date': ['2025-01-01'], 'value': [1.0]})
        df_prev = pd.DataFrame({'Date': ['2025-01-01'], 'value': [2.0]})

        # Both corrective and preventive CSVs exist for every tech
        mock_exists.return_value = True
        # read_csv alternates: corrective then preventive for each tech
        mock_read_csv.side_effect = [
            df_corr.copy(), df_prev.copy(),  # wind
            df_corr.copy(), df_prev.copy(),  # wave
            df_corr.copy(), df_prev.copy(),  # pv
        ]

        inputs = self._make_inputs('some/path')
        tech_devices = {'wind': 5, 'wave': 3, 'pv': 10}

        data, need_recompute = ea.recicle_file(inputs, r=1, tech_devices=tech_devices)

        self.assertFalse(need_recompute)
        for tech in ['wind', 'wave', 'pv']:
            self.assertFalse(data['corrective'][tech].empty)
            self.assertFalse(data['preventive'][tech].empty)

    # ------------------------------------------------------------------
    # Scenario 2: one tech has no device (None) → empty DataFrame inserted
    # ------------------------------------------------------------------
    @patch("oriom.core.functions.layout_power.layout_power.aux_functions.convert_stringtime")
    @patch("pandas.read_csv")
    @patch("os.path.exists")
    def test_none_device_inserts_empty_dataframe(
        self, mock_exists, mock_read_csv, mock_convert
    ):
        df_corr = pd.DataFrame({'Date': ['2025-01-01'], 'value': [1.0]})
        df_prev = pd.DataFrame({'Date': ['2025-01-01'], 'value': [2.0]})

        mock_exists.return_value = True
        mock_read_csv.side_effect = [
            df_corr.copy(), df_prev.copy(),  # wind
            df_corr.copy(), df_prev.copy(),  # pv
        ]

        inputs = self._make_inputs('some/path')
        tech_devices = {'wind': 5, 'wave': None, 'pv': 10}

        data, need_recompute = ea.recicle_file(inputs, r=1, tech_devices=tech_devices)

        self.assertFalse(need_recompute)
        self.assertTrue(data['corrective']['wave'].empty)
        self.assertTrue(data['preventive']['wave'].empty)

    # ------------------------------------------------------------------
    # Scenario 3: a CSV is missing → need_recompute=True, loop breaks
    # ------------------------------------------------------------------
    @patch("os.path.exists")
    def test_missing_file_sets_need_recompute(self, mock_exists):
        # Simulate that at least one file does not exist
        mock_exists.return_value = False

        inputs = self._make_inputs('some/path')
        tech_devices = {'wind': 5, 'wave': 3, 'pv': 10}

        data, need_recompute = ea.recicle_file(inputs, r=1, tech_devices=tech_devices)

        self.assertTrue(need_recompute)

    # ------------------------------------------------------------------
    # Scenario 4: powerevent_file is None → TypeError caught → need_recompute=True
    # ------------------------------------------------------------------
    def test_none_powerevent_path_sets_need_recompute(self):
        inputs = self._make_inputs(None)  # will raise TypeError in os.path.join
        tech_devices = {'wind': 5, 'wave': 3, 'pv': 10}

        data, need_recompute = ea.recicle_file(inputs, r=1, tech_devices=tech_devices)

        self.assertTrue(need_recompute)

    # ------------------------------------------------------------------
    # Scenario 5: CSV exists but is empty → stored as empty DataFrame,
    #             convert_stringtime NOT called
    # ------------------------------------------------------------------
    @patch("oriom.core.functions.layout_power.layout_power.aux_functions.convert_stringtime")
    @patch("pandas.read_csv")
    @patch("os.path.exists")
    def test_empty_csv_skips_convert_stringtime(
        self, mock_exists, mock_read_csv, mock_convert
    ):
        mock_exists.return_value = True
        mock_read_csv.return_value = pd.DataFrame()  # always empty

        inputs = self._make_inputs('some/path')
        tech_devices = {'wind': 5}

        data, need_recompute = ea.recicle_file(inputs, r=1, tech_devices=tech_devices)

        mock_convert.assert_not_called()
        self.assertFalse(need_recompute)
        self.assertTrue(data['corrective']['wind'].empty)
        self.assertTrue(data['preventive']['wind'].empty)

        
if __name__ == "__main__":
    unittest.main(verbosity=2)
