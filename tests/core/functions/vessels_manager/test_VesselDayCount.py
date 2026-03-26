#test_VesselDayCount.py

import unittest
from datetime import datetime
from types import SimpleNamespace

import pandas as pd
import numpy as np

from oriom.core.functions.vessels_manager.VesselDayCount import (
    VesselDayCounter,
)


def make_vessel(
    vid,
    n_ves_annual_contract=0,
    months_contract=None,
    n_ves_monthly_contract=0,
):
    """Build a minimal vessel-like object with the required contract attributes."""
    return SimpleNamespace(
        id=vid,
        n_ves_annual_contract=n_ves_annual_contract,
        months_contract=months_contract or [],
        n_ves_monthly_contract=n_ves_monthly_contract,
    )


class TestVesselDayCounter(unittest.TestCase):
    def setUp(self):
        # We bypass __init__ to avoid dependencies on aux_functions and external files
        self.counter = object.__new__(VesselDayCounter)
        self.counter.dict_vess_long_term = {}
        self.counter.usage_records = {}
        self.counter.vessels_calendar = pd.DataFrame()

    # -------------------------------------------------------------------------
    # create_dict_vessel_contract_month
    # -------------------------------------------------------------------------
    def test_create_dict_vessel_contract_month_basic(self):
        """Annual and monthly contracts are correctly expanded per month."""
        v1 = make_vessel("V1", n_ves_annual_contract=1)  # 1 vessel all year
        v2 = make_vessel(
            "V2",
            n_ves_annual_contract=0,
            months_contract=[6, 7],
            n_ves_monthly_contract=2,  # 2 vessels only in June and July
        )
        v3 = make_vessel("V3", n_ves_annual_contract=0)  # no contract at all

        self.counter.create_dict_vessel_contract_month([v1, v2, v3])

        # V1 must have 1 vessel in all 12 months
        self.assertIn("V1", self.counter.dict_vess_long_term)
        self.assertEqual(
            self.counter.dict_vess_long_term["V1"],
            {m: 1 for m in range(1, 13)},
        )

        # V2 must have 2 vessels only in months 6 and 7, 0 elsewhere
        self.assertIn("V2", self.counter.dict_vess_long_term)
        self.assertEqual(self.counter.dict_vess_long_term["V2"][6], 2)
        self.assertEqual(self.counter.dict_vess_long_term["V2"][7], 2)
        for m in range(1, 13):
            if m not in (6, 7):
                self.assertEqual(self.counter.dict_vess_long_term["V2"][m], 0)

        # V3 should not appear (no month with contract > 0)
        self.assertNotIn("V3", self.counter.dict_vess_long_term)

    # -------------------------------------------------------------------------
    # log_event_preparation
    # -------------------------------------------------------------------------
    def test_log_event_preparation_merges_campaign_operations(self):
        """
        Campaign operations (operation_deferred_merged) are reduced so that
        only one row per campaign remains, with start taken from the earliest
        row and non-campaign operations preserved.
        """
        # Columns: first three are those copied between rows in a campaign
        dt0 = datetime(2025, 1, 1, 0, 0)
        dt1 = datetime(2025, 1, 2, 0, 0)
        dt2 = datetime(2025, 1, 3, 0, 0)
        dt3 = datetime(2025, 1, 4, 0, 0)

        df = pd.DataFrame(
            {
                "d_trigger": [dt0, dt0, dt0, dt2, dt3],
                "d_end_leadtime": [dt0, dt0, dt0, dt2, dt3],
                "d_end_wait_start": [dt0, dt0, dt0, dt2, dt3],
                "d_end": [dt1, dt1, dt1, dt3, dt3],
                "vessel_1": [None, 'v001', 'v001', 'v002', 'v001'],
                "event": [
                    "failure"    ,                 # failure
                    "operation_deferred_merged",  # same campaign same vessel
                    "operation_deferred_merged",  # same campaign same vessel
                    "operation_deferred_merged",  # same campaign different vessel
                    "operation",                  # normal operation
                ],
                "comments": ["x", "x", "x", "x", "y"],
                "d_end_stat_chart": [
                    datetime(2025, 1, 10),
                    datetime(2025, 1, 10),  # same key for first 2 rows
                    datetime(2025, 1, 10), 
                    datetime(2025, 1, 10),
                    datetime(2025, 1, 20),
                ],
            }
        )

        out = self.counter.log_event_preparation(df.copy())

        # We expect:
        # - 1 merged campaign row for the 'operation_deferred_merged'
        # - 1 row for the normal 'operation'
        self.assertEqual(len(out), 3)
        self.assertEqual(out["event"].tolist().count("operation_deferred_merged"), 2)
        self.assertEqual(out["event"].tolist().count("operation"), 1)

        # The remaining campaign row should have d_trigger equal to earliest
        # d_trigger of the campaign.
        campaign_row = out[out["event"] == "operation_deferred_merged"].iloc[0]
        self.assertEqual(campaign_row["d_trigger"], dt0)

    # -------------------------------------------------------------------------
    # date_evaluation
    # -------------------------------------------------------------------------
    def test_date_evaluation_branches_inspection_and_operation(self):
        """date_evaluation returns correct start/end for inspection and other events."""
        row = pd.Series(
            {
                "d_trigger": datetime(2025, 5, 1, 8),
                "d_end": datetime(2025, 5, 3, 18),
                "d_end_stat_chart": datetime(2025, 5, 4, 0),
                "d_end_wait_start": datetime(2025, 5, 1, 10),
                "d_end_leadtime": datetime(2025, 5, 2, 0),
            }
        )

        # Inspection: uses d_trigger + d_end when effective_dates=True
        start, end = self.counter.date_evaluation(row, "inspection_site", True)
        self.assertEqual(start, row["d_trigger"])
        self.assertEqual(end, row["d_end"])

        # Inspection: uses d_trigger + d_end_stat_chart when effective_dates=False
        start, end = self.counter.date_evaluation(row, "inspection_site", False)
        self.assertEqual(start, row["d_trigger"])
        self.assertEqual(end, row["d_end_stat_chart"])

        # Other events: uses d_end_wait_start + d_end when effective_dates=True
        start, end = self.counter.date_evaluation(row, "operation", True)
        self.assertEqual(start, row["d_end_wait_start"])
        self.assertEqual(end, row["d_end"])

        # Other events: uses d_end_leadtime + d_end_stat_chart when effective_dates=False
        start, end = self.counter.date_evaluation(row, "operation", False)
        self.assertEqual(start, row["d_end_leadtime"])
        self.assertEqual(end, row["d_end_stat_chart"])

    # -------------------------------------------------------------------------
    # allocate_vessels + count_day_vessel
    # -------------------------------------------------------------------------
    def _build_single_operation_df(self):
        """Helper: build a minimal log_events_merged/log_event_day DataFrame."""
        d_trig = datetime(2025, 1, 1, 0, 0)
        d_end_wait_start = datetime(2025, 1, 1, 0, 0)  # for effective_dates=True (operation)
        d_end = datetime(2025, 1, 3, 0, 0)
        d_end_leadtime = datetime(2025, 1, 2, 0, 0)    # for effective_dates=False
        d_end_stat_chart = datetime(2025, 1, 4, 0, 0)  # for effective_dates=False

        df = pd.DataFrame(
            {
                "id": ["op1"],
                "event": ["operation"],
                "comments": [""],
                "d_trigger": [d_trig],
                "d_end_wait_start": [d_end_wait_start],
                "d_end": [d_end],
                "d_end_leadtime": [d_end_leadtime],
                "d_end_stat_chart": [d_end_stat_chart],
                "vessel_1": ["V1"],
                "n_vessel_1": [2],             # used when ST=True
                "n_vessel_1_effective": [2],   # used when ST=False
                "vessel_2": [np.nan],
                "n_vessel_2": [0],
            }
        )
        return df

    def test_allocate_vessels_and_count_short_term_LT_only(self):
        """
        When the requested number of vessels exceeds the long-term contract,
        usage is recorded and count_day_vessel returns the correct
        number of short-term vessel-days.
        """
        # Long-term contract: 1 vessel per month in every month
        self.counter.dict_vess_long_term = {
            "V1": {m: 1 for m in range(1, 13)}
        }
        self.counter.usage_records = {}
        self.counter.vessels_calendar = pd.DataFrame()

        # Build log_event_day and pass the same DataFrame as log_events_merged
        df_events = self._build_single_operation_df()
        self.counter.log_event_day = df_events.copy()

        # No ST flag; only LT capacity is considered, and vessel usage is stored
        log_events_merged_out = self.counter.allocate_vessels(
            log_events_merged=df_events.copy(),
            ST=False,
        )

        # usage_records must reflect 2 vessels per day from 2025-01-02 to 2025-01-04
        cal = self.counter.vessels_calendar
        self.assertIn("V1", cal.columns)
        self.assertEqual(
            cal.index.tolist(),
            [
                datetime(2025, 1, 2),
                datetime(2025, 1, 3),
                datetime(2025, 1, 4),
            ],
        )
        self.assertTrue((cal["V1"] == 2).all())

        # Long-term allows 1 vessel per day → 1 short-term per day → 3 short-term vessel-days
        st_days = self.counter.count_day_vessel("V1")
        self.assertEqual(st_days, 6)

        # A vessel not present in the calendar returns 0
        self.assertEqual(self.counter.count_day_vessel("V_UNKNOWN"), 0)

        # ST_contract is not touched when ST=False
        self.assertNotIn("ST_contract_1", log_events_merged_out.columns)

    def test_allocate_vessels_marks_ST_contract_when_needed(self):
        """
        When ST=True and LT capacity is exceeded, ST_contract_1 is set to True
        on the corresponding row.
        """
        # Long-term contract: 1 vessel per month
        self.counter.dict_vess_long_term = {
            "V1": {m: 1 for m in range(1, 13)}
        }
        self.counter.usage_records = {}
        self.counter.vessels_calendar = pd.DataFrame()

        df_events = self._build_single_operation_df()
        # ST_contract column initialized to False
        df_events["ST_contract_1"] = False

        self.counter.log_event_day = df_events.copy()

        out = self.counter.allocate_vessels(
            log_events_merged=df_events,
            ST=True,
            contract_evaluation=True
        )

        # Since 2 > 1 LT vessels needed, row should be marked as ST_contract
        self.assertTrue(out["ST_contract_1"].iloc[0])

        # Calendar still records the full usage (2 per day, 3 days)
        cal = self.counter.vessels_calendar
        self.assertIn("V1", cal.columns)
        self.assertTrue((cal["V1"] == 2).all())
        self.assertEqual(len(cal.index), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
