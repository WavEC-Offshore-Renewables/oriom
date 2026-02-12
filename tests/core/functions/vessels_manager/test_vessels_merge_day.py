# test_vessels_merge_day.py

import unittest
import pandas as pd
import numpy as np
from datetime import datetime

from logistic_tools.core.functions.vessels_manager.vessels_merge_day import (
    number_vessels_func_with_oper,
    vessel_day_func,
    df_vessel_merge_use,
)


class TestNumberVesselsFuncWithOper(unittest.TestCase):
    def setUp(self):
        # Common base log_events for several tests
        self.log_events = pd.DataFrame(
            {
                # Two events on the same day
                "event": ["operation_corrective", "inspection_site"],
                "id": ["op1", "insp1"],
                "d_trigger": [
                    datetime(2025, 1, 1, 0, 0),
                    datetime(2025, 1, 1, 2, 0),
                ],
                "d_end_wait_start": [
                    datetime(2025, 1, 1, 1, 0),  # operation starts counting here
                    datetime(2025, 1, 1, 2, 0),  # not used for inspection
                ],
                "d_end": [
                    datetime(2025, 1, 1, 3, 0),  # operation ends here
                    datetime(2025, 1, 1, 4, 0),  # inspection ends here
                ],
                # used also for non-mobilisation mode (stat chart)
                "d_end_stat_chart": [
                    datetime(2025, 1, 1, 3, 0),
                    datetime(2025, 1, 1, 4, 0),
                ],
                "vessel_1": ["v1", "v1"],
                "n_vessel_1": [1, 1],
                "vessel_2": ["v2", None],
                "n_vessel_2": [2, 0],
            }
        )

    def test_number_vessels_normal_mode_counts_and_ops(self):
        """
        number_vessels_func_with_oper (mobilisation=False) should:
        - build an hourly time series from min(d_trigger) to max(d_end_stat_chart)
        - increment vessel_1 and vessel_2 according to overlaps
        - fill 'operations' column with dict {row_index: operation_id}
        """
        df = number_vessels_func_with_oper(
            log_events=self.log_events,
            col_to_count="d_end_wait_start",
            mobilisation=False,
        )

        # Time range: from 00:00 to 04:00, hourly -> 5 rows
        self.assertEqual(len(df), 5)
        expected_times = [
            datetime(2025, 1, 1, h, 0) for h in range(5)
        ]
        self.assertEqual(df["date"].tolist(), expected_times)

        # Helper to get row by datetime
        def row_at(hour):
            return df.loc[df["date"] == datetime(2025, 1, 1, hour, 0)].iloc[0]

        # Row 0: no operation yet
        r0 = row_at(0)
        self.assertEqual(r0["v1"], 0)
        self.assertEqual(r0["v2"], 0)
        self.assertIsInstance(r0["operations"], dict)
        self.assertEqual(r0["operations"], {})

        # Row 1: op1 only (operation from 1:00 to 3:00)
        r1 = row_at(1)
        self.assertEqual(r1["v1"], 1)
        self.assertEqual(r1["v2"], 2)
        self.assertEqual(r1["operations"], {0: "op1"})

        # Row 2: op1 + inspection (2:00 to 4:00)
        r2 = row_at(2)
        self.assertEqual(r2["v1"], 2)  # 1 from op1 + 1 from insp
        self.assertEqual(r2["v2"], 2)  # op1 only
        # operations dict must contain both indices 0 and 1
        self.assertEqual(r2["operations"], {0: "op1", 1: "insp1"})

        # Row 3: still both operations
        r3 = row_at(3)
        self.assertEqual(r3["v1"], 2)
        self.assertEqual(r3["v2"], 2)
        self.assertEqual(r3["operations"], {0: "op1", 1: "insp1"})

        # Row 4: only inspection
        r4 = row_at(4)
        self.assertEqual(r4["v1"], 1)
        self.assertEqual(r4["v2"], 0)
        self.assertEqual(r4["operations"], {1: "insp1"})

        # All vessel columns must be integer dtype
        self.assertTrue(np.issubdtype(df["v1"].dtype, np.integer))
        self.assertTrue(np.issubdtype(df["v2"].dtype, np.integer))

    def test_number_vessels_mobilisation_mode_filters_mobi_events(self):
        """
        mobilisation=True should:
        - use only events starting with 'mobi'
        - set d_end_stat_chart = d_end internally
        """
        log_events = pd.DataFrame(
            {
                "event": ["mobilisation", "operation_corrective"],
                "id": ["mobi1", "op1"],
                "d_trigger": [
                    datetime(2025, 1, 1, 0, 0),
                    datetime(2025, 1, 1, 2, 0),
                ],
                "d_end_wait_start": [
                    datetime(2025, 1, 1, 1, 0),
                    datetime(2025, 1, 1, 3, 0),
                ],
                "d_end": [
                    datetime(2025, 1, 1, 5, 0),
                    datetime(2025, 1, 1, 4, 0),
                ],
                "d_end_stat_chart": [pd.NaT, pd.NaT],
                "vessel_1": ["v1", "v1"],
                "n_vessel_1": [1, 1],
                "vessel_2": [None, None],
                "n_vessel_2": [0, 0],
            }
        )

        df = number_vessels_func_with_oper(
            log_events=log_events,
            col_to_count="d_end_wait_start",
            mobilisation=True,
        )

        # Only mobilisation row should be considered -> from 0:00 to 5:00
        self.assertEqual(len(df), 6)
        # operation id should be 'mobi1' only
        ops_union = set()
        for ops in df["operations"]:
            ops_union.update(ops.values())
        self.assertEqual(ops_union, {"mobi1"})


class TestVesselDayFunc(unittest.TestCase):
    def test_vessel_day_func_aggregates_max_per_day_and_merges_ops(self):
        """
        vessel_day_func should:
        - compute max vessel count per day for each vessel column
        - keep the operations dict from the hour with max usage
        - merge operations dicts for all vessels into a single 'operations' column
        """
        # Construct a small hourly df similar to number_vessels_func_with_oper output
        data = [
            # date, v1, v2, operations
            (datetime(2025, 1, 1, 0, 0), 0, 0, {}),
            (datetime(2025, 1, 1, 1, 0), 1, 2, {0: "op1"}),
            (datetime(2025, 1, 1, 2, 0), 2, 2, {0: "op1", 1: "insp1"}),
            (datetime(2025, 1, 1, 3, 0), 2, 2, {0: "op1", 1: "insp1"}),
            (datetime(2025, 1, 1, 4, 0), 1, 0, {1: "insp1"}),
        ]
        df_hourly = pd.DataFrame(
            data,
            columns=["date", "v1", "v2", "operations"],
        )

        daily = vessel_day_func(df_hourly)

        # Single day index
        self.assertEqual(len(daily), 1)
        self.assertEqual(daily.index[0], datetime(2025, 1, 1))

        # Max per day: v1=2, v2=2
        self.assertEqual(daily["v1"].iloc[0], 2)
        self.assertEqual(daily["v2"].iloc[0], 2)

        # operations must contain union of operations from max-usage rows
        ops = daily["operations"].iloc[0]
        self.assertIsInstance(ops, dict)
        self.assertEqual(ops, {0: "op1", 1: "insp1"})

    def test_vessel_day_func_empty_operations_dict(self):
        """
        vessel_day_func should handle days where operations dict is empty.
        """
        df_hourly = pd.DataFrame(
            {
                "date": [datetime(2025, 1, 1, h, 0) for h in range(3)],
                "v1": [0, 0, 0],
                "operations": [{}, {}, {}],
            }
        )
        daily = vessel_day_func(df_hourly)

        self.assertEqual(len(daily), 1)
        self.assertEqual(daily["v1"].iloc[0], 0)
        self.assertEqual(daily["operations"].iloc[0], {})


class TestDfVesselMergeUse(unittest.TestCase):
    def test_df_vessel_merge_use_composition(self):
        """
        df_vessel_merge_use should be equivalent to:
        vessel_day_func(number_vessels_func_with_oper(log_events))
        """
        log_events = pd.DataFrame(
            {
                "event": ["operation_corrective"],
                "id": ["op1"],
                "d_trigger": [datetime(2025, 1, 1, 0, 0)],
                "d_end_wait_start": [datetime(2025, 1, 1, 1, 0)],
                "d_end": [datetime(2025, 1, 1, 3, 0)],
                "d_end_stat_chart": [datetime(2025, 1, 1, 3, 0)],
                "vessel_1": ["v1"],
                "n_vessel_1": [1],
                "vessel_2": [None],
                "n_vessel_2": [0],
            }
        )

        df_direct = df_vessel_merge_use(log_events=log_events, col_to_count="d_end_wait_start")
        df_manual = vessel_day_func(
            number_vessels_func_with_oper(
                log_events=log_events,
                col_to_count="d_end_wait_start",
                mobilisation=False,
            )
        )

        # Same index and columns
        self.assertTrue(df_direct.index.equals(df_manual.index))
        self.assertEqual(set(df_direct.columns), set(df_manual.columns))

        # Same data for vessel columns and operations dict
        for col in df_direct.columns:
            if col == "operations":
                self.assertEqual(df_direct[col].iloc[0], df_manual[col].iloc[0])
            else:
                self.assertEqual(df_direct[col].iloc[0], df_manual[col].iloc[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
