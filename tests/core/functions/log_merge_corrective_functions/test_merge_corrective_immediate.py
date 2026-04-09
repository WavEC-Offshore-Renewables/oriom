# test_merge_corrective_immediate

import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
import pandas as pd

from oriom.core.functions.log_merge_corrective_functions.merge_corrective_immediate import merge_operation


# Minimal COLS matching the structure expected when building merged rows
COLS_MERGED = [
    "d_trigger",          # 0
    "d_end_leadtime",     # 1
    "d_end_wait_start",   # 2
    "d_end_dur_net_port", # 3
    "d_end_transit_ts",   # 4
    "d_end_wait_site",    # 5
    "d_end_dur_net_site", # 6
    "d_end_transit_tp",   # 7
    "d_end",              # 8
    "d_end_stat_chart",   # 9
    "event",              # 10
    "group_def_id",       # 11
    "vessel_1",           # 12
    "n_vessels",          # 13
    "vessel_2",           # 14
    "ves_2",              # 15
    "comments",           # 16
    "extra",              # 17
    "flag",               # 18
    "ST_flag_1"           # 19
    "ST_flag_2"           # 20
]


class DummyVessel:
    def __init__(self, vid, crew_capacity=4, mobilisation_time=0.0):
        self.id = vid
        self.crew_capacity = crew_capacity
        self.mobilisation_time = mobilisation_time
        # Not needed for these tests, but defined for completeness
        self.charter = 0.0


class DummyOperSchedule:
    """Minimal object returned by find_oper_schedule."""

    def __init__(self, df, dur_total, last_valid_index):
        self.oper_sched = df
        self.dur_total = dur_total
        self.last_valid_index = last_valid_index

class DummyOP:
    """Fake OP with only what we need."""

    def __init__(self, vessel1_qt):
        self.vessel1_qt = vessel1_qt

class DummyFinder:
    """Fake Find_element_class with only what we need."""

    def __init__(self, vessel, oper_schedule, op):
        self._vessel = vessel
        self._oper_schedule = oper_schedule
        self._op = op

    def find_vessel(self, vessel_id):
        # Always return the test vessel
        return self._vessel

    def find_oper_schedule(self, op_id):
        # Always return the same schedule for simplicity
        return self._oper_schedule

    def find_operation(self, op_id):
        return self._op



class TestMergeOperationSingleOp(unittest.TestCase):
    """Tests for merge_operation when there is only one operation in the day."""

    @patch(
        "oriom.core.functions.log_merge_corrective_functions.merge_corrective_immediate."
        "df_vessel_merge_use"
    )
    def test_single_operation_no_merge(self, mock_vessel_use):
        """Single operation in a day must be returned as-is (no merging)."""
        base = datetime(2025, 1, 1, 8, 0, 0)

        # Build a simple log_events_oper_imm with a single immediate operation
        log_events_oper_imm = pd.DataFrame(
            [
                [
                    base,                      # d_trigger
                    base + timedelta(hours=1), # d_end_leadtime
                    base + timedelta(hours=2), # d_end_wait_start
                    base + timedelta(hours=3), # d_end_dur_net_port
                    None, None, None, None, None, None,
                    "operation",               # event
                    None,                      # group_def_id
                    "V1",                      # vessel_1
                    1,                         # n_vessels
                    None, None,
                    "fail_001",                # comments
                    None,
                    False,
                    False
                ]
            ],
            columns=COLS_MERGED,
        )

        # df_vessel_merge_use returns one day with one operation (index 0 → "ofw_opA")
        mock_vessel_use.return_value = pd.DataFrame(
            {
                "date": [base.date()],
                "operations": [{0: "ofw_opA"}],
            }
        )

        # Minimal oper_dict; grouped_operations not used in len(group)==1 branch
        oper_dict = {"ofw_opA": {"vess_1": "V1", "technician": 1, "technician_cost": 100.0, "duration": 2.0}}
        grouped_operations = {
            "V1": {
                "Group 1": {
                    "ofw_opA": {"Rank": 1},
                }
            }
        }

        # No vessel actually needed in the single-op branch
        result = merge_operation(
            log_events_oper_imm=log_events_oper_imm,
            vessels=[],
            find_element_class=None,  # never used
            time_between_devices={"opv": 1.0, "ofw": 1.0, "owc": 1.0},
            grouped_operations=grouped_operations,
            oper_dict=oper_dict,
            COLS=COLS_MERGED,
        )

        # We expect exactly one row, equal to the original operation
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["event"], "operation")
        self.assertEqual(result.iloc[0]["comments"], "fail_001")
        self.assertEqual(result.iloc[0]["vessel_1"], "V1")


class TestMergeOperationMultipleOps(unittest.TestCase):
    """Tests for merge_operation when multiple operations can be merged."""

    @patch(
        "oriom.core.functions.log_merge_corrective_functions.merge_corrective_immediate."
        "df_vessel_merge_use"
    )
    @patch(
        "oriom.core.functions.log_merge_corrective_functions.merge_corrective_immediate."
        "create_data",
        side_effect=lambda df, col, current: current + timedelta(hours=1),
    )
    @patch(
        "oriom.core.functions.log_merge_corrective_functions.merge_corrective_immediate."
        "approximate_hourly_data",
        side_effect=lambda dt: dt,
    )
    def test_two_operations_merged_into_one(
        self,
        _mock_approx,
        _mock_create_data,
        mock_vessel_use,
    ):
        """
        Two immediate corrective operations of the same vessel/technology:
        - grouped via grouped_operations
        - merged into a single 'operation_merged' row.
        """
        base = datetime(2025, 1, 1, 8, 0, 0)

        # Two operations happening the same day, same vessel, same 'tech'
        log_events_oper_imm = pd.DataFrame(
            [
                [
                    base,                      # d_trigger
                    base + timedelta(hours=0.5),
                    base + timedelta(hours=1),
                    base + timedelta(hours=2),  # d_end_dur_net_port
                    None, None, None, None, None, None,
                    "operation",
                    None,
                    "CTV1",                    # vessel_1
                    1,
                    None, None,
                    "fail_001",
                    None,
                    False,
                ],
                [
                    base + timedelta(hours=1),  # d_trigger (later but same day)
                    base + timedelta(hours=1.5),
                    base + timedelta(hours=2),
                    base + timedelta(hours=3),  # d_end_dur_net_port
                    None, None, None, None, None, None,
                    "operation",
                    None,
                    "CTV1",
                    1,
                    None, None,
                    "fail_002",
                    None,
                    False,
                    False
                ],
            ],
            columns=COLS_MERGED,
        )

        # df_vessel_merge_use: one day, with two operations (index 0 and 1)
        mock_vessel_use.return_value = pd.DataFrame(
            {
                "date": [base.date()],
                "operations": [{0: "ofw_opA", 1: "ofw_opB"}],
            }
        )

        # grouped_operations structure: vessel → group → {op: {...}}
        grouped_operations = {
            "CTV1": {
                "Group 1": {
                    "ofw_opA": {"Rank": 1},
                    "ofw_opB": {"Rank": 2},
                }
            }
        }

        # oper_dict with same vessel and durations
        oper_dict = {
            "ofw_opA": {
                "vess_1": "CTV1",
                "technician": 2,
                "technician_cost": 1000.0,
                "duration": 4.0,
            },
            "ofw_opB": {
                "vess_1": "CTV1",
                "technician": 1,
                "technician_cost": 500.0,
                "duration": 3.0,
            },
        }

        # Build a simple operation schedule DataFrame
        sched_datetimes = [base + timedelta(hours=h) for h in range(0, 24)]
        oper_sched_df = pd.DataFrame(
            {
                "datetime": sched_datetimes,
                "dur_total": [10.0] * 24,
                "transit_to_site": [1.0] * 24,
                "wait_site": [0.0] * 24,
                "dur_net_site": [2.0] * 24,
                "transit_to_port": [1.0] * 24,
                "wait_port": [0.5] * 24,
                "wait_start": [0.0] * 24,
            }
        )
        dummy_schedule = DummyOperSchedule(
            df=oper_sched_df,
            dur_total=10.0,
            last_valid_index=oper_sched_df.index.max(),
        )

        vessel = DummyVessel(vid="CTV1", crew_capacity=10, mobilisation_time=0.0)
        op = DummyOP(1)
        finder = DummyFinder(vessel=vessel, oper_schedule=dummy_schedule, op = op)

        # time_between_devices: use 1h per tech
        time_between_devices = {"opv": 1.0, "ofw": 1.0, "owc": 1.0}

        result = merge_operation(
            log_events_oper_imm=log_events_oper_imm,
            vessels=[vessel],
            find_element_class=finder,
            time_between_devices=time_between_devices,
            grouped_operations=grouped_operations,
            oper_dict=oper_dict,
            COLS=COLS_MERGED,
        )

        # We expect a single merged row
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["event"], "operation_merged")

        # group_def_id must contain both original operations (index 0 and 1)
        group_def_id = result.iloc[0]["group_def_id"]
        self.assertIsInstance(group_def_id, list)
        self.assertEqual(len(group_def_id), 2)
        idxs = sorted(idx for idx, _ in group_def_id)
        self.assertEqual(idxs, [0, 1])

        # Comments of failures were collected
        oper_group_comments = result.iloc[0]["comments"]
        self.assertIsInstance(oper_group_comments, dict)
        self.assertIn("failures", oper_group_comments)
        self.assertCountEqual(
            oper_group_comments["failures"], ["fail_001", "fail_002"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
