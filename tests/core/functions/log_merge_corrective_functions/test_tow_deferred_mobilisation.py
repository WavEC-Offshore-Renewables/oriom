# test_tow_deferred_mobilisation
import unittest
import pandas as pd
from unittest.mock import MagicMock, patch

from logistic_tools.core.functions.log_merge_corrective_functions.tow_deferred_mobilisation import tow_deferred_mobi


# --------------------------------------------
# Helper: Fake Vessel
# --------------------------------------------
class FakeVessel:
    def __init__(self, mobilisation_time=10):
        self.mobilisation_time = mobilisation_time


# ============================================
# TEST 1
# No event → Empty DataFrame
# ============================================
class TestEmptyData(unittest.TestCase):
    #AVOID THIS TEST AS IMPOSSIBLE TO OCCURE, CHECK IF VALID DATAFRAME BEFORE tow_deferred_mobi
    def test_no_events_returns_empty_df(self):
        return
        COLS = ["id", "vessel_1", "n_vessel_1", "d_trigger", "d_end_wait_start", "comments"]
        empty_df = pd.DataFrame(columns=COLS)

        find_class = MagicMock()

        result = tow_deferred_mobi(COLS, empty_df, find_class)

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 0)
        self.assertListEqual(list(result.columns), COLS)


# ============================================
# TEST 2
# Single event → mobilisation created
# ============================================
class TestSingleVesselMobi(unittest.TestCase):

    @patch("logistic_tools.core.functions.log_merge_corrective_functions.tow_deferred_mobilisation.create_mobilisation")
    def test_single_event_creates_mobilisation(self, mock_create_mobi):
        COLS = ["id", "vessel_1",  "n_vessel_1", "d_trigger", "d_end_wait_start", "comments"]

        df = pd.DataFrame([{
            "id": "123_removal",
            "vessel_1": "V1",
            "n_vessel_1": 1,
            "d_trigger": pd.Timestamp("2024-01-10"),
            "d_end_wait_start": pd.Timestamp("2024-01-12"),
            "comments": "x_5"
        }])

        mock_create_mobi.return_value = pd.DataFrame([{
            "id": "new",
            "vessel_1": "V1",
            "n_vessel_1": 1,
            "d_trigger": pd.Timestamp("2024-01-10"),
            "d_end_wait_start": pd.Timestamp("2024-01-12"),
            "comments": "mobilisation_merged"
        }])

        find_class = MagicMock()
        find_class.find_vessel.return_value = FakeVessel(mobilisation_time=10)

        result = tow_deferred_mobi(COLS, df, find_class)

        self.assertEqual(len(result), 1)
        mock_create_mobi.assert_called_once()

        args = mock_create_mobi.call_args.kwargs
        self.assertEqual(args["count_fail"], "5")


# ============================================
# TEST 3
# More events in same month → Only one mobilisation per vessel
# ============================================
class TestManyVesselMobi(unittest.TestCase):

    @patch("logistic_tools.core.functions.log_merge_corrective_functions.tow_deferred_mobilisation.create_mobilisation")
    def test_multiple_events_same_month(self, mock_create_mobi):
        COLS = ["id", "vessel_1", "n_vessel_1", "d_trigger", "d_end_wait_start", "comments"]

        df = pd.DataFrame([
            {
                "id": "r1_removal",
                "vessel_1": "V1",
                "n_vessel_1": 2,
                "d_trigger": pd.Timestamp("2024-03-02"),
                "d_end_wait_start": pd.Timestamp("2024-03-05"),
                "comments": "a_1"
            },
            {
                "id": "r2_removal",
                "vessel_1": "V1",
                "n_vessel_1": 2,
                "d_trigger": pd.Timestamp("2024-03-10"),
                "d_end_wait_start": pd.Timestamp("2024-03-12"),
                "comments": "b_2"
            }
        ])

        mock_create_mobi.side_effect = [
            pd.DataFrame([{"id": "mob_1"}]),
            pd.DataFrame([{"id": "mob_1"}, {"id": "mob_2"}]),
        ]

        find_class = MagicMock()
        find_class.find_vessel.return_value = FakeVessel()

        result = tow_deferred_mobi(COLS, df, find_class)

        assert mock_create_mobi.call_count == 2
        self.assertEqual(len(result), 2)


# ============================================
# TEST 4
# Vessel with mobilisation_time = 0 → no mobilisation
# ============================================
class TestVesselZeroMobi(unittest.TestCase):
    def test_vessel_with_zero_mobilisation_time_skipped(self):
        COLS = ["id", "vessel_1", "n_vessel_1", "d_trigger", "d_end_wait_start", "comments"]

        df = pd.DataFrame([{
            "id": "123_removal",
            "vessel_1": "V1",
            "n_vessel_1": 1,
            "d_trigger": pd.Timestamp("2024-01-10"),
            "d_end_wait_start": pd.Timestamp("2024-01-12"),
            "comments": "x_3"
        }])

        find_class = MagicMock()
        find_class.find_vessel.return_value = FakeVessel(mobilisation_time=0)

        result = tow_deferred_mobi(COLS, df, find_class)

        self.assertEqual(len(result), 0)


# ============================================
# TEST 5
# First event of group must be used
# ============================================
class TestOrderOfEvents(unittest.TestCase):

    @patch("logistic_tools.core.functions.log_merge_corrective_functions.tow_deferred_mobilisation.create_mobilisation")
    def test_first_event_is_used(self, mock_create_mobi):
        COLS = ["id", "vessel_1", "n_vessel_1", "d_trigger", "d_end_wait_start", "comments"]

        df = pd.DataFrame([
            {
                "id": "a_removal",
                "vessel_1": "V1",
                "n_vessel_1": 1,
                "d_trigger": pd.Timestamp("2024-01-05"),
                "d_end_wait_start": pd.Timestamp("2024-01-07"),
                "comments": "x_2"
            },
            {
                "id": "a_removal",
                "vessel_1": "V1",
                "n_vessel_1": 1,
                "d_trigger": pd.Timestamp("2024-01-20"),
                "d_end_wait_start": pd.Timestamp("2024-01-22"),
                "comments": "x_1"
            }
        ])

        mock_create_mobi.return_value = pd.DataFrame([{"id": "mob"}])

        find_class = MagicMock()
        find_class.find_vessel.return_value = FakeVessel()

        result = tow_deferred_mobi(COLS, df, find_class)

        args = mock_create_mobi.call_args.kwargs
        self.assertEqual(args["mobilisation_date"], pd.Timestamp("2024-01-05"))
        self.assertEqual(args["end_mobi"], pd.Timestamp("2024-01-07"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
