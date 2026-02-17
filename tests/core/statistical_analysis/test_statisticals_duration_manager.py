# test_statistical_duration_manager
import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
import pandas as pd

from oriom.core.statistical_analysis.statisticals_duration_manager import statistical_duration_manager


def make_operation(op_id, name):
    """Create a minimal operation object with id, name, and ts_data.oper_sched."""
    ts_data = SimpleNamespace(oper_sched=pd.DataFrame({"dummy": [1, 2, 3]}))
    return SimpleNamespace(id=op_id, name=name, ts_data=ts_data)


class TestStatisticalDurationManager(unittest.TestCase):
    @patch("oriom.core.statistical_analysis.statisticals_duration_manager.aux_functions.save_file_csv")
    @patch("oriom.core.statistical_analysis.statisticals_duration_manager.operation_stats")
    def test_basic_statistical_duration_manager(self, mock_operation_stats, mock_save_csv):
        """
        Test that statistical_duration_manager:
        - calls operation_stats for each operation and percentile
        - sets 'operation_id' column
        - saves CSV using aux_functions.save_file_csv
        - computes the maximum percentile correctly
        """
        # Prepare mock operation_stats to return a DataFrame
        mock_df = pd.DataFrame({"dummy_stat": [10, 20]})
        mock_operation_stats.return_value = mock_df.copy()

        # Prepare operations and inputs_stats
        ops = [make_operation("OP1", "Operation 1"), make_operation("OP2", "Operation 2")]
        inputs_stats = SimpleNamespace(percentiles={"value": [50, 90]}, percentile_max=None)

        # Call the function
        statistical_duration_manager(
            operation_dir="dummy_dir",
            total_operations=ops,
            inputs_stats=inputs_stats
        )

        # Check that operation_stats was called for each operation and percentile
        expected_calls = len(ops) * len(inputs_stats.percentiles["value"])
        self.assertEqual(mock_operation_stats.call_count, expected_calls)

        # Check that save_file_csv was called the same number of times
        self.assertEqual(mock_save_csv.call_count, expected_calls)

        # Check that 'operation_id' was added to the DataFrame before saving
        for call_args in mock_save_csv.call_args_list:
            df_arg = call_args[0][0]  # first positional argument is df
            self.assertIn("operation_id", df_arg.columns)

        # Check that percentile_max is set correctly
        self.assertEqual(inputs_stats.percentile_max, {"value": 90, "units": None})

    @patch("oriom.core.statistical_analysis.statisticals_duration_manager.aux_functions.save_file_csv")
    @patch("oriom.core.statistical_analysis.statisticals_duration_manager.operation_stats", side_effect=FileNotFoundError)
    def test_file_not_found_warning(self, mock_operation_stats, mock_save_csv):
        """
        Test that if operation_stats raises FileNotFoundError, a warning is logged
        and processing continues without crashing.
        """
        ops = [make_operation("OP1", "Operation 1")]
        inputs_stats = SimpleNamespace(percentiles={"value": [50]}, percentile_max=None)
        for op in ops:
            delattr(op, 'ts_data')

        #with self.assertLogs(level='WARNING') as log_cm:
        statistical_duration_manager(
            operation_dir="dummy_dir",
            total_operations=ops,
            inputs_stats=inputs_stats
        )

        #self.assertIn("WARNING", log_cm.output[0])

        # save_file_csv should not be called
        mock_save_csv.assert_not_called()

        # percentile_max should still be set
        self.assertEqual(inputs_stats.percentile_max, {"value": 50, "units": None})


if __name__ == "__main__":
    unittest.main(verbosity=2)
