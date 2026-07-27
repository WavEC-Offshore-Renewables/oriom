# test_vessel_mobilisation_manager

import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime, timedelta

from oriom.core.functions.vessels_manager.vessel_mobilisation_manager import (
    create_yearly_mobilisation_mother_vessel,
    reduce_redundant_mobilisations_inspection,
)


class TestCreateYearlyMobilisationMotherVessel(unittest.TestCase):

    @patch("oriom.core.functions.vessels_manager.vessel_mobilisation_manager.create_mobilisation")
    @patch("oriom.core.functions.vessels_manager.vessel_mobilisation_manager.get_first_failure")
    def test_create_yearly_mobilisation_single_year(
        self, mock_get_first_failure, mock_create_mobilisation
    ):
        """
        Test mobilisation creation for a mother vessel used in a single year.
        Validates that one mobilisation is added and external functions are called correctly.
        """

        # Fake returned failure ID
        mock_get_first_failure.return_value = "fail_001"

        # Fake create_mobilisation returns new rows appended
        mock_create_mobilisation.side_effect = lambda **kwargs: kwargs["df"].append(
            {
                "event": "mobilisation",
                "vessel_1": kwargs["vessel"].id,
                "d_trigger": kwargs["end_mobi"],
                "id": kwargs["oper_list"],
                "comments": f"mobi_{kwargs['count_fail']}",
            },
            ignore_index=True,
        )

        # Input DataFrame: 1 event for one mother vessel in 2025
        df = pd.DataFrame(
            {
                "id": ["OP_001"],
                "vessel_1": ["SOV1"],
                "n_vessel_1": [1],
                "vessel_2": [None],
                "n_vessel_2": [1],
                "d_trigger": [datetime(2025, 3, 15, 10, 0, 0)],
                "d_end_wait_start": [datetime(2025, 4, 15, 10, 0, 0)],
                "comments": ["failure_fail_001"],
                "event": ["inspection_site"],
            }
        )

        mv = MagicMock()
        mv.id = "SOV1"
        mv.mobilisation_time = 12  # hours

        out = create_yearly_mobilisation_mother_vessel(
            log_events_merged=df,
            mother_vessel_list=[mv],
        )

        # Expected: original + 1 mobilisation
        self.assertEqual(len(out), 2)

        # Check mobilisation row exists
        mobi_rows = out[out["event"] == "mobilisation"]
        self.assertEqual(len(mobi_rows), 1)

        # Ensure get_first_failure was called
        mock_get_first_failure.assert_called_once()


class TestReduceRedundantMobilisationsInspection(unittest.TestCase):

    @patch("oriom.core.functions.vessels_manager.vessel_mobilisation_manager.safe_copy_df")
    def test_reduce_redundant_same_month(self, mock_safe_copy):
        """
        If two inspections occur in the same month for the same vessel,
        mobilisations for all but the first should be removed.
        """

        # Construct fake DataFrame
        df = pd.DataFrame(
            {
                "id": ["insp_1", "insp_2", "mobi_insp_1", "mobi_insp_2"],
                "event": ["inspection_site", "inspection_site", "mobilisation", "mobilisation"],
                "vessel_1": ["V1", "V1", "V1", "V1"],
                "comments": ["c1", "c2", "c3", "c4"],
                "d_trigger": [
                    datetime(2025, 4, 5),
                    datetime(2025, 4, 12),
                    datetime(2025, 4, 5) - timedelta(hours=10),
                    datetime(2025, 4, 12) - timedelta(hours=10),
                ],
            }
        )

        # safe_copy_df should return a deep copy of df
        mock_safe_copy.return_value = df.copy()

        # Vessel mock
        vessel = MagicMock()
        vessel.id = "V1"
        vessel.mobilisation_time = 5

        # Run function
        out = reduce_redundant_mobilisations_inspection(
            log_events_merged=df.copy(),
            vessels=[vessel],
        )

        # Only one mobilisation should remain
        remaining_mobi = out[out["event"] == "mobilisation"]
        self.assertEqual(len(remaining_mobi), 1)


    @patch("oriom.core.functions.vessels_manager.vessel_mobilisation_manager.safe_copy_df")
    def test_reduce_redundant_no_reduction_if_single_inspection(self, mock_safe_copy):
        """
        If there is only one inspection in a period, no mobilisation is removed.
        """

        df = pd.DataFrame(
            {
                "id": ["insp_1", "mobi_1"],
                "event": ["inspection_site", "mobilisation"],
                "vessel_1": ["V1", "V1"],
                "comments": ["c1", "c2"],
                "d_trigger": [datetime(2025, 5, 10), datetime(2025, 5, 10) - timedelta(hours=10)],
            }
        )

        mock_safe_copy.return_value = df.copy()

        vessel = MagicMock()
        vessel.id = "V1"
        vessel.mobilisation_time = 5

        out = reduce_redundant_mobilisations_inspection(
            log_events_merged=df.copy(),
            vessels=[vessel],
        )

        # No mobilisation should be removed
        self.assertEqual(len(out), len(df))

    @patch("oriom.core.functions.vessels_manager.vessel_mobilisation_manager.safe_copy_df")
    def test_reduce_redundant_vessel_with_zero_mobilisation_time(self, mock_safe_copy):
        """
        If vessel.mobilisation_time == 0, mobilisations must not be removed.
        """

        df = pd.DataFrame(
            {
                "id": ["insp_1", "insp_2", "mobi_1", "mobi_2"],
                "event": ["inspection_site", "inspection_site", "mobilisation", "mobilisation"],
                "vessel_1": ["V1", "V1", "V1", "V1"],
                "comments": ["c1", "c2", "c3", "c4"],
                "d_trigger": [
                    datetime(2025, 4, 5),
                    datetime(2025, 4, 12),
                    datetime(2025, 4, 5),
                    datetime(2025, 4, 12),
                ],
            }
        )

        mock_safe_copy.return_value = df.copy()

        vessel = MagicMock()
        vessel.id = "V1"
        vessel.mobilisation_time = 0

        out = reduce_redundant_mobilisations_inspection(
            log_events_merged=df.copy(),
            vessels=[vessel],
        )

        # Nothing should be removed when mobilisation_time == 0
        self.assertEqual(len(out), len(df))


if __name__ == "__main__":
    unittest.main()
