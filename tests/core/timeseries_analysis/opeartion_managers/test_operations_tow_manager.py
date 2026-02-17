# test_operation_tow_manager.py

import os
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import importlib.util

import pandas as pd

from oriom.core.timeseries_analysis.operation_managers.operations_tow_manager import (
    operation_tow_manager,
)

# --- check module check_files is present---
try:
    check_files_spec = importlib.util.find_spec(
        "oriom.core.functions.private.check_files"
    )
except ModuleNotFoundError:
    check_files_spec = None
    
skip_if_no_check_files = unittest.skipIf(
    check_files_spec is None,
    "check_files module not available, skipping related tests"
)
skip_if_check_files_present = unittest.skipIf(
    check_files_spec is not None,
    "check_files module available, skipping this test",
)

class DummyOperationTow:
    """Minimal OperationTow-like object for testing operation_tow_manager."""

    def __init__(self, op_id: str, name: str, activities=None, months=None):
        self.id = op_id
        self.name = name
        self.activities = activities if activities is not None else ["activity_1"]
        # months is used only to check if < 12 when op_timesteps is empty
        self.months = months if months is not None else list(range(1, 13))
        self.ts_data = None


class TestOperationTowManager(unittest.TestCase):
    def setUp(self):
        # Temporary directory for operation_dir
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_ctx.cleanup)
        self.operation_dir = self.tmp_ctx.name

        # Simple metocean dataframe
        self.df_metocean = pd.DataFrame(
            {"hs": [1.0, 1.1, 1.2]},
            index=pd.date_range("2020-01-01", periods=3, freq="H"),
        )

        # Dummy timesteps dataframe (content not really used in tests)
        self.timesteps = pd.DataFrame({"dummy": [1, 2, 3]})

        # max_wait is passed down to define_operation_values
        self.max_wait = 24.0

    # ---------------- 1) Short-circuit when reuse_file_exist is True ----------------
    @skip_if_no_check_files
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.tqdm")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.check_files.reuse_file_exist")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.workability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.startability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.recycle_major_other_oper_scheduler")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.get_meaningful_timesteps")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.define_operation_values")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.OperationTimeSeriesData.create_timeseries_data")
    def test_reuse_file_exist_short_circuits(
        self,
        m_create_ts,
        m_define_operation,
        m_get_timesteps,
        m_recycle,
        m_startability,
        m_workability,
        m_reuse_file,
        m_tqdm,
    ):
        """If reuse_file_exist returns True, the function must skip the heavy computation."""
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable
        Config = MagicMock(DIFF_DISTANCE=5)
        inputs_tseries = MagicMock(distance={'value':10})
        op = DummyOperationTow("tow_001", "Tow operation 1")
        operations = [op]

        m_reuse_file.return_value = True

        operation_tow_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            max_wait=self.max_wait,
            operations_tow=operations,
            timesteps=self.timesteps,
            Config = Config,
            inputs_tseries = inputs_tseries
        )

        op_dir = os.path.join(self.operation_dir, op.id)
        m_reuse_file.assert_called_once_with(
            op_dir=op_dir,
            file_name_schedule="operation_schedule.csv",
            operation=op,
        )

        # All the heavy functions must not be called
        m_workability.assert_not_called()
        m_startability.assert_not_called()
        m_recycle.assert_not_called()
        m_get_timesteps.assert_not_called()
        m_define_operation.assert_not_called()
        m_create_ts.assert_not_called()
        self.assertIsNone(op.ts_data)

    # ---------------- 2) Happy path: everything runs, ts_data is set ----------------
    @skip_if_no_check_files
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.tqdm")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.check_files.reuse_file_exist")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.workability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.startability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.recycle_major_other_oper_scheduler")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.get_meaningful_timesteps")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.define_operation_values")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.OperationTimeSeriesData.create_timeseries_data")
    def test_happy_path_calls_all_and_sets_ts_data(
        self,
        m_create_ts,
        m_define_operation,
        m_get_timesteps,
        m_recycle,
        m_startability,
        m_workability,
        m_reuse_file,
        m_tqdm,
    ):
        """When no reuse is available, the full pipeline should run and ts_data should be created."""
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable
        Config = MagicMock(DIFF_DISTANCE=5)
        inputs_tseries = MagicMock(distance={'value':10})
        op = DummyOperationTow("tow_002", "Tow operation 2")
        operations = [op]

        # First reuse_file_exist (for this operation) returns False
        m_reuse_file.return_value = False

        # Workability / Startability DataFrames
        df_work = pd.DataFrame({"ok": [True, True]}, index=self.df_metocean.index[:2])
        df_start = pd.DataFrame({"start": [1, 0]}, index=self.df_metocean.index[:2])
        m_workability.return_value = df_work
        m_startability.return_value = df_start

        # Recycle function is called, but its return is ignored by manager
        m_recycle.return_value = False

        # Meaningful timesteps
        timesteps_list = list(self.df_metocean.index)
        m_get_timesteps.return_value = timesteps_list

        # define_operation_values returns some schedule object (can be a DataFrame or any placeholder)
        oper_sched = pd.DataFrame({"dur_total": [10.0]}, index=[self.df_metocean.index[0]])
        m_define_operation.return_value = oper_sched

        # create_timeseries_data returns a sentinel object
        m_create_ts.return_value = "TS_DATA_OK"

        operation_tow_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            max_wait=self.max_wait,
            operations_tow=operations,
            timesteps=self.timesteps,
            Config= Config,
            inputs_tseries = inputs_tseries
        )

        op_dir = os.path.join(self.operation_dir, op.id)

        # Initial reuse_file_exist call
        m_reuse_file.assert_any_call(
            op_dir=op_dir,
            file_name_schedule="operation_schedule.csv",
            operation=op,
        )

        # Workability & startability calls
        m_workability.workability.assert_called_once_with(
            activities=op.activities,
            df_metocean=self.df_metocean,
            out_dir=op_dir,
        )
        m_startability.assert_called_once()
        _, kwargs = m_startability.call_args
        self.assertEqual(kwargs["activities"], op.activities)
        self.assertEqual(kwargs["out_dir"], op_dir)

        # Recycle check
        m_recycle.assert_called_once_with(
            operations=operations,
            actual_oper=op,
            df_startability=df_start,
            counter_op=0,
            operation_dir=self.operation_dir,
        )

        # get_meaningful_timesteps call
        m_get_timesteps.assert_called_once_with(
            timeseries=self.df_metocean,
            timesteps=self.timesteps,
        )

        # define_operation_values call
        m_define_operation.assert_called_once()
        _, kwargs_def = m_define_operation.call_args
        self.assertIs(kwargs_def["operation"], op)
        self.assertIs(kwargs_def["df_startability"], df_start)
        self.assertEqual(kwargs_def["ts_analyse"], timesteps_list)
        self.assertEqual(kwargs_def["MAX_WAIT"], self.max_wait)
        self.assertEqual(
            kwargs_def["out_dir"],
            os.path.join(op_dir, "operation_schedule.csv"),
        )

        # create_timeseries_data call
        m_create_ts.assert_called_once_with(op, oper_sched, op_dir)
        self.assertEqual(op.ts_data, "TS_DATA_OK")

    # ---------------- 3) Empty timesteps still calls define_operation_values ----------------
    @skip_if_no_check_files
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.tqdm")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.check_files.reuse_file_exist")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.workability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.startability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.recycle_major_other_oper_scheduler")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.get_meaningful_timesteps")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.define_operation_values")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.OperationTimeSeriesData.create_timeseries_data")
    def test_empty_timesteps_still_runs_define_operation_values(
        self,
        m_create_ts,
        m_define_operation,
        m_get_timesteps,
        m_recycle,
        m_startability,
        m_workability,
        m_reuse_file,
        m_tqdm,
    ):
        """
        If get_meaningful_timesteps returns an empty sequence, define_operation_values
        should still be called with ts_analyse = [].
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable
        Config = MagicMock(DIFF_DISTANCE=5)
        inputs_tseries = MagicMock(distance={'value':10})
        # months < 12 to trigger log message branch (not asserted but we respect logic)
        op = DummyOperationTow("tow_003", "Tow operation 3", months=[1, 2, 3])
        operations = [op]

        m_reuse_file.return_value = False

        df_work = pd.DataFrame({"ok": [True]}, index=self.df_metocean.index[:1])
        df_start = pd.DataFrame({"start": [1]}, index=self.df_metocean.index[:1])
        m_workability.return_value = df_work
        m_startability.return_value = df_start
        m_recycle.return_value = False

        # Empty timesteps
        m_get_timesteps.return_value = []

        oper_sched = pd.DataFrame({"dur_total": [5.0]}, index=[self.df_metocean.index[0]])
        m_define_operation.return_value = oper_sched
        m_create_ts.return_value = "TS_DATA_OK"

        operation_tow_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            max_wait=self.max_wait,
            operations_tow=operations,
            Config = Config,
            inputs_tseries = inputs_tseries,
            timesteps=self.timesteps,
        )

        m_get_timesteps.assert_called_once_with(
            timeseries=self.df_metocean,
            timesteps=self.timesteps,
        )

        m_define_operation.assert_called_once()
        _, kwargs_def = m_define_operation.call_args
        self.assertEqual(kwargs_def["ts_analyse"], [])

        self.assertEqual(op.ts_data, "TS_DATA_OK")

    # ---------------- 4) InterruptedError with specific message is swallowed ----------------
    @skip_if_no_check_files
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.tqdm")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.check_files.reuse_file_exist")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.workability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.startability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.recycle_major_other_oper_scheduler")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.get_meaningful_timesteps")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.define_operation_values")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.OperationTimeSeriesData.create_timeseries_data")
    def test_interrupted_error_with_specific_message_is_swallowed(
        self,
        m_create_ts,
        m_define_operation,
        m_get_timesteps,
        m_recycle,
        m_startability,
        m_workability,
        m_reuse_file,
        m_tqdm,
    ):
        """
        If define_operation_values raises InterruptedError with the specific message
        'The operation can never occur. OLCs may be to resctric.', it must be swallowed.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable
        Config = MagicMock(DIFF_DISTANCE=5)
        inputs_tseries = MagicMock(distance={'value':10})
        op = DummyOperationTow("tow_004", "Tow operation 4")
        operations = [op]

        m_reuse_file.return_value = False

        df_work = pd.DataFrame({"ok": [True]}, index=self.df_metocean.index[:1])
        df_start = pd.DataFrame({"start": [1]}, index=self.df_metocean.index[:1])
        m_workability.return_value = df_work
        m_startability.return_value = df_start
        m_recycle.return_value = False

        m_get_timesteps.return_value = list(self.df_metocean.index[:1])

        m_define_operation.side_effect = InterruptedError(
            "The operation can never occur. OLCs may be to resctric."
        )

        # Should NOT raise
        operation_tow_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            max_wait=self.max_wait,
            operations_tow=operations,
            timesteps=self.timesteps,
            Config = Config,
            inputs_tseries = inputs_tseries
        )

        # No TS data created
        m_create_ts.assert_not_called()
        self.assertIsNone(op.ts_data)

    # ---------------- 5) InterruptedError with different message is re-raised ----------------
    @skip_if_no_check_files
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.tqdm")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.check_files.reuse_file_exist")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.workability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.startability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.recycle_major_other_oper_scheduler")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.get_meaningful_timesteps")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.define_operation_values")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.OperationTimeSeriesData.create_timeseries_data")
    def test_interrupted_error_with_other_message_is_reraised(
        self,
        m_create_ts,
        m_define_operation,
        m_get_timesteps,
        m_recycle,
        m_startability,
        m_workability,
        m_reuse_file,
        m_tqdm,
    ):
        """
        If define_operation_values raises InterruptedError with a different message,
        the error must be re-raised.
        """
        Config = MagicMock(DIFF_DISTANCE=5)
        inputs_tseries = MagicMock(distance={'value':10})
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperationTow("tow_005", "Tow operation 5")
        operations = [op]

        m_reuse_file.return_value = False

        df_work = pd.DataFrame({"ok": [True]}, index=self.df_metocean.index[:1])
        df_start = pd.DataFrame({"start": [1]}, index=self.df_metocean.index[:1])
        m_workability.return_value = df_work
        m_startability.return_value = df_start
        m_recycle.return_value = False

        m_get_timesteps.return_value = list(self.df_metocean.index[:1])

        m_define_operation.side_effect = InterruptedError("Some other problem")

        with self.assertRaises(InterruptedError):
            operation_tow_manager(
                operation_dir=self.operation_dir,
                df_metocean=self.df_metocean,
                max_wait=self.max_wait,
                operations_tow=operations,
                timesteps=self.timesteps,
                Config = Config,
                inputs_tseries = inputs_tseries
            )

        m_create_ts.assert_not_called()
        self.assertIsNone(op.ts_data)

    # ---------------- 2-bis) Happy path: everything runs, ts_data is set ----------------
    @skip_if_check_files_present
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.tqdm")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.check_files")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.workability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.startability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.recycle_major_other_oper_scheduler")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.get_meaningful_timesteps")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.define_operation_values")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.OperationTimeSeriesData.create_timeseries_data")
    def test_happy_path_calls_all_and_sets_ts_data_bis(
        self,
        m_create_ts,
        m_define_operation,
        m_get_timesteps,
        m_recycle,
        m_startability,
        m_workability,
        m_reuse_file,
        m_tqdm,
    ):
        """When no reuse is available, the full pipeline should run and ts_data should be created."""
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable
        Config = MagicMock(DIFF_DISTANCE=5)
        inputs_tseries = MagicMock(distance={'value':10})
        op = DummyOperationTow("tow_002", "Tow operation 2")
        operations = [op]

        # First reuse_file_exist (for this operation) returns False
        m_reuse_file.return_value = None
        m_reuse_file.__bool__.return_value = False
        

        # Workability / Startability DataFrames
        df_work = pd.DataFrame({"ok": [True, True]}, index=self.df_metocean.index[:2])
        df_start = pd.DataFrame({"start": [1, 0]}, index=self.df_metocean.index[:2])
        m_workability.return_value = df_work
        m_startability.return_value = df_start

        # Recycle function is called, but its return is ignored by manager
        m_recycle.return_value = False

        # Meaningful timesteps
        timesteps_list = list(self.df_metocean.index)
        m_get_timesteps.return_value = timesteps_list

        # define_operation_values returns some schedule object (can be a DataFrame or any placeholder)
        oper_sched = pd.DataFrame({"dur_total": [10.0]}, index=[self.df_metocean.index[0]])
        m_define_operation.return_value = oper_sched

        # create_timeseries_data returns a sentinel object
        m_create_ts.return_value = "TS_DATA_OK"

        operation_tow_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            max_wait=self.max_wait,
            operations_tow=operations,
            timesteps=self.timesteps,
            Config= Config,
            inputs_tseries = inputs_tseries
        )

        op_dir = os.path.join(self.operation_dir, op.id)

        # Workability & startability calls
        m_workability.workability.assert_called_once_with(
            activities=op.activities,
            df_metocean=self.df_metocean,
            out_dir=op_dir,
        )
        m_startability.assert_called_once()
        _, kwargs = m_startability.call_args
        self.assertEqual(kwargs["activities"], op.activities)
        self.assertEqual(kwargs["out_dir"], op_dir)

        # Recycle check
        m_recycle.assert_called_once_with(
            operations=operations,
            actual_oper=op,
            df_startability=df_start,
            counter_op=0,
            operation_dir=self.operation_dir,
        )

        # get_meaningful_timesteps call
        m_get_timesteps.assert_called_once_with(
            timeseries=self.df_metocean,
            timesteps=self.timesteps,
        )

        # define_operation_values call
        m_define_operation.assert_called_once()
        _, kwargs_def = m_define_operation.call_args
        self.assertIs(kwargs_def["operation"], op)
        self.assertIs(kwargs_def["df_startability"], df_start)
        self.assertEqual(kwargs_def["ts_analyse"], timesteps_list)
        self.assertEqual(kwargs_def["MAX_WAIT"], self.max_wait)
        self.assertEqual(
            kwargs_def["out_dir"],
            os.path.join(op_dir, "operation_schedule.csv"),
        )

        # create_timeseries_data call
        m_create_ts.assert_called_once_with(op, oper_sched, op_dir)
        self.assertEqual(op.ts_data, "TS_DATA_OK")

    # ---------------- 3-bis) Empty timesteps still calls define_operation_values ----------------
    @skip_if_check_files_present
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.tqdm")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.check_files")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.workability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.startability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.recycle_major_other_oper_scheduler")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.get_meaningful_timesteps")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.define_operation_values")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.OperationTimeSeriesData.create_timeseries_data")
    def test_empty_timesteps_still_runs_define_operation_values_bis(
        self,
        m_create_ts,
        m_define_operation,
        m_get_timesteps,
        m_recycle,
        m_startability,
        m_workability,
        m_reuse_file,
        m_tqdm,
    ):
        """
        If get_meaningful_timesteps returns an empty sequence, define_operation_values
        should still be called with ts_analyse = [].
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable
        Config = MagicMock(DIFF_DISTANCE=5)
        inputs_tseries = MagicMock(distance={'value':10})
        # months < 12 to trigger log message branch (not asserted but we respect logic)
        op = DummyOperationTow("tow_003", "Tow operation 3", months=[1, 2, 3])
        operations = [op]

        m_reuse_file.return_value = None
        m_reuse_file.__bool__.return_value = False

        df_work = pd.DataFrame({"ok": [True]}, index=self.df_metocean.index[:1])
        df_start = pd.DataFrame({"start": [1]}, index=self.df_metocean.index[:1])
        m_workability.return_value = df_work
        m_startability.return_value = df_start
        m_recycle.return_value = False

        # Empty timesteps
        m_get_timesteps.return_value = []

        oper_sched = pd.DataFrame({"dur_total": [5.0]}, index=[self.df_metocean.index[0]])
        m_define_operation.return_value = oper_sched
        m_create_ts.return_value = "TS_DATA_OK"

        operation_tow_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            max_wait=self.max_wait,
            operations_tow=operations,
            Config = Config,
            inputs_tseries = inputs_tseries,
            timesteps=self.timesteps,
        )

        m_get_timesteps.assert_called_once_with(
            timeseries=self.df_metocean,
            timesteps=self.timesteps,
        )

        m_define_operation.assert_called_once()
        _, kwargs_def = m_define_operation.call_args
        self.assertEqual(kwargs_def["ts_analyse"], [])

        self.assertEqual(op.ts_data, "TS_DATA_OK")

    # ---------------- 4-bis) InterruptedError with specific message is swallowed ----------------
    @skip_if_check_files_present
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.tqdm")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.check_files")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.workability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.startability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.recycle_major_other_oper_scheduler")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.get_meaningful_timesteps")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.define_operation_values")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.OperationTimeSeriesData.create_timeseries_data")
    def test_interrupted_error_with_specific_message_is_swallowed_bis(
        self,
        m_create_ts,
        m_define_operation,
        m_get_timesteps,
        m_recycle,
        m_startability,
        m_workability,
        m_reuse_file,
        m_tqdm,
    ):
        """
        If define_operation_values raises InterruptedError with the specific message
        'The operation can never occur. OLCs may be to resctric.', it must be swallowed.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable
        Config = MagicMock(DIFF_DISTANCE=5)
        inputs_tseries = MagicMock(distance={'value':10})
        op = DummyOperationTow("tow_004", "Tow operation 4")
        operations = [op]

        m_reuse_file.return_value = None
        m_reuse_file.__bool__.return_value = False

        df_work = pd.DataFrame({"ok": [True]}, index=self.df_metocean.index[:1])
        df_start = pd.DataFrame({"start": [1]}, index=self.df_metocean.index[:1])
        m_workability.return_value = df_work
        m_startability.return_value = df_start
        m_recycle.return_value = False

        m_get_timesteps.return_value = list(self.df_metocean.index[:1])

        m_define_operation.side_effect = InterruptedError(
            "The operation can never occur. OLCs may be to resctric."
        )

        # Should NOT raise
        operation_tow_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            max_wait=self.max_wait,
            operations_tow=operations,
            timesteps=self.timesteps,
            Config = Config,
            inputs_tseries = inputs_tseries
        )

        # No TS data created
        m_create_ts.assert_not_called()
        self.assertIsNone(op.ts_data)

    # ---------------- 5_bis) InterruptedError with different message is re-raised ----------------
    @skip_if_check_files_present

    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.tqdm")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.check_files")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.workability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.startability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.recycle_major_other_oper_scheduler")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.get_meaningful_timesteps")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.define_operation_values")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_tow_manager.OperationTimeSeriesData.create_timeseries_data")
    def test_interrupted_error_with_other_message_is_reraised_bis(
        self,
        m_create_ts,
        m_define_operation,
        m_get_timesteps,
        m_recycle,
        m_startability,
        m_workability,
        m_reuse_file,
        m_tqdm,
    ):
        """
        If define_operation_values raises InterruptedError with a different message,
        the error must be re-raised.
        """
        Config = MagicMock(DIFF_DISTANCE=5)
        inputs_tseries = MagicMock(distance={'value':10})
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperationTow("tow_005", "Tow operation 5")
        operations = [op]

        m_reuse_file.return_value = None
        m_reuse_file.__bool__.return_value = False

        df_work = pd.DataFrame({"ok": [True]}, index=self.df_metocean.index[:1])
        df_start = pd.DataFrame({"start": [1]}, index=self.df_metocean.index[:1])
        m_workability.return_value = df_work
        m_startability.return_value = df_start
        m_recycle.return_value = False

        m_get_timesteps.return_value = list(self.df_metocean.index[:1])

        m_define_operation.side_effect = InterruptedError("Some other problem")

        with self.assertRaises(InterruptedError):
            operation_tow_manager(
                operation_dir=self.operation_dir,
                df_metocean=self.df_metocean,
                max_wait=self.max_wait,
                operations_tow=operations,
                timesteps=self.timesteps,
                Config = Config,
                inputs_tseries = inputs_tseries
            )

        m_create_ts.assert_not_called()
        self.assertIsNone(op.ts_data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
