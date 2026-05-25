import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pandas.testing as pdt

import pandas as pd

from oriom.core.results_block_manager import results_block


class DummyResults:
    def __init__(self):
        self.dfs_energy_yearly_month_dict = {
            "availability_month_wind": [],
            "availability_month_wave": [],
            "availability_month_pv": [],
        }
        self.dfs_energy_yearly_dict = {
            "availability_year_wind": [],
            "availability_year_wave": [],
            "availability_year_pv": [],
        }
        self.dfs_ctv_list = []
        self.dfs_tot_cost_list = []
        self.dfs_tot_yearly_cost_list = []
        self.kpi_om_type_cost_list = []
        self.dfs_log_events = []
        self.dfs_log_events_merged = []
        self.dfs_vessel_fuel_usage = []


class DummyVesselDayCounter:
    def __init__(self, log_events_merged=None, vessels=None):
        self.log_events_merged = log_events_merged
        self.vessels = vessels
        self.calls = []

    def allocate_vessels(self, log_events_merged=None, ST=False):
        self.calls.append({"log_events_merged": log_events_merged, "ST": ST})
        return log_events_merged.copy()


class TestResultsBlock(unittest.TestCase):
    def setUp(self):
        self.result_dir = "/tmp/test_result_dir"
        self.run_index = 0

        self.inputs = SimpleNamespace(
            general=SimpleNamespace(
                failureevent_file={"value": "/fake/failures"},
                logevents_file={"value": "/fake/logs"},
                number_runs={"value": 1},
            ),
            tseries=SimpleNamespace(
                failure_scenario={"value": "base"},
                scenario={"dummy": "scenario"},
                merge_vessel={"value": ["ctv"]},
                time_between_devices_dict={"device": 1.0},
                shift_duration={"value": 12},
            ),
            stats=SimpleNamespace(
                lifetime={"value": 20},
                start_year={"value": 2025},
                start_month={"value": 1},
                period_infant_mortality={"value": 0},
                period_wear_out={"value": 0},
                failure_ratio={"value": 1.0},
                percentile_max={"value": 95},
            ),
            cost=SimpleNamespace(
                fuel_cost_hfo={"value": 1.0},
                fuel_cost_mgo={"value": 2.0},
                fuel_cost_mdo={"value": 3.0},
                port_cost_year={"value": 1000.0},
                insurance_cost_year={"value": 2000.0},
                technicians_year={"value": 3000.0},
                electricity_price_dict={"wt": 50.0, "wec": 60.0, "pv": 70.0},
            ),
        )

        self.config = SimpleNamespace(
            TIME_FAIL_OP_IMMEDIATELY=2,
            STATISTICAL_CHART=False,
            ENERGY_AVAILABILITY_CALCULATION=True,
            ENERGY_STATISTICAL_CALCULATION=False,
        )

        self.find_element = MagicMock()
        self.failures = [MagicMock(id="f1")]
        self.operations_tow_stats = {"pmain": ["tow_main"], "pmax": ["tow_max"]}
        self.inspections_port_stats = {"pmain": ["port_main"], "pmax": ["port_max"]}
        self.inspections_site_stats = {"pmain": ["site_main"], "pmax": ["site_max"]}
        self.operations_corrective_stats = {"pmain": ["corr_main"], "pmax": ["corr_max"]}
        self.vessels = [MagicMock(id="ctv_1")]
        self.mother_vessels = [MagicMock(id="mv_1")]
        self.G_layouts = {"G_wind": MagicMock(), "G_wave": MagicMock(), "G_pv": MagicMock()}
        self.dict_power_wind = {"1": 100.0}
        self.dict_power_wave = {"1": 200.0}
        self.metocean_timeseries = pd.DataFrame({"p": [1, 2, 3]})

        self.farm_technologies = SimpleNamespace(
            power=SimpleNamespace(
                pv_farm_prod={"1": {0: 10.0}},
                degradation_rate=0.5,
                wtg_number_devices=10,
                wec_number_devices=5,
                pv_number_devices=20,
            )
        )

        self.results_dict = DummyResults()

        self.dates_failures_df = pd.DataFrame(
            {
                "datetime": pd.to_datetime(["2025-01-01 00:00:00"]),
                "id": ["f1.0"],
                'preferred_month': [1]
            }
        )

        self.log_events_df = pd.DataFrame(
            {
                "event": ["operation", "recommissioning"],
                "id": ["op1", "op2"],
                "n_vessel_1": [1, 1],
                "d_end": pd.to_datetime(["2025-01-02", "2025-01-03"]),
            }
        )

        self.log_events_merged_df = pd.DataFrame(
            {
                "event": ["operation", "recommissioning"],
                "id": ["op1", "op2"],
                "n_vessel_1": [1, 1],
                "d_end": pd.to_datetime(["2025-01-04", "2025-01-05"]),
            }
        )

        self.kpi_total_df = pd.DataFrame({"metric": ["a"], "value": [1.0]})
        self.kpi_yearly_df = pd.DataFrame({"year": [2025], "value": [2.0]})
        self.daily_vessel_df = pd.DataFrame({"day": [1], "vessel": ["ctv_1"]})

    @patch("oriom.core.results_block_manager.report_graphs.distribution_failures")
    @patch("oriom.core.results_block_manager.report_graphs.indirect_costs_per_year")
    @patch("oriom.core.results_block_manager.report_graphs.farm_availability")
    @patch("oriom.core.results_block_manager.report_graphs.energy_yield_combined")
    @patch("oriom.core.results_block_manager.report_graphs.energy_yield")
    @patch("oriom.core.results_block_manager.kpi_final_total_cost")
    @patch("oriom.core.results_block_manager.energy_availability")
    @patch("oriom.core.results_block_manager.config_energy_availability")
    @patch("oriom.core.results_block_manager.vessel_mobilisation_manager.reduce_redundant_mobilisations_inspection")
    @patch("oriom.core.results_block_manager.vessel_mobilisation_manager.create_yearly_mobilisation_mother_vessel")
    @patch("oriom.core.results_block_manager.VesselDayCounter")
    @patch("oriom.core.results_block_manager.create_logs_merge")
    @patch("oriom.core.results_block_manager.create_logs_timeseries_file")
    @patch("oriom.core.results_block_manager.failures_event")
    @patch("oriom.core.results_block_manager.os.makedirs")
    @patch("oriom.core.results_block_manager.aux_functions.save_file_csv")
    @patch("oriom.core.results_block_manager.aux_functions.log_event_convert_stringtime")
    @patch("oriom.core.results_block_manager.aux_functions.convert_stringtime")
    @patch("oriom.core.results_block_manager.pd.read_csv")
    def test_results_block_generates_all_outputs_when_previous_files_do_not_exist(
        self,
        mock_read_csv,
        mock_convert_stringtime,
        mock_log_event_convert_stringtime,
        mock_save_file_csv,
        mock_makedirs,
        mock_failures_event,
        mock_create_logs_timeseries_file,
        mock_create_logs_merge,
        mock_vessel_day_counter_cls,
        mock_create_yearly_mob,
        mock_reduce_redundant,
        mock_config_energy,
        mock_energy_availability,
        mock_kpi_final_total_cost,
        mock_energy_yield,
        mock_energy_yield_combined,
        mock_farm_availability,
        mock_indirect_costs_per_year,
        mock_distribution_failures,
    ):
        """
        This test covers the main generation path:
        - failures are generated
        - log events are generated
        - merged log events are generated
        - deferred overwrite path is applied
        - energy availability is calculated
        - KPI files are generated
        - result containers are updated
        """

        mock_read_csv.side_effect = FileNotFoundError
        mock_convert_stringtime.return_value = self.dates_failures_df.copy()
        mock_log_event_convert_stringtime.side_effect = lambda df: df.copy()

        mock_failures_event.return_value = self.dates_failures_df.copy()
        mock_create_logs_timeseries_file.return_value = self.log_events_df.copy()

        merged_after_create = self.log_events_merged_df.copy()
        deferred_log_df = pd.DataFrame({"event": ["deferred"]})
        mock_create_logs_merge.return_value = (
            merged_after_create,
            [0, 1],
            deferred_log_df,
        )

        vessel_day_counter_instance = DummyVesselDayCounter(
            log_events_merged=self.log_events_merged_df.copy(),
            vessels=self.vessels,
        )
        mock_vessel_day_counter_cls.return_value = vessel_day_counter_instance

        mock_create_yearly_mob.side_effect = lambda log_events_merged, mother_vessel_list: log_events_merged
        mock_reduce_redundant.side_effect = lambda log_events_merged, vessels: log_events_merged

        mock_config_energy.return_value = {
            "G_wind_copy": MagicMock(),
            "G_wave_copy": MagicMock(),
            "G_pv_copy": MagicMock(),
            "n_strings_per_inv": 2,
            "n_modules_per_strings": 3,
            "max_failure_module": 4,
        }

        availability_month_wind = pd.DataFrame({"Months": [1], "En_max_kWh": [1000], "En_loss_kWh": [100]})
        availability_year_wind = pd.DataFrame({"Years": [2025], "En_loss_kWh": [100], "En_availability": [99], "Time_availability": [98]})
        availability_month_wave = pd.DataFrame({"Months": [1], "En_max_kWh": [2000], "En_loss_kWh": [200]})
        availability_year_wave = pd.DataFrame({"Years": [2025], "En_loss_kWh": [200], "En_availability": [97], "Time_availability": [96]})
        availability_year_pv = pd.DataFrame({"Years": [2025], "En_loss_kWh": [300], "En_availability": [95], "Time_availability": [94]})

        mock_energy_availability.return_value = {
            "availability_month_wind": availability_month_wind,
            "availability_year_wind": availability_year_wind,
            "availability_month_wave": availability_month_wave,
            "availability_year_wave": availability_year_wave,
            "availability_year_pv": availability_year_pv,
        }

        mock_kpi_final_total_cost.return_value = (
            self.kpi_total_df,
            self.kpi_yearly_df,
            {"ctv_1": {"days": 12}},
            self.daily_vessel_df,
            {"corrective": 10.0},
            pd.DataFrame({
                "vessel_type": ["v001_ctv"],
                "transit": [80],
                "maneuver": [50],
                "standby": [20],
            })
        )

        with patch(
            "oriom.core.results_block_manager.manage_def_to_log_events",
            return_value=self.log_events_df.copy(),
        ) as mock_manage_def_to_log_events:
            results_block(
                result_dir_r=self.result_dir,
                r=self.run_index,
                inputs=self.inputs,
                Config=self.config,
                find_element=self.find_element,
                farm_technologies=self.farm_technologies,
                results_dict=self.results_dict,
                failures=self.failures,
                operations_tow_stats=self.operations_tow_stats,
                inspections_port_stats=self.inspections_port_stats,
                inspections_site_stats=self.inspections_site_stats,
                operations_corrective_stats=self.operations_corrective_stats,
                vessels=self.vessels,
                mother_vessels=self.mother_vessels,
                G_layouts=self.G_layouts,
                dict_power_wind=self.dict_power_wind,
                dict_power_wave=self.dict_power_wave,
                metocean_timeseries=self.metocean_timeseries,
            )

        mock_failures_event.assert_called_once()
        mock_create_logs_timeseries_file.assert_called_once()
        mock_create_logs_merge.assert_called_once()
        mock_manage_def_to_log_events.assert_called_once()

        self.assertGreaterEqual(len(vessel_day_counter_instance.calls), 1)
        self.assertTrue(any(call["ST"] is True for call in vessel_day_counter_instance.calls))

        mock_config_energy.assert_called_once()
        mock_energy_availability.assert_called_once()
        mock_kpi_final_total_cost.assert_called_once()

        called_df_month = mock_energy_yield.call_args_list[0][1]["df"]
        pdt.assert_frame_equal(called_df_month, availability_month_wind)
        called_df = mock_farm_availability.call_args_list[0][1]["df"]
        pdt.assert_frame_equal(called_df, availability_year_wind)
        called_df = mock_indirect_costs_per_year.call_args_list[0][1]["df"]
        pdt.assert_frame_equal(called_df, availability_year_wind)

        mock_energy_yield_combined.assert_called_once()
        mock_distribution_failures.assert_called_once()

        self.assertEqual(len(self.results_dict.dfs_tot_cost_list), 1)
        self.assertEqual(len(self.results_dict.dfs_tot_yearly_cost_list), 1)
        self.assertEqual(len(self.results_dict.kpi_om_type_cost_list), 1)
        self.assertEqual(len(self.results_dict.dfs_log_events), 1)
        self.assertEqual(len(self.results_dict.dfs_log_events_merged), 1)
        self.assertEqual(len(self.results_dict.dfs_ctv_list), 1)
        self.assertEqual(len(self.results_dict.dfs_vessel_fuel_usage), 1)

        self.assertEqual(len(self.results_dict.dfs_energy_yearly_month_dict["availability_month_wind"]), 1)
        self.assertEqual(len(self.results_dict.dfs_energy_yearly_month_dict["availability_month_wave"]), 1)
        self.assertEqual(len(self.results_dict.dfs_energy_yearly_dict["availability_year_wind"]), 1)
        self.assertEqual(len(self.results_dict.dfs_energy_yearly_dict["availability_year_wave"]), 1)
        self.assertEqual(len(self.results_dict.dfs_energy_yearly_dict["availability_year_pv"]), 1)

        mock_makedirs.assert_called_once_with(os.path.join(self.result_dir, "graph_dir"))

    @patch("oriom.core.results_block_manager.report_graphs.distribution_failures")
    @patch("oriom.core.results_block_manager.kpi_final_total_cost")
    @patch("oriom.core.results_block_manager.VesselDayCounter")
    @patch("oriom.core.results_block_manager.aux_functions.save_file_csv")
    @patch("oriom.core.results_block_manager.aux_functions.log_event_convert_stringtime")
    @patch("oriom.core.results_block_manager.aux_functions.convert_stringtime")
    @patch("oriom.core.results_block_manager.pd.read_csv")
    @patch("oriom.core.results_block_manager.os.makedirs")
    def test_results_block_reuses_previous_files_and_skips_energy_when_disabled(
        self,
        mock_makedirs,
        mock_read_csv,
        mock_convert_stringtime,
        mock_log_event_convert_stringtime,
        mock_save_file_csv,
        mock_vessel_day_counter_cls,
        mock_kpi_final_total_cost,
        mock_distribution_failures,
    ):
        """
        This test covers the reuse path:
        - failure file is loaded from a previous run
        - log_events file is loaded from a previous run
        - merged log_events file is loaded from a previous run
        - energy availability is skipped
        - KPI path still runs
        """

        config = SimpleNamespace(
            TIME_FAIL_OP_IMMEDIATELY=2,
            STATISTICAL_CHART=False,
            ENERGY_AVAILABILITY_CALCULATION=False,
            ENERGY_STATISTICAL_CALCULATION=False,
        )

        mock_read_csv.side_effect = [
            self.dates_failures_df.copy(),
            self.log_events_df.copy(),
            self.log_events_merged_df.copy(),
        ]
        mock_convert_stringtime.return_value = self.dates_failures_df.copy()
        mock_log_event_convert_stringtime.side_effect = lambda df: df.copy()

        vessel_day_counter_instance = DummyVesselDayCounter(
            log_events_merged=self.log_events_merged_df.copy(),
            vessels=self.vessels,
        )
        mock_vessel_day_counter_cls.return_value = vessel_day_counter_instance

        mock_kpi_final_total_cost.return_value = (
            self.kpi_total_df,
            self.kpi_yearly_df,
            {},
            self.daily_vessel_df,
            {"preventive": 20.0},
            pd.DataFrame({
                "vessel_type": ["v001_ctv"],
                "transit": [80],
                "maneuver": [50],
                "standby": [20],
            })
        )

        with patch("oriom.core.results_block_manager.failures_event") as mock_failures_event, \
             patch("oriom.core.results_block_manager.create_logs_timeseries_file") as mock_create_logs_timeseries_file, \
             patch("oriom.core.results_block_manager.create_logs_merge") as mock_create_logs_merge, \
             patch("oriom.core.results_block_manager.config_energy_availability") as mock_config_energy, \
             patch("oriom.core.results_block_manager.energy_availability") as mock_energy_availability, \
             patch("oriom.core.results_block_manager.report_graphs.energy_yield") as mock_energy_yield, \
             patch("oriom.core.results_block_manager.report_graphs.energy_yield_combined") as mock_energy_yield_combined, \
             patch("oriom.core.results_block_manager.report_graphs.farm_availability") as mock_farm_availability, \
             patch("oriom.core.results_block_manager.report_graphs.indirect_costs_per_year") as mock_indirect_costs_per_year:

            results_block(
                result_dir_r=self.result_dir,
                r=self.run_index,
                inputs=self.inputs,
                Config=config,
                find_element=self.find_element,
                farm_technologies=self.farm_technologies,
                results_dict=self.results_dict,
                failures=self.failures,
                operations_tow_stats=self.operations_tow_stats,
                inspections_port_stats=self.inspections_port_stats,
                inspections_site_stats=self.inspections_site_stats,
                operations_corrective_stats=self.operations_corrective_stats,
                vessels=self.vessels,
                mother_vessels=self.mother_vessels,
                G_layouts=self.G_layouts,
                dict_power_wind=self.dict_power_wind,
                dict_power_wave=self.dict_power_wave,
                metocean_timeseries=self.metocean_timeseries,
            )

        mock_failures_event.assert_not_called()
        mock_create_logs_timeseries_file.assert_not_called()
        mock_create_logs_merge.assert_not_called()
        mock_config_energy.assert_not_called()
        mock_energy_availability.assert_not_called()
        mock_energy_yield.assert_not_called()
        mock_energy_yield_combined.assert_not_called()
        mock_farm_availability.assert_not_called()
        mock_indirect_costs_per_year.assert_not_called()

        self.assertEqual(len(vessel_day_counter_instance.calls), 1)
        self.assertTrue(vessel_day_counter_instance.calls[0]["ST"])

        mock_kpi_final_total_cost.assert_called_once()
        mock_distribution_failures.assert_called_once()
        mock_makedirs.assert_called_once_with(os.path.join(self.result_dir, "graph_dir"))

        self.assertEqual(len(self.results_dict.dfs_ctv_list), 0)

    @patch("oriom.core.results_block_manager.create_logs_timeseries_file")
    @patch("oriom.core.results_block_manager.failures_event")
    @patch("oriom.core.results_block_manager.pd.read_csv", side_effect=FileNotFoundError)
    @patch("oriom.core.results_block_manager.aux_functions.save_file_csv")
    def test_results_block_raises_when_log_events_are_empty(
        self,
        mock_save_file_csv,
        mock_read_csv,
        mock_failures_event,
        mock_create_logs_timeseries_file,
    ):
        """
        This test covers the explicit guard that raises when log_events is empty.
        """

        mock_failures_event.return_value = self.dates_failures_df.copy()
        mock_create_logs_timeseries_file.return_value = pd.DataFrame()

        with self.assertRaises(Exception) as ctx:
            results_block(
                result_dir_r=self.result_dir,
                r=self.run_index,
                inputs=self.inputs,
                Config=self.config,
                find_element=self.find_element,
                farm_technologies=self.farm_technologies,
                results_dict=self.results_dict,
                failures=self.failures,
                operations_tow_stats=self.operations_tow_stats,
                inspections_port_stats=self.inspections_port_stats,
                inspections_site_stats=self.inspections_site_stats,
                operations_corrective_stats=self.operations_corrective_stats,
                vessels=self.vessels,
                mother_vessels=self.mother_vessels,
                G_layouts=self.G_layouts,
                dict_power_wind=self.dict_power_wind,
                dict_power_wave=self.dict_power_wave,
                metocean_timeseries=self.metocean_timeseries,
            )

        self.assertIn("log_events dataframe is empty", str(ctx.exception))
        mock_failures_event.assert_called_once()
        mock_create_logs_timeseries_file.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)