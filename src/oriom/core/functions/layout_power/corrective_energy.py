import pandas as pd
import logging
import networkx as nx
import time

from oriom.utils.read_dataframe_value import approximate_hourly_data
from oriom.utils import aux_functions

from oriom.core.functions.layout_power.layout_percentage import return_percentage
from oriom.core.functions.layout_power.pv_power_calculation import calculate_energy_loss_pv


def timeseries_energy_calculation(df_tech: pd.DataFrame, timeseries: pd.DataFrame, tech1: str)-> list:
    """
    For each relevant event date take the sum of power produced
    by the entire farm from start date to end date. Return a list of energy values."""

    energy_list = []
    power_col = 'p_' + tech1
    for i in range(len(df_tech) - 1):
        row = df_tech.iloc[i]
        next_row = df_tech.iloc[i+1]
        date_start = approximate_hourly_data(row['Date'])
        date_end = approximate_hourly_data(next_row['Date'])
        mask = (timeseries.index >= date_start) & (timeseries.index < date_end)
        power_data = timeseries.loc[mask, power_col]
        energy_list.append(power_data.sum())
    energy_list.append(energy_list[-1])
    return energy_list


def manage_energy_calculation(
            df_tech: pd.DataFrame,
            series_power: pd.Series,
            STATISTIC_ENERGY: bool,
            metocean_timeseries: pd.DataFrame,
            tech1: str
    ):

    if STATISTIC_ENERGY:
        df_tech['Power_loss_kW'] = ((100 - df_tech['Perc_availability']) * df_tech['Date'].dt.month.map(series_power) / 100)
    else:
        df_tech.sort_values(by='Date', inplace=True)
        df_tech.reset_index(drop=True, inplace=True)
        energy_list = timeseries_energy_calculation(df_tech, metocean_timeseries, tech1)
        # It actually calculates already energtimeseries_energy_calculationy loss losses, not Power losses
        df_tech['Power_loss_kW'] = energy_list * (100-df_tech['Perc_availability'])/100

        # Sort and reset index
        df_tech.sort_values(by='Date', inplace=True)
        df_tech.reset_index(drop=True, inplace=True)

    return df_tech


def corrective_layout(
    log_events: pd.DataFrame,
    start_year: int,
    start_month: int,
    n_lifetime: int,
    operations_corrective_stat: list,
    find_element_class: object,
    n_device_wtg: int=None,
    n_device_wec: int=None,
    n_device_pv: int=None,
    G_wind: nx.DiGraph=None,
    G_wave: nx.DiGraph=None,
    G_pv: nx.DiGraph=None,
    dict_power_wind: dict=None,
    dict_power_wave: dict=None,
    dict_power_pv: pd.DataFrame=None,
    degradation_rate: float=None,
    n_strings_per_inv: int=None,
    n_modules_per_strings: int=None,
    max_failure_module: int=None,
    metocean_timeseries: pd.DataFrame = pd.DataFrame(),
    STATISTIC_ENERGY = False
)-> pd.DataFrame:

    """Based on the log of events it picks the locations at which the operation is being performed.
    When the operation starts -> shutdown(Y/N)
    When the operation end -> the failure is fixed
    Being the events chronologically ordered, for every event the function uses the graphs (layout)
    to understand the percentage of farm available at that instant and returns the relative power farm
    (power averaged among the month).

    Args:
        log_events (:obj:`pd.DataFrame`): Log of all the events (failure,
            operation, inspection_port, inspection_site, tow).
        start_year (:obj:`int`): Start_year of the project.
        start_month (:obj:`int`): Start_month of the project
        n_lifetime (:obj:`int`): Lifetime of the project in years.
        operations_corrective_stat (:obj:`list`): List of objects :class:`OperationsCorrectiveStat`.
        find_element_class (Find_element_class): Initialized instance that provides fast access to operations, vessels and failures via internal dictionaries.
        n_device_wtg (:obj:`int`, optional): Number of devices of WTG.  Defalut as None
        n_device_wec (:obj:`int`, optional):  Number of devices of WEC. Defalut as None
        n_device_pv (:obj:`int`, optional): Number of devices of PV. Defalut as None
        G_wind (:obj:`nx.DiGraph`, optional): Graph of WTG farm. Defalut as None
        G_wave (:obj:`nx.DiGraph`, optional): Graph of WEC farm. Defalut as None
        G_pv (:obj:`nx.DiGraph`, optional): Graph of PV farm. Defalut as None
        power_wind (:obj:`dict`, optional): Statistical power wind. Defalut as None
        power_wave (:obj:`dict`, optional): Statistical power wave. Defalut as None
        power_pv (:obj:`dict`, optional): Statistical power pv. Defalut as None
        degradation_rate (:obj:`float`): Yearly degradation rate for PV farm in %. Defalut as None
        n_strings_per_inv (:obj:`int`, *optional*): number of string each inverter Defalut as None
        n_modules_per_strings (:obj:`int`, *optional*): number of modules each string Defalut as None
        max_failure_module (:obj:`int`, *optional*): number of failed module allowed each string Defalut as None
        metocean_timeseries (:obj:`pd.DataFrame`, *optional*): DataFrame with metocean timeseries data and power ORE production.
        STATISTIC_ENERGY (bool): Boolean to choose if corrective operation losses are calculated with power averaged

    Raises:
        ValueError: if "power_pv" is defined and "degradation_rate" not defined.
        ValueError: if the level of failure is not recognized.
        ValueError: if failure event found and corrective operation not found
            in case the failure is triggering an intervention.
        ValueError: if operation corrective found and failure event not found.
        ValueError: if "n_device_wtg" defined and "G_wind" not defined.
        ValueError: if "n_device_wec" defined and "G_wave" not defined.
        ValueError: if "n_device_pv" defined and "G_pv" not defined.
        ValueError: if "n_device_wtg" defined and "power_wind" not defined.
        ValueError: if "n_device_wec" defined and "power_wave" not defined.
        ValueError: if "n_device_pv" defined and "power_pv" not defined.

    Returns:
        pd.DataFrame: dataframe with all the failure and operationsevents,
            percentage farm available and power for WTG farm.
        pd.DataFrame: dataframe with all the failure and operationsevents,
            percentage farm available and power for WEC farm.
        pd.DataFrame: dataframe with all the failure and operationsevents,
            percentage farm available and power for PV farm.
    """

    if n_device_wtg is not None and G_wind is None:
        logging.error('Layout perc: n_device_wtg defined and graph missing')
        raise ValueError('Layout perc: n_device_wtg defined and graph missing')
    if n_device_wec is not None and G_wave is None:
        logging.error('Layout perc: n_device_wec defined and graph missing')
        raise ValueError('Layout perc: n_device_wec defined and graph missing')
    if n_device_pv is not None and G_pv is None:
        logging.error('Layout perc: n_device_pv defined and graph missing')
        raise ValueError('Layout perc: n_device_pv defined and graph missing')


    df_wind, df_wave, df_pv = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Transform power dict in series (faster calculations)
    series_power_wind = pd.Series(dict_power_wind)
    series_power_wave = pd.Series(dict_power_wave)
    series_power_pv = dict_power_pv

    # Filter the log_events file for the corrective events and only if create a shutdown of a component
    log_events = log_events[~log_events['event'].isin(['inspection_site','inspection_port', 'mobilisation', 'mobilisation_merged'])]

    if n_device_wtg is not None:
        tech1 = 'wind'
        prefix_list = ['ofw', 'oce']
        df_wind = return_percentage(
            log_events=log_events,
            prefix_list=prefix_list,
            operations_corrective_stat=operations_corrective_stat,
            G=G_wind,
            shut_attribute='wtg_shutdown_dict',
            start_year=start_year,
            start_month=start_month,
            n_lifetime=n_lifetime,
            n_devices=n_device_wtg,
            tech = tech1,
            find_element_class = find_element_class
        )
        if series_power_wind is None:
            _e = '"n_device_wtg" defined and "power_wind" not defined.'
            logging.error('Layout perc: '+_e)
            raise ValueError(_e)

        df_wind = manage_energy_calculation(
            df_tech = df_wind,
            series_power = series_power_wind,
            STATISTIC_ENERGY = STATISTIC_ENERGY,
            metocean_timeseries = metocean_timeseries,
            tech1 = tech1
        )

    if n_device_wec is not None:
        tech1 = 'wave'
        prefix_list = ['owc', 'oce']
        df_wave = return_percentage(
            log_events=log_events,
            prefix_list=prefix_list,
            operations_corrective_stat=operations_corrective_stat,
            G=G_wave,
            shut_attribute='wec_shutdown_dict',
            start_year=start_year,
            start_month=start_month,
            n_lifetime=n_lifetime,
            n_devices=n_device_wec,
            tech = tech1,
            find_element_class = find_element_class
        )
        if series_power_wave is None:
            _e = '"n_device_wec" defined and "power_wave" not defined.'
            logging.error('Layout perc: '+_e)
            raise ValueError(_e)

        df_wave = manage_energy_calculation(
            df_tech = df_wave,
            series_power = series_power_wave,
            STATISTIC_ENERGY = STATISTIC_ENERGY,
            metocean_timeseries = metocean_timeseries,
            tech1 = tech1
        )

    if n_device_pv is not None:
        tech1 = 'PV'
        prefix_list = ['opv', 'oce']
        df_pv = return_percentage(
            log_events=log_events,
            prefix_list=prefix_list,
            operations_corrective_stat=operations_corrective_stat,
            G=G_pv,
            shut_attribute='pv_shutdown_dict',
            start_year=start_year,
            start_month=start_month,
            n_lifetime=n_lifetime,
            n_devices=n_device_pv,
            tech = tech1,
            find_element_class = find_element_class,
            n_strings_per_inv = n_strings_per_inv,
            n_pv_per_string = int(n_modules_per_strings),
            max_failure_module=max_failure_module
        )

        if series_power_pv is None:
            _e = '"n_device_pv" defined and "power_pv" not defined.'
            logging.error('Layout perc: '+_e)
            raise ValueError(_e)

        df_pv = aux_functions.convert_stringtime(df = df_pv, dt_column = 'Date')
        df_pv["Power_loss_kW"] = 0.0
        # Statistical calculation of energy losses
        for m in series_power_pv.columns:
            df_month = df_pv[df_pv['Date'].dt.month == m ]
            if df_month.empty:
                continue

            df_month['Date_next'] = df_month['Date'].shift(-1)

            # What is calculated here is not power losses but Energy losses
            df_month['Power_loss_kW'] = df_month.apply(
                lambda r: calculate_energy_loss_pv(r, series_power_pv, start_year, degradation_rate),
                axis=1
            )

            df_pv.loc[df_month.index, 'Power_loss_kW'] = df_month['Power_loss_kW']

        # Sort and reset index
        df_pv.sort_values(by='Date', inplace=True)
        df_pv.reset_index(drop=True, inplace=True)

    return df_wind, df_wave, df_pv