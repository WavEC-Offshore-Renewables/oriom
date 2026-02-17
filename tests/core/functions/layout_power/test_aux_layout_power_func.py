# tests/test_power_preventive_evaluation.py

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import math

import pandas as pd
import numpy as np
import networkx as nx

from oriom.core.functions.layout_power import aux_layout_power_func


class TestStatisticalPowerPreventiveEvaluation(unittest.TestCase):
    def test_wind_wave_branch_simple(self):
        """
        Non-PV branch: dict_power maps month -> scalar value.
        energy = shutdown_hours[selected_month] * (dict_power[selected_month]/n_device_tot) * power_level
        """
        energy = aux_layout_power_func.statistical_power_preventive_evaluation(
            dict_power={6: 1200.0},
            shutdown_hours_dict={6: 10.0},
            date=datetime(2025, 6, 1, 5, 0, 0),
            n_device_tot=4,
            power_level=2.0,
            degradation_rate=0,
            start_year=2020,
            double_shift=False,
            selected_month=6,
        )

        # expected = 10 * (1200/4) * 2 = 10 * 300 * 2 = 6000
        self.assertAlmostEqual(energy, 6000.0, places=7)

    def test_pv_branch_correct_energy_no_night_shift(self):
        """
        PV branch (no night shift):
        - dict_power: month -> dict(hour -> power)
          hours 6..17 => 100, night => 0
        - shutdown_hours ceil -> 4 hours
        - start at 16:00: count hours 16, 17, poi salta la notte, poi 6 e 7
        - per-hour share = power / (n_device_tot * power_level)
        - apply yearly degradation from start_year to date.year
        Expected energy = 4 * [100/(5*2)] * (0.9 ** 2).
        """
        dict_power = {6: {h: (100.0 if 6 <= h <= 17 else 0.0) for h in range(24)}}
        n_device_tot = 5
        power_level = 2.0
        degradation_rate = 10  # 10%
        start_year = 2023
        date = datetime(2025, 6, 1, 16, 0, 0)

        per_hour = (100.0 / (n_device_tot * power_level))
        per_hour_degraded = per_hour * (1 - degradation_rate / 100) ** (date.year - start_year)
        expected_total = 4 * per_hour_degraded  # 4 daylight counted hours

        energy = aux_layout_power_func.statistical_power_preventive_evaluation(
            dict_power=dict_power,
            shutdown_hours_dict={6: 3.3},
            date=date,
            n_device_tot=n_device_tot,
            power_level=power_level,
            degradation_rate=degradation_rate,
            start_year=start_year,
            double_shift=False,
            selected_month=6,
        )

        self.assertAlmostEqual(energy, expected_total, places=9)

    def test_pv_branch_with_double_shift_counts_night_hours(self):
        """
        PV branch con double_shift=True:
        Le ore notturne vengono comunque conteggiate nel totale di shutdown,
        ma contribuiscono energia solo se la potenza è > 0.
        Per 4 ore a partire dalle 16:00:
        - 16 e 17 hanno power>0, 2 ore aggiuntive di notte con power=0.
        => energy = 2 * per_hour_degraded.
        """
        dict_power = {6: {h: (100.0 if 6 <= h <= 17 else 0.0) for h in range(24)}}
        n_device_tot = 5
        power_level = 2.0
        degradation_rate = 10
        start_year = 2023
        date = datetime(2025, 6, 1, 16, 0, 0)

        per_hour = (100.0 / (n_device_tot * power_level))
        per_hour_degraded = per_hour * (1 - degradation_rate / 100) ** (date.year - start_year)

        energy = aux_layout_power_func.statistical_power_preventive_evaluation(
            dict_power=dict_power,
            shutdown_hours_dict={6: 3.3},
            date=date,
            n_device_tot=n_device_tot,
            power_level=power_level,
            degradation_rate=degradation_rate,
            start_year=start_year,
            double_shift=True,
            selected_month=6,
        )

        expected_total_double = 2 * per_hour_degraded  # solo 16 e 17 contribuiscono
        self.assertAlmostEqual(energy, expected_total_double, places=9)


class TestFindHighestPowerNode(unittest.TestCase):

    def test_returns_level_of_node_with_max_power(self):
        G = nx.DiGraph()
        G.add_node("sub", level="substation", power=10.0)
        G.add_node("dev1", level="device", power=5.0)
        G.add_node("dev2", level="device", power=15.0)

        level = aux_layout_power_func.find_highest_power_node(G)
        self.assertEqual(level, "device")

    def test_missing_power_treated_as_zero(self):
        G = nx.DiGraph()
        G.add_node("n1", level="level_a")          # no power -> 0
        G.add_node("n2", level="level_b", power=3)

        level = aux_layout_power_func.find_highest_power_node(G)
        self.assertEqual(level, "level_b")

    def test_all_zero_power_returns_first_level(self):
        G = nx.DiGraph()
        G.add_node("n1", level="L1", power=0.0)
        G.add_node("n2", level="L2", power=0.0)

        level = aux_layout_power_func.find_highest_power_node(G)
        self.assertEqual(level, "L1")


class TestGetNearestMonthValue(unittest.TestCase):

    def test_several_cases_with_subtests(self):
        """
        Use subTest to cover multiple month / expected combinations.
        """
        month_dict = {3: 1.0, 7: 2.0, 10: 3.0}
        cases = [
            (3, 3),   # exact
            (5, 3),   # midway between 3 and 7 -> 3
            (1, 3),   # < all -> 3
            (12, 10), # > all -> 10
        ]
        for month, expected in cases:
            with self.subTest(month=month, expected=expected):
                nearest = aux_layout_power_func.get_nearest_month_value(month, month_dict)
                self.assertEqual(nearest, expected)

    def test_exact_month_present(self):
        month_dict = {3: 1.0, 6: 2.0}
        nearest = aux_layout_power_func.get_nearest_month_value(3, month_dict)
        self.assertEqual(nearest, 3)


class TestCreateEndStartLifetime(unittest.TestCase):

    def test_create_single_row_with_expected_values(self):
        cols = [
            "Date",
            "Event",
            "col3",
            "col4",
            "col5",
            "col6",
            "col7",
            "col8",
            "Perc_availability",
            "Extra",
        ]
        d = datetime(2030, 1, 1)
        event = "commissioning"

        df = aux_layout_power_func.create_end_start_lifetime(d, event, cols)

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(df.shape, (1, len(cols)))
        self.assertListEqual(list(df.columns), cols)

        row = df.iloc[0]
        self.assertEqual(row["Date"], d)
        self.assertEqual(row["Event"], event)
        self.assertEqual(row["Perc_availability"], 100.0)
        for c in ["col3", "col4", "col5", "col6", "col7", "col8"]:
            self.assertEqual(row[c], "-")
        self.assertIsNone(row["Extra"])


class TestChooseLoc(unittest.TestCase):

    def setUp(self):
        self.date = datetime(2025, 1, 1)

    @patch("oriom.core.functions.layout_power.aux_layout_power_func.random.choice")
    def test_choose_node_non_pv_avoids_failed_nodes(self, m_choice):
        """
        For node-level failures, choose_loc must not select nodes in list_failed.
        """
        G = nx.DiGraph()
        G.add_node(1, level="device")
        G.add_node(2, level="device")
        G.add_node(3, level="device")

        failed = {1}
        m_choice.return_value = 2

        loc = aux_layout_power_func.choose_loc(
            level="device",
            G=G,
            component_level_power="device",
            date=self.date,
            list_failed=failed,
            tech="WIND",
        )

        self.assertEqual(loc, 2)
        self.assertNotIn(loc, failed)

    @patch("oriom.core.functions.layout_power.aux_layout_power_func.random.choice")
    def test_choose_node_pv_uses_component_level_power(self, m_choice):
        """
        For PV and levels 'device'/'string', level is replaced by component_level_power.
        """
        G = nx.DiGraph()
        G.add_node(10, level="string")
        G.add_node(11, level="string")

        m_choice.return_value = 10

        loc = aux_layout_power_func.choose_loc(
            level="device",
            G=G,
            component_level_power="string",
            date=self.date,
            list_failed=set(),
            tech="PV",
        )

        self.assertEqual(loc, 10)
        self.assertEqual(G.nodes[loc]["level"], "string")

    @patch("oriom.core.functions.layout_power.aux_layout_power_func.random.choice")
    def test_choose_edge_visible_only(self, m_choice):
        """
        For edge levels, only edges with visible=True are eligible.
        """
        G = nx.DiGraph()
        G.add_node(1, level="sub")
        G.add_node(2, level="sub")
        G.add_node(3, level="sub")

        G.add_edge(1, 2, level="array_cable", visible=True)
        G.add_edge(2, 3, level="array_cable", visible=False)

        m_choice.return_value = (1, 2)

        loc = aux_layout_power_func.choose_loc(
            level="array_cable",
            G=G,
            component_level_power="device",
            date=self.date,
            list_failed=set(),
            tech="WIND",
        )

        self.assertEqual(loc, (1, 2))

    def test_choose_edge_pv_string_cable_without_edges_returns_dummy(self):
        """
        For PV and 'string_cable', if there are no edges, the function returns ('x', 'x').
        """
        G = nx.DiGraph()
        G.add_node(1, level="string")

        loc = aux_layout_power_func.choose_loc(
            level="string_cable",
            G=G,
            component_level_power="string",
            date=self.date,
            list_failed=set(),
            tech="PV",
        )

        self.assertEqual(loc, ("x", "x"))

    def test_choose_edge_no_edges_raises_keyerror_for_non_pv(self):
        """
        For non-PV and an edge level with no edges, a KeyError must be raised.
        """
        G = nx.DiGraph()
        G.add_node(1, level="string")

        with self.assertRaises(KeyError):
            aux_layout_power_func.choose_loc(
                level="array_cable",
                G=G,
                component_level_power="device",
                date=self.date,
                list_failed=set(),
                tech="WIND",
            )

    def test_unknown_level_raises_value_error(self):
        """
        Unknown level must raise ValueError.
        """
        G = nx.DiGraph()
        G.add_node(1, level="device")

        with self.assertRaises(ValueError):
            aux_layout_power_func.choose_loc(
                level="unknown_level",
                G=G,
                component_level_power="device",
                date=self.date,
                list_failed=set(),
                tech="WIND",
            )

    @patch("oriom.core.functions.layout_power.aux_layout_power_func.random.choice")
    @patch("oriom.core.functions.layout_power.aux_layout_power_func.logging.error")
    def test_all_nodes_failed_logs_error_and_selects_any(self, m_log_error, m_choice):
        """
        If all nodes at a given level are failed, an error is logged and one of them is still selected.
        """
        G = nx.DiGraph()
        G.add_node(1, level="device")
        G.add_node(2, level="device")
        failed = {1, 2}
        m_choice.return_value = 1

        loc = aux_layout_power_func.choose_loc(
            level="device",
            G=G,
            component_level_power="device",
            date=self.date,
            list_failed=failed,
            tech="WIND",
        )

        self.assertEqual(loc, 1)
        # verify error is logged
        m_log_error.assert_called_once()
        self.assertIn("all device has failed", m_log_error.call_args[0][0])

    @patch("oriom.core.functions.layout_power.aux_layout_power_func.random.choice")
    @patch("oriom.core.functions.layout_power.aux_layout_power_func.logging.error")
    def test_all_edges_failed_logs_error_and_selects_any(self, m_log_error, m_choice):
        """
        If all candidate edges are failed, an error is logged and one of them is still selected.
        """
        G = nx.DiGraph()
        G.add_node(1, level="sub")
        G.add_node(2, level="sub")
        G.add_edge(1, 2, level="array_cable", visible=True)

        failed_edges = {(1, 2)}
        m_choice.return_value = (1, 2)

        loc = aux_layout_power_func.choose_loc(
            level="array_cable",
            G=G,
            component_level_power="device",
            date=self.date,
            list_failed=failed_edges,
            tech="WIND",
        )

        self.assertEqual(loc, (1, 2))
        # verify error is logged
        m_log_error.assert_called_once()
        self.assertIn("all the components", m_log_error.call_args[0][0])

class TestFixPercentageMarkersDates(unittest.TestCase):

    def test_copy_percentage_to_markers_only(self):
        df = pd.DataFrame(
            {
                "Date": pd.date_range("2025-01-01", periods=5, freq="D"),
                "Event": [
                    "normal",
                    "First Day of month",
                    "normal",
                    "Last Day of month",
                    "decomissioning_project",
                ],
                "Perc_availability": [90.0, 0.0, 80.0, 0.0, 0.0],
            }
        )

        df_out = aux_layout_power_func.fix_percentage_markers_dates(df.copy())

        # non-target events unchanged
        self.assertEqual(df_out.loc[0, "Perc_availability"], 90.0)
        self.assertEqual(df_out.loc[2, "Perc_availability"], 80.0)

        # First Day of month takes previous value: 90.0
        self.assertEqual(df_out.loc[1, "Perc_availability"], 90.0)
        # Last Day of month takes previous non-target value: 80.0
        self.assertEqual(df_out.loc[3, "Perc_availability"], 80.0)
        # decomissioning_project also takes last known value: 80.0
        self.assertEqual(df_out.loc[4, "Perc_availability"], 80.0)

    def test_no_markers_no_change(self):
        """
        If there are no target marker events, the DataFrame must remain unchanged.
        """
        df = pd.DataFrame(
            {
                "Date": pd.date_range("2025-01-01", periods=3, freq="D"),
                "Event": ["normal", "normal", "normal"],
                "Perc_availability": [90.0, 85.0, 80.0],
            }
        )

        df_out = aux_layout_power_func.fix_percentage_markers_dates(df.copy())
        pd.testing.assert_frame_equal(df, df_out)


class TestStringLocation(unittest.TestCase):

    @patch("oriom.core.functions.layout_power.aux_layout_power_func.random.choice")
    def test_returns_string_not_in_failed_set(self, m_choice):
        failed_strings = {0, 1}
        string_inverter = {0, 1, 2, 3}

        m_choice.return_value = 2

        k = aux_layout_power_func.string_location(
            failed_strings=failed_strings,
            string_inverter=string_inverter,
        )

        self.assertEqual(k, 2)
        self.assertNotIn(k, failed_strings)

    @patch("oriom.core.functions.layout_power.aux_layout_power_func.random.choice")
    @patch("oriom.core.functions.layout_power.aux_layout_power_func.logging.warning")
    def test_when_all_failed_logs_warning_and_still_returns_choice(self, m_log_warning, m_choice):
        """
        If all strings are failed for the inverter, a warning is logged and
        random.choice is still used over that set.
        """
        failed_strings = {0, 1}
        string_inverter = {0, 1}
        m_choice.return_value = 0

        k = aux_layout_power_func.string_location(
            failed_strings=failed_strings,
            string_inverter=string_inverter,
        )

        self.assertIn(k, failed_strings)
        # verify warning is logged
        m_log_warning.assert_called_once()
        self.assertIn("All strings are failed", m_log_warning.call_args[0][0])


class TestAddMarkersMonthYear(unittest.TestCase):

    def test_insert_extra_rows_in_order(self):
        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2025-01-01", "2025-01-03", "2025-01-05"]),
                "Event": ["A", "B", "C"],
            }
        )

        df_extra = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2025-01-02", "2025-01-04"]),
                "Event": ["M1", "M2"],
            }
        )

        df_final = aux_layout_power_func.add_markers_month_year(df, df_extra)

        self.assertEqual(len(df_final), 5)
        self.assertListEqual(
            list(df_final["Date"]),
            list(pd.to_datetime(
                ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05"]
            )),
        )

        # Check that extra markers are in the right place
        self.assertEqual(df_final.loc[1, "Event"], "M1")
        self.assertEqual(df_final.loc[3, "Event"], "M2")

    def test_insert_before_first_and_after_last(self):
        df = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2025-01-10", "2025-01-20"]),
                "Event": ["A", "B"],
            }
        )

        df_extra = pd.DataFrame(
            {
                "Date": pd.to_datetime(["2025-01-01", "2025-01-30"]),
                "Event": ["Start", "End"],
            }
        )

        df_final = aux_layout_power_func.add_markers_month_year(df, df_extra)

        self.assertEqual(len(df_final), 4)
        self.assertListEqual(
            list(df_final["Date"]),
            list(pd.to_datetime(
                ["2025-01-01", "2025-01-10", "2025-01-20", "2025-01-30"]
            )),
        )
        self.assertEqual(df_final.loc[0, "Event"], "Start")
        self.assertEqual(df_final.loc[3, "Event"], "End")


class TestFindPowerAtNode(unittest.TestCase):

    def test_node_level_with_zero_power_uses_ancestors_sum(self):
        G = nx.DiGraph()
        G.add_node("sub", level="substation", power=5.0)
        G.add_node("string1", level="string", power=0.0)
        G.add_node("device1", level="device", power=0.0)

        G.add_edge("sub", "string1")
        G.add_edge("string1", "device1")

        # For level "device", node device1 has power 0,
        # so function should sum power over ancestors + node itself => 5.0
        p = aux_layout_power_func.find_power_at_node(G, level="device")
        self.assertAlmostEqual(p, 5.0)

    def test_node_level_with_non_zero_power_returns_direct_value(self):
        G = nx.DiGraph()
        G.add_node("sub", level="substation", power=7.5)
        G.add_node("device1", level="device", power=0.0)
        G.add_edge("sub", "device1")

        p = aux_layout_power_func.find_power_at_node(G, level="substation")
        self.assertAlmostEqual(p, 7.5)

    def test_edge_level_uses_reference_node_power(self):
        G = nx.DiGraph()
        G.add_node("sub", power=10.0)
        G.add_node("string1", power=0.0)
        G.add_edge("sub", "string1", level="array_cable")

        p = aux_layout_power_func.find_power_at_node(G, level="array_cable")
        self.assertAlmostEqual(p, 10.0)


class TestCreateListDate(unittest.TestCase):

    def test_with_last_shift_present(self):
        """
        days_last != 0:
        - Per ogni sub-list, start = date originali
        - end:
            * elementi tranne l’ultimo: + duration_main
            * ultimo elemento: + duration_last
        """
        insp = MagicMock()
        insp.days_last = 1
        insp.duration_main = 2.0
        insp.duration_last = 3.0

        t0 = pd.Timestamp("2025-01-01 00:00")
        t1 = pd.Timestamp("2025-01-01 04:00")
        t2 = pd.Timestamp("2025-01-02 00:00")
        inspection_dates = [[t0, t1], [t2]]

        starts, ends = aux_layout_power_func.create_list_date(insp, inspection_dates)

        # starts
        self.assertEqual(starts, [[t0, t1], [t2]])

        # first sub: t0 -> +dur_main, t1 -> +dur_last
        self.assertEqual(ends[0][0], t0 + pd.Timedelta(hours=math.ceil(insp.duration_main)))
        self.assertEqual(ends[0][1], t1 + pd.Timedelta(hours=math.ceil(insp.duration_last)))

        # second sub: unico elemento -> ultimo => +dur_last
        self.assertEqual(ends[1][0], t2 + pd.Timedelta(hours=math.ceil(insp.duration_last)))

    def test_without_last_shift(self):
        """
        days_last == 0:
        - tutti gli elementi usano duration_main
        """
        insp = MagicMock()
        insp.days_last = 0
        insp.duration_main = 2.0
        insp.duration_last = 0.0

        t0 = pd.Timestamp("2025-01-01 00:00")
        t1 = pd.Timestamp("2025-01-01 04:00")
        t2 = pd.Timestamp("2025-01-02 00:00")
        inspection_dates = [[t0, t1], [t2]]

        starts, ends = aux_layout_power_func.create_list_date(insp, inspection_dates)

        self.assertEqual(starts, [[t0, t1], [t2]])

        self.assertEqual(ends[0][0], t0 + pd.Timedelta(hours=math.ceil(insp.duration_main)))
        self.assertEqual(ends[0][1], t1 + pd.Timedelta(hours=math.ceil(insp.duration_main)))
        self.assertEqual(ends[1][0], t2 + pd.Timedelta(hours=math.ceil(insp.duration_main)))


class TestTakeDateInspectionOperScheduler(unittest.TestCase):

    @patch("oriom.core.functions.layout_power.aux_layout_power_func.get_inspections_date")
    @patch("oriom.core.functions.layout_power.aux_layout_power_func.approximate_hourly_data")
    def test_take_date_inspection_oper_scheduler_basic(self, m_approx, m_get_dates):
        """
        Ensure approximate_hourly_data is applied to each trigger and that
        get_inspections_date is called with the correct series.
        """
        d1 = datetime(2025, 1, 1, 12, 15)
        d2 = datetime(2025, 1, 2, 3, 45)

        m_approx.side_effect = lambda d: d.replace(minute=0, second=0, microsecond=0)

        log_aux = pd.DataFrame({"d_trigger": [d1, d2]})
        # Use m_approx to create the expected index
        idx = [m_approx(d1), m_approx(d2)]
        oper_schedule = pd.DataFrame(
            {"days_inspected": [["a"], ["b"]]},
            index=idx,
        )

        m_get_dates.return_value = ["INSPECTION_DATES"]

        result = aux_layout_power_func.take_date_inspection_oper_scheduler(
            log_aux=log_aux, oper_schedule=oper_schedule
        )

        self.assertEqual(result, ["INSPECTION_DATES"])
        # 2 calls in the test + 2 inside the function = 4
        self.assertEqual(m_approx.call_count, 4)

        args, kwargs = m_get_dates.call_args
        series_passed = args[0]
        self.assertTrue(series_passed.index.equals(pd.DatetimeIndex(idx)))
        self.assertListEqual(series_passed['days_inspected'].tolist(), [["a"], ["b"]])


class TestTimeseriesPowerPreventiveEvaluation(unittest.TestCase):

    @patch("oriom.core.functions.layout_power.aux_layout_power_func.create_list_date")
    def test_simple_case_single_interval_uses_main_factor(self, m_create_list_date):
        """
        Simple case: a single inspection, a single interval.
        Here we verify the use of base_factor_main (consistent with the current logic:
        the condition i == len(insp_start) never occurs).
        """
        insp = MagicMock()
        insp.n_dev_done_last_shift = 1
        insp.n_crew_last = 1
        insp.n_dev_done_main_shift = 1
        insp.n_crew_main = 1
        insp.n_vessel_main = 1
        insp.n_vessel_last = 1
        insp.duration_main = 1.0
        insp.duration_last = 1.0
        insp.days_last = 0  # consider only main
        insp.op_tow_port = False

        start = pd.Timestamp("2025-01-01 00:00")
        end = pd.Timestamp("2025-01-01 01:00")
        # timeseries_power_preventive_evaluation expects two lists-of-lists
        m_create_list_date.return_value = ([[start]], [[end]])

        idx = pd.date_range(start="2025-01-01 00:00", periods=3, freq="H")
        metocean_timeseries = pd.DataFrame(
            {"p_wind_per_device": [10.0, 20.0, 30.0]}, index=idx
        )

        power_level = 0.5
        tech1 = "wind"

        energy_list, shutdown_list = aux_layout_power_func.timeseries_power_preventive_evaluation(
            insp=insp,
            inspection_dates=[["dummy"]],
            metocean_timeseries=metocean_timeseries,
            power_level=power_level,
            tech1=tech1,
        )

        coeff_main = math.ceil(insp.n_dev_done_main_shift / insp.n_crew_main)
        base_factor_main = power_level * insp.n_vessel_main * math.ceil(
            insp.n_dev_done_main_shift / coeff_main
        )
        expected_energy = 10.0 * base_factor_main
        expected_hours = 1 * base_factor_main

        self.assertEqual(len(energy_list), 1)
        self.assertEqual(len(shutdown_list), 1)
        self.assertAlmostEqual(energy_list[0], expected_energy, places=7)
        self.assertAlmostEqual(shutdown_list[0], expected_hours, places=7)

    @patch("oriom.core.functions.layout_power.aux_layout_power_func.create_list_date")
    def test_no_overlap_returns_zero(self, m_create_list_date):
        """
        If there is no overlap between inspection intervals and weather timeseries,
        energy_list and shutdown_hour_list must be [0].
        """
        insp = MagicMock()
        insp.n_dev_done_last_shift = 1
        insp.n_crew_last = 1
        insp.n_dev_done_main_shift = 1
        insp.n_crew_main = 1
        insp.n_vessel_main = 1
        insp.n_vessel_last = 1
        insp.duration_main = 1.0
        insp.duration_last = 1.0
        insp.days_last = 0
        insp.op_tow_port = False

        start = pd.Timestamp("2025-01-01 00:00")
        end = pd.Timestamp("2025-01-01 01:00")
        m_create_list_date.return_value = ([[start]], [[end]])

        idx = pd.date_range(start="2025-01-02 00:00", periods=3, freq="H")
        metocean_timeseries = pd.DataFrame(
            {"p_wind_per_device": [10.0, 20.0, 30.0]}, index=idx
        )

        energy_list, shutdown_list = aux_layout_power_func.timeseries_power_preventive_evaluation(
            insp=insp,
            inspection_dates=[["dummy"]],
            metocean_timeseries=metocean_timeseries,
            power_level=0.5,
            tech1="wind",
        )

        self.assertEqual(energy_list, [0])
        self.assertEqual(shutdown_list, [0])


class TestTakePowerLevelInspections(unittest.TestCase):

    def test_take_power_levels_for_component_and_inspection_levels(self):
        """
        Ensure power at component_level_power and at inspection levels is computed.
        """
        G = nx.DiGraph()
        # component_level_power will be 'device' (max power)
        G.add_node("dev", level="device", power=10.0)
        G.add_node("sub", level="substation", power=5.0)
        G.add_edge("sub", "dev", level="array_cable")

        class DummyInspClass:
            def __init__(self, level):
                self.level = level

        class DummyStat:
            def __init__(self, level):
                self.insp_class = DummyInspClass(level)

        inspections_port_stat = [DummyStat(level="substation")]
        inspections_site_stat = [DummyStat(level="device")]  # same as component level

        power_dict = aux_layout_power_func.take_power_level_inspections(
            G_tech=G,
            inspections_port_stat=inspections_port_stat,
            inspections_site_stat=inspections_site_stat,
        )

        # Keys: 'device' (component) and 'substation'
        self.assertIn("device", power_dict)
        self.assertIn("substation", power_dict)

        self.assertAlmostEqual(power_dict["device"], 10.0, places=7)
        self.assertAlmostEqual(power_dict["substation"], 5.0, places=7)

    def test_inspection_level_none_is_ignored(self):
        """
        If inspection.insp_class.level is None, it must not be added to the dict.
        """
        G = nx.DiGraph()
        G.add_node("dev", level="device", power=10.0)

        class DummyInspClass:
            def __init__(self, level):
                self.level = level

        class DummyStat:
            def __init__(self, level):
                self.insp_class = DummyInspClass(level)

        inspections_port_stat = [DummyStat(level=None)]
        inspections_site_stat = []

        power_dict = aux_layout_power_func.take_power_level_inspections(
            G_tech=G,
            inspections_port_stat=inspections_port_stat,
            inspections_site_stat=inspections_site_stat,
        )

        self.assertEqual(list(power_dict.keys()), ["device"])


class TestTakeMonthInspection(unittest.TestCase):

    @patch("oriom.core.functions.layout_power.aux_layout_power_func.pd.date_range")
    def test_no_months_range_falls_back_to_start_month(self, m_date_range):
        """
        If date_range returns an empty index, the function must fall back to the
        start_insp_date.month before applying get_nearest_month_value.
        """
        m_date_range.return_value = pd.DatetimeIndex([])
        start_insp_date = datetime(2025, 1, 10)
        row = pd.Series({"d_end": datetime(2025, 2, 10)})
        shutdown_hours_dict = {1: 10.0, 2: 20.0}

        month = aux_layout_power_func.take_month_inspection(
            start_insp_date=start_insp_date,
            row=row,
            shutdown_hours_dict=shutdown_hours_dict,
        )

        # start month is 1, and 1 is present in dict
        self.assertEqual(month, 1)

    def test_average_months_range_and_nearest(self):
        """
        With a non-empty months_list, selected_month is ceil(mean(months_list)),
        then snapped to the nearest available month in shutdown_hours_dict.
        """
        start_insp_date = datetime(2025, 1, 1)
        row = pd.Series({"d_end": datetime(2025, 3, 31)})
        shutdown_hours_dict = {2: 10.0, 3: 20.0}

        month = aux_layout_power_func.take_month_inspection(
            start_insp_date=start_insp_date,
            row=row,
            shutdown_hours_dict=shutdown_hours_dict,
        )

        self.assertEqual(month, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
