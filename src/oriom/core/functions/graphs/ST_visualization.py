from __future__ import annotations
import logging
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch
import os


STAGES = [
    ('d_end_leadtime', 'd_end_wait_start', 'Port'),
    ('d_end_wait_start', 'd_end_dur_net_port', 'Port'),
    ('d_end_dur_net_port', 'd_end_transit_ts', 'Transit'),
    ('d_end_transit_ts', 'd_end_wait_site', 'Site'),
    ('d_end_wait_site', 'd_end_dur_net_site', 'Site'),
    ('d_end_dur_net_site', 'd_end_transit_tp', 'Transit'),
    ('d_end_transit_tp', 'd_end', 'Port'),
]

COLORS = {'Port': '#7895A8', 'Transit': '#E8A54A', 'Site': '#126B82'}

@dataclass
class PlotConfig:
    vessel_types: dict[str, str] = field(default_factory=dict)
    price_eur_mwh: float | pd.Series | pd.DataFrame | None = None
    output_dir: Path = Path('oriom_figures')
    dpi: int = 180
    # Set True ONLY if wind_corrective_energy.Power_loss_kW is confirmed to
    # represent a cumulative meter, not a point-in-time event quantity.
    use_event_power_loss: bool = False


def _style():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.grid': True, 'grid.alpha': .16,
                         'figure.facecolor': 'white', 'axes.facecolor': 'white',
                         'savefig.facecolor': 'white'})




def _format_time_axis(ax, start=None, end=None):
    """Display datetime ticks at six-hour intervals with compact labels."""
    if start is not None and end is not None:
        ax.set_xlim(start, end)
    ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 6, 12, 18]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
    ax.xaxis.set_minor_locator(mdates.DayLocator())
    ax.tick_params(axis='x', labelsize=8, rotation=45, pad=4)
    ax.grid(axis='x', which='major', alpha=.12)
    ax.grid(axis='x', which='minor', alpha=.25, linewidth=1)
    # Date displayed separately at 00:00 to avoid repeating it at every tick.
    for tick in ax.get_xticklabels():
        tick.set_ha('right')


def _legend_above(ax, *, ncol=3, handles=None, labels=None):
    """Place the legend just above the plotting area, below the title."""
    kwargs = dict(loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=ncol,
                  frameon=False, fontsize=9, borderaxespad=0,
                  columnspacing=1.6, handlelength=1.6)
    if handles is not None:
        return ax.legend(handles=handles, labels=labels, **kwargs) if labels is not None else ax.legend(handles=handles, **kwargs)
    return ax.legend(**kwargs)


def _power(power: pd.DataFrame) -> pd.DataFrame:
    df = power.copy()
    df = df.sort_index()
    return df


def _interval_hours(index: pd.DatetimeIndex) -> np.ndarray:
    if len(index) < 2:
        raise ValueError('At least two power timestamps are required')
    ns = index.asi8
    dt = np.diff(ns) / 3.6e12
    if (dt <= 0).any():
        raise ValueError('Power timestamps must be strictly increasing')
    # Each power observation represents the interval [timestamp, next timestamp).
    # Last row uses the preceding step; trim input if it is only an endpoint marker.
    return np.r_[dt, dt[-1]]


def _prices(price, index: pd.DatetimeIndex) -> pd.Series:
    if price is None:
        return pd.Series(np.nan, index=index, name='price_eur_mwh')
    if np.isscalar(price):
        return pd.Series(float(price), index=index, name='price_eur_mwh')
    if isinstance(price, pd.DataFrame):
        if 'datetime' in price.columns:
            price = price.set_index('datetime')
        if 'price_eur_mwh' not in price.columns:
            raise ValueError('Price DataFrame needs price_eur_mwh column')
        price = price['price_eur_mwh']
    s = price.copy()
    s.index = pd.to_datetime(s.index)
    s = pd.to_numeric(s, errors='coerce').sort_index()
    if s.index.has_duplicates:
        raise ValueError('Duplicate price timestamps')
    # Exact matching only: missing hourly prices remain missing, never silently filled.
    return s.reindex(index).rename('price_eur_mwh')


def _availability(events: pd.DataFrame, index: pd.DatetimeIndex) -> pd.Series:
    if not {'Date', 'Perc_availability'}.issubset(events.columns):
        raise ValueError('Missing Date/Perc_availability in corrective events')
    df = events[['Date', 'Perc_availability']].copy()
    df['Perc_availability'] = pd.to_numeric(df['Perc_availability'], errors='coerce')
    df = df.dropna().sort_values('Date', kind='stable')
    # Multiple simultaneous events can share a timestamp. The event log's
    # LAST recorded aggregate availability is the post-event state.
    df = df.drop_duplicates('Date', keep='last').set_index('Date')
    if df.empty:
        raise ValueError('No valid availability events')
    # Carry forward most recent state, but never assume 100% before first event.
    all_times = df.index.union(index)
    availability = df['Perc_availability'].reindex(all_times).sort_index().ffill().reindex(index)
    if availability.isna().any():
        raise ValueError('Availability is undefined at the start of the power timeseries')
    if not availability.between(0, 100).all():
        raise ValueError('Availability must be between 0 and 100')
    return availability


def build_energy_results(
    power: pd.DataFrame,
    corrective: pd.DataFrame,
    price_eur_mwh=None
) -> pd.DataFrame:
    """Integrate power at interval starts, applying last-known event availability.

    IMPORTANT: p_wind must be gross potential farm power BEFORE corrective losses.
    If p_wind already includes losses, change the baseline to avoid double counting.
    Availability is applied at sample timestamps; sub-hour events are approximated.
    """
    df = _power(power)
    result = pd.DataFrame(index=df.index)
    result['interval_hours'] = _interval_hours(df.index)
    result['availability_pct'] = _availability(corrective, df.index)
    result['potential_power_kw'] = pd.to_numeric(df['p_wind'], errors='raise')
    result['actual_power_kw'] = result['potential_power_kw'] * result['availability_pct'] / 100
    result['lost_power_kw'] = round(result['potential_power_kw'] - result['actual_power_kw'], 2)
    for key in ('potential', 'actual', 'lost'):
        result[f'{key}_energy_mwh'] = result[f'{key}_power_kw'] * result['interval_hours'] / 1000
    result['price_eur_mwh'] = _prices(price_eur_mwh, result.index)
    result['actual_revenue_eur'] = result['actual_energy_mwh'] * result['price_eur_mwh']
    result['lost_revenue_eur'] = result['lost_energy_mwh'] * result['price_eur_mwh']
    result['cumulative_lost_energy_mwh'] = result['lost_energy_mwh'].cumsum()
    result['cumulative_lost_revenue_eur'] = result['lost_revenue_eur'].cumsum() if result['price_eur_mwh'].notna().all() else np.nan
    return result


def build_vessel_segments(
    events: pd.DataFrame,
    vessel_types: dict[str, str],
    start: pd.Timestamp,
    end: pd.Timestamp
) -> pd.DataFrame:
    """Construct phase segments; quantity is a fleet count, NOT a unique hull ID."""
    df = events.copy()
    segments = []
    for row_id, r in df.iterrows():
        for slot in (1, 2):
            vessel = r.get(f'vessel_{slot}')
            count = pd.to_numeric(r.get(f'n_vessel_{slot}'), errors='coerce')
            if pd.isna(vessel) or pd.isna(count) or count <= 0:
                continue
            for begin_col, finish_col, location in STAGES:
                a, b = r.get(begin_col), r.get(finish_col)
                if pd.isna(a) or pd.isna(b) or b <= a:
                    continue
                a, b = max(a, start), min(b, end)
                if b <= a:
                    continue
                segments.append({'vessel_id': str(vessel), 'vessel_type': vessel_types.get(str(vessel), 'Unclassified'),
                                 'count': int(count), 'start': a, 'end': b,
                                 'location': location, 'event_id': str(r.get('id', row_id))})
    return pd.DataFrame(segments)


def plot_vessel_gantt(segments: pd.DataFrame, start, end):
    _style()
    if segments is None or segments.empty:
        logging.warning('No vessel phases overlap the power timeseries')
        return
    ids = segments[['vessel_type', 'vessel_id']].drop_duplicates().sort_values(['vessel_type', 'vessel_id'])
    labels = [f'{r.vessel_type}  |  {r.vessel_id}' for r in ids.itertuples()]
    mapping = {r.vessel_id: i for i, r in enumerate(ids.itertuples())}
    fig, ax = plt.subplots(figsize=(15, max(4.2, len(labels) * .65 + 1.8)), layout='constrained')
    for r in segments.itertuples():
        y = mapping[r.vessel_id]
        x = mdates.date2num(r.start)
        width = (r.end - r.start).total_seconds() / 86400
        ax.broken_barh([(x, width)], (y - .32, .64), facecolors=COLORS[r.location], edgecolors='white', linewidth=.5)
    
    # Find the longest segment for each vessel and write number of vessel used
    longest_segments = segments.loc[segments.groupby('vessel_id').apply(lambda g: (g['end'] - g['start']).idxmax(), include_groups=False).values]
    for r in longest_segments.itertuples():
        y = mapping[r.vessel_id]
        x = mdates.date2num(r.start)
        width = (r.end - r.start).total_seconds() / 86400
        if width > (mdates.date2num(end) - mdates.date2num(start)) * .022:
            ax.text(x + width / 2, y, f'{r.count}x', ha='center', va='center', color='white', fontsize=9, fontweight='bold')
        else:
            ax.text(x + width / 2, y + .48, f'{r.count}x', ha='center', va='center', color='black', fontsize=9, fontweight='bold')
            
    ax.set_yticks(range(len(labels)), labels)
    ax.set_ylim(-.8, len(labels) - .2)
    ax.invert_yaxis()
    ax.set_xlim(start, end)
    _format_time_axis(ax, start, end)
    fig.suptitle('Vessel utilisation | Operational timeline', x=.075, ha='left', fontweight='bold', fontsize=15)
    ax.set_xlabel('Simulation time')
    _legend_above(ax, handles=[Patch(color=c, label=k) for k, c in COLORS.items()])
    ax.grid(axis='y', visible=False)
    return fig


def plot_energy_and_revenue(result: pd.DataFrame):
    _style()
    has_prices = result['price_eur_mwh'].notna().any()
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(15, 8), sharex=True, layout='constrained', height_ratios=[2, 1])
    x = result.index
    ax.plot(x, result['potential_power_kw'] / 1000, label='Potential generation', color='#9AAAB7', linewidth=1.6)
    ax.plot(x, result['actual_power_kw'] / 1000, label='Actual generation', color='#126B82', linewidth=1.9)
    ax.fill_between(x, result['actual_power_kw'] / 1000, result['potential_power_kw'] / 1000,
                    color='#E8A54A', alpha=.35, label='Unavailable generation')
    ax.set_ylabel('Power [MW]')
    ax.set_ylim(bottom=0)
    _legend_above(ax, ncol=3)
    fig.suptitle('Energy production and revenue losses', x=.075, ha='left', fontweight='bold', fontsize=15)
    if has_prices:
        ax2.bar(x, result['lost_revenue_eur'] / 1000, width=result['interval_hours'] / 24 * .85,
                color='#C35B4D', label='Lost revenue')
        ax2.set_ylabel('Lost revenue [k€ / interval]')
        _legend_above(ax2, ncol=1)
    else:
        ax2.bar(x, result['lost_energy_mwh'], width=result['interval_hours'] / 24 * .85, color='#C35B4D')
        ax2.set_ylabel('Lost energy [MWh / interval]')
        ax2.set_title('Electricity prices not provided — showing energy losses', fontsize=10)
    ax2.set_xlabel('Simulation time')
    _format_time_axis(ax2, result.index[0], result.index[-1] + pd.Timedelta(hours=float(result['interval_hours'].iloc[-1])))
    ax2.set_ylim(bottom=0)
    return fig


def plot_cumulative_losses(result: pd.DataFrame):
    _style()
    fig, ax = plt.subplots(figsize=(15, 5), layout='constrained')
    ax.plot(result.index, result['cumulative_lost_energy_mwh'], linewidth=2.2, label='Cumulative lost energy')
    ax.set_ylabel('Cumulative lost energy [MWh]')
    if result['price_eur_mwh'].notna().all():
        ax2 = ax.twinx()
        ax2.plot(result.index, result['cumulative_lost_revenue_eur'] / 1000,
                 color='#C35B4D', linewidth=2, label='Cumulative lost revenue')
        ax2.set_ylabel('Cumulative lost revenue [k€]')
        ax2.set_ylim(bottom=0) 
        lines = ax.lines + ax2.lines
        _legend_above(ax, handles=lines, labels=[l.get_label() for l in lines], ncol=2)
    else:
        _legend_above(ax, ncol=1)
    fig.suptitle('Cumulative O&M impact', x=.075, ha='left', fontweight='bold', fontsize=15)
    ax.set_xlabel('Simulation time')
    _format_time_axis(ax, result.index[0], result.index[-1] + pd.Timedelta(hours=float(result['interval_hours'].iloc[-1])))
    ax.set_ylim(bottom=0)
    
    return fig


def create_ST_figures(
        log_events_merged: pd.DataFrame,
        wind_corrective_energy: pd.DataFrame,
        timeseries_power: pd.DataFrame,
        vessel_types: dict[str, str],
        energy_price: float,
        graph_dir_r: str
    ):
    """Generate three figures, return auditable results and save PNG/CSV outputs."""

    Path(graph_dir_r).mkdir(parents=True, exist_ok=True)
    power = _power(timeseries_power)
    dt = _interval_hours(power.index)
    start, end = power.index[0], power.index[-1] + pd.Timedelta(hours=float(dt[-1]))
    segments = build_vessel_segments(log_events_merged, vessel_types, start, end)
    energy = build_energy_results(power, wind_corrective_energy, energy_price) if not wind_corrective_energy.empty else pd.DataFrame()
    
    figures = {
        '01_vessel_utilisation': plot_vessel_gantt(segments, start, end),
        '02_energy_revenue_losses': (plot_energy_and_revenue(energy) if not energy.empty else None),
        '03_cumulative_losses': plot_cumulative_losses(energy) if not energy.empty else None,
    }
    
    for name, fig in figures.items():
        if fig:
            fig.savefig(f'{graph_dir_r}/{name}.png', dpi=300, bbox_inches='tight')
            plt.close()
    

def final_stat_graph_ST(
    failure_ranges: list[tuple[int, int, list[str]]],
    failure_not_corrected_idx: int,
    total_costs: dict, 
    total_energy_losses_costs: dict, 
    metocean_df: pd.DataFrame,
    save_dir: str = None
)-> int:
    """ Create a graph to show the total costs and energy losses along the runs"""
    
    # Runs and values
    runs = sorted(total_costs)
    direct = np.array([total_costs[i] for i in runs])
    energy = np.array([total_energy_losses_costs[i] * 1e6 for i in runs])
    total = direct + energy

    # Datetime index
    dates = metocean_df.index[:len(runs)]
    # Minimum
    if failure_not_corrected_idx > 0:
        minimum_idx = int(np.argmin(total[:failure_not_corrected_idx]))
    else:
        minimum_idx = int(np.argmin(total))

    # Figure
    fig, ax = plt.subplots(figsize=(14, 6))
    bar_width = (dates[-1] - dates[0]).total_seconds() / (len(dates) - 1) / 86400 * 0.65

    # Stacked vertical bars
    ax.bar(
        dates, direct,
        width=bar_width,
        label='Direct costs',
        color='#527C9B',
        zorder=3
    )

    ax.bar(
        dates, energy,
        bottom=direct,
        width=bar_width,
        label='Energy losses',
        color='#D5A45B',
        zorder=3
    )

    # Highlight optimal run
    ax.bar(
        dates[minimum_idx],
        total[minimum_idx],
        width=bar_width,
        facecolor='none',
        edgecolor='red',
        linewidth=2.5,
        zorder=4
    )

    # Total values
    offset = max(total) * 0.012
    ax.text(
        dates[minimum_idx],
        total[minimum_idx] + offset,
        f'€{total[minimum_idx]:,.0f}',
        ha='center',
        va='bottom',
        fontsize=9,
    )
    
    for i, (start_idx, end_idx, failures) in enumerate(failure_ranges):

        # Time boundaries of the excluded interval
        left = dates[start_idx] - (dates[1] - dates[0]) / 2
        right = dates[end_idx] + (dates[1] - dates[0]) / 2

        # Grey background to identify the excluded region
        ax.axvspan(
            left,
            right,
            facecolor='#F1F3F5',
            edgecolor='none',
            alpha=0.85,
            zorder=2
        )

        # Diagonal hatching to clearly mark invalid results
        ax.axvspan(
            left,
            right,
            facecolor='none',
            edgecolor='#AAB2BA',
            hatch='///',
            linewidth=0,
            zorder=4,
            alpha=0.6,
        )

        ax.text(
            dates[start_idx] + (dates[end_idx] - dates[start_idx]) / 2,
            0.7-i/10,
            '\n'.join(failure.split('_', 2)[-1].replace('_', ' ') for failure in failures),
            transform=ax.get_xaxis_transform(),
            ha='center',
            va='center',
            fontsize=7,
            fontweight='bold'
        )
        
    if failure_ranges:
        start_idx_min = min(failure_ranges, key=lambda x: x[0])[0]
        end_idx_max = max(failure_ranges, key=lambda x: x[1])[1]
        
        ax.text(
                dates[start_idx_min] + (dates[end_idx_max] - dates[start_idx_min]) / 2,
                0.9,
                'Failure not corrected',
                transform=ax.get_xaxis_transform(),
                ha='center',
                va='center',
                fontsize=9,
                fontweight='bold'
            )
    
    # X-axis: metocean datetime index
    ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 6, 12, 18]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

    ax.set_xlabel('Work start date', fontsize=11, labelpad=12)
    ax.set_ylabel('Total lifetime costs (€)', fontsize=11, labelpad=12)

    ax.set_title(
        'OPEX O&M Cost Comparison for different day of start',
        fontsize=15,
        fontweight='bold',
        loc='left',
        pad=20
    )

    # Y-axis formatting
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'€{y / 1e3:,.0f}k'))

    # Styling
    ax.grid(axis='y', linestyle='--', alpha=0.25, zorder=0)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
    ax.tick_params(axis='both', length=0, pad=8)
    ax.legend(frameon=False, loc='best', ncol=2, fontsize=9)
    ax.set_ylim(0, max(total) * 1.15)
    fig.tight_layout()
    
    if save_dir:
        plt.savefig(f"{save_dir}/total_cost_losses_vs_Start_Date.png", dpi=300, bbox_inches='tight')
    plt.close()
        
    return minimum_idx


def plot_energy_losses_ST(
    failure_ranges: list[tuple[int, int, list[str]]],
    failure_not_corrected_idx: int,
    total_energy_losses: dict,
    metocean_df: pd.DataFrame,
    save_dir: str = None
):
    # Data
    runs = sorted(total_energy_losses)
    dates = metocean_df.index[:len(runs)]
    energy_losses = np.array([total_energy_losses[i] for i in runs])

    # Minimum
    if failure_not_corrected_idx > 0:
        minimum_idx = int(np.argmin(energy_losses[:failure_not_corrected_idx]))
    else:
        minimum_idx = int(np.argmin(energy_losses))
    minimum_value = energy_losses[minimum_idx]

    # Figure
    fig, ax = plt.subplots(figsize=(12, 5.5))

    # Main line
    ax.plot(
        dates,
        energy_losses,
        color='#527C9B',
        linewidth=2.2,
        marker='o',
        markersize=6,
        label='Total energy losses',
        zorder=3
    )

    # Highlight minimum
    ax.scatter(
        dates[minimum_idx],
        minimum_value,
        color='red',
        edgecolor='white',
        linewidth=1.5,
        s=110,
        zorder=5,
        label='Minimum energy loss'
    )

    # Value annotations
    ax.annotate(
        f'{energy_losses[minimum_idx]:,.0f} kWh',
        (dates[minimum_idx], energy_losses[minimum_idx]),
        xytext=(0, 12),
        textcoords='offset points',
        ha='center',
        fontsize=9,
    )
    
    for i, (start_idx, end_idx, failures) in enumerate(failure_ranges):
        # Time boundaries of the excluded interval
        left = dates[start_idx] - (dates[1] - dates[0]) / 2
        right = dates[end_idx] + (dates[1] - dates[0]) / 2

        # Grey background to identify the excluded region
        ax.axvspan(
            left,
            right,
            facecolor='#F1F3F5',
            edgecolor='none',
            alpha=0.85,
            zorder=2
        )

        # Diagonal hatching to clearly mark invalid results
        ax.axvspan(
            left,
            right,
            facecolor='none',
            edgecolor='#AAB2BA',
            hatch='///',
            linewidth=0,
            zorder=4,
            alpha=0.6,
        )

        ax.text(
            dates[start_idx] + (dates[end_idx] - dates[start_idx]) / 2,
            0.7-i/10,
            '\n'.join(failure.split('_', 2)[-1].replace('_', ' ') for failure in failures),
            transform=ax.get_xaxis_transform(),
            ha='center',
            va='center',
            fontsize=7,
            fontweight='bold'
        )
        
    if failure_ranges:
        start_idx_min = min(failure_ranges, key=lambda x: x[0])[0]
        end_idx_max = max(failure_ranges, key=lambda x: x[1])[1]
        
        ax.text(
                dates[start_idx_min] + (dates[end_idx_max] - dates[start_idx_min]) / 2,
                0.9,
                'Failure not corrected',
                transform=ax.get_xaxis_transform(),
                ha='center',
                va='center',
                fontsize=9,
                fontweight='bold'
            )

    ax.set_xticks(dates[::12])
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))
    # X-axis formatting
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    
    # Labels and title
    ax.set_xlabel('Work start date', fontsize=11, labelpad=12)
    ax.set_ylabel('Total energy losses (kWh)', fontsize=11, labelpad=12)

    ax.set_title(
        'Total Energy Losses vs. Work Start Date',
        fontsize=15,
        fontweight='bold',
        loc='left',
        pad=20
    )

    # Styling
    ax.grid(axis='y', linestyle='--', alpha=0.25)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
    ax.tick_params(axis='both', length=0, pad=8)
    ax.legend(frameon=False, loc='best')

    fig.autofmt_xdate()
    fig.tight_layout()
    
    if save_dir:
        plt.savefig(f"{save_dir}/total_energy_losses_vs_Start_Date.png", dpi=300, bbox_inches='tight')
    plt.close()