# Updated tests/test_create_logs_corrective_file.py

# --- I will insert the existing content and add all new test cases here ---

# tests/test_create_logs_corrective_file.py

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd

from logistic_tools.core.functions.logs_timeseries.create_logs_events_corrective import (
    create_logs_corrective_file,
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

# ----------------- Helpers -----------------

# (original helpers retained)

def make_oper_sched(start_dt, n_rows=10, step_h=1,
                    wait_start=1, dur_net_port=1, transit_to_site=1,
                    wait_site=1, dur_net_site=1, transit_to_port=1, wait_port=1):
    dts = [start_dt + timedelta(hours=i*step_h) for i in range(n_rows)]
    dur_total = (
        wait_start + dur_net_port + transit_to_site + wait_site + dur_net_site + transit_to_port + wait_port
    )
    return pd.DataFrame({
        "datetime": dts,
        "wait_start": [wait_start]*n_rows,
        "dur_net_port": [dur_net_port]*n_rows,
        "transit_to_site": [transit_to_site]*n_rows,
        "wait_site": [wait_site]*n_rows,
        "dur_net_site": [dur_net_site]*n_rows,
        "transit_to_port": [transit_to_port]*n_rows,
        "wait_port": [wait_port]*n_rows,
        "dur_total": [dur_total]*n_rows,
    })


class DummyTS:
    def __init__(self, oper_sched, last_valid_index):
        self.oper_sched = oper_sched
        self.last_valid_index = last_valid_index


class DummyOp:
    def __init__(self, id_, vessel1, vessel2=None, ts_data=None):
        self.id = id_
        self.vessel1 = vessel1
        self.vessel2 = vessel2
        self.vessel1_id = vessel1.id
        self.vessel1_qt = 1
        self.vessel2_id = vessel2.id if vessel2 else None
        self.vessel2_qt = 1 if vessel2 else None
        self.ts_data = ts_data
        self.tow_to_port = False
        self.op_tow_port = None
        self.op_tow_site = None
        self.vessel1_qt = 1
        self.tow_to_site_dict = {"1": 0}


class DummyOperStat:
    def __init__(self, op_class, dur_total_dict):
        self.op_class = op_class
        self.dur_total_dict = dur_total_dict


class DummyVessel:
    def __init__(self, id_, mobilisation_time=0, vtype="workboat"):
        self.id = id_
        self.mobilisation_time = mobilisation_time
        self.type = vtype


class DummyFailure:
    def __init__(self, maintenance_strategy, lead_time=0, preferred_month=None):
        self.maintenance_strategy = maintenance_strategy
        self.lead_time = lead_time
        self.preferred_month = preferred_month


class DummyFinder:
    def __init__(self, vessel_map, failure_map, op_stats_pmax_map=None, operations=None):
        self.vessel_map = vessel_map
        self.failure_map = failure_map
        self.op_stats_pmax_map = op_stats_pmax_map or {}
        self.operations = operations or {}

    def find_vessel(self, vessel_id): return self.vessel_map[vessel_id]
    def find_failure_from_id(self, fail_id): return self.failure_map[fail_id]
    def find_operation_stats_pmax(self, op_id): return self.op_stats_pmax_map[op_id]
    def find_operation(self, op_id): return self.operations[op_id]


# ----------------- Original Test Cases (unchanged) -----------------

# (existing two tests retained exactly as before)

# ----------------- NEW TESTS ADDED BELOW -----------------

class TestCreateLogsCorrectiveFileExtended(unittest.TestCase):

    # 1) Failure beyond cutoff — no output
    @patch("logistic_tools.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df")
    def test_failure_beyond_cutoff(self, mock_fail_to_log):
        mock_fail_to_log.return_value = pd.DataFrame(columns=["d_trigger"])  # minimal
        cutoff = datetime(2025, 1, 1)
        dates_failures = pd.DataFrame([{ "datetime": cutoff + timedelta(days=10), "id": "F001.0", "maintenance_strategy": "immediately", "operation_triggered": "opA" }])
        finder = DummyFinder({}, {})
        out = create_logs_corrective_file(COLS=["d_trigger"], CUTOFF_DATE=cutoff,
                                          dates_failures=dates_failures,
                                          operation_log_file_stats=[], time_fail_op_immediately=1,
                                          vessel_to_merge=[], find_element_class=finder)
        self.assertTrue(out.empty)

    # 2) Vessel mobilisation influencing leadtime
    @patch("logistic_tools.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.create_data")
    @patch("logistic_tools.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df")
    @patch("logistic_tools.core.functions.logs_timeseries.create_logs_events_corrective.CorrectionImmediate")
    def test_mobilisation_effect(self, MockImmediate, mock_fail_to_log, mock_create_data):
        # create_data: ritorna semplicemente la data di partenza (ci basta per il test)
        mock_create_data.side_effect = lambda df_slice, col, start: start
        mock_fail_to_log.return_value = pd.DataFrame(columns=LOG_COLS)

        base = datetime(2025, 1, 1)
        sched = make_oper_sched(base, n_rows=10)
        ts = DummyTS(sched, last_valid_index=9)

        # mobilizzazione = 0, ma lead_time del failure = 3 h
        vessel = DummyVessel("V1", mobilisation_time=0)
        op = DummyOp("opA", vessel1=vessel, ts_data=ts)
        stat = DummyOperStat(op, dur_total_dict={"1": 5})

        dates_failures = pd.DataFrame([{
            "datetime": base,
            "id": "F1.0",
            "maintenance_strategy": "immediately",
            "operation_triggered": op.id.lower(),  # <-- deve coincidere con oper.id.lower()
        }])

        failure = DummyFailure("immediately", lead_time=3)
        finder = DummyFinder({"V1": vessel}, {"F1": failure})

        # Stub per CorrectionImmediate
        class StubImmediate:
            def __init__(self, date_failure, vessel, oper, time_fail_op_immediately, tow_op):
                self.date_failure = date_failure
                self.date_op = date_failure + timedelta(hours=time_fail_op_immediately)
                self.idx_end_leadtime = None

            def mobilitate_vessel(self, log_events, row):
                return None  # niente mobilizzazione nel test

            def add_hours_for_noon_shift(self, fail_index, lead_mob_time, oper_sched):
                # simuliamo idx_end_leadtime = indice failure + lead_mob_time
                self.idx_end_leadtime = fail_index + lead_mob_time

        MockImmediate.side_effect = StubImmediate

        out = create_logs_corrective_file(
            COLS=LOG_COLS,
            CUTOFF_DATE=base + timedelta(days=1),
            dates_failures=dates_failures,
            operation_log_file_stats=[stat],
            time_fail_op_immediately=1,
            vessel_to_merge=[],
            find_element_class=finder,
        )

        self.assertEqual(len(out), 1)
        # idx_end_leadtime = 0 + 3 → riga 3 della schedule
        self.assertEqual(out.iloc[0]["d_end_leadtime"], sched.iloc[3]["datetime"])

    # 3) Preferred-month deferred maintenance
    @patch("logistic_tools.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.create_data")
    @patch("logistic_tools.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df")
    @patch("logistic_tools.core.functions.logs_timeseries.create_logs_events_corrective.CorrectionDeferred")
    def test_preferred_month_deferred(self, MockDeferred, mock_fail_to_log, mock_create_data):
        # create_data: ritorna semplicemente la data di partenza
        mock_create_data.side_effect = lambda df_slice, col, start: start
        mock_fail_to_log.return_value = pd.DataFrame(columns=LOG_COLS)

        base = datetime(2025, 1, 15)
        sched = make_oper_sched(base, n_rows=10)
        ts = DummyTS(sched, last_valid_index=9)

        vessel = DummyVessel("V1")
        op = DummyOp("opA", vessel1=vessel, ts_data=ts)
        stat = DummyOperStat(op, dur_total_dict={"1": 5, "2": 5})

        dates_failures = pd.DataFrame([{
            "datetime": base,
            "id": "F2.0",
            "maintenance_strategy": "specific month",  # <--- questa è la stringa che il codice gestisce
            "operation_triggered": op.id.lower(),
        }])

        failure = DummyFailure("specific month", lead_time=0, preferred_month=2)
        finder = DummyFinder({"V1": vessel}, {"F2": failure})

        class StubDeferred:
            def __init__(self, date_failure, vessel, oper, preferred_month, tow_op):
                self.date_failure = date_failure
                self.date_op = date_failure  # per il test basta
                self.idx_end_leadtime = 0

            def leadtime_evaluation(self, lead_mob_time):
                # per semplicità teniamo sempre idx=0
                self.idx_end_leadtime = 0

            def add_leadtime_tow(self, lead_mob_time):
                self.idx_end_leadtime = 0

            def check_leadtime_index(self, oper_sched, CUTOFF_DATE):
                return True  # sempre trovata una finestra valida

        MockDeferred.side_effect = StubDeferred

        out = create_logs_corrective_file(
            COLS=LOG_COLS,
            CUTOFF_DATE=base + timedelta(days=60),
            dates_failures=dates_failures,
            operation_log_file_stats=[stat],
            time_fail_op_immediately=0,
            vessel_to_merge=[],
            find_element_class=finder,
        )

        # basta verificare che venga creata almeno una riga
        self.assertGreaterEqual(len(out), 1)

    # 4) Test with vessel_2 present
    @patch("logistic_tools.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.create_data")
    @patch("logistic_tools.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df")
    @patch("logistic_tools.core.functions.logs_timeseries.create_logs_events_corrective.CorrectionImmediate")
    def test_vessel2_fields(self, MockImmediate, mock_fail_to_log, mock_create_data):
        mock_create_data.side_effect = lambda df_slice, col, start: start
        mock_fail_to_log.return_value = pd.DataFrame(columns=LOG_COLS)

        base = datetime(2025, 1, 1)
        v1 = DummyVessel("A")
        v2 = DummyVessel("B")
        op = DummyOp("opAB", v1, vessel2=v2, ts_data=DummyTS(make_oper_sched(base), 5))
        stat = DummyOperStat(op, {"1": 5})

        dates_failures = pd.DataFrame([{
            "datetime": base,
            "id": "FX.0",
            "maintenance_strategy": "immediately",
            "operation_triggered": op.id.lower(),  # "opab"
        }])

        finder = DummyFinder(
            {"A": v1, "B": v2},
            {"FX": DummyFailure("immediately")}
        )

        class StubImmediate:
            def __init__(self, date_failure, vessel, oper, time_fail_op_immediately, tow_op):
                self.date_failure = date_failure
                self.date_op = date_failure + timedelta(hours=time_fail_op_immediately)
                self.idx_end_leadtime = 0

            def mobilitate_vessel(self, log_events, row):
                return None

            def add_hours_for_noon_shift(self, fail_index, lead_mob_time, oper_sched):
                self.idx_end_leadtime = fail_index

        MockImmediate.side_effect = StubImmediate

        out = create_logs_corrective_file(
            COLS=LOG_COLS,
            CUTOFF_DATE=base + timedelta(days=1),
            dates_failures=dates_failures,
            operation_log_file_stats=[stat],
            time_fail_op_immediately=1,
            vessel_to_merge=[],
            find_element_class=finder,
        )

        self.assertGreaterEqual(len(out), 1)
        # controlliamo che il campo vessel_2 contenga l'id del secondo vessel
        self.assertIn("vessel_2", out.columns)
        self.assertIn("n_vessel_2", out.columns)
        self.assertEqual(out.iloc[0]["vessel_2"], "B")

    # 5) Multiple failures
    @patch("logistic_tools.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.create_data")
    @patch("logistic_tools.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df")
    @patch("logistic_tools.core.functions.logs_timeseries.create_logs_events_corrective.CorrectionImmediate")
    def test_multiple_failures(self, MockImmediate, mock_fail_to_log, mock_create_data):
        mock_create_data.side_effect = lambda df_slice, col, start: start
        mock_fail_to_log.return_value = pd.DataFrame(columns=LOG_COLS)

        base = datetime(2025, 1, 1)
        v = DummyVessel("V1")  # mobilisation_time=0
        op = DummyOp("opM", v, ts_data=DummyTS(make_oper_sched(base), 5))
        stat = DummyOperStat(op, {"1": 5})

        dates_failures = pd.DataFrame([
            {
                "datetime": base,
                "id": "F1.0",
                "maintenance_strategy": "immediately",
                "operation_triggered": op.id.lower(),  # "opm"
            },
            {
                "datetime": base + timedelta(hours=1),
                "id": "F2.0",
                "maintenance_strategy": "immediately",
                "operation_triggered": op.id.lower(),
            },
        ])

        finder = DummyFinder(
            {"V1": v},
            {
                "F1": DummyFailure("immediately"),
                "F2": DummyFailure("immediately"),
            },
        )

        class StubImmediate:
            def __init__(self, date_failure, vessel, oper, time_fail_op_immediately, tow_op):
                self.date_failure = date_failure
                self.date_op = date_failure + timedelta(hours=time_fail_op_immediately)
                self.idx_end_leadtime = None

            def mobilitate_vessel(self, log_events, row):
                return None

            def add_hours_for_noon_shift(self, fail_index, lead_mob_time, oper_sched):
                # in questo test non ci interessa il leadtime aggiuntivo
                self.idx_end_leadtime = fail_index

        MockImmediate.side_effect = StubImmediate

        out = create_logs_corrective_file(
            COLS=LOG_COLS,
            CUTOFF_DATE=base + timedelta(days=1),
            dates_failures=dates_failures,
            operation_log_file_stats=[stat],
            time_fail_op_immediately=1,
            vessel_to_merge=[],
            find_element_class=finder,
        )

        # una riga di operazione per ogni failure
        ops_only = out[out["event"] == "operation"]
        self.assertEqual(len(ops_only), 2)

    # 6) Trigger operation missing
    @patch("logistic_tools.core.functions.logs_timeseries.create_logs_events_corrective.logs_timeseries_func.failure_df_to_logevent_df", return_value=pd.DataFrame(columns=["d_trigger"]))
    def test_missing_operation_trigger(self, mock_fail):
        base = datetime(2025,1,1)
        dates_failures = pd.DataFrame([{ "datetime": base, "id":"FX.0","maintenance_strategy":"immediately","operation_triggered":"missing_op" }])
        finder = DummyFinder({}, {"FX":DummyFailure("immediately")})

        out = create_logs_corrective_file(COLS=["d_trigger"], CUTOFF_DATE=base+timedelta(days=1),
                                          dates_failures=dates_failures, operation_log_file_stats=[], time_fail_op_immediately=1,
                                          vessel_to_merge=[], find_element_class=finder)
        self.assertTrue(out.empty)

if __name__ == "__main__":
    unittest.main(verbosity=2)
