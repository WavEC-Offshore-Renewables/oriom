import os
import pandas as pd
import numpy as np
import logging
import matplotlib.pyplot as plt
from copy import deepcopy


"""Relevant graphs based on results."""


def distribution_failures(
        df: pd.DataFrame,
        save_dir: str=None
    ):
    '''It produces a graph representing the distribution of failures.

    Args:
        df (:obj:`DataFrame`): Dates_failures.
        save_dir (:obj:`str`, *optional*): Path dir to save graph representation.
            Deafults to `None`.
    '''

    dates_year = df.copy()
    dates_year['year'] = dates_year['datetime'].dt.year
    if '.' in dates_year['id'].iloc[0]:
        dates_year['id'] = dates_year['id'].str.split('.').str[0]
    grouped = dates_year.groupby(['year', 'id']).size().unstack(fill_value=0)

    years = grouped.index
    events = grouped.columns
    fig1 = plt.figure(figsize=(20,10))
    for event in events:
        event_occurrences = grouped[event]
        plt.scatter(years, [event] * len(years), s=event_occurrences*1.1, label=event) ##event_ccurrences*1.1 to adapt size of points
        for year, count in zip(years, event_occurrences):
            if count > 0:
                plt.annotate(str(count), xy=(year, event), xytext=(5, 5), textcoords='offset points')

    years = list(range(years[0],years[-1]))
    plt.xticks(years)

    plt.yticks(events)
    plt.xlabel('Years')
    plt.ylabel('Failure ids')
    plt.title('Failure Occurrences Over Years')
    plt.legend(title='id', loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=8)

    if save_dir is not None:
        plt.savefig(os.path.join(save_dir, 'distribution_failure.jpg'))

    plt.close()


def energy_yield(
    df: pd.DataFrame,
    name_file: str=None,
    save_dir: str=None
    ):
    '''It produces a graph representing the potential monthly energy and produced monthyl energy.

    Args:
        df (:obj:`DataFrame`): Availability_month.
        save_dir (:obj:`str`, *optional*): Path dir to save graph representation.
            Deafults to `None`.
    '''
    months = [1,2,3,4,5,6,7,8,9,10,11,12]
    energy_produced = []
    energy_potential = []
    for m in months:
        df_month = df[df['Months'] == m]
        df_month['Produced'] = df_month['En_max_kWh']-df_month['En_loss_kWh']
        energy_produced.append(df_month['Produced'].sum()/(1000*len(df_month.axes[0])))
        energy_potential.append(df_month['En_max_kWh'].sum()/(1000*len(df_month.axes[0])))

    fig2 = plt.figure(figsize=(10,6))
    plt.plot(months,energy_potential,'-k')
    plt.grid()
    plt.xticks(months)
    plt.xlabel('Months')
    plt.ylabel('Energy MWh')
    plt.title('Monthly energy maximum MWh')
    if save_dir is not None:
        plt.savefig(os.path.join(save_dir, 'energy_maximum_'+ name_file +'.jpg'))
    plt.close()

    plt.figure(figsize=(10,6))
    plt.plot(months,energy_produced,'-k')
    plt.grid()
    plt.xticks(months)
    plt.xlabel('Months')
    plt.ylabel('Energy MWh')
    plt.title('Monthly energy produced MWh')
    if save_dir is not None:
        plt.savefig(os.path.join(save_dir, 'energy_produced_'+ name_file +'.jpg'))
    plt.close()

def energy_yield_combined(
    dfs: dict,
    save_dir: str=None
    ):
    '''It produces a graph representing the potential monthly energy and produced monthyl energy.

    Args:
        dfs (dict): Dictionary of energy availability dataframes.
        save_dir (:obj:`str`, *optional*): Path dir to save graph representation.
            Deafults to `None`.
    '''
    months = [1,2,3,4,5,6,7,8,9,10,11,12]
    energy_potential_sublist = {}
    energy_produced_sublist = {}
    for f in dfs.keys():
        if 'wave' in f:
            name = 'Wave energy'
        elif 'wind' in f:
            name = 'Wind energy'
        else:
            name = 'Solar energy'
        energy_produced = []
        energy_potential = []
        for m in months:
            df = dfs[f]
            df_month = df[df['Months'] == m]
            df_month['Produced'] = df_month['En_max_kWh']-df_month['En_loss_kWh']
            energy_produced.append(df_month['Produced'].sum()/(1000*len(df_month.axes[0])))
            energy_potential.append(df_month['En_max_kWh'].sum()/(1000*len(df_month.axes[0])))
        energy_potential_sublist.update({name:energy_potential})
        energy_produced_sublist.update({name:energy_produced})

    energy_produced_overall = [sum(x) for x in zip(*energy_produced_sublist.values())]
    energy_potential_overall = [sum(x) for x in zip(*energy_potential_sublist.values())]
    energy_produced_sublist.update({'combined_produced':energy_produced_overall})
    energy_potential_sublist.update({'combined_produced':energy_potential_overall})

    fig3 = plt.figure(figsize=(10,6))
    for k,v in energy_potential_sublist.items():
        plt.plot(months,v,label=k)
    plt.grid()
    plt.xticks(months)
    plt.xlabel('Months')
    plt.ylabel('Energy MWh')
    plt.title('Monthly energy maximum MWh')
    plt.legend()
    if save_dir is not None:
        plt.savefig(os.path.join(save_dir, 'energy_maximum_total.jpg'))
    plt.close()

    plt.figure(figsize=(10,6))
    for k,v in energy_produced_sublist.items():
        plt.plot(months,v,label=k)
    plt.grid()
    plt.xticks(months)
    plt.xlabel('Months')
    plt.ylabel('Energy MWh')
    plt.title('Monthly energy produced MWh')
    plt.legend()
    if save_dir is not None:
        plt.savefig(os.path.join(save_dir, 'energy_produced_total.jpg'))
    plt.close()


def direct_costs_per_year(
        df: pd.DataFrame,
        df_p10: pd.DataFrame,
        df_p90: pd.DataFrame,
        save_dir: str = None
    ):
    """Plot yearly direct costs: AVG bars with P10-P90 error bars."""

    years_cols = df.columns[1:-1]

    years = np.array([int(c) for c in years_cols])
    avg = df.loc[:, years_cols].sum(axis=0).to_numpy(dtype=float) / 1e6
    p10 = df_p10.loc[:, years_cols].sum(axis=0).to_numpy(dtype=float) / 1e6
    p90 = df_p90.loc[:, years_cols].sum(axis=0).to_numpy(dtype=float) / 1e6

    yerr = np.maximum(np.vstack([avg - p10, p90 - avg]), 0)

    fig, ax = plt.subplots(figsize=(15, 6))
    ax.bar(years, avg, color='skyblue', edgecolor='black')
    ax.errorbar(
        years, avg, yerr=yerr,
        fmt='none', ecolor='black',
        capsize=4, elinewidth=1.2
    )

    ax.set_xticks(years)
    ax.set_xlabel('Years')
    ax.set_ylabel('Direct costs (M€)')
    ax.set_title('Direct costs per year (AVG with P10-P90 range)')
    ax.grid(axis='y', alpha=0.3)
    ax.set_axisbelow(True)

    fig.tight_layout()

    if save_dir is not None:
        fig.savefig(os.path.join(save_dir, 'yearly_direct_costs.jpg'),dpi=300,bbox_inches='tight')

    plt.close(fig)



def direct_cost_diversified(
        df: pd.DataFrame,
        ops_corr: list,
        insp: list,
        save_dir: str=None
):
    '''It produces a graph representing the direct costs.

    Args:
        df (:obj:`DataFrame`): kpi_om.
        ops_corr (list): List of corrective operations.
        insp (list): List of inspections.
        save_dir (:obj:`str`, *optional*): Path dir to save graph representation.
            Deafults to `None`.
    '''
    tot_lifetime = df['lifetime_direct_costs'].sum()/1000000
    ids_ = df['operation_id'].tolist()
    corr_ops = [o.id for o in ops_corr]
    insp_ops = [o.id for o in insp]
    lifetime_corr = 0
    lifetime_prev = 0
    for i in ids_:
        if i in corr_ops:
            lifetime_corr += df.loc[df['operation_id']==i,'lifetime_direct_costs'].item()
        elif i in insp_ops:
            lifetime_prev += df.loc[df['operation_id']==i,'lifetime_direct_costs'].item()
    lifetime_corr = lifetime_corr/1000000
    lifetime_prev = lifetime_prev/1000000

    ratio = lifetime_prev/lifetime_corr
    X = ['Fixed costs','Variable preventive lifetime costs','Variable corrective lifetime costs']
    Y = [(tot_lifetime-lifetime_prev-lifetime_corr),lifetime_prev,lifetime_corr]
    colors = ['C1','C2','C3']
    fig8 = plt.figure()
    pie2,_ = plt.pie(Y,colors=colors,startangle=100)
    #plt.text(0.5,0.5,'Cost ratio Preventive/Corrective: %i' %ratio,ha='right',va='top',color='black')
    plt.legend(pie2, X,loc='best')

    if save_dir is not None:
        plt.savefig(os.path.join(save_dir, 'lifetime_costs.jpg'))
    plt.close()


def indirect_costs_per_year(
        df: pd.DataFrame,
        electricity_price: float,
        name_file: str = None,
        save_dir: str = None,
        df_p10: pd.DataFrame = None,
        df_p90: pd.DataFrame = None
    ):
    """Plot yearly indirect costs with optional P10-P90 error bars.

    Args:
        df (pd.DataFrame): AVG yearly energy results.
        electricity_price (float): Electricity price in €/MWh.
        name_file (str, optional): Name used in the output filename.
        save_dir (str, optional): Directory where the plot is saved.
        df_p10 (pd.DataFrame, optional): P10 yearly energy results.
        df_p90 (pd.DataFrame, optional): P90 yearly energy results.
    """
    years = df['Years'].to_numpy()
    en_loss = df['En_loss_kWh'].to_numpy(dtype=float)
    energy_av = df['En_availability'].to_numpy(dtype=float)

    use_percentiles = df_p10 is not None and df_p90 is not None

    # Calculate indirect costs in M€.
    cost_avg = en_loss * electricity_price / 1e9

    if use_percentiles:
        cost_p10 = (df_p10['En_loss_kWh'].to_numpy(dtype=float) * electricity_price / 1e9)
        cost_p90 = (df_p90['En_loss_kWh'].to_numpy(dtype=float) * electricity_price / 1e9)

    # Remove the final year if energy availability is 100%.
    if len(energy_av) and energy_av[-1] == 100:
        years = years[:-1]
        cost_avg = cost_avg[:-1]
        if use_percentiles:
            cost_p10 = cost_p10[:-1]
            cost_p90 = cost_p90[:-1]

    if len(cost_avg) == 0:
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(years, cost_avg, color='skyblue', edgecolor='black')

    # Add P10-P90 error bars when both percentile datasets are available.
    if use_percentiles:
        yerr = np.maximum(np.vstack([cost_avg - cost_p10,cost_p90 - cost_avg]),0)
        ax.errorbar(
            years,
            cost_avg,
            yerr=yerr,
            fmt='none',
            ecolor='black',
            capsize=4,
            elinewidth=1.2
        )

    ax.set_xticks([year for year in years if year % 5 == 0])
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    ax.set_xlabel('Years')
    ax.set_ylabel('Indirect costs (M€)')

    min_cost = np.nanmin(cost_p10) if use_percentiles else np.nanmin(cost_avg)
    max_cost = np.nanmax(cost_p90) if use_percentiles else np.nanmax(cost_avg)
    ax.set_ylim(max(0, min_cost * 0.9), max_cost * 1.1 if max_cost > 0 else 1)

    title = 'Indirect costs per year'
    if use_percentiles:
        title += ' (AVG with P10-P90 range)'
    else:
        title += ' (AVG)'
    ax.set_title(title)

    fig.tight_layout()

    if save_dir is not None:
        fig.savefig(os.path.join(save_dir, f'yearly_indirect_costs_{name_file}.jpg'), dpi=300, bbox_inches='tight')

    plt.close(fig)


def farm_availability(
        df_: pd.DataFrame | dict,
        name_file: str = None,
        save_dir: str = None
    ):
    '''It produces graphs representing time and energy availability.
    Args:
        df_ (DataFrame | dict): Availability data. If a dict is provided,
            it must contain 'AVG', 'P10' and 'P90' DataFrames.
        name_file (str, optional): Name used in the output filenames.
        save_dir (str, optional): Directory where graphs are saved.
    '''
    has_percentiles = isinstance(df_, dict)
    df = df_['AVG'] if has_percentiles else df_

    years = df['Years'].tolist()
    energy_av = df['En_availability'].tolist()
    time_av = df['Time_availability'].tolist()

    if has_percentiles:
        df_p10 = df_['P10']
        df_p90 = df_['P90']

    if energy_av[-1] == 100:
        years = years[:-1]
        energy_av = energy_av[:-1]
        time_av = time_av[:-1]
        if has_percentiles:
            df_p10 = df_p10.iloc[:-1]
            df_p90 = df_p90.iloc[:-1]

    avg_time = df['Time_availability'].mean()
    avg_en = df['En_availability'].mean()

    yerr_time = None
    yerr_en = None

    if has_percentiles:
        yerr_time = [
            (time_av - df_p10['Time_availability'].to_numpy()).clip(min=0),
            (df_p90['Time_availability'].to_numpy() - time_av).clip(min=0)
        ]
        yerr_en = [
            (energy_av - df_p10['En_availability'].to_numpy()).clip(min=0),
            (df_p90['En_availability'].to_numpy() - energy_av).clip(min=0)
        ]

    plt.figure(figsize=(15, 6))
    plt.bar(years, time_av, color='skyblue', edgecolor='black', yerr=yerr_time, capsize=3)
    plt.grid(axis='y')
    xticks_filtered = [year for year in years if year % 5 == 0]
    plt.xticks(xticks_filtered)
    plt.xlabel('Years')
    plt.ylabel('Time availability %')
    plt.ylim(min(time_av) * 0.9, 100)
    plt.title('Time availability per year: Avg %i' % avg_time)
    if save_dir is not None:
        plt.savefig(os.path.join(save_dir, 'time_availability_' + str(name_file or '') + '.jpg'), bbox_inches='tight')
    plt.close()

    plt.figure(figsize=(15, 6))
    plt.bar(years, energy_av, color='skyblue', edgecolor='black', yerr=yerr_en, capsize=3)
    plt.grid(axis='y')
    plt.xticks(xticks_filtered)
    plt.xlabel('Years')
    plt.ylabel('Energy availability %')
    plt.ylim(min(energy_av) * 0.9, 100)
    plt.title('Energy availability per year: Avg %i' % avg_en)
    if save_dir is not None:
        plt.savefig(os.path.join(save_dir, 'energy_availability_' + str(name_file or '') + '.jpg'), bbox_inches='tight')
    plt.close()


def direct_cost_pie(
        df: pd.DataFrame,
        save_dir: str=None
    ):
    '''It produces a graph representing a pie chart.

    Args:
        df (:obj:`DataFrame`): kpi_om.
        save_dir (:obj:`str`, *optional*): Path dir to save graph representation.
            Deafults to `None`.
    '''
    labels = ['Lifetime vessel costs','Lifetime port costs', 'Lifetime repair costs', 'Lifetime technicians costs']
    vessel_cost_tot = df.query("operation_id=='total'")["tot_vessel_costs"].item() + df.query("operation_id=='total'")["tot_mobilization_costs"].item()
    port_costs_tot = df.query("operation_id=='total'")["tot_port_costs"].item()
    repair_costs_tot = df.query("operation_id=='total'")["tot_repair_costs"].item()
    tech_costs_tot = df.query("operation_id=='total'")["tot_technicians_costs"].item()
    tot = vessel_cost_tot+port_costs_tot+repair_costs_tot+tech_costs_tot
    sizes = [vessel_cost_tot*100/tot,port_costs_tot*100/tot,repair_costs_tot*100/tot,tech_costs_tot*100/tot]
    colors = ['C1','C2','C3','C4']
    fig7 = plt.figure()
    pie1,_ = plt.pie(sizes,colors=colors,startangle=100)
    plt.legend(pie1, labels,loc='best')

    if save_dir is not None:
        plt.savefig(os.path.join(save_dir, 'pie_direct_costs.jpg'))
    plt.close()


def compare_quartiles_direct_costs(
    df_25: pd.DataFrame,
    df_50: pd.DataFrame,
    df_75: pd.DataFrame,
    save_dir: str=None
):
    '''It produces a graph representing total costs p25,p50,075.

    Args:
        df (:obj:`DataFrame`): kpi_om_25.
        df (:obj:`DataFrame`): kpi_om_50.
        df (:obj:`DataFrame`): kpi_om_75.
        save_dir (:obj:`str`, *optional*): path dir to save graph representation.
            Deafults to `None`.
    '''

    ###scenarios = ['20 km', '40 km', '100 km']
    x = 1 ### one scenario considered
    port_cost = df_50.query("operation_id=='total'")["tot_port_costs"].item()/1000000
    tech_cost = df_50.query("operation_id=='total'")["tot_technicians_costs"].item()/1000000
    repair_cost = df_50.query("operation_id=='total'")["tot_repair_costs"].item()/1000000
    ves_costs = df_50.query("operation_id=='total'")["tot_vessel_costs"].item()/1000000 + df_50.query("operation_id=='total'")["tot_mobilization_costs"].item()/1000000

    lifetime_50 = df_50.query("operation_id=='total'")["lifetime_direct_costs"].item()/1000000
    lifetime_25 = df_25.query("operation_id=='total'")["lifetime_direct_costs"].item()/1000000
    lifetime_75 = df_75.query("operation_id=='total'")["lifetime_direct_costs"].item()/1000000

    plt.bar(x,lifetime_50, width=0.1, color='blue')
    plt.bar(x,ves_costs, width=0.1, color='yellow')
    plt.bar(x,repair_cost,width=0.1, color='orange')
    plt.bar(x,tech_cost,width=0.1, color='red')
    plt.bar(x,port_cost,width=0.1, color='green')

    #plt.xticks(scenarios)
    plt.ylabel('Direct costs M€')

    # Adding lines for whiskers
    #for i, scenario in enumerate(scenarios):
        # plt.hlines(xmin=i-0.1,xmax=i+0.1, y=p75_values[i], color='black', linewidth=1.1)
        # plt.hlines(xmin=i-0.1,xmax=i+0.1, y=p25_values[i], color='black', linewidth=1.1)
        # plt.vlines(x=i,ymin=p75_values[i], ymax=p25_values[i], color='black', linewidth=0.5)
    plt.hlines(xmin=x-0.1,xmax=x+0.1, y=lifetime_75, color='black', linewidth=1.1)
    plt.hlines(xmin=x-0.1,xmax=x+0.1, y=lifetime_25, color='black', linewidth=1.1)
    plt.vlines(x=x,ymin=lifetime_75, ymax=lifetime_25, color='black', linewidth=0.5)

    if save_dir is not None:
        plt.savefig(os.path.join(save_dir, 'lifetime_direct_costs_percentiles.jpg'))
    plt.close()


def distribution_mobilization(
        df_logs: pd.DataFrame,
        vessels: list,
        df_kpi_om: pd.DataFrame,
        name: str,
        save_dir: str=None
    ):
    '''It produces a graph representing the distribution of failures.

    Args:
        df_logs (pd.DataFrame): log_events.
        vessels (list): list of vessels class.
        df_kpi_om (pd.DataFrame): kpi_om.
        save_dir (:obj:`str`, *optional*): path dir to save graph representation.
            Deafults to `None`.
    '''
    df_log = df_logs[df_logs['event'] == 'mobilisation']
    if df_log.empty is False:
        df_log['d_trigger'] = pd.to_datetime(df_log['d_trigger'])
        df_logs_mob = deepcopy(df_log)
        list_ves = df_logs_mob['vessel_1'].tolist()
        list_ves = list(set(list_ves))
        saved_money = 0
        for v in list_ves:
            vessel_found = False
            for ves in vessels:
                if ves.id == v:
                    vessel_found = True
                    break
            if vessel_found is False:
                _e = 'Vessel not found'
                raise ValueError(_e, v)
            v = ves
            mob_v = df_logs_mob[df_logs_mob['vessel_1'] == v.id.lower()]
            if mob_v.empty is True:
                continue
            mob_v['TimeBetween'] = mob_v['d_trigger'].diff().dt.days

            mob_time = v.mobilisation_time/24
            mob_cost = v.mobilisation_cost
            count_below = (mob_v['TimeBetween']<mob_time).sum()
            saved_money += count_below*mob_cost

        tot_cost = df_kpi_om.query("operation_id=='total'")["lifetime_direct_costs"].item()
        tot_cost_less_mob = tot_cost-saved_money
        saving_perc = (tot_cost-tot_cost_less_mob)/tot_cost * 100
        saving_perc = round(saving_perc,2)

        df_logs_mob.sort_values(by='d_trigger', inplace=True)
        df_logs_mob.reset_index(drop=True, inplace=True)
        df_logs_mob['year'] = df_logs_mob['d_trigger'].dt.year
        df_logs_mob
        grouped = df_logs_mob.groupby(['year', 'vessel_1']).size().unstack(fill_value=0)
        years = grouped.index.tolist()
        events = grouped.columns
        fig = plt.figure(figsize=(20,10))
        for event in events:
            event_occurrences = grouped[event]
            plt.scatter(years, [event] * len(years), s=event_occurrences*1.1, label=event) ##event_ccurrences*1.1 to adapt size of points
            for year, count in zip(years, event_occurrences):
                if count > 0:
                    plt.annotate(str(count), xy=(year, event), xytext=(5, 5), textcoords='offset points')

        years = list(range(years[0],years[-1]+1))

        text = f"{'Number of close mobilisation in time:'}{count_below}"
        text += f"{' Total direct costs saves:'}{saving_perc}"

        plt.text(
            0.5,
            5,
            text,
            transform=fig.transFigure,
            fontsize=10,
            color='blue'
        )

        plt.xticks(years)
        plt.xlabel('Years')
        plt.ylabel('Mobilisation vessel')
        plt.title("Mobilisation")

        if save_dir is not None:
                plt.savefig(os.path.join(save_dir,name+".jpg"))
        plt.close()



if '__main__' == __name__:
    pass