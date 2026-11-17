import pandas as pd
from copy import deepcopy

from oriom.utils.aux_functions import save_file_csv
from oriom.core.functions.graphs import final_economic_graphs, report_graphs
from oriom.core.statistical_analysis import final_run_statistics


def graphs_simulation_creation(
    Config: object,
    inputs: object,
    find_element: object,
    dates_failures: pd.DataFrame,
    kpi_total_timeseries: pd.DataFrame,
    kpi_yearly_timeseries: pd.DataFrame,
    graph_dir_r: str,
):
    """ Creation of single simulation graph"""
    if not dates_failures.empty:
        report_graphs.distribution_failures(df = dates_failures, save_dir = graph_dir_r)

    costs = final_run_statistics.create_costs_data(
        lists_costs_tot = [kpi_total_timeseries],
        fuel_add = Config.FUEL_TO_ADD,
        mobilisation_add = Config.MOBILISATION_TO_ADD,
        n_lifetime = inputs.stats.lifetime["value"]
    )
                
    df_cost = pd.DataFrame.from_dict(costs, orient='index').rename_axis('cost_type').rename(columns={0: 'values'}).reset_index()
    df_cost_yearly = deepcopy(df_cost)
    
    df_cost_yearly['values'] /= inputs.stats.lifetime["value"]
    # Create graphs
    report_graphs.lifetime_cost(df = df_cost, title = 'Lifetime costs' if not Config.ST else 'Direct costs', save_dir = graph_dir_r)
    if not Config.ST:
        report_graphs.lifetime_cost(df = df_cost_yearly, title = 'Yearly costs', save_dir = graph_dir_r)
    
    array_stack, all_index, all_columns = final_run_statistics.safe_stack([kpi_yearly_timeseries])
    percentile_arrays = final_run_statistics.calculate_statistics(array_stack, axis=0, ignore_nan=True)

    
    df_cost_yearly_dict = final_run_statistics.create_vessel_cost(
        percentile_arrays = percentile_arrays,
        fuel_add = Config.FUEL_TO_ADD,
        mobilisation_add = Config.MOBILISATION_TO_ADD,
        all_index = all_index,
        all_columns = all_columns
    )


    final_economic_graphs.yearly_vessel_cost(
        df = df_cost_yearly_dict['AVG'],
        title = 'Yearly Vessels costs' if not Config.ST else 'Vessels costs',
        find_element_class = find_element,
        save_dir = graph_dir_r
    )
    
    
def availability_graph_manager(inputs, results_dict, availability_total, result_dir_r, graph_dir_r):
    """ Manage the availability graphs creation and save the results in the results dictionary"""
    combined = {}

    for k, df in availability_total.items():
        if df.empty is False:
            name = k
            save_file_csv(df,result_dir_r,name +'.csv')

            if 'month' in name:
                results_dict.dfs_energy_yearly_month_dict[k].append(df)
                combined.update({k:df})
                report_graphs.energy_yield(df = df, name_file = name[18:], save_dir = graph_dir_r)

            elif 'year' in name:
                results_dict.dfs_energy_yearly_dict[k].append(df)
                if 'pv' in k:
                    electricity_cost_tech = inputs.cost.electricity_price_dict['pv']
                elif 'wind' in k:
                    electricity_cost_tech = inputs.cost.electricity_price_dict['wt']
                elif 'wave' in k:
                    electricity_cost_tech = inputs.cost.electricity_price_dict['wec']
                report_graphs.farm_availability(df_ = df, name_file = name[17:], save_dir = graph_dir_r)
                report_graphs.indirect_costs_per_year(df = df, electricity_price = electricity_cost_tech, name_file = name[17:], save_dir = graph_dir_r)

    if len(combined.keys())>1:
        report_graphs.energy_yield_combined(dfs = combined, save_dir = graph_dir_r)
