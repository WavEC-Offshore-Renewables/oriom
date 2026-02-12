# test_aux_functions.py

import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace

import pandas as pd

from logistic_tools.utils.aux_functions import (
    update_dict,
    save_file_csv,
    safe_getattr,
    convert_stringtime,
    log_event_convert_stringtime,
    take_attribute,
    create_run_folder_operation,
    safe_copy_df,
)


class TestAuxFunctions(unittest.TestCase):
    def test_update_dict_nested_merge(self):
        """update_dict must recursively merge nested mappings."""
        base = {"a": 1, "b": {"x": 10, "y": 20}, "c": 3}
        updates = {"b": {"y": 99, "z": 100}, "d": 4}

        result = update_dict(base, updates)

        expected = {
            "a": 1,
            "b": {"x": 10, "y": 99, "z": 100},
            "c": 3,
            "d": 4,
        }
        self.assertEqual(result, expected)
        # It should modify in-place and return the same reference
        self.assertIs(result, base)

    def test_save_file_csv_with_filename(self):
        """save_file_csv should save a CSV at cwd/save_dir/filename."""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                # Change cwd so function's os.path.join(os.getcwd(), ...) is predictable
                os.chdir(tmpdir)

                save_dir = "out"
                os.makedirs(save_dir, exist_ok=True)
                filename = "test.csv"

                save_file_csv(df_to_save=df, save_dir=save_dir, filename=filename, indexing=False)

                target_path = os.path.join(tmpdir, save_dir, filename)
                self.assertTrue(os.path.exists(target_path))

                df_loaded = pd.read_csv(target_path)
                pd.testing.assert_frame_equal(df.reset_index(drop=True), df_loaded)
            finally:
                os.chdir(old_cwd)

    def test_save_file_csv_without_filename(self):
        """save_file_csv without filename must treat save_dir as the full relative path."""
        df = pd.DataFrame({"x": [10]})

        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                os.chdir(tmpdir)
                # In this case save_dir will be the relative file path
                save_dir = "single.csv"
                save_file_csv(df_to_save=df, save_dir=save_dir, filename=None, indexing=False)

                target_path = os.path.join(tmpdir, save_dir)
                self.assertTrue(os.path.exists(target_path))

                df_loaded = pd.read_csv(target_path)
                pd.testing.assert_frame_equal(df.reset_index(drop=True), df_loaded)
            finally:
                os.chdir(old_cwd)

    def test_safe_getattr_simple_chain(self):
        """safe_getattr should traverse a chain of attributes and return the final value."""
        obj = SimpleNamespace(
            a=SimpleNamespace(
                b=SimpleNamespace(c=42)
            )
        )

        result = safe_getattr(obj, ["a", "b", "c"])
        self.assertEqual(result, 42)

    def test_safe_getattr_missing_attribute_returns_default(self):
        """safe_getattr should return value_not_found if any attribute in the chain is missing."""
        obj = SimpleNamespace(a=SimpleNamespace())

        result = safe_getattr(obj, ["a", "missing"], value_not_found=None)
        self.assertIsNone(result)

    def test_convert_stringtime_already_datetime(self):
        """convert_stringtime must return the same df if the column is already datetime."""
        df = pd.DataFrame(
            {"datetime": pd.to_datetime(["2024-01-01 12:00:00", "2024-02-01 13:00:00"])}
        )
        result = convert_stringtime(df.copy(), "datetime")
        # Column must still be datetime and unchanged
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result["datetime"]))
        pd.testing.assert_series_equal(result["datetime"], df["datetime"])

    def test_convert_stringtime_basic_format(self):
        """convert_stringtime must parse supported datetime format strings."""
        df = pd.DataFrame({"datetime": ["2024-01-01 12:34:00", "2024-02-03 01:02:03"]})
        result = convert_stringtime(df.copy(), "datetime")

        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result["datetime"]))
        self.assertEqual(result["datetime"].iloc[0], pd.Timestamp("2024-01-01 12:34:00"))
        self.assertEqual(result["datetime"].iloc[1], pd.Timestamp("2024-02-03 01:02:03"))

    def test_convert_stringtime_d_end_stat_chart_skips_reuse_vessel(self):
        """convert_stringtime must not convert 'reuse_vessel' entries for d_end_stat_chart."""
        df = pd.DataFrame(
            {
                "d_end_stat_chart": [
                    "2024-01-01 00:00:00",
                    "reuse_vessel",
                ]
            }
        )
        result = convert_stringtime(df.copy(), "d_end_stat_chart")

        # First row converted
        self.assertIsInstance(result["d_end_stat_chart"].iloc[0], pd.Timestamp)
        # Second row must still be the string 'reuse_vessel'
        self.assertEqual(result["d_end_stat_chart"].iloc[1], "reuse_vessel")

    def test_convert_stringtime_invalid_raises_valueerror(self):
        """convert_stringtime must raise ValueError if no format matches."""
        df = pd.DataFrame({"datetime": ["not-a-date"]})
        with self.assertRaises(ValueError):
            convert_stringtime(df, "datetime")

    def test_log_event_convert_stringtime_converts_d_columns(self):
        """
        log_event_convert_stringtime must convert columns beginning with 'd_'
        using convert_stringtime, leaving invalid ones untouched.
        """
        df = pd.DataFrame(
            {
                "d_trigger": ["2024-01-01 00:00:00", "2024-01-02 01:00:00"],
                "d_invalid": ["not-a-date", "still-not-date"],
                "other": [1, 2],
            }
        )

        result = log_event_convert_stringtime(df.copy())

        # d_trigger should be converted
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result["d_trigger"]))
        # d_invalid should still be strings (conversion fails, caught inside)
        self.assertFalse(pd.api.types.is_datetime64_any_dtype(result["d_invalid"]))
        self.assertEqual(result["d_invalid"].tolist(), ["not-a-date", "still-not-date"])

    def test_take_attribute_happy_path(self):
        """take_attribute must return the expected tuple of operation attributes and schedule indexes."""
        # Build a minimal oper_sched with wait_start and wait_port
        oper_sched = pd.DataFrame(
            {
                "dur_total": [1.0],
                "wait_start": [2.0],
                "wait_port": [3.0],
            }
        )

        # Mock ts_data holding oper_sched
        ts_data = SimpleNamespace(oper_sched=oper_sched)

        # Mock oper.op_class
        vessel2 = SimpleNamespace(id="VES2")
        oper_obj = SimpleNamespace(
            tech_cost=123.4,
            vessel2_id="VES2",
            vessel2_qt=1,
            vessel2=vessel2,
            ts_data=ts_data,
        )

        # Mock the stats object returned by find_operation_stats
        oper_stat = SimpleNamespace(op_class=oper_obj)

        class FakeFinder:
            def find_operation_stats(self, op_id):
                self.last_requested = op_id
                return oper_stat

        finder = FakeFinder()

        op_id = "ofw_op001"
        (
            out_oper_stat,
            out_oper,
            tech_cost,
            vessel_2,
            ves_2,
            sched,
            idx_wait_start,
            idx_wait_port,
        ) = take_attribute(op_id, finder)

        # Check finder usage
        self.assertEqual(finder.last_requested, op_id)
        self.assertIs(out_oper_stat, oper_stat)
        self.assertIs(out_oper, oper_obj)
        self.assertEqual(tech_cost, 123.4)
        self.assertEqual(vessel_2, "VES2")
        self.assertEqual(ves_2, 1)
        pd.testing.assert_frame_equal(sched, oper_sched)

        self.assertEqual(idx_wait_start, oper_sched.columns.get_loc("wait_start"))
        self.assertEqual(idx_wait_port, oper_sched.columns.get_loc("wait_port"))

    def test_take_attribute_no_vessel2(self):
        """take_attribute must handle operations without vessel2_id."""
        oper_sched = pd.DataFrame({"wait_start": [1], "wait_port": [2]})
        ts_data = SimpleNamespace(oper_sched=oper_sched)
        oper_obj = SimpleNamespace(
            tech_cost=0.0,
            vessel2_id=None,
            vessel2=None,
            ts_data=ts_data,
        )
        oper_stat = SimpleNamespace(op_class=oper_obj)

        class FakeFinder:
            def find_operation_stats(self, op_id):
                return oper_stat

        finder = FakeFinder()

        _, _, tech_cost, vessel_2, ves_2, _, _, _ = take_attribute("opX", finder)

        self.assertEqual(tech_cost, 0.0)
        self.assertIsNone(vessel_2)
        self.assertIsNone(ves_2)

    def test_create_run_folder_operation_no_previous_dir(self):
        """
        create_run_folder_operation must create the operation folder but not fail
        if the previous_run_dir does not contain the operation subfolder.
        """
        operation = SimpleNamespace(id="op001")
        operation_files = ["operation_schedule.csv"]

        # inputs_gen with consider_tseries True but previous_run_dir missing the op
        with tempfile.TemporaryDirectory() as tmpdir:
            operation_dir = os.path.join(tmpdir, "operation_dir")
            os.makedirs(operation_dir, exist_ok=True)

            previous = os.path.join(tmpdir, "previous")
            os.makedirs(previous, exist_ok=True)

            inputs_gen = SimpleNamespace(
                consider_tseries={"value": True},
                previous_run_dir={"value": previous},
            )

            create_run_folder_operation(
                operation=operation,
                operation_dir=operation_dir,
                inputs_gen=inputs_gen,
                operation_files=operation_files,
            )

            op_dir = os.path.join(operation_dir, "op001")
            self.assertTrue(os.path.exists(op_dir))
            # No files inside since src_dir did not exist
            self.assertEqual(os.listdir(op_dir), [])

    def test_create_run_folder_operation_copies_files(self):
        """create_run_folder_operation must copy only files listed in operation_files."""
        operation = SimpleNamespace(id="op001")
        operation_files = ["operation_schedule.csv"]

        with tempfile.TemporaryDirectory() as tmpdir:
            operation_dir = os.path.join(tmpdir, "operation_dir")
            previous_dir = os.path.join(tmpdir, "previous_run")
            os.makedirs(operation_dir, exist_ok=True)

            # Create source dir and some files
            src_op_dir = os.path.join(previous_dir, "operation_dir", operation.id)
            os.makedirs(src_op_dir, exist_ok=True)

            wanted_file = os.path.join(src_op_dir, "operation_schedule.csv")
            other_file = os.path.join(src_op_dir, "other.txt")

            with open(wanted_file, "w", encoding="utf-8") as f:
                f.write("content")
            with open(other_file, "w", encoding="utf-8") as f:
                f.write("ignore me")

            inputs_gen = SimpleNamespace(
                consider_tseries={"value": True},
                previous_run_dir={"value": previous_dir},
            )

            create_run_folder_operation(
                operation=operation,
                operation_dir=operation_dir,
                inputs_gen=inputs_gen,
                operation_files=operation_files,
            )

            dst_op_dir = os.path.join(operation_dir, operation.id)
            self.assertTrue(os.path.exists(dst_op_dir))

            # Only the wanted file should be copied
            files = set(os.listdir(dst_op_dir))
            self.assertEqual(files, {"operation_schedule.csv"})

    def test_create_run_folder_operation_consider_tseries_false(self):
        """
        If consider_tseries is False, create_run_folder_operation should only
        ensure the operation folder exists and not copy anything.
        """
        operation = SimpleNamespace(id="op001")
        operation_files = ["operation_schedule.csv"]

        with tempfile.TemporaryDirectory() as tmpdir:
            operation_dir = os.path.join(tmpdir, "operation_dir")
            os.makedirs(operation_dir, exist_ok=True)

            previous_dir = os.path.join(tmpdir, "previous_run")
            os.makedirs(previous_dir, exist_ok=True)

            inputs_gen = SimpleNamespace(
                consider_tseries={"value": False},
                previous_run_dir={"value": previous_dir},
            )

            create_run_folder_operation(
                operation=operation,
                operation_dir=operation_dir,
                inputs_gen=inputs_gen,
                operation_files=operation_files,
            )

            dst_op_dir = os.path.join(operation_dir, operation.id)
            self.assertTrue(os.path.exists(dst_op_dir))
            self.assertEqual(os.listdir(dst_op_dir), [])

    def test_safe_copy_df_deep_columns_are_independent(self):
        """
        safe_copy_df must deepcopy the specified columns so that mutations on the
        copy do not affect the original.
        """
        df_orig = pd.DataFrame(
            {
                "id": [1, 2],
                "comments": [["a"], ["b"]],
                "values": [10, 20],
            }
        )

        df_copy = safe_copy_df(df_orig, deep_cols=["comments"])

        # Modify comments and values in the copy
        df_copy.at[0, "comments"].append("changed")
        df_copy.at[0, "values"] = 999

        # Original comments must not be affected (deep copy)
        self.assertEqual(df_orig.at[0, "comments"], ["a"])
        # Original scalar column was shallow-copied; changing copy does not go back
        # thanks to DataFrame copy, but we still ensure values are not equal
        self.assertEqual(df_orig.at[0, "values"], 10)
        self.assertNotEqual(df_copy.at[0, "values"], df_orig.at[0, "values"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
