# test_read_dataframe_value.py

import unittest
from datetime import datetime

from oriom.utils.read_dataframe_value import (
    get_first_failure,
    compute_rov_cost,
    take_id_operation,
    approximate_hourly_data,
)


class TestGetFirstFailure(unittest.TestCase):
    def test_dict_with_failures_list_returns_first(self):
        """get_first_failure should return the first failure from a dict with a 'failures' list."""
        value = {"failures": ["f1", "f2", "f3"]}
        self.assertEqual(get_first_failure(value), "f1")

    def test_dict_with_empty_failures_raises(self):
        """get_first_failure should raise ValueError for dict with empty 'failures' list."""
        value = {"failures": []}
        with self.assertRaises(ValueError):
            get_first_failure(value)

    def test_string_repr_of_dict_returns_first_failure(self):
        """get_first_failure should parse a stringified dict and return the first failure."""
        value = "{'failures': ['fA', 'fB']}"
        self.assertEqual(get_first_failure(value), "fA")

    def test_simple_string_is_returned_stripped(self):
        """get_first_failure should return a plain string stripped of whitespace."""
        value = "  failure_X  "
        self.assertEqual(get_first_failure(value), "failure_X")

    def test_unparsable_string_is_returned_stripped(self):
        """If string is not a dict literal, get_first_failure returns it stripped."""
        value = "not a dict literal"
        self.assertEqual(get_first_failure(value), "not a dict literal")

    def test_unsupported_type_raises(self):
        """get_first_failure should raise ValueError for unsupported types."""
        with self.assertRaises(ValueError):
            get_first_failure(123)  # int is unsupported


class TestComputeRovCost(unittest.TestCase):
    def test_single_string_id_with_cost(self):
        """compute_rov_cost should return cost * n_vessels for a simple string id."""
        rov_dict = {"opA": 100.0}
        self.assertEqual(compute_rov_cost("opA", 2, rov_dict), 200.0)

    def test_single_string_id_with_none_n_vessels_defaults_to_one(self):
        """If n_vessels is None, compute_rov_cost should treat it as 1."""
        rov_dict = {"opA": 50.0}
        self.assertEqual(compute_rov_cost("opA", None, rov_dict), 50.0)

    def test_string_list_repr_first_nonzero_used(self):
        """
        For a string representing a list of tuples, compute_rov_cost should take the
        first operation with non-zero cost and ignore the rest.
        """
        id_value = "[('0', 'opA'), ('1', 'opB')]"
        rov_dict = {"opA": 0.0, "opB": 120.0}
        # Only opB has cost, so we expect 120 * 1
        self.assertEqual(compute_rov_cost(id_value, 1, rov_dict), 120.0)

    def test_string_list_repr_first_item_nonzero_breaks(self):
        """If the first tuple has non-zero cost, it should break immediately and ignore later ones."""
        id_value = "[('0', 'opA'), ('1', 'opB')]"
        rov_dict = {"opA": 80.0, "opB": 999.0}
        # Should use only opA's cost
        self.assertEqual(compute_rov_cost(id_value, 3, rov_dict), 80.0 * 3)

    def test_actual_list_of_tuples_sums_all_costs(self):
        """
        For an actual list of tuples, compute_rov_cost should sum all costs
        and then multiply by n_vessels.
        """
        id_value = [("0", "opA"), ("1", "opB")]
        rov_dict = {"opA": 10.0, "opB": 20.0}
        # (10 + 20) * 2
        self.assertEqual(compute_rov_cost(id_value, 2, rov_dict), 60.0)

    def test_unparsable_string_falls_back_to_single_id_lookup(self):
        """If literal_eval fails, compute_rov_cost should treat the string as a single op id."""
        rov_dict = {"weird_string": 40.0}
        self.assertEqual(compute_rov_cost("weird_string", 2, rov_dict), 80.0)

    def test_unsupported_type_returns_zero(self):
        """If id_value is neither str nor list, compute_rov_cost should return 0."""
        self.assertEqual(compute_rov_cost(123, 1, {"opA": 100.0}), 0)


class TestTakeIdOperation(unittest.TestCase):
    def test_already_list_of_tuples_is_returned(self):
        """If id_value is already a list, take_id_operation must return it unchanged."""
        original = [(0, "opA"), (1, "opB")]
        result = take_id_operation(original, index=10)
        self.assertIs(result, original)

    def test_string_list_literal_is_parsed_to_list(self):
        """A string that is a list literal must be parsed into a list of tuples."""
        id_str = "[(0, 'opA'), (1, 'opB')]"
        result = take_id_operation(id_str, index=5)
        self.assertEqual(result, [(0, "opA"), (1, "opB")])

    def test_simple_string_id_is_wrapped_with_index(self):
        """A simple string id should be wrapped into [(index, id)]."""
        result = take_id_operation("opX", index=7)
        self.assertEqual(result, [(7, "opX")])

    def test_unparsable_string_is_wrapped_with_index(self):
        """If literal_eval fails, take_id_operation must still return [(index, id)]."""
        result = take_id_operation("not-a-list[", index=3)
        self.assertEqual(result, [(3, "not-a-list[")])

    def test_non_str_non_list_returns_empty_list(self):
        """Unsupported types should return an empty list."""
        self.assertEqual(take_id_operation(123, index=0), [])


class TestApproximateHourlyData(unittest.TestCase):
    def test_exact_hour_stays_same(self):
        """A datetime exactly on the hour must stay unchanged."""
        dt = datetime(2024, 1, 1, 10, 0, 0)
        result = approximate_hourly_data(dt)
        self.assertEqual(result, datetime(2024, 1, 1, 10, 0, 0))

    def test_round_nearest_down_for_less_than_half_hour(self):
        """
        With round_up=False, times with minutes < ~30 should round down
        according to the current implementation.
        """
        dt = datetime(2024, 1, 1, 10, 29, 0)
        result = approximate_hourly_data(dt)
        self.assertEqual(result, datetime(2024, 1, 1, 10, 0, 0))

    def test_round_nearest_up_for_more_than_half_hour(self):
        """
        With round_up=False, times with minutes > ~30 should round up
        according to the current implementation.
        """
        dt = datetime(2024, 1, 1, 10, 31, 0)
        result = approximate_hourly_data(dt)
        self.assertEqual(result, datetime(2024, 1, 1, 11, 0, 0))

    def test_half_minute_uses_bankers_rounding(self):
        """
        For 30 seconds past the hour, minutes = 0.5 and round(0.5) == 0 in Python,
        so it should round down to the same hour.
        """
        dt = datetime(2024, 1, 1, 10, 0, 30)
        result = approximate_hourly_data(dt)
        self.assertEqual(result, datetime(2024, 1, 1, 10, 0, 0))

    def test_round_up_true_ceils_if_has_minutes(self):
        """
        With round_up=True, any non-zero minutes/seconds should move to the next hour.
        """
        dt = datetime(2024, 1, 1, 10, 1, 0)
        result = approximate_hourly_data(dt, round_up=True)
        self.assertEqual(result, datetime(2024, 1, 1, 11, 0, 0))

    def test_round_up_true_keeps_exact_hour(self):
        """With round_up=True, exact hour stays unchanged."""
        dt = datetime(2024, 1, 1, 10, 0, 0)
        result = approximate_hourly_data(dt, round_up=True)
        self.assertEqual(result, datetime(2024, 1, 1, 10, 0, 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
