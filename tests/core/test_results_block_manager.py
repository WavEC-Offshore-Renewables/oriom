# tests/core/test_results_block_manager.py

import os
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pandas.testing as pdt

from oriom.core.results_block_manager import results_block


MODULE = "oriom.core.results_block_manager"


class DummyResults:
    """Minimal results container required by results_block."""

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
        self.dfs_failures = {}
        self.dfs_ctv_list = []
        self.dfs_tot_cost_list = []
        self.dfs_tot_yearly_cost_list = []
        self.kpi_om_type_cost_list = []
        self.dfs_log_events = []
        self.dfs_log_events_merged = []
        self.dfs_vessel_fuel_usage = []
        self.dfs_energy_data = []


class DummyVesselDayCounter:
    """Record calls while returning a valid merged-log DataFrame."""

    def __init__(self, log_events_merged=None, vessels=None):
        self.log_events_merged = log_events_merged
        self.vessels = vessels
        self.calls = []

    def allocate_vessels(self, log_events_merged=None, ST_contract=False, **kwargs):
        self.calls.append(
            {"log_events_merged": log_events_merged, "ST_contract": ST_contract, **kwargs}
        )
        source = (
            log_events_merged
            if log_events_merged is not None
            else self.log_events_merged
        )
        return source.copy()


class TestResultsBlock(unittest.TestCase):
    """Tests for new generation, previous-file reuse and empty-log guard."""

    def setUp(self):
        self.result_dir = os.path.join("fake", "test_result_dir")
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
                ST_O_M=False,
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
            FUEL_TO_ADD={},
            MOBILISATION_TO_ADD={},
            ST=False,
        )

        self.find_element = MagicMock()
        self.failures = [MagicMock(id="f1")]
        self.operations_tow_stats = {
            "pmain": ["tow_main"],
            "pmax": ["tow_max"],
        }
        self.inspections_port_stats = {
            "pmain": ["port_main"],
            "pmax": ["port_max"],
        }
        self.inspections_site_stats = {
            "pmain": ["site_main"],
            "pmax": ["site_max"],
        }
        self.operations_corrective_stats = {
            "pmain": ["corr_main"],
            "pmax": ["corr_max"],
        }
        self.vessels = [MagicMock(id="ctv_1")]
        self.mother_vessels = [MagicMock(id="mv_1")]
        self.G_layouts = {
            "G_wind": MagicMock(),
            "G_wave": MagicMock(),
            "G_pv": MagicMock(),
        }
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
                "preferred_month": [1],
            }
        )
        self.log_events_df = pd.DataFrame(
            {
                "d_trigger": pd.to_datetime(["2025-01-01", "2025-01-02"]),
                "d_end_wait_start": pd.to_datetime(["2025-01-01", "2025-01-02"]),
                "event": ["operation", "recommissioning"],
                "id": ["op1", "op2"],
                "n_vessel_1": [1, 1],
                "d_end": pd.to_datetime(["2025-01-02", "2025-01-03"]),
            }
        )
        self.log_events_merged_df = pd.DataFrame(
            {
                "d_trigger": pd.to_datetime(["2025-01-01", "2025-01-02"]),
                "d_end_wait_start": pd.to_datetime(["2025-01-01", "2025-01-02"]),
                "event": ["operation", "recommissioning"],
                "id": ["op1", "op2"],
                "n_vessel_1": [1, 1],
                "d_end": pd.to_datetime(["2025-01-04", "2025-01-05"]),
            }
        )
        self.kpi_total_df = pd.DataFrame(
            {
                "vessel_id": ["v001", "technician", "insurance", "port", "total"],
                "tot_mobilization_costs": [0, 0, 0, 0, 0],
                "tot_vessel_costs": [0, 0, 0, 0, 0],
                "tot_technicians_costs": [0, 0, 0, 0, 0],
                "tot_part_costs": [0, 0, 0, 0, 0],
                "tot_rov_costs": [0, 0, 0, 0, 0],
                "tot_other_costs": [0, 0, 0, 0, 0],
                "value": [1.0, 0, 0, 0, 1.0],
                "lifetime_direct_costs": [1.0, 0, 0, 0, 1.0],
            }
        )
        self.kpi_yearly_df = pd.DataFrame({"year": [2025], "value": [2.0]})
        self.daily_vessel_df = pd.DataFrame({"day": [1], "vessel": ["ctv_1"]})
        self.fuel_usage_df = pd.DataFrame(
            {
                "vessel_type": ["v001_ctv"],
                "transit": [80],
                "maneuver": [50],
                "standby": [20],
            }
        )
        self.availability_month_wind = pd.DataFrame(
            {"Months": [1], "En_max_kWh": [1000], "En_loss_kWh": [100]}
        )
        self.availability_year_wind = pd.DataFrame(
            {
                "Years": [2025],
                "En_loss_kWh": [100],
                "En_availability": [99],
                "Time_availability": [98],
            }
        )
        self.availability_month_wave = pd.DataFrame(
            {"Months": [1], "En_max_kWh": [2000], "En_loss_kWh": [200]}
        )
        self.availability_year_wave = pd.DataFrame(
            {
                "Years": [2025],
                "En_loss_kWh": [200],
                "En_availability": [97],
                "Time_availability": [96],
            }
        )
        self.availability_year_pv = pd.DataFrame(
            {
                "Years": [2025],
                "En_loss_kWh": [300],
                "En_availability": [95],
                "Time_availability": [94],
            }
        )

    @staticmethod
    def _patch_dependencies(stack):
        """Patch dependencies by name to avoid decorator-argument order errors."""
        targets = {
            "read_csv": "pd.read_csv",
            "convert_stringtime": "aux_functions.convert_stringtime",
            "log_event_convert_stringtime": "aux_functions.log_event_convert_stringtime",
            "save_file_csv": "aux_functions.save_file_csv",
            "makedirs": "os.makedirs",
            "failures_event": "failures_event",
            "create_logs_timeseries_file": "create_logs_timeseries_file",
            "create_logs_merge": "create_logs_merge",
            "manage_def_to_log_events": "manage_def_to_log_events",
            "VesselDayCounter": "VesselDayCounter",
            "create_yearly_mob": (
                "vessel_mobilisation_manager.create_yearly_mobilisation_mother_vessel"
            ),
            "reduce_redundant": (
                "vessel_mobilisation_manager.reduce_redundant_mobilisations_inspection"
            ),
            "mobilitate_second_vessel": (
                "vessel_mobilisation_manager.mobilitate_second_vessel"
            ),
            "config_energy": "config_energy_availability",
            "energy_availability": "energy_availability",
            "kpi_final_total_cost": "kpi_final_total_cost",
            "graphs_simulation_creation": "graphs_simulation_creation",
            "availability_graph_manager": "availability_graph_manager"
        }
        return {
            name: stack.enter_context(patch(f"{MODULE}.{target}"))
            for name, target in targets.items()
        }

    def _configure_common_mocks(self, mocks):
        """Return valid domain-shaped outputs from all mocked dependencies."""
        mocks["convert_stringtime"].return_value = self.dates_failures_df.copy()
        mocks["log_event_convert_stringtime"].side_effect = lambda df: df.copy()
        mocks["failures_event"].return_value = self.dates_failures_df.copy()
        mocks["create_logs_timeseries_file"].return_value = self.log_events_df.copy()
        mocks["create_logs_merge"].return_value = (
            self.log_events_merged_df.copy(),
            [0, 1],
            pd.DataFrame({"event": ["deferred"]}),
            {},
        )
        mocks["manage_def_to_log_events"].return_value = self.log_events_df.copy()
        mocks["create_yearly_mob"].side_effect = (
            lambda log_events_merged, mother_vessel_list: log_events_merged
        )
        mocks["reduce_redundant"].side_effect = (
            lambda log_events_merged, vessels: log_events_merged
        )
        mocks["mobilitate_second_vessel"].side_effect = (
            lambda log_events_merged, find_element_class, operations_tow:
            log_events_merged
        )

        counter = DummyVesselDayCounter(
            log_events_merged=self.log_events_merged_df.copy(),
            vessels=self.vessels,
        )
        mocks["VesselDayCounter"].return_value = counter

        mocks["config_energy"].return_value = {
            "G_wind_copy": MagicMock(),
            "G_wave_copy": MagicMock(),
            "G_pv_copy": MagicMock(),
            "n_strings_per_inv": 2,
            "n_modules_per_strings": 3,
            "max_failure_module": 4,
        }
        mocks["energy_availability"].return_value = {
            "availability_month_wind": self.availability_month_wind,
            "availability_year_wind": self.availability_year_wind,
            "availability_month_wave": self.availability_month_wave,
            "availability_year_wave": self.availability_year_wave,
            "availability_year_pv": self.availability_year_pv,
        }, {
            "corrective": {"wind": pd.DataFrame()},
            "preventive": {"wind": pd.DataFrame()},
        }
        mocks["kpi_final_total_cost"].return_value = (
            self.kpi_total_df.copy(),
            self.kpi_yearly_df.copy(),
            {"ctv_1": {"days": 12}},
            self.daily_vessel_df.copy(),
            {"corrective": 10.0},
            self.fuel_usage_df.copy(),
        )
        mocks["availability_graph_manager"].return_value()
        return counter

    def _call_results_block(self, config=None):
        """Call the function under test using its current keyword-based API."""
        return results_block(
            result_dir_r=self.result_dir,
            r=self.run_index,
            inputs=self.inputs,
            Config=config if config is not None else self.config,
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
            ST_operations_TTP_authorized=[],
        )

    def test_results_block_generates_all_outputs_when_previous_files_do_not_exist(self):
        """No previous files: generate logs, energy, KPI outputs and graphs."""
        with ExitStack() as stack:
            mocks = self._patch_dependencies(stack)
            counter = self._configure_common_mocks(mocks)
            mocks["read_csv"].side_effect = FileNotFoundError

            self._call_results_block()

            mocks["read_csv"].assert_called()
            mocks["failures_event"].assert_called_once()
            mocks["create_logs_timeseries_file"].assert_called_once()
            mocks["create_logs_merge"].assert_called_once()
            mocks["manage_def_to_log_events"].assert_called_once()

            self.assertGreaterEqual(len(counter.calls), 1)
            self.assertTrue(any(item["ST_contract"] is True for item in counter.calls))
            mocks["VesselDayCounter"].assert_called()
            self.assertIs(
                mocks["VesselDayCounter"].call_args.kwargs["vessels"],
                self.vessels,
            )
            mocks["config_energy"].assert_called_once()
            mocks["energy_availability"].assert_called_once()
            mocks["kpi_final_total_cost"].assert_called_once()

            mocks["graphs_simulation_creation"].assert_called_once()
            mocks["makedirs"].assert_called_once_with(
                os.path.join(self.result_dir, "graph_dir")
            )

            self.assertEqual(len(self.results_dict.dfs_tot_cost_list), 1)
            self.assertEqual(len(self.results_dict.dfs_tot_yearly_cost_list), 1)
            self.assertEqual(len(self.results_dict.kpi_om_type_cost_list), 1)
            self.assertEqual(len(self.results_dict.dfs_log_events), 1)
            self.assertEqual(len(self.results_dict.dfs_log_events_merged), 1)
            self.assertEqual(len(self.results_dict.dfs_ctv_list), 1)
            self.assertEqual(len(self.results_dict.dfs_vessel_fuel_usage), 1)
            self.assertEqual(len(self.results_dict.dfs_energy_data), 1)

    def test_results_block_reuses_previous_files_and_skips_energy_when_disabled(self):
        """Reuse previous logs, bypass energy calculation and still generate KPIs."""
        with ExitStack() as stack:
            mocks = self._patch_dependencies(stack)
            counter = self._configure_common_mocks(mocks)
            mocks["read_csv"].side_effect = [
                self.dates_failures_df.copy(),
                self.log_events_df.copy(),
                self.log_events_merged_df.copy(),
            ]
            config = SimpleNamespace(**vars(self.config))
            config.ENERGY_AVAILABILITY_CALCULATION = False
            self._call_results_block(config=config)

            self.assertEqual(mocks["read_csv"].call_count, 3)
            mocks["failures_event"].assert_not_called()
            mocks["create_logs_timeseries_file"].assert_not_called()
            mocks["create_logs_merge"].assert_not_called()
            mocks["config_energy"].assert_not_called()
            mocks["energy_availability"].assert_not_called()

            self.assertEqual(len(counter.calls), 1)
            self.assertTrue(counter.calls[0]["ST_contract"])
            mocks["kpi_final_total_cost"].assert_called_once()
            mocks["graphs_simulation_creation"].assert_called_once()
            mocks["makedirs"].assert_called_once_with(
                os.path.join(self.result_dir, "graph_dir")
            )
            self.assertEqual(len(self.results_dict.dfs_ctv_list), 1)

    def test_results_block_raises_when_log_events_are_empty(self):
        """Reject a newly generated empty log_events dataframe."""
        with ExitStack() as stack:
            mocks = self._patch_dependencies(stack)
            self._configure_common_mocks(mocks)
            mocks["read_csv"].side_effect = FileNotFoundError
            mocks["create_logs_timeseries_file"].return_value = pd.DataFrame()

            with self.assertRaisesRegex(Exception, "log_events dataframe is empty"):
                self._call_results_block()

            mocks["failures_event"].assert_called_once()
            mocks["create_logs_timeseries_file"].assert_called_once()
            mocks["create_logs_merge"].assert_not_called()
            mocks["kpi_final_total_cost"].assert_not_called()
            mocks["energy_availability"].assert_not_called()
            mocks["graphs_simulation_creation"].assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
