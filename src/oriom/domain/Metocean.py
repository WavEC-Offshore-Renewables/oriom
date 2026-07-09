# Import packages
import pandas as pd
import numpy as np
from astral import LocationInfo
from astral.sun import sun
import datetime
from copy import deepcopy
from tqdm import tqdm
import os
import logging
from ruamel.yaml import YAML

from oriom.utils import aux_functions
from oriom.core.timeseries_analysis.timestep_power import add_power_columns
from oriom.common.constants import METOCEAN_COLUMNS

try:
    from oriom.core.functions.private.check_files import check_file_exists
except ImportError:
    check_file_exists = None


class Metocean():
    """Metocean timeseries class.

    Attributes:
        file (:obj:`str`): Timeseries file location.
        latitude (:obj:`float`): Latitude for the location of the timeseries.
        longitude (:obj:`float`): Longitude for the location of the timeseries.
        df_timeseries (:obj:`pandas.DataFrame`): Timeseries with metocean data and hourly
            power column of entire farm and for device divided by tech [kW]

    Note:
        When the class is initialized, :func:`_check_attributes`,
        :func:`_read_file` and :func:`_check_timestep_consistency`
        are run.

    Example:
        >>> metocean = Metocean(
        >>>         file_=os.path.join(os.getcwd(), 'tests', 'test_files', 'metocean', 'metocean_dummy.csv'),
        >>>         latitude=41.615065,
        >>>         longitude=-9.348514
        >>> )
        >>> metocean.interpolate()
        >>> metocean.get_daylight_timesteps()
    """
    def __init__(
            self,
            file_: str,
            latitude: float,
            longitude: float,
            stat_inputs: object = None,
            h_ws_measurements: float=None,
            run_funcs: bool=True,
            out_dir: str=None
    ):
        """Initializes :class:`Metocean` class.

        Args:
            file_ (:obj:`str`): Timeseries file path location.
            latitude (:obj:`float`): Latitude for the location of the timeseries.
            longitude (:obj:`float`): Longitude for the location of the timeseries.
            stat_inputs (:obj:`float`): Object of class Input.Statistical.
            h_ws_measurements (:obj:`float`,*optional*): Wind speed measurement height. Defaults to ``None``.
            run_funcs (:obj:`bool`,*optional*): Run inbuilt functions when created. Defaults to ``True``.
            out_dir (:obj:`str`,*optional*): Directory to save the Metocean parameters. Defaults to `None`.
        """
        self.file = str(file_)
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        self.df_timeseries = None

        try:
            self.h_ws_measurements = float(h_ws_measurements)
        except TypeError:
            # ws_measurments defaulted to None
            self.h_ws_measurements = 10
            d_ = "h_ws_measurements input was not defined. It was defaulted to 10 metres"
            logging.warning(d_)

        if run_funcs:
            self._check_attributes()
            self._read_file()
            if stat_inputs:
                self._check_timestep_consistency(stat_inputs)
            else:
                self._check_timestep_consistency()
            self.interpolate()
            self.get_daylight_timesteps()
            self.generateTe()

            if out_dir is not None:
                aux_functions.save_file_csv(df_to_save = self.df_timeseries, save_dir = out_dir+'.csv', indexing = True)
                _i = f'TimeSeries file was sucessfully save at: _i += {out_dir}.csv'
                logging.info('Metocean: ' + _i)

    def _check_attributes(self):
        """
        This method validates the attributes of the `Metocean` class to ensure they
        have valid values and fall within specified ranges.

        Raises errors if any attribute is outside the specified range.
        """
        if self.latitude < -90 or self.latitude > 90:
            raise ValueError('"latitude" must be between -90 and 90 degrees')
        if self.longitude < -180 or self.longitude > 180:
            raise ValueError('"longitude" must be between -180 and 180 degrees')
        if self.h_ws_measurements <= 0:
            raise ValueError('"h_ws_measurements must be bigger than 0')

        logging.debug('Metocean: attributes within ranges and valid.')

    def _read_file(self):
        """
        Reads Metocean CSV file and converts it into a :class:`pandas.DataFrame`.

        Raises:
            FileNotFoundError: If the :attr:`file` does not exist.
            ValueError: If any CSV column is not expected.
        """
        try:
            df_timeseries = pd.read_csv(self.file, sep=',')
        except FileNotFoundError:
            logging.error('Metocean: file "%s" could not be found.' % self.file)
            raise FileNotFoundError('Metocean file could not be found.')

        # Check columns names
        df_timeseries.columns = df_timeseries.columns.str.lower()
        for col_name in df_timeseries.columns.to_list():
            if col_name not in METOCEAN_COLUMNS:
                _e = f'{col_name} is not aceptable as a column name. Please use only {METOCEAN_COLUMNS}'
                logging.error(_e)
                raise ValueError(_e)

        # Convert datetime column to datetime type
        df_timeseries = aux_functions.convert_stringtime(df_timeseries)

        # Arrange columns
        cols_final = deepcopy(METOCEAN_COLUMNS)
        for var in METOCEAN_COLUMNS:
            if var not in df_timeseries.columns.to_list():
                cols_final.remove(var)
        df_timeseries = df_timeseries[cols_final]

        df_timeseries.set_index('datetime', inplace=True)

        self.df_timeseries = df_timeseries
        logging.info('Metocean: timeseries read from file: "%s".' % self.file)

    def _check_timestep_consistency(self, stat_inputs):
        """
        Validates if :attr:`df_timeseries` timesteps always have the same time interval.

        Raises:
            ValueError: timesteps do not have always the same time interval.
            ValueError: time insterval is lower than 1 hour.
        """
        df_timeseries = deepcopy(self.df_timeseries)
        df_timeseries.reset_index(inplace=True)
        df_metocean_diff = df_timeseries["datetime"].diff()
        if df_metocean_diff.mean() != df_metocean_diff.iloc[1]:
            logging.error('Metocean: timeseries has some inconsitency with timesteps')
            raise ValueError('There is some inconsitency in timesteps')

        if df_metocean_diff.mean() < datetime.timedelta(hours=1):
            logging.error('Metocean: timeseries timestep is lower than 1 hour')
            raise ValueError('Metocean timestep is lower than 1 hour')

        start_year = stat_inputs.start_year["value"]
        end_year = start_year + stat_inputs.lifetime["value"] - 1
        if not (df_timeseries["datetime"].dt.year.iloc[0] <= start_year and df_timeseries["datetime"].dt.year.iloc[-1] >= end_year):
            e_ = f'start project: {start_year}, end project: {end_year}\n'
            e_ += f'start timeseries: {df_timeseries["datetime"].dt.year.iloc[0]}, end timeseries: {df_timeseries["datetime"].dt.year.iloc[-1]}'
            logging.error(f'Metocean: the lifetime of the project is not included in timeseries timestep\n{e_}')
            raise ValueError(f'Metocean the lifetime of the project is not included in timeseries timestep\n{e_}')

    def interpolate(self, out_dir: str=None):
        """Interpolates :attr:`df_timeseries` data and returns a
        :attr:`df_timeseries` with a timestep of 1 hour.

        Args:
            out_dir (:obj:`str`): Path to save the timeseries file.
        Example:
            >>> metocean.df_timeseries
                                  hs    tp    ws    cs
            datetime
            2018-02-17 12:00:00  2.5  16.0   7.0  1.00
            2018-02-17 18:00:00  1.9  16.6   4.0  0.88
            >>> metocean.interpolate()
            >>> metocean.df_timeseries
                                   hs    tp    ws    cs
            datetime
            2018-02-17 12:00:00  2.50  16.0   7.0  1.00
            2018-02-17 13:00:00  2.40  16.1   6.5  0.98
            2018-02-17 14:00:00  2.30  16.2   6.0  0.96
            2018-02-17 15:00:00  2.20  16.3   5.5  0.94
            2018-02-17 16:00:00  2.10  16.4   5.0  0.92
            2018-02-17 17:00:00  2.00  16.5   4.5  0.90
            2018-02-17 18:00:00  1.90  16.6   4.0  0.88
        """
        df_timeseries = deepcopy(self.df_timeseries)
        df_timeseries.reset_index(inplace=True)
        df_timeseries_diff = df_timeseries["datetime"].diff()

        timestep_total = df_timeseries.shape[0]

        if df_timeseries_diff.sum().total_seconds() / 3600 == (timestep_total - 1):
            logging.warning('Metocean: timeseries timestep interval is always 1. No need for interpolation.')
            return

        df_timeseries_hour = deepcopy(self.df_timeseries)
        df_timeseries_hour = df_timeseries_hour.resample('1H').interpolate(
                method='linear',
                limit_direction='forward',
                axis=0
        )
        df_timeseries_hour = df_timeseries_hour.round(4)

        self.df_timeseries = df_timeseries_hour
        self.df_timeseries.index.name = 'datetime'
        logging.info('Metocean: timeseries interpolated.')

        # Save new timeseries as a CSV
        if out_dir is not None:
            aux_functions.save_file_csv(df_to_save = self.df_timeseries, save_dir = out_dir+'_hourly.csv', indexing = True)
            logging.info(f'Metocean: timeseries saved as {out_dir}_hourly.csv')

    def get_daylight_timesteps(self, out_dir: str=None):
        """
        Adds a new column called `light` to :attr:`df_timeseries` representing
        if there is sun light for each timeseries timestep.

        Args:
            out_dir (:obj:`str`): Path to save the timeseries file.
        Note:
            It uses :meth:`astral.sun.sun` and :class:`astral.LocationInfo`.

        Example:
            >>> metocean.df_timeseries
                                  hs    tp    ws    cs
            datetime
            2018-02-17 12:00:00  2.5  16.0   7.0  1.00
            2018-02-17 18:00:00  1.9  16.6   4.0  0.88
            2018-02-18 00:00:00  1.6  13.0   4.6  0.82
            2018-02-18 06:00:00  1.6  13.0   4.6  0.82
            2018-02-18 12:00:00  0.4  10.0  10.0  0.64
            >>> metocean.get_daylight_timesteps()
                                  hs    tp    ws    cs  light
            datetime
            2018-02-17 12:00:00  2.5  16.0   7.0  1.00      1
            2018-02-17 18:00:00  1.9  16.6   4.0  0.88      1
            2018-02-18 00:00:00  1.6  13.0   4.6  0.82      0
            2018-02-18 06:00:00  1.6  13.0   4.6  0.82      0
            2018-02-18 12:00:00  0.4  10.0  10.0  0.64      1
        """
        timeseries_file_name = '_daylight.csv'
        # Check if there is already a timeseries with daylight information
        if out_dir:
            if os.path.exists(out_dir+timeseries_file_name):
                # Recycle this file
                df_timeseries = pd.read_csv(
                        filepath_or_buffer=(out_dir+timeseries_file_name),
                        sep=','
                )
                df_timeseries['datetime'] = pd.to_datetime(df_timeseries['datetime'], format='%Y-%m-%d %H:%M:%S')
                df_timeseries.set_index(keys='datetime', drop=True)
                self.df_timeseries = deepcopy(df_timeseries)
                logging.info(f'Metocean: timeseries recycled from "{out_dir+timeseries_file_name}".')
                return

        # If not, generate daylight information
        df_timeseries = deepcopy(self.df_timeseries)
        df_timeseries['light'] = 0

        loc = LocationInfo(
                latitude=self.latitude,
                longitude=self.longitude
        )
        for idx, _ in tqdm(
                df_timeseries.iterrows(),
                total=df_timeseries.shape[0],
                desc='Metocean: Checking daylight per timestep'
        ):
            s = sun(loc.observer, date=idx, tzinfo=loc.timezone)
            sunrise_datetime = s["sunrise"]
            sunset_datetime = s["sunset"]
            sunrise_time = datetime.datetime(
                    sunrise_datetime.year,
                    sunrise_datetime.month,
                    sunrise_datetime.day,
                    sunrise_datetime.hour,
                    sunrise_datetime.minute
            )
            sunset_time = datetime.datetime(
                    sunset_datetime.year,
                    sunset_datetime.month,
                    sunset_datetime.day,
                    sunset_datetime.hour,
                    sunset_datetime.minute
            )
            if sunrise_time <= idx <= sunset_time:
                df_timeseries.loc[idx, 'light'] = 1

        self.df_timeseries = df_timeseries
        logging.info('Metocean: timeseries has sunlight per timestep.')

        # Save new timeseries as a CSV
        if out_dir is not None:
            aux_functions.save_file_csv(df_to_save = self.df_timeseries, save_dir = out_dir+timeseries_file_name, indexing = True)
            logging.info(f'Metocean: timeseries saved as "{out_dir+timeseries_file_name}".')

    def generateTe(self, overwrite: bool=False) -> pd.DataFrame:
        """Generate a new column with wave energy period based on wave peak period.\
        From: http://www.coastalwiki.org/wiki/Statistical_description_of_wave_parameters\
        For pearson moskowitz Te ~ 0.85 Tp\
        For Johnswap Te ~0.9 Tp

        Example:
            >>> metocean.df_timeseries
                                  hs    tp    ws    cs
            datetime
            2018-02-17 12:00:00  2.5  16.0   7.0  1.00
            2018-02-17 18:00:00  1.9  16.6   4.0  0.88
            2018-02-18 00:00:00  1.6  13.0   4.6  0.82
            2018-02-18 06:00:00  1.6  13.0   4.6  0.82
            2018-02-18 12:00:00  0.4  10.0  10.0  0.64
            >>> metocean.generateTe()
                                  hs    tp    ws    cs     te
            datetime
            2018-02-17 12:00:00  2.5  16.0   7.0  1.00  13.60
            2018-02-17 18:00:00  1.9  16.6   4.0  0.88  14.11
            2018-02-18 00:00:00  1.6  13.0   4.6  0.82  11.05
            2018-02-18 06:00:00  1.6  13.0   4.6  0.82  11.05
            2018-02-18 12:00:00  0.4  10.0  10.0  0.64   8.50

        Args:
            overwrite (:obj:`bool`, *optional*): Overwrite :obj:`te` values if any. Defaults to ``False``.

        Raises:
            TypeError: if :obj:`tp` is not part of :attr:`self.df_timeseries` columns.

        Returns:
            :class:`pandas.DataFrame`: table with timestamps as index.
            Wave peak period (Tp) and wave energy peridod (Te) must be
            part of table columns.
                :obj:`index`: time stamps of type :class:`pandas.DatetimeIndex`.

                :obj:`columns`:
                    (...)

                    :obj:`tp`: wave peak period.

                    :obj:`te`: wave energy period.

                    (...)
        """
        if not('tp' in self.df_timeseries.columns):
            logging.error('Metocean: timeseries table does not have a Tp column.')
            raise TypeError('Timeseries table does not have a Tp column')
        if 'te' in self.df_timeseries.columns and overwrite is True:
            self.df_timeseries['te'] = np.nan
            logging.warning('Timeseries table already has a Te column. This column was overwritten.')
        elif 'te' in self.df_timeseries.columns and overwrite is False:
            logging.warning('Metocean: timeseries table already has a Te column. Data was not replaced')
            return

        self.df_timeseries.loc[:, 'te'] = 0.85 * self.df_timeseries.loc[:, 'tp']
        self.df_timeseries['te'] = self.df_timeseries['te'].round(4)
        logging.info('Metocean: Te column included.')

    def add_wind_speed_h_hub_column(
            self,
            h_hub=150,
            z0=0.0002,
            output_dir=None,
            output_filename=None
    ):
        """
        This function computes the wind speed at hub's height based on the wind
        speed measurements for every timestep avaialble in the df_timeseries
        metocean attribute and adds an adittional collumns with that information.

        Args:
            h_hub (:obj:`int` or `float`): Wind turbine hub height. Defaults to ``150.0``.
            z_wind_speed (:obj:`float`): Wind speed measurements height. Defaults to ``10.0``.
            z0 (:obj:`float`): Surface for roughness. Defaults to ``0.0002``.
            output_dir (:obj:`str`, *optional*): Folder path location to save the output .csv file. Defaults to ``None``.
            output_filename (:obj:`str`, *optional*): Name of the output .csv file. Defaults to ``None``.

        Raises:
            ValueError: If any CSV column is not expected.
        """
        df_timeseries = deepcopy(self.df_timeseries)

        if 'ws_hub' in df_timeseries.columns.str.lower():
            _w = 'Wind speed at hub height already part of the '
            _w += 'timeseries. Not overwriting.'
            logging.warning('Metocean: ' + _w)
            return

        z_wind_speed = self.h_ws_measurements

        # Check columns names
        df_timeseries.columns = df_timeseries.columns.str.lower()

        for col_name in df_timeseries.columns.to_list():
            if col_name not in METOCEAN_COLUMNS:
                _e = f'{col_name} is not aceptable as a column name. Please use only {METOCEAN_COLUMNS}'
                logging.error('Metocean: correct_wind_speed: ' + _e)
                raise ValueError(_e)

        # Wind speed correction to the hub's height
        ws_10_data = deepcopy(df_timeseries.loc[:,['ws']])
        ws_corr_factor = np.log(h_hub/z0) / np.log(z_wind_speed/z0)
        ws_corr_data =  ws_10_data * ws_corr_factor
        ws_corr_data = ws_corr_data.round(decimals=2)

        # Add corrected wind speed into DataFrame
        df_timeseries["ws_hub"] = ws_corr_data
        self.df_timeseries = df_timeseries
        logging.info('Metocean: ws corrected to hub height added to df_timeseries')

        # Output into a different .csv if arguments were provided
        if all(arg is not None for arg in [output_dir, output_filename]):
            aux_functions.save_file_csv(df_to_save = self.df_timeseries, save_dir = output_dir+output_filename+".csv", indexing = True)
            _i = f'.csv file was sucessfully save at:{output_dir+output_filename+".csv"}'
            logging.info('Metocean: correct_wind_speed: ' + _i)
        else:
            _i = 'No arguments were provided to save the new DataFrame into a .csv file'
            logging.info('Metocean: correct_wind_speed: ' + _i)

    @classmethod
    def from_yaml(cls, dir: str, loc:str):
        """
        Recycle previous ~Metocean inputs from a YAML file.
        It does not generate a metocena timeseries, df_timeseries e det to `None`.

        Args:
            dir (:obj:`str`): Directory where there is the file to reuse.
        """
        input_file_path = os.path.join(dir, 'inputs_tseries.yaml')
        with open(input_file_path, "r") as f:
            yaml = YAML(typ="safe")
            metocean_yaml = yaml.load(f)

        metocean_args = {
                "file_": metocean_yaml[loc]["value"],
                "latitude": metocean_yaml["site latitude"]["value"],
                "longitude": metocean_yaml["site longitude"]["value"],
                "h_ws_measurements": metocean_yaml["metocean ws height"]["value"],
                "run_funcs": False
        }

        metocean_args = {k: v for k, v in metocean_args.items() if v is not None}

        metocean = cls(**metocean_args)

        logging.info('Metocean: metocean recycled from "%s".' % input_file_path)

        return metocean


    @staticmethod
    def _load_timeseries_csv(csv_path):
        """Load, parse and index the timeseries CSV if present."""
        if not os.path.exists(csv_path):
            return None
        df = pd.read_csv(filepath_or_buffer=csv_path, sep=",")
        # convert 'datetime' column and set as index
        df = aux_functions.convert_stringtime(df)
        df.set_index("datetime", inplace=True)
        return df


    @classmethod
    def from_run_dir(
        cls,
        run_dir,
        stat_inputs,
        tseries_inputs=None,
        power_farm=None,
        wtg=None,
        z0=None,
        tow_metocean=False,
        port_metocean = False,
        site_metocean = None
    ) -> tuple[object | dict, dict]:
        """
        Create or load a Metocean object from a run directory.
        - If the file exists:
            - load the existing Metocean configuration from YAML and the associated time series data from CSV

        - If the file does not exist:
            - create a new Metocean object using the provided input data

        The method computes and appends the wind speed at hub height, either using the provided turbine/farm
        parameters or default assumptions.

        Args:
            run_dir (str | Path): Path to the simulation or run directory.
            stat_inputs (object): Statistical input configuration used to initialize the Metocean data.
            tseries_inputs (object, optional): Object of class ``tseries_inputs``.
            power_farm (object, optional): Wind farm configuration object.
            wtg (object, optional): Wind turbine generator configuration object.
            z0 (float, optional): Surface roughness length used for wind speed extrapolation.
            tow_metocean (bool, default=False): If True, use tow/metocean without processing wind speed.
            port_metocean (bool, default=False): If True, use metocean port without processing wind speed.
            site_metocean (object, optional): Object of the class ``Metocean`` that represent the Site lcoation.
                Considered only for Port metocean case, used if port metocean not defined. Default as ``None``

        Returns:
            object | dict | None:
                A Metocean instance or serialized Metocean representation, depending on the implementation context.
            empty dict | dict: Empty dictionary or dictionary of distances of metocean tow file to site
        """

        def check_create_metocean(
                run_dir,
                file_name = "timeseries.csv",
                file = tseries_inputs.file_metocean["value"],
                loc = "metocean file location"
            ):
            if check_file_exists and check_file_exists(run_dir, file_name):
                # Reuse previously defined Metocean
                met = cls.from_yaml(dir=run_dir, loc = loc)
                df_ts = cls._load_timeseries_csv(os.path.join(run_dir, file_name))
                if df_ts is not None:
                    met.df_timeseries = deepcopy(df_ts)
            else:
                if tseries_inputs is None:
                    raise ValueError("tseries_inputs required to build Metocean when no timeseries.csv exists.")
                met = cls(
                    file_=file,
                    latitude=tseries_inputs.site_lat["value"],
                    longitude=tseries_inputs.site_lon["value"],
                    h_ws_measurements=tseries_inputs.metocean_ws_height["value"],
                    stat_inputs=stat_inputs,
                    out_dir=os.path.join(run_dir, file_name.split('.')[0])
                )
            return met
        
        met_dist = {}
        # reuse path or create new
        if not tow_metocean:
            # SITE METOCEAN
            if not port_metocean:
                met = check_create_metocean(run_dir)
                # add wind speed at hub height column
                if power_farm is not None and getattr(power_farm, "wtg_number_devices", None) is not None:
                    if wtg is None or z0 is None:
                        # fallback if missing params
                        met.add_wind_speed_h_hub_column()
                    else:
                        met.add_wind_speed_h_hub_column(h_hub=wtg.hub_height, z0=z0)
                else:
                    met.add_wind_speed_h_hub_column()
            # PORT METOCEAN
            else:
                if tseries_inputs.file_metocean_port["value"]:
                    met = check_create_metocean(
                        run_dir = run_dir,
                        file_name="timeseries_port.csv",
                        file = tseries_inputs.file_metocean_port["value"],
                        loc = "metocean file port"
                    )
                    if power_farm is not None and getattr(power_farm, "wtg_number_devices", None) is not None:
                        if wtg is None or z0 is None:
                            # fallback if missing params
                            met.add_wind_speed_h_hub_column()
                        else:
                            met.add_wind_speed_h_hub_column(h_hub=wtg.hub_height, z0=z0)
                    else:
                        met.add_wind_speed_h_hub_column()
                # Consider site metocean forcing ocean variables as considering in protected areas
                else:
                    met = deepcopy(site_metocean)

                met.df_timeseries['hs'] = 0
                met.df_timeseries['te'] = 10
                met.df_timeseries['cs'] = 0
        # TOW METOCEAN
        else:
            met = {}
            
            for i in range(1, tseries_inputs.file_metocean_tow_number["value"]+1):
                met[int(i)] = check_create_metocean(
                    run_dir = run_dir,
                    file_name=f"timeseries_{i}.csv",
                    file = tseries_inputs.file_metocean_tow_location[i]["value"],
                    loc = f"metocean file tow location {i}"
                )
                met_dist[int(i)] = tseries_inputs.file_metocean_tow_distance[i]["value"]
        return met, met_dist

    def attach_power_columns(metocean: object, power_farm: object, out_dir: str):
        """Attach wind/wave power columns to metocean.df_timeseries in-place and return df_power slice."""

        timeseries_with_power = add_power_columns(
            df_metocean=metocean.df_timeseries,
            power_losses=power_farm.power_losses,
            pcurve_wind=power_farm.wtg_pcurve,
            pmatrix_wave=power_farm.wec_pmatrix,
            ndevices_wind=power_farm.wtg_number_devices,
            ndevices_wave=power_farm.wec_number_devices,
            out_dir=out_dir,
        )
        metocean.df_timeseries = deepcopy(timeseries_with_power)

        return metocean


if __name__ == '__main__':
    import os
    metocean = Metocean(
            file_=os.path.join(os.getcwd(), 'tests', 'test_files', 'metocean', 'metocean_dummy.csv'),
            latitude=41.615065,
            longitude=-9.348514
    )
    metocean.add_wind_speed_h_hub_column()

    temp_dir = os.path.join(os.getcwd(), 'tmp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    metocean.df_timeseries.to_csv(
            path_or_buf=os.path.join(os.getcwd(), 'tmp', 'metocean_dummy_h_height.csv'),
            sep=','
    )
