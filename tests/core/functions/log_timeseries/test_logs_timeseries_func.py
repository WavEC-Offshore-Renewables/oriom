#test_logs_timeseries_func

import unittest
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from oriom.core.functions.logs_timeseries import logs_timeseries_func


# ---------------------- Dummy helpers per i test ---------------------- #

class DummyVessel:
    def __init__(self, vid, n_vessels=1):
        self.id = vid
        self.n_vessels = n_vessels


class DummyFailureForShutdown:
    def __init__(self, fid, potential_shutdown, perc_shutdown):
        self.id = fid
        self.potential_shutdown = potential_shutdown
        self.perc_shutdown = perc_shutdown


class DummyOpStatShutdownDicts:
    """Have dict wtg/pv/wec, used in try."""
    def __init__(self, op_id, wtg=True, pv=False, wec=False):
        self.id = op_id
        self.wtg_shutdown_dict = {"dummy": wtg}
        self.pv_shutdown_dict = {"dummy": pv}
        self.wec_shutdown_dict = {"dummy": wec}
        # non serve shutdown_dict qui


class DummyOpStatShutdownFlag:
    """It doesn't have dicts, so you use the except branch and shutdown_dict."""
    def __init__(self, op_id, shutdown_dict=True):
        self.id = op_id
        self.shutdown_dict = shutdown_dict


class DummyInspectionStat:
    """Similar to DummyOpStatShutdownDicts, used for inspections_*."""
    def __init__(self, op_id, shutdown=True):
        self.id = op_id
        self.wtg_shutdown_dict = {"dummy": shutdown}
        self.pv_shutdown_dict = {}
        self.wec_shutdown_dict = {}


class DummyInspectionForStatDuration:
    def __init__(self, dur_total_dict):
        self.dur_total_dict = dur_total_dict


# ---------------------- Test create_mobilisation ---------------------- #

class TestCreateMobilisation(unittest.TestCase):
    def test_create_mobilisation_concat_true_with_19_columns(self):
        """Verify that the mobilization row is added and populated correctly (19 columns)."""
        cols = [f"c{i}" for i in range(20)]
        df = pd.DataFrame(columns=cols)

        mobilisation_date = datetime(2025, 1, 1, 6, 0)
        end_mobi = datetime(2025, 1, 1, 12, 0)
        vessel = DummyVessel("V1", n_vessels=2)
        oper_list = ["op1", "op2"]

        out = logs_timeseries_func.create_mobilisation(
            df=df,
            mobilisation_date=mobilisation_date,
            end_mobi=end_mobi,
            event="mobilisation",
            vessel=vessel,
            oper_list=oper_list,
            count_fail="F001",
            concat=True,
        )

        self.assertEqual(len(out), 1)
        row = out.iloc[0]

        # map with row_values in code:
        self.assertEqual(row["c0"], mobilisation_date)        # mobilisation_date
        self.assertEqual(row["c8"], end_mobi)                 # end_mobi
        self.assertEqual(row["c10"], "mobilisation")          # event
        self.assertEqual(row["c11"], "mobi_F001")             # id_mobilisation
        self.assertEqual(row["c12"], "V1")                    # vessel.id
        self.assertEqual(row["c13"], 2)                       # vessel.n_vessels
        self.assertEqual(row["c16"], oper_list)               # oper_list
        self.assertFalse(row["c17"])                          # False
        self.assertFalse(row["c18"])                          # False

    def test_create_mobilisation_concat_false_with_17_columns_and_string_oper_list(self):
        """Test the behavior with 17 columns and oper_list string (truncate last two columns)."""
        cols = [f"c{i}" for i in range(17)]
        df = pd.DataFrame(columns=cols)

        mobilisation_date = datetime(2025, 1, 2, 8, 0)
        end_mobi = datetime(2025, 1, 2, 10, 0)
        vessel = DummyVessel("V2", n_vessels=1)
        oper_list = "op_single"

        row_only = logs_timeseries_func.create_mobilisation(
            df=df,
            mobilisation_date=mobilisation_date,
            end_mobi=end_mobi,
            event="mobilisation",
            vessel=vessel,
            oper_list=oper_list,
            count_fail=None,
            concat=False,
        )

        # should not modify the original
        self.assertTrue(df.empty)
        self.assertEqual(len(row_only), 1)
        row = row_only.iloc[0]

        # c11 = id_mobilisation (None)
        self.assertIsNone(row["c11"])
        # c12 = vessel.id
        self.assertEqual(row["c12"], "V2")
        # c16 = list of opeartions (list)
        self.assertEqual(row["c16"], ["op_single"])


# ---------------------- Test simple function semplici (count_failures, create_data, failure_df_to_logevent_df) ---------------------- #

class TestSimpleHelpers(unittest.TestCase):
    def test_count_failures_suffix(self):
        """Each failure with same id receives suffix .1, .2, ..."""
        df = pd.DataFrame(
            {
                "id": ["A", "A", "B"],
                "datetime": [
                    datetime(2025, 1, 1),
                    datetime(2025, 1, 2),
                    datetime(2025, 1, 3),
                ],
            }
        )
        out = logs_timeseries_func.count_failures(df.copy())
        self.assertListEqual(list(out["id"]), ["A.1", "A.2", "B.1"])

    def test_create_data_with_existing_column(self):
        """create_data must add the hours present in the indicated column"""
        base = datetime(2025, 1, 1, 0, 0)
        # as in real code: a Series is passed, not a DataFrame
        row = pd.Series({"wait_start": 2.5})
        new_date = logs_timeseries_func.create_data(row, "wait_start", base)
        self.assertEqual(new_date, base + timedelta(hours=2.5))

    def test_create_data_missing_column_returns_same_date(self):
        """If the column does not exist, it must return the same date (0 hours)."""
        base = datetime(2025, 1, 1, 0, 0)
        row = pd.Series({"other": 5})
        new_date = logs_timeseries_func.create_data(row, "wait_start", base)
        self.assertEqual(new_date, base)

    def test_failure_df_to_logevent_df_basic(self):
        """Check base mapping from dates_failures to log_events (failure only)."""
        dates_failures = pd.DataFrame(
            {
                "datetime": [
                    datetime(2025, 1, 1),
                    datetime(2025, 1, 2),
                    datetime(2025, 1, 3),
                ],
                "id": ["fA", "fA", "fB"],
                "maintenance_strategy": ["immediately", "immediately", "specific month"],
                "operation_triggered": ["op1", "op1", "op2"],
                "preferred_month": [None, None, 2],
            }
        )
        cols = ["d_trigger", "event", "id", "comments"]
        out = logs_timeseries_func.failure_df_to_logevent_df(dates_failures, cols)

        self.assertEqual(len(out), 3)
        # all event = 'failure'
        self.assertTrue((out["event"] == "failure").all())
        # ID contati
        self.assertListEqual(list(out["id"]), ["fA.1", "fA.2", "fB.1"])
        # comments = maintenance_strategy
        self.assertListEqual(
            list(out["comments"]),
            ["immediately", "immediately", "specific month"],
        )


# ---------------------- Test create_stat_chart_inspection_port ---------------------- #

class TestCreateStatChartInspectionPort(unittest.TestCase):
    def test_create_stat_chart_inspection_port_basic(self):
        """
        Verify that the inspection_port duration percentile is calculated
            and that d_end_stat_chart is set correctly.
        """
        t0 = datetime(2025, 1, 1, 0, 0)
        # two inspections lasting 10 hours and 20 hours
        df = pd.DataFrame(
            {
                "d_trigger": [t0, t0 + timedelta(days=1), t0],
                "d_end": [
                    t0 + timedelta(hours=10),
                    t0 + timedelta(days=1, hours=20),
                    t0 + timedelta(hours=5),
                ],
                "event": ["inspection_port", "inspection_port", "other"],
                "id": ["insp1", "insp1", "x"],
            }
        )

        out = logs_timeseries_func.create_stat_chart_inspection_port(df.copy(), percentile=0.5)

        # the third line is not inspection_port, it must not have d_end_stat_chart set
        self.assertTrue(pd.isna(out.loc[2, "d_end_stat_chart"]))

        # for insp1, the duration in hours is 10 and 20 -> quantile(0.5) = 15
        mask = out["event"] == "inspection_port"
        durations = (out.loc[mask, "d_end_stat_chart"] - out.loc[mask, "d_trigger"]).dt.total_seconds() / 3600
        for d in durations:
            self.assertAlmostEqual(d, 15.0, places=5)

    def test_create_stat_chart_inspection_port_percentile_gt_one(self):
        """
        If percentile > 1, it must be converted to a fraction (e.g., 90 -> 0.9).
            We don't test for the exact number, but we do test that the code doesn't explode.
        """
        t0 = datetime(2025, 1, 1, 0, 0)
        df = pd.DataFrame(
            {
                "d_trigger": [t0, t0 + timedelta(days=1)],
                "d_end": [t0 + timedelta(hours=10), t0 + timedelta(days=1, hours=20)],
                "event": ["inspection_port", "inspection_port"],
                "id": ["insp1", "insp1"],
            }
        )

        out = logs_timeseries_func.create_stat_chart_inspection_port(df.copy(), percentile=90)
        self.assertIn("d_end_stat_chart", out.columns)
        self.assertFalse(out["d_end_stat_chart"].isna().any())


# ---------------------- Test inspection_statistic_duration ---------------------- #

class TestInspectionStatisticDuration(unittest.TestCase):
    def test_inspection_statistic_duration_non_extreme_returns_dur_month(self):
        """If the month is not 'extreme', it should return dur_month directly."""
        # dur_total_dict: current month ~ similar to neighboring ones
        insp = DummyInspectionForStatDuration(
            dur_total_dict={"5": 10.0, "6": 12.0, "7": 15.0}
        )

        # oper_schedule not used in this branch, but let's pass something valid
        dts = pd.date_range("2025-06-01", periods=3, freq="D")
        oper_schedule = pd.DataFrame({"datetime": dts, "dur_total": [10, 12, 14]})
        date_continuous = dts[0]  # month 6

        dur = logs_timeseries_func.inspection_statistic_duration(
            oper_schedule, date_continuous, insp
        )
        self.assertEqual(dur, 12.0)

    def test_inspection_statistic_duration_extreme_uses_percentile(self):
        """
        If the month is 'extreme' compared to its neighbors, it should use the 75th percentile
            of the dur_total column for that month.
        """
        insp = DummyInspectionForStatDuration(
            dur_total_dict={"5": 2.0, "6": 20.0, "7": 2.0}
        )

        dts = pd.date_range("2025-06-01", periods=4, freq="D")
        oper_schedule = pd.DataFrame(
            {"datetime": dts, "dur_total": [10.0, 20.0, 30.0, 40.0]}
        )
        date_continuous = dts[0]  # month 6

        dur = logs_timeseries_func.inspection_statistic_duration(
            oper_schedule, date_continuous, insp
        )

        # 75° percentile nearest di [10,20,30,40] = 30
        self.assertEqual(dur, 30.0)


# ---------------------- Test shutdown_evaluation ---------------------- #

class TestShutdownEvaluation(unittest.TestCase):
    def test_shutdown_evaluation_failures_all_marked_when_100_percent(self):
        """
        If perc_shutdown=100, all failures of that type
        must be marked as shutdown=True.
        """
        # log_events con 4 failure (2 tipo F_A, 2 tipo F_B) e nessuna colonna shutdown iniziale
        df = pd.DataFrame(
            {
                "event": ["failure", "failure", "failure", "failure"],
                "id": ["F_A.1", "F_A.2", "F_B.1", "F_B.2"],
            }
        )

        failures = [
            DummyFailureForShutdown("F_A", potential_shutdown=True, perc_shutdown=100),
            DummyFailureForShutdown("F_B", potential_shutdown=False, perc_shutdown=100),
        ]

        out = logs_timeseries_func.shutdown_evaluation(
            log_events=df.copy(),
            failures=failures,
            operation_log_file_stats=[],
            inspections_port_stat=[],
            inspections_site_stat=[],
        )

        # for F_A.* --> all True
        mask_A = out["id"].str.startswith("F_A")
        self.assertTrue(out.loc[mask_A, "shutdown"].all())

        # for F_B.* --> False (no potential_shutdown)
        mask_B = out["id"].str.startswith("F_B")
        self.assertTrue((out.loc[mask_B, "shutdown"] == False).all())

    def test_shutdown_evaluation_operations_with_dicts(self):
        """
        If operation has wtg/pv/wec dicts with at least one True, all lines with that ID
        should be marked as shutdown=True.
        """
        df = pd.DataFrame(
            {
                "event": ["operation", "operation", "failure"],
                "id": ["OP1", "OP1", "F1.1"],
            }
        )

        failures = []

        op_stats = [
            DummyOpStatShutdownDicts("OP1", wtg=True, pv=False, wec=False),
        ]

        out = logs_timeseries_func.shutdown_evaluation(
            log_events=df.copy(),
            failures=failures,
            operation_log_file_stats=op_stats,
            inspections_port_stat=[],
            inspections_site_stat=[],
        )

        mask_op = out["id"] == "OP1"
        self.assertTrue(out.loc[mask_op, "shutdown"].all())
        #Failure without shutdown info must remain False (or NaN -> we treat it as not True)
        mask_fail = out["id"] == "F1.1"
        self.assertTrue((out.loc[mask_fail, "shutdown"] == False).all())

    def test_shutdown_evaluation_operations_with_shutdown_dict_fallback(self):
        """
        If the object does not have the wtg/pv/wec dicts, it must use shutdown_dict (branch except).
        """
        df = pd.DataFrame(
            {
                "event": ["operation", "operation"],
                "id": ["OPX", "OPY"],
            }
        )

        failures = []

        op_stats = [
            DummyOpStatShutdownFlag("OPX", shutdown_dict=True),
            DummyOpStatShutdownFlag("OPY", shutdown_dict=False),
        ]

        out = logs_timeseries_func.shutdown_evaluation(
            log_events=df.copy(),
            failures=failures,
            operation_log_file_stats=op_stats,
            inspections_port_stat=[],
            inspections_site_stat=[],
        )

        self.assertTrue(out.loc[out["id"] == "OPX", "shutdown"].all())
        self.assertTrue((out.loc[out["id"] == "OPY", "shutdown"] == False).all())



if __name__ == "__main__":
    unittest.main()
