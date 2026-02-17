import unittest
import os
from datetime import datetime
import pandas as pd
import numpy as np

from oriom.core.functions.logs_timeseries.failures import failures_event
from oriom.classes.Failure import Failure
from oriom.classes.Scenario import Scenario


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
    ):
        self.id = id_
        self.fail_rate = fail_rate
        self.n_element = n_element
        self.bath_tub = bath_tub
        self.maintenance_strategy = maintenance_strategy
        self.operation_triggered = operation_triggered
        self.preferred_month = preferred_month


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


if __name__ == '__main__':
    unittest.main()
