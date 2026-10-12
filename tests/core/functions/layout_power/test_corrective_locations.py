# tests/test_logs_corrective_locations.py

import unittest
from datetime import datetime

import networkx as nx
import pandas as pd

from oriom.core.functions.layout_power import corrective_location as logs_mod


# ------------------------------------------------------------------
# Dummy domain objects
# ------------------------------------------------------------------

class DummyFailure:
    """Minimal failure object."""

    def __init__(self, level_failure="device", name="FailureName"):
        self.level_failure = level_failure
        self.name = name
        self.id = name


class DummyOpClass:
    """Minimal operation class object."""

    def __init__(
        self,
        name="OperationName",
        tow_to_port=False,
        string_disconnection=False,
        failures=None,
    ):
        self.name = name
        self.id = name
        self.tow_to_port = tow_to_port
        self.string_disconnection = string_disconnection
        self.failures = failures or []


class DummyOperation:
    """Minimal operation stats object."""

    def __init__(self, op_class, shutdown_dict=None, shutdown_attr_name="ofw_shutdown_dict"):
        self.op_class = op_class
        self.id = op_class.name
        setattr(self, shutdown_attr_name, shutdown_dict or {})


class DummyFindElementClass:
    """Minimal finder used by logs_corrective_locations."""

    def __init__(self, failures=None, operations=None):
        self._failures = failures or {}
        self._operations = operations or {}

    def find_failure_from_id(self, failure_id):
        """Return a failure by id."""
        return self._failures[failure_id]

    def find_operation_stats(self, operation_id):
        """Return operation stats by id."""
        return self._operations[operation_id]


# ------------------------------------------------------------------
# Helper function tests
# ------------------------------------------------------------------

class TestChooseSpecLocString(unittest.TestCase):
    """Tests for choose_spec_loc_string."""

    def test_choose_spec_loc_string_returns_first_edge_after_substation_path(self):
        """The function should return the first downstream edge after the string root."""
        graph = nx.DiGraph()

        graph.add_node(0, level="hub")
        graph.add_node(1, level="substation")
        graph.add_node(2, level="device")
        graph.add_node(3, level="device")

        graph.add_edge(3, 2)
        graph.add_edge(2, 1)
        graph.add_edge(1, 0)

        result = logs_mod.choose_spec_loc_string(
            G=graph,
            start_node=3,
        )

        self.assertEqual(result, (2, 1))

    def test_choose_spec_loc_string_raises_when_substation_is_missing(self):
        """The function should raise when no substation is found on the path."""
        graph = nx.DiGraph()

        graph.add_node(0, level="hub")
        graph.add_node(1, level="device")
        graph.add_node(2, level="device")

        graph.add_edge(2, 1)
        graph.add_edge(1, 0)

        with self.assertRaises(AttributeError):
            logs_mod.choose_spec_loc_string(
                G=graph,
                start_node=2,
            )


class TestConditionFixEvaluation(unittest.TestCase):
    """Tests for condition_fix_evaluation."""

    def test_condition_fix_evaluation_returns_true_for_regular_operation(self):
        """A regular operation should create a fix event."""
        result = logs_mod.condition_fix_evaluation(
            op_add_tow={},
            r_id="operation_1",
        )

        self.assertTrue(result)

    def test_condition_fix_evaluation_returns_false_for_ttp_without_string_disconnection(self):
        """A TTP additional operation without string disconnection should not create a fix event."""
        result = logs_mod.condition_fix_evaluation(
            op_add_tow={
                "operation_1": {
                    "type": "TTP",
                    "string": False,
                }
            },
            r_id="operation_1",
        )

        self.assertFalse(result)

    def test_condition_fix_evaluation_returns_true_for_ttp_with_string_disconnection(self):
        """A TTP additional operation with string disconnection should create a fix event."""
        result = logs_mod.condition_fix_evaluation(
            op_add_tow={
                "operation_1": {
                    "type": "TTP",
                    "string": True,
                }
            },
            r_id="operation_1",
        )

        self.assertTrue(result)

    def test_condition_fix_evaluation_returns_true_for_non_ttp_additional_operation(self):
        """A non-TTP additional operation should create a fix event."""
        result = logs_mod.condition_fix_evaluation(
            op_add_tow={
                "operation_1": {
                    "type": "OTHER",
                    "string": False,
                }
            },
            r_id="operation_1",
        )

        self.assertTrue(result)


# ------------------------------------------------------------------
# logs_corrective_locations: failure branch
# ------------------------------------------------------------------

class TestLogsCorrectiveLocationsFailure(unittest.TestCase):
    """Tests for the failure branch of logs_corrective_locations."""

    def test_failure_creates_event_and_updates_dict_locations(self):
        """A failure row should create one shutdown event and initialise dict_locations."""
        event_row = pd.Series(
            {
                "event": "failure",
                "Date": datetime(2025, 1, 1, 12, 0, 0),
                "id": "ofw.001",
                "comments": "Failure comment",
                "shutdown": True,
            }
        )

        failure = DummyFailure(
            level_failure="device",
            name="FailureName",
        )

        finder = DummyFindElementClass(
            failures={
                "ofw": failure,
            }
        )

        dict_locations = {}

        events, dict_locations_out = logs_mod.logs_corrective_locations(
            r=event_row,
            shut_attribute="ofw_shutdown_dict",
            find_element_class=finder,
            dict_locations=dict_locations,
            op_add_tow={},
        )

        self.assertEqual(len(events), 1)

        evt = events[0]

        self.assertEqual(evt["date"], event_row["Date"])
        self.assertEqual(evt["event"], "failure")
        self.assertEqual(evt["id"], "ofw.001")
        self.assertEqual(evt["comments"], "Failure comment")
        self.assertEqual(evt["name"], "FailureName")
        self.assertEqual(evt["failure_id"], "ofw.001")
        self.assertEqual(evt["level"], "device")
        self.assertTrue(evt["shutdown"])
        self.assertEqual(evt["shut_fix"], "shut")
        self.assertIsNone(evt["loc"])

        self.assertIs(dict_locations_out, dict_locations)
        self.assertIn("ofw.001", dict_locations_out)
        self.assertIsNone(dict_locations_out["ofw.001"])

    def test_failure_shutdown_defaults_to_false_when_missing(self):
        """If shutdown is missing, the failure event should default to False."""
        event_row = pd.Series(
            {
                "event": "failure",
                "Date": datetime(2025, 1, 1, 12, 0, 0),
                "id": "ofw.001",
                "comments": "Failure comment",
            }
        )

        failure = DummyFailure(
            level_failure="device",
            name="FailureName",
        )

        finder = DummyFindElementClass(
            failures={
                "ofw": failure,
            }
        )

        events, _ = logs_mod.logs_corrective_locations(
            r=event_row,
            shut_attribute="ofw_shutdown_dict",
            find_element_class=finder,
            dict_locations={},
            op_add_tow={},
        )

        self.assertEqual(len(events), 1)
        self.assertFalse(events[0]["shutdown"])


# ------------------------------------------------------------------
# logs_corrective_locations: tow branch
# ------------------------------------------------------------------

class TestLogsCorrectiveLocationsTow(unittest.TestCase):
    """Tests for the tow branch of logs_corrective_locations."""

    def test_tow_removal_creates_shutdown_event_at_transit_ts(self):
        """A tow removal row should create a shut event at d_end_transit_ts."""
        dict_locations = {
            "ofw.001": None,
        }

        event_row = pd.Series(
            {
                "event": "tow",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "ofw_removal_001",
                "comments": "tow ofw.001",
                "d_end_transit_ts": datetime(2025, 1, 2, 0, 0, 0),
            }
        )

        events, dict_locations_out = logs_mod.logs_corrective_locations(
            r=event_row,
            shut_attribute="ofw_shutdown_dict",
            find_element_class=None,
            dict_locations=dict_locations,
            op_add_tow={},
        )

        self.assertEqual(len(events), 1)

        evt = events[0]

        self.assertEqual(evt["date"], event_row["d_end_transit_ts"])
        self.assertEqual(evt["event"], "tow")
        self.assertEqual(evt["id"], "ofw_removal_001")
        self.assertEqual(evt["comments"], "tow ofw.001")
        self.assertEqual(evt["name"], "ofw_removal_001")
        self.assertEqual(evt["failure_id"], "ofw.001")
        self.assertTrue(evt["shutdown"])
        self.assertEqual(evt["shut_fix"], "shut")
        self.assertIsNone(evt["loc"])

        self.assertIs(dict_locations_out, dict_locations)

    def test_tow_redeploy_creates_fix_event_at_end_dur_net_site(self):
        """A tow redeploy row should create a fix event at d_end_dur_net_site."""
        dict_locations = {
            "ofw.001": None,
        }

        event_row = pd.Series(
            {
                "event": "tow",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "ofw_redeploy_001",
                "comments": "tow ofw.001",
                "d_end_dur_net_site": datetime(2025, 1, 3, 0, 0, 0),
            }
        )

        events, _ = logs_mod.logs_corrective_locations(
            r=event_row,
            shut_attribute="ofw_shutdown_dict",
            find_element_class=None,
            dict_locations=dict_locations,
            op_add_tow={},
        )

        self.assertEqual(len(events), 1)

        evt = events[0]

        self.assertEqual(evt["date"], event_row["d_end_dur_net_site"])
        self.assertEqual(evt["event"], "tow")
        self.assertEqual(evt["id"], "ofw_redeploy_001")
        self.assertEqual(evt["failure_id"], "ofw.001")
        self.assertFalse(evt["shutdown"])
        self.assertEqual(evt["shut_fix"], "fix")
        self.assertIsNone(evt["loc"])

    def test_tow_without_matching_failure_raises_value_error(self):
        """A tow row should raise if its failure was not previously registered."""
        event_row = pd.Series(
            {
                "event": "tow",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "ofw_removal_001",
                "comments": "tow ofw.999",
                "d_end_transit_ts": datetime(2025, 1, 2, 0, 0, 0),
            }
        )

        with self.assertRaises(ValueError):
            logs_mod.logs_corrective_locations(
                r=event_row,
                shut_attribute="ofw_shutdown_dict",
                find_element_class=None,
                dict_locations={},
                op_add_tow={},
            )

    def test_tow_without_removal_or_redeploy_creates_no_event(self):
        """A tow row with no removal/redeploy marker should create no event."""
        dict_locations = {
            "ofw.001": None,
        }

        event_row = pd.Series(
            {
                "event": "tow",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "ofw_generic_001",
                "comments": "tow ofw.001",
                "d_end_transit_ts": datetime(2025, 1, 2, 0, 0, 0),
                "d_end_dur_net_site": datetime(2025, 1, 3, 0, 0, 0),
            }
        )

        events, dict_locations_out = logs_mod.logs_corrective_locations(
            r=event_row,
            shut_attribute="ofw_shutdown_dict",
            find_element_class=None,
            dict_locations=dict_locations,
            op_add_tow={},
        )

        self.assertEqual(events, [])
        self.assertIs(dict_locations_out, dict_locations)


# ------------------------------------------------------------------
# logs_corrective_locations: operation and recommissioning branches
# ------------------------------------------------------------------

class TestLogsCorrectiveLocationsOperation(unittest.TestCase):
    """Tests for the operation branch of logs_corrective_locations."""

    @staticmethod
    def _operation_comments(failure_id):
        """Create comments compatible with comments[5:]."""
        return f"op:  {failure_id}"

    def test_operation_with_non_string_comments_raises_type_error(self):
        """Operation comments must be a string."""
        event_row = pd.Series(
            {
                "event": "operation",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "operation_1",
                "comments": 123,
                "d_end_transit_ts": datetime(2025, 1, 2, 0, 0, 0),
                "d_end_dur_net_site": datetime(2025, 1, 3, 0, 0, 0),
            }
        )

        with self.assertRaises(TypeError):
            logs_mod.logs_corrective_locations(
                r=event_row,
                shut_attribute="ofw_shutdown_dict",
                find_element_class=DummyFindElementClass(),
                dict_locations={"ofw.001": None},
                op_add_tow={},
            )

    def test_operation_without_matching_failure_raises_value_error(self):
        """An operation should raise if its failure was not previously registered."""
        failure_id = "ofw.999"

        event_row = pd.Series(
            {
                "event": "operation",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "operation_1",
                "comments": self._operation_comments(failure_id),
                "d_end_transit_ts": datetime(2025, 1, 2, 0, 0, 0),
                "d_end_dur_net_site": datetime(2025, 1, 3, 0, 0, 0),
            }
        )

        operation = DummyOperation(
            op_class=DummyOpClass(
                name="OperationName",
                tow_to_port=False,
            ),
            shutdown_dict={},
            shutdown_attr_name="ofw_shutdown_dict",
        )

        finder = DummyFindElementClass(
            operations={
                "operation_1": operation,
            }
        )

        with self.assertRaises(ValueError):
            logs_mod.logs_corrective_locations(
                r=event_row,
                shut_attribute="ofw_shutdown_dict",
                find_element_class=finder,
                dict_locations={},
                op_add_tow={},
            )

    def test_tow_to_port_operation_returns_no_events(self):
        """Operations marked as tow_to_port should be ignored by this function."""
        failure_id = "ofw.001"

        event_row = pd.Series(
            {
                "event": "operation",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "operation_ttp",
                "comments": self._operation_comments(failure_id),
                "d_end_transit_ts": datetime(2025, 1, 2, 0, 0, 0),
                "d_end_dur_net_site": datetime(2025, 1, 3, 0, 0, 0),
            }
        )

        operation = DummyOperation(
            op_class=DummyOpClass(
                name="TowToPortOperation",
                tow_to_port=True,
            ),
            shutdown_dict={
                "1": 5.0,
            },
            shutdown_attr_name="ofw_shutdown_dict",
        )

        finder = DummyFindElementClass(
            operations={
                "operation_ttp": operation,
            }
        )

        events, dict_locations_out = logs_mod.logs_corrective_locations(
            r=event_row,
            shut_attribute="ofw_shutdown_dict",
            find_element_class=finder,
            dict_locations={failure_id: None},
            op_add_tow={},
        )

        self.assertEqual(events, [])
        self.assertEqual(dict_locations_out, {failure_id: None})

    def test_operation_no_monthly_shutdown_adds_only_final_fix_event(self):
        """Without monthly shutdown hours, a regular operation should add only the final fix event."""
        failure_id = "ofw.001"

        event_row = pd.Series(
            {
                "event": "operation",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "operation_1",
                "comments": self._operation_comments(failure_id),
                "d_end_transit_ts": datetime(2025, 1, 5, 0, 0, 0),
                "d_end_dur_net_site": datetime(2025, 1, 6, 0, 0, 0),
            }
        )

        operation = DummyOperation(
            op_class=DummyOpClass(
                name="OperationName",
                tow_to_port=False,
            ),
            shutdown_dict={},
            shutdown_attr_name="ofw_shutdown_dict",
        )

        finder = DummyFindElementClass(
            operations={
                "operation_1": operation,
            }
        )

        events, _ = logs_mod.logs_corrective_locations(
            r=event_row,
            shut_attribute="ofw_shutdown_dict",
            find_element_class=finder,
            dict_locations={failure_id: None},
            op_add_tow={},
        )

        self.assertEqual(len(events), 1)

        evt = events[0]

        self.assertEqual(evt["date"], event_row["d_end_dur_net_site"])
        self.assertEqual(evt["event"], "operation")
        self.assertEqual(evt["id"], "operation_1")
        self.assertEqual(evt["comments"], event_row["comments"])
        self.assertEqual(evt["name"], "OperationName")
        self.assertEqual(evt["failure_id"], failure_id)
        self.assertTrue(evt["shutdown"])
        self.assertEqual(evt["shut_fix"], "fix")
        self.assertIsNone(evt["loc"])

    def test_operation_with_monthly_shutdown_adds_shutdown_and_final_fix_events(self):
        """With monthly shutdown hours, a regular operation should add shut and fix events."""
        failure_id = "ofw.001"

        event_row = pd.Series(
            {
                "event": "operation",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "operation_1",
                "comments": self._operation_comments(failure_id),
                "d_end_transit_ts": datetime(2025, 1, 10, 0, 0, 0),
                "d_end_dur_net_site": datetime(2025, 1, 11, 0, 0, 0),
            }
        )

        operation = DummyOperation(
            op_class=DummyOpClass(
                name="OperationName",
                tow_to_port=False,
            ),
            shutdown_dict={
                "1": 5.0,
            },
            shutdown_attr_name="ofw_shutdown_dict",
        )

        finder = DummyFindElementClass(
            operations={
                "operation_1": operation,
            }
        )

        events, _ = logs_mod.logs_corrective_locations(
            r=event_row,
            shut_attribute="ofw_shutdown_dict",
            find_element_class=finder,
            dict_locations={failure_id: None},
            op_add_tow={},
        )

        self.assertEqual(len(events), 2)

        shut_evt = events[0]
        fix_evt = events[1]

        self.assertEqual(shut_evt["date"], event_row["d_end_transit_ts"])
        self.assertEqual(shut_evt["event"], "operation")
        self.assertEqual(shut_evt["shut_fix"], "shut")
        self.assertTrue(shut_evt["shutdown"])

        self.assertEqual(fix_evt["date"], event_row["d_end_dur_net_site"])
        self.assertEqual(fix_evt["event"], "operation")
        self.assertEqual(fix_evt["shut_fix"], "fix")
        self.assertTrue(fix_evt["shutdown"])

    def test_ttp_additional_operation_without_string_disconnection_adds_no_final_fix_event(self):
        """A TTP additional operation without string disconnection should not add the final fix event."""
        failure_id = "ofw.001"

        event_row = pd.Series(
            {
                "event": "operation",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "additional_operation",
                "comments": self._operation_comments(failure_id),
                "d_end_transit_ts": datetime(2025, 1, 5, 0, 0, 0),
                "d_end_dur_net_site": datetime(2025, 1, 6, 0, 0, 0),
            }
        )

        operation = DummyOperation(
            op_class=DummyOpClass(
                name="AdditionalOperation",
                tow_to_port=False,
            ),
            shutdown_dict={},
            shutdown_attr_name="ofw_shutdown_dict",
        )

        finder = DummyFindElementClass(
            operations={
                "additional_operation": operation,
            }
        )

        events, _ = logs_mod.logs_corrective_locations(
            r=event_row,
            shut_attribute="ofw_shutdown_dict",
            find_element_class=finder,
            dict_locations={failure_id: None},
            op_add_tow={
                "additional_operation": {
                    "type": "TTP",
                    "string": False,
                }
            },
        )

        self.assertEqual(events, [])

    def test_ttp_additional_operation_with_string_disconnection_adds_final_fix_event(self):
        """A TTP additional operation with string disconnection should add the final fix event."""
        failure_id = "ofw.001"

        event_row = pd.Series(
            {
                "event": "operation",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "additional_operation",
                "comments": self._operation_comments(failure_id),
                "d_end_transit_ts": datetime(2025, 1, 5, 0, 0, 0),
                "d_end_dur_net_site": datetime(2025, 1, 6, 0, 0, 0),
            }
        )

        operation = DummyOperation(
            op_class=DummyOpClass(
                name="AdditionalOperation",
                tow_to_port=False,
            ),
            shutdown_dict={},
            shutdown_attr_name="ofw_shutdown_dict",
        )

        finder = DummyFindElementClass(
            operations={
                "additional_operation": operation,
            }
        )

        events, _ = logs_mod.logs_corrective_locations(
            r=event_row,
            shut_attribute="ofw_shutdown_dict",
            find_element_class=finder,
            dict_locations={failure_id: None},
            op_add_tow={
                "additional_operation": {
                    "type": "TTP",
                    "string": True,
                }
            },
        )

        self.assertEqual(len(events), 1)

        evt = events[0]

        self.assertEqual(evt["date"], event_row["d_end_dur_net_site"])
        self.assertEqual(evt["event"], "operation")
        self.assertEqual(evt["id"], "additional_operation")
        self.assertEqual(evt["name"], "AdditionalOperation")
        self.assertEqual(evt["failure_id"], failure_id)
        self.assertEqual(evt["shut_fix"], "fix")

    def test_recommissioning_adds_only_final_recommissioning_event(self):
        """Recommissioning should skip the pre-repair shutdown event and add only its final event."""
        failure_id = "ofw.001"

        event_row = pd.Series(
            {
                "event": "recommissioning",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "recommissioning_1",
                "comments": self._operation_comments(failure_id),
                "d_end_transit_ts": datetime(2025, 1, 5, 0, 0, 0),
                "d_end_dur_net_site": datetime(2025, 1, 6, 0, 0, 0),
            }
        )

        operation = DummyOperation(
            op_class=DummyOpClass(
                name="RecommissioningOperation",
                tow_to_port=False,
            ),
            shutdown_dict={
                "1": 5.0,
            },
            shutdown_attr_name="ofw_shutdown_dict",
        )

        finder = DummyFindElementClass(
            operations={
                "recommissioning_1": operation,
            }
        )

        events, _ = logs_mod.logs_corrective_locations(
            r=event_row,
            shut_attribute="ofw_shutdown_dict",
            find_element_class=finder,
            dict_locations={failure_id: None},
            op_add_tow={},
        )

        self.assertEqual(len(events), 1)

        evt = events[0]

        self.assertEqual(evt["date"], event_row["d_end_dur_net_site"])
        self.assertEqual(evt["event"], "recommissioning")
        self.assertEqual(evt["id"], "recommissioning_1")
        self.assertEqual(evt["name"], "RecommissioningOperation")
        self.assertEqual(evt["failure_id"], failure_id)
        self.assertEqual(evt["shut_fix"], "fix")
        self.assertTrue(evt["shutdown"])
        self.assertIsNone(evt["loc"])


if __name__ == "__main__":
    unittest.main(verbosity=2)