import unittest
import os
from datetime import datetime
import pandas as pd
import numpy as np

from oriom.core.functions.logs_timeseries.failures import failures_event, find_month_available, ST_failures_event
from oriom.domain.Failure import Failure
from oriom.domain.Scenario import Scenario


class TestFailures(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        file_failures = os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'failures.yaml')
        file_scenarios = os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'scenarios.yaml')

        scenarios = Scenario.get_scenarios_from_yaml(file_scenarios)
        failrates = Failure.get_failures_from_yaml(file_failures)

        # NOTE: The current failures_event signature has an extra argument (optional dates_failures_OLD),
        # but this historical usage remains valid.
        self.dates_failures = failures_event(1, scenarios, failrates, 20, 2022, 7, 1, 2, 3, False)

    def test_countfailures(self):
        self.fail001 = self.dates_failures[self.dates_failures['id'] == 'ofw_fail_001']
        self.fail002 = self.dates_failures[self.dates_failures['id'] == 'owc_fail_002']
        self.fail003 = self.dates_failures[self.dates_failures['id'] == 'ofw_fail_003']
        self.fail004 = self.dates_failures[self.dates_failures['id'] == 'oce_fail_004']
        self.assertEqual(self.fail001['datetime'].count(), 180)
        self.assertEqual(self.fail002['datetime'].count(), 10)
        self.assertEqual(self.fail003['datetime'].count(), 4)
        self.assertEqual(self.fail004['datetime'].count(), 2)
        self.assertEqual(self.dates_failures['id'].count(), 196)


# ---------------------- New unit tests for failures_event ---------------------- #

class DummyScenario:
    """Minimal scenario with only percentage_month list (12 values)."""
    def __init__(self, percentages):
        self.percentage_month = percentages


class DummyFailureSmall:
    """Failure minimale con gli attributi usati da failures_event."""
    def __init__(
        self,
        id_,
        fail_rate,
        n_element,
        bath_tub,
        maintenance_strategy="immediately",
        operation_triggered="op_dummy",
        preferred_month=None,
        avoid_month_correction = []
    ):
        self.id = id_
        self.fail_rate = fail_rate
        self.n_element = n_element
        self.bath_tub = bath_tub
        self.maintenance_strategy = maintenance_strategy
        self.operation_triggered = operation_triggered
        self.preferred_month = preferred_month
        self.avoid_month_correction = avoid_month_correction


class TestFailuresEventUnit(unittest.TestCase):
    """Targeted tests on the behavior of failures_event with minimal and controlled inputs."""

    def test_no_failures_returns_empty_df(self):
        """If the 'failures' list is empty, the resulting DataFrame must be empty."""
        scenarios = [DummyScenario([1.0 / 12.0] * 12)]

        df = failures_event(
            s=0,
            scenarios=scenarios,
            failures=[],
            N_LIFETIME=5,
            START_YEAR=2020,
            START_MONTH=1,
            infant_mortality=0,
            wear_out=0,
            fail_ratio=1.0,
            fixed_seed=True,
        )

        self.assertTrue(df.empty)
        self.assertListEqual(
            list(df.columns),
            ["datetime", "id", "maintenance_strategy", "operation_triggered", "preferred_month"],
        )

    def test_fixed_seed_reproducible(self):
        """
        With fixed_seed=True and deterministic parameters (no Poisson),
        two calls with the same inputs must return the same DataFrame.
        """
        scenarios = [DummyScenario([1.0 / 12.0] * 12)]
        # fail_rate * N_LIFETIME * n_element = 0.5 * 2 * 10 = 10 >= 1 → no Poisson
        failures = [
            DummyFailureSmall(
                id_="compX",
                fail_rate=0.5,
                n_element=10,
                bath_tub=False,
                maintenance_strategy="immediately",
                operation_triggered="op_compX",
            )
        ]

        kwargs = dict(
            s=0,
            scenarios=scenarios,
            failures=failures,
            N_LIFETIME=2,
            START_YEAR=2020,
            START_MONTH=1,
            infant_mortality=0,
            wear_out=0,
            fail_ratio=1.0,
            fixed_seed=True,
        )

        df1 = failures_event(**kwargs)
        df2 = failures_event(**kwargs)

        self.assertFalse(df1.empty)
        self.assertTrue(df1.equals(df2))

    def test_previous_file_is_reused(self):
        """
        If dates_failures_OLD is passed, its rows must be reused
        """
        scenarios = [DummyScenario([1.0 / 12.0] * 12)]

        failures = [
            DummyFailureSmall(
                id_="comp1",
                fail_rate=0.0,
                n_element=1,
                bath_tub=False,
                maintenance_strategy="immediately",
                operation_triggered="op_c1",
                preferred_month=3,
            ),
            DummyFailureSmall(
                id_="comp2",
                fail_rate=0.0,
                n_element=1,
                bath_tub=False,
                maintenance_strategy="specific month",
                operation_triggered="op_c2",
                preferred_month=5,
            ),
        ]

        # Old file
        old_df = pd.DataFrame(
            [
                {
                    "datetime": datetime(2025, 1, 2, 0, 0),
                    "id": "comp2",
                    "maintenance_strategy": "specific month",
                    "operation_triggered": "op_c2",
                    "preferred_month": 5
                },
                {
                    "datetime": datetime(2025, 1, 1, 0, 0),
                    "id": "comp1",
                    "maintenance_strategy": "immediately",
                    "operation_triggered": "op_c1",
                    "preferred_month": np.nan
                }
            ]
        )

        df = failures_event(
            s=0,
            scenarios=scenarios,
            failures=failures,
            N_LIFETIME=5,
            START_YEAR=2020,
            START_MONTH=1,
            infant_mortality=0,
            wear_out=0,
            fail_ratio=1.0,
            fixed_seed=True,
            dates_failures_OLD=old_df,
        )

        self.assertEqual(len(df), 2)
        self.assertSetEqual(set(df["id"]), {"comp1", "comp2"})
        # The extra column values ​​must come from DummyFailureSmall
        row1 = df[df["id"] == "comp1"].iloc[0]
        row2 = df[df["id"] == "comp2"].iloc[0]

        self.assertEqual(row1["maintenance_strategy"], "immediately")
        self.assertEqual(row1["operation_triggered"], "op_c1")
        self.assertTrue(np.isnan(row1["preferred_month"]))

        self.assertEqual(row2["maintenance_strategy"], "specific month")
        self.assertEqual(row2["operation_triggered"], "op_c2")
        self.assertEqual(row2["preferred_month"], 5)


    def test_previous_file_is_invalid(self):
        """
        If dates_failures_OLD is passed, its rows must be reused
        """
        scenarios = [DummyScenario([1.0 / 12.0] * 12)]

        failures = [
            DummyFailureSmall(
                id_="comp1",
                fail_rate=0.0,
                n_element=1,
                bath_tub=False,
                maintenance_strategy="immediately",
                operation_triggered="op_c1",
                preferred_month=3,
            ),
            DummyFailureSmall(
                id_="comp2",
                fail_rate=0.0,
                n_element=1,
                bath_tub=False,
                maintenance_strategy="specific month",
                operation_triggered="op_c2",
                preferred_month=5,
            ),
        ]

        # Old file
        old_df = pd.DataFrame({"id": ["comp1"]})

        with self.assertRaises(FileNotFoundError):
            df = failures_event(
                s=0,
                scenarios=scenarios,
                failures=failures,
                N_LIFETIME=5,
                START_YEAR=2020,
                START_MONTH=1,
                infant_mortality=0,
                wear_out=0,
                fail_ratio=1.0,
                fixed_seed=True,
                dates_failures_OLD=old_df,
            )

            self.assertEqual(len(df), 2)


    def test_previous_file_with_unknown_failure(self):
        """
        If dates_failures_OLD is passed, its rows must be reused
        """
        scenarios = [DummyScenario([1.0 / 12.0] * 12)]

        failures = [
            DummyFailureSmall(
                id_="comp1",
                fail_rate=0.0,
                n_element=1,
                bath_tub=False,
                maintenance_strategy="immediately",
                operation_triggered="op_c1",
                preferred_month=3,
            )
        ]

        # Old file
        old_df = pd.DataFrame(
            [
                {
                    "datetime": datetime(2025, 1, 2, 0, 0),
                    "id": "comp2",
                    "maintenance_strategy": "specific month",
                    "operation_triggered": "op_c2",
                    "preferred_month": 5
                },
                {
                    "datetime": datetime(2025, 1, 1, 0, 0),
                    "id": "comp1",
                    "maintenance_strategy": "immediately",
                    "operation_triggered": "op_c1",
                    "preferred_month": np.nan
                }
            ]
        )

        with self.assertRaises(KeyError):
            df = failures_event(
                s=0,
                scenarios=scenarios,
                failures=failures,
                N_LIFETIME=5,
                START_YEAR=2020,
                START_MONTH=1,
                infant_mortality=0,
                wear_out=0,
                fail_ratio=1.0,
                fixed_seed=True,
                dates_failures_OLD=old_df,
            )

            self.assertEqual(len(df), 2)

    def test_bath_tub_changes_distribution(self):
        """
        With the same fail_rate and n_element, but bath_tub True/False,
        the distribution of failure years must be different
        (different probabilities for start/end years).
        """
        scenarios = [DummyScenario([1.0 / 12.0] * 12)]

        # fail_rate * N_LIFETIME * n_element = 0.8 * 4 * 10 = 32 events each
        bat_failure = DummyFailureSmall(
            id_="bat",
            fail_rate=0.8,
            n_element=10,
            bath_tub=True,
            maintenance_strategy="immediately",
            operation_triggered="op_bat",
        )
        norm_failure = DummyFailureSmall(
            id_="norm",
            fail_rate=0.8,
            n_element=10,
            bath_tub=False,
            maintenance_strategy="immediately",
            operation_triggered="op_norm",
        )

        df_bat = failures_event(
            s=0,
            scenarios=scenarios,
            failures=[bat_failure],
            N_LIFETIME=4,
            START_YEAR=2020,
            START_MONTH=1,
            infant_mortality=1,
            wear_out=1,
            fail_ratio=3.0,
            fixed_seed=True,
        )

        df_norm = failures_event(
            s=0,
            scenarios=scenarios,
            failures=[norm_failure],
            N_LIFETIME=4,
            START_YEAR=2020,
            START_MONTH=1,
            infant_mortality=1,
            wear_out=1,
            fail_ratio=3.0,
            fixed_seed=True,
        )


        # Base Verify: events for both failures
        self.assertGreater(len(df_bat), 0)
        self.assertGreater(len(df_norm), 0)

        years_bat = df_bat["datetime"].dt.year.value_counts(normalize=True).sort_index()
        years_norm = df_norm["datetime"].dt.year.value_counts(normalize=True).sort_index()
        self.assertFalse(years_bat.equals(years_norm))

    def test_avoid_month_correction(self):
        """
        Create one failure in a forbidden month to operate.
        """
        scenarios = [DummyScenario([1,0,0,0,0,0,0,0,0,0,0,0])]
        failures = [
            DummyFailureSmall(
                id_="compX",
                fail_rate=1,
                n_element=1,
                bath_tub=False,
                maintenance_strategy="immediately",
                operation_triggered="op_compX",
                avoid_month_correction=[1]
            )
        ]

        kwargs = dict(
            s=0,
            scenarios=scenarios,
            failures=failures,
            N_LIFETIME=1,
            START_YEAR=2020,
            START_MONTH=1,
            infant_mortality=0,
            wear_out=0,
            fail_ratio=1.0,
            fixed_seed=True,
        )

        df1 = failures_event(**kwargs)

        self.assertFalse(df1.empty)
        self.assertEqual(df1['maintenance_strategy'].iloc[0], 'specific month')
        self.assertEqual(df1['preferred_month'].iloc[0], 2)


class TestFindMonthAvailable(unittest.TestCase):
    """Targeted tests on finding month available"""

    def test_find_month_available_one_month(self):
        month = find_month_available(
            month_check = 1, 
            dict_failures_variables_id = [1]
        )
        self.assertEqual(month,2)

    def test_find_month_available_more_months(self):
        month = find_month_available(
            month_check = 1, 
            dict_failures_variables_id = [1,2]
        )
        self.assertEqual(month,3)

    def test_find_month_available_more_months_december(self):
        month = find_month_available(
            month_check = 12, 
            dict_failures_variables_id = [12,1]
        )
        self.assertEqual(month,2)

    def test_find_month_available_all_month(self):
        self.assertRaises(
            ValueError,
            find_month_available,
            month_check=12,
            dict_failures_variables_id=list(range(1, 13))
        )




# =============================================================================
# Short-term failures event tests
# =============================================================================

class DummyShortTermFailure:
    """Minimal failure double exposing the fields used by ST_failures_event."""

    def __init__(
        self,
        failure_id,
        fail_rate,
        operation_triggered="op_repair",
        maintenance_strategy="immediately",
        n_element=1,
    ):
        self.id = failure_id
        self.fail_rate = fail_rate
        self.operation_triggered = operation_triggered
        self.maintenance_strategy = maintenance_strategy
        self.n_element = n_element


class TestShortTermFailuresEvent(unittest.TestCase):
    """Regression tests for deterministic short-term failure generation."""

    COLUMNS = [
        "datetime",
        "id",
        "maintenance_strategy",
        "operation_triggered",
        "preferred_month",
    ]
    RUN_DATE = datetime(2026, 11, 2, 10, 6, 9)

    def _generate(self, failures, date_use=None, result_dir_r="unused_result_dir"):
        """Call the real ST generator with controlled input objects."""
        return ST_failures_event(
            failures=failures,
            date_use=self.RUN_DATE if date_use is None else date_use,
        )

    def test_empty_failure_list_returns_empty_dataframe_with_expected_columns(self):
        """No configured failures must produce an empty table with the full schema."""
        result = self._generate([])

        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)
        self.assertEqual(result.columns.tolist(), self.COLUMNS)
        self.assertEqual(len(result.index), 0)

    def test_zero_failure_rates_produce_no_events(self):
        """Failure types with zero rate contribute no short-term events."""
        result = self._generate([
            DummyShortTermFailure("fail_a", 0.0),
            DummyShortTermFailure("fail_b", 0),
        ])

        self.assertTrue(result.empty)
        self.assertEqual(result.columns.tolist(), self.COLUMNS)

    def test_each_failure_rate_is_rounded_up_independently(self):
        """The count for each failure type is ceil(fail_rate), not round or floor."""
        cases = [
            ("zero", 0.0, 0),
            ("tiny", 0.00001, 1),
            ("half", 0.5, 1),
            ("exact_one", 1.0, 1),
            ("above_one", 1.00001, 2),
            ("two", 2.0, 2),
            ("two_point_two", 2.2, 3),
        ]

        failures = [DummyShortTermFailure(name, rate) for name, rate, _ in cases]
        result = self._generate(failures)
        actual = result["id"].value_counts().to_dict()

        self.assertEqual(len(result), sum(expected for _, _, expected in cases))
        for name, rate, expected in cases:
            with self.subTest(failure_id=name, fail_rate=rate):
                self.assertEqual(actual.get(name, 0), expected)

    def test_does_not_multiply_failure_rate_by_number_of_devices(self):
        """The current ST implementation uses ceil(fail_rate), without n_element."""
        failure = DummyShortTermFailure(
            failure_id="large_array",
            fail_rate=0.75,
            n_element=1000,
        )

        result = self._generate([failure])

        self.assertEqual(len(result), 1)
        self.assertEqual(result["id"].tolist(), ["large_array"])

    def test_each_row_preserves_failure_metadata(self):
        """Repeated rows must retain their source failure's operation and strategy."""
        failures = [
            DummyShortTermFailure(
                "dynamic_cable",
                1.2,
                operation_triggered="repair_cable",
                maintenance_strategy="specific month",
            ),
            DummyShortTermFailure(
                "wtg_pitch",
                2.1,
                operation_triggered="repair_pitch",
                maintenance_strategy="immediately",
            ),
        ]

        result = self._generate(failures)
        expected = {
            "dynamic_cable": (2, "repair_cable", "specific month"),
            "wtg_pitch": (3, "repair_pitch", "immediately"),
        }

        self.assertEqual(result.columns.tolist(), self.COLUMNS)
        self.assertEqual(len(result), 5)
        for failure_id, (count, operation_id, strategy) in expected.items():
            with self.subTest(failure_id=failure_id):
                rows = result.loc[result["id"] == failure_id]
                self.assertEqual(len(rows), count)
                self.assertEqual(set(rows["operation_triggered"]), {operation_id})
                self.assertEqual(set(rows["maintenance_strategy"]), {strategy})

    def test_all_events_use_the_supplied_timestamp_and_month(self):
        """Every event is generated at date_use with the original string format."""
        failure = DummyShortTermFailure("failure_1", 3.0)
        test_dates = [
            datetime(2026, 11, 2, 10, 6, 9),
            datetime(2027, 1, 1, 0, 0, 0),
            datetime(2028, 2, 29, 23, 59, 59),
            datetime(2029, 12, 31, 12, 30, 5),
        ]

        for date_use in test_dates:
            with self.subTest(date_use=date_use):
                result = self._generate([failure], date_use=date_use)
                expected_date = date_use.strftime("%m-%d-%Y %H:%M:%S")
                self.assertEqual(result["datetime"].tolist(), [expected_date] * 3)
                self.assertEqual(result["preferred_month"].tolist(), [date_use.month] * 3)
                self.assertTrue(result["datetime"].map(lambda value: isinstance(value, str)).all())

    def test_results_have_clean_consecutive_index(self):
        """Returned rows should be indexed from zero without gaps."""
        result = self._generate([
            DummyShortTermFailure("first", 1.0),
            DummyShortTermFailure("second", 2.5),
        ])

        self.assertEqual(result.index.tolist(), [0, 1, 2, 3])
        self.assertTrue(result.index.is_unique)

    def test_repeated_calls_are_deterministic(self):
        """Identical inputs produce equal DataFrames across independent calls."""
        failures = [
            DummyShortTermFailure("failure_1", 1.3),
            DummyShortTermFailure("failure_2", 0.4),
        ]

        first = self._generate(failures)
        second = self._generate(failures)

        pd.testing.assert_frame_equal(first, second)

    def test_failure_objects_are_not_mutated(self):
        """Generating event rows must not modify the supplied domain objects."""
        failures = [
            DummyShortTermFailure("failure_1", 1.2, "operation_1", "immediately", 10),
            DummyShortTermFailure("failure_2", 0.7, "operation_2", "specific month", 20),
        ]
        before = [vars(failure).copy() for failure in failures]

        self._generate(failures)

        self.assertEqual([vars(failure) for failure in failures], before)

    def test_invalid_nan_failure_rate_raises_value_error(self):
        """An undefined rate cannot be converted to a finite number of events."""
        failure = DummyShortTermFailure("invalid", float("nan"))

        with self.assertRaises(ValueError):
            self._generate([failure])

    def test_result_dir_does_not_affect_dataframe(self):
        """The result_dir_r argument does not change in-memory event generation."""
        failures = [DummyShortTermFailure("failure_1", 2.4)]

        first = self._generate(failures, result_dir_r="first_directory")
        second = self._generate(failures, result_dir_r="second_directory")

        pd.testing.assert_frame_equal(first, second)

if __name__ == '__main__':
    unittest.main()
