# tests/core/functions/layout_power/test_layout_percentage_energy_manager_integration.py

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from unittest import skip

import networkx as nx
import pandas as pd

from oriom.core.functions.layout_power import layout_percentage


# =============================================================================
# Expected results
# =============================================================================

CASES = [
    (False, False, False, False),
    (False, False, True, False),
    (True, False, False, False),
    (True, True, False, False),
    (True, True, True, False),
    (True, False, True, True),
    (True, False, True, False),
    (True, False, False, True),
    (True, True, False, True),
    (True, True, True, True),
    
]


EXPECTED_AVAILABILITY_4_TURBINES_LOC_2 = {
    1: [100, 75, 100],
    2: [100, 50, 100],
    3: [100, 75, 75, 75, 75, 100],
    4: [100, 50, 75, 75, 75, 50, 100],
    5: [100, 50, 50, 50, 50, 50, 100],
    6: [100, 50, 50, 50, 50, 75, 100],
    7: [100, 50, 50, 50, 50, 100],
    8: [100, 75, 75, 75, 75, 75, 100],
    9: [100, 50, 75, 75, 75, 50, 75, 100],
    10: [100, 50, 50, 50, 50, 50, 75, 100],
}


EXPECTED_AVAILABILITY_6_TURBINES_LOC_3 = {
    1: [100, 83, 100],
    2: [100, 66, 100],
    3: [100, 83, 83, 83, 83, 100],
    4: [100, 50, 83, 83, 83, 50, 100],
    5: [100, 50, 66, 66, 66, 50, 100],
    6: [100, 66, 66, 66, 66, 83, 100],
    7: [100, 66, 66, 66, 66, 100],
    8: [100, 83, 83, 83, 83, 83, 100],
    9: [100, 50, 83, 83, 83, 50, 83, 100],
    10: [100, 50, 66, 66, 66, 50, 83, 100],
}


# =============================================================================
# Graph builders
# =============================================================================

def make_direct_device_graph(n_devices=1):
    """Create a direct device graph."""
    graph = nx.DiGraph()
    graph.add_node(0, level="shore", power=0)
    graph.add_node(1, level="substation", power=1)
    graph.add_edge(1, 0, visible=True)

    for node in range(2, n_devices + 2):
        graph.add_node(node, level="device", power=1)
        graph.add_edge(node, node - 1, visible=True)

    return graph


def make_array_cable_graph(n_devices=3):
    """Create a simple array/cable graph."""
    graph = nx.DiGraph()
    graph.add_node(0, level="substation", power=0)

    for node in range(1,n_devices+1):
        graph.add_node(node, level="device", power=1)

    graph.add_edge(1, 0, visible=True)
    graph.add_edge(2, 1, visible=True)
    graph.add_edge(3, 2, visible=True)

    return graph


def make_tow_graph(n_devices, devices_per_string):
    """
    Create a two-string offshore wind graph.

    Node convention:
        0 = shore
        1 = substation
        2..N = turbines

    Direction:
        device -> upstream node -> substation -> shore
    """
    graph = nx.DiGraph()
    graph.graph["tow_string_shutdown"] = False

    graph.add_node(0, level="shore", power=0)
    graph.add_node(1, level="substation", power=0)
    graph.add_edge(1, 0, visible=True)

    n_strings = 2
    first_device_node = 2

    for string_index in range(n_strings):
        previous_node = 1

        for device_index in range(devices_per_string):
            node = first_device_node + string_index * devices_per_string + device_index

            graph.add_node(node, level="device", power=1)
            graph.add_edge(node, previous_node, visible=True)

            previous_node = node

    actual_device_nodes = [
        node
        for node, data in graph.nodes(data=True)
        if data.get("level") == "device"
    ]

    assert len(actual_device_nodes) == n_devices

    return graph


# =============================================================================
# Test doubles
# =============================================================================

class TowToPortOpClass:
    """Minimal operation class for tow-to-port corrective operations."""

    def __init__(self, tow_to_port=True, op_tow_port=None, op_tow_site=None):
        self.tow_to_port = tow_to_port
        self.op_tow_port = op_tow_port
        self.op_tow_site = op_tow_site


class TowToPortCorrectiveStat:
    """Minimal corrective-stat operation object."""

    def __init__(self, op_id, op_tow_port, op_tow_site):
        self.id = op_id
        self.op_class = TowToPortOpClass(
            tow_to_port=True,
            op_tow_port=op_tow_port,
            op_tow_site=op_tow_site,
        )


class RegularCorrectiveStat:
    """Minimal non-TTP corrective operation object."""

    def __init__(self, op_id="regular_operation"):
        self.id = op_id
        self.op_class = SimpleNamespace(
            tow_to_port=False,
            op_tow_port=None,
            op_tow_site=None,
        )


class AdditionalTowOperation:
    """Minimal additional tow operation."""

    def __init__(self, op_id):
        self.id = op_id


class TowOperation:
    """Minimal tow operation returned by find_element_class.find_operation."""

    def __init__(
        self,
        op_id,
        addition_op_tow=None,
        string_disconnection=False,
        recommissioning_time=0,
    ):
        self.id = op_id
        self.addition_op_tow = addition_op_tow
        self.string_disconnection = string_disconnection
        self.recommissioning_time = recommissioning_time


class DummyFindElement:
    """Minimal finder object."""

    def __init__(self, operations=None):
        self.operations = operations or {}

    def find_operation(self, op_id):
        """Return an operation by id."""
        return self.operations[op_id]


# =============================================================================
# Test helpers
# =============================================================================

def make_event(
    date,
    event,
    event_id,
    shut_fix,
    loc,
    shutdown=True,
    name="event_name",
    failure_id="ofw_fail_001",
    level="device",
):
    """Create one abstract corrective event as returned by logs_corrective_locations."""
    return {
        "date": pd.Timestamp(date),
        "id": event_id,
        "event": event,
        "comments": f"{event} comments",
        "name": name,
        "failure_id": failure_id,
        "level": level,
        "shutdown": shutdown,
        "shut_fix": shut_fix,
        "loc": loc,
    }


def make_log_events_from_abstract_events(events):
    """Create the log_events dataframe consumed by return_percentage."""
    return pd.DataFrame(
        [
            {
                "id": event["id"],
                "event": event["event"],
                "d_trigger": event["date"],
            }
            for event in events
        ]
    )


def make_logs_corrective_locations_side_effect(events):
    """Return one abstract event per input log row."""
    events_by_key = {
        (event["id"], event["date"]): event
        for event in events
    }

    def fake_logs_corrective_locations(
        r,
        shut_attribute,
        find_element_class,
        dict_locations,
        op_add_tow,
    ):
        key = (
            r["id"],
            r["Date"],
        )

        return [
            events_by_key[key],
        ], dict_locations

    return fake_logs_corrective_locations


def round_availability_sequence(values):
    """Convert percentage values into the integer format used by the reference sequences."""
    return [
        int(value)
        for value in values
    ]


# =============================================================================
# Tests
# =============================================================================

class TestLayoutPercentageEnergyManagerIntegration(unittest.TestCase):
    """Integration tests for return_percentage energy-manager behaviour."""

    def run_return_percentage(
        self,
        graph,
        events,
        n_devices,
        operations_corrective_stat=None,
        find_element_class=None,
    ):
        """Run return_percentage with mocked event generation and monthly markers."""
        if operations_corrective_stat is None:
            operations_corrective_stat = [
                RegularCorrectiveStat(),
            ]

        if find_element_class is None:
            find_element_class = DummyFindElement()

        log_events = make_log_events_from_abstract_events(events)

        with patch(
            "oriom.core.functions.layout_power.layout_percentage.logs_corrective_locations",
            side_effect=make_logs_corrective_locations_side_effect(events),
        ), patch(
            "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.find_highest_power_node",
            return_value=["device"],
        ), patch(
            "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.add_markers_month_year",
            side_effect=lambda df, df_extra: df,
        ), patch(
            "oriom.core.functions.layout_power.layout_percentage.aux_layout_power_func.fix_percentage_markers_dates",
            side_effect=lambda df: df,
        ):
            result = layout_percentage.return_percentage(
                log_events=log_events,
                prefix_list=["ofw", "oce"],
                operations_corrective_stat=operations_corrective_stat,
                G=graph,
                shut_attribute="wtg_shutdown_dict",
                start_year=2025,
                start_month=1,
                n_lifetime=1,
                n_devices=n_devices,
                tech="wind",
                find_element_class=find_element_class,
            )

        return result, graph

    @staticmethod
    def availability_sequence(result):
        """Return the availability sequence including the initial 100% state."""
        corrective_rows = result[
            result["Event"].isin(
                [
                    "failure",
                    "operation",
                    "tow",
                    "recommissioning",
                ]
            )
        ].sort_values("Date")

        values = round_availability_sequence(
            corrective_rows["Perc_availability"].tolist()
        )

        return [
            *values,
        ]

    def test_device_shutdown_and_fix(self):
        """A device shutdown should reduce availability and a fix should restore it."""
        graph = make_direct_device_graph(n_devices=1)

        events = [
            make_event(
                date="2025-01-01 08:00",
                event="failure",
                event_id="ofw_fail_001",
                shut_fix="shut",
                loc=2,
                name="device failure",
                failure_id="ofw_fail_001",
            ),
            make_event(
                date="2025-01-02 08:00",
                event="operation",
                event_id="ofw_repair_001",
                shut_fix="shut",
                loc=2,
                name="device shut",
                failure_id="ofw_fail_001",
            ),
            make_event(
                date="2025-01-02 18:00",
                event="operation",
                event_id="ofw_repair_001",
                shut_fix="fix",
                loc=2,
                name="device repair",
                failure_id="ofw_fail_001",
            ),
        ]

        result, graph = self.run_return_percentage(
            graph=graph,
            events=events,
            n_devices=1,
        )

        actual = self.availability_sequence(result)

        self.assertEqual(
            actual,
            [
                0,
                0,
                100,
            ],
        )

        self.assertEqual(graph.nodes[2]["power"], 1)
        self.assertTrue(graph.edges[2, 1]["visible"])

    def test_cable_shutdown_and_fix(self):
        """An array/cable-level shutdown and fix should update availability."""
        graph = make_array_cable_graph(n_devices=3)

        events = [
            make_event(
                date="2025-01-01 08:00",
                event="failure",
                event_id="ofw_cable_fail_001",
                shut_fix="shut",
                loc=1,
                name="array cable failure",
                failure_id="ofw_cable_fail_001",
                level="device",
            ),
            make_event(
                date="2025-01-02 08:00",
                event="operation",
                event_id="ofw_cable_repair_001",
                shut_fix="fix",
                loc=1,
                name="array cable repair",
                failure_id="ofw_cable_fail_001",
                level="device",
            ),
        ]

        result, graph = self.run_return_percentage(
            graph=graph,
            events=events,
            n_devices=3,
        )

        actual = self.availability_sequence(result)

        self.assertEqual(
            actual,
            [
                66,
                100,
            ],
        )

    def make_tow_to_port_objects(
        self,
        has_add_operation=False,
        string_disconnection=False,
        recommissioning=False,
    ):
        """Create TTP operation objects and a finder."""
        tow_port_id = "ofw_removal_tow"
        tow_site_id = "ofw_redeploy_tow"

        addition_port = (
            AdditionalTowOperation("ofw_add_tow_port_001")
            if has_add_operation
            else None
        )

        addition_site = (
            AdditionalTowOperation("ofw_add_tow_site_001")
            if has_add_operation
            else None
        )

        tow_port = TowOperation(
            op_id=tow_port_id,
            addition_op_tow=addition_port,
            string_disconnection=string_disconnection,
            recommissioning_time=0,
        )

        tow_site = TowOperation(
            op_id=tow_site_id,
            addition_op_tow=addition_site,
            string_disconnection=string_disconnection,
            recommissioning_time=1 if recommissioning else 0,
        )

        corrective_stat = TowToPortCorrectiveStat(
            op_id="ofw_corrective_main",
            op_tow_port=tow_port_id,
            op_tow_site=tow_site_id,
        )

        find_element_class = DummyFindElement(
            operations={
                tow_port_id: tow_port,
                tow_site_id: tow_site,
            }
        )

        return corrective_stat, find_element_class

    @staticmethod
    def make_tow_events(
        has_add_operation=False,
        recommissioning=False,
        failure_loc=3,
        string_disconnection = False,
        shutdown = True
    ):
        """Create an abstract TTP event sequence."""
        events = [
            make_event(
                date="2025-03-01 08:00",
                event="failure",
                event_id="ofw_fail_001",
                shut_fix="shut",
                loc=failure_loc,
                name="device failure",
                failure_id="ofw_fail_001",
                shutdown= shutdown
            ),
        ]

        if has_add_operation:
            events.extend(
                [
                    make_event(
                        date="2025-03-02 08:00",
                        event="operation",
                        event_id="ofw_add_tow_port_001",
                        shut_fix="shut",
                        loc=failure_loc,
                        name="additional tow-to-port preparation",
                        failure_id="ofw_fail_001",
                    )
                ]
            )
            if string_disconnection:
                events.extend(
                    [
                        make_event(
                            date="2025-03-02 14:00",
                            event="operation",
                            event_id="ofw_add_tow_port_001",
                            shut_fix="fix",
                            loc=failure_loc,
                            name="additional tow-to-port preparation",
                            failure_id="ofw_fail_001",
                        ),
                ]
            )

        events.extend(
            [
                make_event(
                    date="2025-03-02 15:00",
                    event="tow",
                    event_id="ofw_removal_tow",
                    shut_fix="shut",
                    loc=failure_loc,
                    name="tow removal",
                    failure_id="ofw_fail_001",
                ),
                make_event(
                    date="2025-03-04 12:00",
                    event="tow",
                    event_id="ofw_redeploy_tow",
                    shut_fix="fix",
                    loc=failure_loc,
                    name="tow redeploy",
                    failure_id="ofw_fail_001",
                ),
            ]
        )

        if has_add_operation:
            events.extend(
                [
                    make_event(
                        date="2025-03-04 13:00",
                        event="operation",
                        event_id="ofw_add_tow_site_001",
                        shut_fix="shut",
                        loc=failure_loc,
                        name="additional tow-to-site preparation",
                        failure_id="ofw_fail_001",
                    ),
                    make_event(
                        date="2025-03-04 18:00",
                        event="operation",
                        event_id="ofw_add_tow_site_001",
                        shut_fix="fix",
                        loc=failure_loc,
                        name="additional tow-to-site preparation",
                        failure_id="ofw_fail_001",
                    ),
                ]
            )

        if recommissioning:
            events.append(
                make_event(
                    date="2025-03-04 19:00",
                    event="recommissioning",
                    event_id="ofw_add_tow_site_001",
                    shut_fix="fix",
                    loc=failure_loc,
                    name="recommissioning",
                    failure_id="ofw_fail_001",
                )
            )

        return events

    def run_tow_case(
        self,
        has_add_operation,
        string_disconnection,
        tow_string_shutdown,
        recommissioning,
        n_devices,
        devices_per_string,
        failure_loc,
    ):
        """Run one tow-to-port case through return_percentage."""
        graph = make_tow_graph(
            n_devices=n_devices,
            devices_per_string=devices_per_string,
        )
        graph.graph["tow_string_shutdown"] = tow_string_shutdown

        corrective_stat, find_element_class = self.make_tow_to_port_objects(
            has_add_operation=has_add_operation,
            string_disconnection=string_disconnection,
            recommissioning=recommissioning,
        )

        events = self.make_tow_events(
            has_add_operation=has_add_operation,
            recommissioning=recommissioning,
            failure_loc=failure_loc,
            string_disconnection=string_disconnection,
            shutdown=False,
        )

        result, graph = self.run_return_percentage(
            graph=graph,
            events=events,
            n_devices=n_devices,
            operations_corrective_stat=[
                corrective_stat,
            ],
            find_element_class=find_element_class,
        )

        return result, graph

    @skip
    def test_tow_to_port_cases_4_turbines_two_strings_failure_at_node_2(self):
        """
        Test the 10 TTP cases for 4 turbines split into two strings.

        Layout:
            string 1: node 2 -> node 3
            string 2: node 4 -> node 5

        Failure location:
            node 2, first turbine in the first string.
        """
        for case_index, case in enumerate(CASES, start=1):
            with self.subTest(case_index=case_index, case=case):
                (
                    has_add_operation,
                    string_disconnection,
                    tow_string_shutdown,
                    recommissioning,
                ) = case

                result, graph = self.run_tow_case(
                    has_add_operation=has_add_operation,
                    string_disconnection=string_disconnection,
                    tow_string_shutdown=tow_string_shutdown,
                    recommissioning=recommissioning,
                    n_devices=4,
                    devices_per_string=2,
                    failure_loc=2,
                )

                actual = self.availability_sequence(result)
                expected = EXPECTED_AVAILABILITY_4_TURBINES_LOC_2[case_index]

                self.assertEqual(
                    actual,
                    expected,
                    msg=(
                        "Unexpected availability sequence for 4 turbines. "
                        f"case_index={case_index}, "
                        f"case={case}, "
                        f"actual={actual}, "
                        f"expected={expected}"
                    ),
                )

                self.assertEqual(graph.nodes[3]["power"], 1)
                self.assertTrue(graph.edges[1, 0]["visible"])

                for node in range(2, 6):
                    self.assertEqual(graph.nodes[node]["power"], 1)

    def test_tow_to_port_cases_6_turbines_two_strings_failure_at_node_3(self):
        """
        Test the 10 TTP cases for 6 turbines split into two strings.

        Layout:
            string 1: node 2 -> node 3 -> node 4
            string 2: node 5 -> node 6 -> node 7

        Failure location:
            node 3, second turbine in the first string.
        """
        for case_index, case in enumerate(CASES, start=1):
            with self.subTest(case_index=case_index, case=case):
                (
                    has_add_operation,
                    string_disconnection,
                    tow_string_shutdown,
                    recommissioning,
                ) = case

                result, graph = self.run_tow_case(
                    has_add_operation=has_add_operation,
                    string_disconnection=string_disconnection,
                    tow_string_shutdown=tow_string_shutdown,
                    recommissioning=recommissioning,
                    n_devices=6,
                    devices_per_string=3,
                    failure_loc=3,
                )

                actual = self.availability_sequence(result)
                expected = EXPECTED_AVAILABILITY_6_TURBINES_LOC_3[case_index]
                
                self.assertEqual(
                    actual,
                    expected,
                    msg=(
                        "Unexpected availability sequence for 6 turbines. "
                        f"case_index={case_index},\n"
                        f"case={case}\n"
                        f"actual={actual}\n"
                        f"expected={expected}"
                    ),
                )

                self.assertEqual(graph.nodes[3]["power"], 1)
                self.assertTrue(graph.edges[1, 0]["visible"])

                for node in range(2, 8):
                    self.assertEqual(graph.nodes[node]["power"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)