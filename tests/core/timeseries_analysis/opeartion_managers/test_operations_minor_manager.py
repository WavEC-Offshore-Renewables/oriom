# test_operations_minor_manager.py

import os
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import importlib.util

import pandas as pd

from oriom.core.timeseries_analysis.operation_managers.operations_minor_manager import (
    opeartion_minor_manager,
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


class DummyOperation:
    """Minimal CorrectiveMinor-like object for testing opeartion_minor_manager."""

    def __init__(
        self,
        op_id: str,
        name: str,
        duration_net: float = 5.0,
        device_shutdown: bool = False,
        technology: str = "ofw",
    ):
        self.id = op_id
        self.name = name
        self.duration_net = duration_net
        self.device_shutdown = device_shutdown
        self.technology = technology
        self.ts_data = None

        # Attributes used in ATTRIBUTE_LIST (can be simplified)
        self.duration_net = duration_net
        self.hs = None
        self.tp = None
        self.ws = None
        self.ws_hub = None
        self.cs = None
        self.light = None
        self.vessel1_id = "v1"
        self.vessel2_id = None
        self.shutdown = device_shutdown
        self.technology = technology
        self.rov = None


class DummyInputsTseries:
    """Minimal InputsTimeSeries-like object used by opeartion_minor_manager."""

    def __init__(self, distance=10.0, shift_duration=12.0, time_between=0.0):
        self.distance = {"value": distance}
        self.shift_duration = {"value": shift_duration}
        self._time_between = time_between
        self.ST_O_M = False

    def find_time_between_devices(self, operation_obj_id: str) -> float:
        return self._time_between


class TestInspectMinorManager(unittest.TestCase):
    def setUp(self):
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_ctx.cleanup)
        self.operation_dir = self.tmp_ctx.name

        # Simple metocean dataframe
        self.df_metocean = pd.DataFrame(
            {"hs": [1.0, 1.1, 1.2]},
            index=pd.date_range("2020-01-01", periods=3, freq="H"),
        )

        # Dummy Config and inputs
        self.Config = SimpleNamespace()
        self.inputs_tseries = DummyInputsTseries(
            distance=15.0, shift_duration=12.0, time_between=1.0
        )

    # -------- 1) Reuse existing schedule: reuse_file_exist returns True --------
    @skip_if_no_check_files
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.tqdm"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.check_files.reuse_file_exist"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.recycle_other_oper_scheduler"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.modify_distance"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.working_shifts"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.workability"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.yaml_manager.update_yaml_each_attribute"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.yaml_manager.update_yaml"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.define_shift_operation_values"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.aux_functions.convert_stringtime"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.OperationTimeSeriesData.create_timeseries_data"
    )
    def test_reuse_existing_schedule_short_circuits(
        self,
        m_create_ts,
        m_convert_time,
        m_define_shift,
        m_yaml_update,
        m_yaml_each,
        m_workability,
        m_working_shifts,
        m_modify_distance,
        m_recycle,
        m_reuse_file,
        m_tqdm,
    ):
        """If reuse_file_exist returns True, the body should skip heavy computation."""
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation("ofw_min_001", "Minor op 1")
        operations = [op]

        # recycle_other_oper_scheduler returns some similar id
        m_recycle.return_value = "ofw_min_001"
        # reuse_file_exist says a schedule already exists / is reused
        m_reuse_file.return_value = True

        opeartion_minor_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            operations_corr_minor=operations,
            inputs_tseries=self.inputs_tseries,
            Config=self.Config,
        )

        # Basic checks
        m_recycle.assert_called_once()
        op_dir = os.path.join(self.operation_dir, op.id)
        op_dir_other = os.path.join(self.operation_dir, "ofw_min_001")
        m_reuse_file.assert_called_once_with(
            op_dir=op_dir,
            file_name_schedule="operation_schedule.csv",
            operation=op,
            similar_inspection_id="ofw_min_001",
            op_dir_other=op_dir_other,
        )

        # No further heavy calls
        m_modify_distance.assert_not_called()
        m_working_shifts.assert_not_called()
        m_workability.assert_not_called()
        m_yaml_each.assert_not_called()
        m_yaml_update.assert_not_called()
        m_define_shift.assert_not_called()
        m_convert_time.assert_not_called()
        m_create_ts.assert_not_called()
        self.assertIsNone(op.ts_data)

    # -------- 2) Happy path: single shift, device_shutdown False --------
    @skip_if_no_check_files
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.tqdm"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.check_files.reuse_file_exist"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.recycle_other_oper_scheduler"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.modify_distance"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.working_shifts"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.workability"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.yaml_manager.update_yaml_each_attribute"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.yaml_manager.update_yaml"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.define_shift_operation_values"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.aux_functions.convert_stringtime"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.OperationTimeSeriesData.create_timeseries_data"
    )
    def test_happy_path_single_shift_no_shutdown(
        self,
        m_create_ts,
        m_convert_time,
        m_define_shift,
        m_yaml_update,
        m_yaml_each,
        m_workability,
        m_working_shifts,
        m_modify_distance,
        m_recycle,
        m_reuse_file,
        m_tqdm,
    ):
        """
        When no reuse exists and working_shifts returns a single shift,
        define_shift_operation_values is called and ts_data is set.
        Shutdown durations must be NaN if device_shutdown is False.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation("ofw_min_002", "Minor op 2", device_shutdown=False)
        operations = [op]

        m_recycle.return_value = op.id
        m_reuse_file.return_value = False

        m_modify_distance.return_value = 3.5

        # Working shifts: one shift only
        op_working_shifts = {"number_shifts_main": 1, "number_shifts_last": 0}
        data_working_shifts = {"dummy": "data"}
        m_working_shifts.return_value = (op_working_shifts, data_working_shifts)

        # Workability df
        df_workability = pd.DataFrame({"ok": [True, True]}, index=self.df_metocean.index[:2])
        m_workability.return_value = df_workability

        # Schedule df from define_shift_operation_values
        oper_sched_raw = pd.DataFrame(
            {"dur_total": [1.0, 2.0]}, index=self.df_metocean.index[:2]
        )
        m_define_shift.return_value = oper_sched_raw

        # convert_stringtime returns the same df
        m_convert_time.side_effect = lambda df: df

        # create_timeseries_data returns a sentinel
        m_create_ts.return_value = "TS_DATA_OK"

        opeartion_minor_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            operations_corr_minor=operations,
            inputs_tseries=self.inputs_tseries,
            Config=self.Config,
        )

        # modify_distance called
        m_modify_distance.assert_called_once_with(
            Config=self.Config,
            operation=op,
            default_distance=self.inputs_tseries.distance["value"],
        )

        # working_shifts called with proper args
        m_working_shifts.assert_called_once()
        _, kwargs_ws = m_working_shifts.call_args
        self.assertIs(kwargs_ws["operation"], op)
        self.assertEqual(
            kwargs_ws["duration_shift"], self.inputs_tseries.shift_duration["value"]
        )
        self.assertEqual(kwargs_ws["transit"], 3.5)
        self.assertEqual(
            kwargs_ws["transit_between_devices"],
            self.inputs_tseries.find_time_between_devices(op.id),
        )
        self.assertTrue(kwargs_ws["minor_op"])

        # workability called
        op_dir = os.path.join(self.operation_dir, op.id)
        m_workability.assert_called_once_with(
            operation=op, df_metocean=self.df_metocean, out_dir=op_dir
        )

        # YAML updates
        m_yaml_each.assert_called_once()

        _, kwargs = m_yaml_each.call_args

        self.assertEqual(kwargs["file_dir"], op_dir)
        self.assertEqual(kwargs["file_name"], "attributes.yaml")
        self.assertEqual(kwargs["data"], op_working_shifts)

        m_yaml_update.assert_called_once()

        _, kwargs = m_yaml_update.call_args

        self.assertEqual(kwargs["file_dir"], op_dir)
        self.assertEqual(kwargs["file_name"], "attributes.yaml")
        self.assertEqual(kwargs["data"], data_working_shifts)

        # define_shift_operation_values called with NaN shutdowns
        m_define_shift.assert_called_once()
        _, kwargs_def = m_define_shift.call_args
        self.assertIs(kwargs_def["operation"], op)
        self.assertIs(kwargs_def["df_metocean"], self.df_metocean)
        self.assertIs(kwargs_def["df_workability"], df_workability)
        self.assertEqual(kwargs_def["shift_data"], op_working_shifts)
        self.assertEqual(kwargs_def["transit_duration"], 3.5)
        # shutdowns must be NaN because device_shutdown=False
        self.assertTrue(pd.isna(kwargs_def["shutdown_wtg"]))
        self.assertTrue(pd.isna(kwargs_def["shutdown_wec"]))
        self.assertTrue(pd.isna(kwargs_def["shutdown_pv"]))

        # convert_stringtime + create_timeseries_data
        m_convert_time.assert_called_once_with(oper_sched_raw)
        m_create_ts.assert_called_once_with(op, oper_sched_raw, op_dir)
        self.assertEqual(op.ts_data, "TS_DATA_OK")

    # -------- 3) Device shutdown True, type-specific assignment (ofw/opv/owc) --------
    @skip_if_no_check_files
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.tqdm"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.check_files.reuse_file_exist"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.recycle_other_oper_scheduler"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.modify_distance"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.working_shifts"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.workability"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.yaml_manager.update_yaml_each_attribute"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.yaml_manager.update_yaml"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.define_shift_operation_values"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.aux_functions.convert_stringtime"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.OperationTimeSeriesData.create_timeseries_data"
    )
    def test_shutdown_type_branches_ofw_opv_owc(
        self,
        m_create_ts,
        m_convert_time,
        m_define_shift,
        m_yaml_update,
        m_yaml_each,
        m_workability,
        m_working_shifts,
        m_modify_distance,
        m_recycle,
        m_reuse_file,
        m_tqdm,
    ):
        """
        When device_shutdown is True, shutdown_* must be set according to the id prefix:
        - 'ofw' -> shutdown_wtg
        - 'owc' -> shutdown_wec
        - 'opv' -> shutdown_pv
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable
        m_reuse_file.return_value = False
        m_modify_distance.return_value = 1.0
        op_working_shifts = {"number_shifts_main": 1, "number_shifts_last": 0}
        data_working_shifts = {}
        m_working_shifts.return_value = (op_working_shifts, data_working_shifts)
        df_workability = pd.DataFrame({"ok": [True]}, index=self.df_metocean.index[:1])
        m_workability.return_value = df_workability
        oper_sched_raw = pd.DataFrame({"dur_total": [1.0]}, index=self.df_metocean.index[:1])
        m_define_shift.return_value = oper_sched_raw
        m_convert_time.side_effect = lambda df: df
        m_create_ts.return_value = "TS_DATA"

        # We test three operations
        ops = [
            DummyOperation("ofw_min_003", "Minor ofw", duration_net=4.0, device_shutdown=True),
            DummyOperation("owc_min_004", "Minor owc", duration_net=6.0, device_shutdown=True),
            DummyOperation("opv_min_005", "Minor opv", duration_net=8.0, device_shutdown=True),
        ]

        # recycle_other_oper_scheduler simply returns its own op.id
        m_recycle.side_effect = lambda minor_oper_dict, hash_to_key, operation, attribute_list: operation.id

        opeartion_minor_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            operations_corr_minor=ops,
            inputs_tseries=self.inputs_tseries,
            Config=self.Config,
        )

        # We expect define_shift_operation_values invoked three times
        self.assertEqual(m_define_shift.call_count, 3)

        # Extract shutdown arguments per call
        calls = m_define_shift.call_args_list
        shutdown_sets = []
        for call in calls:
            _, kwargs_def = call
            shutdown_sets.append(
                (
                    kwargs_def["shutdown_wtg"],
                    kwargs_def["shutdown_wec"],
                    kwargs_def["shutdown_pv"],
                )
            )

        # For ofw_min_003 (duration_net=4.0) -> shutdown_wtg=4.0
        self.assertAlmostEqual(shutdown_sets[0][0], 4.0)
        self.assertTrue(pd.isna(shutdown_sets[0][1]))
        self.assertTrue(pd.isna(shutdown_sets[0][2]))

        # For owc_min_004 -> shutdown_wec=6.0
        self.assertTrue(pd.isna(shutdown_sets[1][0]))
        self.assertAlmostEqual(shutdown_sets[1][1], 6.0)
        self.assertTrue(pd.isna(shutdown_sets[1][2]))

        # For opv_min_005 -> shutdown_pv=8.0
        self.assertTrue(pd.isna(shutdown_sets[2][0]))
        self.assertTrue(pd.isna(shutdown_sets[2][1]))
        self.assertAlmostEqual(shutdown_sets[2][2], 8.0)

    # -------- 4) RuntimeError when more than one shift is required --------
    @skip_if_no_check_files
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.tqdm"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.check_files.reuse_file_exist"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.recycle_other_oper_scheduler"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.modify_distance"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.working_shifts"
    )
    def test_runtime_error_when_more_than_one_shift(
        self,
        m_working_shifts,
        m_modify_distance,
        m_recycle,
        m_reuse_file,
        m_tqdm,
    ):
        """
        If number_shifts_main + number_shifts_last > 1, a RuntimeError must be raised.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation("ofw_min_006", "Too long minor op", device_shutdown=False)
        operations = [op]

        m_reuse_file.return_value = False
        m_recycle.return_value = op.id
        m_modify_distance.return_value = 2.0

        # Two shifts in total -> triggers RuntimeError
        op_working_shifts = {"number_shifts_main": 1, "number_shifts_last": 1}
        data_working_shifts = {}
        m_working_shifts.return_value = (op_working_shifts, data_working_shifts)

        with self.assertRaises(RuntimeError) as ctx:
            opeartion_minor_manager(
                operation_dir=self.operation_dir,
                df_metocean=self.df_metocean,
                operations_corr_minor=operations,
                inputs_tseries=self.inputs_tseries,
                Config=self.Config,
            )

        self.assertIn("operation too long, consider defining as CorrectiveMajor", str(ctx.exception))

    # -------- 5) InterruptedError with specific message is swallowed --------
    @skip_if_no_check_files
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.tqdm"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.check_files.reuse_file_exist"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.recycle_other_oper_scheduler"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.modify_distance"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.working_shifts"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.workability"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.yaml_manager.update_yaml_each_attribute"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.yaml_manager.update_yaml"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.define_shift_operation_values"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.aux_functions.convert_stringtime"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.OperationTimeSeriesData.create_timeseries_data"
    )
    def test_interrupted_error_is_caught(
        self,
        m_create_ts,
        m_convert_time,
        m_define_shift,
        m_yaml_update,
        m_yaml_each,
        m_workability,
        m_working_shifts,
        m_modify_distance,
        m_recycle,
        m_reuse_file,
        m_tqdm,
    ):
        """
        If define_shift_operation_values raises the specific InterruptedError,
        it must be swallowed and ts_data left as None.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation("ofw_min_007", "Interrupted minor op", device_shutdown=False)
        operations = [op]

        m_reuse_file.return_value = False
        m_recycle.return_value = op.id
        m_modify_distance.return_value = 1.0

        op_working_shifts = {"number_shifts_main": 1, "number_shifts_last": 0}
        data_working_shifts = {}
        m_working_shifts.return_value = (op_working_shifts, data_working_shifts)

        df_workability = pd.DataFrame({"ok": [True]}, index=self.df_metocean.index[:1])
        m_workability.return_value = df_workability

        m_define_shift.side_effect = InterruptedError(
            "The operation can never occur. OLCs may be to resctric."
        )

        # Should not raise
        opeartion_minor_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            operations_corr_minor=operations,
            inputs_tseries=self.inputs_tseries,
            Config=self.Config,
        )

        # No TS data created
        m_create_ts.assert_not_called()
        self.assertIsNone(op.ts_data)

    # -------- 2-bis) Happy path: single shift, device_shutdown False --------
    @skip_if_check_files_present
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.tqdm"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.check_files"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.recycle_other_oper_scheduler"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.modify_distance"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.working_shifts"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.workability"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.yaml_manager.update_yaml_each_attribute"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.yaml_manager.update_yaml"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.define_shift_operation_values"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.aux_functions.convert_stringtime"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.OperationTimeSeriesData.create_timeseries_data"
    )
    def test_happy_path_single_shift_no_shutdown_bis(
        self,
        m_create_ts,
        m_convert_time,
        m_define_shift,
        m_yaml_update,
        m_yaml_each,
        m_workability,
        m_working_shifts,
        m_modify_distance,
        m_recycle,
        m_reuse_file,
        m_tqdm,
    ):
        """
        When no reuse exists and working_shifts returns a single shift,
        define_shift_operation_values is called and ts_data is set.
        Shutdown durations must be NaN if device_shutdown is False.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation("ofw_min_002", "Minor op 2", device_shutdown=False)
        operations = [op]

        m_recycle.return_value = op.id
        m_reuse_file.return_value = None
        m_reuse_file.__bool__.return_value = False

        m_modify_distance.return_value = 3.5

        # Working shifts: one shift only
        op_working_shifts = {"number_shifts_main": 1, "number_shifts_last": 0}
        data_working_shifts = {"dummy": "data"}
        m_working_shifts.return_value = (op_working_shifts, data_working_shifts)

        # Workability df
        df_workability = pd.DataFrame({"ok": [True, True]}, index=self.df_metocean.index[:2])
        m_workability.return_value = df_workability

        # Schedule df from define_shift_operation_values
        oper_sched_raw = pd.DataFrame(
            {"dur_total": [1.0, 2.0]}, index=self.df_metocean.index[:2]
        )
        m_define_shift.return_value = oper_sched_raw

        # convert_stringtime returns the same df
        m_convert_time.side_effect = lambda df: df

        # create_timeseries_data returns a sentinel
        m_create_ts.return_value = "TS_DATA_OK"

        opeartion_minor_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            operations_corr_minor=operations,
            inputs_tseries=self.inputs_tseries,
            Config=self.Config,
        )

        # modify_distance called
        m_modify_distance.assert_called_once_with(
            Config=self.Config,
            operation=op,
            default_distance=self.inputs_tseries.distance["value"],
        )

        # working_shifts called with proper args
        m_working_shifts.assert_called_once()
        _, kwargs_ws = m_working_shifts.call_args
        self.assertIs(kwargs_ws["operation"], op)
        self.assertEqual(
            kwargs_ws["duration_shift"], self.inputs_tseries.shift_duration["value"]
        )
        self.assertEqual(kwargs_ws["transit"], 3.5)
        self.assertEqual(
            kwargs_ws["transit_between_devices"],
            self.inputs_tseries.find_time_between_devices(op.id),
        )
        self.assertTrue(kwargs_ws["minor_op"])

        # workability called
        op_dir = os.path.join(self.operation_dir, op.id)
        m_workability.assert_called_once_with(
            operation=op, df_metocean=self.df_metocean, out_dir=op_dir
        )
        
        # YAML updates
        m_yaml_each.assert_called_once_with(
            file_dir=op_dir, file_name="attributes.yaml", data=op_working_shifts, operation_id = 'ofw_min_002'
        )
        m_yaml_update.assert_called_once_with(
            file_dir=op_dir,
            file_name="attributes.yaml",
            data=data_working_shifts,
            operation_id='ofw_min_002'
        )

        # define_shift_operation_values called with NaN shutdowns
        m_define_shift.assert_called_once()
        _, kwargs_def = m_define_shift.call_args
        self.assertIs(kwargs_def["operation"], op)
        self.assertIs(kwargs_def["df_metocean"], self.df_metocean)
        self.assertIs(kwargs_def["df_workability"], df_workability)
        self.assertEqual(kwargs_def["shift_data"], op_working_shifts)
        self.assertEqual(kwargs_def["transit_duration"], 3.5)
        # shutdowns must be NaN because device_shutdown=False
        self.assertTrue(pd.isna(kwargs_def["shutdown_wtg"]))
        self.assertTrue(pd.isna(kwargs_def["shutdown_wec"]))
        self.assertTrue(pd.isna(kwargs_def["shutdown_pv"]))

        # convert_stringtime + create_timeseries_data
        m_convert_time.assert_called_once_with(oper_sched_raw)
        m_create_ts.assert_called_once_with(op, oper_sched_raw, op_dir)
        self.assertEqual(op.ts_data, "TS_DATA_OK")

    # -------- 3 -bis) Device shutdown True, type-specific assignment (ofw/opv/owc) --------
    @skip_if_check_files_present
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.tqdm"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.check_files"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.recycle_other_oper_scheduler"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.modify_distance"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.working_shifts"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.workability"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.yaml_manager.update_yaml_each_attribute"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.yaml_manager.update_yaml"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.define_shift_operation_values"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.aux_functions.convert_stringtime"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.OperationTimeSeriesData.create_timeseries_data"
    )
    def test_shutdown_type_branches_ofw_opv_owc_bis(
        self,
        m_create_ts,
        m_convert_time,
        m_define_shift,
        m_yaml_update,
        m_yaml_each,
        m_workability,
        m_working_shifts,
        m_modify_distance,
        m_recycle,
        m_reuse_file,
        m_tqdm,
    ):
        """
        When device_shutdown is True, shutdown_* must be set according to the id prefix:
        - 'ofw' -> shutdown_wtg
        - 'owc' -> shutdown_wec
        - 'opv' -> shutdown_pv
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable
        m_reuse_file.return_value = None
        m_reuse_file.__bool__.return_value = False
        m_modify_distance.return_value = 1.0
        op_working_shifts = {"number_shifts_main": 1, "number_shifts_last": 0}
        data_working_shifts = {}
        m_working_shifts.return_value = (op_working_shifts, data_working_shifts)
        df_workability = pd.DataFrame({"ok": [True]}, index=self.df_metocean.index[:1])
        m_workability.return_value = df_workability
        oper_sched_raw = pd.DataFrame({"dur_total": [1.0]}, index=self.df_metocean.index[:1])
        m_define_shift.return_value = oper_sched_raw
        m_convert_time.side_effect = lambda df: df
        m_create_ts.return_value = "TS_DATA"

        # We test three operations
        ops = [
            DummyOperation("ofw_min_003", "Minor ofw", duration_net=4.0, device_shutdown=True),
            DummyOperation("owc_min_004", "Minor owc", duration_net=6.0, device_shutdown=True),
            DummyOperation("opv_min_005", "Minor opv", duration_net=8.0, device_shutdown=True),
        ]

        # recycle_other_oper_scheduler simply returns its own op.id
        m_recycle.side_effect = lambda minor_oper_dict, hash_to_key, operation, attribute_list: operation.id

        opeartion_minor_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            operations_corr_minor=ops,
            inputs_tseries=self.inputs_tseries,
            Config=self.Config,
        )

        # We expect define_shift_operation_values invoked three times
        self.assertEqual(m_define_shift.call_count, 3)

        # Extract shutdown arguments per call
        calls = m_define_shift.call_args_list
        shutdown_sets = []
        for call in calls:
            _, kwargs_def = call
            shutdown_sets.append(
                (
                    kwargs_def["shutdown_wtg"],
                    kwargs_def["shutdown_wec"],
                    kwargs_def["shutdown_pv"],
                )
            )

        # For ofw_min_003 (duration_net=4.0) -> shutdown_wtg=4.0
        self.assertAlmostEqual(shutdown_sets[0][0], 4.0)
        self.assertTrue(pd.isna(shutdown_sets[0][1]))
        self.assertTrue(pd.isna(shutdown_sets[0][2]))

        # For owc_min_004 -> shutdown_wec=6.0
        self.assertTrue(pd.isna(shutdown_sets[1][0]))
        self.assertAlmostEqual(shutdown_sets[1][1], 6.0)
        self.assertTrue(pd.isna(shutdown_sets[1][2]))

        # For opv_min_005 -> shutdown_pv=8.0
        self.assertTrue(pd.isna(shutdown_sets[2][0]))
        self.assertTrue(pd.isna(shutdown_sets[2][1]))
        self.assertAlmostEqual(shutdown_sets[2][2], 8.0)

    # -------- 4 -bis) RuntimeError when more than one shift is required --------
    @skip_if_check_files_present
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.tqdm"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.check_files"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.recycle_other_oper_scheduler"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.modify_distance"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.working_shifts"
    )
    def test_runtime_error_when_more_than_one_shift_bis(
        self,
        m_working_shifts,
        m_modify_distance,
        m_recycle,
        m_reuse_file,
        m_tqdm,
    ):
        """
        If number_shifts_main + number_shifts_last > 1, a RuntimeError must be raised.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation("ofw_min_006", "Too long minor op", device_shutdown=False)
        operations = [op]

        m_reuse_file.return_value = None
        m_reuse_file.__bool__.return_value = False
        m_recycle.return_value = op.id
        m_modify_distance.return_value = 2.0

        # Two shifts in total -> triggers RuntimeError
        op_working_shifts = {"number_shifts_main": 1, "number_shifts_last": 1}
        data_working_shifts = {}
        m_working_shifts.return_value = (op_working_shifts, data_working_shifts)

        with self.assertRaises(RuntimeError) as ctx:
            opeartion_minor_manager(
                operation_dir=self.operation_dir,
                df_metocean=self.df_metocean,
                operations_corr_minor=operations,
                inputs_tseries=self.inputs_tseries,
                Config=self.Config,
            )

        self.assertIn("operation too long, consider defining as CorrectiveMajor", str(ctx.exception))

    # -------- 5-bis) InterruptedError with specific message is swallowed --------
    @skip_if_check_files_present
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.tqdm"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.check_files"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.recycle_other_oper_scheduler"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.modify_distance"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.working_shifts"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.workability"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.yaml_manager.update_yaml_each_attribute"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.yaml_manager.update_yaml"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.define_shift_operation_values"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.aux_functions.convert_stringtime"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_minor_manager.OperationTimeSeriesData.create_timeseries_data"
    )
    def test_interrupted_error_is_caught_bis(
        self,
        m_create_ts,
        m_convert_time,
        m_define_shift,
        m_yaml_update,
        m_yaml_each,
        m_workability,
        m_working_shifts,
        m_modify_distance,
        m_recycle,
        m_reuse_file,
        m_tqdm,
    ):
        """
        If define_shift_operation_values raises the specific InterruptedError,
        it must be swallowed and ts_data left as None.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation("ofw_min_007", "Interrupted minor op", device_shutdown=False)
        operations = [op]

        m_reuse_file.return_value = None
        m_reuse_file.__bool__.return_value = False
        m_recycle.return_value = op.id
        m_modify_distance.return_value = 1.0

        op_working_shifts = {"number_shifts_main": 1, "number_shifts_last": 0}
        data_working_shifts = {}
        m_working_shifts.return_value = (op_working_shifts, data_working_shifts)

        df_workability = pd.DataFrame({"ok": [True]}, index=self.df_metocean.index[:1])
        m_workability.return_value = df_workability

        m_define_shift.side_effect = InterruptedError(
            "The operation can never occur. OLCs may be to resctric."
        )

        # Should not raise
        opeartion_minor_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            operations_corr_minor=operations,
            inputs_tseries=self.inputs_tseries,
            Config=self.Config,
        )

        # No TS data created
        m_create_ts.assert_not_called()
        self.assertIsNone(op.ts_data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
