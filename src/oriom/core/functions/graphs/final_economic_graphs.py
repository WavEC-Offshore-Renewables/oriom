import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os


def plot_ctv_annual_chart_strategy(df_ctv: pd.DataFrame, title: str = '', save_dir: str = None):

    """   Plot the CTV costs based on the number of vessels for long term strategy  """

    # Plot
    plt.figure(figsize=(8, 5))
    df_ctv["short_term_cost_million"] = df_ctv["short_term_cost"] / (1e6*30)
    df_ctv["long_term_cost_million"] = df_ctv["long_term_cost"] / (1e6*30)
    df_ctv["tot_cost_million"] = df_ctv["tot_cost"] / (1e6*30)

    plt.plot(df_ctv["n_vessel"], df_ctv["short_term_cost_million"], marker='o', label="Short-term cost",color='black')
    plt.plot(df_ctv["n_vessel"], df_ctv["long_term_cost_million"], marker='s', label="Long-term cost",color='b')
    plt.plot(df_ctv["n_vessel"], df_ctv["tot_cost_million"], marker='^', label="Total cost",color='r')

    plt.xlabel("Number of vessels")
    plt.ylabel("Cost (M€)")
    plt.title(f"{title} Yearly CTV cost - Long Term Chart strategy")
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    if save_dir:
        plt.savefig(os.path.join(save_dir, 'CTV Long Term Chart strategy.png'), dpi=300)
    plt.close()


def lifetime_cost(
        df: pd.DataFrame, 
        title: str,
        file_name: str = 'lifetime_cost',
        save_dir: str = None
    ):
    
    """   Plot the lifetime costs based   """

    colors = ['#4E79A7','#F28E2B','#E15759','#76B7B2','#59A14F','#EDC948', '#B07AA1', '#FF9DA7', '#BAB0AC', '#86BCB6', '#FABFD2', '#D37295',  '#8CD17D', '#C49C94', '#7F7F7F']
    df_filtered = df[df['value'] != 0]
    df_filtered['cost_type'] = df_filtered['cost_type'].str.split('€').str[0].str.strip()
    data_aggregated = df_filtered.groupby('cost_type')['value'].sum()

    raw_labels = data_aggregated.index
    labels = [label.split('_', 1)[-1].replace('_', ' ') for label in raw_labels]
    values = data_aggregated.values
    total = values.sum()
    percentages = values / total * 100

    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, _ = ax.pie(values, colors=colors, startangle=90, radius=1.0)

    ax.set_title(f'{title}: {total/ 1e6:.2f} M€', fontsize=16, pad=20)
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
                ha=ha, va='center', fontsize=16)

        ax.plot([0.9 * x, offset_x], [0.9 * y, offset_y], color='gray', lw=0.8)

    ax.legend(wedges, labels, title="Cost type", loc=10, bbox_to_anchor=(0.9, 0.9), fontsize = 13, title_fontsize = 13)

    plt.tight_layout()
    if save_dir:
        plt.savefig(os.path.join(save_dir, f'{file_name}.png'), dpi=300)
    plt.close()


def yearly_vessel_cost(
        df: pd.DataFrame, 
        title: str,
        find_element_class: dict,
        save_dir: str = None
    ):
    
    """   Plot the lifetime costs based   """

    # df preparation
    direct_costs_cols = df.loc[:, df.columns.get_level_values('metric') == 'direct_costs']
    avg_direct_costs = direct_costs_cols.mean(axis=1, skipna=True)
    result_df = pd.DataFrame({
        'cost_type': df[('vessel_id', '')],
        'value': avg_direct_costs
    })

    df_filtered = result_df[(result_df['value'] != 0) & (result_df['cost_type'] != 'fixed_annual_cost')]
    df_filtered['cost_type'] = df_filtered['cost_type'].apply(
        lambda vessel_id: (
            f"{vessel_id.upper()} - {find_element_class.find_vessel(vessel_id).type.upper()}"
            if vessel_id.lower() != 'oper_port'
            else 'Port Operation'
        )
    )

    # Plot
    colors = ['#4E79A7','#F28E2B','#E15759','#76B7B2','#59A14F','#EDC948', '#B07AA1', '#FF9DA7', '#BAB0AC', '#86BCB6', '#FABFD2', '#D37295',  '#8CD17D', '#C49C94', '#7F7F7F']
    
    data_aggregated = df_filtered.groupby('cost_type')['value'].sum()

    raw_labels = data_aggregated.index
    labels = [label.split('_', 1)[-1].replace('_', ' ') for label in raw_labels]
    values = data_aggregated.values
    total = values.sum()
    percentages = values / total * 100

    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, _ = ax.pie(values, colors=colors, startangle=90, radius=1.0)

    ax.set_title(f'{title}: {total/ 1e6:.2f} M€', fontsize=16, pad=20)
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
                ha=ha, va='center', fontsize=16)

        ax.plot([0.9 * x, offset_x], [0.9 * y, offset_y], color='gray', lw=0.8)

    ax.legend(wedges, labels, title="Vessel type", loc=10, bbox_to_anchor=(0.9, 0.9), fontsize = 13, title_fontsize = 13)

    plt.tight_layout()
    if save_dir:
        plt.savefig(os.path.join(save_dir, 'yearly_vessels_cost.png'), dpi=300)
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
    pass
