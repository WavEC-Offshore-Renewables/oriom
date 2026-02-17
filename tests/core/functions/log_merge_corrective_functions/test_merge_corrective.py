#test_merge_corrective

import unittest
import pandas as pd
from unittest.mock import MagicMock

from oriom.core.functions.log_merge_corrective_functions import merge_corrective


class TestCreateLogsMerge(unittest.TestCase):

    def setUp(self):
        """
        Prepare minimal input data needed to test merge_corrective.
        """

        # Minimal log_events DataFrame
        self.log_events = pd.DataFrame({
            'd_trigger': pd.to_datetime(['2025-01-10', '2025-01-11']),
            'd_end': pd.to_datetime(['2025-01-10', '2025-01-12']),
            'comments': ['fail_1.x', 'fail_2.x'],
            'event': ['failure', 'operation'],
            'id': [1, 2],
            'vessel_1': ['V1', 'V1'],
            'n_vessel_1': [1, 1],
            'vessel_2': [None, None],
            'n_vessel_2': [None, None],
            'd_end_leadtime': [None, None],
            'd_end_wait_start': [None, None],
            'd_end_dur_net_port': [None, None],
            'd_end_transit_ts': [None, None],
            'd_end_wait_site': [None, None],
            'd_end_dur_net_site': [None, None],
            'd_end_transit_tp': [None, None],
            'd_end_stat_chart': [None, None],
            'shutdown': [False, False],
            'ST_contract_1': [False, False],
            'ST_contract_2': [False, False]
        })

        # Failures list (empty because we mock functions)
        self.failures = []

        # Mocked objects
        self.find_element_class = MagicMock()
        self.operation_log_file_stats = []
        self.vessels = []
        self.time_between_devices = {}

        # Simple numeric parameters
        self.percentile = 0.9
        self.vessel_to_merge = []
        self.time_fail_op_immediately = 1.0
        self.duration_shift = 8.0

        # Mock external functions called by merge_corrective
        # This avoids needing the real complex system
        self.patcher1 = unittest.mock.patch(
            'oriom.core.functions.log_merge_corrective_functions.merge_corrective.creation_oper_vessel_dict',
            return_value=None
        )
        self.patcher2 = unittest.mock.patch(
            'oriom.core.functions.log_merge_corrective_functions.merge_corrective.merge_deferred_operations',
            return_value=pd.DataFrame()
        )
        self.patcher3 = unittest.mock.patch(
            'oriom.core.functions.log_merge_corrective_functions.merge_corrective.merge_operation',
            return_value=pd.DataFrame()
        )
        self.patcher4 = unittest.mock.patch(
            'oriom.core.functions.log_merge_corrective_functions.merge_corrective.mergeble_operation',
            return_value={}
        )
        self.patcher5 = unittest.mock.patch(
            'oriom.core.functions.log_merge_corrective_functions.merge_corrective.tow_deferred_mobi',
            return_value=pd.DataFrame()
        )

        self.patcher1.start()
        self.patcher2.start()
        self.patcher3.start()
        self.patcher4.start()
        self.patcher5.start()

        self.addCleanup(self.patcher1.stop)
        self.addCleanup(self.patcher2.stop)
        self.addCleanup(self.patcher3.stop)
        self.addCleanup(self.patcher4.stop)
        self.addCleanup(self.patcher5.stop)

    def test_output_is_dataframe(self):
        """
        Ensure the function returns a pandas DataFrame.
        """

        df_out = merge_corrective.create_logs_merge(
            log_events=self.log_events,
            failures=self.failures,
            operation_log_file_stats=self.operation_log_file_stats,
            result_dir_r="results/",
            vessels=self.vessels,
            find_element_class=self.find_element_class,
            time_between_devices=self.time_between_devices,
            percentile=self.percentile,
            vessel_to_merge=self.vessel_to_merge,
            time_fail_op_immediately=self.time_fail_op_immediately,
            duration_shift=self.duration_shift
        )

        self.assertIsInstance(df_out, pd.DataFrame)

    def test_preserves_failure_rows(self):
        """
        Check that failure events are kept in the output DataFrame.
        """

        df_out = merge_corrective.create_logs_merge(
            log_events=self.log_events,
            failures=self.failures,
            operation_log_file_stats=self.operation_log_file_stats,
            result_dir_r="results/",
            vessels=self.vessels,
            find_element_class=self.find_element_class,
            time_between_devices=self.time_between_devices,
            percentile=self.percentile,
            vessel_to_merge=self.vessel_to_merge,
            time_fail_op_immediately=self.time_fail_op_immediately,
            duration_shift=self.duration_shift
        )

        # Expect the failure row to be included
        self.assertIn('failure', df_out['event'].values)

    def test_sorted_by_trigger_date(self):
        """
        Ensure the output is sorted by d_trigger.
        """

        df_out = merge_corrective.create_logs_merge(
            log_events=self.log_events.sample(frac=1),  # shuffle rows
            failures=self.failures,
            operation_log_file_stats=self.operation_log_file_stats,
            result_dir_r="results/",
            vessels=self.vessels,
            find_element_class=self.find_element_class,
            time_between_devices=self.time_between_devices,
            percentile=self.percentile,
            vessel_to_merge=self.vessel_to_merge,
            time_fail_op_immediately=self.time_fail_op_immediately,
            duration_shift=self.duration_shift
        )

        sorted_dates = df_out['d_trigger'].tolist()
        self.assertEqual(sorted_dates, sorted(sorted_dates))


if __name__ == '__main__':
    unittest.main()
