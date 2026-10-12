# tests/core/functions/layout_power/test_layout_percentage.py

import unittest
from unittest.mock import Mock, patch
from datetime import datetime
from types import SimpleNamespace

import pandas as pd
import networkx as nx

from oriom.core.functions.layout_power import layout_percentage


# ------------------------------------------------------------------
# Minimal test doubles
# ------------------------------------------------------------------

class DummyOpClass:
    """Minimal operation-class object."""

    def __init__(
        self,
        tow_to_port=False,
        op_tow_port=None,
        op_tow_site=None,
    ):
        self.tow_to_port = tow_to_port
        self.op_tow_port = op_tow_port
        self.op_tow_site = op_tow_site


class DummyOp:
    """Minimal operation-stat object."""

    def __init__(
        self,
        op_id,
        tow_to_port=False,
        op_tow_port=None,
        op_tow_site=None,
    ):
        self.id = op_id
        self.op_class = DummyOpClass(
            tow_to_port=tow_to_port,
            op_tow_port=op_tow_port,
            op_tow_site=op_tow_site,
        )


DUMMY_OPERATIONS_STATS = [
    DummyOp(
        op_id="op_corr_001",
        tow_to_port=False,
    )
]


# ------------------------------------------------------------------
# Tests: empty log
# ------------------------------------------------------------------

class TestReturnPercentageEmptyLog(unittest.TestCase):
    """Tests for return_percentage when no events match the target technology."""

    def setUp(self):
        """Create a log that does not match the requested prefix."""
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

    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.find_highest_power_node",
        return_value=["device"],
    )
    def test_returns_empty_df_with_expected_columns(
        self,
        _mock_find_highest_power_node,
    ):
        """If no rows match the prefix list, return an empty dataframe with base columns."""
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
            [
                "Date",
                "Event",
                "id",
                "Comments",
                "Name",
                "Loc",
                "Shutdown",
                "Shut/Fix",
            ],
        )


# ------------------------------------------------------------------
# Tests: non-PV logic
# ------------------------------------------------------------------

class TestReturnPercentageNonPV(unittest.TestCase):
    """Tests for non-PV logic inside return_percentage."""

    def setUp(self):
        """Create a simple non-PV corrective sequence."""
        self.log_events = pd.DataFrame(
            {
                "id": [
                    "ofw.001",
                    "ofw.002",
                ],
                "event": [
                    "failure",
                    "operation",
                ],
                "d_trigger": [
                    datetime(2025, 1, 10, 0, 0, 0),
                    datetime(2025, 1, 20, 0, 0, 0),
                ],
            }
        )

        self.G = nx.DiGraph()
        self.G.add_node(0, level="SHORE", power=0)
        self.G.add_node(1, level="device", power=10.0)

    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.fix_percentage_markers_dates",
        side_effect=lambda df: df,
    )
    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.add_markers_month_year",
        side_effect=lambda df, df_extra: pd.concat(
            [
                df,
                df_extra,
            ],
            ignore_index=True,
        ),
    )
    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.find_highest_power_node",
        return_value=["device"],
    )
    @patch("oriom.core.functions.layout_power.layout_percentage.logs_corrective_locations")
    @patch("oriom.core.functions.layout_power.layout_percentage.shut")
    @patch("oriom.core.functions.layout_power.layout_percentage.fix")
    def test_non_pv_shut_and_fix_update_percentages(
        self,
        mock_fix,
        mock_shut,
        mock_logs_corr,
        _mock_find_highest_power_node,
        _mock_add_markers_month_year,
        _mock_fix_percentage_markers_dates,
    ):
        """
        Non-PV sequence:
        - failure shut event reduces availability to 50%
        - operation fix event restores availability to 100%
        """

        def fake_logs_corrective_locations(
            r,
            shut_attribute,
            find_element_class,
            dict_locations,
            op_add_tow,
        ):
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

            return (
                [],
                dict_locations,
            )

        mock_logs_corr.side_effect = fake_logs_corrective_locations

        def fake_shut(*args, **kwargs):
            graph = args[2]
            return graph, 5.0

        def fake_fix(*args, **kwargs):
            graph = args[1]
            return graph, 10.0

        mock_shut.side_effect = fake_shut
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

        self.assertEqual(
            df_corr["Perc_availability"].tolist(),
            [
                50.0,
                100.0,
            ],
        )

        mock_shut.assert_called_once()
        mock_fix.assert_called_once()

    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.fix_percentage_markers_dates",
        side_effect=lambda df: df,
    )
    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.add_markers_month_year",
        side_effect=lambda df, df_extra: pd.concat(
            [
                df,
                df_extra,
            ],
            ignore_index=True,
        ),
    )
    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.find_highest_power_node",
        return_value=["device"],
    )
    @patch("oriom.core.functions.layout_power.layout_percentage.logs_corrective_locations")
    def test_unknown_shut_fix_raises_value_error(
        self,
        mock_logs_corr,
        _mock_find_highest_power_node,
        _mock_add_markers_month_year,
        _mock_fix_percentage_markers_dates,
    ):
        """If an event has an unknown shut_fix value, return_percentage should raise ValueError."""

        def fake_logs_corrective_locations(
            r,
            shut_attribute,
            find_element_class,
            dict_locations,
            op_add_tow,
        ):
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
                log_events=self.log_events.iloc[[0]].copy(),
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

    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.fix_percentage_markers_dates",
        side_effect=lambda df: df,
    )
    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.add_markers_month_year",
        side_effect=lambda df, df_extra: pd.concat(
            [
                df,
                df_extra,
            ],
            ignore_index=True,
        ),
    )
    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.find_highest_power_node",
        return_value=["device"],
    )
    @patch("oriom.core.functions.layout_power.layout_percentage.logs_corrective_locations")
    def test_op_add_tow_is_built_from_tow_operations_and_passed_to_logs_corrective_locations(
        self,
        mock_logs_corr,
        _mock_find_highest_power_node,
        _mock_add_markers_month_year,
        _mock_fix_percentage_markers_dates,
    ):
        """return_percentage should build op_add_tow from TTP/TTS operation definitions."""
        captured_op_add_tow = []

        def fake_logs_corrective_locations(
            r,
            shut_attribute,
            find_element_class,
            dict_locations,
            op_add_tow,
        ):
            captured_op_add_tow.append(dict(op_add_tow))
            return (
                [],
                dict_locations,
            )

        mock_logs_corr.side_effect = fake_logs_corrective_locations

        add_ttp = SimpleNamespace(id="additional_ttp")
        add_tts = SimpleNamespace(id="additional_tts")

        tow_port_operation = SimpleNamespace(
            id="tow_port_operation",
            recommissioning_time=0,
            addition_op_tow=add_ttp,
            string_disconnection=True,
        )

        tow_site_operation = SimpleNamespace(
            id="tow_site_operation",
            recommissioning_time=3,
            addition_op_tow=add_tts,
            string_disconnection=False,
        )

        find_element = Mock()
        find_element.find_operation.side_effect = {
            "tow_port_id": tow_port_operation,
            "tow_site_id": tow_site_operation,
        }.__getitem__

        operations_corrective_stat = [
            DummyOp(
                op_id="main_corrective_operation",
                tow_to_port=True,
                op_tow_port="tow_port_id",
                op_tow_site="tow_site_id",
            )
        ]

        layout_percentage.return_percentage(
            log_events=self.log_events.iloc[[0]].copy(),
            prefix_list=["ofw", "oce"],
            operations_corrective_stat=operations_corrective_stat,
            G=self.G,
            shut_attribute="wtg_shutdown_dict",
            start_year=2025,
            start_month=1,
            n_lifetime=1,
            n_devices=10,
            tech="wind",
            find_element_class=find_element,
        )

        self.assertEqual(
            captured_op_add_tow[0],
            {
                "additional_ttp": {
                    "string": True,
                    "type": "TTP",
                },
                "additional_tts": {
                    "string": False,
                    "type": "TTS",
                },
            },
        )

        self.assertEqual(find_element.find_operation.call_count, 2)


# ------------------------------------------------------------------
# Tests: PV logic
# ------------------------------------------------------------------

class TestReturnPercentagePV(unittest.TestCase):
    """Tests for PV-specific logic inside return_percentage."""

    def setUp(self):
        """Create two PV failures on the same inverter."""
        self.log_events = pd.DataFrame(
            {
                "id": [
                    "opv.001",
                    "opv.002",
                ],
                "event": [
                    "failure",
                    "failure",
                ],
                "d_trigger": [
                    datetime(2025, 6, 1, 10, 0, 0),
                    datetime(2025, 6, 2, 10, 0, 0),
                ],
            }
        )

        self.G_pv = nx.DiGraph()
        self.G_pv.add_node(0, level="SHORE", power=0)
        self.G_pv.add_node(1, level="inverter", power=10.0)

    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.fix_percentage_markers_dates",
        side_effect=lambda df: df,
    )
    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.add_markers_month_year",
        side_effect=lambda df, df_extra: pd.concat(
            [
                df,
                df_extra,
            ],
            ignore_index=True,
        ),
    )
    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.find_highest_power_node",
        return_value=["inverter"],
    )
    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.string_location",
        side_effect=lambda failed_strings, string_inverter: sorted(
            list(string_inverter - failed_strings)
        )[0],
    )
    @patch("oriom.core.functions.layout_power.layout_percentage.logs_corrective_locations")
    @patch("oriom.core.functions.layout_power.layout_percentage.shut")
    def test_pv_device_failures_update_string_logic_and_availability(
        self,
        mock_shut,
        mock_logs_corr,
        mock_string_location,
        _mock_find_highest_power_node,
        _mock_add_markers_month_year,
        _mock_fix_percentage_markers_dates,
    ):
        """PV device failures should exercise string-level shutdown logic and produce availability."""
        def fake_logs_corrective_locations(
            r,
            shut_attribute,
            find_element_class,
            dict_locations,
            op_add_tow,
        ):
            return (
                [
                    {
                        "date": r["Date"],
                        "event": "failure",
                        "id": r["id"],
                        "comments": "PV device failure",
                        "name": "opv_fail_device",
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

        def fake_shut(*args, **kwargs):
            graph = args[2]
            return graph, 9.0

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

        self.assertEqual(mock_shut.call_count, 2)
        self.assertEqual(mock_string_location.call_count, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)