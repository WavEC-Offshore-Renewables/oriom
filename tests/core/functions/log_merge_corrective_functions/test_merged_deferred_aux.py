#test_merged_deferred_aux

import unittest
from unittest.mock import patch
from datetime import datetime, timedelta

import pandas as pd

from oriom.core.functions.log_merge_corrective_functions import merged_deferred_aux


class DummyVessel:
    """Minimal vessel with just an id attribute."""

    def __init__(self, vid):
        self.id = vid


class DummyFailure:
    """Minimal Failure object for creation_oper_vessel_dict tests."""

    def __init__(self, fid, maintenance_strategy, operation_triggered):
        self.id = fid
        self.maintenance_strategy = maintenance_strategy
        self.operation_triggered = operation_triggered


class DummyOperation:
    """Minimal Operation object for creation_oper_vessel_dict tests."""

    def __init__(self, oid, vessel1_id, tow_to_port=False):
        self.id = oid
        self.vessel1_id = vessel1_id
        self.tow_to_port = tow_to_port


class DummyFinder:
    """Minimal Find_element_class stub."""

    def __init__(self, operations_by_id):
        self.operations_by_id = operations_by_id

    def find_operation(self, op_id):
        return self.operations_by_id[op_id]


# ---------------------- create_stat_chart_campaign_operation ----------------------


class TestCreateStatChartCampaignOperation(unittest.TestCase):
    """Tests for create_stat_chart_campaign_operation."""

    def test_single_vessel_two_months_updates_only_deferred_rows(self):
        """Deferred merged operations must get d_end_stat_chart updated per monthly percentile."""

        v1 = DummyVessel("V1")
        v2 = DummyVessel("V2")

        # Row 1: Jan campaign for V1, duration 10 days
        d1_start = datetime(2025, 1, 1, 0, 0, 0)
        d1_end = datetime(2025, 1, 11, 0, 0, 0)

        # Row 2: Feb campaign for V1, duration 5 days
        d2_start = datetime(2025, 2, 1, 0, 0, 0)
        d2_end = datetime(2025, 2, 6, 0, 0, 0)

        # Row 3: non-deferred event for V1 (should not be touched)
        d3_start = datetime(2025, 1, 5, 0, 0, 0)
        d3_end = datetime(2025, 1, 6, 0, 0, 0)

        # Row 4: deferred merged for another vessel V2 (should be handled separately)
        d4_start = datetime(2025, 1, 3, 0, 0, 0)
        d4_end = datetime(2025, 1, 8, 0, 0, 0)

        df = pd.DataFrame(
            [
                [d1_start, d1_end, "operation_deferred_merged", "V1", None],
                [d2_start, d2_end, "operation_deferred_merged", "V1", None],
                [d3_start, d3_end, "operation", "V1", None],
                [d4_start, d4_end, "operation_deferred_merged", "V2", None],
            ],
            columns=["d_trigger", "d_end", "event", "vessel_1", "d_end_stat_chart"],
        )

        result = merged_deferred_aux.create_stat_chart_campaign_operation(
            df=df.copy(), vessels=[v1, v2], percentile=0.9
        )

        # For V1, Jan (month=1): percentile(0.9) of duration_days = 10 → ceil = 10
        expected_v1_jan = d1_start + timedelta(days=10)
        # For V1, Feb (month=2): duration_days = 5 → percentile = 5 → ceil = 5
        expected_v1_feb = d2_start + timedelta(days=5)

        row_jan = result.iloc[0]
        row_feb = result.iloc[1]
        row_non_deferred = result.iloc[2]
        row_v2 = result.iloc[3]

        self.assertEqual(row_jan["d_end_stat_chart"], expected_v1_jan)
        self.assertEqual(row_feb["d_end_stat_chart"], expected_v1_feb)

        # Non-deferred event must remain None
        self.assertIsNone(row_non_deferred["d_end_stat_chart"])

        # For V2, single January campaign:
        expected_v2_jan = d4_start + timedelta(days=5)  # duration 5 days
        self.assertEqual(row_v2["d_end_stat_chart"], expected_v2_jan)

    def test_percentile_greater_than_one_is_interpreted_as_fraction(self):
        """If percentile > 1 it must be interpreted as percentile / 100."""

        v1 = DummyVessel("V1")
        d_start = datetime(2025, 3, 1, 0, 0, 0)
        d_end = datetime(2025, 3, 6, 0, 0, 0)  # duration 5 days

        df = pd.DataFrame(
            [[d_start, d_end, "operation_deferred_merged", "V1", None]],
            columns=["d_trigger", "d_end", "event", "vessel_1", "d_end_stat_chart"],
        )

        # Using percentile=90 should behave like 0.9 in this simple 1-row case
        result = merged_deferred_aux.create_stat_chart_campaign_operation(
            df=df.copy(), vessels=[v1], percentile=90
        )

        expected = d_start + timedelta(days=5)
        self.assertEqual(result.iloc[0]["d_end_stat_chart"], expected)


# ----------------------------- vessel_reuse ---------------------------------------


class TestVesselReuse(unittest.TestCase):
    """Tests for vessel_reuse."""

    def test_partial_usage_not_all_busy(self):
        """If not all vessels are busy, keep previous start index and update busy count."""
        vessel_n = 4
        n_used = 1
        prev_idx = 10
        next_idx = 20
        vessel_busy = 2  # already 2 busy

        available, new_idx, new_busy = merged_deferred_aux.vessel_reuse(
            vessel_n=vessel_n,
            n_vessel_used=n_used,
            day_start_idx_previous=prev_idx,
            day_start_idx_next=next_idx,
            vessel_busy=vessel_busy,
        )

        # Now busy = 3 < 4, keep previous idx
        self.assertEqual(available, 3)       # 4 - 1
        self.assertEqual(new_idx, prev_idx)  # still previous
        self.assertEqual(new_busy, 3)

    def test_partial_usage_all_busy(self):
        """If total busy reaches or exceeds vessel_n, reset busy and move to next index."""
        vessel_n = 4
        n_used = 2
        prev_idx = 10
        next_idx = 20
        vessel_busy = 2  # 2 already busy

        available, new_idx, new_busy = merged_deferred_aux.vessel_reuse(
            vessel_n=vessel_n,
            n_vessel_used=n_used,
            day_start_idx_previous=prev_idx,
            day_start_idx_next=next_idx,
            vessel_busy=vessel_busy,
        )

        # 2 + 2 = 4 ≥ vessel_n -> reset
        self.assertEqual(available, 4)
        self.assertEqual(new_idx, next_idx)
        self.assertEqual(new_busy, 0)

    def test_all_vessels_used_in_this_shift(self):
        """If n_vessel_used >= vessel_n, all vessels are used and index moves to next."""
        vessel_n = 3
        n_used = 3
        prev_idx = 5
        next_idx = 7
        vessel_busy = 1  # irrelevant here

        available, new_idx, new_busy = merged_deferred_aux.vessel_reuse(
            vessel_n=vessel_n,
            n_vessel_used=n_used,
            day_start_idx_previous=prev_idx,
            day_start_idx_next=next_idx,
            vessel_busy=vessel_busy,
        )

        self.assertEqual(available, 3)
        self.assertEqual(new_idx, next_idx)
        # vessel_busy is not changed in this branch
        self.assertEqual(new_busy, vessel_busy)


# ----------------------------- find_start_time ------------------------------------


class TestFindStartTime(unittest.TestCase):
    """Tests for find_start_time."""

    @patch(
        "oriom.core.functions.log_merge_corrective_functions."
        "merged_deferred_aux.approximate_hourly_data",
        side_effect=lambda dt: dt,
    )
    def test_find_first_zero_wait_start_with_wait_site_column(self, _mock_approx):
        """Must move index until wait_start == 0 and read wait_site from schedule."""
        base = datetime(2025, 1, 1, 8, 0, 0)
        sched = pd.DataFrame(
            {
                "datetime": [base + timedelta(hours=h) for h in range(4)],
                "wait_start": [1, 1, 0, 0],
                "wait_site": [0.0, 0.5, 2.5, 0.0],
            }
        )

        idx_wait_start = sched.columns.get_loc("wait_start")
        idx_wait_site = sched.columns.get_loc("wait_site")

        day_start_oper = sched.at[0, "datetime"]
        day_start_oper_single_op = day_start_oper

        new_date, new_idx, wait_to_start, wait_at_site = merged_deferred_aux.find_start_time(
            day_start_oper=day_start_oper,
            day_start_oper_single_op=day_start_oper_single_op,
            day_start_idx=0,
            oper_sched=sched,
            index_wait_at_site_col=idx_wait_site,
            index_wait_to_start_col=idx_wait_start,
        )

        # First row with wait_start == 0 is index 2
        self.assertEqual(new_idx, 2)
        self.assertEqual(wait_to_start, 0)
        self.assertEqual(wait_at_site, 2.5)
        self.assertEqual(new_date, sched.at[2, "datetime"])

    @patch(
        "oriom.core.functions.log_merge_corrective_functions."
        "merged_deferred_aux.approximate_hourly_data",
        side_effect=lambda dt: dt,
    )
    def test_find_zero_wait_start_without_wait_site_column(self, _mock_approx):
        """If index_wait_at_site_col is None, wait_at_site must be 0 even if column exists."""
        base = datetime(2025, 1, 1, 8, 0, 0)
        sched = pd.DataFrame(
            {
                "datetime": [base + timedelta(hours=h) for h in range(3)],
                "wait_start": [2, 1, 0],
                "wait_site": [1.0, 1.0, 5.0],
            }
        )

        idx_wait_start = sched.columns.get_loc("wait_start")

        new_date, new_idx, wait_to_start, wait_at_site = merged_deferred_aux.find_start_time(
            day_start_oper=sched.at[0, "datetime"],
            day_start_oper_single_op=sched.at[0, "datetime"],
            day_start_idx=0,
            oper_sched=sched,
            index_wait_at_site_col=None,
            index_wait_to_start_col=idx_wait_start,
        )

        self.assertEqual(new_idx, 2)
        self.assertEqual(wait_to_start, 0)
        self.assertEqual(wait_at_site, 0)  # forced to 0 when index_wait_at_site_col is None
        self.assertEqual(new_date, sched.at[2, "datetime"])


# -------------------------- creation_oper_vessel_dict ------------------------------


class TestCreationOperVesselDict(unittest.TestCase):
    """Tests for creation_oper_vessel_dict."""

    def test_mixes_normal_and_tow_operations(self):
        """
        Failures with 'specific month' strategy must:
        - be added to deferred_failures_correction
        - be assigned to oper_per_vessel[vessel1_id] if non-tow and not tow_to_port
        - be assigned to oper_per_vessel['tow'] if operation id contains 'tow'
          or tow_to_port is True.
        """
        # Define operations
        opA = DummyOperation(oid="opA", vessel1_id="V1", tow_to_port=False)   # normal op
        opTow = DummyOperation(oid="opTow", vessel1_id="V2", tow_to_port=True)  # tow due to tow_to_port
        opTowName = DummyOperation(oid="tow_special", vessel1_id="V3", tow_to_port=False)  # tow because name contains 'tow'

        operations_by_id = {
            "opA": opA,
            "opTow": opTow,
            "tow_special": opTowName,
        }
        finder = DummyFinder(operations_by_id=operations_by_id)

        # Define failures
        f1 = DummyFailure(fid="fail1", maintenance_strategy="specific month", operation_triggered="opA")
        f2 = DummyFailure(fid="fail2", maintenance_strategy="specific month", operation_triggered="opTow")
        f3 = DummyFailure(fid="fail3", maintenance_strategy="other", operation_triggered="opA")  # ignored
        f4 = DummyFailure(fid="fail4", maintenance_strategy="specific month", operation_triggered="tow_special")

        failures = [f1, f2, f3, f4]

        oper_per_vessel = {}
        deferred_failures_correction = []

        merged_deferred_aux.creation_oper_vessel_dict(
            failures=failures,
            find_element_class=finder,
            oper_per_vessel=oper_per_vessel,
            deferred_failures_correction=deferred_failures_correction,
        )

        # Check failures list
        self.assertCountEqual(
            deferred_failures_correction,
            ["fail1", "fail2", "fail4"],
        )

        # Check oper_per_vessel structure
        self.assertIn("V1", oper_per_vessel)
        self.assertIn("tow", oper_per_vessel)

        self.assertEqual(oper_per_vessel["V1"], ["opA"])
        # tow bucket contains only port operation (via name)
        self.assertCountEqual(
            oper_per_vessel["tow"],
            ["opTow"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
