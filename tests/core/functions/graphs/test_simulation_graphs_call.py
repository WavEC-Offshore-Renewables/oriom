"""Unit tests for graphs_simulation_creation.

Run from the ORIOM project root:
    python -m unittest tests.core.functions.graphs.test_simulation_graphs_call -v

Alternatively, run this file directly from the project environment.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

from oriom.core.functions.graphs import simulation_graphs_call as graphs_module


class TestGraphsSimulationCreation(unittest.TestCase):
    """Verify graph orchestration, data transformations, and failure handling."""

    def setUp(self):
        """Prepare deterministic inputs and isolate plotting/statistical dependencies."""
        self.config = SimpleNamespace(
            ST=False,
            FUEL_TO_ADD={"CTV": 20.0},
            MOBILISATION_TO_ADD={"CTV": 100.0},
        )
        self.inputs = SimpleNamespace(
            stats=SimpleNamespace(lifetime={"value": 4}),
        )
        self.find_element = object()
        self.graph_dir = "test_graph_directory"

        self.dates_failures = pd.DataFrame(
            {
                "datetime": pd.to_datetime(["2025-03-01", "2025-06-10"]),
                "id": ["failure_1", "failure_2"],
            }
        )
        self.kpi_total = pd.DataFrame(
            {
                "vessel_id": ["CTV"],
                "lifetime_direct_costs": [2400.0],
            }
        )
        self.kpi_yearly = pd.DataFrame(
            {
                "year": [2025, 2026],
                "CTV": [700.0, 900.0],
            }
        )

        self.costs = {
            "Vessels": 1200.0,
            "Fuel": 400.0,
            "Mobilisation": 800.0,
        }
        self.stacked_array = object()
        self.all_index = [2025, 2026]
        self.all_columns = ["CTV"]
        self.percentile_arrays = object()
        self.average_vessel_cost = pd.DataFrame(
            {
                "year": [2025, 2026],
                "CTV": [700.0, 900.0],
            }
        )

        self.mock_distribution_failures = self._patch(
            graphs_module.report_graphs, "distribution_failures"
        )
        self.mock_lifetime_cost = self._patch(
            graphs_module.report_graphs, "lifetime_cost"
        )
        self.mock_create_costs_data = self._patch(
            graphs_module.final_run_statistics, "create_costs_data"
        )
        self.mock_safe_stack = self._patch(
            graphs_module.final_run_statistics, "safe_stack"
        )
        self.mock_calculate_statistics = self._patch(
            graphs_module.final_run_statistics, "calculate_statistics"
        )
        self.mock_create_vessel_cost = self._patch(
            graphs_module.final_run_statistics, "create_vessel_cost"
        )
        self.mock_yearly_vessel_cost = self._patch(
            graphs_module.final_economic_graphs, "yearly_vessel_cost"
        )

        self.mock_create_costs_data.return_value = self.costs.copy()
        self.mock_safe_stack.return_value = (
            self.stacked_array,
            self.all_index,
            self.all_columns,
        )
        self.mock_calculate_statistics.return_value = self.percentile_arrays
        self.mock_create_vessel_cost.return_value = {
            "AVG": self.average_vessel_cost,
        }

    def _patch(self, module, function_name):
        """Patch a function used by the target module and register automatic cleanup."""
        patcher = patch.object(module, function_name)
        mocked_function = patcher.start()
        self.addCleanup(patcher.stop)
        return mocked_function

    def _run(self, dates_failures=None):
        """Call the function under test with the configured input objects."""
        if dates_failures is None:
            dates_failures = self.dates_failures

        return graphs_module.graphs_simulation_creation(
            Config=self.config,
            inputs=self.inputs,
            find_element=self.find_element,
            dates_failures=dates_failures,
            kpi_total_timeseries=self.kpi_total,
            kpi_yearly_timeseries=self.kpi_yearly,
            graph_dir_r=self.graph_dir,
        )

    def _assert_statistical_pipeline(self):
        """Verify that input data and statistics flow through the correct calls."""
        self.mock_create_costs_data.assert_called_once()
        cost_kwargs = self.mock_create_costs_data.call_args.kwargs
        self.assertEqual(set(cost_kwargs), {
            "lists_costs_tot",
            "fuel_add",
            "mobilisation_add",
            "n_lifetime",
        })
        self.assertEqual(len(cost_kwargs["lists_costs_tot"]), 1)
        self.assertIs(cost_kwargs["lists_costs_tot"][0], self.kpi_total)
        self.assertIs(cost_kwargs["fuel_add"], self.config.FUEL_TO_ADD)
        self.assertIs(
            cost_kwargs["mobilisation_add"], self.config.MOBILISATION_TO_ADD
        )
        self.assertEqual(cost_kwargs["n_lifetime"], 4)

        self.mock_safe_stack.assert_called_once()
        stack_args, stack_kwargs = self.mock_safe_stack.call_args
        self.assertEqual(stack_kwargs, {})
        self.assertEqual(len(stack_args), 1)
        self.assertEqual(len(stack_args[0]), 1)
        self.assertIs(stack_args[0][0], self.kpi_yearly)

        self.mock_calculate_statistics.assert_called_once_with(
            self.stacked_array,
            axis=0,
            ignore_nan=True,
        )

        self.mock_create_vessel_cost.assert_called_once()
        vessel_kwargs = self.mock_create_vessel_cost.call_args.kwargs
        self.assertEqual(set(vessel_kwargs), {
            "percentile_arrays",
            "fuel_add",
            "mobilisation_add",
            "all_index",
            "all_columns",
        })
        self.assertIs(vessel_kwargs["percentile_arrays"], self.percentile_arrays)
        self.assertIs(vessel_kwargs["fuel_add"], self.config.FUEL_TO_ADD)
        self.assertIs(
            vessel_kwargs["mobilisation_add"], self.config.MOBILISATION_TO_ADD
        )
        self.assertIs(vessel_kwargs["all_index"], self.all_index)
        self.assertIs(vessel_kwargs["all_columns"], self.all_columns)

    def _assert_vessel_graph(self, expected_title):
        """Verify that the AVG annual vessel costs are used in the final graph."""
        self.mock_yearly_vessel_cost.assert_called_once()
        graph_kwargs = self.mock_yearly_vessel_cost.call_args.kwargs
        self.assertIs(graph_kwargs["df"], self.average_vessel_cost)
        self.assertEqual(graph_kwargs["title"], expected_title)
        self.assertIs(graph_kwargs["find_element_class"], self.find_element)
        self.assertEqual(graph_kwargs["save_dir"], self.graph_dir)

    def test_long_term_creates_failure_lifetime_yearly_and_vessel_graphs(self):
        """LT mode should produce failure, lifetime, yearly and vessel graphs."""
        original_total = self.kpi_total.copy(deep=True)
        original_yearly = self.kpi_yearly.copy(deep=True)

        result = self._run()

        self.assertIsNone(result)
        self.mock_distribution_failures.assert_called_once()
        distribution_kwargs = self.mock_distribution_failures.call_args.kwargs
        self.assertIs(distribution_kwargs["df"], self.dates_failures)
        self.assertEqual(distribution_kwargs["save_dir"], self.graph_dir)

        self.mock_lifetime_cost.assert_called()
        self.assertEqual(self.mock_lifetime_cost.call_count, 2)
        lifetime_call, yearly_call = self.mock_lifetime_cost.call_args_list

        expected_lifetime_df = pd.DataFrame(
            {
                "cost_type": ["Vessels", "Fuel", "Mobilisation"],
                "values": [1200.0, 400.0, 800.0],
            }
        )
        expected_yearly_df = expected_lifetime_df.copy(deep=True)
        expected_yearly_df["values"] /= 4

        assert_frame_equal(
            lifetime_call.kwargs["df"], expected_lifetime_df
        )
        assert_frame_equal(
            yearly_call.kwargs["df"], expected_yearly_df
        )
        self.assertEqual(lifetime_call.kwargs["title"], "Lifetime costs")
        self.assertEqual(yearly_call.kwargs["title"], "Yearly costs")
        self.assertEqual(lifetime_call.kwargs["save_dir"], self.graph_dir)
        self.assertEqual(yearly_call.kwargs["save_dir"], self.graph_dir)
        self.assertIsNot(lifetime_call.kwargs["df"], yearly_call.kwargs["df"])

        self._assert_statistical_pipeline()
        self._assert_vessel_graph("Yearly Vessels costs")
        assert_frame_equal(self.kpi_total, original_total)
        assert_frame_equal(self.kpi_yearly, original_yearly)
        self.assertEqual(self.costs["Vessels"], 1200.0)

    def test_short_term_creates_direct_and_vessel_graphs_without_yearly_cost(self):
        """ST mode should skip the yearly-cost graph and use the ST titles."""
        self.config.ST = True

        self._run()

        self.mock_distribution_failures.assert_called_once()
        self.assertEqual(self.mock_lifetime_cost.call_count, 1)
        cost_kwargs = self.mock_lifetime_cost.call_args.kwargs
        self.assertEqual(cost_kwargs["title"], "Direct costs")
        self.assertEqual(cost_kwargs["save_dir"], self.graph_dir)
        self.assertEqual(
            cost_kwargs["df"]["values"].tolist(),
            [1200.0, 400.0, 800.0],
        )
        self._assert_statistical_pipeline()
        self._assert_vessel_graph("Vessels costs")

    def test_empty_failure_data_skips_only_failure_distribution_graph(self):
        """An empty failure dataframe should not prevent economic charts."""
        empty_failures = self.dates_failures.iloc[0:0].copy()

        self._run(dates_failures=empty_failures)

        self.mock_distribution_failures.assert_not_called()
        self.assertEqual(self.mock_lifetime_cost.call_count, 2)
        self._assert_statistical_pipeline()
        self._assert_vessel_graph("Yearly Vessels costs")

    def test_missing_avg_vessel_statistics_raises_key_error(self):
        """The function requires the AVG entry in the vessel-cost result."""
        self.mock_create_vessel_cost.return_value = {"P50": pd.DataFrame()}

        with self.assertRaises(KeyError) as error:
            self._run()

        self.assertEqual(error.exception.args[0], "AVG")
        self.mock_create_vessel_cost.assert_called_once()
        self.mock_yearly_vessel_cost.assert_not_called()

    def test_cost_statistic_failure_propagates_without_generating_cost_graphs(self):
        """A failure in cost aggregation should propagate to the caller."""
        self.mock_create_costs_data.side_effect = ValueError("Invalid cost inputs")

        with self.assertRaisesRegex(ValueError, "Invalid cost inputs"):
            self._run()

        self.mock_distribution_failures.assert_called_once()
        self.mock_lifetime_cost.assert_not_called()
        self.mock_safe_stack.assert_not_called()
        self.mock_calculate_statistics.assert_not_called()
        self.mock_create_vessel_cost.assert_not_called()
        self.mock_yearly_vessel_cost.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
