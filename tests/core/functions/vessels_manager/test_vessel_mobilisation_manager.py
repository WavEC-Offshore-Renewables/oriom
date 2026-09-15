# test_vessel_mobilisation_manager

import unittest
import pandas as pd
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch, call, MagicMock

from oriom.core.functions.vessels_manager.vessel_mobilisation_manager import (
    create_yearly_mobilisation_mother_vessel,
    reduce_redundant_mobilisations_inspection,
    mobilitate_second_vessel
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

        
import oriom.core.functions.vessels_manager.vessel_mobilisation_manager as vessel_mobilisation_module

class TestMobilitateSecondVessel(unittest.TestCase):
    """Tests for mobilitate_second_vessel."""

    def setUp(self):
        """Create reusable test objects."""
        self.base_time = pd.Timestamp("2026-01-01 08:00:00")

        self.log_columns = [
            "d_trigger",
            "d_end_stat_chart",
            "event",
            "comments",
            "id",
            "vessel_1",
            "vessel_2",
            "n_vessel",
        ]

        self.log_events_df = pd.DataFrame(
            [
                {
                    "d_trigger": self.base_time,
                    "d_end_stat_chart": self.base_time + pd.Timedelta(hours=2),
                    "event": "mobilisation",
                    "comments": ["operation_1"],
                    "id": "mobi_123",
                    "vessel_1": "V1",
                    "vessel_2": None,
                    "n_vessel": 1,
                }
            ],
            columns=self.log_columns,
        )

        self.vessel_1 = SimpleNamespace(
            id="V1",
            mobilisation_cost=1000,
            mobilisation_time=5,
        )

        self.vessel_2 = SimpleNamespace(
            id="V2",
            mobilisation_cost=2000,
            mobilisation_time=3,
        )

        self.vessel_3 = SimpleNamespace(
            id="V3",
            mobilisation_cost=3000,
            mobilisation_time=4,
        )

        self.operation_1 = SimpleNamespace(
            id="operation_1",
            vessel2=self.vessel_2,
            vessel2_qt=1,
            op_class=SimpleNamespace(
                vessel1_id="V1",
                vessel2_id=None,
                addition_op_tow=None,
            ),
        )

        self.find_element = Mock()
        self.find_element.find_operation.return_value = self.operation_1

        self.operations_tow = {
            "pmain": [
                self.operation_1,
            ],
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fake_create_mobilisation(
        self,
        df,
        mobilisation_date,
        end_mobi,
        event,
        vessel,
        oper_list,
        count_fail,
        concat,
        n_vessel,
    ):
        """Return a valid mobilisation dataframe and support concat=True."""
        row = {
            "d_trigger": mobilisation_date,
            "d_end_stat_chart": None,
            "event": event,
            "comments": oper_list,
            "id": f"mobi_second_{count_fail}",
            "vessel_1": None,
            "vessel_2": vessel.id,
            "n_vessel": n_vessel,
        }

        row_df = pd.DataFrame(
            [row],
            columns=df.columns,
        )

        if concat:
            return pd.concat(
                [df, row_df],
                axis=0,
                ignore_index=False,
            )

        return row_df

    def _set_find_operation_mapping(self, operation_mapping):
        """Configure find_operation to return operations by id."""
        def fake_find_operation(operation_id):
            return operation_mapping[operation_id]

        self.find_element.find_operation.side_effect = fake_find_operation

    def _make_log_row(
        self,
        event,
        operation_id,
        mobilisation_id,
        offset_hours=0,
    ):
        """Create one log event row."""
        trigger = self.base_time + pd.Timedelta(hours=offset_hours)

        return {
            "d_trigger": trigger,
            "d_end_stat_chart": trigger + pd.Timedelta(hours=2),
            "event": event,
            "comments": [operation_id],
            "id": mobilisation_id,
            "vessel_1": "V1",
            "vessel_2": None,
            "n_vessel": 1,
        }

    @staticmethod
    def _second_vessel_rows(result):
        """Return rows generated for second-vessel mobilisation."""
        return result[
            (result["event"] == "mobilisation")
            & result["vessel_2"].notna()
        ]

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    @patch.object(vessel_mobilisation_module, "create_mobilisation")
    def test_mobilitate_second_vessel_appends_second_vessel_row(
        self,
        mock_create_mobilisation,
    ):
        """A mobilisation row should be appended for operation vessel_2."""
        mock_create_mobilisation.side_effect = self._fake_create_mobilisation

        result = mobilitate_second_vessel(
            log_events_merged=self.log_events_df,
            find_element_class=self.find_element,
            operations_tow=self.operations_tow,
        )

        self.assertEqual(len(result), 2)

        second_vessel_rows = self._second_vessel_rows(result)

        self.assertEqual(len(second_vessel_rows), 1)
        self.assertEqual(second_vessel_rows.iloc[0]["vessel_2"], "V2")
        self.assertEqual(second_vessel_rows.iloc[0]["n_vessel"], 1)

        self.assertEqual(
            second_vessel_rows.iloc[0]["d_end_stat_chart"],
            self.log_events_df.iloc[0]["d_end_stat_chart"],
        )

        mock_create_mobilisation.assert_called_once()

        kwargs = mock_create_mobilisation.call_args.kwargs

        self.assertEqual(
            kwargs["mobilisation_date"],
            pd.Timestamp("2026-01-01 08:00:00"),
        )
        self.assertEqual(
            kwargs["end_mobi"],
            pd.Timestamp("2026-01-01 11:00:00"),
        )
        self.assertEqual(kwargs["event"], "mobilisation")
        self.assertEqual(kwargs["oper_list"], ["operation_1"])
        self.assertEqual(kwargs["count_fail"], "123")
        self.assertTrue(kwargs["concat"])
        self.assertEqual(kwargs["n_vessel"], 1)
        self.assertIs(kwargs["vessel"], self.vessel_2)

    @patch.object(vessel_mobilisation_module, "create_mobilisation")
    def test_mobilisation_merged_is_processed(
        self,
        mock_create_mobilisation,
    ):
        """mobilisation_merged rows should also create second-vessel mobilisation."""
        df = self.log_events_df.copy()
        df.loc[0, "event"] = "mobilisation_merged"

        mock_create_mobilisation.side_effect = self._fake_create_mobilisation

        result = mobilitate_second_vessel(
            log_events_merged=df,
            find_element_class=self.find_element,
            operations_tow=self.operations_tow,
        )

        self.assertEqual(len(result), 2)
        mock_create_mobilisation.assert_called_once()

        second_vessel_rows = self._second_vessel_rows(result)

        self.assertEqual(len(second_vessel_rows), 1)
        self.assertEqual(second_vessel_rows.iloc[0]["vessel_2"], "V2")

    @patch.object(vessel_mobilisation_module, "create_mobilisation")
    def test_only_mobilisation_events_are_processed(
        self,
        mock_create_mobilisation,
    ):
        """Rows that are not mobilisation or mobilisation_merged should be ignored."""
        df = pd.DataFrame(
            [
                self._make_log_row(
                    event="mobilisation",
                    operation_id="operation_1",
                    mobilisation_id="mobi_123",
                    offset_hours=0,
                ),
                self._make_log_row(
                    event="failure",
                    operation_id="operation_1",
                    mobilisation_id="failure_001",
                    offset_hours=1,
                ),
            ],
            columns=self.log_columns,
        )

        mock_create_mobilisation.side_effect = self._fake_create_mobilisation

        result = mobilitate_second_vessel(
            log_events_merged=df,
            find_element_class=self.find_element,
            operations_tow=self.operations_tow,
        )

        self.assertEqual(len(result), 3)
        mock_create_mobilisation.assert_called_once()
        self.find_element.find_operation.assert_called_once_with("operation_1")

    @patch.object(vessel_mobilisation_module, "create_mobilisation")
    def test_no_vessel2_does_not_append_row(
        self,
        mock_create_mobilisation,
    ):
        """Operations without vessel_2 should not create second-vessel mobilisation."""
        self.operation_1.vessel2 = None
        self.operation_1.vessel2_qt = 0

        mock_create_mobilisation.side_effect = self._fake_create_mobilisation

        result = mobilitate_second_vessel(
            log_events_merged=self.log_events_df,
            find_element_class=self.find_element,
            operations_tow=self.operations_tow,
        )

        self.assertEqual(len(result), 1)
        mock_create_mobilisation.assert_not_called()

    @patch.object(vessel_mobilisation_module, "create_mobilisation")
    def test_vessel2_without_mobilisation_cost_does_not_append_row(
        self,
        mock_create_mobilisation,
    ):
        """A vessel_2 without mobilisation cost should not be mobilised."""
        self.vessel_2.mobilisation_cost = None

        mock_create_mobilisation.side_effect = self._fake_create_mobilisation

        result = mobilitate_second_vessel(
            log_events_merged=self.log_events_df,
            find_element_class=self.find_element,
            operations_tow=self.operations_tow,
        )

        self.assertEqual(len(result), 1)
        mock_create_mobilisation.assert_not_called()

    @patch.object(vessel_mobilisation_module, "create_mobilisation")
    def test_vessel2_with_zero_mobilisation_cost_does_not_append_row(
        self,
        mock_create_mobilisation,
    ):
        """A vessel_2 with zero mobilisation cost should not be mobilised."""
        self.vessel_2.mobilisation_cost = 0

        mock_create_mobilisation.side_effect = self._fake_create_mobilisation

        result = mobilitate_second_vessel(
            log_events_merged=self.log_events_df,
            find_element_class=self.find_element,
            operations_tow=self.operations_tow,
        )

        self.assertEqual(len(result), 1)
        mock_create_mobilisation.assert_not_called()

    @patch.object(vessel_mobilisation_module, "create_mobilisation")
    def test_vessel2_quantity_is_passed_to_create_mobilisation(
        self,
        mock_create_mobilisation,
    ):
        """The vessel2_qt value should be passed to create_mobilisation."""
        self.operation_1.vessel2_qt = 3

        mock_create_mobilisation.side_effect = self._fake_create_mobilisation

        result = mobilitate_second_vessel(
            log_events_merged=self.log_events_df,
            find_element_class=self.find_element,
            operations_tow=self.operations_tow,
        )

        self.assertEqual(len(result), 2)

        kwargs = mock_create_mobilisation.call_args.kwargs

        self.assertEqual(kwargs["n_vessel"], 3)

        second_vessel_rows = self._second_vessel_rows(result)

        self.assertEqual(second_vessel_rows.iloc[0]["n_vessel"], 3)

    @patch.object(vessel_mobilisation_module, "create_mobilisation")
    def test_operation_id_is_read_from_comments(
        self,
        mock_create_mobilisation,
    ):
        """The operation id should be obtained from row comments[0]."""
        mock_create_mobilisation.side_effect = self._fake_create_mobilisation

        mobilitate_second_vessel(
            log_events_merged=self.log_events_df,
            find_element_class=self.find_element,
            operations_tow=self.operations_tow,
        )

        self.find_element.find_operation.assert_called_once_with("operation_1")

    @patch.object(vessel_mobilisation_module, "create_mobilisation")
    def test_count_fail_removes_mobi_prefix(
        self,
        mock_create_mobilisation,
    ):
        """The count_fail argument should remove the mobi_ prefix from the mobilisation id."""
        mock_create_mobilisation.side_effect = self._fake_create_mobilisation

        mobilitate_second_vessel(
            log_events_merged=self.log_events_df,
            find_element_class=self.find_element,
            operations_tow=self.operations_tow,
        )

        kwargs = mock_create_mobilisation.call_args.kwargs

        self.assertEqual(kwargs["count_fail"], "123")

    @patch.object(vessel_mobilisation_module, "create_mobilisation")
    def test_additional_operation_is_skipped_when_vessel2_is_already_in_towing_vessels(
        self,
        mock_create_mobilisation,
    ):
        """
        Additional operation should be skipped when its vessel2_id is already used
        by a towing operation vessel_1 or vessel_2.
        """
        additional_operation_reference = SimpleNamespace(
            id="additional_operation",
            vessel2_id="V1",
        )

        self.operation_1.op_class.addition_op_tow = additional_operation_reference

        additional_operation = SimpleNamespace(
            id="additional_operation",
            vessel2=self.vessel_2,
            vessel2_qt=1,
            op_class=SimpleNamespace(
                vessel1_id="V_ADD",
                vessel2_id="V1",
                addition_op_tow=None,
            ),
        )

        self._set_find_operation_mapping(
            {
                "additional_operation": additional_operation,
            }
        )

        df = pd.DataFrame(
            [
                self._make_log_row(
                    event="mobilisation",
                    operation_id="additional_operation",
                    mobilisation_id="mobi_456",
                    offset_hours=0,
                )
            ],
            columns=self.log_columns,
        )

        mock_create_mobilisation.side_effect = self._fake_create_mobilisation

        result = mobilitate_second_vessel(
            log_events_merged=df,
            find_element_class=self.find_element,
            operations_tow=self.operations_tow,
        )

        self.assertEqual(len(result), 1)
        mock_create_mobilisation.assert_not_called()

    @patch.object(vessel_mobilisation_module, "create_mobilisation")
    def test_additional_operation_is_not_skipped_when_vessel2_is_not_in_towing_vessels(
        self,
        mock_create_mobilisation,
    ):
        """
        Additional operation should be processed when its vessel2_id is not already
        used by the main towing operation.
        """
        additional_operation_reference = SimpleNamespace(
            id="additional_operation",
            vessel2_id="V3",
        )

        self.operation_1.op_class.addition_op_tow = additional_operation_reference

        additional_operation = SimpleNamespace(
            id="additional_operation",
            vessel2=self.vessel_3,
            vessel2_qt=2,
            op_class=SimpleNamespace(
                vessel1_id="V_ADD",
                vessel2_id="V3",
                addition_op_tow=None,
            ),
        )

        self._set_find_operation_mapping(
            {
                "additional_operation": additional_operation,
            }
        )

        df = pd.DataFrame(
            [
                self._make_log_row(
                    event="mobilisation",
                    operation_id="additional_operation",
                    mobilisation_id="mobi_456",
                    offset_hours=0,
                )
            ],
            columns=self.log_columns,
        )

        mock_create_mobilisation.side_effect = self._fake_create_mobilisation

        result = mobilitate_second_vessel(
            log_events_merged=df,
            find_element_class=self.find_element,
            operations_tow=self.operations_tow,
        )

        self.assertEqual(len(result), 2)

        mock_create_mobilisation.assert_called_once()

        kwargs = mock_create_mobilisation.call_args.kwargs

        self.assertIs(kwargs["vessel"], self.vessel_3)
        self.assertEqual(kwargs["n_vessel"], 2)

    @patch.object(vessel_mobilisation_module, "create_mobilisation")
    def test_vessel2_id_from_operation_class_is_in_towing_vessel_list(
        self,
        mock_create_mobilisation,
    ):
        """
        operation.op_class.vessel2_id should also be considered part of the main
        towing vessel list used to skip additional operation vessel_2.
        """
        self.operation_1.op_class.vessel2_id = "V2"

        additional_operation_reference = SimpleNamespace(
            id="additional_operation",
            vessel2_id="V2",
        )

        self.operation_1.op_class.addition_op_tow = additional_operation_reference

        additional_operation = SimpleNamespace(
            id="additional_operation",
            vessel2=self.vessel_2,
            vessel2_qt=1,
            op_class=SimpleNamespace(
                vessel1_id="V_ADD",
                vessel2_id="V2",
                addition_op_tow=None,
            ),
        )

        self._set_find_operation_mapping(
            {
                "additional_operation": additional_operation,
            }
        )

        df = pd.DataFrame(
            [
                self._make_log_row(
                    event="mobilisation",
                    operation_id="additional_operation",
                    mobilisation_id="mobi_789",
                    offset_hours=0,
                )
            ],
            columns=self.log_columns,
        )

        mock_create_mobilisation.side_effect = self._fake_create_mobilisation

        result = mobilitate_second_vessel(
            log_events_merged=df,
            find_element_class=self.find_element,
            operations_tow=self.operations_tow,
        )

        self.assertEqual(len(result), 1)
        mock_create_mobilisation.assert_not_called()

    @patch.object(vessel_mobilisation_module, "create_mobilisation")
    def test_multiple_mobilisation_rows_create_multiple_second_vessel_rows(
        self,
        mock_create_mobilisation,
    ):
        """Several mobilisation rows should create several second-vessel mobilisation rows."""
        operation_2 = SimpleNamespace(
            id="operation_2",
            vessel2=self.vessel_3,
            vessel2_qt=2,
            op_class=SimpleNamespace(
                vessel1_id="V1",
                vessel2_id=None,
                addition_op_tow=None,
            ),
        )

        self._set_find_operation_mapping(
            {
                "operation_1": self.operation_1,
                "operation_2": operation_2,
            }
        )

        df = pd.DataFrame(
            [
                self._make_log_row(
                    event="mobilisation",
                    operation_id="operation_1",
                    mobilisation_id="mobi_123",
                    offset_hours=0,
                ),
                self._make_log_row(
                    event="mobilisation_merged",
                    operation_id="operation_2",
                    mobilisation_id="mobi_456",
                    offset_hours=4,
                ),
            ],
            columns=self.log_columns,
        )

        mock_create_mobilisation.side_effect = self._fake_create_mobilisation

        result = mobilitate_second_vessel(
            log_events_merged=df,
            find_element_class=self.find_element,
            operations_tow=self.operations_tow,
        )

        self.assertEqual(len(result), 4)

        second_vessel_rows = self._second_vessel_rows(result)

        self.assertEqual(len(second_vessel_rows), 2)
        self.assertEqual(second_vessel_rows.iloc[0]["vessel_2"], "V2")
        self.assertEqual(second_vessel_rows.iloc[0]["n_vessel"], 1)
        self.assertEqual(second_vessel_rows.iloc[1]["vessel_2"], "V3")
        self.assertEqual(second_vessel_rows.iloc[1]["n_vessel"], 2)

        self.assertEqual(mock_create_mobilisation.call_count, 2)

        self.find_element.find_operation.assert_has_calls(
            [
                call("operation_1"),
                call("operation_2"),
            ]
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)