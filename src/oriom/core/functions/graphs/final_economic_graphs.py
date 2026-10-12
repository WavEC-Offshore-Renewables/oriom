import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

from oriom.common.constants import COLORS_GRAPH


def plot_ctv_annual_chart_strategy(df_ctv: pd.DataFrame, title: str = '', save_dir: str = None):
    """Plot the CTV costs based on the number of vessels for long-term strategy."""

    cost_types = {
        'short_term_cost': ('Short-term cost', 'black', 'o'),
        'long_term_cost': ('Long-term cost', 'b', 's'),
        'tot_cost': ('Total cost', 'r', '^')
    }

    fig, ax = plt.subplots(figsize=(8, 5))

    for col, (label, color, marker) in cost_types.items():
        # AVG data
        if 'AVG' in df_ctv:
            df_avg = df_ctv['AVG']
            ax.plot(df_avg['n_vessel'], df_avg[col] / (1e6 * 30), marker=marker, linestyle='-', color=color, label=f'{label} AVG')

        # P10-P90 data
        for perc in ('P10', 'P90'):
            if perc in df_ctv:
                df_perc = df_ctv[perc]
                ax.plot(df_perc['n_vessel'], df_perc[col] / (1e6 * 30), linestyle='--', color=color, alpha=0.35, label='_nolegend_')

        # Single combined legend entry for P10-P90
        if 'P10' in df_ctv or 'P90' in df_ctv:
            ax.plot([], [], linestyle='--', color=color, alpha=0.6, label=f'{label} P10–P90')

    ax.set_xlabel('Number of vessels')
    ax.set_ylabel('Yearly cost (M€)')
    ax.set_title(f'{title} Yearly CTV cost - Long Term Chart Strategy')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend()
    fig.tight_layout()

    if save_dir:
        fig.savefig(os.path.join(save_dir, 'CTV Long Term Chart strategy.png'), dpi=300, bbox_inches='tight')
    else:
        plt.show()

    plt.close(fig)


def lifetime_cost(
        df: pd.DataFrame,
        title: str,
        file_name: str = 'lifetime_cost',
        save_dir: str = None
    ):
    """Plot lifetime costs as horizontal AVG bars with P10-P90 error bars."""

    colors = COLORS_GRAPH

    df_filtered = df.loc[df['AVG'] != 0, ['cost_type', 'P10', 'AVG', 'P90']].copy()
    df_filtered['cost_type'] = (df_filtered['cost_type'].str.split('€').str[0].str.strip())

    df_filtered = df_filtered.groupby('cost_type', as_index=False)[['P10', 'AVG', 'P90']].sum().sort_values('AVG')

    labels = [label.split('_', 1)[-1].replace('_', ' ') for label in df_filtered['cost_type']]
    values = df_filtered['AVG'].to_numpy(dtype=float)
    p10 = df_filtered['P10'].to_numpy(dtype=float)
    p90 = df_filtered['P90'].to_numpy(dtype=float)

    total = values.sum()
    percentages = values / total * 100 if total else np.zeros_like(values)

    # Asymmetric error bars: AVG - P10 and P90 - AVG.
    xerr = np.maximum(np.vstack([values - p10, p90 - values]),0)

    fig, ax = plt.subplots(figsize=(10, max(5, len(labels) * 0.6)))

    bar_colors = [colors[i % len(colors)] for i in range(len(labels))]
    bars = ax.barh(
        labels,
        values,
        color=bar_colors,
        height=0.7,
        xerr=xerr,
        error_kw={'ecolor': 'black', 'capsize': 4, 'elinewidth': 1.2}
    )

    max_value = max(p90) if len(p90) else 0
    ax.set_xlim(0, max_value * 1.35 if max_value > 0 else 1)

    for bar, value, percentage in zip(bars, values, percentages):
        ax.text(
            bar.get_width() + max_value * 0.015,
            bar.get_y() + (bar.get_height() / 3),
            f'{value:,.0f} € ({percentage:.1f}%)',
            va='center',
            fontsize=11
        )

    ax.set_title(f'{title}: {total / 1e6:.2f} M€', fontsize=16, pad=15)
    ax.set_xlabel('Cost (€)', fontsize=12)
    ax.set_ylabel('Cost type', fontsize=12)
    ax.tick_params(axis='y', labelsize=11)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.spines['bottom'].set_visible(True)

    plt.tight_layout()

    if save_dir:
        plt.savefig(os.path.join(save_dir, f'{file_name}.png'),dpi=300,bbox_inches='tight')
    else:
        plt.show()

    plt.close()


def yearly_vessel_cost(
        df: pd.DataFrame,
        title: str,
        find_element_class: dict,
        save_dir: str = None
    ):
    """Plot yearly vessel costs as horizontal bars."""

    colors = COLORS_GRAPH
    
    # Prepare data
    direct_costs_cols = df.loc[:, df.columns.get_level_values(1) == 'direct_costs']
    avg_direct_costs = direct_costs_cols.mean(axis=1, skipna=True)

    result_df = pd.DataFrame({'cost_type': df[('vessel_id', '')], 'value': avg_direct_costs})

    df_filtered = result_df.loc[(result_df['value'] != 0) & (result_df['cost_type'] != 'fixed_annual_cost')].copy()

    df_filtered['cost_type'] = df_filtered['cost_type'].apply(
        lambda vessel_id: (f"{vessel_id.upper()} - {find_element_class.find_vessel(vessel_id).type.upper()}"
            if vessel_id.lower() != 'oper_port'else 'Port Operation'
        )
    )

    data_aggregated = (df_filtered.groupby('cost_type')['value'].sum().sort_values())
    labels = [label.split('_', 1)[-1].replace('_', ' ') for label in data_aggregated.index]
    values = data_aggregated.values
    total = values.sum()
    percentages = values / total * 100 if total else np.zeros(len(values))

    bar_colors = [colors[i % len(colors)] for i in range(len(labels))]

    fig, ax = plt.subplots(figsize=(10, max(5, len(labels) * 0.6)))
    bars = ax.barh(labels, values, color=bar_colors, height=0.7)
    max_value = max(values) if len(values) else 0
    ax.set_xlim(0, max_value * 1.25 if max_value > 0 else 1)

    for bar, value, percentage in zip(bars, values, percentages):
        ax.text(
            bar.get_width() + max_value * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f'{value:,.0f} € ({percentage:.1f}%)',
            va='center',
            fontsize=11
        )

    ax.set_title(f'{title}: {total / 1e6:.2f} M€', fontsize=16, pad=15)
    ax.set_xlabel('Yearly cost (€)', fontsize=12)
    ax.set_ylabel('Vessel type', fontsize=12)
    ax.tick_params(axis='y', labelsize=11)
    ax.grid(axis='x', linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.spines['bottom'].set_visible(True)
    plt.tight_layout()

    if save_dir:
        plt.savefig(os.path.join(save_dir, 'yearly_vessels_cost.png'), dpi=300, bbox_inches='tight')
    else:
        plt.show()

    plt.close()


def pie_chart(
        df: pd.DataFrame,
        description: str,
        value: str,
        title: str = 'Pie Chart',
        tot_in_title = False,
        title_unit: str = '',
        coefficient_number: float = 1,
        legend_title: str = 'Legend',
        save_dir: str = None,
        file_name_save: str = 'graph.png',
        legend_bbox_to_anchor: tuple = (1, 1),
        text: str = None
    ):

    """   Plot the pie chart graph. Input data must be in dataframe format with two columns

    Args:
        df (pd.DataFrame): Dataframe containing the data to plot.
        description (string): Column name of the data description.
        value (string): Column name of the data value.
        title (string): Title of the pie chart. Defalut to ´´Pie Chart´´,
        tot_in_title (bool): If True, the total value will be included in the title. Default to ´´False´´,
        coefficient_number (float): Coefficient to multiply the total value in the title by. Default to ´´1´´,
        legend_title (string): Title of the legend of the pie chart. Defalut to ´´None´´,
        save_dir (string): Saving directory  Defalut to ´´None´´,
        file_name_save (string): File name on which the graph should be saved Defalut to ´´graph.png´´
        legend_bbox_to_anchor (tuple): Bbox to anchor the legend. Default to ´´(1, 1)´´.
        text (string): String of text to add if needed. Defalut to ´´None´´
    """

    # Plot
    data_aggregated = df.groupby(description)[value].sum()

    labels = data_aggregated.index
    values = data_aggregated.values

    total = values.sum()
    percentages = values / total * 100

    cmap = plt.get_cmap('tab20')
    palette = [cmap(i) for i in range(20)]

    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, _ = ax.pie(values, colors=palette, startangle=90, radius=1.0)
    if tot_in_title:
        ax.set_title(f'{title}: {total/ coefficient_number:.2f} {title_unit}', fontsize=16, pad=20)
    else:
        ax.set_title(f'{title}', fontsize=16, pad=20)
    ax.axis('equal')

    for i, p in enumerate(wedges):
        ang = (p.theta2 - p.theta1)/2. + p.theta1
        x = np.cos(np.deg2rad(ang))
        y = np.sin(np.deg2rad(ang))
        ha = 'left' if x > 0 else 'right'
        offset_x = 1.05 * x
        offset_y = 1.05 * y

        ax.text(offset_x, offset_y,
                f"{percentages[i]:.1f}%",
                ha=ha, va='center', fontsize=14)

        ax.plot([0.9 * x, offset_x], [0.9 * y, offset_y], color='gray', lw=0.8)

    if text:
        fig.text(0.5, 0.05, text, ha='center', fontsize=11)
    ax.legend(wedges, labels, title=legend_title, loc=10, bbox_to_anchor=legend_bbox_to_anchor, fontsize = 13, title_fontsize = 13)

    plt.tight_layout()
    if save_dir:
        plt.savefig(os.path.join(save_dir, file_name_save), dpi=300)
    plt.close()


if __name__ == '__main__':
    df_cost = pd.DataFrame([
        {'cost_type': 'lifetime_vessels_cost €', 'P10': 810.0, 'AVG': 810.0, 'P90': 810.0},
        {'cost_type': 'lifetime_mobilisation_cost €', 'P10': 910.0, 'AVG': 910.0, 'P90': 910.0},
        {'cost_type': 'lifetime_rov_cost €', 'P10': 400.0, 'AVG': 400.0, 'P90': 400.0},
        {'cost_type': 'lifetime_technician_cost €', 'P10': 700.0, 'AVG': 700.0, 'P90': 700.0},
        {'cost_type': 'lifetime_repair_cost €', 'P10': 500.0, 'AVG': 500.0, 'P90': 500.0},
        {'cost_type': 'lifetime_other_cost €', 'P10': 0.0, 'AVG': 0.0, 'P90': 0.0},
        {'cost_type': 'lifetime_fixed_port_cost €', 'P10': 2000.0, 'AVG': 2000.0, 'P90': 2000.0},
        {'cost_type': 'lifetime_fixed_tech_cost €', 'P10': 3000.0, 'AVG': 3000.0, 'P90': 3000.0},
        {'cost_type': 'lifetime_fixed_insurance_cost €', 'P10': 1000.0, 'AVG': 1000.0, 'P90': 1000.0},
        {'cost_type': 'lifetime_direct_cost', 'P10': 9320.0, 'AVG': 9320.0, 'P90': 9320.0},
    ])

    df_cost_yearly = pd.DataFrame([
        {'cost_type': 'lifetime_vessels_cost €', 'P10': 405.0, 'AVG': 405.0, 'P90': 405.0},
        {'cost_type': 'lifetime_mobilisation_cost €', 'P10': 455.0, 'AVG': 455.0, 'P90': 455.0},
        {'cost_type': 'lifetime_rov_cost €', 'P10': 200.0, 'AVG': 200.0, 'P90': 200.0},
        {'cost_type': 'lifetime_technician_cost €', 'P10': 350.0, 'AVG': 350.0, 'P90': 350.0},
        {'cost_type': 'lifetime_repair_cost €', 'P10': 250.0, 'AVG': 250.0, 'P90': 250.0},
        {'cost_type': 'lifetime_other_cost €', 'P10': 0.0, 'AVG': 0.0, 'P90': 0.0},
        {'cost_type': 'lifetime_fixed_port_cost €', 'P10': 1000.0, 'AVG': 1000.0, 'P90': 1000.0},
        {'cost_type': 'lifetime_fixed_tech_cost €', 'P10': 1500.0, 'AVG': 1500.0, 'P90': 1500.0},
        {'cost_type': 'lifetime_fixed_insurance_cost €', 'P10': 500.0, 'AVG': 500.0, 'P90': 500.0},
    ])

        # Create graphs
    lifetime_cost(df = df_cost, title = 'Lifetime costs')
    lifetime_cost(df = df_cost_yearly, title = 'Yearly costs')
    
    
    df_ctv = {
        'P10': pd.DataFrame({
            'n_vessel': [1, 2, 3],
            'short_term_cost': [100000, 90000, 80000],
            'long_term_cost': [200000, 180000, 160000],
            'tot_cost': [300000, 270000, 240000],
        }),
        'AVG': pd.DataFrame({
            'n_vessel': [1, 2, 3],
            'short_term_cost': [120000, 110000, 100000],
            'long_term_cost': [220000, 200000, 180000],
            'tot_cost': [340000, 310000, 280000],
        }),
        'P90': pd.DataFrame({
            'n_vessel': [1, 2, 3],
            'short_term_cost': [140000, 130000, 120000],
            'long_term_cost': [240000, 220000, 200000],
            'tot_cost': [380000, 350000, 320000],
        }),
    }
    
    plot_ctv_annual_chart_strategy(df_ctv)
