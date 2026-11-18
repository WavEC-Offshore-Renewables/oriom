"""Unit tests for ORIOM return_statistics_runs_ST."""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import tempfile
import unittest
from copy import deepcopy
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal

from oriom.core.statistical_analysis import final_run_statistics_ST


def make_energy_results():
    """Three simulated runs, with data for wind, wave and solar production."""
    sources = {
        'Availability_year_wind': [
            [(0.10, 10), (0.10, 15)],
            [(0.05, 3), (0.00, 2)],
            [(0.10, 20), (0.10, 10)],
        ],
        'Availability_year_wave': [
            [(0.01, 1)],
            [(0.02, 2)],
            [(0.00, 0)],
        ],
        'Availability_year_pv': [
            [(0.00, 0)],
            [(0.03, 5)],
            [(0.02, 3)],
        ],
    }
    return {
        name: [
            pd.DataFrame(rows, columns=['energy_loss_Meur', 'En_loss_kWh'])
            for rows in run_rows
        ]
        for name, run_rows in sources.items()
    }


def make_cost_results():
    """The 'total' row, not individual vessel rows, defines each run's OPEX."""
    return [
        pd.DataFrame({
            'vessel_id': ['ctv_001', 'sv_001', 'total'],
            'lifetime_direct_costs': [100000.0, 300000.0, 400000.0],
        }),
        pd.DataFrame({
            'vessel_id': ['ctv_001', 'sv_001', 'total'],
            'lifetime_direct_costs': [70000.0, 180000.0, 250000.0],
        }),
        pd.DataFrame({
            'vessel_id': ['ctv_001', 'sv_001', 'total'],
            'lifetime_direct_costs': [100000.0, 100000.0, 200000.0],
        }),
    ]


def make_log_results():
    """Three run logs: run 2 leaves one of the original failures unresolved."""
    initial = [
        {'event': 'failure', 'id': 'ofw_fail_a', 'comments': None},
        {'event': 'failure', 'id': 'ofw_fail_b', 'comments': None},
    ]
    both_corrected = [
        {'event': 'operation', 'id': 'work_a', 'comments': 'operation_ofw_fail_a'},
        {'event': 'tow', 'id': 'work_b', 'comments': 'tow_ofw_fail_b'},
    ]
    only_a_corrected = [both_corrected[0]]
    return [
        pd.DataFrame(initial + both_corrected),
        pd.DataFrame(both_corrected),
        pd.DataFrame(only_a_corrected),
    ]


def make_results():
    return SimpleNamespace(
        dfs_energy_yearly_dict=make_energy_results(),
        dfs_tot_cost_list=make_cost_results(),
        dfs_log_events_merged=make_log_results(),
    )


class TestReturnStatisticsRunsST(unittest.TestCase):
    """Exercise the real function while mocking only plotting side effects."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.result_dir = self.root / 'results'
        self.save_dir = self.root / 'figures'
        self.results = make_results()
        self.metocean = pd.DataFrame(
            {'Hs': [1.0, 1.2, 1.4]},
            index=pd.date_range('2026-11-03 06:00:00', periods=3, freq='h'),
        )

        for run in range(3):
            folder = self.result_dir / f'result_{run}'
            folder.mkdir(parents=True)
            (folder / 'run_id.txt').write_text(f'RUN={run}', encoding='utf-8')
            (folder / 'nested').mkdir()
            (folder / 'nested' / 'result.csv').write_text(
                f'run,value\n{run},{run * 10}\n', encoding='utf-8'
            )

        self.cost_patcher = patch.object(final_run_statistics_ST, 'final_stat_graph_ST', return_value=1)
        self.energy_patcher = patch.object(final_run_statistics_ST, 'plot_energy_losses_ST')
        self.mock_cost_plot = self.cost_patcher.start()
        self.mock_energy_plot = self.energy_patcher.start()
        self.addCleanup(self.cost_patcher.stop)
        self.addCleanup(self.energy_patcher.stop)

    def _run(self, *, results=None, n_runs=3, save_dir=None, result_dir=None):
        return final_run_statistics_ST.return_statistics_runs_ST(
            results_dict=self.results if results is None else results,
            n_runs=n_runs,
            metocean_df=self.metocean,
            dir_result=str(self.result_dir if result_dir is None else result_dir),
            save_dir=str(self.save_dir if save_dir is None else save_dir),
        )

    def _assert_no_graphs(self):
        self.mock_cost_plot.assert_not_called()
        self.mock_energy_plot.assert_not_called()

    def test_aggregates_energy_costs_across_wind_wave_and_pv(self):
        self._run()
        self.mock_cost_plot.assert_called_once()
        call_kwargs = self.mock_cost_plot.call_args.kwargs
        costs = call_kwargs['total_costs']
        energy_costs = call_kwargs['total_energy_losses_costs']
        metocean = call_kwargs['metocean_df']
        self.assertEqual(costs, {0: 400000.0, 1: 250000.0, 2: 200000.0})
        for run, expected in {0: 0.21, 1: 0.10, 2: 0.22}.items():
            self.assertAlmostEqual(energy_costs[run], expected)
        self.assertIs(metocean, self.metocean)
        self.assertEqual(self.mock_cost_plot.call_args.kwargs['save_dir'], str(self.save_dir))
        self.assertEqual(call_kwargs['failure_not_corrected_idx'], 2)
        self.assertEqual(call_kwargs['failure_ranges'], [(2, 2, ['ofw_fail_b'])])

    def test_aggregates_energy_losses_in_kwh_separately_from_costs(self):
        self._run()
        self.mock_energy_plot.assert_called_once()
        self.assertEqual(
            self.mock_energy_plot.call_args.kwargs['total_energy_losses'],
            {0: 26, 1: 12, 2: 33},
        )
        self.assertIs(self.mock_energy_plot.call_args.kwargs['metocean_df'],
                      self.metocean)
        self.assertEqual(self.mock_energy_plot.call_args.kwargs['save_dir'],
                         str(self.save_dir))
        self.assertEqual(self.mock_energy_plot.call_args.kwargs['failure_not_corrected_idx'], 2)
        self.assertEqual(self.mock_energy_plot.call_args.kwargs['failure_ranges'],
                         [(2, 2, ['ofw_fail_b'])])

    def test_direct_costs_come_exclusively_from_total_rows(self):
        self.results.dfs_tot_cost_list[0].loc[
            self.results.dfs_tot_cost_list[0]['vessel_id'] == 'ctv_001',
            'lifetime_direct_costs',
        ] = 9999999
        self._run()
        total_costs = self.mock_cost_plot.call_args.kwargs['total_costs']
        self.assertEqual(total_costs, {0: 400000.0, 1: 250000.0, 2: 200000.0})

    def test_first_total_row_is_used_when_duplicate_total_rows_exist(self):
        df = self.results.dfs_tot_cost_list[0]
        self.results.dfs_tot_cost_list[0] = pd.concat(
            [df, pd.DataFrame([{'vessel_id': 'total', 'lifetime_direct_costs': 999999}])],
            ignore_index=True,
        )
        self._run()
        self.assertEqual(self.mock_cost_plot.call_args.kwargs['total_costs'][0], 400000.0)

    def test_aggregation_uses_all_rows_in_each_energy_dataframe(self):
        self.results.dfs_energy_yearly_dict['Availability_year_wind'][1] = pd.DataFrame({
            'energy_loss_Meur': [0.01, 0.02, 0.03],
            'En_loss_kWh': [2, 4, 6],
        })
        self._run()
        self.assertAlmostEqual(self.mock_cost_plot.call_args.kwargs['total_energy_losses_costs'][1], 0.11)
        self.assertEqual(self.mock_energy_plot.call_args.kwargs['total_energy_losses'][1], 19)

    def test_nan_values_are_skipped_by_pandas_sum(self):
        self.results.dfs_energy_yearly_dict['Availability_year_wind'][0].loc[
            0, ['energy_loss_Meur', 'En_loss_kWh']
        ] = float('nan')
        self._run()
        self.assertAlmostEqual(self.mock_cost_plot.call_args.kwargs['total_energy_losses_costs'][0], 0.11)
        self.assertEqual(self.mock_energy_plot.call_args.kwargs['total_energy_losses'][0], 16)

    def test_empty_energy_lists_contribute_zero(self):
        self.results.dfs_energy_yearly_dict = {
            'Availability_year_wind': [],
            'Availability_year_wave': [],
            'Availability_year_pv': [],
        }
        self._run()
        self.assertEqual(self.mock_cost_plot.call_args.kwargs['total_energy_losses_costs'], {0: 0, 1: 0, 2: 0})
        self.assertEqual(
            self.mock_energy_plot.call_args,
            None,
        )

    def test_extra_energy_columns_do_not_affect_results(self):
        for frames in self.results.dfs_energy_yearly_dict.values():
            for df in frames:
                df['other'] = 1e9
        self._run()
        self.assertAlmostEqual(self.mock_cost_plot.call_args.kwargs['total_energy_losses_costs'][0], 0.21)
        self.assertEqual(self.mock_energy_plot.call_args.kwargs['total_energy_losses'][2], 33)

    def test_input_dataframes_and_metocean_are_not_modified(self):
        original_energy = deepcopy(self.results.dfs_energy_yearly_dict)
        original_costs = deepcopy(self.results.dfs_tot_cost_list)
        original_metocean = self.metocean.copy(deep=True)
        original_logs = deepcopy(self.results.dfs_log_events_merged)
        self._run()
        for name in original_energy:
            for actual, expected in zip(
                self.results.dfs_energy_yearly_dict[name], original_energy[name]
            ):
                assert_frame_equal(actual, expected)
        for actual, expected in zip(self.results.dfs_tot_cost_list, original_costs):
            assert_frame_equal(actual, expected)
        assert_frame_equal(self.metocean, original_metocean)
        for actual, expected in zip(self.results.dfs_log_events_merged, original_logs):
            assert_frame_equal(actual, expected)

    def test_metocean_dataframe_is_passed_by_identity_to_both_plots(self):
        self._run()
        self.assertIs(self.mock_cost_plot.call_args.kwargs['metocean_df'], self.metocean)
        self.assertIs(self.mock_energy_plot.call_args.kwargs['metocean_df'], self.metocean)

    def test_both_graphs_are_called_exactly_once(self):
        self._run()
        self.assertEqual(self.mock_cost_plot.call_count, 1)
        self.assertEqual(self.mock_energy_plot.call_count, 1)

    def test_copies_only_the_minimum_cost_run_including_nested_files(self):
        self.mock_cost_plot.return_value = 2
        self._run()
        destination = self.save_dir / 'minimum_cost_run'
        self.assertEqual((destination / 'run_id.txt').read_text(encoding='utf-8'), 'RUN=2')
        self.assertEqual(
            (destination / 'nested' / 'result.csv').read_text(encoding='utf-8'),
            'run,value\n2,20\n',
        )
        self.assertEqual({p.name for p in destination.iterdir()}, {'run_id.txt', 'nested'})

    def test_existing_minimum_cost_run_destination_is_merged(self):
        destination = self.save_dir / 'minimum_cost_run'
        destination.mkdir(parents=True)
        (destination / 'keep_this.txt').write_text('existing', encoding='utf-8')
        (destination / 'run_id.txt').write_text('old content', encoding='utf-8')
        self._run()
        self.assertEqual((destination / 'keep_this.txt').read_text(), 'existing')
        self.assertEqual((destination / 'run_id.txt').read_text(), 'RUN=1')
        self.assertTrue((destination / 'nested' / 'result.csv').exists())

    def test_save_dir_can_be_an_existing_deeply_nested_path(self):
        nested_output = self.root / 'uncreated' / 'many' / 'levels'
        self._run(save_dir=nested_output)
        self.assertEqual(
            (nested_output / 'minimum_cost_run' / 'run_id.txt').read_text(), 'RUN=1'
        )
        self.mock_cost_plot.assert_called_once()
        self.assertEqual(self.mock_cost_plot.call_args.kwargs['total_costs'],
                         {0: 400000.0, 1: 250000.0, 2: 200000.0})
        for run, expected in {0: 0.21, 1: 0.10, 2: 0.22}.items():
            self.assertAlmostEqual(self.mock_cost_plot.call_args.kwargs['total_energy_losses_costs'][run], expected)
        self.assertIs(self.mock_cost_plot.call_args.kwargs['metocean_df'], self.metocean)
        self.assertEqual(self.mock_cost_plot.call_args.kwargs['save_dir'], str(nested_output))

    def test_function_returns_none(self):
        self.assertIsNone(self._run())

    def test_can_process_a_single_run(self):
        results = make_results()
        results.dfs_energy_yearly_dict = {
            name: frames[:1] for name, frames in results.dfs_energy_yearly_dict.items()
        }
        results.dfs_tot_cost_list = results.dfs_tot_cost_list[:1]
        self.mock_cost_plot.return_value = 0
        self._run(results=results, n_runs=1)
        self.assertEqual(self.mock_cost_plot.call_args.kwargs['total_costs'], {0: 400000.0})
        self.assertEqual(self.mock_energy_plot.call_args.kwargs['total_energy_losses'], {0: 26})
        self.assertEqual((self.save_dir / 'minimum_cost_run' / 'run_id.txt').read_text(), 'RUN=0')

    def test_missing_selected_run_directory_raises_filenotfounderror(self):
        self.mock_cost_plot.return_value = 5
        with self.assertRaises(FileNotFoundError):
            self._run()
        self.mock_energy_plot.assert_called_once()
        self.assertFalse((self.save_dir / 'minimum_cost_run').exists())

    def test_none_save_dir_raises_typeerror_on_copy(self):
        # The signature permits None but the current implementation passes None
        # to os.path.join. This checks the existing behavior, not a desired API.
        with self.assertRaises(TypeError):
            final_run_statistics_ST.return_statistics_runs_ST(
                self.results, 3, self.metocean, str(self.result_dir), save_dir=None
            )
        self.mock_cost_plot.assert_called_once()
        self.mock_energy_plot.assert_called_once()

    def test_missing_energy_source_raises_keyerror_before_plotting(self):
        del self.results.dfs_energy_yearly_dict['Availability_year_wave']
        with self.assertRaises(KeyError):
            self._run()
        self._assert_no_graphs()

    def test_missing_energy_cost_column_raises_keyerror_before_plotting(self):
        self.results.dfs_energy_yearly_dict['Availability_year_pv'][0].drop(
            columns='energy_loss_Meur', inplace=True
        )
        with self.assertRaises(KeyError):
            self._run()
        self._assert_no_graphs()

    def test_missing_kwh_column_raises_keyerror_before_plotting(self):
        self.results.dfs_energy_yearly_dict['Availability_year_pv'][0].drop(
            columns='En_loss_kWh', inplace=True
        )
        with self.assertRaises(KeyError):
            self._run()
        self._assert_no_graphs()

    def test_missing_total_cost_row_raises_indexerror_before_plotting(self):
        self.results.dfs_tot_cost_list[0] = self.results.dfs_tot_cost_list[0].query(
            "vessel_id != 'total'"
        )
        with self.assertRaises(IndexError):
            self._run()
        self._assert_no_graphs()

    def test_missing_vessel_id_column_raises_keyerror_before_plotting(self):
        self.results.dfs_tot_cost_list[0] = self.results.dfs_tot_cost_list[0].drop(
            columns='vessel_id'
        )
        with self.assertRaises(KeyError):
            self._run()
        self._assert_no_graphs()

    def test_missing_lifetime_direct_costs_column_raises_keyerror_before_plotting(self):
        self.results.dfs_tot_cost_list[0] = self.results.dfs_tot_cost_list[0].drop(
            columns='lifetime_direct_costs'
        )
        with self.assertRaises(KeyError):
            self._run()
        self._assert_no_graphs()

    def test_more_energy_runs_than_n_runs_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self._run(n_runs=2)
        self._assert_no_graphs()

    def test_missing_cost_runs_remain_zero_current_behavior(self):
        self.results.dfs_tot_cost_list = self.results.dfs_tot_cost_list[:2]
        self._run()
        self.assertEqual(
            self.mock_cost_plot.call_args.kwargs['total_costs'],
            {0: 400000.0, 1: 250000.0, 2: 0.0},
        )

    def test_graph_callback_failure_propagates_and_no_copy_is_made(self):
        self.mock_cost_plot.side_effect = RuntimeError('chart error')
        with self.assertRaisesRegex(RuntimeError, 'chart error'):
            self._run()
        self.mock_energy_plot.assert_not_called()
        self.assertFalse((self.save_dir / 'minimum_cost_run').exists())

    def test_energy_graph_callback_failure_propagates_and_no_copy_is_made(self):
        self.mock_energy_plot.side_effect = RuntimeError('energy chart error')
        with self.assertRaisesRegex(RuntimeError, 'energy chart error'):
            self._run()
        self.mock_cost_plot.assert_called_once()
        self.assertFalse((self.save_dir / 'minimum_cost_run').exists())




class TestCheckFailureCorrected(unittest.TestCase):
    """Validate corrected failure ID extraction, including merged operations."""

    def setUp(self):
        self.logs = make_log_results()

    def test_initial_failures_are_taken_only_from_first_run(self):
        self.logs[1] = pd.DataFrame([
            {'event': 'failure', 'id': 'ofw_unexpected', 'comments': None},
            {'event': 'operation', 'id': 'work_a', 'comments': 'operation_ofw_fail_a'},
        ])
        actual = final_run_statistics_ST.check_failure_corrected(self.logs)
        self.assertEqual(actual[1], ['ofw_fail_b'])
        self.assertNotIn('ofw_unexpected', actual[1])

    def test_operation_and_tow_both_mark_failures_corrected(self):
        actual = final_run_statistics_ST.check_failure_corrected(self.logs)
        self.assertEqual(actual, {0: [], 1: [], 2: ['ofw_fail_b']})

    def test_missing_corrections_preserve_initial_order(self):
        self.logs[2] = pd.DataFrame([
            {'event': 'other', 'id': 'x', 'comments': 'operation_ofw_fail_a'},
        ])
        self.assertEqual(
            final_run_statistics_ST.check_failure_corrected(self.logs)[2],
            ['ofw_fail_a', 'ofw_fail_b'],
        )

    def test_merged_operation_parser_returning_list(self):
        merged_comment = 'combined_operations'
        self.logs[2] = pd.DataFrame([
            {'event': 'operation_merged', 'id': 'combined', 'comments': merged_comment}
        ])
        with patch.object(final_run_statistics_ST, 'get_first_failure', return_value=[
            'operation_ofw_fail_a', 'tow_ofw_fail_b'
        ]) as parser:
            result = final_run_statistics_ST.check_failure_corrected(self.logs)
        self.assertEqual(result[2], [])
        parser.assert_called_once_with(merged_comment, first=False)

    def test_deferred_merged_operation_parser_returning_string(self):
        self.logs[2] = pd.DataFrame([
            {'event': 'operation_deferred_merged', 'id': 'combined', 'comments': 'merged'}
        ])
        with patch.object(final_run_statistics_ST, 'get_first_failure', return_value='operation_ofw_fail_b') as parser:
            result = final_run_statistics_ST.check_failure_corrected(self.logs)
        self.assertEqual(result[2], ['ofw_fail_a'])
        parser.assert_called_once_with('merged', first=False)

    def test_multiple_merged_rows_are_aggregated(self):
        self.logs[2] = pd.DataFrame([
            {'event': 'operation_merged', 'id': 'a', 'comments': 'group_a'},
            {'event': 'operation_deferred_merged', 'id': 'b', 'comments': 'group_b'},
        ])
        with patch.object(final_run_statistics_ST, 'get_first_failure', side_effect=[
            ['operation_ofw_fail_a'], ['operation_ofw_fail_b']
        ]) as parser:
            actual = final_run_statistics_ST.check_failure_corrected(self.logs)
        self.assertEqual(actual[2], [])
        self.assertEqual(parser.call_count, 2)

    def test_duplicate_correction_comments_do_not_duplicate_failures(self):
        self.logs[2] = pd.DataFrame([
            {'event': 'operation', 'id': 'a', 'comments': 'operation_ofw_fail_a'},
            {'event': 'operation', 'id': 'b', 'comments': 'operation_ofw_fail_a'},
        ])
        self.assertEqual(final_run_statistics_ST.check_failure_corrected(self.logs)[2], ['ofw_fail_b'])

    def test_missing_comments_are_ignored(self):
        self.logs[2] = pd.DataFrame([
            {'event': 'operation', 'id': 'a', 'comments': None},
            {'event': 'tow', 'id': 'b', 'comments': float('nan')},
        ])
        self.assertEqual(final_run_statistics_ST.check_failure_corrected(self.logs)[2],
                         ['ofw_fail_a', 'ofw_fail_b'])

    def test_unrecognised_event_types_do_not_count_as_corrections(self):
        self.logs[2] = pd.DataFrame([
            {'event': 'repair', 'id': 'a', 'comments': 'operation_ofw_fail_a'},
            {'event': 'failure', 'id': 'b', 'comments': 'tow_ofw_fail_b'},
        ])
        self.assertEqual(final_run_statistics_ST.check_failure_corrected(self.logs)[2],
                         ['ofw_fail_a', 'ofw_fail_b'])

    def test_initial_failure_ids_are_not_deduplicated(self):
        self.logs[0] = pd.concat([
            self.logs[0],
            pd.DataFrame([{'event': 'failure', 'id': 'ofw_fail_b', 'comments': None}]),
        ], ignore_index=True)
        self.assertEqual(final_run_statistics_ST.check_failure_corrected(self.logs)[2],
                         ['ofw_fail_b', 'ofw_fail_b'])

    def test_no_initial_failures_results_in_empty_lists(self):
        self.logs[0] = self.logs[0].query("event != 'failure'").copy()
        self.assertEqual(final_run_statistics_ST.check_failure_corrected(self.logs),
                         {0: [], 1: [], 2: []})

    def test_input_dataframes_remain_unchanged(self):
        originals = deepcopy(self.logs)
        final_run_statistics_ST.check_failure_corrected(self.logs)
        for actual, expected in zip(self.logs, originals):
            assert_frame_equal(actual, expected)

    def test_empty_list_of_runs_raises_index_error(self):
        with self.assertRaises(IndexError):
            final_run_statistics_ST.check_failure_corrected([])

    def test_missing_event_column_raises_key_error(self):
        with self.assertRaises(KeyError):
            final_run_statistics_ST.check_failure_corrected([pd.DataFrame({'id': ['a']})])

    def test_merged_parser_must_return_string_or_iterable(self):
        self.logs[2] = pd.DataFrame([
            {'event': 'operation_merged', 'id': 'a', 'comments': 'bad'}
        ])
        with patch.object(final_run_statistics_ST, 'get_first_failure', return_value=None):
            with self.assertRaises(TypeError):
                final_run_statistics_ST.check_failure_corrected(self.logs)


class TestFindListValidForMinimum(unittest.TestCase):
    """The boundary is the first run with at least one uncorrected failure."""

    def test_first_nonempty_run(self):
        self.assertEqual(final_run_statistics_ST.find_list_valid_for_minimum(
            {0: [], 1: [], 2: ['f1'], 3: ['f1']}), 2)

    def test_all_runs_corrected(self):
        self.assertEqual(final_run_statistics_ST.find_list_valid_for_minimum(
            {0: [], 1: [], 2: []}), 3)

    def test_failure_on_first_run(self):
        self.assertEqual(final_run_statistics_ST.find_list_valid_for_minimum(
            {0: ['f1'], 1: []}), 0)

    def test_empty_results(self):
        self.assertEqual(final_run_statistics_ST.find_list_valid_for_minimum({}), 0)

    def test_first_nonempty_is_selected_not_most_failures(self):
        self.assertEqual(final_run_statistics_ST.find_list_valid_for_minimum(
            {0: [], 1: ['f1'], 2: ['f1', 'f2']}), 1)


class TestFailureRange(unittest.TestCase):
    """Ensure consecutive invalid run blocks are grouped by failure list."""

    def test_empty_dict_produces_no_ranges(self):
        self.assertEqual(final_run_statistics_ST.failure_range({}), [])

    def test_all_corrected_produces_no_ranges(self):
        self.assertEqual(final_run_statistics_ST.failure_range({0: [], 1: [], 2: []}), [])

    def test_consecutive_same_failures_create_one_range(self):
        self.assertEqual(final_run_statistics_ST.failure_range(
            {0: [], 1: ['f1'], 2: ['f1'], 3: ['f1']}),
            [(1, 3, ['f1'])])

    def test_different_failure_sets_split_ranges(self):
        actual = final_run_statistics_ST.failure_range({
            0: ['f1'], 1: ['f1'], 2: ['f2'], 3: ['f1', 'f2'],
        })
        self.assertEqual(actual, [
            (0, 1, ['f1']), (2, 2, ['f2']), (3, 3, ['f1', 'f2'])
        ])

    def test_corrected_run_interrupts_an_invalid_range(self):
        actual = final_run_statistics_ST.failure_range({
            0: ['f1'], 1: [], 2: ['f1'], 3: ['f1'], 4: []
        })
        self.assertEqual(actual, [(0, 0, ['f1']), (2, 3, ['f1'])])

    def test_single_invalid_run_at_end(self):
        self.assertEqual(final_run_statistics_ST.failure_range(
            {0: [], 1: [], 2: ['f2']}), [(2, 2, ['f2'])])

    def test_one_run_invalid(self):
        self.assertEqual(final_run_statistics_ST.failure_range({0: ['f1']}),
                         [(0, 0, ['f1'])])

    def test_failure_list_order_is_significant_in_current_implementation(self):
        actual = final_run_statistics_ST.failure_range({0: ['f1', 'f2'], 1: ['f2', 'f1']})
        self.assertEqual(actual, [(0, 0, ['f1', 'f2']), (1, 1, ['f2', 'f1'])])

    def test_does_not_modify_input(self):
        original = {0: ['a'], 1: ['a'], 2: [], 3: ['b']}
        before = deepcopy(original)
        final_run_statistics_ST.failure_range(original)
        self.assertEqual(original, before)


class TestReturnStatisticsFailureBoundaries(unittest.TestCase):
    """Integrated tests for forwarding validity metadata to both graph functions."""

    setUp = TestReturnStatisticsRunsST.setUp
    _run = TestReturnStatisticsRunsST._run
    _assert_no_graphs = TestReturnStatisticsRunsST._assert_no_graphs

    def test_all_corrected_runs_have_empty_failure_ranges(self):
        self.results.dfs_log_events_merged = make_log_results()
        self.results.dfs_log_events_merged[2] = self.results.dfs_log_events_merged[1].copy()
        self._run()
        self.assertEqual(self.mock_cost_plot.call_args.kwargs['failure_not_corrected_idx'], 3)
        self.assertEqual(self.mock_cost_plot.call_args.kwargs['failure_ranges'], [])
        self.assertEqual(self.mock_energy_plot.call_args.kwargs['failure_ranges'], [])

    def test_first_run_invalid_has_boundary_zero(self):
        logs = make_log_results()
        logs[0] = logs[0].query("event != 'tow'").copy()
        self.results.dfs_log_events_merged = logs
        self._run()
        self.assertEqual(self.mock_cost_plot.call_args.kwargs['failure_not_corrected_idx'], 0)
        self.assertEqual(self.mock_cost_plot.call_args.kwargs['failure_ranges'], [
            (0, 0, ['ofw_fail_b']), (2, 2, ['ofw_fail_b'])
        ])

    def test_both_graphs_receive_identical_failure_metadata(self):
        self._run()
        for key in ('failure_ranges', 'failure_not_corrected_idx'):
            self.assertEqual(self.mock_cost_plot.call_args.kwargs[key],
                             self.mock_energy_plot.call_args.kwargs[key])

    def test_missing_log_dataframe_raises_before_plotting(self):
        self.results.dfs_log_events_merged = []
        with self.assertRaises(IndexError):
            self._run()
        self._assert_no_graphs()

    def test_merged_operations_are_used_during_full_aggregation(self):
        self.results.dfs_log_events_merged[2] = pd.DataFrame([
            {'event': 'operation_merged', 'id': 'combined', 'comments': 'merged_work'}
        ])
        with patch.object(final_run_statistics_ST, 'get_first_failure', return_value=[
            'operation_ofw_fail_a', 'operation_ofw_fail_b'
        ]) as parser:
            self._run()
        parser.assert_called_once_with('merged_work', first=False)
        self.assertEqual(self.mock_cost_plot.call_args.kwargs['failure_ranges'], [])
        self.assertEqual(self.mock_cost_plot.call_args.kwargs['failure_not_corrected_idx'], 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
