# tests_create_logs_timeseries.py

import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

import pandas as pd

from oriom.core.functions.logs_timeseries.create_logs_timeseries import (
    create_logs_timeseries_file,
)


class TestCreateLogsTimeseriesFile(unittest.TestCase):
    def setUp(self):
        """Set up a minimal inputs object and common parameters."""
        # Inputs.stats.*["value"]
        stats = SimpleNamespace(
            start_year={"value": 2020},       # start year
            lifetime={"value": 3},           # 3-year lifetime
            start_month={"value": 3},        # March
            percentile_max={"value": 0.9},   # percentile
        )
        # Inputs.tseries.merge_vessel["value"]
        tseries = SimpleNamespace(
            merge_vessel={"value": ["vA", "vB"]}
        )

        self.inputs = SimpleNamespace(
            stats=stats,
            tseries=tseries,
        )

        # Common placeholders
        self.dates_failures = pd.DataFrame()
        self.failures = []
        self.operation_log_file_stats = ["dummy_op_stats"]
        self.inspections_port_stat = ["dummy_port_stat"]
        self.inspections_site_stat = ["dummy_site_stat"]
        self.time_fail_op_immediately = 0.5
        self.vessels = ["v1", "v2"]
        self.find_element_class = object()
        self.mother_vessels_list = []

        # Expected cutoff:
        # start_year=2020, lifetime=3 -> 2023
        # start_month=3 -> end_month=2, same year 2023
        # last day of Feb=28 => 2023-02-28 23:59:59
        self.expected_cutoff_date = pd.to_datetime("2023-02-28 23:59:59")

    # Helper to build rows consistent with COLS
    def _make_row(self, trigger_str: str, label: str):
        dt = pd.to_datetime(trigger_str)
        return {
            "d_trigger": dt,
            "d_end_leadtime": dt,
            "d_end_wait_start": dt,
            "d_end_dur_net_port": dt,
            "d_end_transit_ts": dt,
            "d_end_wait_site": dt,
            "d_end_dur_net_site": dt,
            "d_end_transit_tp": dt,
            "d_end": dt,
            "d_end_stat_chart": dt,
            "event": f"event_{label}",
            "id": f"id_{label}",
            "vessel_1": "v1",
            "n_vessel_1": 1,
            "vessel_2": None,
            "n_vessel_2": 0,
            "comments": "",
        }

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_timeseries"
        ".logs_timeseries_func.shutdown_evaluation"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_timeseries"
        ".Stat_chart_inspection_campaign"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_timeseries"
        ".create_logs_events_preventive.create_logs_preventive"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_timeseries"
        ".create_logs_events_corrective.create_logs_corrective_file"
    )
    def test_flow_calls_subfunctions_and_filters_by_cutoff(
        self,
        m_create_logs_corrective,
        m_create_logs_preventive,
        m_stat_campaign_cls,
        m_shutdown_eval,
    ):
        """
        Full happy-path test:
        - verify that subfunctions are called with expected arguments (CUTOFF_DATE,
          percentile, vessel_to_merge, inspections_site_stat, vessels);
        - verify that concatenation is passed into shutdown_evaluation;
        - verify that the returned dataframe is filtered by CUTOFF_DATE and sorted by d_trigger.
        """

        # Corrective logs: two rows, one inside cutoff, one after cutoff
        corr_rows = [
            self._make_row("2023-02-20 12:00:00", "corr_keep"),
            self._make_row("2023-03-01 00:00:00", "corr_drop"),
        ]
        df_corr = pd.DataFrame(corr_rows)

        # Preventive logs: one row before everything, inside cutoff
        prev_rows_raw = [
            self._make_row("2022-12-31 10:00:00", "prev_keep"),
        ]
        df_prev_raw = pd.DataFrame(prev_rows_raw)

        # After Stat_chart_inspection_campaign, the preventive df is processed
        df_prev_processed = df_prev_raw.copy()

        m_create_logs_corrective.return_value = df_corr
        m_create_logs_preventive.return_value = df_prev_raw

        # Mock Stat_chart_inspection_campaign instance
        stat_instance = MagicMock()
        stat_instance.create_stat_chart_inspection_campaign.return_value = df_prev_processed
        m_stat_campaign_cls.return_value = stat_instance

        # Combined dataframe returned by shutdown_evaluation
        combined = pd.concat([df_corr, df_prev_processed], axis=0, ignore_index=True)
        m_shutdown_eval.return_value = combined

        result = create_logs_timeseries_file(
            inputs=self.inputs,
            dates_failures=self.dates_failures,
            failures=self.failures,
            operation_log_file_stats=self.operation_log_file_stats,
            inspections_port_stat=self.inspections_port_stat,
            inspections_site_stat=self.inspections_site_stat,
            time_fail_op_immediately=self.time_fail_op_immediately,
            vessels=self.vessels,
            find_element_class=self.find_element_class,
            vessel_to_merge=None,  # default path must become []
            mother_vessels_list=self.mother_vessels_list,
        )

        # --- Check call to create_logs_corrective_file ---
        m_create_logs_corrective.assert_called_once()
        _, kwargs_corr = m_create_logs_corrective.call_args

        self.assertEqual(kwargs_corr["CUTOFF_DATE"], self.expected_cutoff_date)
        # vessel_to_merge should be [] when None is passed
        self.assertEqual(kwargs_corr["vessel_to_merge"], [])

        # --- Check call to create_logs_preventive ---
        m_create_logs_preventive.assert_called_once()
        _, kwargs_prev = m_create_logs_preventive.call_args
        self.assertIs(kwargs_prev["inputs"], self.inputs)
        self.assertEqual(
            kwargs_prev["percentile"],
            self.inputs.stats.percentile_max["value"],
        )

        # --- Stat_chart_inspection_campaign usage ---
        m_stat_campaign_cls.assert_called_once_with(
            inspections_site_stat=self.inspections_site_stat
        )
        stat_instance.create_stat_chart_inspection_campaign.assert_called_once()
        _, kwargs_stat = stat_instance.create_stat_chart_inspection_campaign.call_args
        # df argument should be the preventive df returned by create_logs_preventive
        pd.testing.assert_frame_equal(kwargs_stat["df"], df_prev_raw)
        self.assertIs(kwargs_stat["vessels"], self.vessels)
        self.assertEqual(
            kwargs_stat["percentile"],
            self.inputs.stats.percentile_max["value"],
        )

        # --- shutdown_evaluation is called with concatenated logs ---
        m_shutdown_eval.assert_called_once()
        _, kwargs_shutdown = m_shutdown_eval.call_args
        log_events_passed = kwargs_shutdown["log_events"]
        expected_concat = pd.concat(
            [df_corr, df_prev_processed], axis=0, ignore_index=True
        )
        pd.testing.assert_frame_equal(log_events_passed, expected_concat)

        # --- Final result is filtered and sorted by d_trigger ---
        expected_filtered_sorted = (
            combined[combined["d_trigger"] < self.expected_cutoff_date]
            .sort_values(by="d_trigger")
            .reset_index(drop=True)
        )
        pd.testing.assert_frame_equal(result, expected_filtered_sorted)

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_timeseries"
        ".logs_timeseries_func.shutdown_evaluation"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_timeseries"
        ".Stat_chart_inspection_campaign"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_timeseries"
        ".create_logs_events_preventive.create_logs_preventive"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_timeseries"
        ".create_logs_events_corrective.create_logs_corrective_file"
    )
    def test_vessel_to_merge_is_passed_through_when_provided(
        self,
        m_create_logs_corrective,
        m_create_logs_preventive,
        m_stat_campaign_cls,
        m_shutdown_eval,
    ):
        """
        If vessel_to_merge is explicitly provided, it must be passed unchanged
        to create_logs_corrective_file.
        """
        # Minimal non-empty frames to avoid edge cases
        df_corr = pd.DataFrame([self._make_row("2022-01-01 00:00:00", "c1")])
        df_prev = pd.DataFrame([self._make_row("2022-01-02 00:00:00", "p1")])

        m_create_logs_corrective.return_value = df_corr
        m_create_logs_preventive.return_value = df_prev

        stat_instance = MagicMock()
        stat_instance.create_stat_chart_inspection_campaign.return_value = df_prev
        m_stat_campaign_cls.return_value = stat_instance

        # After shutdown_evaluation, return same df
        combined = pd.concat([df_corr, df_prev], ignore_index=True)
        m_shutdown_eval.return_value = combined

        vessel_to_merge = ["CTV", "SOV"]

        _ = create_logs_timeseries_file(
            inputs=self.inputs,
            dates_failures=self.dates_failures,
            failures=self.failures,
            operation_log_file_stats=self.operation_log_file_stats,
            inspections_port_stat=self.inspections_port_stat,
            inspections_site_stat=self.inspections_site_stat,
            time_fail_op_immediately=self.time_fail_op_immediately,
            vessels=self.vessels,
            find_element_class=self.find_element_class,
            vessel_to_merge=vessel_to_merge,  # here we pass a list
            mother_vessels_list=self.mother_vessels_list,
        )

        m_create_logs_corrective.assert_called_once()
        _, kwargs_corr = m_create_logs_corrective.call_args
        self.assertEqual(kwargs_corr["vessel_to_merge"], vessel_to_merge)


if __name__ == "__main__":
    unittest.main(verbosity=2)
