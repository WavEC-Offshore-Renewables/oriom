# test_operations_major_manager.py

import os
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pandas as pd
import importlib.util

from logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager import (
    operation_major_manager,
)

# --- check module check_files is present---
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
skip_if_check_files_present = unittest.skipIf(
    check_files_spec is not None,
    "check_files module available, skipping this test",
)

class DummyOperation:
    """Minimal CorrectiveMajor-like object for testing operation_major_manager."""

    def __init__(self, op_id: str, name: str, months=None):
        self.id = op_id
        self.name = name
        self.activities = ["A0", "A1"]  # content is not used because workability/startability are mocked
        self.months = months if months is not None else list(range(1, 13))
        self.ts_data = None  # will be set by the manager


class DummyInputsTseries:
    """Minimal InputsTimeSeries-like object used by operation_major_manager."""

    def __init__(self, distance=10.0, max_wait=24.0):
        self.distance = {"value": distance}
        self.max_wait = {"value": max_wait}


class TestOperationMajorManager(unittest.TestCase):
    def setUp(self):
        # Temporary directory to simulate operation_dir
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_ctx.cleanup)
        self.operation_dir = self.tmp_ctx.name

        # Simple metocean dataframe
        self.df_metocean = pd.DataFrame(
            {"hs": [1.0, 1.1, 1.2, 1.3]},
            index=pd.date_range("2020-01-01", periods=4, freq="H"),
        )

        # Dummy config and inputs
        self.Config = SimpleNamespace()
        self.inputs_tseries = DummyInputsTseries(distance=15.0, max_wait=18.0)

        # Dummy timesteps df (content not used because get_meaningful_timesteps is mocked)
        self.timesteps = pd.DataFrame({"t": [0, 1, 2]})

    # ---------- 1) Short-circuit when schedule file already exists ----------
    @skip_if_no_check_files
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.tqdm"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.OperationTimeSeriesData.create_timeseries_data"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.check_files.check_file_exists"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.modify_distance"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.workability"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.startability"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.recycle_major_other_oper_scheduler"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.get_meaningful_timesteps"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.define_operation_values"
    )
    def test_existing_schedule_short_circuits(
        self,
        m_define_op,
        m_get_ts,
        m_recycle,
        m_startability,
        m_workability,
        m_modify_distance,
        m_check_exists,
        m_create_tsdata,
        m_tqdm,
    ):
        """
        If operation_schedule.csv already exists, the manager must:
        - call OperationTimeSeriesData.create_timeseries_data with the file name
        - NOT call modify_distance, workability, startability, recycler, timesteps, define_operation_values.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation("ofw_corr_001", "Major op 1")
        operations = [op]

        # Simulate schedule file existing
        m_check_exists.return_value = True
        # create_timeseries_data returns a sentinel
        m_create_tsdata.return_value = "TS_DATA_FILE"

        operation_major_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            operations_corr_major=operations,
            Config=self.Config,
            inputs_tseries=self.inputs_tseries,
            timesteps=self.timesteps,
        )

        # File existence was checked
        op_dir = os.path.join(self.operation_dir, op.id)
        m_check_exists.assert_called_once_with(path=op_dir, file_name="operation_schedule.csv")

        # create_timeseries_data was called with the file name
        m_create_tsdata.assert_called_once_with(op, "operation_schedule.csv", op_dir)
        self.assertEqual(op.ts_data, "TS_DATA_FILE")

        # Heavy calls should NOT happen in this branch
        m_modify_distance.assert_not_called()
        m_workability.assert_not_called()
        m_startability.assert_not_called()
        m_recycle.assert_not_called()
        m_get_ts.assert_not_called()
        m_define_op.assert_not_called()

    # ---------- 2) Full path: new schedule, not recycled ----------
    @skip_if_no_check_files
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.tqdm"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.OperationTimeSeriesData.create_timeseries_data"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.define_operation_values"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.get_meaningful_timesteps"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.recycle_major_other_oper_scheduler"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.startability"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.workability"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.modify_distance"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.check_files.check_file_exists"
    )
    def test_create_schedule_when_not_existing_and_not_recycled(
        self,
        m_check_exists,
        m_modify_distance,
        m_workability,
        m_startability,
        m_recycle,
        m_get_ts,
        m_define_op,
        m_create_tsdata,
        m_tqdm,
    ):
        """
        When no schedule exists and nothing is recycled:
        - distance, workability, startability, and meaningful timesteps are computed
        - define_operation_values is called
        - OperationTimeSeriesData.create_timeseries_data is called with the returned schedule
        - ts_data is set on the operation.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation("ofw_corr_002", "Major op 2", months=[1, 2, 3])
        operations = [op]

        # No existing file
        m_check_exists.return_value = False

        # modify_distance returns a fixed transit duration
        m_modify_distance.return_value = 4.5

        # workability / startability return simple dataframes
        df_workability = pd.DataFrame(
            {"ok": [True, True]},
            index=self.df_metocean.index[:2],
        )
        m_workability.return_value = df_workability

        df_startability = pd.DataFrame(
            {"A0": [True, False], "A1": [True, True]},
            index=self.df_metocean.index[:2],
        )
        m_startability.return_value = df_startability

        # Nothing is recycled
        m_recycle.return_value = False

        # Meaningful timesteps
        op_ts = [10, 11, 12]
        m_get_ts.return_value = op_ts

        # define_operation_values returns a schedule dataframe
        oper_sched = pd.DataFrame(
            {"dur_total": [1.0, 2.0, 3.0]},
            index=self.df_metocean.index[:3],
        )
        m_define_op.return_value = oper_sched

        # create_timeseries_data returns a sentinel
        m_create_tsdata.return_value = "TS_DATA_NEW"

        operation_major_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            operations_corr_major=operations,
            Config=self.Config,
            inputs_tseries=self.inputs_tseries,
            timesteps=self.timesteps,
        )

        op_dir = os.path.join(self.operation_dir, op.id)
        # check_file_exists called
        m_check_exists.assert_called_once_with(path=op_dir, file_name="operation_schedule.csv")

        # distance computed
        m_modify_distance.assert_called_once_with(
            Config=self.Config,
            operation=op,
            default_distance=self.inputs_tseries.distance["value"],
        )

        # workability & startability computed
        m_workability.assert_called_once_with(
            activities=op.activities,
            df_metocean=self.df_metocean,
            out_dir=op_dir,
        )
        m_startability.assert_called_once_with(
            activities=op.activities,
            df_workability=df_workability,
            out_dir=op_dir,
        )

        # recycler called with correct args
        m_recycle.assert_called_once_with(
            operations=operations,
            actual_oper=op,
            df_startability=df_startability,
            counter_op=0,
            operation_dir=self.operation_dir,
        )

        # meaningful timesteps computed
        m_get_ts.assert_called_once_with(
            timeseries=self.df_metocean,
            timesteps=self.timesteps,
        )

        # define_operation_values called with expected args
        m_define_op.assert_called_once()
        _, kwargs_define = m_define_op.call_args
        self.assertEqual(kwargs_define["ts_analyse"], op_ts)
        self.assertIs(kwargs_define["operation"], op)
        self.assertTrue(kwargs_define["df_startability"].equals(df_startability))
        self.assertEqual(kwargs_define["MAX_WAIT"], self.inputs_tseries.max_wait["value"])
        self.assertEqual(kwargs_define["out_dir"], os.path.join(op_dir, "operation_schedule.csv"))

        # TS data creation and assignment
        m_create_tsdata.assert_called_once_with(op, oper_sched, op_dir)
        self.assertEqual(op.ts_data, "TS_DATA_NEW")

    # ---------- 3) Recycled schedule: skip define_operation_values ----------
    @skip_if_no_check_files
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.tqdm"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.define_operation_values"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.get_meaningful_timesteps"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.recycle_major_other_oper_scheduler"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.startability"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.workability"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.modify_distance"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.check_files.check_file_exists"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.OperationTimeSeriesData.create_timeseries_data"
    )
    def test_recycled_schedule_skips_define_operation_values(
        self,
        m_create_tsdata,
        m_check_exists,
        m_modify_distance,
        m_workability,
        m_startability,
        m_recycle,
        m_get_ts,
        m_define_op,
        m_tqdm,
    ):
        """
        When recycle_major_other_oper_scheduler returns True:
        - define_operation_values is not called
        - create_timeseries_data is not called
        - distance, workability, startability are still computed.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation("ofw_corr_003", "Major op 3")
        operations = [op]

        m_check_exists.return_value = False
        m_modify_distance.return_value = 3.0

        df_workability = pd.DataFrame({"ok": [True]}, index=self.df_metocean.index[:1])
        df_startability = pd.DataFrame({"A0": [True]}, index=self.df_metocean.index[:1])
        m_workability.return_value = df_workability
        m_startability.return_value = df_startability

        # Reuse existing schedule
        m_recycle.return_value = True

        operation_major_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            operations_corr_major=operations,
            Config=self.Config,
            inputs_tseries=self.inputs_tseries,
            timesteps=self.timesteps,
        )

        # distance, workability, startability called
        m_modify_distance.assert_called_once()
        m_workability.assert_called_once()
        m_startability.assert_called_once()
        m_recycle.assert_called_once()

        # No timesteps, no define_operation_values, no ts_data
        m_get_ts.assert_not_called()
        m_define_op.assert_not_called()
        m_create_tsdata.assert_not_called()
        self.assertIsNone(op.ts_data)

    # ---------- 3-bis) Recycled schedule: skip define_operation_values if no check_file is present ----------
    @skip_if_check_files_present
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.tqdm"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.define_operation_values"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.get_meaningful_timesteps"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.recycle_major_other_oper_scheduler"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.startability"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.workability"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.modify_distance"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.check_files"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.OperationTimeSeriesData.create_timeseries_data"
    )
    def test_recycled_schedule_skips_define_operation_values_bis(
        self,
        m_create_tsdata,
        m_check_exists,
        m_modify_distance,
        m_workability,
        m_startability,
        m_recycle,
        m_get_ts,
        m_define_op,
        m_tqdm,
    ):
        """
        When recycle_major_other_oper_scheduler returns True:
        - define_operation_values is not called
        - create_timeseries_data is not called
        - distance, workability, startability are still computed.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation("ofw_corr_003", "Major op 3")
        operations = [op]

        m_check_exists.return_value = None
        m_check_exists.__bool__.return_value = False
        m_modify_distance.return_value = 3.0

        df_workability = pd.DataFrame({"ok": [True]}, index=self.df_metocean.index[:1])
        df_startability = pd.DataFrame({"A0": [True]}, index=self.df_metocean.index[:1])
        m_workability.return_value = df_workability
        m_startability.return_value = df_startability

        # Reuse existing schedule
        m_recycle.return_value = True

        operation_major_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            operations_corr_major=operations,
            Config=self.Config,
            inputs_tseries=self.inputs_tseries,
            timesteps=self.timesteps,
        )

        # distance, workability, startability called
        m_modify_distance.assert_called_once()
        m_workability.assert_called_once()
        m_startability.assert_called_once()
        m_recycle.assert_called_once()

        # No timesteps, no define_operation_values, no ts_data
        m_get_ts.assert_not_called()
        m_define_op.assert_not_called()
        m_create_tsdata.assert_not_called()
        self.assertIsNone(op.ts_data)

    # ---------- 4) InterruptedError from define_operation_values is swallowed ----------
    @skip_if_no_check_files
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.tqdm"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.OperationTimeSeriesData.create_timeseries_data"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.define_operation_values"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.get_meaningful_timesteps"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.recycle_major_other_oper_scheduler"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.startability"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.workability"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.modify_distance"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.check_files.check_file_exists"
    )
    def test_interrupted_error_is_caught_and_not_re_raised(
        self,
        m_check_exists,
        m_modify_distance,
        m_workability,
        m_startability,
        m_recycle,
        m_get_ts,
        m_define_op,
        m_create_tsdata,
        m_tqdm,
    ):
        """
        If define_operation_values raises InterruptedError with the expected message:
        - exception is swallowed (no crash)
        - ts_data is left as None
        - create_timeseries_data is not called.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation("ofw_corr_004", "Major op 4", months=[1, 2])
        operations = [op]

        m_check_exists.return_value = False
        m_modify_distance.return_value = 2.0

        df_workability = pd.DataFrame({"ok": [True]}, index=self.df_metocean.index[:1])
        df_startability = pd.DataFrame({"A0": [True]}, index=self.df_metocean.index[:1])
        m_workability.return_value = df_workability
        m_startability.return_value = df_startability

        m_recycle.return_value = False
        m_get_ts.return_value = [0, 1]

        # define_operation_values raises the specific InterruptedError
        m_define_op.side_effect = InterruptedError(
            "The operation can never occur. OLCs may be to resctric."
        )

        # Should not raise
        operation_major_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            operations_corr_major=operations,
            Config=self.Config,
            inputs_tseries=self.inputs_tseries,
            timesteps=self.timesteps,
        )

        # create_timeseries_data must not be called and ts_data must remain None
        m_create_tsdata.assert_not_called()
        self.assertIsNone(op.ts_data)

# ---------- 4-bis) InterruptedError from define_operation_values is swallowed if check file do not exist----------
    @skip_if_check_files_present
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.tqdm"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.OperationTimeSeriesData.create_timeseries_data"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.define_operation_values"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.get_meaningful_timesteps"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.recycle_major_other_oper_scheduler"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.startability"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.workability"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.modify_distance"
    )
    @patch(
        "logistic_tools.core.timeseries_analysis.operation_managers.operations_major_manager.check_files"
    )
    def test_interrupted_error_is_caught_and_not_re_raised_bis(
        self,
        m_check_exists,
        m_modify_distance,
        m_workability,
        m_startability,
        m_recycle,
        m_get_ts,
        m_define_op,
        m_create_tsdata,
        m_tqdm,
    ):
        """
        If define_operation_values raises InterruptedError with the expected message:
        - exception is swallowed (no crash)
        - ts_data is left as None
        - create_timeseries_data is not called.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation("ofw_corr_004", "Major op 4", months=[1, 2])
        operations = [op]

        m_check_exists.return_value = None
        m_check_exists.__bool__.return_value = False
        m_modify_distance.return_value = 2.0

        df_workability = pd.DataFrame({"ok": [True]}, index=self.df_metocean.index[:1])
        df_startability = pd.DataFrame({"A0": [True]}, index=self.df_metocean.index[:1])
        m_workability.return_value = df_workability
        m_startability.return_value = df_startability

        m_recycle.return_value = False
        m_get_ts.return_value = [0, 1]

        # define_operation_values raises the specific InterruptedError
        m_define_op.side_effect = InterruptedError(
            "The operation can never occur. OLCs may be to resctric."
        )

        # Should not raise
        operation_major_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            operations_corr_major=operations,
            Config=self.Config,
            inputs_tseries=self.inputs_tseries,
            timesteps=self.timesteps,
        )

        # create_timeseries_data must not be called and ts_data must remain None
        m_create_tsdata.assert_not_called()
        self.assertIsNone(op.ts_data)
if __name__ == "__main__":
    unittest.main(verbosity=2)
