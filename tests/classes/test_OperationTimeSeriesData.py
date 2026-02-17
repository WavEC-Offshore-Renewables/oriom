import unittest
from unittest.mock import patch
import tempfile
import os
import pandas as pd

# SUT
from oriom.classes.OperationTimeSeriesData import OperationTimeSeriesData


# ----------------- Helpers -----------------

class DummyOp:
    """Minimal operation object with an id attribute."""
    def __init__(self, id_="ofw_001"):
        self.id = id_


def make_sched_df(cols=None, rows=None):
    """
    Build a minimal oper_sched DataFrame with required columns.
    You can pass extra columns via 'cols'/'rows' if needed.
    """
    base_cols = ["datetime", "dur_net_site", "transit_to_port", "transit_to_site"]
    if cols:
        for c in cols:
            if c not in base_cols:
                base_cols.append(c)
    if rows is None:
        rows = [[pd.Timestamp("2025-06-01 00:00:00"), 4.0, 1.5, 2.5]]
    df = pd.DataFrame(rows, columns=base_cols)
    return df


# ----------------- Tests -----------------

class TestOperationTimeSeriesData_Init(unittest.TestCase):

    @patch("oriom.classes.OperationTimeSeriesData.convert_stringtime")
    def test_extracts_core_fields_and_dur_total_with_port_dur(self, conv_mock):
        """__init__ sets fields from oper_sched and computes dur_total including dur_net_port."""
        conv_mock.side_effect = lambda df, col: df  # no-op

        op = DummyOp("ofw_A")
        df = make_sched_df(
            cols=["dur_net_port"],
            rows=[[pd.Timestamp("2025-06-01 00:00:00"), 4.0, 1.0, 2.0, 0.5]],
        )
        # Manually add an extra column with some NaNs to exercise last_valid_index
        df["extra"] = [None]

        obj = OperationTimeSeriesData(operation=op, id=op.id, oper_sched=df, startability=pd.DataFrame())

        self.assertEqual(obj.id, "ofw_A")
        self.assertIs(obj.operation, op)
        self.assertEqual(obj.dur_net_site, 4.0)
        self.assertEqual(obj.dur_net_port, 0.5)
        self.assertEqual(obj.transit_tp, 1.0)
        self.assertEqual(obj.transit_ts, 2.0)
        # Sum: 2.0 + 1.0 + 0.5 + 4.0 = 7.5
        self.assertEqual(obj.dur_total, 7.5)
        # last_valid_index should be an integer index (0 here)
        self.assertEqual(obj.last_valid_index, 0)

    @patch("oriom.classes.OperationTimeSeriesData.convert_stringtime")
    def test_missing_dur_net_port_defaults_to_zero(self, conv_mock):
        """If 'dur_net_port' is missing, it defaults to 0 in _extract_from_sched."""
        conv_mock.side_effect = lambda df, col: df  # no-op

        op = DummyOp("ofw_B")
        df = make_sched_df(rows=[[pd.Timestamp("2025-06-01 00:00:00"), 3.0, 2.0, 1.0]])
        obj = OperationTimeSeriesData(operation=op, id=op.id, oper_sched=df, startability=pd.DataFrame())

        self.assertEqual(obj.dur_net_site, 3.0)
        self.assertEqual(obj.dur_net_port, 0)
        # Sum: 1.0 + 2.0 + 0 + 3.0 = 6.0
        self.assertEqual(obj.dur_total, 6.0)

    def test_empty_oper_sched_raises(self):
        """If oper_sched is empty, __init__ raises ValueError."""
        op = DummyOp("ofw_C")
        with self.assertRaises(ValueError):
            OperationTimeSeriesData(operation=op, id=op.id, oper_sched=pd.DataFrame(), startability=pd.DataFrame())


class TestOperationTimeSeriesData_CreateTimeseries(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = self.tmp.name
        self.op = DummyOp("ofw_123")
        # Build default schedule & related CSVs in temp dir
        self.oper = make_sched_df(
            cols=["dur_net_port"],
            rows=[[pd.Timestamp("2025-06-01 08:00:00"), 5.0, 2.0, 3.0, 1.0]],
        )

    @patch("oriom.classes.OperationTimeSeriesData.convert_stringtime")
    def test_with_csv_path_returns_instance_and_reads_optional_startability(self, conv_mock):
        """Passing a filename (str) loads CSV from op_dir and returns an instance (no 'save')."""
        conv_mock.side_effect = lambda df, col: df  # no-op

        # Write operation_schedule.csv and startability.csv
        op_dir = self.base
        sched_path = os.path.join(op_dir, "operation_schedule.csv")
        self.oper.to_csv(sched_path, index=False)
        start_df = pd.DataFrame({"x": [1]})
        start_df.to_csv(os.path.join(op_dir, "startability.csv"), index=False)

        ts = OperationTimeSeriesData.create_timeseries_data(
            operation=self.op,
            file_name_dir="operation_schedule.csv",
            op_dir=op_dir,
            save=None,
        )
        self.assertIsInstance(ts, OperationTimeSeriesData)
        self.assertEqual(ts.id, "ofw_123")
        self.assertEqual(ts.dur_total, 5.0 + 1.0 + 2.0 + 3.0)  # site + port + tp + ts

    @patch("oriom.classes.OperationTimeSeriesData.convert_stringtime")
    def test_with_csv_path_rename_first_column_if_not_datetime(self, conv_mock):
        """If first column is not named 'datetime', it is renamed before conversion."""
        conv_mock.side_effect = lambda df, col: df  # no-op

        op_dir = self.base
        # Create a CSV with first column 'ts' instead of 'datetime'
        df = pd.DataFrame({
            "ts": [pd.Timestamp("2025-06-01 08:00:00")],
            "dur_net_site": [2.0],
            "transit_to_port": [1.0],
            "transit_to_site": [1.0],
            "dur_net_port": [0.0],
        })
        df.to_csv(os.path.join(op_dir, "operation_schedule.csv"), index=False)

        ts = OperationTimeSeriesData.create_timeseries_data(
            operation=self.op, file_name_dir="operation_schedule.csv", op_dir=op_dir, save=None
        )
        # If the rename worked and conversion didn't error, instance exists and dur_total sums correctly
        self.assertIsInstance(ts, OperationTimeSeriesData)
        self.assertEqual(ts.dur_total, 2.0 + 0.0 + 1.0 + 1.0)

    @patch("oriom.classes.OperationTimeSeriesData.convert_stringtime")
    def test_with_dataframe_input_and_no_startability(self, conv_mock):
        """Passing a DataFrame directly should build the instance; missing startability is tolerated."""
        conv_mock.side_effect = lambda df, col: df  # no-op
        ts = OperationTimeSeriesData.create_timeseries_data(
            operation=self.op, file_name_dir=self.oper.copy(), op_dir=self.base, save=None
        )
        self.assertIsInstance(ts, OperationTimeSeriesData)
        self.assertEqual(ts.dur_total, 5.0 + 1.0 + 2.0 + 3.0)

    @patch("oriom.classes.OperationTimeSeriesData.convert_stringtime")
    def test_save_true_returns_tuple_with_oper_sched_and_workability(self, conv_mock):
        """
        With save=True, returns (instance, oper_sched_df, workability_df).
        Requires 'workability.csv' to exist in op_dir.
        """
        conv_mock.side_effect = lambda df, col: df  # no-op

        op_dir = self.base
        self.oper.to_csv(os.path.join(op_dir, "operation_schedule.csv"), index=False)
        # create workability.csv
        work_df = pd.DataFrame({"ok": [1, 2, 3]})
        work_df.to_csv(os.path.join(op_dir, "workability.csv"), index=False)

        ts, oper_df_ret, work_df_ret = OperationTimeSeriesData.create_timeseries_data(
            operation=self.op,
            file_name_dir="operation_schedule.csv",
            op_dir=op_dir,
            save=True,
        )
        self.oper = self.oper.iloc[:,1:]
        oper_df_ret = oper_df_ret.iloc[:,1:]
        self.assertIsInstance(ts, OperationTimeSeriesData)
        pd.testing.assert_frame_equal(oper_df_ret.reset_index(drop=True), self.oper.reset_index(drop=True))
        pd.testing.assert_frame_equal(work_df_ret.reset_index(drop=True), work_df.reset_index(drop=True))

    def test_missing_schedule_csv_raises(self):
        """If a string path is given but the CSV is missing, FileNotFoundError is raised."""
        with self.assertRaises(FileNotFoundError):
            OperationTimeSeriesData.create_timeseries_data(
                operation=self.op, file_name_dir="operation_schedule.csv", op_dir=self.base, save=None
            )

    def test_wrong_type_for_file_name_dir_raises(self):
        """file_name_dir must be str (CSV path) or pandas DataFrame."""
        with self.assertRaises(TypeError):
            OperationTimeSeriesData.create_timeseries_data(
                operation=self.op, file_name_dir=123, op_dir=self.base, save=None
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
