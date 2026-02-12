# tests/scheduling/test_define_operation_values.py

import os
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pandas as pd
import numpy as np

from logistic_tools.core.functions.operation_scheduler.define_operation import define_operation_values


def make_activity(name, duration, location, wtg_sd=False, wec_sd=False, pv_sd=False):
    """Build a minimal activity object with required attributes."""
    return SimpleNamespace(
        name=name,
        duration=float(duration),
        location=location,
        wtg_shutdown_dur=float(wtg_sd),
        wec_shutdown_dur=float(wec_sd),
        pv_shutdown_dur=float(pv_sd),
    )


def make_operation(op_id, name, activities):
    """Build a minimal operation object with required attributes."""
    return SimpleNamespace(id=op_id, name=name, activities=activities)


class TestDefineOperationValues(unittest.TestCase):
    def setUp(self):
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_ctx.cleanup)
        # function expects a file path for save_file_csv
        self.out_dir = os.path.join(self.tmp_ctx.name, "schedule.csv")

    # ---------- Happy path: no waiting, 3 activities (<=3 forces MAX_WAIT=0) ----------
    @patch("logistic_tools.core.functions.operation_scheduler.define_operation.save_file_csv")
    @patch("logistic_tools.core.functions.operation_scheduler.define_operation.tqdm")
    def test_happy_path_no_wait_three_activities(self, m_tqdm, m_save):
        # Progress bar mock
        m_tqdm.return_value = MagicMock(total=10, update=lambda *a, **k: None, close=lambda: None)

        # Build activities: port (2.0h), transit (1.0h), site (3.0h)
        acts = [
            make_activity("A_port", 2.0, "port", wtg_sd=True),
            make_activity("A_transit", 1.0, "transit"),
            make_activity("A_site", 3.0, "site", wtg_sd=True),
        ]
        op = make_operation("OP1", "Happy", acts)

        # Startability: 3 columns (one per activity), all True for first 20 timesteps
        n = 20
        df_startability = pd.DataFrame(
            np.ones((n, len(acts)), dtype=bool),
            index=pd.RangeIndex(start=0, stop=n, step=1),
            columns=[f"A{i}" for i in range(len(acts))],
        )

        df = define_operation_values(
            ts_analyse=list(range(10)),
            operation=op,
            df_startability=df_startability,
            out_dir=self.out_dir,  # trigger save
        )

        # Assert CSV save was called
        m_save.assert_called_once()

        # Pick the first scheduled row (t=0)
        row0 = df.iloc[0]
        # Durations as expected
        self.assertAlmostEqual(row0["dur_net_port"], 2.0)
        self.assertAlmostEqual(row0["transit_to_site"], 1.0)
        self.assertAlmostEqual(row0["dur_net_site"], 3.0)

        # No waiting at start and between activities
        self.assertAlmostEqual(row0["wait_start"], 0.0)
        self.assertAlmostEqual(row0["wait_site"], 0.0)
        self.assertAlmostEqual(row0["wait_port"], 0.0)

        # Total duration = sum(port, transit_to_site, site, transit_to_port(if any=0))
        self.assertAlmostEqual(row0["dur_total"], 6, places=1)

        # Shutdown accumulation: sum(wtg_sd * act_dur)
        self.assertAlmostEqual(row0["dur_shutdown_wtg"], 5, places=3)
        # The others default to 0.0
        self.assertAlmostEqual(row0["dur_shutdown_wec"], 0.0, places=3)
        self.assertAlmostEqual(row0["dur_shutdown_pv"], 0.0, places=3)

    # ---------- Wait-at-start scenario: first activity is most restrictive ----------
    @patch("logistic_tools.core.functions.operation_scheduler.define_operation.tqdm")
    def test_WoW_Watsite(self, m_tqdm):
        m_tqdm.return_value = MagicMock(total=50, update=lambda *a, **k: None, close=lambda: None)

        acts = [
            make_activity("A_port", 2.0, "port"),
            make_activity("A_transit_site", 1.0, "transit"),
            make_activity("A_site", 3.0, "site", wtg_sd=True),  # most restrictive
            make_activity("A_site", 2.0, "site"),
            make_activity("A_transit_port", 1.0, "transit"),
        ]
        op = make_operation("OP2", "WaitStart", acts)

        # Build startability (copied from your example)
        n = 50
        col0 = np.ones(n, dtype=bool)
        col1 = np.ones(n, dtype=bool)
        col2 = np.array([False] * 5 + [True] * 8 + [False] * 5 + [True] * (n - 18), dtype=bool)
        col3 = np.array([True] * 5 + [True] * 6 + [False] * 7 + [True] * (n - 18), dtype=bool)
        col4 = np.ones(n, dtype=bool)
        df_startability = pd.DataFrame(
            np.vstack([col0, col1, col2, col3, col4]).T,
            index=pd.RangeIndex(start=0, stop=n, step=1),
            columns=["A0", "A1", "A2", "A3", "A4"],
        )

        df = define_operation_values(
            ts_analyse=list(range(20)),
            operation=op,
            df_startability=df_startability,
            MAX_WAIT=10,
            out_dir=None,
        )

        exp_dur_total = ([11, 10, 9, 9, 9] + [16, 15, 14, 13, 12] + [14, 13, 12, 11, 10] + [9] * 27)

        exp_dur_net_port = [2] * 42
        exp_dur_net_site = [5] * 42
        exp_wait_start = [2, 1, 0, 0, 0] + [0] * 5 + [5, 4, 3, 2, 1] + [0] * 27
        exp_wait_site = [0] * 5 + [7, 6, 5, 4, 3] + [0] * 32
        exp_tr_site, exp_tr_port = ([1] * 42, [1] * 42)
        exp_shut_wtg = [3] * 42
        exp_wait_port, exp_shut_wec, exp_shut_pv = ([0] * 42, [0] * 42, [0] * 42)

        def assert_col(col, expected):
            pd.testing.assert_series_equal(
                df.loc[:41, col].reset_index(drop=True),
                pd.Series(expected, dtype=float),
                check_names=False,
                check_dtype=False,
            )

        # 1) verify columns 0..41
        for col, exp in [
            ("dur_total", exp_dur_total),
            ("dur_net_port", exp_dur_net_port),
            ("dur_net_site", exp_dur_net_site),
            ("wait_start", exp_wait_start),
            ("wait_port", exp_wait_port),
            ("wait_site", exp_wait_site),
            ("transit_to_site", exp_tr_site),
            ("transit_to_port", exp_tr_port),
            ("dur_shutdown_wtg", exp_shut_wtg),
            ("dur_shutdown_wec", exp_shut_wec),
            ("dur_shutdown_pv", exp_shut_pv),
        ]:
            assert_col(col, exp)

        # 2) base_no_wait consistency
        base_no_wait = 9.0  # 2 + 1 + 5 + 1
        net_no_wait = (
            df.loc[:41, "dur_net_port"]
            + df.loc[:41, "transit_to_site"]
            + df.loc[:41, "dur_net_site"]
            + df.loc[:41, "transit_to_port"]
        )
        self.assertTrue((abs(net_no_wait - base_no_wait) < 1e-9).all())

        lhs = df.loc[:41, "dur_total"]
        rhs = base_no_wait + df.loc[:41, "wait_start"] + df.loc[:41, "wait_site"]
        self.assertTrue((abs(lhs - rhs) < 1e-9).all())

        # 3) rows 42..49: all NaN except 'datetime'
        self.assertTrue(df.loc[42:, df.columns.difference(["datetime"])].isna().all().all())

        # 4) spot checks
        self.assertEqual(df.loc[0:2, "wait_start"].astype(int).tolist(), [2, 1, 0])
        self.assertEqual(df.loc[5:9, "wait_site"].astype(int).tolist(), [7, 6, 5, 4, 3])
        self.assertEqual(df.loc[10:14, "wait_start"].astype(int).tolist(), [5, 4, 3, 2, 1])

    # ---------- Impossible scenario: raise InterruptedError ----------
    @patch("logistic_tools.core.functions.operation_scheduler.define_operation.tqdm")
    def test_impossible_operation_raises(self, m_tqdm):
        m_tqdm.return_value = MagicMock(total=10, update=lambda *a, **k: None, close=lambda: None)

        acts = [
            make_activity("A_port", 1.0, "port"),
            make_activity("A_site", 1.0, "site"),
            make_activity("A_transit", 1.0, "transit"),
        ]
        op = make_operation("OP3", "Impossible", acts)

        # All False -> cannot schedule at any timestep
        df_startability = pd.DataFrame(
            np.zeros((10, len(acts)), dtype=bool),
            index=pd.RangeIndex(0, 10, 1),
            columns=[f"A{i}" for i in range(len(acts))],
        )

        with self.assertRaises(InterruptedError):
            define_operation_values(
                ts_analyse=list(range(10)),
                operation=op,
                df_startability=df_startability,
                out_dir=None,
            )

    # ---------- NEW: invalid activity location should raise AssertionError ----------
    @patch("logistic_tools.core.functions.operation_scheduler.define_operation.tqdm")
    def test_invalid_activity_location_raises(self, m_tqdm):
        """
        If an activity has an unrecognized location, the function must raise AssertionError.
        Covers the error branch inside the loop over activities.
        """
        m_tqdm.return_value = MagicMock(total=5, update=lambda *a, **k: None, close=lambda: None)

        acts = [
            make_activity("A_invalid", 1.0, "unknown"),  # invalid location
        ]
        op = make_operation("OP4", "BadLocation", acts)

        # Startability: activity always possible
        n = 5
        df_startability = pd.DataFrame(
            np.ones((n, 1), dtype=bool),
            index=pd.RangeIndex(0, n, 1),
            columns=["A0"],
        )

        with self.assertRaises(AssertionError):
            define_operation_values(
                ts_analyse=list(range(n)),
                operation=op,
                df_startability=df_startability,
                out_dir=None,
            )

    # ---------- NEW: MAX_WAIT forced to 0 for <=3 activities ----------
    @patch("logistic_tools.core.functions.operation_scheduler.define_operation.tqdm")
    def test_max_wait_forced_zero_for_three_activities(self, m_tqdm):
        """
        For operations with <=3 activities, the function forces MAX_WAIT = 0.
        Here we build a case where the activities could be scheduled only if waiting
        (MAX_WAIT>0) were allowed. We pass MAX_WAIT=10 but with 3 activities we verify
        that an InterruptedError is raised (no possible solution).
        """
        m_tqdm.return_value = MagicMock(total=10, update=lambda *a, **k: None, close=lambda: None)

        # Three site activities, each with a single startability window
        acts = [
            make_activity("A_site0", 1.0, "site"),
            make_activity("A_site1", 1.0, "site"),
            make_activity("A_site2", 1.0, "site"),
        ]
        op = make_operation("OP5", "MaxWait3Acts", acts)

        n = 10
        col0 = np.zeros(n, dtype=bool)
        col1 = np.zeros(n, dtype=bool)
        col2 = np.zeros(n, dtype=bool)

        # Each column has a single valid timestep, but separated in time:
        # A0 only at t=0, A1 only at t=3, A2 only at t=6
        col0[0] = True
        col1[3] = True
        col2[6] = True

        df_startability = pd.DataFrame(
            np.vstack([col0, col1, col2]).T,
            index=pd.RangeIndex(0, n, 1),
            columns=["A0", "A1", "A2"],
        )

        # If MAX_WAIT were honored (e.g., =10h), concatenating all activities with waits
        # would be possible. But with len(activities)<=3, the function forces MAX_WAIT=0,
        # so it cannot wait between activities -> no solution -> InterruptedError.
        with self.assertRaises(InterruptedError):
            define_operation_values(
                ts_analyse=list(range(n)),
                operation=op,
                df_startability=df_startability,
                MAX_WAIT=10,  # will be ignored and forced to 0
                out_dir=None,
            )


if __name__ == '__main__':
    unittest.main(verbosity=2)
