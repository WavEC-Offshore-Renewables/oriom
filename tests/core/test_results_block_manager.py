# test_results_block_manager.py

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import importlib.util

import pandas as pd

import oriom.core.results_block_manager as results_block_module


# --- check module check_files is present---
try:
    KPI_Insight_spec = importlib.util.find_spec(
        "oriom.core.functions.private.KPI_Insight"
    )
except ModuleNotFoundError:
    KPI_Insight_spec = None

class TestResultsBlock(unittest.TestCase):
    def _make_common_objects(
        self,
        energy_calc=True,
        statistical_chart=False,
        pv_devices=100,
    ):
        """Create minimal but consistent input objects for results_block."""
        # inputs
        inputs = SimpleNamespace(
            general=SimpleNamespace(
                logevents_file={"value": "/tmp/logs"},
                failureevent_file={"value": "/tmp/fails"},
            ),
            tseries=SimpleNamespace(
                scenario="scenario_A",
                # usato in failures_event
                merge_vessel={"value": ["v1"]},
                time_between_devices_dict={"wt": 1.0},
                shift_duration={"value": 12},
                failure_scenario = {"value": 0}
            ),
            stats=SimpleNamespace(
                lifetime={"value": 20},
                start_year={"value": 2020},
                start_month={"value": 1},
                period_infant_mortality={"value": 1},
                period_wear_out={"value": 1},
                failure_ratio={"value": 0.1},
                percentile_max={"value": 90},
            ),
            cost=SimpleNamespace(
                fuel_cost_hfo={"value": 10.0},
                fuel_cost_mgo={"value": 20.0},
                fuel_cost_mdo={"value": 30.0},
                port_cost_year={"value": 1000.0},
                insurance_cost_year={"value": 2000.0},
                technicians_year={"value": 3000.0},
                electricity_price_dict={"pv": 40.0, "wt": 50.0, "wec": 60.0},
            ),
        )

        # Config
        Config = SimpleNamespace(
            TIME_FAIL_OP_IMMEDIATELY=True,
            STATISTICAL_CHART=statistical_chart,
            ENERGY_AVAILABILITY_CALCULATION=energy_calc,
            ENERGY_STATISTICAL_CALCULATION=False,
        )

        # farm_technologies
        farm_technologies = SimpleNamespace(
            power=SimpleNamespace(
                pv_number_devices=pv_devices,
                pv_max_failure_module=5,
                pv_farm_prod={"dummy": 1.0},
                degradation_rate=0.01,
                wtg_number_devices=10,
                wec_number_devices=0,
            ),
            pv=SimpleNamespace(
                number_strings=2,
                number_inverters=2,
            ),
        )

        # results_dict
        results_dict = SimpleNamespace(
            dfs_energy_yearly_month_dict={"availability_month_wind": []},
            dfs_energy_yearly_dict={"availability_year_wind": []},
            dfs_ctv_list=[],
            dfs_tot_cost_list=[],
            dfs_tot_yearly_cost_list=[],
            kpi_om_type_cost_list=[],
            dfs_log_events=[],
            dfs_log_events_merged=[],
        )

        # stats / operations
        failures = ["f1", "f2"]  # not used in internal logic (mocked)
        operations_tow_stats = {"pmax": [1.0], "pmain": [2.0]}
        inspections_port_stats = {"pmax": [2.0], "pmain": [2.0]}
        inspections_site_stats = {"pmax": [3.0], "pmain": [3.0]}
        operations_corrective_stats = {"pmax": [4.0], "pmain": [5.0]}

        vessels = [SimpleNamespace(id="v1")]
        mother_vessels = ["v1"]

        # layout graphs (one without .copy to test the try/except)
        class DummyGraph:
            def __init__(self, name):
                self.name = name

            def copy(self):
                return DummyGraph(self.name + "_copy")

        G_layouts = {
            "G_wind": 1,  # this will cause AttributeError → G_wind_copy = None
            "G_wave": DummyGraph("wave"),
            "G_pv": DummyGraph("pv"),
        }

        dict_power_wind = {"dummy": 1.0}
        dict_power_wave = {"dummy": 2.0}
        metocean_timeseries = pd.DataFrame({"power": [0.0]})

        return (
            inputs,
            Config,
            farm_technologies,
            results_dict,
            failures,
            operations_tow_stats,
            inspections_port_stats,
            inspections_site_stats,
            operations_corrective_stats,
            vessels,
            mother_vessels,
            G_layouts,
            dict_power_wind,
            dict_power_wave,
            metocean_timeseries,
        )

    def _make_dates_failures_df(self):
        return pd.DataFrame(
            {
                "datetime": pd.to_datetime(["2020-01-01 00:00:00", "2021-01-01 00:00:00"]),
                "id": ["F1", "F2"],
            }
        )

    def _make_log_events_df(self):
        return pd.DataFrame(
            {
                "d_start": pd.to_datetime(["2020-01-01 00:00:00"]),
                "d_end": pd.to_datetime(["2020-01-01 12:00:00"]),
                "event": ["operation"],
                "n_vessel_1": [1],
            }
        )

    def _make_log_events_merged_df(self):
        return pd.DataFrame(
            {
                "d_start": pd.to_datetime(["2020-01-01 00:00:00"]),
                "d_end": pd.to_datetime(["2020-01-01 12:00:00"]),
                "event": ["operation"],
                "n_vessel_1": [1],
            }
        )

    # ------------------------------------------------------------------
    # 1) Caso base: nessun CSV precedente, tutto viene generato
    # ------------------------------------------------------------------
    def test_results_block_generates_failures_logs_and_kpis_when_no_previous_files(self):
        """
        When CSV files for failures/log_events/log_events_merged do not exist,
        results_block must:
            - call failures_event
            - create log_events with create_logs_timeseries_file
            - create log_events_merged with create_logs_merge + pipeline nave
            - calculate energy_availability if enabled
            - calculate KPI with kpi_final_total_cost
            - call distribution_failures if there are failures.
        """
        (
            inputs,
            Config,
            farm_technologies,
            results_dict,
            failures,
            operations_tow_stats,
            inspections_port_stats,
            inspections_site_stats,
            operations_corrective_stats,
            vessels,
            mother_vessels,
            G_layouts,
            dict_power_wind,
            dict_power_wave,
            metocean_timeseries,
        ) = self._make_common_objects()

        dates_failures_df = self._make_dates_failures_df()
        log_events_df = self._make_log_events_df()
        log_events_merged_df = self._make_log_events_merged_df()

        # availability_total
        availability_month = pd.DataFrame(
            {"Months": [1], "En_max_kWh": [1000.0], "En_loss_kWh": [100.0]}
        )
        availability_year = pd.DataFrame(
            {
                "Years": [1, 2],
                "En_loss_kWh": [1000.0, 2000.0],
                "En_availability": [95.0, 100.0],
                "Time_availability": [94.0, 100.0],
            }
        )
        availability_total = {
            "availability_month_wind": availability_month,
            "availability_year_wind": availability_year,
        }

        kpi_total_df = pd.DataFrame({"cost": [1.0]})
        kpi_yearly_df = pd.DataFrame({"year": [1], "cost": [1.0]})
        daily_vessel_df = pd.DataFrame({"v": [1]})
        ctv_dict = {}
        kpi_om_type_cost = {"dummy": 1}

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("oriom.core.results_block_manager.pd.read_csv") as mock_read_csv,
            patch("oriom.core.results_block_manager.aux_functions") as mock_aux,
            patch("oriom.core.results_block_manager.failures_event") as mock_failures_event,
            patch("oriom.core.results_block_manager.create_logs_timeseries_file") as mock_create_logs_ts,
            patch("oriom.core.results_block_manager.create_logs_merge") as mock_create_logs_merge,
            patch("oriom.core.results_block_manager.VesselDayCounter") as mock_vessel_day_counter,
            patch(
                "oriom.core.results_block_manager.vessel_mobilisation_manager"
            ) as mock_vessel_mob_mgr,
            patch("oriom.core.results_block_manager.VesselMobilisationScheduler") as mock_vessel_sched,
            patch("oriom.core.results_block_manager.energy_availability") as mock_energy_av,
            patch("oriom.core.results_block_manager.report_graphs") as mock_report_graphs,
            patch("oriom.core.results_block_manager.kpi_final_total_cost") as mock_kpi_final,
        ):
            result_dir_r = tmpdir
            r = 1

            # no existing csv → always FileNotFoundError
            mock_read_csv.side_effect = FileNotFoundError()

            mock_failures_event.return_value = dates_failures_df
            mock_create_logs_ts.return_value = log_events_df
            mock_create_logs_merge.return_value = log_events_merged_df

            # aux_functions conversions: identity
            mock_aux.convert_stringtime.side_effect = lambda df: df
            mock_aux.log_event_convert_stringtime.side_effect = lambda df: df

            # VesselDayCounter.allocate_vessels gives df merged
            mock_vessel_day_counter.return_value.allocate_vessels.return_value = (
                log_events_merged_df
            )

            # vessel_mobilisation_manager funcs gives df merged
            mock_vessel_mob_mgr.create_yearly_mobilisation_mother_vessel.return_value = (
                log_events_merged_df
            )
            mock_vessel_mob_mgr.reduce_redundant_mobilisations_inspection.return_value = (
                log_events_merged_df
            )

            # STATISTICAL_CHART False → VesselMobilisationScheduler not used
            mock_energy_av.return_value = availability_total

            mock_kpi_final.return_value = (
                kpi_total_df,
                kpi_yearly_df,
                ctv_dict,
                daily_vessel_df,
                kpi_om_type_cost,
            )

            results_block_module.results_block(
                result_dir_r=result_dir_r,
                r=r,
                inputs=inputs,
                Config=Config,
                find_element=SimpleNamespace(),
                farm_technologies=farm_technologies,
                results_dict=results_dict,
                failures=failures,
                operations_tow_stats=operations_tow_stats,
                inspections_port_stats=inspections_port_stats,
                inspections_site_stats=inspections_site_stats,
                operations_corrective_stats=operations_corrective_stats,
                vessels=vessels,
                mother_vessels=mother_vessels,
                G_layouts=G_layouts,
                dict_power_wind=dict_power_wind,
                dict_power_wave=dict_power_wave,
                metocean_timeseries=metocean_timeseries,
            )

            self.assertTrue(mock_failures_event.called, "failures_event non è stato chiamato")
            self.assertTrue(
                mock_create_logs_ts.called, "create_logs_timeseries_file non è stato chiamato"
            )
            self.assertTrue(
                mock_create_logs_merge.called, "create_logs_merge non è stato chiamato"
            )
            self.assertTrue(mock_energy_av.called, "energy_availability non è stato chiamato")
            self.assertTrue(mock_kpi_final.called, "kpi_final_total_cost non è stato chiamato")

            # distribution_failures calls cause dates_failures not empty
            mock_report_graphs.distribution_failures.assert_called_once()

            # energy_availability: G_wind must be None
            ea_kwargs = mock_energy_av.call_args.kwargs
            self.assertIsNone(ea_kwargs["G_wind"])

            # electricity_price correct (wt for "wind")
            self.assertTrue(mock_report_graphs.indirect_costs_per_year.called)
            _, ikw = mock_report_graphs.indirect_costs_per_year.call_args
            self.assertEqual(ikw["electricity_price"], 50.0)

            # results_dict populated
            self.assertEqual(len(results_dict.dfs_tot_cost_list), 1)
            self.assertEqual(len(results_dict.dfs_tot_yearly_cost_list), 1)
            self.assertEqual(len(results_dict.dfs_log_events), 1)
            self.assertEqual(len(results_dict.dfs_log_events_merged), 1)
            self.assertEqual(
                results_dict.dfs_energy_yearly_month_dict["availability_month_wind"][0].equals(
                    availability_month
                ),
                True,
            )
            self.assertEqual(
                results_dict.dfs_energy_yearly_dict["availability_year_wind"][0].equals(
                    availability_year
                ),
                True,
            )

    # ------------------------------------------------------------------
    # 2) ENERGY_AVAILABILITY_CALCULATION = False → no energy_availability
    # ------------------------------------------------------------------
    def test_results_block_skips_energy_availability_when_disabled(self):
        """
        If Config.ENERGY_AVAILABILITY_CALCULATION is False, it should not call energy_availability
        or energy availability graphs.
        """
        (
            inputs,
            Config,
            farm_technologies,
            results_dict,
            failures,
            operations_tow_stats,
            inspections_port_stats,
            inspections_site_stats,
            operations_corrective_stats,
            vessels,
            mother_vessels,
            G_layouts,
            dict_power_wind,
            dict_power_wave,
            metocean_timeseries,
        ) = self._make_common_objects(energy_calc=False)

        dates_failures_df = self._make_dates_failures_df()
        log_events_df = self._make_log_events_df()
        log_events_merged_df = self._make_log_events_merged_df()

        kpi_total_df = pd.DataFrame({"cost": [1.0]})
        kpi_yearly_df = pd.DataFrame({"year": [1], "cost": [1.0]})
        daily_vessel_df = pd.DataFrame({"v": [1]})
        ctv_dict = {}
        kpi_om_type_cost = {"dummy": 1}

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("oriom.core.results_block_manager.pd.read_csv") as mock_read_csv,
            patch("oriom.core.results_block_manager.aux_functions") as mock_aux,
            patch("oriom.core.results_block_manager.failures_event") as mock_failures_event,
            patch("oriom.core.results_block_manager.create_logs_timeseries_file") as mock_create_logs_ts,
            patch("oriom.core.results_block_manager.create_logs_merge") as mock_create_logs_merge,
            patch("oriom.core.results_block_manager.VesselDayCounter") as mock_vessel_day_counter,
            patch(
                "oriom.core.results_block_manager.vessel_mobilisation_manager"
            ) as mock_vessel_mob_mgr,
            patch("oriom.core.results_block_manager.energy_availability") as mock_energy_av,
            patch("oriom.core.results_block_manager.report_graphs") as mock_report_graphs,
            patch("oriom.core.results_block_manager.kpi_final_total_cost") as mock_kpi_final,
        ):
            result_dir_r = tmpdir
            r = 1

            mock_read_csv.side_effect = FileNotFoundError()
            mock_failures_event.return_value = dates_failures_df
            mock_create_logs_ts.return_value = log_events_df
            mock_create_logs_merge.return_value = log_events_merged_df

            mock_aux.convert_stringtime.side_effect = lambda df: df
            mock_aux.log_event_convert_stringtime.side_effect = lambda df: df

            mock_vessel_day_counter.return_value.allocate_vessels.return_value = (
                log_events_merged_df
            )
            mock_vessel_mob_mgr.create_yearly_mobilisation_mother_vessel.return_value = (
                log_events_merged_df
            )
            mock_vessel_mob_mgr.reduce_redundant_mobilisations_inspection.return_value = (
                log_events_merged_df
            )

            mock_kpi_final.return_value = (
                kpi_total_df,
                kpi_yearly_df,
                ctv_dict,
                daily_vessel_df,
                kpi_om_type_cost,
            )

            results_block_module.results_block(
                result_dir_r=result_dir_r,
                r=r,
                inputs=inputs,
                Config=Config,
                find_element=SimpleNamespace(),
                farm_technologies=farm_technologies,
                results_dict=results_dict,
                failures=failures,
                operations_tow_stats=operations_tow_stats,
                inspections_port_stats=inspections_port_stats,
                inspections_site_stats=inspections_site_stats,
                operations_corrective_stats=operations_corrective_stats,
                vessels=vessels,
                mother_vessels=mother_vessels,
                G_layouts=G_layouts,
                dict_power_wind=dict_power_wind,
                dict_power_wave=dict_power_wave,
                metocean_timeseries=metocean_timeseries,
            )

            mock_energy_av.assert_not_called()
            mock_report_graphs.energy_yield.assert_not_called()
            mock_report_graphs.farm_availability.assert_not_called()
            mock_report_graphs.indirect_costs_per_year.assert_not_called()
            mock_report_graphs.energy_yield_combined.assert_not_called()

    # ------------------------------------------------------------------
    # 3) PV without devices → None parameters and energy_availability
    # ------------------------------------------------------------------
    def test_results_block_passes_none_for_pv_parameters_when_no_pv_devices(self):
        """
        If pv_number_devices is None, n_strings_per_inv, n_modules_per_strings, and
        max_failure_module must be passed to energy_availability as None.
        """
        (
            inputs,
            Config,
            farm_technologies,
            results_dict,
            failures,
            operations_tow_stats,
            inspections_port_stats,
            inspections_site_stats,
            operations_corrective_stats,
            vessels,
            mother_vessels,
            G_layouts,
            dict_power_wind,
            dict_power_wave,
            metocean_timeseries,
        ) = self._make_common_objects(pv_devices=None)

        dates_failures_df = self._make_dates_failures_df()
        log_events_df = self._make_log_events_df()
        log_events_merged_df = self._make_log_events_merged_df()

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("oriom.core.results_block_manager.pd.read_csv") as mock_read_csv,
            patch("oriom.core.results_block_manager.aux_functions") as mock_aux,
            patch("oriom.core.results_block_manager.failures_event") as mock_failures_event,
            patch("oriom.core.results_block_manager.create_logs_timeseries_file") as mock_create_logs_ts,
            patch("oriom.core.results_block_manager.create_logs_merge") as mock_create_logs_merge,
            patch("oriom.core.results_block_manager.VesselDayCounter") as mock_vessel_day_counter,
            patch(
                "oriom.core.results_block_manager.vessel_mobilisation_manager"
            ) as mock_vessel_mob_mgr,
            patch("oriom.core.results_block_manager.energy_availability") as mock_energy_av,
            patch("oriom.core.results_block_manager.report_graphs") as mock_report_graphs,
            patch("oriom.core.results_block_manager.kpi_final_total_cost") as mock_kpi_final,
        ):
            result_dir_r = tmpdir
            r = 1

            mock_read_csv.side_effect = FileNotFoundError()
            mock_failures_event.return_value = dates_failures_df
            mock_create_logs_ts.return_value = log_events_df
            mock_create_logs_merge.return_value = log_events_merged_df

            mock_aux.convert_stringtime.side_effect = lambda df: df
            mock_aux.log_event_convert_stringtime.side_effect = lambda df: df

            mock_vessel_day_counter.return_value.allocate_vessels.return_value = (
                log_events_merged_df
            )
            mock_vessel_mob_mgr.create_yearly_mobilisation_mother_vessel.return_value = (
                log_events_merged_df
            )
            mock_vessel_mob_mgr.reduce_redundant_mobilisations_inspection.return_value = (
                log_events_merged_df
            )

            mock_energy_av.return_value = {}

            kpi_total_df = pd.DataFrame({"cost": [1.0]})
            kpi_yearly_df = pd.DataFrame({"year": [1], "cost": [1.0]})
            daily_vessel_df = pd.DataFrame({"v": [1]})
            kpi_om_type_cost = {}
            mock_kpi_final.return_value = (
                kpi_total_df,
                kpi_yearly_df,
                {},
                daily_vessel_df,
                kpi_om_type_cost,
            )

            results_block_module.results_block(
                result_dir_r=result_dir_r,
                r=r,
                inputs=inputs,
                Config=Config,
                find_element=SimpleNamespace(),
                farm_technologies=farm_technologies,
                results_dict=results_dict,
                failures=failures,
                operations_tow_stats=operations_tow_stats,
                inspections_port_stats=inspections_port_stats,
                inspections_site_stats=inspections_site_stats,
                operations_corrective_stats=operations_corrective_stats,
                vessels=vessels,
                mother_vessels=mother_vessels,
                G_layouts=G_layouts,
                dict_power_wind=dict_power_wind,
                dict_power_wave=dict_power_wave,
                metocean_timeseries=metocean_timeseries,
            )

            self.assertTrue(mock_energy_av.called)
            kwargs = mock_energy_av.call_args.kwargs
            self.assertIsNone(kwargs["n_strings_per_inv"])
            self.assertIsNone(kwargs["n_modules_per_strings"])
            self.assertIsNone(kwargs["max_failure_module"])

    # ------------------------------------------------------------------
    # 4) STATISTICAL_CHART True → use VesselMobilisationScheduler and 2x VesselDayCounter
    # ------------------------------------------------------------------
    def test_results_block_uses_vessel_mobilisation_scheduler_when_statistical_chart_true(self):
        """
        If Config.STATISTICAL_CHART is True, it must:
        - instantiate VesselMobilizationScheduler and call charts_manager
        - instantiate VesselDayCounter twice.
        """
        (
            inputs,
            Config,
            farm_technologies,
            results_dict,
            failures,
            operations_tow_stats,
            inspections_port_stats,
            inspections_site_stats,
            operations_corrective_stats,
            vessels,
            mother_vessels,
            G_layouts,
            dict_power_wind,
            dict_power_wave,
            metocean_timeseries,
        ) = self._make_common_objects(statistical_chart=True)

        dates_failures_df = self._make_dates_failures_df()
        log_events_df = self._make_log_events_df()
        log_events_merged_df = self._make_log_events_merged_df()

        availability_total = {}
        kpi_total_df = pd.DataFrame({"cost": [1.0]})
        kpi_yearly_df = pd.DataFrame({"year": [1], "cost": [1.0]})
        daily_vessel_df = pd.DataFrame({"v": [1]})

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("oriom.core.results_block_manager.pd.read_csv") as mock_read_csv,
            patch("oriom.core.results_block_manager.aux_functions") as mock_aux,
            patch("oriom.core.results_block_manager.failures_event") as mock_failures_event,
            patch("oriom.core.results_block_manager.create_logs_timeseries_file") as mock_create_logs_ts,
            patch("oriom.core.results_block_manager.create_logs_merge") as mock_create_logs_merge,
            patch("oriom.core.results_block_manager.VesselDayCounter") as mock_vessel_day_counter,
            patch(
                "oriom.core.results_block_manager.vessel_mobilisation_manager"
            ) as mock_vessel_mob_mgr,
            patch("oriom.core.results_block_manager.VesselMobilisationScheduler") as mock_vessel_sched,
            patch("oriom.core.results_block_manager.energy_availability") as mock_energy_av,
            patch("oriom.core.results_block_manager.report_graphs") as mock_report_graphs,
            patch("oriom.core.results_block_manager.kpi_final_total_cost") as mock_kpi_final,
        ):
            result_dir_r = tmpdir
            r = 1

            mock_read_csv.side_effect = FileNotFoundError()
            mock_failures_event.return_value = dates_failures_df
            mock_create_logs_ts.return_value = log_events_df
            mock_create_logs_merge.return_value = log_events_merged_df

            mock_aux.convert_stringtime.side_effect = lambda df: df
            mock_aux.log_event_convert_stringtime.side_effect = lambda df: df

            # primo VesselDayCounter.allocate_vessels
            mock_vessel_day_counter.return_value.allocate_vessels.return_value = (
                log_events_merged_df
            )

            mock_vessel_mob_mgr.create_yearly_mobilisation_mother_vessel.return_value = (
                log_events_merged_df
            )
            mock_vessel_mob_mgr.reduce_redundant_mobilisations_inspection.return_value = (
                log_events_merged_df
            )

            # charts_manager gives df_merged
            mock_vessel_sched.return_value.charts_manager.return_value = log_events_merged_df

            mock_energy_av.return_value = availability_total

            mock_kpi_final.return_value = (
                kpi_total_df,
                kpi_yearly_df,
                {},
                daily_vessel_df,
                {},
            )

            results_block_module.results_block(
                result_dir_r=result_dir_r,
                r=r,
                inputs=inputs,
                Config=Config,
                find_element=SimpleNamespace(),
                farm_technologies=farm_technologies,
                results_dict=results_dict,
                failures=failures,
                operations_tow_stats=operations_tow_stats,
                inspections_port_stats=inspections_port_stats,
                inspections_site_stats=inspections_site_stats,
                operations_corrective_stats=operations_corrective_stats,
                vessels=vessels,
                mother_vessels=mother_vessels,
                G_layouts=G_layouts,
                dict_power_wind=dict_power_wind,
                dict_power_wave=dict_power_wave,
                metocean_timeseries=metocean_timeseries,
            )

            if KPI_Insight_spec:
                # Check KPI insight Excel is created
                mock_vessel_sched.assert_called_once()
                self.assertGreaterEqual(mock_vessel_day_counter.call_count, 2)
                # allocate_vessels called twice
                self.assertGreaterEqual(
                    mock_vessel_day_counter.return_value.allocate_vessels.call_count, 2
                )
            else:
                pass


    # ------------------------------------------------------------------
    # 5) empty log_events → exception
    # ------------------------------------------------------------------
    def test_results_block_raises_if_log_events_empty(self):
        """
        If create_logs_timeseries_file returns an empty DataFrame,
        results_block should raise an exception and NOT call kpi_final_total_cost.
        """
        (
            inputs,
            Config,
            farm_technologies,
            results_dict,
            failures,
            operations_tow_stats,
            inspections_port_stats,
            inspections_site_stats,
            operations_corrective_stats,
            vessels,
            mother_vessels,
            G_layouts,
            dict_power_wind,
            dict_power_wave,
            metocean_timeseries,
        ) = self._make_common_objects()

        dates_failures_df = self._make_dates_failures_df()
        empty_log_events_df = pd.DataFrame()

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("oriom.core.results_block_manager.pd.read_csv") as mock_read_csv,
            patch("oriom.core.results_block_manager.aux_functions") as mock_aux,
            patch("oriom.core.results_block_manager.failures_event") as mock_failures_event,
            patch("oriom.core.results_block_manager.create_logs_timeseries_file") as mock_create_logs_ts,
            patch("oriom.core.results_block_manager.kpi_final_total_cost") as mock_kpi_final,
        ):
            result_dir_r = tmpdir
            r = 1

            mock_read_csv.side_effect = FileNotFoundError()
            mock_failures_event.return_value = dates_failures_df
            mock_create_logs_ts.return_value = empty_log_events_df

            mock_aux.convert_stringtime.side_effect = lambda df: df

            with self.assertRaises(Exception) as ctx:
                results_block_module.results_block(
                    result_dir_r=result_dir_r,
                    r=r,
                    inputs=inputs,
                    Config=Config,
                    find_element=SimpleNamespace(),
                    farm_technologies=farm_technologies,
                    results_dict=results_dict,
                    failures=failures,
                    operations_tow_stats=operations_tow_stats,
                    inspections_port_stats=inspections_port_stats,
                    inspections_site_stats=inspections_site_stats,
                    operations_corrective_stats=operations_corrective_stats,
                    vessels=vessels,
                    mother_vessels=mother_vessels,
                    G_layouts=G_layouts,
                    dict_power_wind=dict_power_wind,
                    dict_power_wave=dict_power_wave,
                    metocean_timeseries=metocean_timeseries,
                )

            self.assertIn("log_events dataframe is empty", str(ctx.exception))
            mock_kpi_final.assert_not_called()

    # ------------------------------------------------------------------
    # 6) dates failures empty → distribution failures NOT called
    # ------------------------------------------------------------------
    def test_results_block_does_not_call_distribution_failures_when_dates_failures_empty(self):
        """
        If the DataFrame dates failures is empty, distribution failures should not be called.
        """
        (
            inputs,
            Config,
            farm_technologies,
            results_dict,
            failures,
            operations_tow_stats,
            inspections_port_stats,
            inspections_site_stats,
            operations_corrective_stats,
            vessels,
            mother_vessels,
            G_layouts,
            dict_power_wind,
            dict_power_wave,
            metocean_timeseries,
        ) = self._make_common_objects()

        empty_dates = pd.DataFrame(columns=["datetime", "id"])
        log_events_df = self._make_log_events_df()
        log_events_merged_df = self._make_log_events_merged_df()

        availability_total = {}
        kpi_total_df = pd.DataFrame({"cost": [1.0]})
        kpi_yearly_df = pd.DataFrame({"year": [1], "cost": [1.0]})
        daily_vessel_df = pd.DataFrame({"v": [1]})

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("oriom.core.results_block_manager.pd.read_csv") as mock_read_csv,
            patch("oriom.core.results_block_manager.aux_functions") as mock_aux,
            patch("oriom.core.results_block_manager.failures_event") as mock_failures_event,
            patch("oriom.core.results_block_manager.create_logs_timeseries_file") as mock_create_logs_ts,
            patch("oriom.core.results_block_manager.create_logs_merge") as mock_create_logs_merge,
            patch("oriom.core.results_block_manager.VesselDayCounter") as mock_vessel_day_counter,
            patch(
                "oriom.core.results_block_manager.vessel_mobilisation_manager"
            ) as mock_vessel_mob_mgr,
            patch("oriom.core.results_block_manager.energy_availability") as mock_energy_av,
            patch("oriom.core.results_block_manager.report_graphs") as mock_report_graphs,
            patch("oriom.core.results_block_manager.kpi_final_total_cost") as mock_kpi_final,
        ):
            result_dir_r = tmpdir
            r = 1

            mock_read_csv.side_effect = FileNotFoundError()
            mock_failures_event.return_value = empty_dates
            mock_create_logs_ts.return_value = log_events_df
            mock_create_logs_merge.return_value = log_events_merged_df

            mock_aux.convert_stringtime.side_effect = lambda df: df
            mock_aux.log_event_convert_stringtime.side_effect = lambda df: df

            mock_vessel_day_counter.return_value.allocate_vessels.return_value = (
                log_events_merged_df
            )
            mock_vessel_mob_mgr.create_yearly_mobilisation_mother_vessel.return_value = (
                log_events_merged_df
            )
            mock_vessel_mob_mgr.reduce_redundant_mobilisations_inspection.return_value = (
                log_events_merged_df
            )

            mock_energy_av.return_value = availability_total

            mock_kpi_final.return_value = (
                kpi_total_df,
                kpi_yearly_df,
                {},
                daily_vessel_df,
                {},
            )

            results_block_module.results_block(
                result_dir_r=result_dir_r,
                r=r,
                inputs=inputs,
                Config=Config,
                find_element=SimpleNamespace(),
                farm_technologies=farm_technologies,
                results_dict=results_dict,
                failures=failures,
                operations_tow_stats=operations_tow_stats,
                inspections_port_stats=inspections_port_stats,
                inspections_site_stats=inspections_site_stats,
                operations_corrective_stats=operations_corrective_stats,
                vessels=vessels,
                mother_vessels=mother_vessels,
                G_layouts=G_layouts,
                dict_power_wind=dict_power_wind,
                dict_power_wave=dict_power_wave,
                metocean_timeseries=metocean_timeseries,
            )

            mock_report_graphs.distribution_failures.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
