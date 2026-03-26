# test_define_merged_operations.py

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

# Update this import path if the function is located in a different module.
from oriom.core.functions.operation_scheduler.define_merged_operations import define_merged_operations_values


class TestDefineMergedOperationsValues(unittest.TestCase):

    def setUp(self):
        """
        Prepare reusable inputs for the tests.
        """

        self.operation = SimpleNamespace(id=1, name="Test operation")

        self.shift_data_basic = {
            "number_shifts_main": 1,
            "duration_shift_main": 2.0,
            "number_shifts_last": 1,
            "duration_shift_last": 1.0,
        }

        self.shift_data_with_two_solo_shifts = {
            "number_shifts_main": 1,
            "duration_shift_main": 2.0,
            "number_shifts_last": 2,
            "duration_shift_last": 1.0,
        }

        self.transit_duration = 0.25
        self.shutdown_wtg = 10.0
        self.shutdown_wec = 20.0
        self.shutdown_pv = 30.0

        self._original_tqdm = define_merged_operations_values.__globals__["tqdm"]
        define_merged_operations_values.__globals__["tqdm"] = lambda iterable, **kwargs: iterable
        self.addCleanup(self._restore_tqdm)

    def _restore_tqdm(self):
        """
        Restore the original tqdm object after each test.
        """

        define_merged_operations_values.__globals__["tqdm"] = self._original_tqdm

    @staticmethod
    def _build_workability_dataframe(index, true_hours):
        """
        Build a single-column workability DataFrame.
        """

        values = [dt.hour in true_hours for dt in index]
        return pd.DataFrame({"workability": values}, index=index)

    def test_raises_value_error_when_group_dataframe_has_more_than_one_column(self):
        """
        Ensure the function raises ValueError when the grouped workability DataFrame
        has more than one column.
        """

        index = pd.date_range("2025-01-01 08:00:00", periods=6, freq="h")
        df_workability_group = pd.DataFrame(
            {
                "workability_1": [True] * 6,
                "workability_2": [True] * 6,
            },
            index=index,
        )
        df_workability_solo = pd.DataFrame({"workability": [True] * 6}, index=index)

        with self.assertRaises(ValueError) as context:
            define_merged_operations_values(
                ts_analyse=[0],
                operation=self.operation,
                df_workability_group=df_workability_group,
                df_workability_solo=df_workability_solo,
                shift_data=self.shift_data_basic,
                transit_duration=self.transit_duration,
                shutdown_wtg=self.shutdown_wtg,
                shutdown_wec=self.shutdown_wec,
                shutdown_pv=self.shutdown_pv,
            )

        self.assertIn("This function only works with operations.", str(context.exception))

    def test_raises_value_error_when_solo_dataframe_has_more_than_one_column(self):
        """
        Ensure the function raises ValueError when the solo workability DataFrame
        has more than one column.
        """

        index = pd.date_range("2025-01-01 08:00:00", periods=6, freq="h")
        df_workability_group = pd.DataFrame({"workability": [True] * 6}, index=index)
        df_workability_solo = pd.DataFrame(
            {
                "workability_1": [True] * 6,
                "workability_2": [True] * 6,
            },
            index=index,
        )

        with self.assertRaises(ValueError) as context:
            define_merged_operations_values(
                ts_analyse=[0],
                operation=self.operation,
                df_workability_group=df_workability_group,
                df_workability_solo=df_workability_solo,
                shift_data=self.shift_data_basic,
                transit_duration=self.transit_duration,
                shutdown_wtg=self.shutdown_wtg,
                shutdown_wec=self.shutdown_wec,
                shutdown_pv=self.shutdown_pv,
            )

        self.assertIn("This function only works with operations.", str(context.exception))

    def test_returns_expected_values_for_simple_feasible_case_and_saves_csv(self):
        """
        Ensure the function returns the expected schedule values for a simple feasible
        case and saves the CSV file when an output path is provided.
        """

        index = pd.date_range("2025-01-01 08:00:00", periods=15, freq="h")
        df_workability_group = pd.DataFrame({"workability": [True] * len(index)}, index=index)
        df_workability_solo = pd.DataFrame({"workability": [True] * len(index)}, index=index)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
            out_dir = tmp_file.name

        try:
            with patch.object(
                define_merged_operations_values.__globals__["logging"],
                "info",
            ) as mock_logging_info:
                df_out = define_merged_operations_values(
                    ts_analyse=[0],
                    operation=self.operation,
                    df_workability_group=df_workability_group,
                    df_workability_solo=df_workability_solo,
                    shift_data=self.shift_data_basic,
                    transit_duration=self.transit_duration,
                    shutdown_wtg=self.shutdown_wtg,
                    shutdown_wec=self.shutdown_wec,
                    shutdown_pv=self.shutdown_pv,
                    out_dir=out_dir,
                )

            self.assertIsInstance(df_out, pd.DataFrame)
            self.assertTrue(os.path.exists(out_dir))
            self.assertEqual(df_out.index[0], index[0])

            self.assertEqual(df_out.iloc[0]["dur_net_site_group"], 1.5)
            self.assertEqual(df_out.iloc[0]["dur_net_site_solo"], 0.5)
            self.assertEqual(df_out.iloc[0]["transit_to_site_group"], 0.25)
            self.assertEqual(df_out.iloc[0]["transit_to_site_solo"], 0.25)
            self.assertEqual(df_out.iloc[0]["transit_to_port_group"], 0.25)
            self.assertEqual(df_out.iloc[0]["transit_to_port_solo"], 0.25)
            self.assertEqual(df_out.iloc[0]["wait_start"], 0.0)
            self.assertEqual(df_out.iloc[0]["wait_port_group"], 0.0)
            self.assertEqual(df_out.iloc[0]["wait_port_solo"], 0.0)
            self.assertEqual(df_out.iloc[0]["dur_shutdown_wtg"], self.shutdown_wtg)
            self.assertEqual(df_out.iloc[0]["dur_shutdown_wec"], self.shutdown_wec)
            self.assertEqual(df_out.iloc[0]["dur_shutdown_pv"], self.shutdown_pv)
            self.assertEqual(df_out.iloc[0]["dur_total"], 3.0)

            expected_columns = [
                "dur_total",
                "dur_net_site_group",
                "dur_net_site_solo",
                "wait_start",
                "wait_port_group",
                "wait_port_solo",
                "transit_to_site_group",
                "transit_to_site_solo",
                "transit_to_port_group",
                "transit_to_port_solo",
                "dur_shutdown_wtg",
                "dur_shutdown_wec",
                "dur_shutdown_pv",
            ]
            self.assertEqual(list(df_out.columns), expected_columns)

            mock_logging_info.assert_called_once()
        finally:
            if os.path.exists(out_dir):
                os.remove(out_dir)

    def test_double_shift_allows_night_hours_and_reduces_wait_start(self):
        """
        Ensure enabling double_shift allows operations to start during night hours
        and reduces the initial waiting time.
        """

        index = pd.date_range("2025-01-01 00:00:00", periods=24, freq="h")

        group_true_hours = {0, 1, 2, 8, 9, 10}
        solo_true_hours = {0, 1, 8, 9, 10}

        df_workability_group = self._build_workability_dataframe(index, group_true_hours)
        df_workability_solo = self._build_workability_dataframe(index, solo_true_hours)

        df_out_without_double_shift = define_merged_operations_values(
            ts_analyse=[0],
            operation=self.operation,
            df_workability_group=df_workability_group,
            df_workability_solo=df_workability_solo,
            shift_data=self.shift_data_basic,
            transit_duration=self.transit_duration,
            shutdown_wtg=self.shutdown_wtg,
            shutdown_wec=self.shutdown_wec,
            shutdown_pv=self.shutdown_pv,
            double_shift=False,
        )

        df_out_with_double_shift = define_merged_operations_values(
            ts_analyse=[0],
            operation=self.operation,
            df_workability_group=df_workability_group,
            df_workability_solo=df_workability_solo,
            shift_data=self.shift_data_basic,
            transit_duration=self.transit_duration,
            shutdown_wtg=self.shutdown_wtg,
            shutdown_wec=self.shutdown_wec,
            shutdown_pv=self.shutdown_pv,
            double_shift=True,
        )

        self.assertEqual(df_out_with_double_shift.iloc[0]["wait_start"], 0.0)

    def test_splits_waiting_between_group_and_solo_when_solo_starts_first(self):
        """
        Ensure waiting time is split correctly when the solo operation starts before
        the grouped operation.
        """

        index = pd.date_range("2025-01-01 08:00:00", periods=8, freq="h")

        group_true_hours = {10, 11, 12}
        solo_true_hours = {8, 9, 12, 13}

        df_workability_group = self._build_workability_dataframe(index, group_true_hours)
        df_workability_solo = self._build_workability_dataframe(index, solo_true_hours)

        df_out = define_merged_operations_values(
            ts_analyse=[0],
            operation=self.operation,
            df_workability_group=df_workability_group,
            df_workability_solo=df_workability_solo,
            shift_data=self.shift_data_with_two_solo_shifts,
            transit_duration=self.transit_duration,
            shutdown_wtg=self.shutdown_wtg,
            shutdown_wec=self.shutdown_wec,
            shutdown_pv=self.shutdown_pv,
        )

        self.assertEqual(df_out.iloc[0]["wait_start"], 0.0)
        self.assertEqual(df_out.iloc[0]["wait_port_solo"], 0.0)
        self.assertEqual(df_out.iloc[0]["wait_port_group"], 0.0)


if __name__ == "__main__":
    unittest.main()