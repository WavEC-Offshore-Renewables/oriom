# test_logs_corrective_aux.py

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import pandas as pd

from oriom.core.functions.logs_timeseries.logs_corrective_aux import (
    _check_index_row_validity,
    compute_operation_datetimes,
    create_operation_site,
)


LOG_COLS = [
    "d_trigger",
    "d_end_leadtime",
    "d_end_wait_start",
    "d_end_dur_net_port",
    "d_end_transit_ts",
    "d_end_wait_site",
    "d_end_dur_net_site",
    "d_end_transit_tp",
    "d_end",
    "d_end_stat_chart",
    "event",
    "id",
    "vessel_1",
    "n_vessel_1",
    "vessel_2",
    "n_vessel_2",
    "comments",
]


class DummyOperStat:
    def __init__(self, dur_total_dict):
        self.dur_total_dict = dur_total_dict


class DummyFailure:
    def __init__(self, maintenance_strategy, preferred_month=None):
        self.maintenance_strategy = maintenance_strategy
        self.preferred_month = preferred_month
        # lead_time is not used directly in this module but exists in upstream code
        self.lead_time = 0


class DummyOperation:
    def __init__(self, op_id: str):
        self.id = op_id


class DummyVessel:
    def __init__(self, vessel_id: str, vessel_type: str = "workboat"):
        self.id = vessel_id
        self.type = vessel_type
        # mobilisation_time not used directly here, but part of real data structure
        self.mobilisation_time = 0


class TestCheckIndexRowValidity(unittest.TestCase):
    def test_index_greater_than_last_valid_returns_empty_dataframe(self):
        """If idx_end_leadtime > last_valid_idx, function must return an empty DataFrame."""
        base_dt = datetime(2025, 1, 1, 0, 0)
        oper_sched = pd.DataFrame(
            {
                "datetime": [base_dt + timedelta(hours=i) for i in range(3)],
                "col1": [1, 2, 3],
                "col2": [4, 5, 6],
                "col3": [7, 8, 9],
            }
        )
        row = pd.Series({"id": "F1.0"})

        result = _check_index_row_validity(
            idx_end_leadtime=5,
            last_valid_idx=2,
            r=row,
            oper_sched=oper_sched,
        )

        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

    def test_valid_index_returns_row_series(self):
        """If index is valid and there are no NaNs, the corresponding schedule row is returned."""
        base_dt = datetime(2025, 1, 1, 0, 0)
        oper_sched = pd.DataFrame(
            {
                "datetime": [base_dt + timedelta(hours=i) for i in range(3)],
                "col1": [1, 2, 3],
                "col2": [4, 5, 6],
                "col3": [7, 8, 9],
            }
        )
        row = pd.Series({"id": "F1.0"})

        result = _check_index_row_validity(
            idx_end_leadtime=1,
            last_valid_idx=2,
            r=row,
            oper_sched=oper_sched,
        )

        # Current implementation returns a Series (one row of oper_sched)
        self.assertIsInstance(result, pd.Series)
        self.assertEqual(result["datetime"], oper_sched.loc[1, "datetime"])

    def test_nan_in_filtered_row_raises_value_error(self):
        """If the filtered schedule row contains NaNs in the relevant columns, a ValueError must be raised."""
        base_dt = datetime(2025, 1, 1, 0, 0)
        # Build a schedule where row 0 contains a NaN in an internal column
        oper_sched = pd.DataFrame(
            {
                "datetime": [base_dt, base_dt + timedelta(hours=1)],
                "col1": [1.0, 2.0],
                "col2": [float("nan"), 5.0],
                "col3": [7.0, 8.0],
                "col4": [9.0, 10.0],
                "col5": [11.0, 12.0],
                "col6": [11.0, 12.0],
                "col7": [11.0, 12.0],
                "col8": [11.0, 12.0],
                "col9": [11.0, 12.0],
                "col10": [11.0, 12.0],
                "col11": [11.0, 12.0],
            }
        )
        row = pd.Series({"id": "F2.0"})

        with self.assertRaises(ValueError):
            _check_index_row_validity(
                idx_end_leadtime=0,
                last_valid_idx=1,
                r=row,
                oper_sched=oper_sched,
            )


class TestComputeOperationDatetimes(unittest.TestCase):
    @patch(
        "oriom.core.functions.logs_timeseries.logs_corrective_aux.logs_timeseries_func.create_data"
    )
    def test_compute_operation_datetimes_basic(self, mock_create_data):
        """Basic path: no additional operation, full dictionary of dates is returned."""
        base_dt = datetime(2025, 1, 1, 0, 0)
        # Series mimicking a schedule row
        sched_row = pd.Series(
            {
                "datetime": base_dt,
                "wait_start": 1.0,
                "dur_net_port": 2.0,
                "wait_port": 1.0,
                "transit_to_site": 3.0,
                "wait_site": 2.0,
                "dur_net_site": 4.0,
                "transit_to_port": 1.0,
                "dur_total": 14.0,
            }
        )

        # create_data simply adds "value" hours to the start datetime
        def fake_create_data(row, col_name, start):
            return start + timedelta(hours=float(row[col_name]))

        mock_create_data.side_effect = fake_create_data

        oper_stat = DummyOperStat(dur_total_dict={"1": 100.0})

        result = compute_operation_datetimes(sched_row, oper_stat)

        # date_end_leadtime is the original datetime
        self.assertEqual(result["date_end_leadtime"], base_dt)
        # date_end_wait_start is + wait_start
        self.assertEqual(
            result["date_end_wait_start"], base_dt + timedelta(hours=1.0)
        )
        # date_end_stat_chart uses dur_total_dict for the month (January -> "1")
        self.assertEqual(
            result["date_end_stat_chart"],
            base_dt + timedelta(hours=oper_stat.dur_total_dict["1"]),
        )
        # dur_total is passed through from the schedule row
        self.assertEqual(result["dur_total"], sched_row["dur_total"])

    @patch(
        "oriom.core.functions.logs_timeseries.logs_corrective_aux.logs_timeseries_func.create_data"
    )
    def test_additional_operation_delay_without_wait_start(self, mock_create_data):
        """When add_op_end is later than wait_site and wait_start is zero, diff_time in hours is returned."""
        base_dt = datetime(2025, 1, 1, 0, 0)
        sched_row = pd.Series(
            {
                "datetime": base_dt,
                "wait_start": 0.0,
                "dur_net_port": 2.0,
                "wait_port": 1.0,
                "transit_to_site": 3.0,
                "wait_site": 2.0,
                "dur_net_site": 4.0,
                "transit_to_port": 1.0,
                "dur_total": 14.0,
            }
        )

        def fake_create_data(row, col_name, start):
            return start + timedelta(hours=float(row[col_name]))

        mock_create_data.side_effect = fake_create_data
        oper_stat = DummyOperStat(dur_total_dict={"1": 50.0})

        # Reproduce internal chain to build date_end_wait_site
        date_end_wait_start = base_dt + timedelta(hours=sched_row["wait_start"])
        date_end_dur_net_work_port = date_end_wait_start + timedelta(
            hours=sched_row["dur_net_port"]
        )
        date_end_dur_net_port = date_end_dur_net_work_port + timedelta(
            hours=sched_row["wait_port"]
        )
        date_end_transit_ts = date_end_dur_net_port + timedelta(
            hours=sched_row["transit_to_site"]
        )
        date_end_wait_site = date_end_transit_ts + timedelta(
            hours=sched_row["wait_site"]
        )

        # Additional operation ends 5 hours after date_end_wait_site
        add_op_end = date_end_wait_site + timedelta(hours=5)

        result = compute_operation_datetimes(
            sched_row, oper_stat, add_op_end=add_op_end
        )

        self.assertIn("diff_time", result)
        self.assertEqual(result["diff_time"], 5)

    @patch(
        "oriom.core.functions.logs_timeseries.logs_corrective_aux.logs_timeseries_func.create_data"
    )
    def test_additional_operation_delay_with_wait_start(self, mock_create_data):
        """
        When add_op_end is later than wait_site and wait_start > 0,
        diff_time + wait_start (rounded to int) is returned.
        """
        base_dt = datetime(2025, 1, 1, 0, 0)
        sched_row = pd.Series(
            {
                "datetime": base_dt,
                "wait_start": 2.0,
                "dur_net_port": 2.0,
                "wait_port": 1.0,
                "transit_to_site": 3.0,
                "wait_site": 2.0,
                "dur_net_site": 4.0,
                "transit_to_port": 1.0,
                "dur_total": 14.0,
            }
        )

        def fake_create_data(row, col_name, start):
            return start + timedelta(hours=float(row[col_name]))

        mock_create_data.side_effect = fake_create_data
        oper_stat = DummyOperStat(dur_total_dict={"1": 50.0})

        # Same chain as above
        date_end_wait_start = base_dt + timedelta(hours=sched_row["wait_start"])
        date_end_dur_net_work_port = date_end_wait_start + timedelta(
            hours=sched_row["dur_net_port"]
        )
        date_end_dur_net_port = date_end_dur_net_work_port + timedelta(
            hours=sched_row["wait_port"]
        )
        date_end_transit_ts = date_end_dur_net_port + timedelta(
            hours=sched_row["transit_to_site"]
        )
        date_end_wait_site = date_end_transit_ts + timedelta(
            hours=sched_row["wait_site"]
        )

        add_op_end = date_end_wait_site + timedelta(hours=5)
        result = compute_operation_datetimes(
            sched_row, oper_stat, add_op_end=add_op_end
        )

        self.assertIn("diff_time", result)
        # Base diff_time = 5, wait_start = 2 -> expected 7
        self.assertEqual(result["diff_time"], 7)


class TestCreateOperationSite(unittest.TestCase):
    @patch(
        "oriom.core.functions.logs_timeseries.logs_corrective_aux.compute_operation_datetimes"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.logs_corrective_aux._check_index_row_validity"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.logs_corrective_aux.CorrectionImmediate"
    )
    def test_immediate_strategy_returns_row_and_mobilisation(
        self, MockImmediate, mock_check_validity, mock_compute_dates
    ):
        """Immediate maintenance: an operation row and a mobilisation line are returned."""
        base_dt = datetime(2025, 1, 1, 0, 0)

        failure = DummyFailure(maintenance_strategy="immediately")
        vessel = DummyVessel(vessel_id="V1", vessel_type="workboat")
        operation = DummyOperation(op_id="OP1")
        oper_stat = DummyOperStat(dur_total_dict={"1": 10.0})
        oper_sched = pd.DataFrame({"datetime": [base_dt + timedelta(hours=i) for i in range(5)]})

        failure_dict = {"failure": failure, "date_failure": base_dt}
        vessel_dict = {"vessel": vessel, "vessel_to_merge": []}
        vessels_dict = {
            "vessel1_id": "V1",
            "ves_1": 1,
            "vessel2_id": None,
            "ves_2": None,
        }
        oper_dict = {
            "oper": operation,
            "oper_stat": oper_stat,
            "oper_sched": oper_sched,
        }
        mobilisation_dict = {"mob_time": 2, "lead_mob_time": 2}
        row_series = pd.Series({"id": "F1.0"})
        row_dict = {
            "row": row_series,
            "tow_op_flag": False,
            "log_events": pd.DataFrame(columns=LOG_COLS),
        }
        index_dict = {"fail_index": 0, "last_valid_idx": len(oper_sched) - 1}
        const_dict = {
            "COLS": LOG_COLS,
            "CUTOFF_DATE": base_dt + timedelta(days=1),
            "time_fail_op_immediately": 1.0,
        }

        # Stub CorrectionImmediate behaviour
        class StubImmediate:
            def __init__(self, date_failure, vessel, oper, time_fail_op_immediately, tow_op):
                self.date_failure = date_failure
                # Start from failure + time_fail_op_immediately
                self.date_op = date_failure + timedelta(hours=time_fail_op_immediately)
                self.idx_end_leadtime = None

            def mobilitate_vessel(self, log_events, r):
                # One simple mobilisation row
                return pd.DataFrame(
                    [[self.date_failure]],
                    columns=["d_trigger"],
                )

            def add_hours_for_noon_shift(self, fail_index, lead_mob_time, oper_sched):
                # For the test, simply set idx_end_leadtime
                self.idx_end_leadtime = fail_index + lead_mob_time
                self.date_op = oper_sched.iloc[self.idx_end_leadtime]["datetime"]

        MockImmediate.side_effect = StubImmediate

        # _check_index_row_validity returns a schedule row as a Series
        mock_check_validity.return_value = pd.Series(
            {
                "datetime": base_dt,
                "wait_start": 1.0,
                "dur_net_port": 1.0,
                "wait_port": 0.0,
                "transit_to_site": 0.0,
                "wait_site": 0.0,
                "dur_net_site": 0.0,
                "transit_to_port": 0.0,
                "dur_total": 2.0,
            }
        )

        # compute_operation_datetimes returns a fixed set of dates
        mock_compute_dates.return_value = {
            "date_end_leadtime": base_dt,
            "date_end_wait_start": base_dt + timedelta(hours=1),
            "date_end_dur_net_port": base_dt + timedelta(hours=2),
            "date_end_transit_ts": base_dt + timedelta(hours=3),
            "date_end_wait_site": base_dt + timedelta(hours=4),
            "date_end_dur_net_site": base_dt + timedelta(hours=5),
            "date_end_transit_tp": base_dt + timedelta(hours=6),
            "date_end": base_dt + timedelta(hours=7),
            "date_end_stat_chart": base_dt + timedelta(hours=8),
            "dur_total": 2.0,
        }

        row_dates, row_mob_line = create_operation_site(
            failure_=failure_dict,
            vessel_=vessel_dict,
            vessels_=vessels_dict,
            oper_=oper_dict,
            mobilisation=mobilisation_dict,
            row_=row_dict,
            index=index_dict,
            CONST=const_dict,
        )

        # Operation row is created
        self.assertIsInstance(row_dates, pd.DataFrame)
        self.assertEqual(len(row_dates), 1)
        self.assertEqual(row_dates.iloc[0]["event"], "operation")
        self.assertEqual(row_dates.iloc[0]["id"], "OP1")
        self.assertEqual(row_dates.iloc[0]["vessel_1"], "V1")
        self.assertEqual(row_dates.iloc[0]["n_vessel_1"], 1)
        self.assertEqual(row_dates.iloc[0]["comments"], "oper_F1.0")

        # Mobilisation line is also returned
        self.assertIsInstance(row_mob_line, pd.DataFrame)
        self.assertEqual(row_mob_line.iloc[0]["d_trigger"], base_dt)

    @patch(
        "oriom.core.functions.logs_timeseries.logs_corrective_aux.compute_operation_datetimes"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.logs_corrective_aux._check_index_row_validity"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.logs_corrective_aux.CorrectionDeferred"
    )
    def test_deferred_strategy_returns_operation_row(
        self, MockDeferred, mock_check_validity, mock_compute_dates
    ):
        """Deferred (specific month) maintenance produces an operation row when a valid index is found."""
        base_dt = datetime(2025, 1, 10, 0, 0)

        failure = DummyFailure(maintenance_strategy="specific month", preferred_month=2)
        vessel = DummyVessel(vessel_id="V2")
        operation = DummyOperation(op_id="OP2")
        oper_stat = DummyOperStat(dur_total_dict={"2": 20.0})
        oper_sched = pd.DataFrame({"datetime": [base_dt + timedelta(hours=i) for i in range(5)]})

        failure_dict = {"failure": failure, "date_failure": base_dt}
        vessel_dict = {"vessel": vessel, "vessel_to_merge": []}
        vessels_dict = {
            "vessel1_id": "V2",
            "ves_1": 1,
            "vessel2_id": None,
            "ves_2": None,
        }
        oper_dict = {
            "oper": operation,
            "oper_stat": oper_stat,
            "oper_sched": oper_sched,
        }
        mobilisation_dict = {"mob_time": 1, "lead_mob_time": 1}
        row_series = pd.Series({"id": "F2.0"})
        row_dict = {
            "row": row_series,
            "tow_op_flag": False,
            "log_events": pd.DataFrame(columns=LOG_COLS),
        }
        index_dict = {"fail_index": 0, "last_valid_idx": len(oper_sched) - 1}
        const_dict = {
            "COLS": LOG_COLS,
            "CUTOFF_DATE": base_dt + timedelta(days=60),
            "time_fail_op_immediately": 1.0,
        }

        class StubDeferred:
            def __init__(self, date_failure, vessel, oper, preferred_month, tow_op):
                self.date_failure = date_failure
                self.date_op = date_failure
                self.idx_end_leadtime = 0

            def leadtime_evaluation(self, lead_mob_time):
                self.idx_end_leadtime = 0

            def add_leadtime_tow(self, lead_mob_time):
                self.idx_end_leadtime = 0

            def check_leadtime_index(self, oper_sched, CUTOFF_DATE):
                return True

        MockDeferred.side_effect = StubDeferred

        mock_check_validity.return_value = pd.Series(
            {
                "datetime": base_dt,
                "wait_start": 0.0,
                "dur_net_port": 1.0,
                "wait_port": 0.0,
                "transit_to_site": 0.0,
                "wait_site": 0.0,
                "dur_net_site": 0.0,
                "transit_to_port": 0.0,
                "dur_total": 1.0,
            }
        )

        mock_compute_dates.return_value = {
            "date_end_leadtime": base_dt,
            "date_end_wait_start": base_dt,
            "date_end_dur_net_port": base_dt + timedelta(hours=1),
            "date_end_transit_ts": base_dt + timedelta(hours=1),
            "date_end_wait_site": base_dt + timedelta(hours=1),
            "date_end_dur_net_site": base_dt + timedelta(hours=1),
            "date_end_transit_tp": base_dt + timedelta(hours=1),
            "date_end": base_dt + timedelta(hours=1),
            "date_end_stat_chart": base_dt + timedelta(hours=oper_stat.dur_total_dict["2"]),
            "dur_total": 1.0,
        }

        row_dates, row_mob_line = create_operation_site(
            failure_=failure_dict,
            vessel_=vessel_dict,
            vessels_=vessels_dict,
            oper_=oper_dict,
            mobilisation=mobilisation_dict,
            row_=row_dict,
            index=index_dict,
            CONST=const_dict,
        )

        self.assertIsInstance(row_dates, pd.DataFrame)
        self.assertEqual(len(row_dates), 1)
        self.assertEqual(row_dates.iloc[0]["event"], "operation")
        self.assertEqual(row_dates.iloc[0]["id"], "OP2")
        self.assertIsNone(row_mob_line)

    @patch(
        "oriom.core.functions.logs_timeseries.logs_corrective_aux.CorrectionDeferred"
    )
    def test_deferred_strategy_no_valid_index_returns_none(self, MockDeferred):
        """If deferred correction does not find a valid index, (None, None) must be returned."""
        base_dt = datetime(2025, 1, 10, 0, 0)

        failure = DummyFailure(maintenance_strategy="specific month", preferred_month=2)
        vessel = DummyVessel(vessel_id="V3")
        operation = DummyOperation(op_id="OP3")
        oper_stat = DummyOperStat(dur_total_dict={"2": 20.0})
        oper_sched = pd.DataFrame({"datetime": [base_dt + timedelta(hours=i) for i in range(5)]})

        failure_dict = {"failure": failure, "date_failure": base_dt}
        vessel_dict = {"vessel": vessel, "vessel_to_merge": []}
        vessels_dict = {
            "vessel1_id": "V3",
            "ves_1": 1,
            "vessel2_id": None,
            "ves_2": None,
        }
        oper_dict = {
            "oper": operation,
            "oper_stat": oper_stat,
            "oper_sched": oper_sched,
        }
        mobilisation_dict = {"mob_time": 1, "lead_mob_time": 1}
        row_series = pd.Series({"id": "F3.0"})
        row_dict = {
            "row": row_series,
            "tow_op_flag": False,
            "log_events": pd.DataFrame(columns=LOG_COLS),
        }
        index_dict = {"fail_index": 0, "last_valid_idx": len(oper_sched) - 1}
        const_dict = {
            "COLS": LOG_COLS,
            "CUTOFF_DATE": base_dt + timedelta(days=60),
            "time_fail_op_immediately": 1.0,
        }

        class StubDeferred:
            def __init__(self, date_failure, vessel, oper, preferred_month, tow_op):
                self.date_failure = date_failure
                self.date_op = date_failure
                self.idx_end_leadtime = 0

            def leadtime_evaluation(self, lead_mob_time):
                self.idx_end_leadtime = 0

            def add_leadtime_tow(self, lead_mob_time):
                self.idx_end_leadtime = 0

            def check_leadtime_index(self, oper_sched, CUTOFF_DATE):
                return False

        MockDeferred.side_effect = StubDeferred

        row_dates, row_mob_line = create_operation_site(
            failure_=failure_dict,
            vessel_=vessel_dict,
            vessels_=vessels_dict,
            oper_=oper_dict,
            mobilisation=mobilisation_dict,
            row_=row_dict,
            index=index_dict,
            CONST=const_dict,
        )

        self.assertIsNone(row_dates)
        self.assertIsNone(row_mob_line)

    def test_unknown_maintenance_strategy_raises_keyerror(self):
        """An unknown maintenance strategy must raise a KeyError."""
        base_dt = datetime(2025, 1, 1, 0, 0)

        failure = DummyFailure(maintenance_strategy="unknown_strategy")
        vessel = DummyVessel(vessel_id="V4")
        operation = DummyOperation(op_id="OP4")
        oper_stat = DummyOperStat(dur_total_dict={"1": 10.0})
        oper_sched = pd.DataFrame({"datetime": [base_dt]})

        failure_dict = {"failure": failure, "date_failure": base_dt}
        vessel_dict = {"vessel": vessel, "vessel_to_merge": []}
        vessels_dict = {
            "vessel1_id": "V4",
            "ves_1": 1,
            "vessel2_id": None,
            "ves_2": None,
        }
        oper_dict = {
            "oper": operation,
            "oper_stat": oper_stat,
            "oper_sched": oper_sched,
        }
        mobilisation_dict = {"mob_time": 0, "lead_mob_time": 0}
        row_series = pd.Series({"id": "F4.0"})
        row_dict = {
            "row": row_series,
            "tow_op_flag": False,
            "log_events": pd.DataFrame(columns=LOG_COLS),
        }
        index_dict = {"fail_index": 0, "last_valid_idx": 0}
        const_dict = {
            "COLS": LOG_COLS,
            "CUTOFF_DATE": base_dt + timedelta(days=1),
            "time_fail_op_immediately": 1.0,
        }

        with self.assertRaises(KeyError):
            create_operation_site(
                failure_=failure_dict,
                vessel_=vessel_dict,
                vessels_=vessels_dict,
                oper_=oper_dict,
                mobilisation=mobilisation_dict,
                row_=row_dict,
                index=index_dict,
                CONST=const_dict,
            )

    @patch(
        "oriom.core.functions.logs_timeseries.logs_corrective_aux.compute_operation_datetimes"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.logs_corrective_aux._check_index_row_validity"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.logs_corrective_aux.CorrectionImmediate"
    )
    def test_additional_operation_diff_time_branch(
        self, MockImmediate, mock_check_validity, mock_compute_dates
    ):
        """
        When compute_operation_datetimes returns a diff_time key, the function must
        call _check_index_row_validity and compute_operation_datetimes a second time.
        """
        base_dt = datetime(2025, 1, 1, 0, 0)

        failure = DummyFailure(maintenance_strategy="immediately")
        vessel = DummyVessel(vessel_id="V5")
        operation = DummyOperation(op_id="OP5")
        oper_stat = DummyOperStat(dur_total_dict={"1": 10.0})
        oper_sched = pd.DataFrame({"datetime": [base_dt + timedelta(hours=i) for i in range(10)]})

        failure_dict = {"failure": failure, "date_failure": base_dt}
        vessel_dict = {"vessel": vessel, "vessel_to_merge": []}
        vessels_dict = {
            "vessel1_id": "V5",
            "ves_1": 1,
            "vessel2_id": None,
            "ves_2": None,
        }
        oper_dict = {
            "oper": operation,
            "oper_stat": oper_stat,
            "oper_sched": oper_sched,
        }
        mobilisation_dict = {"mob_time": 0, "lead_mob_time": 0}
        row_series = pd.Series({"id": "F5.0"})
        row_dict = {
            "row": row_series,
            "tow_op_flag": False,
            "log_events": pd.DataFrame(columns=LOG_COLS),
        }
        index_dict = {"fail_index": 0, "last_valid_idx": len(oper_sched) - 1}
        const_dict = {
            "COLS": LOG_COLS,
            "CUTOFF_DATE": base_dt + timedelta(days=1),
            "time_fail_op_immediately": 1.0,
        }

        class StubImmediate:
            def __init__(self, date_failure, vessel, oper, time_fail_op_immediately, tow_op):
                self.date_failure = date_failure
                self.date_op = date_failure + timedelta(hours=time_fail_op_immediately)
                self.idx_end_leadtime = 0

            def mobilitate_vessel(self, log_events, r):
                return None

            def add_hours_for_noon_shift(self, fail_index, lead_mob_time, oper_sched):
                self.idx_end_leadtime = fail_index

        MockImmediate.side_effect = StubImmediate

        # First validity check result (before delay) and second (after applying diff_time)
        first_row = pd.Series(
            {
                "datetime": base_dt,
                "wait_start": 0.0,
                "dur_net_port": 1.0,
                "wait_port": 0.0,
                "transit_to_site": 0.0,
                "wait_site": 0.0,
                "dur_net_site": 0.0,
                "transit_to_port": 0.0,
                "dur_total": 1.0,
            }
        )
        second_row = first_row.copy()

        mock_check_validity.side_effect = [first_row, second_row]

        # First call returns diff_time only, second call returns full dates
        mock_compute_dates.side_effect = [
            {"diff_time": 3},
            {
                "date_end_leadtime": base_dt,
                "date_end_wait_start": base_dt,
                "date_end_dur_net_port": base_dt + timedelta(hours=1),
                "date_end_transit_ts": base_dt + timedelta(hours=1),
                "date_end_wait_site": base_dt + timedelta(hours=1),
                "date_end_dur_net_site": base_dt + timedelta(hours=1),
                "date_end_transit_tp": base_dt + timedelta(hours=1),
                "date_end": base_dt + timedelta(hours=1),
                "date_end_stat_chart": base_dt + timedelta(
                    hours=oper_stat.dur_total_dict["1"]
                ),
                "dur_total": 1.0,
            },
        ]

        row_dates, row_mob_line = create_operation_site(
            failure_=failure_dict,
            vessel_=vessel_dict,
            vessels_=vessels_dict,
            oper_=oper_dict,
            mobilisation=mobilisation_dict,
            row_=row_dict,
            index=index_dict,
            CONST=const_dict,
        )

        # compute_operation_datetimes is called twice due to diff_time
        self.assertEqual(mock_compute_dates.call_count, 2)
        self.assertIsInstance(row_dates, pd.DataFrame)
        self.assertEqual(len(row_dates), 1)
        self.assertEqual(row_dates.iloc[0]["event"], "operation")


if __name__ == "__main__":
    unittest.main(verbosity=2)