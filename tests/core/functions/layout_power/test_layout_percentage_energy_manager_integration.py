#test_layout_percentage_energy_manager_integration

import unittest
from unittest.mock import patch
from datetime import datetime

import pandas as pd
import networkx as nx

from oriom.core.functions.layout_power import layout_percentage
import pytest

#pytest.skip("Test temporaneamente disabilitato", allow_module_level=True)
# ------------------------------------------------------------------
# Minimal test doubles
# ------------------------------------------------------------------

class DummyOpClass:
    def __init__(self, tow_to_port=False, op_tow_site=None, op_tow_port=None):
        self.tow_to_port = tow_to_port
        self.op_tow_site = op_tow_site
        self.op_tow_port = op_tow_port


class DummyOp:
    def __init__(self, op_id, tow_to_port=False):
        self.id = op_id
        self.op_class = DummyOpClass(tow_to_port=tow_to_port)

DUMMY_OPERATIONS_STATS = [DummyOp("op_corr_001", tow_to_port=False)]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def make_direct_device_graph(n_devices=10):
    """
    Graph:
        device_i -> shore

    Each device has power = 1.
    Total farm power = n_devices.
    """
    G = nx.DiGraph()
    G.add_node(0, level="SHORE", power=0)

    for i in range(1, n_devices + 1):
        G.add_node(i, level="device", power=1)
        G.add_edge(i, 0, visible=True)

    return G


def make_array_cable_graph(n_devices=3):
    """
    Graph:
        device_i -> hub -> shore

    Closing edge (100, 0) disconnects all devices from shore.
    """
    G = nx.DiGraph()
    G.add_node(0, level="SHORE", power=0)
    G.add_node(100, level="hub", power=0)

    for i in range(1, n_devices + 1):
        G.add_node(i, level="device", power=1)
        G.add_edge(i, 100, visible=True)

    G.add_edge(100, 0, visible=True)

    return G


# ------------------------------------------------------------------
# Integration tests
# ------------------------------------------------------------------

class TestReturnPercentageWithRealEnergyManager(unittest.TestCase):
    """
    Integration tests for:

        layout_percentage.return_percentage()
        +
        layout_energy_manager.shut()
        +
        layout_energy_manager.fix()

    These tests mock logs_corrective_locations only to control the generated
    events. shut() and fix() are NOT mocked.
    """

    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.fix_percentage_markers_dates",
        side_effect=lambda df: df,
    )
    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.add_markers_month_year",
        side_effect=lambda df, df_extra: df,
    )
    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.find_highest_power_node",
        return_value=["device"],
    )
    @patch("oriom.core.functions.layout_power.layout_percentage.logs_corrective_locations")
    def test_device_shutdown_false_shutdown_true_and_fix(
        self,
        mock_logs_corr,
        _mock_find_highest_power_node,
        _mock_add_markers_month_year,
        _mock_fix_percentage_markers_dates,
    ):
        """
        Non-PV device case with real shut/fix:

        1. failure with shutdown=False -> availability remains 100%
        2. failure with shutdown=True  -> one device power becomes 0 -> 90%
        3. operation fix              -> device power restored -> 100%
        """
        log_events = pd.DataFrame(
            {
                "id": ["ofw.001", "ofw.002", "ofw.003"],
                "event": ["failure", "failure", "operation"],
                "d_trigger": [
                    datetime(2025, 1, 10, 0, 0, 0),
                    datetime(2025, 1, 11, 0, 0, 0),
                    datetime(2025, 1, 20, 0, 0, 0),
                ],
            }
        )

        G = make_direct_device_graph(n_devices=10)

        def fake_logs_corrective_locations(
            r,
            op_corr_excluding_tow,
            shut_attribute,
            find_element_class,
            dict_locations,
            op_corr_tow={},
            op_add_tow={},
        ):
            if r["id"] == "ofw.001":
                return (
                    [
                        {
                            "date": r["Date"],
                            "event": "failure",
                            "id": r["id"],
                            "comments": "non-shutdown failure",
                            "name": "WTG minor failure",
                            "failure_id": r["id"],
                            "level": "device",
                            "shutdown": False,
                            "shut_fix": "shut",
                            "loc": 1,
                        }
                    ],
                    dict_locations,
                )

            if r["id"] == "ofw.002":
                return (
                    [
                        {
                            "date": r["Date"],
                            "event": "failure",
                            "id": r["id"],
                            "comments": "shutdown failure",
                            "name": "WTG major failure",
                            "failure_id": r["id"],
                            "level": "device",
                            "shutdown": True,
                            "shut_fix": "shut",
                            "loc": 2,
                        }
                    ],
                    dict_locations,
                )

            if r["id"] == "ofw.003":
                return (
                    [
                        {
                            "date": r["Date"],
                            "event": "operation",
                            "id": r["id"],
                            "comments": "repair operation",
                            "name": "WTG repair",
                            "failure_id": "ofw.002",
                            "level": "device",
                            "shutdown": True,
                            "shut_fix": "fix",
                            "loc": 2,
                        }
                    ],
                    dict_locations,
                )

            return ([], dict_locations)

        mock_logs_corr.side_effect = fake_logs_corrective_locations

        df = layout_percentage.return_percentage(
            log_events=log_events,
            prefix_list=["ofw", "oce"],
            operations_corrective_stat=DUMMY_OPERATIONS_STATS,
            G=G,
            shut_attribute="wtg_shutdown_dict",
            start_year=2025,
            start_month=1,
            n_lifetime=1,
            n_devices=10,
            tech="wind",
            find_element_class=None,
        )

        df_events = df[df["Event"].isin(["failure", "operation"])].sort_values("Date")

        self.assertEqual(
            df_events["Perc_availability"].tolist(),
            [100.0, 90.0, 100.0],
        )

        # Real fix() restored device 2 power.
        self.assertEqual(G.nodes[2]["power"], 1)

    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.fix_percentage_markers_dates",
        side_effect=lambda df: df,
    )
    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.add_markers_month_year",
        side_effect=lambda df, df_extra: df,
    )
    @patch(
        "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.find_highest_power_node",
        return_value=["device"],
    )
    @patch("oriom.core.functions.layout_power.layout_percentage.logs_corrective_locations")
    def test_array_cable_shutdown_and_fix(
        self,
        mock_logs_corr,
        _mock_find_highest_power_node,
        _mock_add_markers_month_year,
        _mock_fix_percentage_markers_dates,
    ):
        """
        Non-PV cable/edge case with real shut/fix:

        1. cable failure closes edge (100, 0) -> all devices disconnected -> 0%
        2. operation fix restores edge       -> all devices connected -> 100%
        """
        log_events = pd.DataFrame(
            {
                "id": ["ofw.001", "ofw.002"],
                "event": ["failure", "operation"],
                "d_trigger": [
                    datetime(2025, 2, 10, 0, 0, 0),
                    datetime(2025, 2, 20, 0, 0, 0),
                ],
            }
        )

        G = make_array_cable_graph(n_devices=3)

        def fake_logs_corrective_locations(
            r,
            op_corr_excluding_tow,
            shut_attribute,
            find_element_class,
            dict_locations,
            op_corr_tow={},
            op_add_tow={},
        ):
            if r["id"] == "ofw.001":
                return (
                    [
                        {
                            "date": r["Date"],
                            "event": "failure",
                            "id": r["id"],
                            "comments": "array cable failure",
                            "name": "array cable failure",
                            "failure_id": r["id"],
                            "level": "array_cable",
                            "shutdown": True,
                            "shut_fix": "shut",
                            "loc": (100, 0),
                        }
                    ],
                    dict_locations,
                )

            if r["id"] == "ofw.002":
                return (
                    [
                        {
                            "date": r["Date"],
                            "event": "operation",
                            "id": r["id"],
                            "comments": "array cable repair",
                            "name": "array cable repair",
                            "failure_id": "ofw.001",
                            "level": "array_cable",
                            "shutdown": True,
                            "shut_fix": "fix",
                            "loc": (100, 0),
                        }
                    ],
                    dict_locations,
                )

            return ([], dict_locations)

        mock_logs_corr.side_effect = fake_logs_corrective_locations

        df = layout_percentage.return_percentage(
            log_events=log_events,
            prefix_list=["ofw", "oce"],
            operations_corrective_stat=DUMMY_OPERATIONS_STATS,
            G=G,
            shut_attribute="wtg_shutdown_dict",
            start_year=2025,
            start_month=1,
            n_lifetime=1,
            n_devices=3,
            tech="wind",
            find_element_class=None,
        )

        df_events = df[df["Event"].isin(["failure", "operation"])].sort_values("Date")

        self.assertEqual(
            df_events["Perc_availability"].tolist(),
            [0.0, 100.0],
        )

        # Real fix() restored the edge visibility.
        self.assertTrue(G.edges[100, 0]["visible"])



# ------------------------------------------------------------------
# Tow-to-port integration test doubles
# ------------------------------------------------------------------

class TowToPortOpClass:
    def __init__(self, tow_to_port=True, op_tow_port=None, op_tow_site=None):
        self.tow_to_port = tow_to_port
        self.op_tow_port = op_tow_port
        self.op_tow_site = op_tow_site


class TowToPortCorrectiveStat:
    def __init__(self, op_id, op_tow_port, op_tow_site):
        self.id = op_id
        self.op_class = TowToPortOpClass(
            tow_to_port=True,
            op_tow_port=op_tow_port,
            op_tow_site=op_tow_site,
        )


class AdditionalTowOperation:
    def __init__(self, op_id):
        self.id = op_id


class TowOperation:
    def __init__(
        self,
        op_id,
        addition_op_tow=False,
        string_disconnection=False,
        recommissioning_time=0,
    ):
        self.id = op_id
        self.addition_op_tow = addition_op_tow
        self.string_disconnection = string_disconnection
        self.recommissioning_time = recommissioning_time


class DummyFindElement:
    def __init__(self, operations):
        self.operations = operations

    def find_operation(self, op_id):
        return self.operations[op_id]


# ------------------------------------------------------------------
# Tow-to-port helpers
# ------------------------------------------------------------------
from itertools import product

def make_wind_string_graph(tow_string_shutdown=False):
    """
    Graph:

        device 2 -> device 1 -> shore

    This is intentional.

    If device 1 is towed and edge (1, 0) is disconnected,
    device 2 also loses its path to shore. This makes the effect of
    tow_string_shutdown visible in the availability result.
    """
    G = nx.DiGraph()
    G.graph["tow_string_shutdown"] = tow_string_shutdown

    G.add_node(0, level="SHORE", power=0, name="SHORE", coords=(0, 0))
    G.add_node(1, level="device", power=1, name="D1", coords=(1, 0))
    G.add_node(2, level="device", power=1, name="D2", coords=(2, 0))
    G.add_node(3, level="device", power=1, name="D3", coords=(3, 0))
    G.add_node(4, level="device", power=1, name="D4", coords=(4, 0))

    # Edges
    G.add_edge(1, 0, visible=True, name="1-0")
    G.add_edge(2, 1, visible=True, name="2-1")
    G.add_edge(3, 2, visible=True, name="3-2")
    G.add_edge(4, 3, visible=True, name="4-3")

    return G


def make_tow_to_port_objects(
    has_add_operation,
    string_disconnection,
    recommissioning,
):
    tow_add_port_id = "ofw_add_tow_port_001"
    tow_add_site_id = "ofw_add_tow_site_001"
    tow_port_id = "ofw_redeploy_tow"
    tow_site_id = "ofw_removal_tow"

    add_op_port = AdditionalTowOperation(tow_add_port_id) if has_add_operation else None
    add_op_site = AdditionalTowOperation(tow_add_site_id) if has_add_operation else None

    tow_port = TowOperation(
        op_id=tow_port_id,
        addition_op_tow=add_op_port,
        string_disconnection=string_disconnection if string_disconnection else False,
        recommissioning_time=1 if recommissioning else 0,
    )

    tow_site = TowOperation(
        op_id=tow_site_id,
        addition_op_tow=add_op_site,
        string_disconnection=string_disconnection if string_disconnection else False,
        recommissioning_time=1 if recommissioning else 0,
    )

    operations_corrective_stat = [
        TowToPortCorrectiveStat(
            op_id="op_corr_001",
            op_tow_port=tow_port_id,
            op_tow_site=tow_site_id,
        )
    ]

    find_element_class = DummyFindElement(
        {
            tow_port_id: tow_port,
            tow_site_id: tow_site,
        }
    )

    return operations_corrective_stat, find_element_class


def make_tow_to_port_events(
    has_add_operation,
    recommission,
):
    failure_id = "ofw_fail_001"

    failure = {
        "date": datetime(2025, 3, 1, 8, 0, 0),
        "event": "failure",
        "id": failure_id,
        "comments": "failure before tow to port",
        "name": "WTG major failure",
        "failure_id": failure_id,
        "level": "device",
        "shutdown": True,
        "shut_fix": "shut",
        "loc": 2,
    }
    add_op_TTP = {
        "date": datetime(2025, 3, 2, 8, 0, 0),
        "event": "operation",
        "id": "ofw_add_tow_port_001",
        "comments": "additional tow/site operation starts",
        "name": "Tow site additional operation",
        "failure_id": failure_id,
        "level": "device",
        "shutdown": True,
        "shut_fix": "shut",
        "loc": 2,
    }
    add_op_TTS = {
        "date": datetime(2025, 3, 2, 14, 0, 0),
        "event": "operation",
        "id": "ofw_add_tow_port_001",
        "comments": "additional tow/site operation completed",
        "name": "Tow site additional operation",
        "failure_id": failure_id,
        "level": "device",
        "shutdown": True,
        "shut_fix": "fix",
        "loc": 2,
    }
    tow_port = {
        "date": datetime(2025, 3, 2, 15, 0, 0),
        "event": "tow",
        "id": "ofw_removal_tow",
        "comments": "tow to port starts",
        "name": "Tow to port",
        "failure_id": failure_id,
        "level": "device",
        "shutdown": True,
        "shut_fix": "shut",
        "loc": 2,
    }
    tow_site = {
        "date": datetime(2025, 3, 4, 12, 0, 0),
        "event": "tow",
        "id": "ofw_redeploy_tow",
        "comments": "tow to port completed",
        "name": "Tow to port",
        "failure_id": failure_id,
        "level": "device",
        "shutdown": True,
        "shut_fix": "fix",
        "loc": 2,
    }
    add_op_TTS_shut = {
        "date": datetime(2025, 3, 4, 13, 0, 0),
        "event": "operation",
        "id": "ofw_add_tow_site_001",
        "comments": "additional tow/site operation starts",
        "name": "Tow site additional operation",
        "failure_id": failure_id,
        "level": "device",
        "shutdown": True,
        "shut_fix": "shut",
        "loc": 2,
    }
    add_op_TTS_fix = {
        "date": datetime(2025, 3, 4, 18, 0, 0),
        "event": "operation",
        "id": "ofw_add_tow_site_001",
        "comments": "additional tow/site operation completed",
        "name": "Tow site additional operation",
        "failure_id": failure_id,
        "level": "device",
        "shutdown": True,
        "shut_fix": "fix",
        "loc": 2,
    }
    recommissioning = {
        "date": datetime(2025, 3, 4, 19, 0, 0),
        "event": "recommissioning",
        "id": "ofw_add_tow_site_001",
        "comments": "recommissioning completed",
        "name": "Recommissioning",
        "failure_id": failure_id,
        "level": "device",
        "shutdown": True,
        "shut_fix": "fix",
        "loc": 2,
    }

    # NORMAL TOW
    if not has_add_operation and not recommission:
        events = [failure, tow_port, tow_site]
    elif not has_add_operation and recommission:
        events = [failure, tow_port, tow_site, recommissioning]
    # TOW with additional operations
    elif has_add_operation and not recommission:
        events = [failure, add_op_TTP, add_op_TTS, tow_port, tow_site, add_op_TTS_shut, add_op_TTS_fix]
    # TOW with additional operations and recommission
    else:
        events = [failure, add_op_TTP, add_op_TTS, tow_port, tow_site, add_op_TTS_shut, add_op_TTS_fix, recommissioning]

    return events


# ------------------------------------------------------------------
# Tow-to-port integration tests
# ------------------------------------------------------------------

EXPECTED_AVAILABILITY = {
    # existing cases
    (False, False, False, False): [75.0, 75.0, 100.0],
    (False, False, True,  False): [75.0, 25.0, 100.0],
    (True,  False, False, False): [75.0, 75.0, 75.0, 75.0, 75.0, 75.0, 100.0],
    (True,  True,  False, False): [75.0, 0.0, 75.0, 75.0, 75.0, 0.0, 100.0],
    (True,  True,  True,  False): [75.0, 0.0, 25.0, 25.0, 25.0, 0.0, 100.0],
    (True,  False, True,  True ): [75.0, 75.0, 25.0, 25.0, 25.0, 25.0, 75.0, 100.0],
    (True,  True,  True,  True ): [75.0, 0.0, 25.0, 25.0, 25.0, 0.0, 75.0, 100.0],
    (True,  False, True,  False): [75.0, 75.0, 25.0, 25.0, 25.0, 25.0, 100.0],
    (True,  False, False, True ): [75.0, 75.0, 75.0, 75.0, 75.0, 75.0, 75.0, 100.0],
    (True,  True,  False, True ): [75.0, 0.0, 75.0, 75.0, 75.0, 0.0, 75.0, 100.0],
}

class TestReturnPercentageTowToPortIntegration(unittest.TestCase):
    """
    Integration tests for tow-to-port logic.

    Real functions tested:
        - return_percentage()
        - shut()
        - fix()

    Mocked only:
        - logs_corrective_locations()
        - monthly marker helpers
        - find_highest_power_node()
        - choose_spec_loc_string()
    """

    def run_tow_to_port_case(
        self,
        has_add_operation,
        string_disconnection,
        tow_string_shutdown,
        recommissioning,
    ):
        log_events = pd.DataFrame(
            {
                "id": ["ofw.seed"],
                "event": ["failure"],
                "d_trigger": [datetime(2025, 3, 1, 0, 0, 0)],
            }
        )

        G = make_wind_string_graph(
            tow_string_shutdown=tow_string_shutdown,
        )

        operations_corrective_stat, find_element_class = make_tow_to_port_objects(
            has_add_operation=has_add_operation,
            string_disconnection=string_disconnection,
            recommissioning=recommissioning,
        )

        generated_events = make_tow_to_port_events(
            has_add_operation=has_add_operation,
            recommission=recommissioning,
        )

        with patch(
            "oriom.core.functions.layout_power.layout_percentage.logs_corrective_locations",
            return_value=(generated_events, {}),
        ), patch(
            "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.find_highest_power_node",
            return_value=["device"],
        ), patch(
            "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.add_markers_month_year",
            side_effect=lambda df, df_extra: df,
        ), patch(
            "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.fix_percentage_markers_dates",
            side_effect=lambda df: df,
        ), patch(
            "oriom.core.functions.layout_power.layout_percentage.choose_spec_loc_string",
            side_effect=lambda G, loc: (1, 0) if isinstance(loc, int) else loc,
        ):
            df = layout_percentage.return_percentage(
                log_events=log_events,
                prefix_list=["ofw", "oce"],
                operations_corrective_stat=operations_corrective_stat,
                G=G,
                shut_attribute="wtg_shutdown_dict",
                start_year=2025,
                start_month=1,
                n_lifetime=1,
                n_devices=4,
                tech="wind",
                find_element_class=find_element_class,
            )

        return df, G

    def test_tow_to_port_all_combinations(self):
    
        for (
            has_add_operation,
            string_disconnection,
            tow_string_shutdown,
            recommissioning,
        ) in product(
            [False, True],
            [False, True],
            [False, True],
            [False, True],
        ):

            if not has_add_operation and string_disconnection or not has_add_operation and recommissioning:
                continue

            case_key = (
                has_add_operation,
                string_disconnection,
                tow_string_shutdown,
                recommissioning,
            )

            with self.subTest(case=case_key):

                df, G = self.run_tow_to_port_case(
                    has_add_operation=has_add_operation,
                    string_disconnection=string_disconnection,
                    tow_string_shutdown=tow_string_shutdown,
                    recommissioning=recommissioning,
                )

                self.assertEqual(
                    df["Perc_availability"].tolist(),
                    EXPECTED_AVAILABILITY[case_key],
                    msg=('\n',has_add_operation,string_disconnection,tow_string_shutdown,recommissioning),
                )


                self.assertEqual(G.nodes[1]["power"], 1)
                self.assertTrue(G.edges[1, 0]["visible"])


            
if __name__ == "__main__":
    unittest.main(verbosity=2)