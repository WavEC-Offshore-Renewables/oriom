# test_operations_inspection_site_manager.py

import os
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util

import pandas as pd

from oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager import (
    inspect_site_manager,
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
    """Minimal InspectionSite-like object for testing inspect_site_manager."""

    def __init__(
        self,
        op_id: str,
        name: str,
        dur_per_device: float = 10.0,
        intervened_wtg: int = 0,
        intervened_wec: int = 0,
        intervened_pv: int = 0,
        device_shutdown: bool = True,
    ):
        self.id = op_id
        self.name = name
        self.dur_per_device = float(dur_per_device)
        self.intervened_wtg = intervened_wtg
        self.intervened_wec = intervened_wec
        self.intervened_pv = intervened_pv
        self.device_shutdown = device_shutdown

        # Attributes used in ATTRIBUTE_LIST_REUSE
        self.hs = None
        self.tp = None
        self.ws = None
        self.ws_hub = None
        self.cs = None
        self.light = None
        self.vessel1_id = "v1"
        self.rov_drone = None
        self.technicians_per_device = 1
        self.vessel2_id = None
        self.rov = None
        self.overnight = False
        self.double_shift = False

        # Extra attributes used in manager
        self.to_group_with = None

        # Filled by manager
        self.shift_assigned = None
        self.ts_data = None

    def assign_shift_attributes(self, data):
        """Record shift data assigned by the manager."""
        self.shift_assigned = data


class DummyInputsTseries:
    """Minimal InputsTimeSeries-like object used by inspect_site_manager."""

    def __init__(self, distance=5.0, shift_duration=8.0, time_between_devices=1.5):
        self._time_between_devices = time_between_devices
        self.distance = {"value": distance}
        self.shift_duration = {"value": shift_duration}

    def find_time_between_devices(self, operation_obj_id: str) -> float:
        """Return a constant time between devices for testing."""
        return self._time_between_devices


class TestInspectSiteManager(unittest.TestCase):
    def setUp(self):
        # Temporary dir to simulate operation_dir
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_ctx.cleanup)
        self.operation_dir = self.tmp_ctx.name

        # Simple metocean DataFrame (content not relevant because workability is mocked)
        self.df_metocean = pd.DataFrame(
            {"hs": [1.0, 1.1, 1.2]},
            index=pd.date_range("2020-01-01", periods=3, freq="H"),
        )

        # Dummy inputs and config
        self.inputs_tseries = DummyInputsTseries(distance=10.0, shift_duration=12.0)
        self.Config = SimpleNamespace()  # not used directly because modify_distance is mocked

    # ---------- 1) Existing schedule: path should short-circuit ----------
    @skip_if_no_check_files
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.tqdm"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.check_files.reuse_file_exist"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.recycle_other_oper_scheduler"
    )
    def test_skip_when_schedule_already_exists(
        self, m_recycle, m_reuse_file, m_tqdm
    ):
        """
        If reuse_file_exist returns True, the manager must:
        - not call workability, working_shifts, YAML updates, or define_shift_operation_values
        - leave operation.ts_data as None.
        """
        # tqdm should just iterate transparently
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation("ofw_insp_1", "Inspection 1")
        operations = [op]

        # similar_inspection_id returned by recycler
        m_recycle.return_value = op.id
        # Schedule already exists
        m_reuse_file.return_value = True

        with patch(
            "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.workability"
        ) as m_workability, patch(
            "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.working_shifts"
        ) as m_working_shifts, patch(
            "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.define_shift_operation_values"
        ) as m_define_shift, patch(
            "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.yaml_manager.update_yaml_each_attribute"
        ) as m_update_each, patch(
            "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.yaml_manager.update_yaml"
        ) as m_update_yaml:
            inspect_site_manager(
                operation_dir=self.operation_dir,
                df_metocean=self.df_metocean,
                operations_inspect_site=operations,
                inputs_tseries=self.inputs_tseries,
                Config=self.Config,
            )

        # Check the short-circuit behaviour
        m_recycle.assert_called_once()  # we did try to recycle
        m_reuse_file.assert_called_once()  # but reused an existing schedule

        m_workability.assert_not_called()
        m_working_shifts.assert_not_called()
        m_define_shift.assert_not_called()
        m_update_each.assert_not_called()
        m_update_yaml.assert_not_called()

        # No ts_data should be assigned
        self.assertIsNone(op.ts_data)
        self.assertIsNone(op.shift_assigned)

    # ---------- 2) Full path: new schedule is created ----------
    @skip_if_no_check_files
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.tqdm"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.OperationTimeSeriesData.create_timeseries_data"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.define_shift_operation_values"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.workability"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.yaml_manager.update_yaml"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.yaml_manager.update_yaml_each_attribute"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.working_shifts"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.modify_distance"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.check_files.reuse_file_exist"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.recycle_other_oper_scheduler"
    )
    def test_create_schedule_when_not_existing(
        self,
        m_recycle,
        m_reuse_file,
        m_modify_distance,
        m_working_shifts,
        m_update_each,
        m_update_yaml,
        m_workability,
        m_define_shift,
        m_create_tsdata,
        m_tqdm,
    ):
        """
        When no schedule exists:
        - distance and working_shifts are computed
        - shift attributes are assigned to the operation
        - YAML files are updated
        - workability and define_shift_operation_values are called
        - OperationTimeSeriesData.create_timeseries_data is called and ts_data is set.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation(
            "ofw_insp_1",
            "Inspection 1",
            dur_per_device=10.0,
            intervened_wtg=2,
            intervened_wec=0,
            intervened_pv=0,
            device_shutdown=True,
        )
        operations = [op]

        # No existing schedule
        m_recycle.return_value = op.id  # first time, it will just map to itself
        m_reuse_file.return_value = False

        # modify_distance returns a given transit duration
        m_modify_distance.return_value = 3.5

        # working_shifts returns (op_working_shifts, data_working_shifts)
        op_working_shifts = {
            "number_shifts_main": 1,
            "number_shifts_last": 1,
            "duration_shift_main": 12.0,
            "duration_shift_last": 4.0,
        }
        data_working_shifts = {
            "shift": {"number": 1, "duration": 12.0},
            "last_shift": {"number": 1, "duration": 4.0},
        }
        m_working_shifts.return_value = (op_working_shifts, data_working_shifts)

        # workability returns simple mask dataframe
        df_workability = pd.DataFrame(
            {"ok": [True, True, False]},
            index=self.df_metocean.index,
        )
        m_workability.return_value = df_workability

        # define_shift_operation_values returns a dummy schedule
        oper_sched = pd.DataFrame(
            {"dur_total": [5.0, 6.0, 7.0]},
            index=self.df_metocean.index,
        )
        m_define_shift.return_value = oper_sched

        # create_timeseries_data returns a sentinel
        m_create_tsdata.return_value = "TS_DATA"

        inspect_site_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            operations_inspect_site=operations,
            inputs_tseries=self.inputs_tseries,
            Config=self.Config,
        )

        op_dir = os.path.join(self.operation_dir, op.id)
        file_name_schedule = "operation_schedule.csv"
        out_dir_schedule = os.path.join(op_dir, file_name_schedule)

        # 1) distance and working_shifts are called with expected arguments
        m_modify_distance.assert_called_once_with(
            Config=self.Config,
            operation=op,
            default_distance=self.inputs_tseries.distance["value"],
        )

        m_working_shifts.assert_called_once()
        _, kw_ws = m_working_shifts.call_args
        self.assertIs(kw_ws["operation"], op)
        self.assertEqual(kw_ws["duration_shift"], self.inputs_tseries.shift_duration["value"])
        self.assertEqual(kw_ws["transit"], m_modify_distance.return_value)
        self.assertEqual(kw_ws["transit_between_devices"], self.inputs_tseries._time_between_devices)
        self.assertEqual(kw_ws["operation_to_group_with"], op.to_group_with)

        # 2) shift attributes assigned to operation
        self.assertEqual(op.shift_assigned, op_working_shifts)

        # 3) YAML updates called correctly
        m_update_each.assert_called_once()

        _, kwargs = m_update_each.call_args

        self.assertEqual(kwargs["file_dir"], op_dir)
        self.assertEqual(kwargs["file_name"], "attributes.yaml")
        self.assertEqual(kwargs["data"], op_working_shifts)

        m_update_yaml.assert_called_once()

        _, kwargs = m_update_yaml.call_args

        self.assertEqual(kwargs["file_dir"], op_dir)
        self.assertEqual(kwargs["file_name"], "attributes.yaml")
        self.assertEqual(kwargs["data"], data_working_shifts)
        self.assertEqual(kwargs["data_key"], "working_shifts")

        # 4) shutdown durations computed correctly
        expected_shutdown_wtg = op.dur_per_device * op.intervened_wtg
        expected_shutdown_wec = op.dur_per_device * op.intervened_wec
        expected_shutdown_pv = op.dur_per_device * op.intervened_pv

        # workability called with op and df_metocean
        m_workability.assert_called_once_with(
            operation=op,
            df_metocean=self.df_metocean,
            out_dir=op_dir,
        )

        # define_shift_operation_values called with correct parameters
        m_define_shift.assert_called_once()
        _, kw_ds = m_define_shift.call_args

        self.assertIs(kw_ds["df_metocean"], self.df_metocean)
        self.assertIs(kw_ds["operation"], op)
        self.assertTrue(kw_ds["df_workability"].equals(df_workability))
        self.assertEqual(kw_ds["shift_data"], op_working_shifts)
        self.assertEqual(kw_ds["transit_duration"], m_modify_distance.return_value)
        self.assertEqual(kw_ds["shutdown_wtg"], expected_shutdown_wtg)
        self.assertEqual(kw_ds["shutdown_wec"], expected_shutdown_wec)
        self.assertEqual(kw_ds["shutdown_pv"], expected_shutdown_pv)
        self.assertEqual(kw_ds["duration_shift"], self.inputs_tseries.shift_duration["value"])
        self.assertEqual(kw_ds["out_dir"], out_dir_schedule)

        # 5) TS data creation and assignment
        m_create_tsdata.assert_called_once_with(op, oper_sched, op_dir)
        self.assertEqual(op.ts_data, "TS_DATA")


# ---------- 2-bis) Full path: new schedule is created ----------
    @skip_if_check_files_present
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.tqdm"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.OperationTimeSeriesData.create_timeseries_data"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.define_shift_operation_values"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.workability"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.yaml_manager.update_yaml"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.yaml_manager.update_yaml_each_attribute"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.working_shifts"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.modify_distance"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.check_files"
    )
    @patch(
        "oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager.recycle_other_oper_scheduler"
    )
    def test_create_schedule_when_not_existing_bis(
        self,
        m_recycle,
        m_reuse_file,
        m_modify_distance,
        m_working_shifts,
        m_update_each,
        m_update_yaml,
        m_workability,
        m_define_shift,
        m_create_tsdata,
        m_tqdm,
    ):
        """
        When no schedule exists:
        - distance and working_shifts are computed
        - shift attributes are assigned to the operation
        - YAML files are updated
        - workability and define_shift_operation_values are called
        - OperationTimeSeriesData.create_timeseries_data is called and ts_data is set.
        """
        m_tqdm.side_effect = lambda iterable, *a, **k: iterable

        op = DummyOperation(
            "ofw_insp_1",
            "Inspection 1",
            dur_per_device=10.0,
            intervened_wtg=2,
            intervened_wec=0,
            intervened_pv=0,
            device_shutdown=True,
        )
        operations = [op]

        # No existing schedule
        m_recycle.return_value = op.id  # first time, it will just map to itself
        m_reuse_file.return_value = None
        m_reuse_file.__bool__.return_value = False

        # modify_distance returns a given transit duration
        m_modify_distance.return_value = 3.5

        # working_shifts returns (op_working_shifts, data_working_shifts)
        op_working_shifts = {
            "number_shifts_main": 1,
            "number_shifts_last": 1,
            "duration_shift_main": 12.0,
            "duration_shift_last": 4.0,
        }
        data_working_shifts = {
            "shift": {"number": 1, "duration": 12.0},
            "last_shift": {"number": 1, "duration": 4.0},
        }
        m_working_shifts.return_value = (op_working_shifts, data_working_shifts)

        # workability returns simple mask dataframe
        df_workability = pd.DataFrame(
            {"ok": [True, True, False]},
            index=self.df_metocean.index,
        )
        m_workability.return_value = df_workability

        # define_shift_operation_values returns a dummy schedule
        oper_sched = pd.DataFrame(
            {"dur_total": [5.0, 6.0, 7.0]},
            index=self.df_metocean.index,
        )
        m_define_shift.return_value = oper_sched

        # create_timeseries_data returns a sentinel
        m_create_tsdata.return_value = "TS_DATA"

        inspect_site_manager(
            operation_dir=self.operation_dir,
            df_metocean=self.df_metocean,
            operations_inspect_site=operations,
            inputs_tseries=self.inputs_tseries,
            Config=self.Config,
        )

        op_dir = os.path.join(self.operation_dir, op.id)
        file_name_schedule = "operation_schedule.csv"
        out_dir_schedule = os.path.join(op_dir, file_name_schedule)

        # 1) distance and working_shifts are called with expected arguments
        m_modify_distance.assert_called_once_with(
            Config=self.Config,
            operation=op,
            default_distance=self.inputs_tseries.distance["value"],
        )

        m_working_shifts.assert_called_once()
        _, kw_ws = m_working_shifts.call_args
        self.assertIs(kw_ws["operation"], op)
        self.assertEqual(kw_ws["duration_shift"], self.inputs_tseries.shift_duration["value"])
        self.assertEqual(kw_ws["transit"], m_modify_distance.return_value)
        self.assertEqual(kw_ws["transit_between_devices"], self.inputs_tseries._time_between_devices)
        self.assertEqual(kw_ws["operation_to_group_with"], op.to_group_with)

        # 2) shift attributes assigned to operation
        self.assertEqual(op.shift_assigned, op_working_shifts)

        # 3) YAML updates called correctly
        m_update_each.assert_called_once_with(
            file_dir=op_dir,
            file_name="attributes.yaml",
            data=op_working_shifts,
            operation_id='ofw_insp_1'
        )
        m_update_yaml.assert_called_once_with(
            file_dir=op_dir,
            file_name="attributes.yaml",
            data=data_working_shifts,
            data_key="working_shifts",
            operation_id='ofw_insp_1'
        )

        # 4) shutdown durations computed correctly
        expected_shutdown_wtg = op.dur_per_device * op.intervened_wtg
        expected_shutdown_wec = op.dur_per_device * op.intervened_wec
        expected_shutdown_pv = op.dur_per_device * op.intervened_pv

        # workability called with op and df_metocean
        m_workability.assert_called_once_with(
            operation=op,
            df_metocean=self.df_metocean,
            out_dir=op_dir,
        )

        # define_shift_operation_values called with correct parameters
        m_define_shift.assert_called_once()
        _, kw_ds = m_define_shift.call_args

        self.assertIs(kw_ds["df_metocean"], self.df_metocean)
        self.assertIs(kw_ds["operation"], op)
        self.assertTrue(kw_ds["df_workability"].equals(df_workability))
        self.assertEqual(kw_ds["shift_data"], op_working_shifts)
        self.assertEqual(kw_ds["transit_duration"], m_modify_distance.return_value)
        self.assertEqual(kw_ds["shutdown_wtg"], expected_shutdown_wtg)
        self.assertEqual(kw_ds["shutdown_wec"], expected_shutdown_wec)
        self.assertEqual(kw_ds["shutdown_pv"], expected_shutdown_pv)
        self.assertEqual(kw_ds["duration_shift"], self.inputs_tseries.shift_duration["value"])
        self.assertEqual(kw_ds["out_dir"], out_dir_schedule)

        # 5) TS data creation and assignment
        m_create_tsdata.assert_called_once_with(op, oper_sched, op_dir)
        self.assertEqual(op.ts_data, "TS_DATA")


if __name__ == "__main__":
    unittest.main(verbosity=2)
