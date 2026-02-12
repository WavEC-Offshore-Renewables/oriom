# test_merge_corrective_deferred

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pandas as pd

from logistic_tools.core.functions.log_merge_corrective_functions import merge_corrective_deferred


class DummyTsData:
    """Minimal container for time-series related durations used in merge_corrective_deferred."""
    def __init__(self, dur_net_site=1.0, dur_net_port=1.0, transit_ts=1.0, transit_tp=1.0):
        self.dur_net_site = dur_net_site
        self.dur_net_port = dur_net_port
        self.transit_ts = transit_ts
        self.transit_tp = transit_tp


class DummyOperStat:
    """Minimal object with dur_total_dict for deferred operation statistics."""
    def __init__(self, dur_total_dict=None):
        # dur_total_dict is a dict with month (as string) → hours
        self.dur_total_dict = dur_total_dict or {"1": 2.0}


class DummyOperation:
    """Minimal operation object returned by aux_functions.take_attribute."""
    def __init__(self, op_id="opv001"):
        self.id = op_id
        self.ts_data = DummyTsData()
        self.tech_required = 2
        self.rov_drone = False


class DummyVessel:
    """Minimal vessel object used in merge_corrective_deferred."""
    def __init__(self, vid="V1", n_vessels=1, mobilisation_time=0.0):
        self.id = vid
        self.mobilisation_time = mobilisation_time
        self.n_vessels = n_vessels
        self.crew_capacity = 10
        self.type = "CTV"


class DummyFinder:
    """Minimal Find_element_class-like object with only find_vessel implemented."""
    def __init__(self, vessel):
        self._vessel = vessel

    def find_vessel(self, vessel_id):
        return self._vessel


# Common COLS used to build the merged dataframe
COLS_MERGED = [
    "d_trigger",           # 0
    "d_end_leadtime",      # 1
    "d_end_wait_start",    # 2
    "d_end_dur_net_port",  # 3
    "d_end_transit_site",  # 4
    "d_end_wait_site",     # 5
    "d_end_dur_net_site",  # 6
    "d_end_transit_port",  # 7
    "d_end",               # 8
    "d_end_stat_chart",    # 9
    "event",               # 10 -> here "operation_deferred_merged" is stored
    "group_def_id",        # 11
    "vessel_1",            # 12
    "n_vessel",            # 13
    "vessel_2",            # 14
    "ves_2",               # 15
    "group_def_comm",      # 16
    "shutdown",            # 17
    "St-1",                # 18
    "St-2",                # 19
]


class TestMergeDeferredOperationsTow(unittest.TestCase):
    """Tests for the special 'tow' vessel branch (rows are simply copied)."""

    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred."
        "merged_deferred_aux.create_stat_chart_campaign_operation",
        side_effect=lambda df, vessels, percentile: df,
    )
    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred.merge_shift_deferred"
    )
    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred.approximate_hourly_data"
    )
    def test_tow_branch_copies_rows_verbatim(
        self, mock_approx, mock_merge_shift, mock_stat_chart
    ):
        """
        When vessel_id == 'tow', rows for those operations must be copied directly
        (no merging logic, no merge_shift_deferred calls).
        """
        base_time = datetime(2025, 1, 1, 0, 0, 0)
        log_events_def = pd.DataFrame(
            {
                "d_trigger": [base_time, base_time + timedelta(days=1)],
                "id": ["tow_op", "tow_op"],
                "comments": ["c1", "c2"],
                "d_end_wait_start": [base_time, base_time + timedelta(days=1)],
                "d_end_transit_tp": [base_time, base_time + timedelta(days=1)],
                "shutdown": True
            }
        )

        mock_approx.side_effect = lambda dt: dt  # identity, but should not be used for tow

        result = merge_corrective_deferred.merge_deferred_operations(
            log_events_def=log_events_def,
            vessels=[],
            time_between_devices={},
            oper_per_vessel={"tow": ["tow_op"]},
            time_fail_op_immediately=0.0,
            percentile=0.9,
            COLS=log_events_def.columns.tolist(),  # tow branch uses original columns
            find_element_class=DummyFinder(DummyVessel()),
            duration_shift=8.0,
        )

        # tow branch should NOT call merge_shift_deferred
        mock_merge_shift.assert_not_called()

        # rows are copied (apart from internal 'year_month' handling)
        self.assertEqual(len(result), 2)
        self.assertListEqual(result["id"].tolist(), ["tow_op", "tow_op"])
        self.assertListEqual(result["comments"].tolist(), ["c1", "c2"])


class TestMergeDeferredOperationsSingleOp(unittest.TestCase):
    """Tests for a minimal one-operation deferred merging case."""

    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred."
        "merged_deferred_aux.create_stat_chart_campaign_operation",
        side_effect=lambda df, vessels, percentile: df,
    )
    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred."
        "merged_deferred_aux.vessel_reuse",
        side_effect=lambda vessel_n, n_vessel_used, day_start_idx_previous, day_start_idx_next, vessel_busy: (
            vessel_n,
            day_start_idx_next,
            vessel_busy,
        ),
    )
    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred.merge_shift_deferred"
    )
    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred.approximate_hourly_data",
        side_effect=lambda dt: dt,
    )
    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred.aux_functions.take_attribute"
    )
    def test_single_deferred_operation_creates_one_merged_row(
        self,
        mock_take_attribute,
        _mock_approx,
        mock_merge_shift,
        _mock_vessel_reuse,
        _mock_stat_chart,
    ):
        """
        For a single deferred operation:
        - one merged row with event == 'operation_deferred_merged' must be created
        - merge_shift_deferred must be called once
        """
        # Build a simple hourly schedule that contains the end_wait_start time
        base_day = datetime(2025, 1, 1, 0, 0, 0)
        datetimes = [base_day + timedelta(hours=h) for h in range(0, 24)]
        oper_sched = pd.DataFrame(
            {
                "datetime": datetimes,
                "wait_start": [0.0] * 24,
                "wait_port": [0.0] * 24,
                # no 'wait_site' column → considered as key error in code
            }
        )

        # Fake operation and statistics returned by aux_functions.take_attribute
        dummy_oper = DummyOperation("opv001")
        dummy_oper_stat = DummyOperStat({"1": 2.0})

        # indexes for wait_to_start / wait_port in oper_sched
        index_wait_to_start_col = oper_sched.columns.get_loc("wait_start")
        index_wait_port_col = oper_sched.columns.get_loc("wait_port")

        mock_take_attribute.return_value = (
            dummy_oper_stat,
            dummy_oper,
            100.0,   # tech_cost (not used in assertion)
            None,    # vessel_2
            None,    # ves_2
            oper_sched,
            index_wait_to_start_col,
            index_wait_port_col,
        )

        # merge_shift_deferred: merge everything in one shift
        def fake_merge_shift_deferred(
            duration_shift,
            duration_inspection,
            transit_between_devices,
            operation_total_duration,
            n_vessel,
            n_oper,
            operation_concluded,
            end_wait_start_list_idx,
            day_start_idx,
            N_technicians_on_vessel,
            N_technicians_per_inspection,
            vessel_type,
            rov,
            day_start_oper,
        ):
            new_operation_concluded = n_oper  # all operations done in this shift
            day_shift_end = day_start_oper + timedelta(hours=operation_total_duration)
            total_device_this_shift = n_oper
            number_technicians = N_technicians_per_inspection
            n_vessel_used = 1
            return (
                new_operation_concluded,
                day_start_idx,
                day_shift_end,
                total_device_this_shift,
                number_technicians,
                n_vessel_used,
            )

        mock_merge_shift.side_effect = fake_merge_shift_deferred

        # Build a minimal deferred log with one entry
        d_trigger = base_day
        d_end_wait_start = base_day + timedelta(hours=8)
        d_end_transit_tp = base_day + timedelta(hours=20)

        log_events_def = pd.DataFrame(
            {
                "d_trigger": [d_trigger],
                "id": ["opv001"],
                "comments": ["fail_001"],
                "d_end_wait_start": [d_end_wait_start],
                "d_end_transit_tp": [d_end_transit_tp],
                "d_end_leadtime": [d_end_wait_start],
                "shutdown": True
            }
        )

        vessel = DummyVessel(vid="V1", n_vessels=1, mobilisation_time=0.0)
        finder = DummyFinder(vessel)

        result = merge_corrective_deferred.merge_deferred_operations(
            log_events_def=log_events_def,
            vessels=[vessel],
            time_between_devices={"opv": 1.0},
            oper_per_vessel={"V1": ["opv001"]},
            time_fail_op_immediately=0.0,
            percentile=0.9,
            COLS=COLS_MERGED,
            find_element_class=finder,
            duration_shift=8.0,
            
        )

        # One merged row expected
        self.assertEqual(len(result), 1)

        # The event column (COLS_MERGED[10]) must contain 'operation_deferred_merged'
        self.assertIn("event", result.columns)
        self.assertEqual(result["event"].iloc[0], "operation_deferred_merged")

        # merge_shift_deferred must have been called once
        mock_merge_shift.assert_called_once()


class TestMergeDeferredOperationsMultipleOps(unittest.TestCase):
    """Tests for deferred merging when more than one failure of the same operation is present."""

    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred."
        "merged_deferred_aux.create_stat_chart_campaign_operation",
        side_effect=lambda df, vessels, percentile: df,
    )
    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred."
        "merged_deferred_aux.vessel_reuse",
        side_effect=lambda vessel_n, n_vessel_used, day_start_idx_previous, day_start_idx_next, vessel_busy: (
            vessel_n,
            day_start_idx_next,
            vessel_busy,
        ),
    )
    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred.merge_shift_deferred"
    )
    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred.approximate_hourly_data",
        side_effect=lambda dt: dt,
    )
    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred.aux_functions.take_attribute"
    )
    def test_multiple_deferred_operations_are_grouped_in_one_shift(
        self,
        mock_take_attribute,
        _mock_approx,
        mock_merge_shift,
        _mock_vessel_reuse,
        _mock_stat_chart,
    ):
        """
        When more than one failure of the same operation is present in the month for a vessel:
        - a single merged row should be generated
        - group_def_id must contain multiple (index, id) pairs
        """
        base_day = datetime(2025, 1, 1, 0, 0, 0)
        datetimes = [base_day + timedelta(hours=h) for h in range(0, 48)]
        oper_sched = pd.DataFrame(
            {
                "datetime": datetimes,
                "wait_start": [0.0] * 48,
                "wait_port": [0.0] * 48,
            }
        )

        dummy_oper = DummyOperation("opv001")
        dummy_oper_stat = DummyOperStat({"1": 2.0})

        index_wait_to_start_col = oper_sched.columns.get_loc("wait_start")
        index_wait_port_col = oper_sched.columns.get_loc("wait_port")

        mock_take_attribute.return_value = (
            dummy_oper_stat,
            dummy_oper,
            100.0,   # tech_cost
            None,    # vessel_2
            None,    # ves_2
            oper_sched,
            index_wait_to_start_col,
            index_wait_port_col,
        )

        def fake_merge_shift_deferred(
            duration_shift,
            duration_inspection,
            transit_between_devices,
            operation_total_duration,
            n_vessel,
            n_oper,
            operation_concluded,
            end_wait_start_list_idx,
            day_start_idx,
            N_technicians_on_vessel,
            N_technicians_per_inspection,
            vessel_type,
            rov,
            day_start_oper,
        ):
            # Assume both failures are merged in a single shift
            new_operation_concluded = n_oper
            day_shift_end = day_start_oper + timedelta(hours=operation_total_duration)
            total_device_this_shift = n_oper
            number_technicians = N_technicians_per_inspection*n_oper
            n_vessel_used = 1
            return (
                new_operation_concluded,
                day_start_idx,
                day_shift_end,
                total_device_this_shift,
                number_technicians,
                n_vessel_used,
            )

        mock_merge_shift.side_effect = fake_merge_shift_deferred

        # Two failures for the same operation id "opv001"
        d_trigger_1 = base_day
        d_trigger_2 = base_day

        d_end_wait_start_1 = base_day + timedelta(hours=8)
        d_end_wait_start_2 = base_day + timedelta(hours=8)

        d_end_transit_tp_1 = base_day + timedelta(hours=20)
        d_end_transit_tp_2 = base_day + timedelta(hours=20)

        log_events_def = pd.DataFrame(
            {
                "d_trigger": [d_trigger_1, d_trigger_2],
                "d_end_leadtime": [d_end_wait_start_1, d_end_wait_start_2],
                "d_end_wait_start": [d_end_wait_start_1, d_end_wait_start_2],
                "d_end_transit_tp": [d_end_transit_tp_1, d_end_transit_tp_2],
                "id": ["opv001", "opv001"],
                "comments": ["fail_001", "fail_002"],
                "shutdown": True
            }
        )

        vessel = DummyVessel(vid="V1", n_vessels=1, mobilisation_time=0.0)
        finder = DummyFinder(vessel)

        result = merge_corrective_deferred.merge_deferred_operations(
            log_events_def=log_events_def,
            vessels=[vessel],
            time_between_devices={"opv": 1.0},
            oper_per_vessel={"V1": ["opv001"]},
            time_fail_op_immediately=0.0,
            percentile=0.9,
            COLS=COLS_MERGED,
            find_element_class=finder,
            duration_shift=8.0,
        )

        # We expect only one merged row (both failures grouped)
        self.assertEqual(len(result), 1)
        self.assertIn("event", result.columns)
        self.assertEqual(result["event"].iloc[0], "operation_deferred_merged")

        # group_def_id must contain 2 tuples (index, id)
        self.assertIn("group_def_id", result.columns)
        group_def_id = result["group_def_id"].iloc[0]
        self.assertIsInstance(group_def_id, list)
        self.assertEqual(len(group_def_id), 2)
        dict_result = result["group_def_comm"].iloc[0]
        self.assertEqual(dict_result['tech_tot'], 4)
        a, a, single_tech_cost, b, v, a,a,a = mock_take_attribute.return_value
        self.assertEqual(dict_result["tech_cost"]/dict_result["tech_tot"], single_tech_cost)
        self.assertEqual(len(group_def_id), 2)

        # merge_shift_deferred must have been called
        mock_merge_shift.assert_called_once()

class TestMergeDeferredOperationsMultipleShifts(unittest.TestCase):
    """Tests when multiple deferred failures are split across two shifts (partial merge)."""

    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred."
        "merged_deferred_aux.create_stat_chart_campaign_operation",
        side_effect=lambda df, vessels, percentile: df,
    )
    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred."
        "merged_deferred_aux.vessel_reuse",
        side_effect=lambda vessel_n, n_vessel_used, day_start_idx_previous, day_start_idx_next, vessel_busy: (
            vessel_n,
            day_start_idx_next,
            vessel_busy,
        ),
    )
    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred."
        "merged_deferred_aux.find_start_time"
    )
    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred.merge_shift_deferred"
    )
    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred.approximate_hourly_data",
        side_effect=lambda dt: dt,
    )
    @patch(
        "logistic_tools.core.functions.log_merge_corrective_functions.merge_corrective_deferred.aux_functions.take_attribute"
    )
    def test_multiple_failures_split_into_two_shifts(
        self,
        mock_take_attribute,
        _mock_approx,
        mock_merge_shift,
        mock_find_start,
        _mock_vessel_reuse,
        _mock_stat_chart,
    ):
        """
        Two failures of the same operation:
        - cannot all be merged in one shift (merge_shift_deferred returns only 1 device per shift)
        - result must contain two merged rows, each with a single failure in group_def_id.
        """
        base_day = datetime(2025, 1, 1, 0, 0, 0)

        # Simple daily schedule
        datetimes = [base_day + timedelta(hours=h) for h in range(0, 48)]
        oper_sched = pd.DataFrame(
            {
                "datetime": datetimes,
                "wait_start": [0.0] * 48,
                "wait_port": [0.0] * 48,
            }
        )

        dummy_oper = DummyOperation("opv001")
        dummy_oper_stat = DummyOperStat({"1": 2.0})

        index_wait_to_start_col = oper_sched.columns.get_loc("wait_start")
        index_wait_port_col = oper_sched.columns.get_loc("wait_port")

        mock_take_attribute.return_value = (
            dummy_oper_stat,
            dummy_oper,
            100.0,   # tech_cost
            None,    # vessel_2
            None,    # ves_2
            oper_sched,
            index_wait_to_start_col,
            index_wait_port_col,
        )

        # find_start_time: keep same start time and index, no extra waits
        def fake_find_start_time(
            day_start_oper,
            day_start_oper_single_op,
            day_start_idx,
            oper_sched,
            index_wait_at_site_col,
            index_wait_to_start_col,
        ):
            return day_start_oper, day_start_idx, 0.0, 0.0

        mock_find_start.side_effect = fake_find_start_time

        # merge_shift_deferred: only one operation per shift (no full merge)
        def fake_merge_shift_deferred(
            duration_shift,
            duration_inspection,
            transit_between_devices,
            operation_total_duration,
            n_vessel,
            n_oper,
            operation_concluded,
            end_wait_start_list_idx,
            day_start_idx,
            N_technicians_on_vessel,
            N_technicians_per_inspection,
            vessel_type,
            rov,
            day_start_oper,
        ):
            new_operation_concluded = operation_concluded + 1
            day_shift_end = day_start_oper + timedelta(hours=operation_total_duration)
            total_device_this_shift = 1      # only 1 failure corrected per shift
            number_technicians = N_technicians_per_inspection
            n_vessel_used = 1
            return (
                new_operation_concluded,
                day_start_idx,
                day_shift_end,
                total_device_this_shift,
                number_technicians,
                n_vessel_used,
            )

        mock_merge_shift.side_effect = fake_merge_shift_deferred

        # Two failures for the same operation
        d_trigger_1 = base_day
        d_trigger_2 = base_day + timedelta(days=1)

        d_end_wait_start_1 = base_day + timedelta(hours=8)
        d_end_wait_start_2 = base_day + timedelta(days=1, hours=8)

        d_end_transit_tp_1 = base_day + timedelta(hours=20)
        d_end_transit_tp_2 = base_day + timedelta(days=1, hours=20)

        log_events_def = pd.DataFrame(
            {
                "d_trigger": [d_trigger_1, d_trigger_2],
                "id": ["opv001", "opv001"],
                "comments": ["fail_001", "fail_002"],
                "d_end_wait_start": [d_end_wait_start_1, d_end_wait_start_2],
                "d_end_transit_tp": [d_end_transit_tp_1, d_end_transit_tp_2],
                "d_end_leadtime": [d_end_wait_start_1, d_end_wait_start_2],
                "shutdown": True
            }
        )

        vessel = DummyVessel(vid="V1", n_vessels=1, mobilisation_time=0.0)
        finder = DummyFinder(vessel)

        result = merge_corrective_deferred.merge_deferred_operations(
            log_events_def=log_events_def,
            vessels=[vessel],
            time_between_devices={"opv": 1.0},
            oper_per_vessel={"V1": ["opv001"]},
            time_fail_op_immediately=0.0,
            percentile=0.9,
            COLS=COLS_MERGED,
            find_element_class=finder,
            duration_shift=8.0,
        )

        # Two merged rows (each for one failure)
        self.assertEqual(len(result), 2)
        self.assertTrue((result["event"] == "operation_deferred_merged").all())

        # Each group_def_id should contain exactly one (index, id) pair
        for group_def_id in result["group_def_id"]:
            self.assertIsInstance(group_def_id, list)
            self.assertEqual(len(group_def_id), 1)

        # merge_shift_deferred must have been called twice (two shifts)
        self.assertEqual(mock_merge_shift.call_count, 2)

if __name__ == "__main__":
    unittest.main(verbosity=2)
