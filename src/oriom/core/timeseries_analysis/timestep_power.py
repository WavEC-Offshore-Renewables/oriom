# Import packages
import logging
import pandas as pd
import numpy as np
import os

# Import classes
from oriom.classes import Metocean
from oriom.classes.Techs.Power import Curve as PowerCurve
from oriom.classes.Techs.Power import Matrix


def add_power_columns(
        df_metocean: pd.DataFrame,
        pcurve_wind: object,
        pmatrix_wave: object,
        ndevices_wind: int=0,
        ndevices_wave: int=0,
        out_dir: str=None
) -> pd.DataFrame:
    """For a given timeseries of metocean data, this function adds three
    columns of power production for the total farm divided by tech:
    wind power, wave power and pv power; to that table taking into
    consideration wind and wave conditions for that timestep. Results are in kW

    Args:
        df_metocean (:obj:`pandas.DataFrame`): Metocean timeseries table. Rows
            as timesteps and coluns as sea conditions. Must contain a column
            named "ws_hub" with the wind speed correct at the turbine's
            hub height.
        pcurve_wind (:obj:`PowerCurve`, *optional*): Power curve for the WTGs.
            Defaults to ``None``.
        pmatrix_wave (:obj:`PowerMatrix`, *optional*): Power matrix for the
            WECs. Defaults to ``None``.
        ndevices_wind (int, *optional*): Number of WTGs for the farm.
            Defaults to ``0``.
        ndevices_wave (int, *optional*): Number of WECs for the farm.
            Defaults to ``0``.
        out_dir (str, *optional*): Output directory folder path.
            Defaults to ``None``.

    Raises:
        ValueError: if a :attr:`pcurve_wind` is defined and the
            :attr:`ndevices_wind` is ``0``.
        ValueError: if a :attr:`pmatrix_wave` is defined and the
            :attr:`ndevices_wave` is ``0``.

    Returns:
        :class:`pandas.DataFrame`: Table with timesteps as rows and three new
        columns with the average power produced per technology for each
        timestep. The units of the three columns is killowatt hour (kWh).
            :obj:`index`: timestamps of type :class:`pandas.DatetimeIndex`.

            :obj:`columns`:
                (...)

                :obj:`p_wind`: :obj:`float`, dtype: object

                :obj:`p_wave`: :obj:`float`, dtype: object
    """
    timeseries_file_name = 'timeseries_power.csv'
    # Check if there is already a timeseries with power information
    if os.path.exists(os.path.join(str(out_dir), timeseries_file_name)):
        # Recycle this file
        df_metocean = pd.read_csv(
                filepath_or_buffer=os.path.join(out_dir, timeseries_file_name),
                sep=','
        )
        df_metocean['datetime'] = pd.to_datetime(df_metocean['datetime'], format='%Y-%m-%d %H:%M:%S')
        df_metocean.set_index(keys='datetime', drop=True, inplace=True)
        logging.info('Metocean Power: timeseries with power per timestep recycled from "%s".' % os.path.join(out_dir, timeseries_file_name))
        return df_metocean

    # If not, generate power information
    df_metocean["p_wind"] = 0
    df_metocean["p_wind_per_device"] = 0
    df_metocean["p_wave"] = 0
    df_metocean["p_wave_per_device"] = 0

    # Evaluate inputs to ensure that add_power_columns can run
    if pcurve_wind is not None:
        if ndevices_wind < 1:
            logging.error('Metocean Power: Define the number of WTGs.')
            raise ValueError('Define the number of WTGs.')
        df_metocean["p_wind"] = np.nan
    if pmatrix_wave is not None:
        if ndevices_wave < 1:
            logging.error('Metocean Power: Define the number of WECs.')
            raise ValueError('Define the number of WECs.')
        df_metocean["p_wave"] = np.nan

    if "ws_hub" not in df_metocean.columns.to_list():
        _e = '"df_metocean" DataFrame does not contain the "ws_hub"'
        _e+= ' column. Ensure that the "add_wind_speed_h_hub_column" function'
        _e+= ' from the "Metocean" class was run to add this column.'
        logging.error('Metocean Power: ' + _e)
        raise ValueError(_e)

    # Calculate Wind Turbines power per timestep
    if pcurve_wind is not None:
        array_wind_idx = np.linspace(0, len(pcurve_wind.array) - 1, len(pcurve_wind.array))
        df_metocean['p_wind_per_device'] = np.interp(df_metocean['ws_hub'], array_wind_idx, pcurve_wind.array)
        df_metocean[(df_metocean['ws_hub'] < pcurve_wind.c_in) | (df_metocean['ws_hub'] > pcurve_wind.c_off)]['p_wind_per_device'] = 0
        df_metocean['p_wind'] = df_metocean['p_wind_per_device'] * ndevices_wind
        df_metocean['p_wind_per_device'] = df_metocean['p_wind_per_device'].fillna(0)
        df_metocean['p_wind_per_device'] = df_metocean['p_wind_per_device'].round(4)
        df_metocean['p_wind'] = df_metocean['p_wind'].fillna(0)
        df_metocean['p_wind'] = df_metocean['p_wind'].round(4)

    # Calculate WECs power per timestep
    if pmatrix_wave is not None:
        for hss, tp_row in pmatrix_wave.matrix.iterrows():
            hs_min = hss[0]
            hs_max = hss[1]
            df_hs_min = df_metocean['hs'] >= hs_min
            df_hs_max = df_metocean['hs'] < hs_max
            for tps, power in tp_row.items():
                tp_min = tps[0]
                tp_max = tps[1]
                df_tp_min = df_metocean['te'] >= tp_min
                df_tp_max = df_metocean['te'] < tp_max

                filter_ = df_hs_min & df_hs_max & df_tp_min & df_tp_max

                df_metocean['p_wave_per_device'].iloc[filter_] = power

        df_metocean['p_wave'] = df_metocean['p_wave_per_device'] * ndevices_wave
        df_metocean['p_wave_per_device'] = df_metocean['p_wave_per_device'].fillna(0)
        df_metocean['p_wave_per_device'] = df_metocean['p_wave_per_device'].round(4)
        df_metocean['p_wave'] = df_metocean['p_wave'].fillna(0)
        df_metocean['p_wave'] = df_metocean['p_wave'].round(4)

    # Save new timeseries as a CSV
    if out_dir is not None:
        df_metocean.to_csv(
                path_or_buf=os.path.join(out_dir, timeseries_file_name),
                sep=','
        )
        logging.info('Metocean Power: timeseries with power per timestep saved as "%s".' % os.path.join(out_dir, timeseries_file_name))

    return df_metocean


if __name__ == '__main__':
    import os
    pcurve_wind = PowerCurve(
            file_=os.path.join(os.getcwd(), 'tests', 'test_files', 'pcurve_wind.csv'),
            c_in=4,
            c_off=25,
            rated=8000
    )
    pmatrix_wave = Matrix(
            file_=os.path.join(os.getcwd(), 'tests', 'test_files', 'pmatrix_wave.csv'),
            rated=450
    )
    metocean = Metocean(
            file_=os.path.join(os.getcwd(), 'tests', 'test_files', 'metocean', 'metocean_dummy_hourly.csv'),
            latitude=41.615065,
            longitude=-9.348514,
            h_ws_measurements=10
    )
    metocean.generateTe()
    metocean.add_wind_speed_h_hub_column()

    metocean_w_power_columns = add_power_columns(
        df_metocean=metocean.df_timeseries,
        pcurve_wind=pcurve_wind,
        pmatrix_wave=pmatrix_wave,
        ndevices_wind=1,
        ndevices_wave=1
    )
    print(metocean_w_power_columns)
