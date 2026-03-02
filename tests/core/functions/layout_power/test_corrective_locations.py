# tests/test_logs_corrective_locations.py

import unittest
from datetime import datetime

import pandas as pd

from oriom.core.functions.layout_power import corrective_location as logs_mod


# ------------------------------------------------------------------
# Dummy domain objects
# ------------------------------------------------------------------

class DummyFailure:
    def __init__(self, level_failure="device", name="FailureName"):
        self.level_failure = level_failure
        self.name = name
        self.id = name


class DummyOpClass:
    def __init__(self, name="OpName", tow_to_port=False, string_disconnection=False, failures = []):
        self.name = name
        self.id = name
        self.tow_to_port = tow_to_port
        self.string_disconnection = string_disconnection
        self.failures = failures

class DummyOperation:
    def __init__(self, op_class, shutdown_dict, shutdown_attr_name):
        self.op_class = op_class
        self.id = op_class.name
        setattr(self, shutdown_attr_name, shutdown_dict)


class DummyFindElementClass:
    """Minimal finder to satisfy logs_corrective_locations dependencies."""

    def __init__(self, failures=None, operations=None):
        self._failures = failures or {}
        self._operations = operations or {}

    def find_failure_from_id(self, failure_id):
        return self._failures[failure_id]

    def find_operation_stats(self, operation_id):
        return self._operations[operation_id]


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

class TestLogsCorrectiveLocationsFailure(unittest.TestCase):
    """Tests for the 'failure' branch of logs_corrective_locations."""

    def test_failure_creates_event_and_updates_dict_locations(self):
        event_row = pd.Series(
            {
                "event": "failure",
                "Date": datetime(2025, 1, 1, 12, 0, 0),
                "id": "ofw.001",
                "comments": "Failure comment",
                "shutdown": True,
            }
        )

        failure = DummyFailure(level_failure="device", name="FailureName")
        finder = DummyFindElementClass(failures={"ofw": failure})

        dict_locations_in = {}
        events, dict_locations_out = logs_mod.logs_corrective_locations(
            r=event_row,
            op_corr_excluding_tow=[],
            shut_attribute="ofw_shutdown_dict",
            find_element_class=finder,
            dict_locations=dict_locations_in,
            op_corr_tow={},
            op_add_tow={}
        )

        # One event dict is created
        self.assertEqual(len(events), 1)
        evt = events[0]

        self.assertEqual(evt["date"], event_row["Date"])
        self.assertEqual(evt["event"], "failure")
        self.assertEqual(evt["id"], event_row["id"])
        self.assertEqual(evt["comments"], event_row["comments"])
        self.assertEqual(evt["name"], "FailureName")
        self.assertEqual(evt["failure_id"], event_row["id"])
        self.assertEqual(evt["level"], "device")
        self.assertTrue(evt["shutdown"])
        self.assertEqual(evt["shut_fix"], "shut")
        self.assertIsNone(evt["loc"])

        # dict_locations updated with failure id mapped to None (location decided later)
        self.assertIn(event_row["id"], dict_locations_out)
        self.assertIsNone(dict_locations_out[event_row["id"]])

    def test_failure_shutdown_defaults_to_false_when_missing(self):
        event_row = pd.Series(
            {
                "event": "failure",
                "Date": datetime(2025, 1, 1, 12, 0, 0),
                "id": "ofw.001",
                "comments": "Failure comment",
                # "shutdown" missing on purpose
            }
        )

        failure = DummyFailure(level_failure="device", name="FailureName")
        finder = DummyFindElementClass(failures={"ofw": failure})

        events, _ = logs_mod.logs_corrective_locations(
            r=event_row,
            op_corr_excluding_tow=[],
            shut_attribute="ofw_shutdown_dict",
            find_element_class=finder,
            dict_locations={},
            op_corr_tow={},
            op_add_tow={}
        )

        self.assertEqual(len(events), 1)
        self.assertFalse(events[0]["shutdown"])


class TestLogsCorrectiveLocationsTow(unittest.TestCase):
    """Tests for the 'tow' branch of logs_corrective_locations."""

    def test_tow_removal_creates_shutdown_event_at_transit_ts(self):
        dict_locations = {"ofw.001": ("any_previous_loc",)}

        event_row = pd.Series(
            {
                "event": "tow",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "ofw_removal_001",
                "comments": "tow ofw.001",
                "d_end_transit_ts": datetime(2025, 1, 2, 0, 0, 0),
            }
        )

        events, dict_out = logs_mod.logs_corrective_locations(
            r=event_row,
            op_corr_excluding_tow=[],
            shut_attribute="ofw_shutdown_dict",
            find_element_class=None,
            dict_locations=dict_locations,
            op_corr_tow={}, 
            op_add_tow={}
        )

        self.assertEqual(len(events), 1)
        evt = events[0]

        self.assertEqual(evt["date"], event_row["d_end_transit_ts"])
        self.assertEqual(evt["event"], "tow")
        self.assertEqual(evt["id"], event_row["id"])
        self.assertEqual(evt["comments"], event_row["comments"])
        self.assertEqual(evt["name"], event_row["id"])
        self.assertEqual(evt["failure_id"], "ofw.001")
        self.assertTrue(evt["shutdown"])
        self.assertEqual(evt["shut_fix"], "shut")
        self.assertIsNone(evt["loc"])

        # dict_locations is not modified for tow
        self.assertIs(dict_out, dict_locations)

    def test_tow_redeploy_creates_fix_event_at_end_dur_net_site(self):
        dict_locations = {"ofw.001": ("any_previous_loc",)}

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
            op_corr_excluding_tow=[],
            shut_attribute="ofw_shutdown_dict",
            find_element_class=None,
            dict_locations=dict_locations,
            op_corr_tow={}, 
            op_add_tow={}
        )

        self.assertEqual(len(events), 1)
        evt = events[0]

        self.assertEqual(evt["date"], event_row["d_end_dur_net_site"])
        self.assertEqual(evt["event"], "tow")
        self.assertEqual(evt["failure_id"], "ofw.001")
        self.assertFalse(evt["shutdown"])
        self.assertEqual(evt["shut_fix"], "fix")
        self.assertIsNone(evt["loc"])

    def test_tow_without_matching_failure_raises_value_error(self):
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
                op_corr_excluding_tow=[],
                shut_attribute="ofw_shutdown_dict",
                find_element_class=None,
                dict_locations={},
                op_corr_tow={},
                op_add_tow={}
            )


class TestLogsCorrectiveLocationsOperation(unittest.TestCase):
    """Tests for the 'operation' branch (excluding tow) of logs_corrective_locations."""

    def test_operation_with_non_string_comments_raises_type_error(self):
        event_row = pd.Series(
            {
                "event": "operation",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "op_corr_001",
                "comments": 123,  # invalid type
                "d_end_transit_ts": datetime(2025, 1, 2, 0, 0, 0),
                "d_end_dur_net_site": datetime(2025, 1, 3, 0, 0, 0),
            }
        )

        with self.assertRaises(TypeError):
            logs_mod.logs_corrective_locations(
                r=event_row,
                op_corr_excluding_tow=["op_corr_001"],
                shut_attribute="ofw_shutdown_dict",
                find_element_class=DummyFindElementClass(),
                dict_locations={"ofw.001": None},
                op_corr_tow={},
                op_add_tow={}
            )

    def test_operation_without_matching_failure_raises_value_error(self):
        event_row = pd.Series(
            {
                "event": "operation",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "op_corr_001",
                "comments": "op:  ofw.999",  # comments[5:] -> "ofw.999"
                "d_end_transit_ts": datetime(2025, 1, 2, 0, 0, 0),
                "d_end_dur_net_site": datetime(2025, 1, 3, 0, 0, 0),
            }
        )

        operation = DummyOperation(
            op_class=DummyOpClass(name="OperationName", tow_to_port=False),
            shutdown_dict={},
            shutdown_attr_name="ofw_shutdown_dict",
        )
        finder = DummyFindElementClass(operations={"op_corr_001": operation})

        with self.assertRaises(ValueError):
            logs_mod.logs_corrective_locations(
                r=event_row,
                op_corr_excluding_tow=["op_corr_001"],
                shut_attribute="ofw_shutdown_dict",
                find_element_class=finder,
                dict_locations={},  # missing "ofw.999"
                op_corr_tow={},
                op_add_tow={}
            )

    def test_operation_no_monthly_shutdown_adds_only_final_event_fix(self):
        failure_id = "ofw.001"
        comments = f"op:  {failure_id}"  # comments[5:] -> "ofw.001"

        event_row = pd.Series(
            {
                "event": "operation",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "op_corr_001",
                "comments": comments,
                "d_end_transit_ts": datetime(2025, 1, 5, 0, 0, 0),
                "d_end_dur_net_site": datetime(2025, 1, 6, 0, 0, 0),
            }
        )

        operation = DummyOperation(
            op_class=DummyOpClass(name="OperationName", tow_to_port=False),
            shutdown_dict={},  # month not present => treated as 0
            shutdown_attr_name="ofw_shutdown_dict",
        )
        finder = DummyFindElementClass(operations={"op_corr_001": operation})

        events, _ = logs_mod.logs_corrective_locations(
            r=event_row,
            op_corr_excluding_tow=["op_corr_001"],
            shut_attribute="ofw_shutdown_dict",
            find_element_class=finder,
            dict_locations={failure_id: None},
            op_corr_tow={},
            op_add_tow={}
        )

        self.assertEqual(len(events), 1)
        evt = events[0]

        self.assertEqual(evt["date"], event_row["d_end_dur_net_site"])
        self.assertEqual(evt["event"], "operation")
        self.assertEqual(evt["id"], event_row["id"])
        self.assertEqual(evt["name"], "OperationName")
        self.assertEqual(evt["failure_id"], failure_id)
        self.assertTrue(evt["shutdown"])
        self.assertEqual(evt["shut_fix"], "fix")  # tow_to_port=False
        self.assertIsNone(evt["loc"])

    def test_operation_with_monthly_shutdown_adds_two_events_and_shut_final_when_tow_to_port(self):
        failure_id = "ofw.001"
        comments = f"op:  {failure_id}"  # comments[5:] -> "ofw.001"

        event_row = pd.Series(
            {
                "event": "operation",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "op_corr_002",
                "comments": comments,
                "d_end_transit_ts": datetime(2025, 1, 10, 0, 0, 0),
                "d_end_dur_net_site": datetime(2025, 1, 11, 0, 0, 0),
            }
        )

        operation = DummyOperation(
            op_class=DummyOpClass(name="PortOp", tow_to_port=True),
            shutdown_dict={"1": 5.0},  # January -> month "1" => non-zero => extra event
            shutdown_attr_name="ofw_shutdown_dict",
        )
        finder = DummyFindElementClass(operations={"op_corr_002": operation})

        events, _ = logs_mod.logs_corrective_locations(
            r=event_row,
            op_corr_excluding_tow=["op_corr_002"],
            shut_attribute="ofw_shutdown_dict",
            find_element_class=finder,
            dict_locations={failure_id: None},
            op_corr_tow={},
            op_add_tow={}
        )

        self.assertEqual(len(events), 2)

        first_evt = events[0]
        last_evt = events[1]

        # First event: pre-repair shutdown at transit_ts
        self.assertEqual(first_evt["date"], event_row["d_end_transit_ts"])
        self.assertEqual(first_evt["shut_fix"], "shut")
        self.assertTrue(first_evt["shutdown"])

        # Last event: final state at transit_tp (tow_to_port=True => "shut")
        self.assertEqual(last_evt["date"], event_row["d_end_dur_net_site"])
        self.assertEqual(last_evt["shut_fix"], "shut")
        self.assertTrue(last_evt["shutdown"])

    def test_operation_no_monthly_shutdown_add_op_tow(self):
        failure_id = "ofw.001"
        comments = f"op:  {failure_id}"  # comments[5:] -> "ofw.001"

        event_row = pd.Series(
            {
                "event": "operation",
                "Date": datetime(2025, 1, 1, 0, 0, 0),
                "id": "OperationNameAdd",
                "comments": comments,
                "d_end_transit_ts": datetime(2025, 1, 5, 0, 0, 0),
                "d_end_dur_net_site": datetime(2025, 1, 6, 0, 0, 0),
            }
        )

        operation = DummyOperation(
            op_class=DummyOpClass(name="OperationName", tow_to_port=False, failures=[DummyFailure(level_failure="device", name="FailureName")]),
            shutdown_dict={},  # month not present => treated as 0
            shutdown_attr_name="ofw_shutdown_dict",
        )
        operation_tow = DummyOperation(
            op_class=DummyOpClass(name="OperationNameTow", tow_to_port=True, string_disconnection = True),
            shutdown_dict={},  # month not present => treated as 0
            shutdown_attr_name="ofw_shutdown_dict",
        )
        operation_add = DummyOperation(
            op_class=DummyOpClass(name="OperationNameAdd", tow_to_port=False, failures=[operation_tow.op_class]),
            shutdown_dict={"1":1},  # month not present => treated as 0
            shutdown_attr_name="ofw_shutdown_dict",
        )
        finder = DummyFindElementClass(operations={"op_corr_001": operation, "OperationNameTow": operation_tow, "OperationNameAdd": operation_add})

        events, _ = logs_mod.logs_corrective_locations(
            r=event_row,
            op_corr_excluding_tow=["op_corr_001", "OperationNameAdd"],
            shut_attribute="ofw_shutdown_dict",
            find_element_class=finder,
            dict_locations={failure_id: None},
            op_corr_tow={operation_tow.id: operation_tow},
            op_add_tow={operation_add.id: operation_add}
        )

        self.assertEqual(len(events), 2)

        evt = events[0]

        self.assertEqual(evt["date"], datetime(2025, 1, 5, 0, 0))
        self.assertEqual(evt["event"], "operation")
        self.assertEqual(evt["id"], event_row["id"])
        self.assertEqual(evt["name"], "OperationNameAdd")
        self.assertEqual(evt["failure_id"], failure_id)
        self.assertTrue(evt["shutdown"])
        self.assertEqual(evt["shut_fix"], "shut")  # tow_to_port=False
        self.assertIsNone(evt["loc"])

        evt = events[1]

        self.assertEqual(evt["date"], event_row["d_end_dur_net_site"])
        self.assertEqual(evt["event"], "operation")
        self.assertEqual(evt["id"], event_row["id"])
        self.assertEqual(evt["name"], "OperationNameAdd")
        self.assertEqual(evt["failure_id"], failure_id)
        self.assertTrue(evt["shutdown"])
        self.assertEqual(evt["shut_fix"], "fix")  # tow_to_port=False
        self.assertIsNone(evt["loc"])
if __name__ == "__main__":
    unittest.main(verbosity=2)
