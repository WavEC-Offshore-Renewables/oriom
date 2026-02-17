# tests_operations_inspection_port_manager

import os
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import importlib.util

import pandas as pd

from oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager import (
    creation_data_working_shift_port,
    operation_inspect_port_manager,
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
    """Minimal operation object for testing InspectionPort behaviour."""

    def __init__(self, op_id, name, dur_per_device, intervened_devices):
        self.id = op_id
        self.name = name
        self.dur_per_device = float(dur_per_device)
        self.intervened_devices = int(intervened_devices)
        self.shift_assigned = None
        self.ts_data = None

    def assign_shift_attributes(self, data):
        """Store assigned shift data for inspection."""
        self.shift_assigned = data


class TestCreationDataWorkingShiftPort(unittest.TestCase):
    def test_exact_multiple_of_shift_duration(self):
        """
        When total_hours is an exact multiple of shift_duration:
        - all work is done in 'main' shifts
        - no 'last' shift is needed.
        """
        op = SimpleNamespace(dur_per_device=24.0)  # total_hours = 24
        shift_duration = 8.0                      # n_shifts = 3.0

        result = creation_data_working_shift_port(op, shift_duration)

        self.assertEqual(result["number_shifts_main"], 3)
        self.assertEqual(result["number_shifts_last"], 0)
        self.assertEqual(result["duration_shift_main"], 8.0)
        self.assertEqual(result["duration_shift_last"], 0.0)

    def test_fractional_number_of_shifts(self):
        """
        When total_hours is not an exact multiple:
        - integer part → 'main' shifts of full duration_shift
        - remainder → one 'last' shift of h * duration_shift_main (rounded to 1 decimal).
        """
        op = SimpleNamespace(dur_per_device=10.0)  # total_hours = 10
        shift_duration = 8.0                      # n_shifts = 1.25

        result = creation_data_working_shift_port(op, shift_duration)

        # n_shifts = 1.25 -> main=1, h=0.25
        self.assertEqual(result["number_shifts_main"], 1)
        self.assertEqual(result["number_shifts_last"], 1)
        self.assertEqual(result["duration_shift_main"], 8.0)
        # last shift duration = 0.25 * 8.0 = 2.0
        self.assertAlmostEqual(result["duration_shift_last"], 2.0, places=3)

    def test_duration_less_than_one_shift(self):
        """
        Edge case: total_hours < shift_duration.
        The current implementation:
        - number_shifts_main = 0
        - number_shifts_last = 1 (because h != 0)
        - duration_shift_main = 0
        - duration_shift_last = h * duration_shift_main = 0
        This test documents that behaviour.
        """
        op = SimpleNamespace(dur_per_device=5.0)  # total_hours = 5
        shift_duration = 8.0                      # n_shifts = 0.625

        result = creation_data_working_shift_port(op, shift_duration)

        self.assertEqual(result["number_shifts_main"], 0)
        self.assertEqual(result["number_shifts_last"], 1)
        self.assertEqual(result["duration_shift_main"], 0.0)
        self.assertAlmostEqual(result["duration_shift_last"], 0.0, places=3)


class TestOperationInspectPortManager(unittest.TestCase):
    def setUp(self):
        # Temporary directory for operation_dir
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_ctx.cleanup)
        self.operation_dir = self.tmp_ctx.name

        # Minimal metocean dataframe (content irrelevant because workability is mocked)
        self.df_metocean = pd.DataFrame({"hs": [1.0, 1.2]}, index=pd.date_range("2020-01-01", periods=2, freq="H"))

    @skip_if_no_check_files
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.tqdm")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.define_shift_operation_values")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.workability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.yaml_manager.update_yaml")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.yaml_manager.update_yaml_each_attribute")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.check_files.reuse_file_exist")
    def test_skip_operation_if_schedule_already_exists(
        self,
        m_reuse_file,
        m_update_each,
        m_update_yaml,
        m_workability,
        m_define_shift,
        m_tqdm,
    ):
        """
        If reuse_file_exist returns True, the function must:
        - skip workability computation
        - skip YAML updates
        - skip define_shift_operation_values
        - not assign ts_data.
        """
        # tqdm mock: just return an iterable over the list
        m_tqdm.side_effect = lambda it, *a, **k: it

        # One inspection at port, already scheduled
        op = DummyOperation("ofw_op1", "PortInsp", dur_per_device=10.0, intervened_devices=2)
        m_reuse_file.return_value = True

        operation_inspect_port_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            duration_shift=12.0,
            operations_inspect_port=[op],
        )

        m_workability.assert_not_called()
        m_update_each.assert_not_called()
        m_update_yaml.assert_not_called()
        m_define_shift.assert_not_called()
        self.assertIsNone(op.ts_data)

    @skip_if_no_check_files
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.tqdm")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.OperationTimeSeriesData.create_timeseries_data")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.define_shift_operation_values")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.workability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.yaml_manager.update_yaml")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.yaml_manager.update_yaml_each_attribute")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.check_files.reuse_file_exist")
    def test_create_schedule_and_tsdata_when_not_existing(
        self,
        m_reuse_file,
        m_update_each,
        m_update_yaml,
        m_workability,
        m_define_shift,
        m_create_tsdata,
        m_tqdm,
    ):
        """
        When no schedule exists for an inspection:
        - workability is called
        - shift attributes are computed and assigned
        - YAML updates are called with correct data
        - define_shift_operation_values is called with correct arguments
        - OperationTimeSeriesData.create_timeseries_data is called and its result is assigned to operation.ts_data.
        """
        m_tqdm.side_effect = lambda it, *a, **k: it

        op = DummyOperation("ofw_op1", "PortInsp", dur_per_device=10.0, intervened_devices=2)

        # No existing schedule
        m_reuse_file.return_value = False

        # Mock workability to return a simple dataframe
        df_workability = pd.DataFrame(
            {"work": [True, True]},
            index=pd.date_range("2020-01-01", periods=2, freq="H"),
        )
        m_workability.return_value = df_workability

        # Mock define_shift_operation_values to return a dummy schedule
        oper_sched = pd.DataFrame({"dur_total": [5.0, 5.0]}, index=df_workability.index)
        m_define_shift.return_value = oper_sched

        # Mock TS data creation
        m_create_tsdata.return_value = "TSDATA"

        duration_shift = 8.0  # to produce non-trivial main/last shift split

        operation_inspect_port_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            duration_shift=duration_shift,
            operations_inspect_port=[op],
        )

        op_dir = os.path.join(self.operation_dir, op.id)
        file_name_schedule = "operation_schedule.csv"
        out_dir_schedule = os.path.join(op_dir, file_name_schedule)

        # 1) workability called correctly
        m_workability.assert_called_once_with(
            operation=op,
            df_metocean=self.df_metocean,
            out_dir=op_dir,
        )

        # 2) check shift data that should have been computed
        # total_hours = 1 * 10; shift_duration = 8 -> n_shifts = 1.25
        expected_shift_data = {
            "number_shifts_main": 1,
            "number_shifts_last": 1,
            "duration_shift_main": duration_shift,
            "duration_shift_last": 2.0,  # 0.25 * 8
        }

        # assign_shift_attributes must have been called (stored in op.shift_assigned)
        self.assertEqual(op.shift_assigned, expected_shift_data)

        # 3) YAML updates
        m_update_each.assert_called_once_with(
            file_dir=op_dir,
            file_name="attributes.yaml",
            data=expected_shift_data,
        )

        expected_data_new = {
            "shift": {
                "number": expected_shift_data["number_shifts_main"],
                "duration": expected_shift_data["duration_shift_main"],
            },
            "last_shift": {
                "number": expected_shift_data["number_shifts_last"],
                "duration": expected_shift_data["duration_shift_last"],
            },
        }

        m_update_yaml.assert_called_once_with(
            file_dir=op_dir,
            file_name="attributes.yaml",
            data=expected_data_new,
            data_key="working_shifts",
        )

        # 4) define_shift_operation_values called with expected arguments
        # shutdown_wtg should be non-zero because op.id starts with 'ofw'
        expected_shutdown_wtg = op.dur_per_device * op.intervened_devices
        m_define_shift.assert_called_once()
        _, kwargs = m_define_shift.call_args

        self.assertIs(kwargs["df_metocean"], self.df_metocean)
        self.assertIs(kwargs["operation"], op)
        self.assertTrue(kwargs["df_workability"].equals(df_workability))
        self.assertEqual(kwargs["shift_data"], expected_shift_data)
        self.assertEqual(kwargs["transit_duration"], 0)
        self.assertEqual(kwargs["shutdown_wtg"], expected_shutdown_wtg)
        self.assertEqual(kwargs["shutdown_wec"], 0)
        self.assertEqual(kwargs["shutdown_pv"], 0)
        self.assertEqual(kwargs["out_dir"], out_dir_schedule)

        # 5) TS data creation and assignment
        m_create_tsdata.assert_called_once_with(op, oper_sched, op_dir)
        self.assertEqual(op.ts_data, "TSDATA")


    @skip_if_check_files_present
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.tqdm")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.OperationTimeSeriesData.create_timeseries_data")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.define_shift_operation_values")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.workability")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.yaml_manager.update_yaml")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.yaml_manager.update_yaml_each_attribute")
    @patch("oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager.check_files")
    def test_create_schedule_and_tsdata_when_not_existing_bis(
        self,
        m_reuse_file,
        m_update_each,
        m_update_yaml,
        m_workability,
        m_define_shift,
        m_create_tsdata,
        m_tqdm,
    ):
        """
        When no schedule exists for an inspection:
        - workability is called
        - shift attributes are computed and assigned
        - YAML updates are called with correct data
        - define_shift_operation_values is called with correct arguments
        - OperationTimeSeriesData.create_timeseries_data is called and its result is assigned to operation.ts_data.
        """
        m_tqdm.side_effect = lambda it, *a, **k: it

        op = DummyOperation("ofw_op1", "PortInsp", dur_per_device=10.0, intervened_devices=2)

        # No existing schedule
        m_reuse_file.return_value = None
        m_reuse_file.__bool__.return_value = False

        # Mock workability to return a simple dataframe
        df_workability = pd.DataFrame(
            {"work": [True, True]},
            index=pd.date_range("2020-01-01", periods=2, freq="H"),
        )
        m_workability.return_value = df_workability

        # Mock define_shift_operation_values to return a dummy schedule
        oper_sched = pd.DataFrame({"dur_total": [5.0, 5.0]}, index=df_workability.index)
        m_define_shift.return_value = oper_sched

        # Mock TS data creation
        m_create_tsdata.return_value = "TSDATA"

        duration_shift = 8.0  # to produce non-trivial main/last shift split

        operation_inspect_port_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            duration_shift=duration_shift,
            operations_inspect_port=[op],
        )

        op_dir = os.path.join(self.operation_dir, op.id)
        file_name_schedule = "operation_schedule.csv"
        out_dir_schedule = os.path.join(op_dir, file_name_schedule)

        # 1) workability called correctly
        m_workability.assert_called_once_with(
            operation=op,
            df_metocean=self.df_metocean,
            out_dir=op_dir,
        )

        # 2) check shift data that should have been computed
        # total_hours = 1 * 10; shift_duration = 8 -> n_shifts = 1.25
        expected_shift_data = {
            "number_shifts_main": 1,
            "number_shifts_last": 1,
            "duration_shift_main": duration_shift,
            "duration_shift_last": 2.0,  # 0.25 * 8
        }

        # assign_shift_attributes must have been called (stored in op.shift_assigned)
        self.assertEqual(op.shift_assigned, expected_shift_data)

        # 3) YAML updates
        m_update_each.assert_called_once_with(
            file_dir=op_dir,
            file_name="attributes.yaml",
            data=expected_shift_data,
        )

        expected_data_new = {
            "shift": {
                "number": expected_shift_data["number_shifts_main"],
                "duration": expected_shift_data["duration_shift_main"],
            },
            "last_shift": {
                "number": expected_shift_data["number_shifts_last"],
                "duration": expected_shift_data["duration_shift_last"],
            },
        }

        m_update_yaml.assert_called_once_with(
            file_dir=op_dir,
            file_name="attributes.yaml",
            data=expected_data_new,
            data_key="working_shifts",
        )

        # 4) define_shift_operation_values called with expected arguments
        # shutdown_wtg should be non-zero because op.id starts with 'ofw'
        expected_shutdown_wtg = op.dur_per_device * op.intervened_devices
        m_define_shift.assert_called_once()
        _, kwargs = m_define_shift.call_args

        self.assertIs(kwargs["df_metocean"], self.df_metocean)
        self.assertIs(kwargs["operation"], op)
        self.assertTrue(kwargs["df_workability"].equals(df_workability))
        self.assertEqual(kwargs["shift_data"], expected_shift_data)
        self.assertEqual(kwargs["transit_duration"], 0)
        self.assertEqual(kwargs["shutdown_wtg"], expected_shutdown_wtg)
        self.assertEqual(kwargs["shutdown_wec"], 0)
        self.assertEqual(kwargs["shutdown_pv"], 0)
        self.assertEqual(kwargs["out_dir"], out_dir_schedule)

        # 5) TS data creation and assignment
        m_create_tsdata.assert_called_once_with(op, oper_sched, op_dir)
        self.assertEqual(op.ts_data, "TSDATA")

if __name__ == "__main__":
    unittest.main(verbosity=2)
