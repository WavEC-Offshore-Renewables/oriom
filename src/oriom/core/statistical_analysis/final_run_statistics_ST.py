import os
import pandas as pd
import logging
import shutil

from oriom.core.functions.graphs.ST_visualization import final_stat_graph_ST, plot_energy_losses_ST
from oriom.utils.read_dataframe_value import get_first_failure

FILTER_OP_MERGED = ['operation_deferred_merged', 'operation_merged']
FILTER_OP = ['operation', 'tow']


def check_failure_corrected(
    dfs_log_events_merged: list,
)-> dict[int, list[str]]:
    
    failure_not_corrected = {}

    # Initial failures from the first dataframe
    initial_failures = dfs_log_events_merged[0].loc[dfs_log_events_merged[0]['event'] == 'failure', 'id'].tolist()

    for i, df in enumerate(dfs_log_events_merged):
        # Get all operation IDs
        operation_events = df.loc[df['event'].isin(FILTER_OP), 'comments']
        corrected_ids = set(operation_events.dropna())

        # Get failure IDs referenced in merged-operation comments
        merged_comments = df.loc[df['event'].isin(FILTER_OP_MERGED), 'comments']

        for failures in merged_comments.map(lambda x: get_first_failure(x, first=False)):
            if isinstance(failures, str):
                corrected_ids.add(failures)
            else:
                corrected_ids.update(failures)

        corrected_ids = {failure_id.split('_', 1)[1] for failure_id in corrected_ids if isinstance(failure_id, str)}
        # Identify failures that have not been corrected
        failure_not_corrected[i] = [failure for failure in initial_failures if failure not in corrected_ids]

    return failure_not_corrected


def find_list_valid_for_minimum(failure_not_corrected:dict):
    return next((i for i, failures in failure_not_corrected.items() if failures), len(failure_not_corrected))
    

def failure_range(
    failure_not_corrected: dict[int, list[str]]
)-> list[tuple[int, int, list[str]]]:
    """
    This function identifies the ranges of consecutive runs with the same failures.

    Args:
        failure_not_corrected (dict): A dictionary where keys are run indices and values are lists of failures not corrected in that run.

    Returns:
        list: A list of tuples, each containing the start index, end index, and the list of failures for that range.
    """
    failure_ranges = []
    start_idx = None
    previous_failures = None

    for idx, failures in failure_not_corrected.items():
        if not failures:
            if start_idx is not None:
                failure_ranges.append((start_idx, idx - 1, previous_failures))
                start_idx = None
                previous_failures = None
            continue

        if failures != previous_failures:
            if start_idx is not None:
                failure_ranges.append((start_idx, idx - 1, previous_failures))

            start_idx = idx
            previous_failures = failures

    if start_idx is not None:
        failure_ranges.append((
            start_idx,
            list(failure_not_corrected.keys())[-1],
            previous_failures
        ))
        
    return failure_ranges


def total_energy_losses_finder(
    dfs_energy_yearly_dict: dict,
    n_runs: int,
    var: str
):
    """ Find the total energy losses along each run"""

    total_energy_losses = {i:0 for i in range(n_runs)}
    for name in ['Availability_year_wind', 'Availability_year_wave', 'Availability_year_pv']:
        for i, df in enumerate(dfs_energy_yearly_dict[name]):
            total_energy_losses[i] += df[var].sum()
        
    return total_energy_losses


def total_cost_finder(
    dfs_cost_list: list,
    n_runs: int
):
    """ Find the total costs along each run"""

    total_costs = {i: 0.0 for i in range(n_runs)}
    for i, df_cost in enumerate(dfs_cost_list):
        total_costs[i] = df_cost.loc[df_cost['vessel_id'] == 'total','lifetime_direct_costs'].iloc[0]
        
    return total_costs


def return_statistics_runs_ST(
    results_dict: object,
    n_runs: int,
    metocean_df: pd.DataFrame,
    dir_result: str,
    save_dir: str = None
):
    
    # Obtain the total results for each run
    total_costs = total_cost_finder(dfs_cost_list = results_dict.dfs_tot_cost_list, n_runs = n_runs)
    
    if results_dict.dfs_energy_yearly_dict:
        total_energy_losses_costs = total_energy_losses_finder(
            dfs_energy_yearly_dict = results_dict.dfs_energy_yearly_dict,
            n_runs = n_runs,
            var = 'energy_loss_Meur'
        )
        total_energy_losses = total_energy_losses_finder(
            dfs_energy_yearly_dict = results_dict.dfs_energy_yearly_dict,
            n_runs = n_runs,
            var = 'En_loss_kWh'
        )
    else:
        total_energy_losses_costs = [0]*n_runs
        
    
    # Obtain the failures that have not been corrected along the runs
    failure_not_corrected = check_failure_corrected(dfs_log_events_merged = results_dict.dfs_log_events_merged)
    failure_not_corrected_idx = find_list_valid_for_minimum(failure_not_corrected)
    failure_ranges = failure_range(failure_not_corrected)
    
    # Plot the final results and save the minimum cost run in a separate folder
    minimum_cost_index = final_stat_graph_ST(
        failure_ranges = failure_ranges,
        failure_not_corrected_idx = failure_not_corrected_idx,
        total_costs = total_costs,
        total_energy_losses_costs = total_energy_losses_costs,
        metocean_df = metocean_df,
        save_dir = save_dir
    )
    if any(results_dict.dfs_energy_yearly_dict.values()):
        plot_energy_losses_ST(
            failure_ranges = failure_ranges,
            failure_not_corrected_idx = failure_not_corrected_idx,
            total_energy_losses = total_energy_losses,
            metocean_df = metocean_df,
            save_dir = save_dir
        )
    
    minimum_cost_dir = os.path.join(dir_result,f"{'result_'}{minimum_cost_index}")
    shutil.copytree(minimum_cost_dir, os.path.join(save_dir, 'minimum_cost_run'), dirs_exist_ok=True)
    logging.info(f"Minimum cost of O&M found in run index: {minimum_cost_index}")
    logging.info(f"Recommended to start O&M at date {metocean_df.index[minimum_cost_index]}")

    