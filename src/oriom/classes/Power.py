# Import packages
import pandas as pd
import numpy as np
import logging


class Curve():
    """Based on a CSV file, fetched data related with the WTG power curve and
    generates a :class:`Curve` class.

    Attributes:
        file (:obj:`str`): CSV file path. Wind speed in m/s and power in watts,
            kilowatts or megawatts.
        c_in (:obj:`float`): Cut in wind speed, in m/s, km/h or knots.
        c_off (:obj:`float`): Cut off wind speed, in m/s, km/h or knots.
        rated (:obj:`float`): WTG rated power.
        array (:obj:`np.ndarray`): Generated power, in megawatts,
            per wind speed unit, in m/s.

    Note:
        When the class is initialized, :func:`_check_attributes`
        and :func:`_read_file` are run.

    Example:
        >>> pcurve = Curve(
        >>>         file_=curve_file_path,
        >>>         c_in=4,
        >>>         c_off=25,
        >>>         rated=8000
        >>> )
        >>> pcurve.array
        [   0.    0.    0.    0.  100.  650. 1150. 1850. 2900. 4150. 5600. 7100.
        7800. 8000. 8000. 8000. 8000. 8000. 8000. 8000. 8000. 8000. 8000. 8000.
        8000. 8000.    0.    0.    0.    0.    0.]
    """

    def __init__(
            self,
            file_: str,
            c_in: float,
            c_off: float,
            rated: float
    ):
        """Initializes :class:`Curve` class.

        Args:
            file_ (:obj:`str`): CSV file path. Wind speed in m/s and power in
                watts, kilowatts or megawatts.
            c_in (:obj:`float`): Cut in wind speed, in m/s, km/h or knots.
            c_off (:obj:`float`): Cut off wind speed, in m/s, km/h or knots.
            rated (:obj:`float`): WTG rated power.
        """
        self.file = str(file_)
        self.c_in = float(c_in)
        self.c_off = float(c_off)
        self.rated = float(rated)

        self.array = None

        self._check_attributes()
        self._read_file()

    def _check_attributes(self):
        """
        This method validates the attributes of the `Power` class to ensure they
        have valid values and fall within specified ranges.

        Raises errors if any attribute is outside the specified range.
        """
        if self.c_in < 0:
            raise ValueError('"cut-in" must not be negative.')
        if self.c_off < 0:
            raise ValueError('"cut-off" must not be negative.')
        if self.rated < 0:
            raise ValueError('"Rated power" must not be negative.')
        logging.debug('PowerCurve: attributes within ranges and valid.')

    def _read_file(self):
        """Reads Power Curve CSV file and converts it into a :class:`np.ndarray`
        with a speed interval of 1 m/s.

        Raises:
            FileNotFoundError: if the :attr:`file` does not exist.
            IndexError: if power curve file does not have 2 columns.
            NameError: if the first column of the curve file is not the wind speed.
            NameError: if the second column of the curve file is not the power.
            NameError: if wind speed unit is not recognized.
            NameError: if power unit is not recognized.
        """
        try:
            df_pcurve = pd.read_csv(self.file, sep=',')
        except FileNotFoundError:
            logging.error('PowerCurve: file "%s" could not be found.' % self.file)
            raise FileNotFoundError('Power curve file could not be found.')

        df_pcurve_cols = df_pcurve.columns.str.lower().to_list()
        if len(df_pcurve_cols) < 2 or len(df_pcurve_cols) > 2:
            logging.error('PowerCurve: file "%s" must have 2 columns. Column 1: Speed; Column 2: Power' % self.file)
            raise IndexError('Power Curve files must have 2 columns. Column 1: Speed; Column 2: Power')
        col_speed = df_pcurve_cols[0]
        col_power = df_pcurve_cols[1]

        # Default columns
        cols_default = ['speed', 'power']
        speed_units = ['_m/s', '_km/h', '_kn', '_knots']
        power_unit = ['_w', '_kw', '_mw']

        # Columns name
        if cols_default[0] not in col_speed:
            logging.error('PowerCurve: First column should be the speed column.')
            raise NameError('First column should be the speed column.')
        if cols_default[1] not in col_power:
            logging.error('PowerCurve: Second column should be the power column.')
            raise NameError('Second column should be the power column.')

        # Columns units
        speed_found = False
        for unit in speed_units:
            if unit in col_speed:
                if unit == '_m/s':
                    speed_found = True
                    break
                elif unit == '_km/h':
                    df_pcurve.iloc[:, 0] = (df_pcurve.iloc[:, 0] * 1000) / 3600
                    speed_found = True
                    break
                elif unit == '_kn':
                    df_pcurve.iloc[:, 0] = df_pcurve.iloc[:, 0] * 0.514444
                    speed_found = True
                    break
                elif unit == '_knots':
                    df_pcurve.iloc[:, 0] = df_pcurve.iloc[:, 0] * 0.514444
                    speed_found = True
                    break
        if speed_found is False:
            _e = 'Speed unit not recognized. Units recognized: "m/s", "km/h", "kn" and "knots". '
            _e += 'Units must be preceeded by an underscore ("_")'
            logging.error('PowerCurve: ' + _e)
            raise NameError(_e)

        power_found = False
        for unit in power_unit:
            if unit in col_power:
                if unit == '_w':
                    df_pcurve.iloc[:, 1] = df_pcurve.iloc[:, 1] / 1000
                elif unit == '_kw':
                    pass
                elif unit == '_mw':
                    df_pcurve.iloc[:, 1] = df_pcurve.iloc[:, 1] * 1000
                power_found = True
                break
        if power_found is False:
            _e = 'Power unit not recognized. Units recognized: "W", "kW", "MW". '
            _e += 'Units must be preceeded by an underscore ("_")'
            logging.error('PowerCurve: ' + _e)
            raise NameError(_e)

        max_speed = int(df_pcurve.iloc[:, 0].max())
        n_samples = df_pcurve.iloc[:, 0].max() + 1
        if df_pcurve.iloc[:, 0].max() != int(df_pcurve.iloc[:, 0].max()):
            max_speed += 1
            n_samples += 1
        n_samples = int(n_samples)
        newindex = np.linspace(0, max_speed, n_samples)
        df_pcurve.set_index(col_speed, inplace=True)
        df_pcurve = interpolate(df_pcurve, newindex)
        self.array = np.array(df_pcurve.iloc[:, 0].tolist())
        logging.info('PowerCurve: curve defined based on file: "%s".' % self.file)


class Matrix():
    """
    PowerMatrix class for wave energy.
    It reads the power matrix in the CSV file and convert it to :obj:`pd.DataFrame`

    Args:
        file_ (:obj:`str`): The path to the CSV file containing the power matrix data.
        rated (:obj:`float`): The rated power value in kW.
    """
    def __init__(

            self,
            file_: str,
            rated: float
    ):
        """Initializes :class:`Matrix` class.

        Args:
            file_ (:obj:`str`): The path to the CSV file containing the power matrix data.
            rated (:obj:`float`): The rated power value.
        Raises:
            ValueError: If the rated power is negative.
            FileNotFoundError: If the specified file does not exist.

        NOTE: the current file is in kW

        """
        self.file = str(file_)
        self.rated = float(rated)

        self.matrix = None

        self._check_attributes()
        self._read_file()

    def _check_attributes(self):
        """Validates Matrix inputs ranges."""
        if self.rated < 0:
            raise ValueError('"Rated power" must not be negative.')
        logging.debug('PowerMatrix: attributes within ranges and valid.')

    def _read_file(self):
        """Reads Power Matrix CSV file and converts it into a :class:`~pd.DataFrame`.

        Raises:
            FileNotFoundError: If the :attr:`file` does not exist.
        """

        try:
            df_pmatrix = pd.read_csv(self.file, sep=',', index_col=0)
        except FileNotFoundError:
            logging.error('PowerMatrix: file "%s" could not be found.' % self.file)
            raise FileNotFoundError('Power matrix file could not be found.')

        # Corrects list of strings to list of tuples
        df_pmatrix.index = list(map(eval, df_pmatrix.index))
        df_pmatrix.columns = list(map(eval, df_pmatrix.columns))

        self.matrix = df_pmatrix

        # TODO: Code to interpolate the power matrix
        # max_hs = max([max(interval) for interval in df_pmatrix.index])
        # n_hs_samples = max_hs / 0.5
        # if max_hs != int(df_pmatrix.index[-1][1]):
        #     n_hs_samples += 1
        #     max_hs = int(df_pmatrix.index[-1][1]) + 0.5
        # n_hs_samples = int(n_hs_samples)

        # max_tp = max([max(interval) for interval in df_pmatrix.columns])
        # n_tp_samples = max_tp / 1
        # if max_tp != int(df_pmatrix.columns[-1][1]):
        #     n_tp_samples += 1
        # n_tp_samples = int(n_tp_samples)

        # newindex = [(hs, hs + 0.5) for hs in np.linspace(0, (max_hs - 0.5), n_hs_samples)]
        # newcols = [(tp, tp + 1) for tp in np.linspace(0, (max_tp - 1), n_tp_samples)]

        # index_low = newindex[0][0] + ((newindex[0][1] - newindex[0][0]) / 2)
        # index_high = newindex[-1][0] + ((newindex[-1][1] - newindex[-1][0]) / 2)
        # col_low = newcols[0][0] + ((newcols[0][1] - newcols[0][0]) / 2)
        # col_high = newcols[-1][0] + ((newcols[-1][1] - newcols[-1][0]) / 2)

        # grid_x, grid_y = np.mgrid[
        #         col_low:col_high:complex(0, n_tp_samples),
        #         index_low:index_high:complex(0, n_hs_samples)
        # ]
        logging.info('PowerMatrix: matrix defined based on file: "%s".' % self.file)


class PVPower():
    """
    Power class for solar energy.
    It reads the power matrix in the CSV file and convert it to :class:`np.ndarray`.

    Args:
        file_ (:obj:`str`): The path to the CSV file containing the power matrix data.
    """
    def __init__(
            self,
            file_: str
    ):
        """Initializes :class:`PVPower` class.

        Args:
            file_ (:obj:`str`): CSV file path. PV panel hourly power output
                per month in watts.
        """
        self.file = str(file_)

        self.power_month = {
                m: None
                for m in range(1, 13)
        }

        self._read_file()
        self._check_attributes()

    def _check_attributes(self):
        """Validates Curve inputs ranges."""
        for m in range(1, 13):
            if any([power < 0 for power in self.power_month[m]]):
                raise ValueError('Some power values are negative.')

        logging.debug('PowerCurve: attributes within ranges and valid.')

    def _read_file(self):
        """Reads PV Power Output CSV file, loops through each month andconverts
            the hourly production to :class:`np.ndarray`.

        Raises:
            FileNotFoundError: if the :attr:`file` does not exist.
        """
        try:
            df_power = pd.read_csv(self.file, sep=',')
        except FileNotFoundError:
            _e = 'PVPower: file "%s" could not be found.' % self.file
            logging.error(_e)
            raise FileNotFoundError(_e)
        try:
            df_power.set_index('hour', inplace=True)
        except KeyError:
            _e = '"hour" column not present in %s.' % self.file
            logging.error('PVPower: ' + _e)
            raise NameError(_e)

        df_power.columns = df_power.columns.str.lower().to_list()

        for m in range(1, 13):
            self.power_month[m] = np.array(df_power.iloc[:, m-1])

        logging.info('PVPower: pv panels power defined based on file: "%s".' % self.file)


def interpolate(df: pd.DataFrame, new_index: list):
    """Return a new DataFrame with all columns values interpolated to the new_index values.

    Args:
        df (:obj:`pd.DataFrame`)
        new_index (:obj:`list`)
    """
    df_out = pd.DataFrame(index=new_index)
    df_out.index.name = df.index.name

    for colname, col in df.items():
        df_out[colname] = np.interp(new_index, df.index, col)

    logging.info('PowerCurve: curve interpolated.')
    return df_out


if __name__ == '__main__':
    import os
    pcurve = Curve(
            file_=os.path.join(os.getcwd(), 'tests', 'test_files', 'pcurve_wind.csv'),
            c_in=4,
            c_off=25,
            rated=8000
    )

    pcurve = Matrix(
            file_=os.path.join(os.getcwd(), 'tests', 'test_files', 'pmatrix_wave.csv'),
            rated=8000
    )

    pvpower = PVPower(
            file_=os.path.join(os.getcwd(), 'tests', 'test_files', 'pv_prod_month_hour.csv')
    )
