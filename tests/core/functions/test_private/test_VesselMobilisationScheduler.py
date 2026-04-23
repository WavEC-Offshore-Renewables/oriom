# test_VesselMobilisationScheduler

import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

try:
    from oriom.core.functions.private.VesselMobilisationScheduler import (
        VesselMobilisationScheduler,
    )
except ImportError:
    raise unittest.SkipTest("VesselMobilisationScheduler module not available, test skipped")



class TestVesselMobilisationScheduler(unittest.TestCase):
    def setUp(self):
        # Create an instance without going through __init__ side effects
        self.scheduler = VesselMobilisationScheduler()
        self.scheduler.reuse_recall_vess_dict = {}
        self.scheduler.mobilisation_dict = {}
        self.scheduler.avoid_reuse = set()
        self.scheduler.avoid_deferred_reuse = set()

    # ------------------------------------------------------------------ #
    # datetime_conversion_to_date
    # ------------------------------------------------------------------ #
    def test_datetime_conversion_to_date(self):
        dt_index = pd.to_datetime(
            ["2025-01-01 12:00", "2025-01-02 00:00", "2025-01-02 23:59"]
        )
        series = pd.Series(dt_index)

        out = self.scheduler.datetime_conversion_to_date(series)
        self.assertEqual(list(out), [d.date() for d in dt_index])

    # ------------------------------------------------------------------ #
    # recreate_contract
    # ------------------------------------------------------------------ #
    @patch(
        "oriom.core.functions.private.VesselMobilisationScheduler.get_first_failure"
    )
    @patch(
        "oriom.core.functions.private.VesselMobilisationScheduler.take_id_operation"
    )
    def test_recreate_contract_basic(
        self, m_take_id_operation, m_get_first_failure
    ):
        """
        recreate_contract should:
        - add an entry to mobilisation_dict if mobilisation_time > 0
        - update reuse_recall_vess_dict[idx] with new chart end
        - compute new_chart_time using stats duration from find_element
        - return in_time_operation according to new_chart_time vs d_end
        """
        idx = 5
        chart_end = datetime(2025, 1, 10, 0, 0)
        mobilisation_time = 6.0  # hours
        n_vessel_recalled = 1

        # Row with required fields
        row = pd.Series(
            {
                "id": "ofw_fail_001.1",
                "comments": "ofw_fail_001",
                "event": "operation_corrective",
                "d_end_stat_chart": datetime(2025, 1, 10, 0, 0),
                "d_end": datetime(2025, 1, 12, 0, 0),
                "d_trigger": datetime(2025, 1, 8, 0, 0),
                "d_end_wait_start": datetime(2025, 1, 9, 0, 0),
            }
        )

        for col_name in ['d_trigger', 'd_end_wait_start', 'd_end']:
            row[col_name] = row[col_name].date()

        # Mock read_dataframe_value utilities
        m_take_id_operation.return_value = [["ofw_fail_001.1", "ofw_op001"]]
        m_get_first_failure.return_value = "ofw_fail_001"

        # Dummy operation stats returned by find_element
        op_stats = SimpleNamespace(
            dur_total_dict={
                "1": 72.0,  # 3 days
                "2": 10.0,
            }
        )

        find_element = SimpleNamespace(
            find_operation_stats_pmax=lambda _id: op_stats
        )

        new_chart_time, in_time = self.scheduler.recreate_contract(
            mobilisation_time=mobilisation_time,
            idx=idx,
            row=row,
            chart_end=chart_end,
            find_element=find_element,
            n_vessel_recalled=n_vessel_recalled,
        )

        # Stats: month = 1, so stats_chart_time = 72h → +72h from chart_end
        expected_new_chart = chart_end + timedelta(hours=72)
        self.assertEqual(new_chart_time, expected_new_chart)

        # in_time_operation: new_chart_time.date() >= row['d_end']
        self.assertTrue(in_time)

        # mobilisation_dict must have an entry for idx
        self.assertIn(idx, self.scheduler.mobilisation_dict)
        mob_entry = self.scheduler.mobilisation_dict[idx]
        self.assertEqual(mob_entry["mobilisation_call"], n_vessel_recalled)
        self.assertEqual(mob_entry["chart_end"][-1], chart_end)
        # op_end for non-inspection = d_end_wait_start_date
        self.assertEqual(mob_entry["op_end"][-1], row["d_end_wait_start"])
        # comments uses get_first_failure
        self.assertIn("ofw_fail_001", mob_entry["comments"][-1])

        # reuse_recall_vess_dict must be updated with the new chart time
        self.assertIn(idx, self.scheduler.reuse_recall_vess_dict)
        self.assertEqual(
            self.scheduler.reuse_recall_vess_dict[idx]["date"], expected_new_chart
        )
        self.assertIsNone(self.scheduler.reuse_recall_vess_dict[idx]["mobi_id"])

    # ------------------------------------------------------------------ #
    # stats_check
    # ------------------------------------------------------------------ #
    @patch.object(VesselMobilisationScheduler, "in_time_oper")
    @patch.object(VesselMobilisationScheduler, "recreate_contract")
    def test_stats_check_in_time_calls_in_time_oper_only(
        self, m_recreate_contract, m_in_time_oper
    ):
        """
        If in_time_operation is True, stats_check must call in_time_oper once
        and never call recreate_contract.
        """
        df = pd.DataFrame()
        row = pd.Series(
            {
                "id": "op1",
                "d_end_stat_chart": datetime(2025, 1, 10),
                "d_end": datetime(2025, 1, 9),
            }
        )
        vessel = SimpleNamespace(mother_vessel=False, mobilisation_time=4.0)

        in_time_operation = True

        self.scheduler.stats_check(
            log_events_event_reuse=df,
            find_element=MagicMock(),
            mobilisation_time=4.0,
            idx=3,
            row=row,
            in_time_operation=in_time_operation,
            chart_end=row["d_end_stat_chart"],
            vessel=vessel,
        )

        m_in_time_oper.assert_called_once()
        m_recreate_contract.assert_not_called()

    @patch.object(VesselMobilisationScheduler, "in_time_oper")
    @patch.object(VesselMobilisationScheduler, "recreate_contract")
    def test_stats_check_out_of_time_calls_recreate_then_in_time_oper(
        self, m_recreate_contract, m_in_time_oper
    ):
        """
        If in_time_operation is False, stats_check must call recreate_contract
        in a loop until it returns in_time_operation = True, then call in_time_oper.
        """
        df = pd.DataFrame()
        row = pd.Series(
            {
                "id": "op1",
                "d_end_stat_chart": datetime(2025, 1, 5),
                "d_end": datetime(2025, 1, 10),
            }
        )
        vessel = SimpleNamespace(mother_vessel=False, mobilisation_time=4.0)

        # First call returns still out-of-time, second call returns in-time
        first_chart = datetime(2025, 1, 7)
        second_chart = datetime(2025, 1, 11)
        m_recreate_contract.side_effect = [
            (first_chart, False),
            (second_chart, True),
        ]

        self.scheduler.stats_check(
            log_events_event_reuse=df,
            find_element=MagicMock(),
            mobilisation_time=4.0,
            idx=3,
            row=row,
            in_time_operation=False,
            chart_end=row["d_end_stat_chart"],
            vessel=vessel,
        )

        # recreate_contract called twice
        self.assertEqual(m_recreate_contract.call_count, 2)
        # in_time_oper called once with chart_end = second_chart
        m_in_time_oper.assert_called_once()
        args, kwargs = m_in_time_oper.call_args
        self.assertEqual(kwargs["chart_end"], second_chart)

    # ------------------------------------------------------------------ #
    # update_dataframe
    # ------------------------------------------------------------------ #
    def test_update_dataframe_reduces_vessels_and_updates_dates(self):
        """
        update_dataframe must:
        - reduce n_vessel_1_effective by 1 for insp/def rows with reuse_vessel
          when n_vessel_1_effective >= 2
        - update d_end_stat_chart for other indices in reuse_recall_vess_dict
        """
        idx_insp = 0
        idx_other = 1

        df = pd.DataFrame(
            {
                "d_trigger": [
                    datetime(2025, 1, 1),
                    datetime(2025, 1, 2),
                ],
                "d_end": [
                    datetime(2025, 1, 3),
                    datetime(2025, 1, 4),
                ],
                "d_end_stat_chart": [
                    datetime(2025, 1, 5),
                    datetime(2025, 1, 6),
                ],
                "event": [
                    "inspection_site",
                    "operation_corrective",
                ],
                "n_vessel_1_effective": [2, 1],
            }
        )

        # log_events_v can be just df in this test
        log_events_v = df.copy()

        # reuse_recall_vess_dict:
        # - idx_insp: reuse_vessel and >=2 vessels → decrement only
        # - idx_other: new datetime → update d_end_stat_chart
        new_date = datetime(2025, 2, 1)
        self.scheduler.reuse_recall_vess_dict = {
            idx_insp: {"date": "reuse_vessel", "mobi_id": "fail_001"},
            idx_other: {"date": new_date, "mobi_id": None},
        }

        out = self.scheduler.update_dataframe(
            log_events_stats_total=df.copy(), log_events_v=log_events_v
        )

        # idx_insp: n_vessel_1_effective decreased by 1, d_end_stat_chart unchanged
        self.assertEqual(out.loc[idx_insp, "n_vessel_1_effective"], 1)
        self.assertEqual(out.loc[idx_insp, "d_end_stat_chart"], df.loc[idx_insp, "d_end_stat_chart"])

        # idx_other: d_end_stat_chart updated, n_vessel_1_effective unchanged
        self.assertEqual(out.loc[idx_other, "n_vessel_1_effective"], 1)
        self.assertEqual(out.loc[idx_other, "d_end_stat_chart"], new_date)

    # ------------------------------------------------------------------ #
    # reduce_mobi_reused_vessel
    # ------------------------------------------------------------------ #
    @patch(
        "oriom.core.functions.private.VesselMobilisationScheduler.get_first_failure"
    )
    def test_reduce_mobi_reused_vessel_filters_by_mobi_id(self, m_get_first_failure):
        """
        reduce_mobi_reused_vessel:
        - ignores entries with mobi_id=None
        - filters mobilisation rows where id's suffix matches get_first_failure(mobi_id)
        """
        # reuse_recall_vess_dict: one relevant, one with mobi_id=None
        self.scheduler.reuse_recall_vess_dict = {
            10: {"date": "reuse_vessel", "mobi_id": "oper_ofw_fail_001.1", "oper_id": 'oper_owc_OP1'},
            20: {"date": "reuse_vessel", "mobi_id": None, 'oper_id': None},
        }

        m_get_first_failure.return_value = "oper_ofw_fail_001.1"

        df = pd.DataFrame(
            {
                "event": ["mobilisation", "mobilisation", "operation"],
                # id suffix after '_' is the failure id
                "id": [
                    "mobi_ofw_fail_001.1",
                    "mobi_ofw_fail_999",
                    "oper_ofw_fail_001.1",
                ],
                "comments": [
                    ["oper_owc_OP1"],
                    ["oper_owc_OP1"],
                    "oper_owc_OP1",
                ],
            },
            index=[100, 200, 300],
        )

        indices = self.scheduler.reduce_mobi_reused_vessel(df)

        # Only the mobilisation with suffix "ofw_fail_001" should be selected
        self.assertEqual(indices, {100})

    # ------------------------------------------------------------------ #
    # create_mobilisation_recall
    # ------------------------------------------------------------------ #
    @patch(
        "oriom.core.functions.private.VesselMobilisationScheduler.create_mobilisation"
    )
    def test_create_mobilisation_recall_calls_create_mobilisation(
        self, m_create_mobilisation
    ):
        """
        create_mobilisation_recall must call create_mobilisation once per
        mobilisation_call and return a list of the created rows.
        """
        df_mob = pd.DataFrame(columns=['dummy'] + ["other_dummy"]*18)
        vessel = SimpleNamespace(id="V1", mobilisation_time=6.0, n_vessels = 1)

        # Prepare mobilisation_dict with one idx, mobilised twice
        self.scheduler.mobilisation_dict = {
            3: {
                "chart_end": [
                    datetime(2025, 1, 10),
                    datetime(2025, 1, 20),
                ],
                "op_end": [
                    datetime(2025, 1, 11),
                    datetime(2025, 1, 21),
                ],
                "id": ["OP1", "OP2"],
                "comments": ["fail_001", "fail_002"],
                "mobilisation_call": 2,
            }
        }

        # create_mobilisation returns a dummy DataFrame row
        dummy_row_1 = pd.DataFrame(
            {"dummy": pd.Timestamp("2025-01-09 18:00:00")},
            index=[0]
        )

        dummy_row_2 = pd.DataFrame(
            {"dummy": pd.Timestamp("2025-01-19 18:00:00")},
            index=[0]
        )
        m_create_mobilisation.side_effect = [dummy_row_1, dummy_row_2]

        out_list = self.scheduler.create_mobilisation_recall(
            df_mobilisation=df_mob,
            vessel=vessel,
        )

        self.assertEqual(len(out_list), 2)
        assert out_list[0]["dummy"].iloc[0] == dummy_row_1["dummy"].iloc[0]
        assert out_list[1]["dummy"].iloc[0] == dummy_row_2["dummy"].iloc[0]


        # Check that the dates passed to create_mobilisation are consistent
        self.assertEqual(
            out_list[0]["dummy"].iloc[0],
            datetime(2025, 1, 10) - timedelta(hours=vessel.mobilisation_time),
        )
        self.assertEqual(
            out_list[1]["dummy"].iloc[0],
            datetime(2025, 1, 19, 18, 00 , 00)
        )

    # ------------------------------------------------------------------ #
    # charts_manager (smoke test)
    # ------------------------------------------------------------------ #
    @patch(
        "oriom.core.functions.private.VesselMobilisationScheduler.safe_copy_df"
    )
    def test_charts_manager_smoke_no_ST_contract(self, m_safe_copy_df):
        """
        charts_manager must:
        - create d_end_stat_chart_orig
        - create n_vessel_1_effective
        - return a DataFrame sorted by d_trigger
        when there are no ST_contract=True rows.
        """
        # safe_copy_df should behave as a simple .copy()
        m_safe_copy_df.side_effect = lambda df, *args, **kwargs: df.copy()

        df = pd.DataFrame(
            {
                "d_trigger": [
                    datetime(2025, 1, 3),
                    datetime(2025, 1, 1),
                ],
                "d_end_wait_start": [
                    datetime(2025, 1, 3),
                    datetime(2025, 1, 1),
                ],
                "d_end": [
                    datetime(2025, 1, 4),
                    datetime(2025, 1, 2),
                ],
                "d_end_stat_chart": [
                    datetime(2025, 1, 5),
                    datetime(2025, 1, 3),
                ],
                "id": ["op2", "op1"],
                "event": ["operation", "operation"],
                "vessel_1": ["V1", "V1"],
                "n_vessel_1": [1, 1],
                "vessel_2": [np.nan, np.nan],
                "comments": ["", ""],
                "ST_contract_1": [False, False],
                "ST_contract_2": [False, False],
            }
        )

        vessel = SimpleNamespace(
            id="V1", mobilisation_time=4.0, mother_vessel=False
        )

        find_element = MagicMock()  # not used since no ST_contract=True

        out = self.scheduler.charts_manager(
            log_events_merged=df, vessels=[vessel], find_element=find_element
        )

        # Column d_end_stat_chart_orig must exist and equal original
        self.assertIn("d_end_stat_chart_orig", out.columns)
        self.assertTrue(
            (
                out["d_end_stat_chart_orig"].sort_values().values
                == df["d_end_stat_chart"].sort_values().values
            ).all()
        )

        # n_vessel_1_effective must exist and equal n_vessel_1
        self.assertIn("n_vessel_1_effective", out.columns)
        self.assertTrue(
            (
                out["n_vessel_1_effective"].sort_values().values
                == df["n_vessel_1"].sort_values().values
            ).all()
        )

        # Sorted by d_trigger ascending
        self.assertTrue(
            out["d_trigger"].tolist()
            == sorted(df["d_trigger"].tolist())
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
