#!/usr/bin/env python3
"""Regression tests for ORIOM short-term operational visualisations.

The tests exercise the real numerical and plotting functions. Matplotlib uses a
headless backend, and no real ORIOM data files, external APIs or GUIs are needed.

Target module discovery (in order):
    1. ORIOM_ST_VISUALISATIONS_MODULE: fully qualified Python module name.
    2. ORIOM_ST_VISUALISATIONS_PATH: exact path to the source file.
    3. Automatic search below <repository>/src/oriom/ for create_ST_figures.

Run from the repository root:
    python tests/core/functions/graphs/test_ST_visualisations.py

Run against an explicitly specified source module (PowerShell):
    $env:ORIOM_ST_VISUALISATIONS_MODULE = 'oriom.core.functions.graphs.my_module'
    python tests/core/functions/graphs/test_ST_visualisations.py
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal


def _load_target_module():
    """Load the source module without depending on its filename."""
    module_name = os.getenv("ORIOM_ST_VISUALISATIONS_MODULE")
    if module_name:
        return importlib.import_module(module_name)

    source_path = os.getenv("ORIOM_ST_VISUALISATIONS_PATH")
    if source_path:
        path = Path(source_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Visualisations source file not found: {path}")
    else:
        candidates = []
        for parent in Path(__file__).resolve().parents:
            source_root = parent / "src" / "oriom"
            if not source_root.is_dir():
                continue
            for path_candidate in source_root.rglob("*.py"):
                if "def create_ST_figures(" in path_candidate.read_text(
                    encoding="utf-8", errors="replace"
                ):
                    candidates.append(path_candidate)
            break
        if not candidates:
            raise ImportError(
                "Cannot locate the ORIOM visualisations source file. "
                "Set ORIOM_ST_VISUALISATIONS_MODULE to its import path or "
                "ORIOM_ST_VISUALISATIONS_PATH to the source file."
            )
        if len(candidates) > 1:
            raise ImportError(
                "Multiple create_ST_figures modules found. Specify "
                "ORIOM_ST_VISUALISATIONS_MODULE or ORIOM_ST_VISUALISATIONS_PATH: "
                + ", ".join(str(path_candidate) for path_candidate in candidates)
            )
        path = candidates[0]

    temporary_name = "_oriom_st_visualisations_under_test"
    loader = SourceFileLoader(temporary_name, str(path))
    spec = importlib.util.spec_from_loader(temporary_name, loader, origin=str(path))
    if spec is None:
        raise ImportError(f"Cannot create a module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[temporary_name] = module
    loader.exec_module(module)
    return module


visuals = _load_target_module()


def make_power(values=(1000, 2000, 4000, 1000), start="2026-01-10 08:00"):
    """Create gross potential wind power, in kW, at hourly timestamps."""
    index = pd.date_range(start, periods=len(values), freq="h")
    return pd.DataFrame({"p_wind": values}, index=index)


def make_corrective(index, percentages=(100, 50, 50, 100)):
    """Create state-change events; the caller supplies event timestamps."""
    return pd.DataFrame(
        {"Date": list(index), "Perc_availability": list(percentages)}
    )


def make_energy_fixture(price=50.0):
    """Return a four-hour fixture with exactly 3 MWh and EUR 150 lost."""
    power = make_power()
    events = make_corrective(power.index)
    return visuals.build_energy_results(power, events, price)


def make_vessel_events():
    """Create two vessels completing seven consecutive operation phases."""
    starts = pd.date_range("2026-01-10 08:00", periods=8, freq="h")
    columns = [
        "d_end_leadtime",
        "d_end_wait_start",
        "d_end_dur_net_port",
        "d_end_transit_ts",
        "d_end_wait_site",
        "d_end_dur_net_site",
        "d_end_transit_tp",
        "d_end",
    ]
    row = dict(zip(columns, starts))
    row.update(
        {
            "id": "operation_001",
            "vessel_1": "ctv_001",
            "n_vessel_1": 2,
            "vessel_2": "sv_001",
            "n_vessel_2": 1,
        }
    )
    return pd.DataFrame([row])


def make_segments():
    events = make_vessel_events()
    return visuals.build_vessel_segments(
        events,
        {"ctv_001": "CTV", "sv_001": "Support Vessel"},
        pd.Timestamp("2026-01-10 08:00"),
        pd.Timestamp("2026-01-10 16:00"),
    )


class FigureTestCase(unittest.TestCase):
    """Ensure that matplotlib figures cannot leak between tests."""

    def tearDown(self):
        plt.close("all")


class TestConfigurationAndStyling(FigureTestCase):
    def test_plot_config_defaults(self):
        config = visuals.PlotConfig()
        self.assertEqual(config.vessel_types, {})
        self.assertIsNone(config.price_eur_mwh)
        self.assertEqual(config.output_dir, Path("oriom_figures"))
        self.assertEqual(config.dpi, 180)
        self.assertFalse(config.use_event_power_loss)

    def test_plot_config_dictionaries_are_independent(self):
        a = visuals.PlotConfig()
        b = visuals.PlotConfig()
        a.vessel_types["v001"] = "CTV"
        self.assertEqual(b.vessel_types, {})

    def test_style_hides_top_and_right_spines(self):
        with matplotlib.rc_context():
            visuals._style()
            self.assertFalse(plt.rcParams["axes.spines.top"])
            self.assertFalse(plt.rcParams["axes.spines.right"])

    def test_time_axis_has_six_hour_major_ticks(self):
        fig, ax = plt.subplots()
        start = pd.Timestamp("2026-01-10 00:00")
        end = start + pd.Timedelta(days=1)
        visuals._format_time_axis(ax, start, end)
        fig.canvas.draw()
        ticks = mdates.num2date(ax.get_xticks())
        self.assertTrue(ticks)
        self.assertTrue(all(t.hour in (0, 6, 12, 18) for t in ticks))
        self.assertEqual(ax.get_xlabel(), "")
        self.assertAlmostEqual(ax.get_xlim()[0], mdates.date2num(start))
        self.assertAlmostEqual(ax.get_xlim()[1], mdates.date2num(end))

    def test_legend_appears_above_plotting_area(self):
        fig, ax = plt.subplots()
        ax.plot([0, 1], [0, 1], label="Sample")
        legend = visuals._legend_above(ax)
        self.assertIsNotNone(legend)
        self.assertEqual([text.get_text() for text in legend.get_texts()], ["Sample"])


class TestIntervalHours(unittest.TestCase):
    def test_regular_hourly_intervals(self):
        index = pd.date_range("2026-01-10", periods=4, freq="h")
        np.testing.assert_allclose(visuals._interval_hours(index), [1, 1, 1, 1])

    def test_irregular_intervals_and_last_step_reused(self):
        index = pd.to_datetime(
            ["2026-01-10 08:00", "2026-01-10 08:30", "2026-01-10 10:30"]
        )
        np.testing.assert_allclose(visuals._interval_hours(index), [0.5, 2, 2])

    def test_two_timestamps_are_sufficient(self):
        index = pd.to_datetime(["2026-01-10 08:00", "2026-01-10 09:30"])
        np.testing.assert_allclose(visuals._interval_hours(index), [1.5, 1.5])

    def test_less_than_two_timestamps_raises(self):
        for index in (pd.DatetimeIndex([]), pd.DatetimeIndex(["2026-01-10"])):
            with self.subTest(length=len(index)):
                with self.assertRaisesRegex(ValueError, "At least two"):
                    visuals._interval_hours(index)

    def test_duplicate_timestamps_raise(self):
        index = pd.to_datetime(["2026-01-10", "2026-01-10"])
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            visuals._interval_hours(index)

    def test_descending_timestamps_raise(self):
        index = pd.to_datetime(["2026-01-10 10:00", "2026-01-10 09:00"])
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            visuals._interval_hours(index)

    def test_power_is_sorted_without_mutating_input(self):
        power = make_power().iloc[::-1].copy()
        before = power.copy(deep=True)
        actual = visuals._power(power)
        self.assertTrue(actual.index.is_monotonic_increasing)
        assert_frame_equal(power, before)


class TestPrices(unittest.TestCase):
    def setUp(self):
        self.index = pd.date_range("2026-01-10 08:00", periods=3, freq="h")

    def test_missing_prices_are_nan(self):
        actual = visuals._prices(None, self.index)
        self.assertTrue(actual.isna().all())
        self.assertEqual(actual.name, "price_eur_mwh")

    def test_scalar_price_is_broadcast(self):
        actual = visuals._prices(55, self.index)
        np.testing.assert_allclose(actual, [55, 55, 55])

    def test_series_prices_use_exact_timestamp_alignment(self):
        prices = pd.Series([30, 10], index=[self.index[2], self.index[0]])
        before = prices.copy(deep=True)
        actual = visuals._prices(prices, self.index)
        self.assertEqual(actual.loc[self.index[0]], 10)
        self.assertTrue(pd.isna(actual.loc[self.index[1]]))
        self.assertEqual(actual.loc[self.index[2]], 30)
        assert_series_equal(prices, before)

    def test_price_dataframe_with_datetime_column(self):
        prices = pd.DataFrame(
            {"datetime": self.index, "price_eur_mwh": [10, 20, 30]}
        )
        np.testing.assert_allclose(visuals._prices(prices, self.index), [10, 20, 30])

    def test_price_dataframe_with_datetime_index(self):
        prices = pd.DataFrame(
            {"price_eur_mwh": [15, 25, 35]}, index=self.index
        )
        np.testing.assert_allclose(visuals._prices(prices, self.index), [15, 25, 35])

    def test_non_numeric_prices_are_nan(self):
        prices = pd.Series(["10", "bad", "30"], index=self.index)
        actual = visuals._prices(prices, self.index)
        self.assertEqual(actual.iloc[0], 10)
        self.assertTrue(pd.isna(actual.iloc[1]))
        self.assertEqual(actual.iloc[2], 30)

    def test_missing_price_column_raises(self):
        with self.assertRaisesRegex(ValueError, "price_eur_mwh column"):
            visuals._prices(pd.DataFrame({"another": [1]}), self.index)

    def test_duplicate_price_timestamps_raise(self):
        prices = pd.Series([10, 20], index=[self.index[0], self.index[0]])
        with self.assertRaisesRegex(ValueError, "Duplicate price timestamps"):
            visuals._prices(prices, self.index)

    def test_negative_market_prices_are_preserved(self):
        np.testing.assert_allclose(visuals._prices(-20.0, self.index), [-20] * 3)


class TestAvailability(unittest.TestCase):
    def setUp(self):
        self.index = pd.date_range("2026-01-10 08:00", periods=4, freq="h")

    def test_last_known_state_is_forward_filled(self):
        events = make_corrective(
            [self.index[0], self.index[2]], [100, 40]
        )
        np.testing.assert_allclose(
            visuals._availability(events, self.index), [100, 100, 40, 40]
        )

    def test_last_event_wins_for_identical_timestamps(self):
        events = make_corrective(
            [self.index[0], self.index[1], self.index[1]], [100, 80, 25]
        )
        np.testing.assert_allclose(
            visuals._availability(events, self.index), [100, 25, 25, 25]
        )

    def test_events_before_power_start_are_used(self):
        events = make_corrective(
            [self.index[0] - pd.Timedelta(minutes=20), self.index[2]], [90, 50]
        )
        np.testing.assert_allclose(
            visuals._availability(events, self.index), [90, 90, 50, 50]
        )

    def test_undefined_initial_availability_raises(self):
        events = make_corrective([self.index[1]], [80])
        with self.assertRaisesRegex(ValueError, "undefined at the start"):
            visuals._availability(events, self.index)

    def test_duplicate_events_retain_source_order_after_sort(self):
        events = make_corrective(
            [self.index[1], self.index[0], self.index[1]], [30, 100, 60]
        )
        np.testing.assert_allclose(
            visuals._availability(events, self.index), [100, 60, 60, 60]
        )

    def test_invalid_availability_values_raise(self):
        for invalid in (-1, 101):
            with self.subTest(value=invalid):
                events = make_corrective([self.index[0]], [invalid])
                with self.assertRaisesRegex(ValueError, "between 0 and 100"):
                    visuals._availability(events, self.index)

    def test_missing_required_columns_raise(self):
        for bad in (
            pd.DataFrame({"Date": [self.index[0]]}),
            pd.DataFrame({"Perc_availability": [100]}),
        ):
            with self.subTest(columns=list(bad.columns)):
                with self.assertRaisesRegex(ValueError, "Missing Date"):
                    visuals._availability(bad, self.index)

    def test_empty_events_raise(self):
        with self.assertRaisesRegex(ValueError, "No valid availability events"):
            visuals._availability(
                pd.DataFrame(columns=["Date", "Perc_availability"]), self.index
            )

    def test_non_numeric_event_is_dropped(self):
        events = make_corrective(
            [self.index[0], self.index[1], self.index[2]], [100, "bad", 50]
        )
        np.testing.assert_allclose(
            visuals._availability(events, self.index), [100, 100, 50, 50]
        )

    def test_events_dataframe_is_not_modified(self):
        events = make_corrective([self.index[0]], [75])
        before = events.copy(deep=True)
        visuals._availability(events, self.index)
        assert_frame_equal(events, before)


class TestBuildEnergyResults(unittest.TestCase):
    def setUp(self):
        self.power = make_power()
        self.corrective = make_corrective(self.power.index)

    def test_energy_power_and_revenue_are_numerically_correct(self):
        result = visuals.build_energy_results(self.power, self.corrective, 50)
        np.testing.assert_allclose(result["interval_hours"], [1, 1, 1, 1])
        np.testing.assert_allclose(result["availability_pct"], [100, 50, 50, 100])
        np.testing.assert_allclose(result["potential_power_kw"], [1000, 2000, 4000, 1000])
        np.testing.assert_allclose(result["actual_power_kw"], [1000, 1000, 2000, 1000])
        np.testing.assert_allclose(result["lost_power_kw"], [0, 1000, 2000, 0])
        np.testing.assert_allclose(result["potential_energy_mwh"], [1, 2, 4, 1])
        np.testing.assert_allclose(result["actual_energy_mwh"], [1, 1, 2, 1])
        np.testing.assert_allclose(result["lost_energy_mwh"], [0, 1, 2, 0])
        np.testing.assert_allclose(result["actual_revenue_eur"], [50, 50, 100, 50])
        np.testing.assert_allclose(result["lost_revenue_eur"], [0, 50, 100, 0])
        np.testing.assert_allclose(result["cumulative_lost_energy_mwh"], [0, 1, 3, 3])
        np.testing.assert_allclose(result["cumulative_lost_revenue_eur"], [0, 50, 150, 150])

    def test_interval_lengths_affect_energy_integration(self):
        index = pd.to_datetime(
            ["2026-01-10 08:00", "2026-01-10 08:30", "2026-01-10 10:30"]
        )
        power = pd.DataFrame({"p_wind": [1000, 1000, 1000]}, index=index)
        corrective = make_corrective(index, [100, 50, 50])
        result = visuals.build_energy_results(power, corrective, 70)
        np.testing.assert_allclose(result["interval_hours"], [0.5, 2, 2])
        np.testing.assert_allclose(result["lost_energy_mwh"], [0, 1, 1])
        np.testing.assert_allclose(result["cumulative_lost_energy_mwh"], [0, 1, 2])
        self.assertAlmostEqual(result["lost_revenue_eur"].sum(), 140)

    def test_price_series_is_aligned_without_forward_filling(self):
        prices = pd.Series([20.0, 60.0], index=[self.power.index[0], self.power.index[2]])
        result = visuals.build_energy_results(self.power, self.corrective, prices)
        self.assertTrue(pd.isna(result["lost_revenue_eur"].iloc[1]))
        self.assertTrue(result["cumulative_lost_revenue_eur"].isna().all())
        self.assertAlmostEqual(result["lost_revenue_eur"].iloc[2], 120)

    def test_no_prices_means_unknown_revenue_but_known_energy_loss(self):
        result = visuals.build_energy_results(self.power, self.corrective)
        self.assertAlmostEqual(result["lost_energy_mwh"].sum(), 3.0)
        self.assertTrue(result["lost_revenue_eur"].isna().all())
        self.assertTrue(result["cumulative_lost_revenue_eur"].isna().all())

    def test_results_are_sorted_and_original_inputs_are_unchanged(self):
        power = self.power.iloc[::-1].copy()
        events = self.corrective.iloc[::-1].copy()
        power_before = power.copy(deep=True)
        events_before = events.copy(deep=True)
        result = visuals.build_energy_results(power, events, 50)
        self.assertTrue(result.index.is_monotonic_increasing)
        self.assertAlmostEqual(result["lost_energy_mwh"].sum(), 3)
        assert_frame_equal(power, power_before)
        assert_frame_equal(events, events_before)

    def test_non_numeric_potential_power_raises(self):
        power = self.power.copy().astype({"p_wind": object})
        power.loc[power.index[0], "p_wind"] = "invalid"
        with self.assertRaises((ValueError, TypeError)):
            visuals.build_energy_results(power, self.corrective, 50)

    def test_missing_wind_power_column_raises(self):
        power = self.power.rename(columns={"p_wind": "wind"})
        with self.assertRaises(KeyError):
            visuals.build_energy_results(power, self.corrective, 50)

    def test_availability_validation_is_not_bypassed(self):
        corrective = make_corrective([self.power.index[1]], [50])
        with self.assertRaisesRegex(ValueError, "undefined at the start"):
            visuals.build_energy_results(self.power, corrective, 50)


class TestVesselSegments(unittest.TestCase):
    def setUp(self):
        self.events = make_vessel_events()
        self.types = {"ctv_001": "CTV", "sv_001": "Support Vessel"}
        self.start = pd.Timestamp("2026-01-10 08:00")
        self.end = pd.Timestamp("2026-01-10 16:00")

    def _build(self, events=None, start=None, end=None, types=None):
        return visuals.build_vessel_segments(
            self.events if events is None else events,
            self.types if types is None else types,
            self.start if start is None else start,
            self.end if end is None else end,
        )

    def test_two_vessel_slots_generate_fourteen_phases(self):
        segments = self._build()
        self.assertEqual(len(segments), 14)
        self.assertEqual((segments["vessel_id"] == "ctv_001").sum(), 7)
        self.assertEqual((segments["vessel_id"] == "sv_001").sum(), 7)
        self.assertEqual(set(segments["location"]), {"Port", "Transit", "Site"})
        self.assertEqual(segments.loc[segments.vessel_id == "ctv_001", "count"].unique().tolist(), [2])
        self.assertEqual(segments.loc[segments.vessel_id == "sv_001", "count"].unique().tolist(), [1])
        self.assertEqual(set(segments["event_id"]), {"operation_001"})

    def test_phase_order_locations_and_durations(self):
        segments = self._build()
        first = segments.loc[segments.vessel_id == "ctv_001"]
        self.assertEqual(first["location"].tolist(),
                         ["Port", "Port", "Transit", "Site", "Site", "Transit", "Port"])
        self.assertTrue(all((end - start) == pd.Timedelta(hours=1)
                            for start, end in zip(first["start"], first["end"])))

    def test_partial_phases_are_clipped_to_simulation_window(self):
        start = pd.Timestamp("2026-01-10 09:30")
        end = pd.Timestamp("2026-01-10 12:30")
        segments = self._build(start=start, end=end)
        self.assertEqual(len(segments), 8)
        self.assertEqual(segments["start"].min(), start)
        self.assertEqual(segments["end"].max(), end)
        self.assertTrue((segments["start"] >= start).all())
        self.assertTrue((segments["end"] <= end).all())

    def test_operations_outside_window_are_omitted(self):
        segments = self._build(
            start=pd.Timestamp("2026-01-11 08:00"),
            end=pd.Timestamp("2026-01-11 12:00"),
        )
        self.assertTrue(segments.empty)

    def test_nonpositive_or_missing_vessel_quantities_are_skipped(self):
        for count in (0, -1, None, "not-a-number"):
            with self.subTest(count=count):
                events = self.events.copy().astype({"n_vessel_1": object})
                events.loc[0, "n_vessel_1"] = count
                segments = self._build(events=events)
                self.assertEqual(len(segments), 7)
                self.assertEqual(set(segments["vessel_id"]), {"sv_001"})

    def test_unclassified_type_is_explicit(self):
        segments = self._build(types={})
        self.assertEqual(set(segments["vessel_type"]), {"Unclassified"})

    def test_zero_or_negative_stage_duration_is_skipped(self):
        events = self.events.copy()
        events["d_end_dur_net_port"] = events["d_end_wait_start"]
        segments = self._build(events=events)
        self.assertEqual(len(segments), 12)

    def test_original_event_dataframe_is_not_mutated(self):
        before = self.events.copy(deep=True)
        self._build()
        assert_frame_equal(self.events, before)

    def test_missing_optional_vessel_slot_is_ignored(self):
        events = self.events.drop(columns=["vessel_2", "n_vessel_2"])
        segments = self._build(events=events)
        self.assertEqual(len(segments), 7)
        self.assertEqual(set(segments["vessel_id"]), {"ctv_001"})

    def test_multiple_operations_retain_event_ids(self):
        events = pd.concat([self.events, self.events.assign(id="operation_002")], ignore_index=True)
        segments = self._build(events=events)
        self.assertEqual(len(segments), 28)
        self.assertEqual(set(segments["event_id"]), {"operation_001", "operation_002"})


class TestPlotting(FigureTestCase):
    def setUp(self):
        self.energy = make_energy_fixture(50)
        self.segments = make_segments()
        self.start = pd.Timestamp("2026-01-10 08:00")
        self.end = pd.Timestamp("2026-01-10 16:00")

    def test_gantt_uses_vessel_ids_types_and_counts(self):
        fig = visuals.plot_vessel_gantt(self.segments, self.start, self.end)
        ax = fig.axes[0]
        self.assertIn("Vessel utilisation", fig._suptitle.get_text())
        labels = [label.get_text() for label in ax.get_yticklabels()]
        self.assertEqual(labels, ["CTV  |  ctv_001", "Support Vessel  |  sv_001"])
        texts = [text.get_text() for text in ax.texts]
        self.assertIn("2x", texts)
        self.assertIn("1x", texts)
        self.assertEqual(ax.get_xlabel(), "Simulation time")
        self.assertEqual(set(label.get_text() for label in ax.get_legend().get_texts()),
                         {"Port", "Transit", "Site"})

    def test_gantt_rejects_empty_segments(self):
        """No vessel activity now produces a warning and no figure."""
        for segments in (None, pd.DataFrame()):
            with self.subTest(segments_type=type(segments).__name__):
                existing = set(plt.get_fignums())
                result = visuals.plot_vessel_gantt(segments, self.start, self.end)
                self.assertIsNone(result)
                self.assertEqual(set(plt.get_fignums()), existing)

    def test_gantt_contains_coloured_operation_phases(self):
        fig = visuals.plot_vessel_gantt(self.segments, self.start, self.end)
        self.assertGreaterEqual(len(fig.axes[0].collections), len(self.segments))

    def test_energy_revenue_plot_uses_revenue_axis_when_priced(self):
        fig = visuals.plot_energy_and_revenue(self.energy)
        self.assertEqual(len(fig.axes), 2)
        self.assertEqual(fig.axes[0].get_ylabel(), "Power [MW]")
        self.assertEqual(fig.axes[1].get_ylabel(), "Lost revenue [k€ / interval]")
        self.assertEqual(len(fig.axes[0].lines), 2)
        self.assertEqual(len(fig.axes[1].patches), len(self.energy))

    def test_energy_plot_uses_energy_losses_without_prices(self):
        energy = make_energy_fixture(None)
        fig = visuals.plot_energy_and_revenue(energy)
        self.assertEqual(len(fig.axes), 2)
        self.assertEqual(fig.axes[1].get_ylabel(), "Lost energy [MWh / interval]")
        self.assertIn("Electricity prices not provided", fig.axes[1].get_title())

    def test_cumulative_plot_has_second_axis_with_complete_prices(self):
        fig = visuals.plot_cumulative_losses(self.energy)
        self.assertEqual(len(fig.axes), 2)
        self.assertEqual(fig.axes[0].get_ylabel(), "Cumulative lost energy [MWh]")
        self.assertEqual(fig.axes[1].get_ylabel(), "Cumulative lost revenue [k€]")
        self.assertEqual(fig.axes[0].lines[0].get_ydata()[-1], 3.0)
        self.assertEqual(fig.axes[1].lines[0].get_ydata()[-1], 0.15)

    def test_cumulative_plot_has_one_axis_without_complete_prices(self):
        energy = make_energy_fixture(None)
        fig = visuals.plot_cumulative_losses(energy)
        self.assertEqual(len(fig.axes), 1)
        self.assertEqual(fig.axes[0].get_ylabel(), "Cumulative lost energy [MWh]")

    def test_partial_prices_skip_revenue_axis_in_cumulative_plot(self):
        power = make_power()
        events = make_corrective(power.index)
        prices = pd.Series([40], index=[power.index[0]])
        energy = visuals.build_energy_results(power, events, prices)
        fig = visuals.plot_cumulative_losses(energy)
        self.assertEqual(len(fig.axes), 1)


class TestCreateSTFigures(FigureTestCase):
    def setUp(self):
        self.power = make_power()
        self.corrective = make_corrective(self.power.index)
        self.events = make_vessel_events()
        self.types = {"ctv_001": "CTV", "sv_001": "Support Vessel"}

    def test_creates_all_three_png_files_without_return_value(self):
        """create_ST_figures now saves figures but returns None."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            folder = Path(tmp_dir) / "nested" / "figures"
            originals = (
                self.power.copy(deep=True),
                self.corrective.copy(deep=True),
                self.events.copy(deep=True),
            )
            before = set(plt.get_fignums())
            output = visuals.create_ST_figures(
                log_events_merged=self.events,
                wind_corrective_energy=self.corrective,
                timeseries_power=self.power,
                vessel_types=self.types,
                energy_price=50.0,
                graph_dir_r=str(folder),
            )
            self.assertIsNone(output)
            self.assertTrue(folder.is_dir())
            expected_files = {
                "01_vessel_utilisation.png",
                "02_energy_revenue_losses.png",
                "03_cumulative_losses.png",
            }
            self.assertEqual({path.name for path in folder.iterdir()}, expected_files)
            for filename in expected_files:
                assert_valid_png(self, folder / filename)
            self.assertEqual(set(plt.get_fignums()), before)
            assert_frame_equal(self.power, originals[0])
            assert_frame_equal(self.corrective, originals[1])
            assert_frame_equal(self.events, originals[2])

    def test_invalid_power_timeseries_fails_before_plotting(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.object(visuals, "plot_vessel_gantt") as mocked_gantt:
                with self.assertRaisesRegex(ValueError, "At least two"):
                    visuals.create_ST_figures(
                        self.events, self.corrective, self.power.iloc[:1],
                        self.types, 50, tmp_dir,
                    )
                mocked_gantt.assert_not_called()

    def test_no_vessel_phases_skip_gantt_but_save_other_graphs(self):
        """Missing vessel phases skip only the Gantt, not the energy plots."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = visuals.create_ST_figures(
                self.events.iloc[:0].copy(), self.corrective, self.power,
                self.types, 50, tmp_dir,
            )
            actual = {path.name for path in Path(tmp_dir).glob("*.png")}
            self.assertEqual(actual, {
                "02_energy_revenue_losses.png",
                "03_cumulative_losses.png",
            })
            for filename in actual:
                assert_valid_png(self, Path(tmp_dir) / filename)

    def test_none_event_dataframe_raises_before_plotting(self):
        """A missing DataFrame differs from an empty valid event DataFrame."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.object(visuals, "plot_vessel_gantt") as mock_gantt:
                with self.assertRaises(AttributeError):
                    visuals.create_ST_figures(
                        None, self.corrective, self.power,
                        self.types, 50, tmp_dir,
                    )
                mock_gantt.assert_not_called()
            self.assertFalse(any(Path(tmp_dir).glob("*.png")))

    def test_missing_initial_availability_does_not_save_partial_pngs(self):
        corrective = make_corrective(
            [self.power.index[1]], [50]
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaisesRegex(ValueError, "undefined at the start"):
                visuals.create_ST_figures(
                    self.events, corrective, self.power,
                    self.types, 50, tmp_dir,
                )
            self.assertFalse(any(Path(tmp_dir).glob("*.png")))



# =============================================================================
# Short-term cross-run statistical graphs
# =============================================================================
# These tests extend the original suite without changing its existing tests.
# The new functions may live in another ORIOM source module. Override automatic
# discovery if necessary with ORIOM_ST_STATISTICAL_GRAPHS_MODULE or
# ORIOM_ST_STATISTICAL_GRAPHS_PATH.


def _load_st_statistics_module(function_name):
    """Locate the ORIOM source module defining a statistical graph function."""
    import re

    module_name = os.getenv("ORIOM_ST_STATISTICAL_GRAPHS_MODULE")
    source_path = os.getenv("ORIOM_ST_STATISTICAL_GRAPHS_PATH")

    if module_name:
        module = importlib.import_module(module_name)
        if not callable(getattr(module, function_name, None)):
            raise AttributeError(f"{module_name} does not define {function_name}")
        return module

    if source_path:
        selected = Path(source_path).expanduser().resolve()
        if not selected.is_file():
            raise FileNotFoundError(f"Statistical graphs source not found: {selected}")
        loader = SourceFileLoader(
            "_oriom_st_statistical_graphs_under_test", str(selected)
        )
        spec = importlib.util.spec_from_loader(
            loader.name, loader, origin=str(selected)
        )
        if spec is None:
            raise ImportError(f"Cannot load statistical graphs source: {selected}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[loader.name] = module
        loader.exec_module(module)
        if not callable(getattr(module, function_name, None)):
            raise AttributeError(f"{selected} does not define {function_name}")
        return module

    # If the new functions were added to the existing visualisations module,
    # reuse its already loaded instance.
    if callable(getattr(visuals, function_name, None)):
        return visuals

    pattern = re.compile(r"^def\s+" + re.escape(function_name) + r"\s*\(", re.M)
    candidates = []
    for parent in Path(__file__).resolve().parents:
        source_root = parent / "src" / "oriom"
        if not source_root.is_dir():
            continue
        for candidate in source_root.rglob("*.py"):
            if pattern.search(candidate.read_text(encoding="utf-8", errors="replace")):
                candidates.append((source_root, candidate))
        break

    if not candidates:
        raise unittest.SkipTest(
            f"{function_name} not found under src/oriom. "
            "Set ORIOM_ST_STATISTICAL_GRAPHS_MODULE or "
            "ORIOM_ST_STATISTICAL_GRAPHS_PATH to locate its implementation."
        )
    if len(candidates) != 1:
        raise ImportError(
            f"Multiple definitions of {function_name} found: "
            + ", ".join(str(candidate) for _, candidate in candidates)
        )

    source_root, candidate = candidates[0]
    module_name = "oriom." + ".".join(
        candidate.relative_to(source_root).with_suffix("").parts
    )
    module = importlib.import_module(module_name)
    if not callable(getattr(module, function_name, None)):
        raise AttributeError(f"{module_name} does not define {function_name}")
    return module


def make_st_statistical_metocean(periods=25):
    """Build hourly start dates used as cross-run plot labels."""
    return pd.DataFrame(
        {"Hs": np.ones(periods, dtype=float)},
        index=pd.date_range("2026-11-03 06:00", periods=periods, freq="h"),
    )


def assert_valid_png(test_case, path):
    """Check that a graph was saved as a nonempty PNG file."""
    path = Path(path)
    test_case.assertTrue(path.is_file(), f"PNG file was not created: {path}")
    test_case.assertGreater(path.stat().st_size, 1000)
    with path.open("rb") as png_file:
        test_case.assertEqual(png_file.read(8), b"\x89PNG\r\n\x1a\n")


class TestFinalStatGraphST(FigureTestCase):
    """Numerical and plotting regression for costs, dates and invalid windows."""

    @classmethod
    def setUpClass(cls):
        cls.graph_module = _load_st_statistics_module("final_stat_graph_ST")

    def setUp(self):
        self.metocean = make_st_statistical_metocean()
        # Insertion order 10, 1, 5 -> sorted run keys 1, 5, 10.
        self.direct_costs = {10: 250_000, 1: 500_000, 5: 100_000}
        self.energy_losses = {5: 0.08, 10: 0.09, 1: 0.05}
        self.expected_direct = [500_000, 100_000, 250_000]
        self.expected_energy_eur = [50_000, 80_000, 90_000]
        self.expected_total = [550_000, 180_000, 340_000]

    def _call(self, *, failure_ranges=None, failure_not_corrected_idx=0, save_dir=None):
        return self.graph_module.final_stat_graph_ST(
            failure_ranges=[] if failure_ranges is None else failure_ranges,
            failure_not_corrected_idx=failure_not_corrected_idx,
            total_costs=self.direct_costs,
            total_energy_losses_costs=self.energy_losses,
            metocean_df=self.metocean,
            save_dir=save_dir,
        )

    def test_returns_index_of_minimum_total_cost_in_sorted_run_order(self):
        """The returned index is the sorted position, not the original run key."""
        self.assertEqual(self._call(), 1)

    def test_stacked_bar_values_energy_conversion_and_optimal_outline(self):
        """Stacks show EUR direct costs plus M EUR * 1e6 at datetime positions."""
        with patch.object(self.graph_module.plt, "close") as mocked_close:
            self.assertEqual(self._call(), 1)
            ax = plt.gcf().axes[0]
            bars = ax.patches
            self.assertEqual(len(bars), 7)
            np.testing.assert_allclose(
                [bar.get_height() for bar in bars[:3]], self.expected_direct
            )
            np.testing.assert_allclose(
                [bar.get_height() for bar in bars[3:6]], self.expected_energy_eur
            )
            np.testing.assert_allclose(
                [bar.get_y() for bar in bars[3:6]], self.expected_direct
            )
            self.assertAlmostEqual(bars[6].get_height(), self.expected_total[1])
            self.assertAlmostEqual(
                bars[6].get_x() + bars[6].get_width() / 2,
                mdates.date2num(self.metocean.index[1]),
            )
            self.assertAlmostEqual(
                bars[0].get_x() + bars[0].get_width() / 2,
                mdates.date2num(self.metocean.index[0]),
            )
        mocked_close.assert_called_once()

    def test_axis_uses_metocean_timestamps_and_highlights_minimum_label(self):
        """Axes use calendar dates and only the minimum total is annotated."""
        with patch.object(self.graph_module.plt, "close"):
            self._call()
            ax = plt.gcf().axes[0]
            self.assertEqual(ax.get_xlabel(), "Work start date")
            self.assertEqual(ax.get_ylabel(), "Total lifetime costs (€)")
            self.assertIsInstance(ax.xaxis.get_major_formatter(), mdates.DateFormatter)
            self.assertEqual(ax.xaxis.get_major_formatter().fmt, "%d/%m %H:%M")
            self.assertEqual(
                [label.get_text() for label in ax.get_legend().get_texts()],
                ["Direct costs", "Energy losses"],
            )
            self.assertEqual([text.get_text() for text in ax.texts], ["€180,000"])
            self.assertAlmostEqual(
                mdates.date2num(ax.texts[0].get_position()[0]),
                mdates.date2num(self.metocean.index[1]),
            )

    def test_creates_png_with_expected_filename_and_closes_figure(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            before = set(plt.get_fignums())
            self.assertEqual(self._call(save_dir=tmp_dir), 1)
            assert_valid_png(self, Path(tmp_dir) / "total_cost_losses_vs_Start_Date.png")
            self.assertEqual(set(plt.get_fignums()), before)

    def test_none_save_dir_does_not_call_savefig(self):
        with patch.object(self.graph_module.plt, "savefig") as mocked_save:
            self.assertEqual(self._call(save_dir=None), 1)
        mocked_save.assert_not_called()

    def test_tied_minima_select_first_sorted_position(self):
        direct = {30: 300_000, 20: 200_000, 10: 100_000}
        energy = {30: 0.0, 10: 0.1, 20: 0.0}
        self.assertEqual(
            self.graph_module.final_stat_graph_ST(
                [], 0, direct, energy, self.metocean
            ), 0
        )

    def test_original_input_dictionaries_and_metocean_are_unchanged(self):
        before_direct = self.direct_costs.copy()
        before_energy = self.energy_losses.copy()
        before_metocean = self.metocean.copy(deep=True)
        self._call()
        self.assertEqual(self.direct_costs, before_direct)
        self.assertEqual(self.energy_losses, before_energy)
        assert_frame_equal(self.metocean, before_metocean)

    def test_empty_runs_raise_value_error(self):
        with self.assertRaises(ValueError):
            self.graph_module.final_stat_graph_ST([], 0, {}, {}, self.metocean)

    def test_missing_energy_for_a_run_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.graph_module.final_stat_graph_ST(
                [], 0, {1: 100_000, 2: 200_000}, {1: 0.01}, self.metocean
            )

    def test_insufficient_metocean_timestamps_raise_value_error(self):
        with self.assertRaises(ValueError):
            self.graph_module.final_stat_graph_ST(
                [], 0, self.direct_costs, self.energy_losses,
                self.metocean.iloc[:2],
            )

    def test_unavailable_runs_are_excluded_from_minimum_search(self):
        """Index cutoff excludes a cheaper final run, without hiding its bars."""
        direct = {0: 300_000, 1: 250_000, 2: 10_000}
        losses = {0: 0.0, 1: 0.0, 2: 0.0}
        with patch.object(self.graph_module.plt, "close"):
            best = self.graph_module.final_stat_graph_ST(
                [(2, 2, ["ofw_fail_failure_A"])], 2, direct, losses, self.metocean
            )
            ax = plt.gcf().axes[0]
            self.assertEqual(best, 1)
            self.assertEqual(len(ax.patches), 9)  # 7 bars + 2 exclusion spans
            self.assertAlmostEqual(ax.patches[6].get_height(), 250_000)
            self.assertIn("failure A", [t.get_text() for t in ax.texts])

    def test_zero_cutoff_searches_all_runs(self):
        self.assertEqual(self._call(failure_not_corrected_idx=0), 1)

    def test_cutoff_beyond_last_run_searches_all_runs(self):
        self.assertEqual(self._call(failure_not_corrected_idx=99), 1)

    def test_failure_ranges_create_two_shaded_overlays_and_labels(self):
        ranges = [(1, 2, ["device A", "device B"])]
        with patch.object(self.graph_module.plt, "close"):
            self._call(failure_ranges=ranges)
            ax = plt.gcf().axes[0]
            self.assertEqual(len(ax.patches), 9)
            self.assertEqual(ax.patches[-1].get_hatch(), "///")
            self.assertEqual(
                [text.get_text() for text in ax.texts],
                ["€180,000", "device A\ndevice B", "Failure not corrected"],
            )
            self.assertIs(ax.texts[1].get_transform(), ax.get_xaxis_transform())
            self.assertIs(ax.texts[2].get_transform(), ax.get_xaxis_transform())

    def test_multiple_exclusion_ranges_add_individual_and_summary_annotations(self):
        ranges = [(1, 1, ["A"]), (2, 2, ["B"])]
        with patch.object(self.graph_module.plt, "close"):
            self._call(failure_ranges=ranges)
            ax = plt.gcf().axes[0]
            self.assertEqual(len(ax.patches), 11)
            self.assertEqual(
                [text.get_text() for text in ax.texts],
                ["€180,000", "A", "B", "Failure not corrected"],
            )

    def test_bar_width_tracks_metocean_resolution(self):
        with patch.object(self.graph_module.plt, "close"):
            self._call()
            width = plt.gcf().axes[0].patches[0].get_width()
            self.assertAlmostEqual(width, 0.65 / 24, places=8)

    def test_single_run_currently_raises_zero_division_error(self):
        """Document the current two-timestamp requirement for datetime bar width."""
        with self.assertRaises(ZeroDivisionError):
            self.graph_module.final_stat_graph_ST(
                [], 0, {0: 100.0}, {0: 0.0}, self.metocean,
            )

    def test_invalid_failure_range_index_raises(self):
        with self.assertRaises(IndexError):
            self._call(failure_ranges=[(0, 999, ["out of range"])])


class TestPlotEnergyLossesST(FigureTestCase):
    """Line plot tests for run selection and shaded failure intervals."""

    @classmethod
    def setUpClass(cls):
        cls.graph_module = _load_st_statistics_module("plot_energy_losses_ST")

    def setUp(self):
        self.metocean = make_st_statistical_metocean()
        self.losses = {10: 2500.0, 1: 1200.0, 5: 500.0}
        self.expected_losses = [1200.0, 500.0, 2500.0]

    def _call(self, *, failure_ranges=None, failure_not_corrected_idx=0, save_dir=None):
        return self.graph_module.plot_energy_losses_ST(
            failure_ranges=[] if failure_ranges is None else failure_ranges,
            failure_not_corrected_idx=failure_not_corrected_idx,
            total_energy_losses=self.losses,
            metocean_df=self.metocean,
            save_dir=save_dir,
        )

    def test_line_is_sorted_by_run_key_and_uses_kwh_values(self):
        with patch.object(self.graph_module.plt, "close") as mocked_close:
            self.assertIsNone(self._call())
            ax = plt.gcf().axes[0]
            self.assertEqual(len(ax.lines), 1)
            np.testing.assert_allclose(ax.lines[0].get_ydata(), self.expected_losses)
            np.testing.assert_allclose(
                mdates.date2num(pd.to_datetime(ax.lines[0].get_xdata())),
                mdates.date2num(self.metocean.index[:3]),
            )
        mocked_close.assert_called_once()

    def test_minimum_energy_loss_is_highlighted_at_sorted_position(self):
        with patch.object(self.graph_module.plt, "close"):
            self._call()
            ax = plt.gcf().axes[0]
            self.assertEqual(len(ax.collections), 1)
            marker = ax.collections[0].get_offsets()
            self.assertEqual(len(marker), 1)
            self.assertAlmostEqual(float(marker[0, 0]), mdates.date2num(self.metocean.index[1]))
            self.assertAlmostEqual(float(marker[0, 1]), 500.0)
            self.assertEqual(ax.get_ylabel(), "Total energy losses (kWh)")
            self.assertEqual(ax.get_xlabel(), "Work start date")

    def test_annotations_show_only_selected_minimum_in_kwh(self):
        """Only one annotation is produced in the updated function."""
        with patch.object(self.graph_module.plt, "close"):
            self._call()
            ax = plt.gcf().axes[0]
            self.assertEqual([t.get_text() for t in ax.texts], ["500 kWh"])
            self.assertAlmostEqual(mdates.date2num(ax.texts[0].xy[0]), mdates.date2num(self.metocean.index[1]))
            self.assertEqual(ax.texts[0].xy[1], 500.0)

    def test_xticks_use_every_twelfth_metocean_timestamp(self):
        losses = dict(reversed([(i, float(i + 1)) for i in range(25)]))
        with patch.object(self.graph_module.plt, "close"):
            self.graph_module.plot_energy_losses_ST([], 0, losses, self.metocean)
            ax = plt.gcf().axes[0]
            np.testing.assert_allclose(
                ax.get_xticks(), mdates.date2num(self.metocean.index[[0, 12, 24]]),
            )
            self.assertEqual(ax.xaxis.get_major_formatter().fmt, "%d/%m %H:%M")

    def test_creates_png_with_expected_filename_and_closes_figure(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            before = set(plt.get_fignums())
            self.assertIsNone(self._call(save_dir=tmp_dir))
            assert_valid_png(self, Path(tmp_dir) / "total_energy_losses_vs_Start_Date.png")
            self.assertEqual(set(plt.get_fignums()), before)

    def test_none_save_dir_does_not_call_savefig(self):
        with patch.object(self.graph_module.plt, "savefig") as mocked_save:
            self._call(save_dir=None)
        mocked_save.assert_not_called()

    def test_tied_minima_highlight_the_first_sorted_run(self):
        losses = {9: 1000.0, 1: 500.0, 5: 500.0}
        with patch.object(self.graph_module.plt, "close"):
            self.graph_module.plot_energy_losses_ST([], 0, losses, self.metocean)
            ax = plt.gcf().axes[0]
            marker = ax.collections[0].get_offsets()[0]
            self.assertAlmostEqual(float(marker[0]), mdates.date2num(self.metocean.index[0]))
            self.assertAlmostEqual(float(marker[1]), 500.0)

    def test_does_not_mutate_losses_or_metocean(self):
        original_losses = self.losses.copy()
        original_metocean = self.metocean.copy(deep=True)
        self._call()
        self.assertEqual(self.losses, original_losses)
        assert_frame_equal(self.metocean, original_metocean)

    def test_empty_energy_losses_raise_value_error(self):
        with self.assertRaises(ValueError):
            self.graph_module.plot_energy_losses_ST([], 0, {}, self.metocean)

    def test_insufficient_metocean_timestamps_raise_value_error(self):
        with self.assertRaises(ValueError):
            self.graph_module.plot_energy_losses_ST(
                [], 0, self.losses, self.metocean.iloc[:2]
            )

    def test_cutoff_excludes_global_minimum_after_not_corrected_index(self):
        """Select the smallest valid loss, not the globally lowest invalid loss."""
        losses = {0: 1200.0, 1: 800.0, 2: 1.0}
        with patch.object(self.graph_module.plt, "close"):
            self.graph_module.plot_energy_losses_ST(
                [(2, 2, ["unrepaired"])], 2, losses, self.metocean
            )
            ax = plt.gcf().axes[0]
            minimum = ax.collections[0].get_offsets()[0]
            self.assertAlmostEqual(float(minimum[0]), mdates.date2num(self.metocean.index[1]))
            self.assertAlmostEqual(float(minimum[1]), 800.0)
            self.assertEqual(ax.texts[0].get_text(), "800 kWh")

    def test_zero_cutoff_uses_all_runs(self):
        with patch.object(self.graph_module.plt, "close"):
            self._call(failure_not_corrected_idx=0)
            ax = plt.gcf().axes[0]
            self.assertEqual(ax.texts[0].get_text(), "500 kWh")

    def test_cutoff_beyond_last_run_uses_all_runs(self):
        with patch.object(self.graph_module.plt, "close"):
            self._call(failure_not_corrected_idx=25)
            ax = plt.gcf().axes[0]
            self.assertEqual(ax.texts[0].get_text(), "500 kWh")

    def test_failure_ranges_create_hatched_spans_and_descriptions(self):
        with patch.object(self.graph_module.plt, "close"):
            self._call(failure_ranges=[(1, 2, ["broken cable", "bad weather"])])
            ax = plt.gcf().axes[0]
            self.assertEqual(len(ax.patches), 2)
            self.assertEqual(ax.patches[1].get_hatch(), "///")
            self.assertEqual(
                [t.get_text() for t in ax.texts],
                ["500 kWh", "broken cable\nbad weather", "Failure not corrected"],
            )
            self.assertIs(ax.texts[1].get_transform(), ax.get_xaxis_transform())
            self.assertIs(ax.texts[2].get_transform(), ax.get_xaxis_transform())

    def test_multiple_failure_ranges_add_summary_annotation(self):
        with patch.object(self.graph_module.plt, "close"):
            self._call(failure_ranges=[(0, 0, ["A"]), (2, 2, ["B"])])
            ax = plt.gcf().axes[0]
            self.assertEqual(len(ax.patches), 4)
            self.assertEqual(
                [t.get_text() for t in ax.texts],
                ["500 kWh", "A", "B", "Failure not corrected"],
            )

    def test_one_run_works_for_line_plot(self):
        with patch.object(self.graph_module.plt, "close"):
            self.graph_module.plot_energy_losses_ST(
                [], 0, {0: 77.5}, self.metocean
            )
            ax = plt.gcf().axes[0]
            self.assertEqual(ax.texts[0].get_text(), "78 kWh")
            np.testing.assert_allclose(ax.lines[0].get_ydata(), [77.5])

    def test_invalid_failure_range_index_raises(self):
        with self.assertRaises(IndexError):
            self._call(failure_ranges=[(0, 999, ["out of range"])])


if __name__ == "__main__":
    unittest.main(verbosity=2)
