import pandas as pd
import networkx as nx
import logging
import os 
from itertools import repeat

from oriom.common.constants import LIST_MONTHS, DICT_DAYS
from oriom.utils import aux_functions
from oriom.core.functions.layout_power.corrective_energy import corrective_layout
from oriom.core.functions.layout_power.preventive_energy import preventive_energy


def recicle_file(inputs, r, tech_devices):
    """ 
    Check and reuse corrective and preventive data if are available
        Both files must be present of the technology
    """

    
    op_types = ['corrective', 'preventive']
    data = {op: {} for op in op_types}
    paths = {}
    need_recompute = False
    energy_path = None

    try:
        energy_path = os.path.join(inputs.general.powerevent_file["value"], f"result_{r}")
    except TypeError:
        need_recompute = True

    for tech, dev_tech in tech_devices.items():
        paths[tech] = {}
        # avoid if no device installed
        if dev_tech is None:
            for op_type in op_types:
                data[op_type][tech] = pd.DataFrame()
            continue

        if energy_path:
            for op_type in op_types:
                paths[tech][op_type] = os.path.join(
                    energy_path, f"{tech}_{op_type}_energy.csv"
                )

            # Check if exist
            tech_files_exist = all(os.path.exists(paths[tech][op]) for op in op_types)
            # recicle
            if tech_files_exist:
                for op_type in op_types:
                    df = pd.read_csv(paths[tech][op_type])
                    if not df.empty:
                        aux_functions.convert_stringtime(df, 'Date')

                    data[op_type][tech] = df
            else:
                need_recompute = True
                break

    return data, need_recompute

def config_energy_availability(G_layouts: dict, farm_technologies: object):
    try:
        G_wind_copy = G_layouts["G_wind"].copy()
    except AttributeError:
        G_wind_copy = None

    try:
        G_wave_copy = G_layouts["G_wave"].copy()
    except AttributeError:
        G_wave_copy = None

    try:
        G_pv_copy = G_layouts["G_pv"].copy()
    except AttributeError:
        G_pv_copy = None

    if (
        farm_technologies.power.pv_number_devices is not None
        and farm_technologies.pv.number_strings > 0
        and farm_technologies.pv.number_inverters > 0
    ):
        n_modules_per_strings = (
                farm_technologies.power.pv_number_devices/
                (farm_technologies.pv.number_strings*farm_technologies.pv.number_inverters)
            )
        n_strings_per_inv = farm_technologies.pv.number_strings
        max_failure_module = farm_technologies.power.pv_max_failure_module

    else:
        n_strings_per_inv = None
        n_modules_per_strings = None
        max_failure_module = None
    
    return {
        'G_wind_copy': G_wind_copy,
        'G_wave_copy': G_wave_copy,
        'G_pv_copy': G_pv_copy,
        'n_modules_per_strings': n_modules_per_strings,
        'n_strings_per_inv': n_strings_per_inv,
        'max_failure_module': max_failure_module
    }


def fix_values(
        df_fixing: pd.DataFrame,
        column_name: str
):
    '''
    Fix values of En_availab and Time_availab column due to the imprecision of summing preventive maintenance on failed component
    '''

    df_fixing.loc[df_fixing[column_name] > 100, column_name] = 100
    df_fixing.loc[df_fixing[column_name] < 0.1, column_name] = 0


def sum_by_month_year(timeseries, year, month, power_col):
    mask = (timeseries.index.year == year) & (timeseries.index.month == month)
    total = timeseries.loc[mask, power_col].sum()
    return total


def calculate_energy(dict_power, dict_days, key, y, start_year, hour_energy,
                     degradation_rate, ENERGY_STATISTICAL_CALCULATION,
                     metocean_timeseries=None, power_col=None):
    """ Calculate energy data"""
    if any(isinstance(v, dict) for v in dict_power.values()):
        p = sum(dict_power[key].values()) * dict_days[key] * hour_energy
        for _ in range(y - start_year):
            p -= p * degradation_rate / 100
        return p
    else:
        if ENERGY_STATISTICAL_CALCULATION:
            return dict_power[key] * dict_days[key] * hour_energy
        else:
            return sum_by_month_year(metocean_timeseries, y, key, power_col)


def get_energy_data(df, year, month=None, mode='preventive'):
    """
    Extract energetic data (loss, shutdown, operative time)
    Manage annual and monthly case.
    """
    try:
        data = df[df['Date'].dt.year == year]
        if month is not None:
            data = data[data['Date'].dt.month == month]
        list_months = data['Date'].dt.month if not data.empty else []

        if mode == 'preventive':
            loss = data['En_loss_kWh'].sum()
            shutdown = data['Time_shutdown'].sum()
            time_op = None
        else:  # corrective
            loss = data['En_loss_kWh'].sum()
            shutdown = data['Time_operation'].sum()
            time_op = data['hour_diff_next'].sum()
        return list_months, loss, shutdown, time_op
    except (AttributeError, KeyError):
        # returns empty values if df is empty or columns not found (type operations not present)
        return [], 0, 0, None


def energy_availability(
    inputs: object,
    r: int,
    log_events_energy: pd.DataFrame,
    operations_corrective_stat: list,
    inspections_site_stat: list,
    inspections_port_stat: list,
    find_element_class,
    power_wind=None,
    power_wave=None,
    power_pv=None,
    degradation_rate: float=None,
    n_device_wtg: int=None,
    n_device_wec: int=None,
    n_device_pv: int=None,
    G_wind: nx.DiGraph=None,
    G_wave: nx.DiGraph=None,
    G_pv: nx.DiGraph=None,
    n_strings_per_inv: int = None,
    n_modules_per_strings: int = None,
    max_failure_module: int = None,
    metocean_timeseries: pd.DataFrame = pd.DataFrame(),
    ENERGY_STATISTICAL_CALCULATION: bool = False,
    result_dir_r: str = None
)->dict:

    """
    Based on the :func:`corrective_layout` and :func:`preventive_energy`, it returns the energy and time availability per month and year.
    This package is builted only on log_events dataframe as the log_events_merged does not give us the shutdown of the merged operations.

    TODO implement this using log_events_merged operations as deferred merged operations are conducted consequently and so modify the date
        of interventions.

    Args:
        inputs( pbj: object): Object of ``Input`` class
        r (int): number of the simulation,
        log_events (pd.DataFrame): Log of all the events (failure, operation, inspection_port, inspection_site).
        operations_corrective_stat (list): list of objects :class:`OperationsCorrectiveStat`.
        inspections_site_stat (list): list of objects :class:`InspectionsSiteStat`.
        inspections_port_stat (list): list of objects :class:`InspectionsPortStat`.
        find_element_class (Find_element_class): Initialized instance that provides fast access to operations,
            vessels and failures via internal dictionaries.
        dict_power_wind (dict, *optional*): dictionary with the average hourly power production [kW] of wind farm. Default as None
        dict_power_wave (dict,*optional*): dictionary with the average hourly power production [kW] of wave farm. Default as None
        power_pv (:obj:`dict`, *optional*): Statistical power pv (AVG of month and H). Default as None
        degradation_rate (:obj:`float`, *optional*): Yearly degradation rate for PV farm in %. Default as None
        n_device_wtg (:obj:`int`, *optional*): Number of devices of WTG. Default as None
        n_device_wec (:obj:`int`, *optional*):  Number of devices of WEC. Default as None
        n_device_pv (:obj:`int`, *optional*): Number of devices of PV. Default as None
        G_wind (:obj:`nx.DiGraph`, *optional*): Graph of WTG farm. Default as None
        G_wave (:obj:`nx.DiGraph`, *optional*): Graph of WEC farm. Default as None
        G_pv (:obj:`nx.DiGraph`, *optional*): Graph of PV farm. Default as None
        n_strings_per_inv (:obj:`int`, *optional*): number of string each inverter Default as None
        n_modules_per_strings (:obj:`int`, *optional*): number of modules each string Default as None
        max_failure_module (:obj:`int`, *optional*): number of failed module allowed each string Default as None
        metocean_timeseries (pd.DataFrame): Timeseries dataframe with power column
        ENERGY_STATISTICAL_CALCULATION (bool): Boolean to choose if corrective operation losses are calculated with power averaged
            per month or with metocean timeseries. Default as False
        result_dir_r (str): Directory to save temporary results. Default as None

    Raises:
        ValueError: if "power_wind" type is not dict or str.
        ValueError: if "power_wave" type is not dict or str.
        ValueError: if "power_pv" type is not dict or str of DataFrame.
        ValueError: if "power_pv" is defined and "degradation_rate" not defined.

    Returns:
        :obj.`dict` with:
            pd.DataFrame: dataframe with time and energy avaialbility per month and year for WTG farm.
            pd.DataFrame: dataframe with time and energy avaialbility per month and year for WEC farm.
            pd.DataFrame: dataframe with time and energy avaialbility per month and year for PV farm.
    """

    def monthly_yearly_availability(
        df_corrective: pd.DataFrame,
        df_preventive: pd.DataFrame,
        dict_power: pd.DataFrame,
        n_devices: int,
        tech: str,
        degradation_rate: float=None
    ):
        """Based on the farm availability for corrective and preventive, it
        returns the time and energy availabiltiy on a monthly and yearly basis.

        Args:
            df_corrective (pd.DataFrame): Output of :func:`corrective_layout`.
            df_preventive (pd.DataFrame): Output of :func:`preventive_energy`.
            dict_power (dict): Power with monthly power.
            n_devices (:obj:`int`, optional): Number of devices of farm.
            degradation_rate (:obj:`float`, optional): Yearly degradation rate for PV farm in %.
            tech (str): Technology under analisys.

        Returns:
            pd.DataFrame: dataframe with the energy and time availability per month.
            pd.DataFrame: dataframe with the energy and time availability per year.

        """

        # NOTE PV energy calculation differ from wave&wind with PV,
        # Assest the differences as wave, wind power is statisctical average of p_hour for each month so multiply for 24 and days month
        # PV calculation take the sum of hourly avg power so do not need to multiply for 24 h
        if tech == 'wind' or tech == 'wave':
            hour_energy = 24
        elif tech == 'PV':
            hour_energy = 1
        else:
            _e = 'Technology analyzed not found, energy calculation error might occurs'
            logging.error('Layoutper: ' +_e)
            raise ValueError(_e)

        # For Corrective operations
        if df_corrective.empty is False:
            df_corrective['hour_diff_next'] = (df_corrective['Date'].shift(-1) - df_corrective['Date']).dt.total_seconds()/3600
            df_corrective.loc[0,'hour_diff_next'] = 0.0
            if tech != 'PV':
                if ENERGY_STATISTICAL_CALCULATION:
                    df_corrective['En_loss_kWh'] = df_corrective['hour_diff_next']*df_corrective['Power_loss_kW']
                else:
                    df_corrective['En_loss_kWh'] = df_corrective['Power_loss_kW']
            elif tech == 'PV':
                df_corrective['En_loss_kWh'] = df_corrective['Power_loss_kW']
            df_corrective['Time_operation'] = df_corrective['hour_diff_next']*(100-df_corrective['Perc_availability'])/100

        cols_m = ['Years', 'Months', 'En_max_kWh', 'En_loss_kWh', 'En_availability', 'Time_availability']
        cols_y = ['Years', 'En_max_kWh', 'En_loss_kWh', 'En_availability', 'Time_availability']
        energy_availability_m= pd.DataFrame(columns=cols_m)
        energy_availability_y= pd.DataFrame(columns=cols_y)
        if start_month == 1:
            list_years = list(range(start_year,start_year+n_lifetime))
        else:
            list_years = list(range(start_year,start_year+n_lifetime+1))

        years = [r for i in list_years for r in repeat(i,12)]
        years = years[start_month-1:(12*n_lifetime)-1+start_month]
        months = LIST_MONTHS * n_lifetime
        months = months[start_month-1:] + months[: start_month-1]
        energy_availability_m['Years'] = years
        energy_availability_m['Months'] = months
        energy_availability_y['Years'] = list_years

        for y in list_years:
            # --- Annual preventive/corrective ---
            months_p, tot_loss_p, tot_shut_p, _ = get_energy_data(df_preventive, y, mode='preventive')
            months_c, tot_loss_c, tot_shut_c, tot_time = get_energy_data(df_corrective, y, mode='corrective')

            list_months_file = list(set(months_p).union(set(months_c)))
            if tot_time is None:
                tot_time = (12 - start_month) * 30.4 * 24  # fallback

            # --- Annual energy calculation ---
            power_col = f'p_{tech}'
            en_total = [
                calculate_energy(dict_power, DICT_DAYS, k, y, start_year, hour_energy,
                                degradation_rate, ENERGY_STATISTICAL_CALCULATION,
                                metocean_timeseries, power_col)
                for k in list_months_file
            ]
            en_total = sum(en_total)

            # --- Update annual DataFrame ---
            cond_y = (energy_availability_y['Years'] == y)
            energy_availability_y.loc[cond_y, 'En_max_kWh'] = en_total
            energy_availability_y.loc[cond_y, 'En_loss_kWh'] = tot_loss_c + tot_loss_p
            energy_availability_y.loc[cond_y, 'En_availability'] = (en_total - (tot_loss_c + tot_loss_p)) / en_total * 100
            energy_availability_y.loc[cond_y, 'Time_availability'] = ((n_devices * tot_time - (n_devices * tot_shut_c + tot_shut_p)) / (n_devices * tot_time)) * 100

            # --- Monthly preventive/corrective ---
            for m in list_months_file:
                _, tot_loss_c_m, tot_shut_c_m, time_c_m = get_energy_data(df_corrective, y, m, 'corrective')
                _, tot_loss_p_m, tot_shut_p_m, _ = get_energy_data(df_preventive, y, m, 'preventive')

                en_month = calculate_energy(
                    dict_power, DICT_DAYS, m, y, start_year, hour_energy,
                    degradation_rate, ENERGY_STATISTICAL_CALCULATION,
                    metocean_timeseries, power_col
                )

                cond_m = (energy_availability_m['Years'] == y) & (energy_availability_m['Months'] == m)
                energy_availability_m.loc[cond_m, 'En_max_kWh'] = en_month
                energy_availability_m.loc[cond_m, 'En_loss_kWh'] = tot_loss_c_m + tot_loss_p_m
                energy_availability_m.loc[cond_m, 'En_availability'] = (en_month - (tot_loss_c_m + tot_loss_p_m)) / en_month * 100
                energy_availability_m.loc[cond_m, 'Time_availability'] = ((n_devices * time_c_m - (n_devices * tot_shut_c_m + tot_shut_p_m)) / (n_devices * time_c_m)) * 100

                for colum_name in ['En_availability', 'Time_availability']:
                    fix_values(energy_availability_m, colum_name)
                    fix_values(energy_availability_y, colum_name)

        return energy_availability_m, energy_availability_y


    def create_dict_power(
            power_file,
            descr: str,
            degradation_rate: float=None,
            pv:bool=False
        )-> dict:

        """
        Function that take as input the power file of a technology and return a dictionary if power file not empty, otherwise return none.

        Divide the code for pv power and wind/wave power as pv power is averaged per h and months while wind&wave only averaged dayly per month

        Args:
            power_file: power technology file
            descr (str): Description of the technology under analysis ('wind', 'wave', 'pv')
            degradation_rate (float): degradation_rate of the pv modules. Default as None
            pv (bool): flag to divide pv technology evaluation. Default as None

        Return:
            dict of power production divided per months

        Raise:
            ValueError: if the istance of power_file is not str or pd.Dataframe
            ValueError: if the technology analyzed is pv and there is no degradation_rate defined
        """


        if power_file is not None:
            if pv:
                if isinstance(power_file, str):
                    columns = ['hours'] + LIST_MONTHS
                    power_file = pd.read_csv(power_file,names=columns)
                    dict_power_file = {}
                    for k in LIST_MONTHS:
                        dict_power_file.update({k:{}})
                        for i in range(24):
                            dict_power_file[k].update({i:power_file.loc[i,k]})
                elif isinstance(power_file, pd.DataFrame):
                    dict_power_file = {}
                    for k in LIST_MONTHS:
                        dict_power_file.update({k:{}})
                        for i in range(24):
                            dict_power_file[k].update({i:power_file.loc[i,k]})
                else:
                    _e = 'Power pv input format not recognized'
                    logging.error('Layout_power:' +_e)
                    raise ValueError(_e)
                if degradation_rate is None:
                    _e = 'If power pv is defined the degrdation rate must be defined.'
                    logging.error('Layou_power:' +_e)
                    raise ValueError(_e)
            else:
                if isinstance(power_file, str):
                    power_file = pd.read_csv(power_file,names=['Month','Power'])
                    dict_power_file = {}
                    for i in range(1,13):
                        dict_power_file.update({i:power_file.loc[power_file['Month']==i,'Power'].item()})
                elif isinstance(power_file, dict):
                    dict_power_file = power_file
                else:
                    _e = f'Power {descr} input format not recognized'
                    logging.error('Layout_power:' +_e)
                    raise ValueError(_e)

        else: dict_power_file=None

        return dict_power_file


    def create_monthly_yearly_availability(
            df_tech_p: pd.DataFrame,
            df_tech: pd.DataFrame,
            dict_power_tech: dict,
            n_device_tech: int,
            descr: str,
            degradation_rate: float=None
        ):

        """
        Funtion to create monthly_yearly_availability if tech under analysis

        Args:
            df_tech_p (pd.DataFrame): Dataframe of preventive energy availability
            df_tech (pd.DataFrame): Dataframe of corrective energy availability
            dict_power_tech (dict): Dictionary of power production of the technology by months
            n_device_tech (int): Number of devices present for the tech
            descr (str): Description of the technology under analysis ('wind', 'wave', 'pv')
            degradation_rate (float): degradation_rate of the pv modules. Default as None

        Returns:
            availability_tech_m (pd.DataFrame): Monthly dataframe of energy availability
            availability_tech_y (pd.DataFrame): Yearly dataframe of energy availability
        """

        if df_tech_p.empty is False or df_tech.empty is False:
            availability_tech_m, availability_tech_y = monthly_yearly_availability(
                df_corrective=df_tech,
                df_preventive=df_tech_p,
                dict_power=dict_power_tech,
                n_devices=n_device_tech,
                tech = descr,
                degradation_rate=degradation_rate
            )
        else:
            availability_tech_m = pd.DataFrame()
            availability_tech_y = pd.DataFrame()

        return availability_tech_m, availability_tech_y


    log_events = log_events_energy.copy()

    dict_power_wind = create_dict_power(power_wind, 'wind')
    dict_power_wave = create_dict_power(power_wave, 'wave')
    dict_power_pv = create_dict_power(power_pv, 'PV', degradation_rate, True)

    start_year = inputs.stats.start_year["value"]
    start_month = inputs.stats.start_month["value"]
    n_lifetime = inputs.stats.lifetime["value"]
    
    # Reorder all the events by the effective date that occurs (operations for their esecution not for the call)
    mask = ~log_events['event'].isin(['failure', 'inspection_site', 'inspection_port', 'mobilisation'])
    log_events.loc[mask, 'd_trigger'] = log_events.loc[mask, 'd_end_transit_ts']
    log_events = log_events.sort_values(by='d_trigger').reset_index(drop=True)

    tech_devices = {'wind': n_device_wtg, 'wave': n_device_wec, 'pv': n_device_pv}
    energy_data, need_recompute = recicle_file(inputs, r, tech_devices)

    if need_recompute:
        energy_data['corrective'] = corrective_layout(
            log_events = log_events,
            start_year = start_year,
            start_month = start_month,
            n_lifetime = n_lifetime,
            operations_corrective_stat = operations_corrective_stat,
            find_element_class  =  find_element_class,
            n_device_wtg = n_device_wtg,
            n_device_wec = n_device_wec,
            n_device_pv = n_device_pv,
            G_wind = G_wind,
            G_wave = G_wave,
            G_pv = G_pv,
            dict_power_wind = dict_power_wind,
            dict_power_wave = dict_power_wave,
            dict_power_pv = dict_power_pv,
            degradation_rate = degradation_rate,
            n_strings_per_inv  =  n_strings_per_inv,
            n_modules_per_strings = n_modules_per_strings,
            max_failure_module = max_failure_module,
            metocean_timeseries = metocean_timeseries,
            STATISTIC_ENERGY = ENERGY_STATISTICAL_CALCULATION
        )

        energy_data['preventive']  = preventive_energy(
            log_events=log_events,
            inspections_site_stat=inspections_site_stat,
            inspections_port_stat=inspections_port_stat,
            start_year=start_year,
            find_element_class = find_element_class,
            n_device_wtg=n_device_wtg,
            n_device_wec=n_device_wec,
            n_device_pv=n_device_pv,
            G_wind = G_wind,
            G_wave = G_wave,
            G_pv = G_pv,
            power_wind=dict_power_wind,
            power_wave=dict_power_wave,
            power_pv=dict_power_pv,
            degradation_rate=degradation_rate,
            metocean_timeseries = metocean_timeseries,
            STATISTIC_ENERGY = ENERGY_STATISTICAL_CALCULATION
        )
    else:
        logging.info(f'Uploading power file from previous run {r} folder')

    for op_type, tech_dict in energy_data.items():
        for tech, df in tech_dict.items():
            if df.empty is False and result_dir_r:
                filename = f"{tech}_{op_type}_energy.csv"
                aux_functions.save_file_csv(df,result_dir_r,filename) 

    availability_wind_m, availability_wind_y = create_monthly_yearly_availability(
        energy_data['preventive']['wind'], 
        energy_data['corrective']['wind'],
        dict_power_wind, n_device_wtg,
        'wind', degradation_rate=None
    )
    availability_wave_m, availability_wave_y = create_monthly_yearly_availability(
        energy_data['preventive']['wave'],
        energy_data['corrective']['wave'],
        dict_power_wave, n_device_wec,
        'wave',
        degradation_rate=None
    )
    availability_pv_m, availability_pv_y = create_monthly_yearly_availability(
        energy_data['preventive']['pv'],
        energy_data['corrective']['pv'],
        dict_power_pv,
        n_device_pv,
        'PV',
        degradation_rate=degradation_rate
    )

    compressed_output = {
        'Availability_month_wind': availability_wind_m,
        'Availability_year_wind': availability_wind_y,
        'Availability_month_wave': availability_wave_m,
        'Availability_year_wave': availability_wave_y,
        'Availability_month_pv' : availability_pv_m,
        'Availability_year_pv' : availability_pv_y
    }

    return compressed_output


if __name__ == '__main__':
    pass