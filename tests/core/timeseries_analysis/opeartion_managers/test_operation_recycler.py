# test_operation_recycler

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import importlib.util

import pandas as pd

from logistic_tools.core.timeseries_analysis.operation_managers.operation_recycler import (
    recycle_other_oper_scheduler,
    recycle_major_other_oper_scheduler,
    compare_operations,
)

# --- check if module check_files is present otherwise skip that files---
try:
    check_files_spec = importlib.util.find_spec(
        "logistic_tools.core.functions.private.check_files"
    )
except ModuleNotFoundError:
    check_files_spec = None

skip_if_no_check_files = unittest.skipIf(
    check_files_spec is None,
    "check_files module not available, skipping related tests"
)

# --- helpers ---
def make_activity(duration, location, wtg_shutdown_dur):
    """Build a minimal activity object."""
    return SimpleNamespace(
        duration=float(duration),
        location=location,
        wtg_shutdown_dur=float(wtg_shutdown_dur),
    )


def make_operation(op_id, vessel1_id, activities, **extra_attrs):
    """Build a minimal operation object."""
    base = dict(id=op_id, vessel1_id=vessel1_id, activities=activities)
    base.update(extra_attrs)
    return SimpleNamespace(**base)


# --- TEST RECYCLE OTHER OPERATIONS ---
class TestRecycleOtherOperScheduler(unittest.TestCase):
    def test_first_insert_creates_new_group(self):
        minor_oper_dict = {}
        hash_to_key = {}
        attrs = ["a", "b"]

        op = make_operation("op1", "v1", [], a=10, b="X")

        result_id = recycle_other_oper_scheduler(
            minor_oper_dict=minor_oper_dict,
            hash_to_key=hash_to_key,
            operation=op,
            attribute_list=attrs,
        )

        self.assertEqual(result_id, "op1")
        self.assertIn("op1", minor_oper_dict)
        self.assertEqual(minor_oper_dict["op1"], [10, "X"])
        self.assertIn((10, "X"), hash_to_key)
        self.assertEqual(hash_to_key[(10, "X")], "op1")

    def test_second_equivalent_operation_returns_existing_id(self):
        minor_oper_dict = {"op1": [10, "X"]}
        hash_to_key = {(10, "X"): "op1"}
        attrs = ["a", "b"]

        op2 = make_operation("op2", "v2", [], a=10, b="X")

        result_id = recycle_other_oper_scheduler(
            minor_oper_dict=minor_oper_dict,
            hash_to_key=hash_to_key,
            operation=op2,
            attribute_list=attrs,
        )

        self.assertEqual(result_id, "op1")
        self.assertNotIn("op2", minor_oper_dict)
        self.assertEqual(hash_to_key[(10, "X")], "op1")

    def test_missing_attribute_is_treated_as_none(self):
        minor_oper_dict = {}
        hash_to_key = {}
        attrs = ["a", "missing_attr"]

        op = make_operation("opX", "v1", [], a=5)

        result_id = recycle_other_oper_scheduler(
            minor_oper_dict=minor_oper_dict,
            hash_to_key=hash_to_key,
            operation=op,
            attribute_list=attrs,
        )

        self.assertEqual(result_id, "opX")
        self.assertEqual(minor_oper_dict["opX"], [5, None])
        self.assertEqual(hash_to_key[(5, None)], "opX")


# --- TEST COMPARE OPERATIONS ---
class TestCompareOperations(unittest.TestCase):
    def test_equal_operations_return_true(self):
        acts1 = [make_activity(2.0, "port", 1.0), make_activity(3.0, "site", 0.0)]
        acts2 = [make_activity(2.0, "port", 1.0), make_activity(3.0, "site", 0.0)]
        op1 = make_operation("op1", "V1", acts1)
        op2 = make_operation("op2", "V1", acts2)

        self.assertTrue(compare_operations(op1, op2))

    def test_different_number_of_activities_returns_false(self):
        acts1 = [make_activity(2.0, "port", 1.0)]
        acts2 = [make_activity(2.0, "port", 1.0), make_activity(3.0, "site", 0.0)]
        op1 = make_operation("op1", "V1", acts1)
        op2 = make_operation("op2", "V1", acts2)

        self.assertFalse(compare_operations(op1, op2))

    def test_different_vessel1_id_returns_false(self):
        acts1 = [make_activity(2.0, "port", 1.0)]
        acts2 = [make_activity(2.0, "port", 1.0)]
        op1 = make_operation("op1", "V1", acts1)
        op2 = make_operation("op2", "V2", acts2)

        self.assertFalse(compare_operations(op1, op2))

    def test_different_activity_duration_returns_false(self):
        acts1 = [make_activity(2.0, "port", 1.0)]
        acts2 = [make_activity(3.0, "port", 1.0)]
        op1 = make_operation("op1", "V1", acts1)
        op2 = make_operation("op2", "V1", acts2)

        self.assertFalse(compare_operations(op1, op2))

    def test_different_activity_location_returns_false(self):
        acts1 = [make_activity(2.0, "port", 1.0)]
        acts2 = [make_activity(2.0, "site", 1.0)]
        op1 = make_operation("op1", "V1", acts1)
        op2 = make_operation("op2", "V1", acts2)

        self.assertFalse(compare_operations(op1, op2))

    def test_different_activity_wtg_shutdown_dur_returns_false(self):
        acts1 = [make_activity(2.0, "port", 1.0)]
        acts2 = [make_activity(2.0, "port", 0.0)]
        op1 = make_operation("op1", "V1", acts1)
        op2 = make_operation("op2", "V1", acts2)

        self.assertFalse(compare_operations(op1, op2))


# --- TEST RECYCLE MAJOR OTHER OPERATIONS ---
@skip_if_no_check_files
class TestRecycleMajorOtherOperScheduler(unittest.TestCase):
    def setUp(self):
        self.df_start = pd.DataFrame([[True, False], [False, True]], columns=["A0", "A1"])

        acts_prev = [make_activity(2.0, "port", 0.0), make_activity(3.0, "site", 1.0)]
        self.prev_oper = make_operation("OP_PREV", "V1", acts_prev, ts_data=SimpleNamespace(startability=self.df_start))

        acts_curr = [make_activity(2.0, "port", 0.0), make_activity(3.0, "site", 1.0)]
        self.curr_oper = make_operation("OP_CURR", "V1", acts_curr, ts_data=SimpleNamespace(startability=self.df_start))

        self.operations_list = [self.prev_oper, self.curr_oper]
        self.operation_dir = "/fake/path"

    @patch("logistic_tools.core.timeseries_analysis.operation_managers.operation_recycler.check_files.reuse_file_exist")
    def test_reuse_true_when_startability_and_activities_match(self, m_reuse_file):
        m_reuse_file.return_value = True
        result = recycle_major_other_oper_scheduler(
            operations=self.operations_list,
            actual_oper=self.curr_oper,
            df_startability=self.df_start,
            counter_op=1,
            operation_dir=self.operation_dir,
        )
        self.assertTrue(result)
        expected_prev_dir = os.path.join(self.operation_dir, self.prev_oper.id)
        expected_curr_dir = os.path.join(self.operation_dir, self.curr_oper.id)
        m_reuse_file.assert_called_once_with(
            op_dir=expected_curr_dir,
            file_name_schedule="operation_schedule.csv",
            operation=self.curr_oper,
            similar_inspection_id=self.prev_oper.id,
            op_dir_other=expected_prev_dir,
        )

    @patch("logistic_tools.core.timeseries_analysis.operation_managers.operation_recycler.check_files.reuse_file_exist")
    def test_reuse_false_when_startability_differs(self, m_reuse_file):
        m_reuse_file.return_value = True
        df_other = pd.DataFrame([[False, False], [False, False]], columns=["A0", "A1"])
        result = recycle_major_other_oper_scheduler(
            operations=self.operations_list,
            actual_oper=self.curr_oper,
            df_startability=df_other,
            counter_op=1,
            operation_dir=self.operation_dir,
        )
        self.assertFalse(result)
        m_reuse_file.assert_not_called()

    @patch("logistic_tools.core.timeseries_analysis.operation_managers.operation_recycler.check_files.reuse_file_exist")
    def test_reuse_false_when_compare_operations_is_false(self, m_reuse_file):
        m_reuse_file.return_value = True
        acts_curr = [make_activity(2.0, "port", 0.0), make_activity(3.0, "site", 1.0)]
        curr_diff = make_operation("OP_CURR2", "V_DIFF", acts_curr, ts_data=SimpleNamespace(startability=self.df_start))
        result = recycle_major_other_oper_scheduler(
            operations=self.operations_list,
            actual_oper=curr_diff,
            df_startability=self.df_start,
            counter_op=1,
            operation_dir=self.operation_dir,
        )
        self.assertFalse(result)
        m_reuse_file.assert_not_called()

    @patch("logistic_tools.core.timeseries_analysis.operation_managers.operation_recycler.check_files.reuse_file_exist")
    def test_reuse_false_when_reuse_file_exist_returns_false(self, m_reuse_file):
        m_reuse_file.return_value = False
        result = recycle_major_other_oper_scheduler(
            operations=self.operations_list,
            actual_oper=self.curr_oper,
            df_startability=self.df_start,
            counter_op=1,
            operation_dir=self.operation_dir,
        )
        self.assertFalse(result)
        m_reuse_file.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
