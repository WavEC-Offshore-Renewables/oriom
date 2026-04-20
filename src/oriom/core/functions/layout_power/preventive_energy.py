import logging
import networkx as nx
import numpy as np
import pandas as pd

from oriom.utils.aux_functions import log_event_convert_stringtime
from oriom.core.functions.layout_power import aux_layout_power_func


COLS = [
    'Date',
    'Event',
    'id',
    'Name',
    'En_loss_kWh',
    'Time_shutdown'
]


def preventive_energy(
    log_events: pd.DataFrame,
    inspections_site_stat: list,
    inspections_port_stat: list,
    start_year: int,
    find_element_class: object,
    n_device_wtg: int=None,
    n_device_wec: int=None,
    n_device_pv: int=None,
    G_wind: nx.DiGraph=None,
    G_wave: nx.DiGraph=None,
    G_pv: nx.DiGraph=None,
    power_wind: dict=None,
    power_wave: dict=None,
    power_pv: dict=None,
    degradation_rate: float=None,
    metocean_timeseries: pd.DataFrame = pd.DataFrame(),
    STATISTIC_ENERGY = False
)->pd.DataFrame:

    """
    Being the events chronologically ordered, for every event the function
    uses the graphs (layout) to understand the percentage of farm available at that
    instant and returns the relative power farm (power averaged among the month).

    Args:
        log_events (:obj:`pd.DataFrame`): Log of all the events (failure,
            operation, inspection_port, inspection_site).
        inspections_site_stat (:obj:`list`): List of object :class:`InspectionsSiteStat`.
        inspections_port_stat (:obj:`list`): List of object :class:`InspectionsPortStat`.
        start_year (:obj:`int`): start year of the project.
        find_element_class (Find_element_class): Initialized instance that provides fast access to operations, vessels and failures via internal dictionaries.
        n_device_wtg (:obj:`int`, optional): Number of devices of WTG.
        n_device_wec (:obj:`int`, optional):  Number of devices of WEC.
        n_device_pv (:obj:`int`, optional): Number of devices of PV.
        G_wind (:obj:`nx.DiGraph`, optional): Graph of WTG farm. Defalut as None
        G_wave (:obj:`nx.DiGraph`, optional): Graph of WEC farm. Defalut as None
        G_pv (:obj:`nx.DiGraph`, optional): Graph of PV farm. Defalut as None
        power_wind (:obj:`dict`): Statistical power wind.
        power_wave (:obj:`dict`): statistical power wave.
        power_pv (:obj:`dict`): statistical power pv.
        degradation_rate (:obj:`float`): yearly degradation rate for PV farm in %.
        metocean_timeseries (:obj:`pd.DataFrame`, *optional*): DataFrame with metocean timeseries data and power ORE production.
        STATISTIC_ENERGY (bool): Boolean to choose if corrective operation losses are calculated with power averaged

    Raises:
        ValueError: if "n_device_wtg" is defined and  "power_wind" is not defined.
        ValueError: if "n_device_wec" is defined and "power_wave" is not defined.
        ValueError: if "n_device_pv" is defined and "power_pv" is not defined.
        ValueError: if "power_pv" is defined and "degradation_rate" not defined.

    Returns:
        dict{
            pd.DataFrame: dataframe with all the inspections events, percentage farm available and
                power for WTG farm.
            pd.DataFrame: dataframe with all the inspections events, percentage farm available and
                power for WEC farm.
            pd.DataFrame: dataframe with all the inpsections events, percentage farm available and
                power for PV farm.
        }
    """

    def preventive_rows(
        log_events: pd.DataFrame,
        prefix_list: list,
        inspections_site_stat: list,
        inspections_port_stat: list,
        find_element_class: object,
        n_device_tot: int,
        shut_attribute: str,
        start_year: int,
        G_tech: nx.DiGraph,
        dict_power: dict,
        degradation_rate: float=None,
        metocean_timeseries: pd.DataFrame = pd.DataFrame(),
        STATISTIC_ENERGY = False
    )->pd.DataFrame:
        """For every inspection it returns the energy loss in kWh.

        Args:
            log_events (:obj:`pd.DataFrame`): Log of all the events (failure,
                operation, inspection_port, inspection_site).
            prefix_list: (:obj:`list`): Contains the prefix to study the log_events
                for each technolog y['opv','oce'] or ['ofw', 'oce'] or ['owc', 'oce'].
            inspections_site_stat (:obj:`list`): List of object :class:`InspectionsSiteStat`.
            inspections_port_stat (:obj:`list`): List of object :class:`InspectionsPortStat`.
            find_element_class (Find_element_class): Initialized instance that provides fast access to operations, vessels and failures via internal dictionaries.
            n_device_tot (:obj:´int´): Number of devices total.
            shut_attribute (:obj:`str`): str related to the technology.
            start_year (:obj:`int`): Start year of the project.
            G_wind (:obj:`nx.DiGraph`): Graph of tech farm.
            dict_power (:obj:`dict`): Dictionary of monthly power.
            degradation_rate (:obj:`float`, optional): Degradation rate of the PV power,
            metocean_timeseries (:obj:`pd.DataFrame`, *optional*): DataFrame with metocean timeseries data and power ORE production.
            STATISTIC_ENERGY (bool): Boolean to choose if corrective operation losses are calculated with power averaged

        Returns:
            pd.DataFrame: dataframe with all the inspections events, energy losses of the farm.
        """

        power_level_dict = {}

        log_insp = log_events[log_events['event'].isin(['inspection_site','inspection_port'])]
        list_inspections = log_insp['id'].tolist()
        list_inspections = list(set(list_inspections))
        list_inspections = [c for c in list_inspections if c[0:3] in prefix_list]
        log_inspections = pd.DataFrame(columns=COLS)

        power_level_dict = aux_layout_power_func.take_power_level_inspections(
            G_tech = G_tech,
            inspections_port_stat=inspections_port_stat,
            inspections_site_stat=inspections_site_stat
        )

        for inspection in list_inspections:
            inspection_class = find_element_class.find_operation_stats(inspection)
            insp = inspection_class.insp_class
            level_insp = inspection_class.insp_class.level
            double_shift = inspection_class.insp_class.double_shift
            log_aux = log_insp[log_insp['id'] == inspection_class.id]

            if STATISTIC_ENERGY or "opv" in prefix_list:
                for _, r in log_aux.iterrows():
                    # find shutdown_hours
                    try:
                        shutdown_hours_dict = inspection_class.shutdown_dict
                    except AttributeError:
                        shutdown_hours_dict = getattr(inspection_class, shut_attribute)
                    start_insp_date = r['d_trigger']
                    shutdown_hours_dict = {int(k): v for k, v in shutdown_hours_dict.items()}

                    selected_month = aux_layout_power_func.take_month_inspection(
                        start_insp_date = start_insp_date,
                        row = r,
                        shutdown_hours_dict = shutdown_hours_dict
                    )

                    en_loss = aux_layout_power_func.statistical_power_preventive_evaluation(
                        dict_power = dict_power,
                        shutdown_hours_dict = shutdown_hours_dict,
                        date = start_insp_date,
                        n_device_tot = n_device_tot,
                        power_level = power_level_dict[level_insp],
                        degradation_rate = degradation_rate,
                        start_year = start_year,
                        double_shift = double_shift,
                        selected_month = selected_month
                    )

                    shutdown_hours = shutdown_hours_dict[selected_month]
                    line_insp = pd.DataFrame([[
                        start_insp_date,
                        r['event'],
                        r['id'],
                        inspection_class.insp_class.name,
                        en_loss,
                        shutdown_hours
                    ]], columns=COLS)

                    log_inspections = pd.concat([log_inspections,line_insp], ignore_index=True)
            else:
                inspection_dates = []
                if not getattr(insp, 'op_tow_port', False):
                    inspection_dates = aux_layout_power_func.take_date_inspection_oper_scheduler(
                        log_aux = log_aux, oper_schedule=insp.ts_data.oper_sched
                    )

                energy_list, shutdown_hour_list = aux_layout_power_func.timeseries_power_preventive_evaluation(
                    insp = insp,
                    inspection_dates = inspection_dates,
                    metocean_timeseries = metocean_timeseries,
                    power_level = power_level_dict[level_insp],
                    tech1='wind' if prefix_list[0] == 'ofw' else 'wave'
                )

                for i, (_, r) in enumerate(log_aux.iterrows()):
                    line_insp = pd.DataFrame([[
                        r['d_trigger'],
                        r['event'],
                        r['id'],
                        inspection_class.insp_class.name,
                        energy_list[i],
                        shutdown_hour_list[i]
                    ]], columns=COLS)

                    log_inspections = pd.concat([log_inspections,line_insp], ignore_index=True)

        log_inspections.sort_values(by='Date',inplace=True)
        log_inspections.reset_index(drop=True,inplace=True)

        return log_inspections


    if power_wind is not None:
        dict_power_wind = power_wind
    if power_wave is not None:
        dict_power_wave = power_wave
    if power_pv is not None:
        dict_power_pv=power_pv

    log_events = log_event_convert_stringtime(log_events)

    df_wind = pd.DataFrame()
    df_wave = pd.DataFrame()
    df_pv = pd.DataFrame()

    if n_device_wtg is not None:
        prefix_list = ['ofw', 'oce']
        if dict_power_wind is None:
            _e = '"n_device_wtg" defined and "power_wind" not defined.'
            logging.error('Layout perc: '+_e)
            raise ValueError(_e)

        df_wind = preventive_rows(
            log_events=log_events,
            prefix_list=prefix_list,
            find_element_class=find_element_class,
            inspections_site_stat=inspections_site_stat,
            inspections_port_stat=inspections_port_stat,
            n_device_tot=n_device_wtg,
            shut_attribute='wtg_shutdown_dict',
            start_year=start_year,
            G_tech = G_wind,
            dict_power=dict_power_wind,
            metocean_timeseries=metocean_timeseries,
            STATISTIC_ENERGY=STATISTIC_ENERGY
        )

    if n_device_wec is not None:
        prefix_list = ['owc', 'oce']
        if dict_power_wave is None:
            _e = '"n_device_wec" defined and "power_wave" not defined.'
            logging.error('Layout perc: '+_e)
            raise ValueError(_e)

        df_wave = preventive_rows(
            log_events=log_events,
            prefix_list=prefix_list,
            inspections_site_stat=inspections_site_stat,
            inspections_port_stat=inspections_port_stat,
            find_element_class=find_element_class,
            n_device_tot=n_device_wec,
            shut_attribute='wec_shutdown_dict',
            start_year=start_year,
            G_tech = G_wave,
            dict_power=dict_power_wave,
            metocean_timeseries=metocean_timeseries,
            STATISTIC_ENERGY=STATISTIC_ENERGY
        )

    if n_device_pv is not None:
        prefix_list = ['opv', 'oce']
        if dict_power_pv is None:
            _e = '"n_device_pv" defined and "power_pv" not defined.'
            logging.error('Layout perc: '+_e)
            raise ValueError(_e)

        df_pv = preventive_rows(
            log_events=log_events,
            prefix_list=prefix_list,
            inspections_site_stat=inspections_site_stat,
            inspections_port_stat=inspections_port_stat,
            find_element_class=find_element_class,
            n_device_tot=n_device_pv,
            shut_attribute='pv_shutdown_dict',
            start_year=start_year,
            G_tech = G_pv,
            dict_power=dict_power_pv,
            degradation_rate=degradation_rate,
            metocean_timeseries=metocean_timeseries,
            STATISTIC_ENERGY=STATISTIC_ENERGY
        )

    return {'wind': df_wind, 'wave': df_wave, 'pv': df_pv}


if __name__ == '__main__':
    pass