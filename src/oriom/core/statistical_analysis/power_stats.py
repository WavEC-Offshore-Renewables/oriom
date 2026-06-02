import pandas as pd
import os
import logging

from oriom.utils.aux_functions import convert_stringtime, save_file_csv


def average_pwind(
        timeseries_with_power: pd.DataFrame,
        out_dir: str=None
)->dict:
    """
    Args:
        timeseries_with_power (:obj:`pd.DataFrame`): DataFrame with
        the timeseries of the power of the entire wind farm. Data in kW
        out_dir (:obj:`str`*optional*): Output directory to save the
        	power averaged per month.
    """
    # Check input file
    timeseries_with_power.reset_index(inplace=True)

    timeseries_with_power = convert_stringtime(timeseries_with_power)

    columns_mandatory = [
            'datetime',
            'p_wind'
    ]
    if any([
            column not in timeseries_with_power
            for column in columns_mandatory
    ]) is True:
        _e = '"datetime", p_wind"'
        logging.error(_e)
        raise NameError(_e)

    # Calculate the percentiles for each term
    month = list(range(1,13))

    dict_power_wind = dict()

    for m in month:
        df_p = pd.DataFrame()
        df_p = timeseries_with_power[timeseries_with_power['datetime'].dt.month == m]
        dict_power_wind[m] = df_p['p_wind'].mean()

    # Save wind power statistics as a CSV
    if out_dir is not None:
        df_power_wind = dict_power_wind
        df_power_wind = pd.DataFrame.from_dict(
                data=dict_power_wind,
                orient='index'
        )

        save_file_csv(df_power_wind, out_dir,'power_wind_stat.csv', indexing = True)
        _i = 'Wind Power statistics: saved as '
        _i += '"%s".' % os.path.join(out_dir, 'power_wind_stat.csv')

        logging.info(_i)

    return dict_power_wind


def average_pwave(
        timeseries_with_power : pd.DataFrame,
        out_dir: str=None
):
    """
    Args:
        timeseries_with_power (:obj:`pd.DataFrame`): DataFrame with
        the timeseries of the power of the wave farm. Data in kW
        out_dir (:obj:`str`*optional*): Output directory to save the hourly
        power averaged per month.
    """
    # Check input file
    timeseries_with_power.reset_index(inplace=True)

    timeseries_with_power = convert_stringtime(timeseries_with_power)

    columns_mandatory = [
            'datetime',
            'p_wave'
    ]
    if any([
            column not in timeseries_with_power
            for column in columns_mandatory
    ]) is True:
        _e = '"datetime", p_wave"'
        logging.error(_e)
        raise NameError(_e)

    # Calculate the percentiles for each term
    month = list(range(1,13))

    dict_power_wave = dict()

    for m in month:
        df_p = pd.DataFrame()
        df_p = timeseries_with_power[timeseries_with_power['datetime'].dt.month == m]
        dict_power_wave[m] = df_p['p_wave'].mean()

    # Save wave power statistics as a CSV
    if out_dir is not None:
        df_power_wave = dict_power_wave
        df_power_wave = pd.DataFrame.from_dict(
                data=dict_power_wave,
                orient='index'
        )

        save_file_csv(df_power_wave, out_dir,'power_wave_stat.csv', indexing = True)
        _i = 'Wave Power statistics: saved as '
        _i += '"%s".' % os.path.join(out_dir, 'power_wave_stat.csv')

        logging.info(_i)

    return dict_power_wave


if __name__ == '__main__':

    import os
    from oriom.classes.Metocean import Metocean
    from oriom.classes.Techs.Power import Curve as PowerCurve
    from oriom.classes.Techs.Power import Matrix as PowerMatrix
    from oriom.core.timeseries_analysis.timestep_power import add_power_columns

    pcurve_wind = PowerCurve(
            file_=os.path.join(os.getcwd(), 'tests', 'test_files', 'pcurve_wind.csv'),
            c_in=4,
            c_off=25,
            rated=8000
    )

    pmatrix_wave = PowerMatrix(
            file_=os.path.join(os.getcwd(), 'tests', 'test_files', 'pmatrix_wave.csv'),
            rated=450
    )

    metocean = Metocean(
            file_=os.path.join(os.getcwd(), 'tests', 'test_files', 'metocean', 'metocean_dummy.csv'),
            latitude=41.0,
            longitude=-9.0,
            h_ws_measurements=10
    )
    metocean.generateTe()
    metocean.add_wind_speed_h_hub_column()

    metocean_w_power_columns = add_power_columns(
        df_metocean=metocean.df_timeseries,
        pcurve_wind=pcurve_wind,
        pmatrix_wave=pmatrix_wave,
        ndevices_wind=3,
        ndevices_wave=10,
    )
