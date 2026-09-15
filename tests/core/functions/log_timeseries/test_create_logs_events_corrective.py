# test_create_logs_corrective.py

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import pandas as pd

from oriom.core.functions.logs_timeseries import create_logs_events_corrective 

# Keep the same column set used by the production code/tests.
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


# -----------------
# Helpers / dummies
# -----------------

def make_oper_sched(start_dt, n_rows=24, step_h=1):
    """Create a minimal operation schedule with an hourly 'datetime' column."""
    dts = [start_dt + timedelta(hours=i * step_h) for i in range(n_rows)]
    return pd.DataFrame({"datetime": dts})


class DummyTS:
    def __init__(self, oper_sched, last_valid_index=None):
        self.oper_sched = oper_sched
        if last_valid_index is None and oper_sched is not None:
            last_valid_index = len(oper_sched) - 1
        self.last_valid_index = last_valid_index


class DummyVessel:
    def __init__(self, id_, mobilisation_time=0, vtype="workboat", vessel_n=None):
        self.id = id_
        self.mobilisation_time = mobilisation_time
        self.type = vtype
        self.vessel_n = vessel_n


class DummyOp:
    def __init__(
        self,
        id_,
        vessel1,
        vessel2=None,
        vessel2_id=None,
        vessel2_qt=None,
        ts_data=None,
        tow_to_port=False,
        op_tow_port=None,
        op_tow_site=None,
        op_tow_site_port=None,
        addition_op_tow=None,
        fail = None
    ):
        self.id = id_
        self.vessel1 = vessel1
        self.vessel2 = vessel2

        self.vessel1_id = vessel1.id
        self.vessel1_qt = 1

        self.vessel2_id = vessel2.id if vessel2 else None
        if vessel2:
            if getattr(vessel2, 'vessel_n', False):
                vessel_n = vessel2.vessel_n
            else:
                vessel_n = 1
        else:
            vessel_n = None
        
        self.vessel2_qt = vessel_n

        self.ts_data = ts_data

        # Towing-related flags/refs
        self.tow_to_port = tow_to_port
        self.op_tow_port = op_tow_port
        self.op_tow_site = op_tow_site
        self.addition_op_tow = addition_op_tow
        self.op_tow_site_port = op_tow_site_port
        self.failures = []
        if fail:
            self.failures = [DummyFailure("immediately", lead_time=0)]

        # Present in your original dummy; keep for compatibility.
        self.tow_to_site_dict = {"1": 0}


class DummyOperStat:
    def __init__(self, op_class, dur_total_dict=None):
        self.op_class = op_class
        self.dur_total_dict = dur_total_dict or {"1": 1}


class DummyFailure:
    def __init__(self, maintenance_strategy, lead_time=0, preferred_month=None):
        self.maintenance_strategy = maintenance_strategy
        self.lead_time = lead_time
        self.preferred_month = preferred_month
        self.level_failure = 'device'

class DummyFinder:
    def __init__(
        self,
        vessel_map=None,
        failure_map=None,
        op_stats_pmax_map=None,
        operations=None,
    ):
        self.vessel_map = vessel_map or {}
        self.failure_map = failure_map or {}
        self.op_stats_pmax_map = op_stats_pmax_map or {}
        self.operations = operations or {}

    def find_vessel(self, vessel_id):
        return self.vessel_map[vessel_id]

    def find_failure_from_id(self, fail_id):
        return self.failure_map[fail_id]

    def find_operation_stats_pmax(self, op_id):
        return self.op_stats_pmax_map[op_id]

    def find_operation(self, op_id):
        return self.operations[op_id]


def failure_df_to_logevent_df_stub(dates_failures: pd.DataFrame, cols: list) -> pd.DataFrame:
    """Generate deterministic 'failure' log rows from dates_failures."""
    rows = []
    for _, r in dates_failures.iterrows():
        row = {c: None for c in cols}
        if "d_trigger" in cols:
            row["d_trigger"] = r["datetime"]
        if "event" in cols:
            row["event"] = "failure"
        if "id" in cols:
            row["id"] = r["id"]
        if "comments" in cols:
            row["comments"] = f"failure_{r['id']}"
        rows.append(row)
    return pd.DataFrame(rows, columns=cols)


def build_single_operation_row(cols, oper_id, vessel1_id, vessel2_id=None, date_failure=None, lead_h=0):
    """Build a minimal operation row consistent with LOG_COLS."""
    date_failure = date_failure or datetime(2025, 1, 1)
    d_end_leadtime = date_failure + timedelta(hours=lead_h)
    d_end_wait_start = d_end_leadtime + timedelta(hours=1)
    d_end = d_end_wait_start + timedelta(hours=1)

    row = {c: None for c in cols}
    row.update(
        {
            "d_trigger": date_failure,
            "d_end_leadtime": d_end_leadtime,
            "d_end_wait_start": d_end_wait_start,
            "d_end": d_end,
            "event": "operation",
            "id": oper_id,
            "vessel_1": vessel1_id,
            "n_vessel_1": 1,
            "vessel_2": vessel2_id,
            "n_vessel_2": 1 if vessel2_id else None,
            "comments": "operation_row",
        }
    )
    return pd.DataFrame([row], columns=cols)


def build_single_mobilisation_row(cols, oper_id, vessel1_id, date_failure=None):
    """Build a minimal mobilisation row; d_end will be overwritten by the function under test."""
    date_failure = date_failure or datetime(2025, 1, 1)
    row = {c: None for c in cols}
    row.update(
        {
            "d_trigger": date_failure,
            "d_end": date_failure,  # placeholder: should be overwritten by create_logs_events_corrective.create_logs_corrective_file
            "event": "mobilisation",
            "id": oper_id,
            "vessel_1": vessel1_id,
            "n_vessel_1": 1,
            "comments": "mobilisation_row",
        }
    )
    return pd.DataFrame([row], columns=cols)


# -----------------
# Test cases
# -----------------

class TestCreateLogsCorrectiveFile(unittest.TestCase):

    def test_returns_empty_if_dates_failures_empty(self):
        cutoff = datetime(2025, 1, 1)
        finder = DummyFinder()

        out = create_logs_events_corrective.create_logs_corrective_file(
            COLS=LOG_COLS,
            CUTOFF_DATE=cutoff,
            dates_failures=pd.DataFrame(),
            operation_log_file_stats=[],
            time_fail_op_immediately_original=1,
            vessel_to_merge=[],
            find_element_class=finder,
        )
        self.assertTrue(out.empty)
        self.assertEqual(list(out.columns), LOG_COLS)

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df",
        side_effect=failure_df_to_logevent_df_stub,
    )
    @patch("oriom.core.functions.logs_timeseries.create_logs_events_corrective.create_operation_site")
    def test_failure_beyond_cutoff_creates_no_operations(self, mock_create_op, _mock_fail_to_log):
        base = datetime(2025, 1, 1)
        cutoff = base + timedelta(days=1)

        vessel = DummyVessel("V1")
        oper_sched = make_oper_sched(base)
        op = DummyOp("opA", vessel1=vessel, ts_data=DummyTS(oper_sched))
        stat = DummyOperStat(op)

        # Failure occurs after cutoff => should not create an operation row.
        dates_failures = pd.DataFrame(
            [
                {
                    "datetime": cutoff + timedelta(days=10),
                    "id": "F001.0",
                    "maintenance_strategy": "immediately",
                    "operation_triggered": op.id.lower(),
                }
            ]
        )

        finder = DummyFinder(
            vessel_map={"V1": vessel},
            failure_map={"F001": DummyFailure("immediately", lead_time=0)},
        )

        out = create_logs_events_corrective.create_logs_corrective_file(
            COLS=LOG_COLS,
            CUTOFF_DATE=cutoff,
            dates_failures=dates_failures,
            operation_log_file_stats=[stat],
            time_fail_op_immediately_original=1,
            vessel_to_merge=[],
            find_element_class=finder,
        )

        # We still get the "failure" row coming from failure_df_to_logevent_df,
        # but we must not create "operation" rows.
        self.assertEqual((out["event"] == "operation").sum(), 0)
        mock_create_op.assert_not_called()

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df",
        side_effect=failure_df_to_logevent_df_stub,
    )
    @patch("oriom.core.functions.logs_timeseries.create_logs_events_corrective.create_operation_site")
    def test_never_repair_is_filtered_for_operations_only(self, mock_create_op, _mock_fail_to_log):
        base = datetime(2025, 1, 1)
        cutoff = base + timedelta(days=10)

        vessel = DummyVessel("V1")
        op = DummyOp("opA", vessel1=vessel, ts_data=DummyTS(make_oper_sched(base)))
        stat = DummyOperStat(op)

        dates_failures = pd.DataFrame(
            [
                {
                    "datetime": base,
                    "id": "F1.0",
                    "maintenance_strategy": "never repair",
                    "operation_triggered": op.id.lower(),
                },
                {
                    "datetime": base + timedelta(hours=1),
                    "id": "F2.0",
                    "maintenance_strategy": "immediately",
                    "operation_triggered": op.id.lower(),
                },
            ]
        )

        finder = DummyFinder(
            vessel_map={"V1": vessel},
            failure_map={
                "F1": DummyFailure("never repair", lead_time=0),
                "F2": DummyFailure("immediately", lead_time=0),
            },
        )

        # Return a minimal operation row so we can detect call count.
        def _stub_create_operation_site(**kwargs):
            cols = kwargs["CONST"]["COLS"]
            oper_obj = kwargs["oper_"]["oper"]
            vessel_obj = kwargs["vessel_"]["vessel"]
            lead_mob_time = kwargs["mobilisation"]["lead_mob_time"]
            row_dates = build_single_operation_row(
                cols=cols,
                oper_id=oper_obj.id,
                vessel1_id=vessel_obj.id,
                date_failure=kwargs["failure_"]["date_failure"],
                lead_h=int(lead_mob_time),
            )
            return row_dates, None

        mock_create_op.side_effect = _stub_create_operation_site

        out = create_logs_events_corrective.create_logs_corrective_file(
            COLS=LOG_COLS,
            CUTOFF_DATE=cutoff,
            dates_failures=dates_failures,
            operation_log_file_stats=[stat],
            time_fail_op_immediately_original=1,
            vessel_to_merge=[],
            find_element_class=finder,
        )

        # One operation row only (for the repairable failure).
        self.assertEqual((out["event"] == "operation").sum(), 1)
        self.assertEqual(mock_create_op.call_count, 1)

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df",
        side_effect=failure_df_to_logevent_df_stub,
    )
    @patch("oriom.core.functions.logs_timeseries.create_logs_events_corrective.create_operation_site")
    def test_lead_mob_time_passed_to_create_operation_site(self, mock_create_op, _mock_fail_to_log):
        base = datetime(2025, 1, 1)
        cutoff = base + timedelta(days=10)

        # mobilisation_time=2h, component lead_time=3h => lead_mob_time=max(2,3)=3
        vessel = DummyVessel("V1", mobilisation_time=2)
        op = DummyOp("opA", vessel1=vessel, ts_data=DummyTS(make_oper_sched(base)))
        stat = DummyOperStat(op)

        dates_failures = pd.DataFrame(
            [
                {
                    "datetime": base,
                    "id": "F1.0",
                    "maintenance_strategy": "immediately",
                    "operation_triggered": op.id.lower(),
                }
            ]
        )

        finder = DummyFinder(
            vessel_map={"V1": vessel},
            failure_map={"F1": DummyFailure("immediately", lead_time=3)},
        )

        captured = {}

        def _stub_create_operation_site(**kwargs):
            captured["mob_time"] = kwargs["mobilisation"]["mob_time"]
            captured["lead_mob_time"] = kwargs["mobilisation"]["lead_mob_time"]
            cols = kwargs["CONST"]["COLS"]
            oper_obj = kwargs["oper_"]["oper"]
            vessel_obj = kwargs["vessel_"]["vessel"]
            row_dates = build_single_operation_row(
                cols=cols,
                oper_id=oper_obj.id,
                vessel1_id=vessel_obj.id,
                date_failure=kwargs["failure_"]["date_failure"],
                lead_h=int(kwargs["mobilisation"]["lead_mob_time"]),
            )
            return row_dates, None

        mock_create_op.side_effect = _stub_create_operation_site

        _ = create_logs_events_corrective.create_logs_corrective_file(
            COLS=LOG_COLS,
            CUTOFF_DATE=cutoff,
            dates_failures=dates_failures,
            operation_log_file_stats=[stat],
            time_fail_op_immediately_original=1,
            vessel_to_merge=[],
            find_element_class=finder,
        )

        self.assertEqual(captured["mob_time"], 2)
        self.assertEqual(captured["lead_mob_time"], 3)

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df",
        side_effect=failure_df_to_logevent_df_stub,
    )
    @patch("oriom.core.functions.logs_timeseries.create_logs_events_corrective.create_operation_site")
    def test_matching_index_is_passed_to_create_operation_site(self, mock_create_op, _mock_fail_to_log):
        base = datetime(2025, 1, 1)
        cutoff = base + timedelta(days=10)

        sched = make_oper_sched(base, n_rows=12)
        vessel = DummyVessel("V1")
        op = DummyOp("opA", vessel1=vessel, ts_data=DummyTS(sched))
        stat = DummyOperStat(op)

        # Put failure exactly at schedule index 4.
        failure_dt = sched.iloc[4]["datetime"]

        dates_failures = pd.DataFrame(
            [
                {
                    "datetime": failure_dt,
                    "id": "F1.0",
                    "maintenance_strategy": "immediately",
                    "operation_triggered": op.id.lower(),
                }
            ]
        )

        finder = DummyFinder(
            vessel_map={"V1": vessel},
            failure_map={"F1": DummyFailure("immediately", lead_time=0)},
        )

        captured = {}

        def _stub_create_operation_site(**kwargs):
            captured["fail_index"] = kwargs["index"]["fail_index"]
            cols = kwargs["CONST"]["COLS"]
            oper_obj = kwargs["oper_"]["oper"]
            vessel_obj = kwargs["vessel_"]["vessel"]
            row_dates = build_single_operation_row(
                cols=cols,
                oper_id=oper_obj.id,
                vessel1_id=vessel_obj.id,
                date_failure=kwargs["failure_"]["date_failure"],
                lead_h=0,
            )
            return row_dates, None

        mock_create_op.side_effect = _stub_create_operation_site

        _ = create_logs_events_corrective.create_logs_corrective_file(
            COLS=LOG_COLS,
            CUTOFF_DATE=cutoff,
            dates_failures=dates_failures,
            operation_log_file_stats=[stat],
            time_fail_op_immediately_original=1,
            vessel_to_merge=[],
            find_element_class=finder,
        )

        self.assertEqual(captured["fail_index"], 4)

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df",
        side_effect=failure_df_to_logevent_df_stub,
    )
    @patch("oriom.core.functions.logs_timeseries.create_logs_events_corrective.create_operation_site")
    def test_vessel2_fields_are_propagated(self, mock_create_op, _mock_fail_to_log):
        base = datetime(2025, 1, 1)
        cutoff = base + timedelta(days=10)

        v1 = DummyVessel("A")
        v2 = DummyVessel("B")
        op = DummyOp("opAB", vessel1=v1, vessel2=v2, ts_data=DummyTS(make_oper_sched(base)))
        stat = DummyOperStat(op)

        dates_failures = pd.DataFrame(
            [
                {
                    "datetime": base,
                    "id": "FX.0",
                    "maintenance_strategy": "immediately",
                    "operation_triggered": op.id.lower(),
                }
            ]
        )

        finder = DummyFinder(
            vessel_map={"A": v1, "B": v2},
            failure_map={"FX": DummyFailure("immediately", lead_time=0)},
        )

        def _stub_create_operation_site(**kwargs):
            cols = kwargs["CONST"]["COLS"]
            oper_obj = kwargs["oper_"]["oper"]
            vessel_obj = kwargs["vessel_"]["vessel"]
            vessel2_id = kwargs["vessels_"]["vessel2_id"]
            lead_mob_time = kwargs["mobilisation"]["lead_mob_time"]
            row_dates = build_single_operation_row(
                cols=cols,
                oper_id=oper_obj.id,
                vessel1_id=vessel_obj.id,
                vessel2_id=vessel2_id,
                date_failure=kwargs["failure_"]["date_failure"],
                lead_h=int(lead_mob_time),
            )
            return row_dates, None

        mock_create_op.side_effect = _stub_create_operation_site

        out = create_logs_events_corrective.create_logs_corrective_file(
            COLS=LOG_COLS,
            CUTOFF_DATE=cutoff,
            dates_failures=dates_failures,
            operation_log_file_stats=[stat],
            time_fail_op_immediately_original=1,
            vessel_to_merge=[],
            find_element_class=finder,
        )

        ops = out[out["event"] == "operation"]
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops.iloc[0]["vessel_2"], "B")
        self.assertEqual(ops.iloc[0]["n_vessel_2"], 1)

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df",
        side_effect=failure_df_to_logevent_df_stub,
    )
    @patch("oriom.core.functions.logs_timeseries.create_logs_events_corrective.create_operation_site")
    def test_multiple_failures_create_multiple_operations(self, mock_create_op, _mock_fail_to_log):
        base = datetime(2025, 1, 1)
        cutoff = base + timedelta(days=10)

        vessel = DummyVessel("V1")
        op = DummyOp("opM", vessel1=vessel, ts_data=DummyTS(make_oper_sched(base)))
        stat = DummyOperStat(op)

        dates_failures = pd.DataFrame(
            [
                {
                    "datetime": base,
                    "id": "F1.0",
                    "maintenance_strategy": "immediately",
                    "operation_triggered": op.id.lower(),
                },
                {
                    "datetime": base + timedelta(hours=1),
                    "id": "F2.0",
                    "maintenance_strategy": "immediately",
                    "operation_triggered": op.id.lower(),
                },
            ]
        )

        finder = DummyFinder(
            vessel_map={"V1": vessel},
            failure_map={
                "F1": DummyFailure("immediately", lead_time=0),
                "F2": DummyFailure("immediately", lead_time=0),
            },
        )

        def _stub_create_operation_site(**kwargs):
            cols = kwargs["CONST"]["COLS"]
            oper_obj = kwargs["oper_"]["oper"]
            vessel_obj = kwargs["vessel_"]["vessel"]
            row_dates = build_single_operation_row(
                cols=cols,
                oper_id=oper_obj.id,
                vessel1_id=vessel_obj.id,
                date_failure=kwargs["failure_"]["date_failure"],
                lead_h=0,
            )
            return row_dates, None

        mock_create_op.side_effect = _stub_create_operation_site

        out = create_logs_events_corrective.create_logs_corrective_file(
            COLS=LOG_COLS,
            CUTOFF_DATE=cutoff,
            dates_failures=dates_failures,
            operation_log_file_stats=[stat],
            time_fail_op_immediately_original=1,
            vessel_to_merge=[],
            find_element_class=finder,
        )

        ops = out[out["event"] == "operation"]
        self.assertEqual(len(ops), 2)
        self.assertEqual(mock_create_op.call_count, 2)

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df",
        side_effect=failure_df_to_logevent_df_stub,
    )
    @patch("oriom.core.functions.logs_timeseries.create_logs_events_corrective.create_operation_site")
    def test_operation_trigger_mismatch_skips_operations(self, mock_create_op, _mock_fail_to_log):
        base = datetime(2025, 1, 1)
        cutoff = base + timedelta(days=10)

        vessel = DummyVessel("V1")
        op = DummyOp("opA", vessel1=vessel, ts_data=DummyTS(make_oper_sched(base)))
        stat = DummyOperStat(op)

        # operation_triggered does not match op.id.lower() => filtered out.
        dates_failures = pd.DataFrame(
            [
                {
                    "datetime": base,
                    "id": "FX.0",
                    "maintenance_strategy": "immediately",
                    "operation_triggered": "missing_op",
                }
            ]
        )

        finder = DummyFinder(
            vessel_map={"V1": vessel},
            failure_map={"FX": DummyFailure("immediately", lead_time=0)},
        )

        out = create_logs_events_corrective.create_logs_corrective_file(
            COLS=LOG_COLS,
            CUTOFF_DATE=cutoff,
            dates_failures=dates_failures,
            operation_log_file_stats=[stat],
            time_fail_op_immediately_original=1,
            vessel_to_merge=[],
            find_element_class=finder,
        )

        self.assertEqual((out["event"] == "operation").sum(), 0)
        mock_create_op.assert_not_called()

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df",
        side_effect=failure_df_to_logevent_df_stub,
    )
    def test_missing_oper_sched_raises_filenotfound(self, _mock_fail_to_log):
        base = datetime(2025, 1, 1)
        cutoff = base + timedelta(days=10)

        vessel = DummyVessel("V1")
        # ts_data missing schedule => safe_getattr returns None => FileNotFoundError
        op = DummyOp("opA", vessel1=vessel, ts_data=DummyTS(oper_sched=None, last_valid_index=None))
        stat = DummyOperStat(op)

        dates_failures = pd.DataFrame(
            [
                {
                    "datetime": base,
                    "id": "F1.0",
                    "maintenance_strategy": "immediately",
                    "operation_triggered": op.id.lower(),
                }
            ]
        )

        finder = DummyFinder(
            vessel_map={"V1": vessel},
            failure_map={"F1": DummyFailure("immediately", lead_time=0)},
        )

        with self.assertRaises(FileNotFoundError):
            create_logs_events_corrective.create_logs_corrective_file(
                COLS=LOG_COLS,
                CUTOFF_DATE=cutoff,
                dates_failures=dates_failures,
                operation_log_file_stats=[stat],
                time_fail_op_immediately_original=1,
                vessel_to_merge=[],
                find_element_class=finder,
            )

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df",
        side_effect=failure_df_to_logevent_df_stub,
    )
    @patch("oriom.core.functions.logs_timeseries.create_logs_events_corrective.create_operation_site")
    def test_mobilisation_row_d_end_is_overwritten_with_end_wait_start(self, mock_create_op, _mock_fail_to_log):
        base = datetime(2025, 1, 1)
        cutoff = base + timedelta(days=10)

        vessel = DummyVessel("V1", mobilisation_time=2)
        op = DummyOp("opA", vessel1=vessel, ts_data=DummyTS(make_oper_sched(base)))
        stat = DummyOperStat(op)

        dates_failures = pd.DataFrame(
            [
                {
                    "datetime": base,
                    "id": "F1.0",
                    "maintenance_strategy": "immediately",
                    "operation_triggered": op.id.lower(),
                }
            ]
        )

        finder = DummyFinder(
            vessel_map={"V1": vessel},
            failure_map={"F1": DummyFailure("immediately", lead_time=0)},
        )

        def _stub_create_operation_site(**kwargs):
            cols = kwargs["CONST"]["COLS"]
            oper_obj = kwargs["oper_"]["oper"]
            vessel_obj = kwargs["vessel_"]["vessel"]
            # Force a known end_wait_start so we can assert overwrite.
            row_dates = build_single_operation_row(
                cols=cols,
                oper_id=oper_obj.id,
                vessel1_id=vessel_obj.id,
                date_failure=kwargs["failure_"]["date_failure"],
                lead_h=0,
            )
            row_mob = build_single_mobilisation_row(
                cols=cols,
                oper_id=oper_obj.id,
                vessel1_id=vessel_obj.id,
                date_failure=kwargs["failure_"]["date_failure"],
            )
            return row_dates, row_mob

        mock_create_op.side_effect = _stub_create_operation_site

        out = create_logs_events_corrective.create_logs_corrective_file(
            COLS=LOG_COLS,
            CUTOFF_DATE=cutoff,
            dates_failures=dates_failures,
            operation_log_file_stats=[stat],
            time_fail_op_immediately_original=1,
            vessel_to_merge=[],
            find_element_class=finder,
        )

        ops = out[out["event"] == "operation"]
        mobs = out[out["event"] == "mobilisation"]

        self.assertEqual(len(ops), 1)
        self.assertEqual(len(mobs), 1)

        expected = ops.iloc[0]["d_end_wait_start"]
        self.assertEqual(mobs.iloc[0]["d_end"], expected)

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df",
        side_effect=failure_df_to_logevent_df_stub,
    )
    @patch("oriom.core.functions.logs_timeseries.create_logs_events_corrective.create_operation_site")
    def test_failure_datetime_not_in_schedule_can_be_skipped(self, mock_create_op, _mock_fail_to_log):
        base = datetime(2025, 1, 1)
        cutoff = base + timedelta(days=10)

        # Schedule does not include base+999h.
        sched = make_oper_sched(base, n_rows=10)
        vessel = DummyVessel("V1")
        op = DummyOp("opA", vessel1=vessel, ts_data=DummyTS(sched))
        stat = DummyOperStat(op)

        dates_failures = pd.DataFrame(
            [
                {
                    "datetime": base + timedelta(hours=999),
                    "id": "F1.0",
                    "maintenance_strategy": "immediately",
                    "operation_triggered": op.id.lower(),
                }
            ]
        )

        finder = DummyFinder(
            vessel_map={"V1": vessel},
            failure_map={"F1": DummyFailure("immediately", lead_time=0)},
        )

        # If fail_index is NaN, simulate create_operation_site returning an empty DF => function should continue.
        def _stub_create_operation_site(**kwargs):
            fail_index = kwargs["index"]["fail_index"]
            if pd.isna(fail_index):
                return pd.DataFrame(columns=kwargs["CONST"]["COLS"]), None
            raise AssertionError("This branch should not be reached in this test.")

        mock_create_op.side_effect = _stub_create_operation_site

        out = create_logs_events_corrective.create_logs_corrective_file(
            COLS=LOG_COLS,
            CUTOFF_DATE=cutoff,
            dates_failures=dates_failures,
            operation_log_file_stats=[stat],
            time_fail_op_immediately_original=1,
            vessel_to_merge=[],
            find_element_class=finder,
        )

        self.assertEqual((out["event"] == "operation").sum(), 0)

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df",
        side_effect=failure_df_to_logevent_df_stub,
    )
    @patch("oriom.core.functions.logs_timeseries.create_logs_events_corrective.compute_operation_datetimes")
    @patch("oriom.core.functions.logs_timeseries.create_logs_events_corrective._check_index_row_validity")
    @patch("oriom.core.functions.logs_timeseries.create_logs_events_corrective.CorrectionTowSite")
    @patch("oriom.core.functions.logs_timeseries.create_logs_events_corrective.CorrectionTowPort")
    @patch("oriom.core.functions.logs_timeseries.create_logs_events_corrective.create_operation_site")
    def test_tow_flow_creates_tow_rows(
        self,
        mock_create_op,
        MockTowPort,
        MockTowSite,
        mock_check_idx,
        mock_compute_dates,
        _mock_fail_to_log,
    ):
        base = datetime(2025, 1, 1)
        cutoff = base + timedelta(days=10)

        # Main operation (tow enabled)
        v_main = DummyVessel("V_MAIN", mobilisation_time=0)
        main_sched = make_oper_sched(base, n_rows=24)
        op_main = DummyOp(
            "opMain",
            vessel1=v_main,
            ts_data=DummyTS(main_sched),
            tow_to_port=True,
            op_tow_port="opTowPort",
            op_tow_site="opTowSite",
            op_tow_site_port="opTowSitePort",
            fail = True
        )
        stat_main = DummyOperStat(op_main)

        # Tow to port operation
        v_tow_port = DummyVessel("V_TOW_PORT", mobilisation_time=0)
        tow_port_sched = make_oper_sched(base, n_rows=24)
        op_tow_port = DummyOp("opTowPort", vessel1=v_tow_port, ts_data=DummyTS(tow_port_sched))

        # Tow to site operation
        v_tow_site = DummyVessel("V_TOW_SITE", mobilisation_time=0)
        tow_site_sched = make_oper_sched(base, n_rows=24)
        op_tow_site = DummyOp("opTowSite", vessel1=v_tow_site, ts_data=DummyTS(tow_site_sched))

        v_tow_site_port = DummyVessel("V_TOW_SITE_PORT", mobilisation_time=0)
        tow_site_port_sched = make_oper_sched(base, n_rows=24)
        op_tow_site_port = DummyOp("opTowSitePort", vessel1=v_tow_site_port, ts_data=DummyTS(tow_site_port_sched))

        # Failure triggers main operation
        dates_failures = pd.DataFrame(
            [
                {
                    "datetime": base,
                    "id": "F1.0",
                    "maintenance_strategy": "immediately",
                    "operation_triggered": op_main.id.lower(),
                    "preferred_month": None
                }
            ]
        )

        finder = DummyFinder(
            vessel_map={
                "V_MAIN": v_main,
                "V_TOW_PORT": v_tow_port,
                "V_TOW_SITE": v_tow_site,
                "V_TOW_SITE_PORT": v_tow_site_port
            },
            failure_map={"F1": DummyFailure("immediately", lead_time=0)},
            operations={
                "opTowPort": op_tow_port,
                "opTowSite": op_tow_site,
                "opTowSitePort": op_tow_site_port
            },
            op_stats_pmax_map={
                "opTowPort": MagicMock(),
                "opTowSite": MagicMock(),
                "opTowSitePort": MagicMock(),
            },
        )

        # Stub create_operation_site for the main operation (after tow port).
        def _stub_create_operation_site(**kwargs):
            cols = kwargs["CONST"]["COLS"]
            oper_obj = kwargs["oper_"]["oper"]
            vessel_obj = kwargs["vessel_"]["vessel"]
            row_dates = build_single_operation_row(
                cols=cols,
                oper_id=oper_obj.id,
                vessel1_id='v001',
                date_failure=kwargs["failure_"]["date_failure"],
                lead_h=0,
            )
            # No mobilisation lines for this tow test.
            return row_dates, None

        mock_create_op.side_effect = _stub_create_operation_site

        # TowPort stub
        class StubTowPort:
            def __init__(self, date_failure, vessel, oper, failure, maintenance_strategy, time_fail_op_immediately, date_start, preferred_months):
                self.date_failure = date_failure
                self.date_op = date_failure + timedelta(hours=time_fail_op_immediately)
                self.idx_end_leadtime = None
                self.tow_deferred = False
                self.date_start = date_failure + timedelta(hours=time_fail_op_immediately)

            def mobilitate_vessel(self, log_events, row):
                return None

            def add_hours_for_noon_shift(self, fail_index, lead_mob_time, oper_sched):
                self.idx_end_leadtime = int(fail_index)

        MockTowPort.side_effect = StubTowPort

        # TowSite stub
        class StubTowSite:
            def __init__(self, date_failure, vessel, oper, date_start, preferred_months = None):
                self.date_failure = date_failure
                self.idx_end_leadtime = 0

            def mobilitate_vessel(self, log_events, row, date_start=None):
                return None

            def check_leadtime_index(self, oper_sched, CUTOFF_DATE):
                self.idx_end_leadtime = 0
                return True

        MockTowSite.side_effect = StubTowSite

        # _check_index_row_validity: always return a non-empty slice
        mock_check_idx.return_value = pd.DataFrame({"datetime": [base]})

        # compute_operation_datetimes: deterministic timeline
        def _compute_dates(
            df_filtered_start = None,
            oper_stat = None,
            tow_stat_chart_month = None,
            double = None,
            add_op_end = None
        ):

            t0 = df_filtered_start["datetime"].iloc[0]
            return {
                "date_end_leadtime": t0 + timedelta(hours=0),
                "date_end_wait_start": t0 + timedelta(hours=1),
                "date_end_dur_net_port": t0 + timedelta(hours=2),
                "date_end_transit_ts": t0 + timedelta(hours=3),
                "date_end_wait_site": t0 + timedelta(hours=4),
                "date_end_dur_net_site": t0 + timedelta(hours=5),
                "date_end_transit_tp": t0 + timedelta(hours=6),
                "date_end": t0 + timedelta(hours=7),
                "date_end_stat_chart": t0 + timedelta(hours=7),
                "dur_total": 1,
            }

        oper_sched = pd.DataFrame({
            "datetime": [
                pd.Timestamp("2025-06-01 00:00:00"),
                pd.Timestamp("2025-06-01 00:00:00"),
                pd.Timestamp("2025-06-01 00:00:00"),
                pd.Timestamp("2025-06-01 00:00:00")
            ]
        })

        mock_compute_dates.side_effect = _compute_dates

        out = create_logs_events_corrective.create_logs_corrective_file(
            COLS=LOG_COLS,
            CUTOFF_DATE=cutoff,
            dates_failures=dates_failures,
            operation_log_file_stats=[stat_main],
            time_fail_op_immediately_original=1,
            vessel_to_merge=[],
            find_element_class=finder,
        )

        tow_rows = out[out["event"] == "tow"]
        self.assertGreaterEqual(len(tow_rows), 2)


class TestMapFailureIndices(unittest.TestCase):

    def test_map_failure_indices_basic(self):
        oper_sched = pd.DataFrame({
            "datetime": [
                pd.Timestamp("2025-06-01 00:00:00"),
                pd.Timestamp("2025-06-01 01:00:00"),
                pd.Timestamp("2025-06-01 02:00:00"),
            ]
        })

        failure_df = pd.DataFrame({
            "datetime": [
                pd.Timestamp("2025-06-01 01:00:00"),
                pd.Timestamp("2025-06-01 02:00:00"),
            ]
        })

        result = create_logs_events_corrective._map_failure_indices(failure_df, oper_sched)

        expected = pd.Series([1, 2], name="datetime")
        pd.testing.assert_series_equal(result.reset_index(drop=True), expected)

    def test_map_failure_indices_with_missing_datetime(self):
        oper_sched = pd.DataFrame({
            "datetime": [
                pd.Timestamp("2025-06-01 00:00:00"),
                pd.Timestamp("2025-06-01 01:00:00"),
            ]
        })

        failure_df = pd.DataFrame({
            "datetime": [
                pd.Timestamp("2025-06-01 01:00:00"),
                pd.Timestamp("2025-06-01 03:00:00"),  # non presente
            ]
        })

        result = create_logs_events_corrective._map_failure_indices(failure_df, oper_sched)

        self.assertEqual(result.iloc[0], 1)
        self.assertTrue(pd.isna(result.iloc[1]))


class TestTakeVesselData(unittest.TestCase):

    def test_take_vessel_data_basic(self):
        vessel = DummyVessel(id_='v001', mobilisation_time=2.3)
        vessel2 = DummyVessel(id_='v002', mobilisation_time=2.3, vessel_n = 5)
        op = DummyOp(
            id_ = 'op1',
            tow_to_port=None,
            vessel1=vessel,
            vessel2=vessel2,
        )

        v1, v2, mob_time = create_logs_events_corrective._take_vessel_data(op)

        self.assertIs(v1, vessel)
        self.assertEqual(v2, 5)
        self.assertEqual(mob_time, 3)  # ceil(2.3)

    def test_take_vessel_data_tow_to_port(self):
        vessel = DummyVessel(id_='v001', mobilisation_time=2.3)
        op = DummyOp(
            id_ = 'op1',
            tow_to_port=True,
            vessel1=vessel
        )

        v1, v2, mob_time = create_logs_events_corrective._take_vessel_data(op)

        self.assertIsNone(v1)
        self.assertIsNone(v2)
        self.assertEqual(mob_time, 0)

    def test_take_vessel_data_no_vessel2(self):
        vessel = DummyVessel(id_='v001', mobilisation_time=1.2)
        op = DummyOp(
            id_ = 'op1',
            tow_to_port=None,
            vessel1=vessel,
            vessel2_id=None
        )

        v1, v2, mob_time = create_logs_events_corrective._take_vessel_data(op)

        self.assertIs(v1, vessel)
        self.assertIsNone(v2)
        self.assertEqual(mob_time, 2)

if __name__ == "__main__":
    unittest.main(verbosity=2)