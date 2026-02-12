# test_define_shift_operation_values.py

import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from logistic_tools.core.functions.operation_scheduler.define_shift_operation import (
    copy_row_wait_start,
    define_shift_operation_values,
)


def make_operation(op_id, name, has_tow_port=False):
    """
    Creates a minimal operation object with the required attributes.
    has_tow_port=True adds the attribute op_tow_port (used in the final branch).
    """
    op = SimpleNamespace(id=op_id, name=name)
    if has_tow_port:
        setattr(op, "op_tow_port", "dummy_tow_id")
    return op


class TestCopyRowWaitStart(unittest.TestCase):
    def test_basic_propagation(self):
        """
        Check that values are correctly propagated and that wait_start
        is decreased by 1 at each future timestep.
        """
        df = pd.DataFrame(
            {
                "datetime": [0, 1, 2, 3, 4],
                "wait_start": [2.0, 0.0, 0.0, 0.0, 0.0],
                "x": [10.0, 0.0, 0.0, 0.0, 0.0],
            },
            index=[0, 1, 2, 3, 4],
        )

        updated, last_idx, original_wait, success = copy_row_wait_start(
            df_op_values=df,
            ts=0,
            wait_start=2.0,
        )

        self.assertTrue(success)
        self.assertEqual(last_idx, 2)
        self.assertEqual(original_wait, 2.0)

        # row 0 unchanged
        self.assertEqual(updated.loc[0, "x"], 10.0)
        self.assertEqual(updated.loc[0, "wait_start"], 2.0)

        # rows 1 and 2 copy x and scale wait_start
        self.assertEqual(updated.loc[1, "x"], 10.0)
        self.assertEqual(updated.loc[2, "x"], 10.0)
        self.assertEqual(updated.loc[1, "wait_start"], 1.0)
        self.assertEqual(updated.loc[2, "wait_start"], 0.0)

    def test_reindex_when_indices_missing(self):
        """
        If the target indices do not exist, the function must reindex
        and create new rows, copying values into them.
        """
        df = pd.DataFrame(
            {
                "datetime": [0, 1, 2],
                "wait_start": [3.0, 0.0, 0.0],
                "x": [5.0, 0.0, 0.0],
            },
            index=[0, 1, 2],
        )

        updated, last_idx, original_wait, success = copy_row_wait_start(
            df_op_values=df,
            ts=0,
            wait_start=3.0,  # indices 1,2,3 will be needed
        )

        self.assertTrue(success)
        self.assertEqual(last_idx, 3)
        self.assertEqual(original_wait, 3.0)

        # check that indices 0..3 exist
        self.assertListEqual(sorted(updated.index.tolist()), [0, 1, 2, 3])

        # copied values
        for i, w in zip([1, 2, 3], [2.0, 1.0, 0.0]):
            self.assertEqual(updated.loc[i, "x"], 5.0)
            self.assertEqual(updated.loc[i, "wait_start"], w)

    def test_zero_wait_start_no_changes(self):
        """
        If wait_start is zero, no future rows should be modified.
        """
        df = pd.DataFrame(
            {
                "datetime": [0, 1, 2],
                "wait_start": [0.0, 0.0, 0.0],
                "x": [10.0, 0.0, 0.0],
            },
            index=[0, 1, 2],
        )

        updated, last_idx, original_wait, success = copy_row_wait_start(
            df_op_values=df,
            ts=0,
            wait_start=0.0,
        )

        self.assertTrue(success)
        self.assertEqual(last_idx, 0)
        self.assertEqual(original_wait, 0.0)

        # DataFrame must remain unchanged
        pd.testing.assert_frame_equal(updated, df)

    def test_invalid_wait_start_returns_failure(self):
        """
        If wait_start cannot be converted to int (e.g. NaN), the function
        must catch the ValueError and return success=False.
        """
        df = pd.DataFrame(
            {
                "datetime": [0, 1],
                "wait_start": [np.nan, 0.0],
                "x": [5.0, 0.0],
            },
            index=[0, 1],
        )

        updated, last_idx, original_wait, success = copy_row_wait_start(
            df_op_values=df,
            ts=0,
            wait_start=np.nan,
        )

        self.assertFalse(success)
        self.assertEqual(last_idx, 0)
        self.assertTrue(np.isnan(original_wait))
        # Original row should remain intact
        self.assertEqual(updated.loc[0, "x"], 5.0)


class TestLightConstrainWorkability(unittest.TestCase):
    def test_light_mask_applied(self):
        """
        Verify that the first field of df_workability is set to False
        outside of daylight hours.
        """
        # Metocean: 24 hours in a day, daylight 08:00–19:00
        start = datetime(2025, 1, 1, 0, 0)
        idx = pd.date_range(start=start, periods=24, freq="H")
        light = [(8 <= d.hour <= 19) for d in idx]
        df_metocean = pd.DataFrame({"light": [1 if l else 0 for l in light]}, index=idx)

        # Workability: first column all True
        df_work = pd.DataFrame({"work": [True if l else False for l in light]}, index=idx)

        mask = df_work

        # First field True only during daylight hours
        self.assertTrue(df_work.columns.tolist() == ["work"])
        self.assertTrue(mask.index.equals(idx))

        self.assertTrue(
            (df_work.loc[idx[8:20], "work"] == True).all()
        )  # 08–19 True
        self.assertTrue(
            (df_work.loc[idx[:8], "work"] == False).all()
        )  # 00–07 False
        self.assertTrue(
            (df_work.loc[idx[20:], "work"] == False).all()
        )  # 20–23 False


class TestDefineShiftOperationValues(unittest.TestCase):
    @patch("logistic_tools.core.functions.operation_scheduler.define_shift_operation.save_file_csv")
    def test_all_workability_true_branch(self, m_save):
        """
        Simple case: df_workability all True.
        Must use the branch "all workability is True" and return constant values.
        """
        # timeline: 24 hours
        start = datetime(2025, 1, 1, 0, 0)
        idx = pd.date_range(start=start, periods=24, freq="H")

        # df_metocean not used in this branch, but must have a consistent index
        df_metocean = pd.DataFrame(index=idx)

        # df_workability: single column, all True
        df_work = pd.DataFrame({"work": True}, index=idx)

        # Minimal operation
        operation = make_operation("OP_SHIFT", "ShiftOp", has_tow_port=False)

        # Shift data
        shift_data = {
            "number_shifts_main": 1,
            "duration_shift_main": 4.0,  # hours
            "number_shifts_last": 1,
            "duration_shift_last": 2.0,
            "olc_main": None,
            "olc_last": None,
            "n_vessels_main": 1,
            "n_vessels_last": 1,
            "n_crew_main": 1,
            "n_crew_last": 1,
        }

        transit_duration = 0.5  # hours
        shutdown_wtg = 2.0
        shutdown_wec = 0.0
        shutdown_pv = 0.0

        out_dir = "dummy_path.csv"

        df = define_shift_operation_values(
            df_metocean=df_metocean,
            operation=operation,
            df_workability=df_work,
            shift_data=shift_data,
            transit_duration=transit_duration,
            shutdown_wtg=shutdown_wtg,
            shutdown_wec=shutdown_wec,
            shutdown_pv=shutdown_pv,
            duration_shift=12.0,
            out_dir=out_dir,
        )

        # save_file_csv must be called once
        m_save.assert_called_once()

        # DataFrame must contain 'datetime'
        self.assertIn("datetime", df.columns)

        # Expected values (branch "all True"):
        # dur_net_site = n_main*(dur_main - 2*transit) + n_last*(dur_last - 2*transit)
        #               = 1*(4 - 1) + 1*(2 - 1) = 3 + 1 = 4
        # transit_tot = transit * (n_main + n_last) = 0.5 * 2 = 1
        expected_dur_net_site = 4.0
        expected_transit = 1.0
        expected_wait_start = 0.0
        expected_wait_port = 0.0
        expected_dur_total = 6.0  # 4 + 1 + 1

        # First row
        row0 = df.iloc[0]

        self.assertAlmostEqual(row0["dur_net_site"], expected_dur_net_site, places=6)
        self.assertAlmostEqual(row0["transit_to_site"], expected_transit, places=6)
        self.assertAlmostEqual(row0["transit_to_port"], expected_transit, places=6)
        self.assertAlmostEqual(row0["wait_start"], expected_wait_start, places=6)
        self.assertAlmostEqual(row0["wait_port"], expected_wait_port, places=6)
        self.assertAlmostEqual(row0["dur_total"], expected_dur_total, places=6)

        # Shutdown must be uniform (same value for all rows)
        self.assertTrue((df["dur_shutdown_wtg"] == shutdown_wtg).all())
        self.assertTrue((df["dur_shutdown_wec"] == shutdown_wec).all())
        self.assertTrue((df["dur_shutdown_pv"] == shutdown_pv).all())

        # days_inspected must exist and be object dtype
        self.assertIn("days_inspected", df.columns)
        self.assertEqual(df["days_inspected"].dtype, object)

    def test_workability_with_multiple_columns_raises_error(self):
        """
        If df_workability has more than one column, the function must
        raise a ValueError as it only supports single operation workability.
        """
        start = datetime(2025, 1, 1, 0, 0)
        idx = pd.date_range(start=start, periods=10, freq="H")

        df_metocean = pd.DataFrame(index=idx)
        df_work = pd.DataFrame(
            {"a": True, "b": False},
            index=idx,
        )

        operation = make_operation("OP_MULTI", "MultiWork", has_tow_port=False)

        shift_data = {
            "number_shifts_main": 1,
            "duration_shift_main": 2.0,
            "number_shifts_last": 0,
            "duration_shift_last": 1.0,
            "olc_main": None,
            "olc_last": None,
            "n_vessels_main": 1,
            "n_vessels_last": 0,
            "n_crew_main": 1,
            "n_crew_last": 0,
        }

        with self.assertRaises(ValueError):
            define_shift_operation_values(
                df_metocean=df_metocean,
                operation=operation,
                df_workability=df_work,
                shift_data=shift_data,
                transit_duration=0.5,
                shutdown_wtg=1.0,
                shutdown_wec=0.0,
                shutdown_pv=0.0,
                duration_shift=12.0,
                out_dir=None,
            )

    def test_partial_workability_non_24_7_branch(self):
        """
        Case where workability is not always True: the function must follow
        the complex scheduling branch and produce finite durations and
        non-empty 'days_inspected'.
        """
        start = datetime(2025, 1, 1, 0, 0)
        idx = pd.date_range(start=start, periods=10, freq="H")

        # Workability True only first 6 hours, then False
        work_mask = [True] * 6 + [False] * 4
        df_work = pd.DataFrame({"work": work_mask}, index=idx)
        df_metocean = pd.DataFrame(index=idx)

        operation = make_operation("OP_PARTIAL", "PartialShift", has_tow_port=False)

        shift_data = {
            "number_shifts_main": 1,
            "duration_shift_main": 2.0,
            "number_shifts_last": 0,
            "duration_shift_last": 1.0,
            "olc_main": None,
            "olc_last": None,
            "n_vessels_main": 1,
            "n_vessels_last": 0,
            "n_crew_main": 1,
            "n_crew_last": 0,
        }

        transit_duration = 0.5
        shutdown_wtg = 1.0
        shutdown_wec = 0.0
        shutdown_pv = 0.0

        df = define_shift_operation_values(
            df_metocean=df_metocean,
            operation=operation,
            df_workability=df_work,
            shift_data=shift_data,
            transit_duration=transit_duration,
            shutdown_wtg=shutdown_wtg,
            shutdown_wec=shutdown_wec,
            shutdown_pv=shutdown_pv,
            duration_shift=12.0,
            out_dir=None,
        )

        # First row should have finite computed values
        row0 = df.iloc[0]
        # dur_net_site = 1*(2 - 2*0.5) = 1
        self.assertAlmostEqual(row0["dur_net_site"], 1.0, places=6)
        # transit_to_site and _port = 0.5
        self.assertAlmostEqual(row0["transit_to_site"], 0.5, places=6)
        self.assertAlmostEqual(row0["transit_to_port"], 0.5, places=6)
        # total = 1 + 0 + 0 + 0.5 + 0.5 = 2
        self.assertAlmostEqual(row0["dur_total"], 2.0, places=6)

        # Shutdown must be applied
        self.assertAlmostEqual(row0["dur_shutdown_wtg"], shutdown_wtg, places=6)
        self.assertAlmostEqual(row0["dur_shutdown_wec"], shutdown_wec, places=6)
        self.assertAlmostEqual(row0["dur_shutdown_pv"], shutdown_pv, places=6)

        # days_inspected must be a list of datetimes
        self.assertIsInstance(row0["days_inspected"], list)
        self.assertTrue(all(isinstance(d, pd.Timestamp) for d in row0["days_inspected"]))

    def test_port_operation_adds_wait_port_to_shutdown(self):
        """
        For port operations (with op_tow_port defined) and partial workability,
        the wait_port contribution must be added to the shutdown duration.
        """
        start = datetime(2025, 1, 1, 0, 0)
        idx = pd.date_range(start=start, periods=10, freq="H")

        # Workability pattern that creates a gap between two shifts:
        # True at hours 0,1,2 and 5,6,7 -> two blocks of 3h
        work_mask = [True, True, True, False, False, True, True, True, False, False]
        df_work = pd.DataFrame({"work": work_mask}, index=idx)
        df_metocean = pd.DataFrame(index=idx)

        # Operation with tow-to-port behaviour
        operation = make_operation("ofw_PORT", "PortInspection", has_tow_port=True)

        shift_data = {
            "number_shifts_main": 2,   # two main shifts
            "duration_shift_main": 2.0,
            "number_shifts_last": 0,
            "duration_shift_last": 1.0,  # not used
            "olc_main": None,
            "olc_last": None,
            "n_vessels_main": 1,
            "n_vessels_last": 0,
            "n_crew_main": 1,
            "n_crew_last": 0,
        }

        transit_duration = 0.5
        base_shutdown_wtg = 1.0
        shutdown_wec = 0.0
        shutdown_pv = 0.0

        df = define_shift_operation_values(
            df_metocean=df_metocean,
            operation=operation,
            df_workability=df_work,
            shift_data=shift_data,
            transit_duration=transit_duration,
            shutdown_wtg=base_shutdown_wtg,
            shutdown_wec=shutdown_wec,
            shutdown_pv=shutdown_pv,
            duration_shift=12.0,
            out_dir=None,
        )

        row0 = df.iloc[0]

        # In this configuration:
        # - wait_port for second shift should be 3 hours
        #   (first shift at t=0, second at t=5 instead of t=2)
        # - dur_net_site = 2 shifts * (2 - 2*0.5) = 2 * 1 = 2
        # - transit_total = 0.5 * 2 = 1
        # - wait_start = 0
        # - wait_port = 3
        # => dur_total (without shutdown) = 2 + 0 + 3 + 1 + 1 = 7
        self.assertAlmostEqual(row0["dur_net_site"], 2.0, places=6)
        self.assertAlmostEqual(row0["wait_start"], 0.0, places=6)
        self.assertAlmostEqual(row0["wait_port"], 3.0, places=6)
        self.assertAlmostEqual(row0["transit_to_site"], 1.0, places=6)
        self.assertAlmostEqual(row0["transit_to_port"], 1.0, places=6)
        self.assertAlmostEqual(row0["dur_total"], 7.0, places=6)

        # Shutdown for WTG must include wait_port (1 + 3 = 4)
        self.assertAlmostEqual(row0["dur_shutdown_wtg"], 4.0, places=6)
        # Other shutdowns remain zero
        self.assertAlmostEqual(row0["dur_shutdown_wec"], shutdown_wec, places=6)
        self.assertAlmostEqual(row0["dur_shutdown_pv"], shutdown_pv, places=6)

        # days_inspected should contain two dates (two shifts, in different windows)
        self.assertIsInstance(row0["days_inspected"], list)
        self.assertEqual(len(row0["days_inspected"]), 2)
        # First at 00:00, second at 05:00
        self.assertEqual(row0["days_inspected"][0], idx[0])
        self.assertEqual(row0["days_inspected"][1], idx[5])


if __name__ == "__main__":
    unittest.main(verbosity=2)
