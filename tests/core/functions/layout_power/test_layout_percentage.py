# tests/core/functions/layout_power/test_layout_percentage.py

import unittest
from unittest.mock import patch
from datetime import datetime

import pandas as pd
import networkx as nx

from oriom.core.functions.layout_power import layout_percentage


# ------------------------------------------------------------------
# Minimal test doubles
# ------------------------------------------------------------------

class DummyOpClass:
    def __init__(self, tow_to_port=False):
        self.tow_to_port = tow_to_port


class DummyOp:
    def __init__(self, op_id, tow_to_port=False):
        self.id = op_id
        self.op_class = DummyOpClass(tow_to_port=tow_to_port)


DUMMY_OPERATIONS_STATS = [DummyOp("op_corr_001", tow_to_port=False)]


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

class TestReturnPercentageEmptyLog(unittest.TestCase):
    """Tests for return_percentage when no events match the target technology."""

    def setUp(self):
        # Prefix does NOT match prefix_list -> filtered log is empty
        self.log_events = pd.DataFrame(
            {
                "id": ["abc.001"],
                "event": ["failure"],
                "d_trigger": [datetime(2025, 1, 1, 0, 0, 0)],
            }
        )

        self.G = nx.DiGraph()
        self.G.add_node(0, level="SHORE", power=0)
        self.G.add_node(1, level="device", power=10.0)

    def test_returns_empty_df_with_expected_columns(self):
        """
        If log is empty after filtering, function returns an empty DataFrame
        with columns COLS[:-2] (no markers are created in this branch).
        """
        df = layout_percentage.return_percentage(
            log_events=self.log_events,
            prefix_list=["ofw", "oce"],
            operations_corrective_stat=DUMMY_OPERATIONS_STATS,
            G=self.G,
            shut_attribute="wtg_shutdown_dict",
            start_year=2025,
            start_month=1,
            n_lifetime=1,
            n_devices=10,
            tech="wind",
            find_element_class=None,
        )

        self.assertTrue(df.empty)
        self.assertEqual(
            list(df.columns),
            ["Date", "Event", "id", "Comments", "Name", "Loc", "Shutdown", "Shut/Fix"],
        )


class TestReturnPercentageNonPV(unittest.TestCase):
    """Tests for non-PV logic inside return_percentage."""

    def setUp(self):
        # Two events matching prefix_list
        self.log_events = pd.DataFrame(
            {
                "id": ["ofw.001", "ofw.002"],
                "event": ["failure", "operation"],
                "d_trigger": [
                    datetime(2025, 1, 10, 0, 0, 0),
                    datetime(2025, 1, 20, 0, 0, 0),
                ],
            }
        )

        self.G = nx.DiGraph()
        self.G.add_node(0, level="SHORE", power=0)
        self.G.add_node(1, level="device", power=10.0)

    @patch("oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.fix_percentage_markers_dates",
           side_effect=lambda df: df)
    @patch("oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.add_markers_month_year",
           side_effect=lambda df, df_extra: pd.concat([df, df_extra], ignore_index=True))
    @patch("oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.find_highest_power_node",
           return_value="device")
    @patch("oriom.core.functions.layout_power.layout_percentage.logs_corrective_locations")
    @patch("oriom.core.functions.layout_power.layout_percentage.shut")
    @patch("oriom.core.functions.layout_power.layout_percentage.fix")
    def test_non_pv_shut_and_fix_update_percentages(
        self,
        mock_fix,
        mock_shut,
        mock_logs_corr,
        _mock_find_highest,
        _mock_add_markers,
        _mock_fix_markers,
    ):
        """
        Non-PV:
        - failure -> shut -> 50% availability
        - operation -> fix -> 100% availability
        """
        # logs_corrective_locations returns dict-based events (as in real implementation)
        def fake_logs_corrective_locations(r, op_corr_excluding_tow, shut_attribute, find_element_class, dict_locations, op_corr_tow={}, op_add_tow={}):
            if r["id"] == "ofw.001" and r["event"] == "failure":
                return (
                    [
                        {
                            "date": r["Date"],
                            "event": "failure",
                            "id": r["id"],
                            "comments": "failure event",
                            "name": "WTG Failure",
                            "failure_id": r["id"],
                            "level": "device",
                            "shutdown": True,
                            "shut_fix": "shut",
                            "loc": 1,
                        }
                    ],
                    dict_locations,
                )
            if r["id"] == "ofw.002" and r["event"] == "operation":
                return (
                    [
                        {
                            "date": r["Date"],
                            "event": "operation",
                            "id": r["id"],
                            "comments": "repair event",
                            "name": "Repair",
                            "failure_id": "ofw.001",
                            "shutdown": True,
                            "shut_fix": "fix",
                            "loc": 1,
                        }
                    ],
                    dict_locations,
                )
            return ([], dict_locations)

        mock_logs_corr.side_effect = fake_logs_corrective_locations

        # shut -> power_farm 5/10 => 50%
        def fake_shut(*args, **kwargs):
            G = args[2]
            return G, 5.0

        mock_shut.side_effect = fake_shut

        # fix -> power_farm 10/10 => 100%
        def fake_fix(*args, **kwargs):
            G = args[1]
            return G, 10.0

        mock_fix.side_effect = fake_fix

        df = layout_percentage.return_percentage(
            log_events=self.log_events.copy(),
            prefix_list=["ofw", "oce"],
            operations_corrective_stat=DUMMY_OPERATIONS_STATS,
            G=self.G,
            shut_attribute="wtg_shutdown_dict",
            start_year=2025,
            start_month=1,
            n_lifetime=1,
            n_devices=10,
            tech="wind",
            find_element_class=None,
        )

        df_corr = df[df["Event"].isin(["failure", "operation"])].sort_values("Date")
        self.assertEqual(len(df_corr), 2)

        perc_list = df_corr["Perc_availability"].tolist()
        self.assertEqual(perc_list[0], 50.0)
        self.assertEqual(perc_list[1], 100.0)

    @patch("oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.fix_percentage_markers_dates",
           side_effect=lambda df: df)
    @patch("oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.add_markers_month_year",
           side_effect=lambda df, df_extra: pd.concat([df, df_extra], ignore_index=True))
    @patch("oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.find_highest_power_node",
           return_value="device")
    @patch("oriom.core.functions.layout_power.layout_percentage.logs_corrective_locations")
    def test_unknown_shut_fix_raises_value_error(
        self,
        mock_logs_corr,
        _mock_find_highest,
        _mock_add_markers,
        _mock_fix_markers,
    ):
        """
        If events include an unknown shut_fix value, return_percentage raises ValueError.
        """
        def fake_logs_corrective_locations(r, op_corr_excluding_tow, shut_attribute, find_element_class, dict_locations, op_corr_tow={}, op_add_tow={}):

            return (
                [
                    {
                        "date": r["Date"],
                        "event": "failure",
                        "id": r["id"],
                        "comments": "broken flag",
                        "name": "WTG Failure",
                        "failure_id": r["id"],
                        "level": "device",
                        "shutdown": True,
                        "shut_fix": "unknown",
                        "loc": 1,
                    }
                ],
                dict_locations,
            )

        mock_logs_corr.side_effect = fake_logs_corrective_locations

        with self.assertRaises(ValueError):
            layout_percentage.return_percentage(
                log_events=self.log_events.copy(),
                prefix_list=["ofw", "oce"],
                operations_corrective_stat=DUMMY_OPERATIONS_STATS,
                G=self.G,
                shut_attribute="wtg_shutdown_dict",
                start_year=2025,
                start_month=1,
                n_lifetime=1,
                n_devices=10,
                tech="wind",
                find_element_class=None,
            )


class TestReturnPercentagePV(unittest.TestCase):
    """Tests for PV-specific string shutdown logic in return_percentage."""

    def setUp(self):
        # Two PV failures on the same inverter loc=1
        self.log_events = pd.DataFrame(
            {
                "id": ["opv.001", "opv.002"],
                "event": ["failure", "failure"],
                "d_trigger": [
                    datetime(2025, 6, 1, 10, 0, 0),
                    datetime(2025, 6, 2, 10, 0, 0),
                ],
            }
        )

        self.G_pv = nx.DiGraph()
        self.G_pv.add_node(0, level="SHORE", power=0)
        self.G_pv.add_node(1, level="inverter", power=10.0)

    @patch("oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.fix_percentage_markers_dates",
           side_effect=lambda df: df)
    @patch("oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.add_markers_month_year",
           side_effect=lambda df, df_extra: pd.concat([df, df_extra], ignore_index=True))
    @patch("oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.find_highest_power_node",
           return_value="inverter")
    @patch("oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.string_location",
           side_effect=lambda failed_strings, string_inverter: sorted(list(string_inverter - failed_strings))[0])
    @patch("oriom.core.functions.layout_power.layout_percentage.logs_corrective_locations")
    @patch("oriom.core.functions.layout_power.layout_percentage.shut")
    def test_pv_second_device_failure_triggers_rename_when_max_reached(
        self,
        mock_shut,
        mock_logs_corr,
        _mock_string_location,
        _mock_find_highest,
        _mock_add_markers,
        _mock_fix_markers,
    ):
        """
        PV device failures with shutdown=True increment per-string counters.
        When max_failure_module is reached, the internal logic closes a string.
        This test checks:
          - availability values are produced
          - code path for PV update_string_PV_shutdown is exercised (via string_location patch)
        """
        def fake_logs_corrective_locations(r, op_corr_excluding_tow, shut_attribute, find_element_class, dict_locations, op_corr_tow={}, op_add_tow={}):
            return (
                [
                    {
                        "date": r["Date"],
                        "event": "failure",
                        "id": r["id"],
                        "comments": "PV device failure",
                        "name": "opv_fail_device",  # contains "device"
                        "failure_id": r["id"],
                        "level": "device",
                        "shutdown": True,
                        "shut_fix": "shut",
                        "loc": 1,
                    }
                ],
                dict_locations,
            )

        mock_logs_corr.side_effect = fake_logs_corrective_locations

        # Always return same farm power -> deterministic availability
        def fake_shut(*args, **kwargs):
            G = args[2]
            return G, 9.0  # 9/10 => 90%

        mock_shut.side_effect = fake_shut

        df = layout_percentage.return_percentage(
            log_events=self.log_events.copy(),
            prefix_list=["opv", "oce"],
            operations_corrective_stat=DUMMY_OPERATIONS_STATS,
            G=self.G_pv,
            shut_attribute="pv_shutdown_dict",
            start_year=2025,
            start_month=1,
            n_lifetime=1,
            n_devices=10,
            tech="PV",
            find_element_class=None,
            n_strings_per_inv=1,
            n_pv_per_string=1,
            max_failure_module=2,
        )

        df_fail = df[df["Event"] == "failure"].sort_values("Date")
        self.assertEqual(len(df_fail), 2)
        self.assertTrue((df_fail["Perc_availability"] == 90.0).all())


if __name__ == "__main__":
    unittest.main(verbosity=2)
