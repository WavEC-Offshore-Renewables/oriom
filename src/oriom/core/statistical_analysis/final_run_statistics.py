import os
import pandas as pd
import openpyxl
import logging
from openpyxl.utils.dataframe import dataframe_to_rows
import numpy as np
from copy import deepcopy

from oriom.common.constants import PERCENTILE_DICT
from oriom.utils import aux_functions
from oriom.core.functions.graphs import final_economic_graphs
from oriom.core.functions.graphs import report_graphs
try:
    from oriom.core.functions.private.KPI_Insight import KPI_Insight
except ImportError:
    KPI_Insight = None


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # vessel_id as index
    if "vessel_id" in df.columns:
        df = df.set_index("vessel_id")
    else:
        df = df.set_index(df.columns[0])

    # flatten MultiIndex columns (year, metric)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [(str(a), str(b)) for a, b in df.columns]

    df = df.apply(pd.to_numeric, errors="coerce")

    return df


def safe_stack(dfs_lists):

    dfs = [normalize_df(df) for df in dfs_lists]
    # Global INDEX
    all_index = pd.Index(sorted(set.union(*[set(df.index) for df in dfs])))
    # Global col
    all_columns = pd.Index(sorted(set.union(*[set(df.columns) for df in dfs])))
    # ALIGN + FILL ZEROS
    aligned = [df.reindex(index=all_index, columns=all_columns).fillna(0)for df in dfs]
    # STACK
    stack = np.stack([df.to_numpy(dtype=float) for df in aligned], axis=0)

    return stack, all_index, all_columns


def compute_mean(dfs_lists):

    stack, idx, cols = safe_stack(dfs_lists)
    mean = np.mean(stack, axis=0)
    df_out = pd.DataFrame(mean, index=idx, columns=cols)

    return df_out.reset_index().rename(columns={"index": "vessel_id"})


def calculate_statistics(values, axis=None, ignore_nan=False):
    mean_func = np.nanmean if ignore_nan else np.mean
    percentile_func = np.nanpercentile if ignore_nan else np.percentile

    return {
        stat: (mean_func(values, axis=axis) if percentile == '' else percentile_func(values, percentile, axis=axis))
        for stat, percentile in PERCENTILE_DICT.items()
    }
    
def prepare_statistics_sheets(wb): 
    sheets = {}
    for i, stat in enumerate(PERCENTILE_DICT):
        ws = wb.active if i == 0 else wb.create_sheet()
        ws.title = stat
        sheets[stat] = ws
        
    return sheets
    
def append_df_to_sheet(ws, name, df):
    ws.append([name])
    for row in dataframe_to_rows(df, index=False, header=True):
        ws.append(row)
        ws.append([])

def calculate_df_statistics(dfs):
    dfs = [df.astype(float) for df in dfs if not df.empty]
    if not dfs: return {}
    df_concat = pd.concat(dfs, keys=range(len(dfs)))
    grouped = df_concat.groupby(level=1)
    
    return {stat: 
        (grouped.mean() if percentile == '' else grouped.quantile(percentile / 100)).reset_index(drop=True)
        for stat, percentile in PERCENTILE_DICT.items()
    }


def return_statistics_runs(
        n_lifetime: int,
        find_element_class: dict,
        results_dict: object,
        fuel_add: dict,
        mobilisation_add: dict,
        electricity_cost_dict: dict,
        n_runs: int,
        vessels: list,
        operations_total: list,
        recycled: bool = False,
        save_dir: str = None
    ):

    """
    Create averaged data for each simulation. Consider yearly costs, total costs and ctv costs strategy.

    Save all resutls in sheets of excels file and create graphs

    Args:
        n_lifetime (int): number of year of lifetime,
        find_element_class (Find_Element): Initialized instance that provides fast access to operations, vessels and failures via internal dictionaries.
        results_dict (object): Object of class `Results`
        fuel_add (dict): dictionary of vessel_type and fuel yearly cost to add
        mobilisation_add (dict): dictionary of vessel_type and mobilisation yearly cost to add
        electricity_cost_dict: (dict): jey of tech and value cost of electricity per kWh
        n_runs (int): number of simulations
        vessels (list): List of object with attribute `id` for class `Vessels`
        operations_total (list): List of object for all the classes `Operations`
        save_dir (str, optional): directory to averaged results. Defaults to None.
    """


    def restructure_df_year(kpi_om_year_final: pd.DataFrame) -> pd.DataFrame:
        """
        Create a MultiIndex for yearly KPIs from columns like '1990', '1990.1', etc.
        """
        def parse_column(col):
            if '.' in col:
                year, suffix = col.split('.')
                metric = 'n_days'
            else:
                year = col
                metric = 'direct_costs'
            return (int(year), metric)

        vessel_ids = kpi_om_year_final['vessel_id']
        data = kpi_om_year_final.drop(columns='vessel_id')
        data = data.iloc[1:]
        data.reset_index(drop=True)

        multi_cols = pd.MultiIndex.from_tuples(
            [parse_column(col) for col in data.columns],
            names=['year', 'metric']
        )

        data.columns = multi_cols
        data = data.sort_index(axis=1, level=0)
        data.insert(0, 'vessel_id', vessel_ids)

        return data

    wb_resume = openpyxl.Workbook()
    wb_Y_cost = openpyxl.Workbook()
    wb_V_fuel = openpyxl.Workbook()
    wb_E_month = openpyxl.Workbook()
    wb_E_year = openpyxl.Workbook()

    ws = wb_resume.active
    
    ws.title = "Lifetime_results"
    
    # Lifetime costs
    #--------------------
    lifetime_fixed_port_cost, lifetime_technician_cost , lifetime_vessels_cost, lifetime_rov_cost, lifetime_other_cost  = [], [], [], [], []
    lifetime_repair_cost, lifetime_fixed_tech_cost,  lifetime_mobilisation_cost, lifetime_fixed_insurance_cost  = [], [], [], []
    final_cost, final_energy = {}, {}

    # Extrapolate all cost found in the simulations
    for kpi_tot_sim in results_dict.dfs_tot_cost_list:
        kpi_tot = kpi_tot_sim.iloc[-1]
        kpi_tot_sim = kpi_tot_sim.iloc[:-1]
        kpi_tot_sim['lifetime_direct_costs'] = kpi_tot_sim['lifetime_direct_costs'].astype(float)
        fuel_to_add = sum(fuel_add.values())
        mobilisation_to_add = sum(mobilisation_add.values())

        lifetime_fixed_insurance_cost.append(kpi_tot_sim.loc[kpi_tot_sim['vessel_id'] == 'insurance', 'lifetime_direct_costs'].values[0])
        lifetime_fixed_port_cost.append(kpi_tot_sim.loc[kpi_tot_sim['vessel_id'] == 'port', 'lifetime_direct_costs'].values[0])
        lifetime_fixed_tech_cost.append(kpi_tot_sim.loc[kpi_tot_sim['vessel_id'] == 'technician', 'lifetime_direct_costs'].values[0])
        lifetime_technician_cost.append(kpi_tot['tot_technicians_costs'])
        lifetime_vessels_cost.append(kpi_tot['tot_vessel_costs'] + n_lifetime * fuel_to_add)
        lifetime_mobilisation_cost.append(kpi_tot['tot_mobilization_costs'] + n_lifetime * mobilisation_to_add)
        lifetime_rov_cost.append(kpi_tot['tot_rov_costs'])
        lifetime_repair_cost.append(kpi_tot['tot_part_costs'])
        lifetime_other_cost.append(kpi_tot['tot_other_costs'])

    # Create a dataframe with P10, avg and P90 costs
    costs = {
        'lifetime_vessels_cost €': lifetime_vessels_cost,
        'lifetime_mobilisation_cost €': lifetime_mobilisation_cost,
        'lifetime_rov_cost €': lifetime_rov_cost,
        'lifetime_technician_cost €': lifetime_technician_cost,
        'lifetime_repair_cost €': lifetime_repair_cost,
        'lifetime_other_cost €': lifetime_other_cost,
        'lifetime_fixed_port_cost €': lifetime_fixed_port_cost,
        'lifetime_fixed_tech_cost €': lifetime_fixed_tech_cost,
        'lifetime_fixed_insurance_cost €': lifetime_fixed_insurance_cost,
    }
    
    dict_cost = {name: calculate_statistics(values) for name, values in costs.items()}
    df_cost = pd.DataFrame.from_dict(dict_cost, orient='index').rename_axis('cost_type').reset_index()
    df_cost_yearly = deepcopy(df_cost)
    
    for aggregation in PERCENTILE_DICT:
        final_cost[f'lifetime_direct_cost_{aggregation}'] = df_cost[aggregation].sum()
        final_cost[f'yearly_direct_cost_{aggregation}'] = (final_cost[f'lifetime_direct_cost_{aggregation}'] / n_lifetime)
        df_cost_yearly[aggregation] /= n_lifetime
        
    # Create graphs
    final_economic_graphs.lifetime_cost(df = df_cost, title = 'Lifetime costs', save_dir = save_dir, file_name='lifetime cost')
    final_economic_graphs.lifetime_cost(df = df_cost_yearly, title = 'Yearly costs', save_dir = save_dir, file_name='yearly cost')

    # Add a single total row after calculating all statistics
    df_cost.loc[len(df_cost)] = {'cost_type': 'lifetime_direct_cost',
        **{aggregation: df_cost[aggregation].sum()for aggregation in PERCENTILE_DICT}
    }

    ws2 = wb_resume.create_sheet(title="Lifetime_costs")
    for row in dataframe_to_rows(df_cost, index=False, header=True):
        ws2.append(row)
        
    # Yearly costs
    #--------------------
    # If read from excel file need to create multiindex
    if recycled:
        for i in range(len(results_dict.dfs_tot_yearly_cost_list)):
            results_dict.dfs_tot_yearly_cost_list[i] = restructure_df_year(results_dict.dfs_tot_yearly_cost_list[i])
    
    array_stack, all_index, all_columns = safe_stack(results_dict.dfs_tot_yearly_cost_list)
    # Evaluate the average, P10 and P90 for each cell
    percentile_arrays = calculate_statistics(array_stack, axis=0, ignore_nan=True)
    # Reconstruct one DataFrame for each statistic
    df_cost_yearly_dict = {}

    for stat, values in percentile_arrays.items():
        df = pd.DataFrame(values, index=all_index, columns=all_columns)
        df = df.reset_index().rename(columns={"index": "vessel_id"})

        # Add fuel and mobilisation costs to direct costs
        years = sorted(set(col[0] for col in df.columns if isinstance(col, tuple) and col[1] == 'direct_costs'))

        for ves, addition in fuel_add.items():
            for year in years:
                col_key = (year, 'direct_costs')
                if col_key in df.columns:
                    mask = df['vessel_id'] == ves
                    df.loc[mask, col_key] += addition

        for ves, addition in mobilisation_add.items():
            for year in years:
                col_key = (year, 'direct_costs')
                if col_key in df.columns:
                    mask = df['vessel_id'] == ves
                    df.loc[mask, col_key] += addition

        df_cost_yearly_dict[stat] = df

    # Export all three statistics to separate Excel sheets
    for stat, df in df_cost_yearly_dict.items():
        ws_Y_cost = wb_Y_cost.create_sheet(title=f"Yearly_costs_{stat}")
        for row in dataframe_to_rows(df, index=False, header=True):
            ws_Y_cost.append(row)

    final_economic_graphs.yearly_vessel_cost(df = df_cost_yearly_dict['AVG'], title = 'Yearly costs', find_element_class = find_element_class, save_dir = save_dir)

    # Average cost ctv
    #--------------------
    for dfs, sheet_prefix in [
        (results_dict.dfs_ctv_list, "CTV_yearly_strategy"),
        (results_dict.dfs_vessel_fuel_usage, "Vessel_fuel_usage"),
    ]:
        # Avoid if no data
        if not dfs or not any(not df.empty for df in dfs):
            continue

        dfs = [df for df in dfs if not df.empty]
        df_concat = pd.concat(dfs, keys=range(len(dfs)))

        # Create statistical results
        df_stat_dict_CTV = {}
        for stat, percentile in PERCENTILE_DICT.items():
            grouped = df_concat.groupby(level=1)
            df_stat = (grouped.mean() if percentile == '' else grouped.quantile(percentile / 100))

            if sheet_prefix == "CTV_yearly_strategy":
                df_stat.insert(0, 'n_vessel', range(len(df_stat)))
                df_stat_dict_CTV[percentile] = df_stat

            ws_V_guel = wb_V_fuel.create_sheet(title=f"{sheet_prefix}_{stat}")
            for row in dataframe_to_rows(df_stat, index=False, header=True):
                ws_V_guel.append(row)

        if sheet_prefix == "CTV_yearly_strategy":
            final_economic_graphs.plot_ctv_annual_chart_strategy(df_ctv=df_stat_dict_CTV, save_dir=save_dir)
            
    # Average type cost
    if results_dict.kpi_om_type_cost_list:
        kpi_om_type_cost_concat = pd.concat(results_dict.kpi_om_type_cost_list)
        kpi_om_type_avg = kpi_om_type_cost_concat.groupby('description', as_index=False)['values'].mean()
        final_economic_graphs.pie_chart(
            df = kpi_om_type_avg,
            description = 'description',
            value = 'values',
            title = 'Lifetime Inspections vs Corrections costs',
            tot_in_title = True,
            title_unit = 'M€',
            coefficient_number = 1e6,
            legend_title = 'Operation type',
            legend_bbox_to_anchor = (1.05, 0.9),
            text = 'mobilisation cost not included',
            save_dir = save_dir,
            file_name_save = 'O&M type cost'
        )

    # Availability year and year_month
    #--------------------  
    # YEARLY
    sheets_year = prepare_statistics_sheets(wb_E_year)
    sheets_month = prepare_statistics_sheets(wb_E_month)
    final_cost['AEP_kWh'] = 0
    final_cost['En_loss_€'] = 0
    final_cost['En_loss_kWh'] = 0
    yearly_stats = {}
    for k, dfs in results_dict.dfs_energy_yearly_dict.items():
        if not dfs or not any(not df.empty for df in dfs):
            continue

        stats = calculate_df_statistics(dfs)
        yearly_stats[k] = stats

        for stat, df_yearly in stats.items():
            append_df_to_sheet(sheets_year[stat], k, df_yearly)

        # Graphs: AVG bars with P10-P90 error bars
        report_graphs.farm_availability(df_=stats, name_file=k[17:], save_dir=save_dir)

        if 'pv' in k:
            electricity_cost_tech = electricity_cost_dict['pv']
            tech = 'pv'
        elif 'wind' in k:
            electricity_cost_tech = electricity_cost_dict['wt']
            tech = 'wind'
        elif 'wave' in k:
            electricity_cost_tech = electricity_cost_dict['wec']
            tech = 'wave'
        else:
            continue

        # Calculate energy/economic indicators separately for each statistic
        for stat, df_yearly in stats.items():
            final_energy[f'{tech}_En_max_kWh_{stat}'] = df_yearly['En_max_kWh'].sum()
            final_energy[f'{tech}_En_loss_kWh_{stat}'] = df_yearly['En_loss_kWh'].sum()
            final_energy[f'{tech}_En_loss_€_{stat}'] = (final_energy[f'{tech}_En_loss_kWh_{stat}'] * electricity_cost_tech / 1e3)
            final_energy[f'{tech}_En_produced_kWh_{stat}'] = (final_energy[f'{tech}_En_max_kWh_{stat}'] - final_energy[f'{tech}_En_loss_kWh_{stat}'])
            final_energy[f'{tech}_AEP_kWh_{stat}'] = (final_energy[f'{tech}_En_produced_kWh_{stat}'] / n_lifetime)

            final_cost[f'AEP_kWh_{stat}'] = (final_cost.get(f'AEP_kWh_{stat}', 0) + final_energy[f'{tech}_AEP_kWh_{stat}'])
            final_cost[f'En_loss_€_{stat}'] = (final_cost.get(f'En_loss_€_{stat}', 0) + final_energy[f'{tech}_En_loss_€_{stat}'])
            final_cost[f'En_loss_kWh_{stat}'] = (final_cost.get(f'En_loss_kWh_{stat}', 0) + final_energy[f'{tech}_En_loss_kWh_{stat}'])

        report_graphs.indirect_costs_per_year(
            df=stats['AVG'],
            df_p10=stats['P10'],
            df_p90=stats['P90'],
            electricity_price=electricity_cost_tech,
            name_file=k[17:],
            save_dir=save_dir
        )

    # MONTHLY
    combined = {}

    for k, dfs in results_dict.dfs_energy_yearly_month_dict.items():
        if not dfs or not any(not df.empty for df in dfs):
            continue

        stats = calculate_df_statistics(dfs)
        for stat, df_monthly in stats.items():
            append_df_to_sheet(sheets_month[stat], k, df_monthly)

        # Keep the average DataFrames for the combined graph
        combined[k] = stats['AVG']
        report_graphs.energy_yield(df=stats['AVG'],name_file=k[18:],save_dir=save_dir)

    if len(combined) > 1:
        report_graphs.energy_yield_combined(dfs=combined,save_dir=save_dir)
    
    # KPI_Insight
    #--------------------  
    if KPI_Insight is not None:
        # Add insights from log events
        run_insight = KPI_Insight(N_SIMULATION = n_runs, n_lifetime = n_lifetime)
        cost_insight, vessel_insight = run_insight.kpi_insight(results_dict = results_dict, vessels = vessels, operations_total = operations_total)

        if not vessel_insight.empty and "ctv" in vessel_insight.index:
            final_cost['reuse_ctv'] = vessel_insight.loc["ctv", "reuse %"]
            final_cost['merge_ctv'] = vessel_insight.loc["ctv", "merge %"]
            final_cost['ctv_effective_day_y'] = vessel_insight.loc["ctv", "yearly day effective"]
    else:
        cost_insight = pd.DataFrame()
        vessel_insight = pd.DataFrame()

    for df_, ws_use in zip([final_cost, final_energy], [ws, wb_resume.create_sheet(title="Energy_results")]):
        if df_:
            df_save = pd.DataFrame([
                {
                    'Descriptions': key.rsplit('_', 1)[0],
                    'P10': df_.get(f'{key.rsplit("_", 1)[0]}_P10'),
                    'AVG': df_.get(f'{key.rsplit("_", 1)[0]}_AVG'),
                    'P90': df_.get(f'{key.rsplit("_", 1)[0]}_P90'),
                } for key in df_ if key.endswith('_P10')]
            )
            for row in dataframe_to_rows(df_save, index=False, header=True):
                ws_use.append(row)

    # SAVE RESULTS
    #--------------------  
    for wb_, ws_, file_name in zip(
        [wb_resume, wb_Y_cost, wb_V_fuel, wb_E_month, wb_E_year],
        [ws, None, None, None, None],
        ["Average_results.xlsx", "Yearly_costs.xlsx", "Fuel_vessel_use.xlsx", "Availability_month_wind.xlsx", "Availability_year_wind.xlsx"]
    ):
        if ws_ is not None:
            wb_._sheets = [ws_] + [s for s in wb_._sheets if s != ws_]
        else:
            # Remove empty default sheets if other sheets contain data.
            for sheet in wb_._sheets[:]:
                if sheet.max_row == 1 and sheet.max_column == 1 and sheet['A1'].value is None:
                    if len(wb_._sheets) > 1:
                        wb_._sheets.remove(sheet)

        wb_.save(os.path.join(save_dir, file_name))


    if (KPI_Insight is not None and
        (vessel_insight is not None and not vessel_insight.empty)
        or (cost_insight is not None and not cost_insight.empty)
    ):
        with pd.ExcelWriter(os.path.join(save_dir, 'KPI_insight.xlsx'),engine='openpyxl') as writer:
            v_ins, c_ins = False, False
            if not vessel_insight.empty:
                vessel_insight.to_excel(writer, sheet_name='KPI_vessel_use', index=True)
                v_ins = True
            if not cost_insight.empty:
                cost_insight.to_excel(writer, sheet_name='KPI_failure_contribution', index=True)
                c_ins = True

            if v_ins or c_ins:
                worksheet = writer.sheets['KPI_failure_contribution']
            if c_ins:
                # Write notes
                worksheet.cell(row=len(cost_insight)+3, column=1, value="The failure contribution is made evaluating for each failure the FR*devices")
                worksheet.cell(row=len(cost_insight)+4, column=1, value="This show the failure per year that occur in the farm and they are correlated with the vessel_type")
                worksheet.cell(row=len(cost_insight)+4, column=1, value="All the values must be multiplied for the number found only once in the vessels type")