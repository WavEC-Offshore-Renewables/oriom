# Import packages
import pandas as pd
import os
import logging
from ruamel.yaml import YAML


class WindTurbineGenerator():
    """WindTurbineGenerator class.

    Note:
        If the "number_devices" is defined, the technology has to be defined and most attributes become mandatory.
        To not include the technology --> "number_devices" = 0 or None

    Attributes:
        number_devices (:obj:`int`): Number of WTG devices. Defaults to ``None``.
        rated_power (:obj:`float`): Rated power of each WTG, in MW. Defaults to ``None``.
        cut_in (:obj:`float`): WTG cut-in speed, in m/s. Defaults to ``None``.
        cut_off (:obj:`float`): WTG cut-off speed, in m/s. Defaults to ``None``.
        hub_height (:obj:`float`): WTG hub height, in m. Defaults to ``None``.
        pcurve_file (:obj:`str`): WTG power curve file path. Defaults to ``None``.
        moorings (:obj:`int`): Number of mooring systems per WTG. Defaults to ``0``.
        number_strings (:obj:`int`): Number of strings of WTG devices. Defaults to ``1``.
        n_string_to_connector (:obj:`int`): Number of strings for hub. Defaults to ``1``
        number_substations (:obj:`int`): Number of substations of WTG farm. Defaults to ``1``.
        number_exportcables (:obj:`int`): Number of export cables of WTG farm. Defaults to ``1``.
        wtg_layout (:obj:`int`): Type layout. Defaults to ``1``.
        n_device_at_port (:obj:`int`): Number of device that can be mantained simultaneously at port.
            Defaults to ``1``
        n_device_stored_at_port (:obj:`int`): Number of device that can be stored when not in
            maintenance. Defaults to ``0``
        wtg_layout (:obj:`int`): Type layout. Defaults to ``1``.
        tow_string_shutdown (:obj:`bool`): Define if the electrical layout can sustain a tow without disconnect the string.
                Defaults to ``None``

    Note:
        When the class is initialized, :func:`_check_attributes` is run.

    Example:
        >>> wtg = WindTurbineGenerator(
        >>>         number_devices=3,
        >>>             rated_power=8,
        >>>             cut_in=3,
        >>>             cut_off=25,
        >>>             hub_height=100,
        >>>             pcurve_file=os.path.join(
        >>>                         os.getcwd(),
        >>>                         'tests',
        >>>                         'test_files',
        >>>                         'pcurve_wind.csv'
        >>>             ),
        >>>             moorings=3,
        >>>             number_strings=1,
        >>>             wtg_layout=1

        >>> )
    """
    def __init__(
            self,
            number_devices: int=None,
            rated_power: float=None,
            cut_in: float=None,
            cut_off: float=None,
            hub_height: float=None,
            pcurve_file: str=None,
            moorings: int=None,
            number_strings: int=None,
            n_string_to_connector: int=None,
            number_substations: int=1,
            number_exportcables: int=1,
            n_device_at_port: int=None,
            n_device_stored_at_port: int=None,
            tow_string_shutdown: bool = None,
            wtg_layout: int=1,
            out_dir: str=None
    ):
        """Initializes :class:`WindTurbineGenerator` class.

        Args:
            number_devices (:obj:`int`): Number of WTG devices. Defaults to ``None``.
            rated_power (:obj:`float`): Rated power of each WTG (in MW). Defaults to ``None``.
            cut_in (:obj:`float`): WTG cut-in speed (in m/s). Defaults to ``None``.
            cut_off (:obj:`float`): WTG cut-off speed (in m/s). Defaults to ``None``.
            hub_height (:obj:`float`): WTG hub height (in m). Defaults to ``None``.
            pcurve_file (:obj:`str`): WTG power curve file path. Defaults to ``None``.
            moorings (:obj:`int`): Number of mooring systems per WTG. Defaults to ``0``.
            number_strings (:obj:`int`): Number of strings of WTG devices. Defaults to ``None``.
            n_string_to_connector (:obj:`int`): Number of strings for hub. Defaults to ``None``.
            wtg_layout (:obj:`int`): Type layout. Defaults to ``1``.
            number_substations (:obj:`int`): Number of substations of WTG farm. Defaults to ``1``.
            number_exportcables (:obj:`int`): Number of export cables of WTG farm. Defaults to ``1``.
            out_dir (:obj:`str`): Directory to save the WTG parameters. Defaults to `None`.
            n_device_at_port (:obj:`int`): Number of device that can be mantained simultaneously at port. Defaults to ``None``
            n_device_stored_at_port (:obj:`int`): Number of device that can be stored when not in maintenance. Defaults to ``None``
            tow_string_shutdown (:obj:`bool`): Define if the electrical layout can sustain a tow without disconnect the string.
                Defaults to ``None``
        """
        if number_devices != 0 and number_devices is not None:
            self.number_devices = int(number_devices)
            self.tow_string_shutdown = None
        else:
            logging.debug('WindTurbineGenerator: Wind farm not defined')
            return

        try:
            self.moorings = int(moorings)
        except TypeError:
            # moorings is None
            self.moorings = 0
            logging.debug('WindTurbineGenerator: moorings not defined')

        if number_strings != 0 and number_strings is not None:
            self.number_strings = int(number_strings)
        else:
            self.number_strings = 1

        if n_string_to_connector != 0 and n_string_to_connector is not None:
            self.n_string_to_connector = int(n_string_to_connector)
        else:
            self.n_string_to_connector = 1
            
        try:
            self.number_substations = int(number_substations)
        except ValueError:
            self.number_substations = 1

        try:
            self.number_exportcables = int(number_exportcables)
        except ValueError:
            self.number_exportcables = 1

        if n_device_at_port != 0 and n_device_at_port is not None:
            self.n_device_at_port = int(n_device_at_port)
        else:
            self.n_device_at_port = 1

        if n_device_stored_at_port != 0 and n_device_stored_at_port is not None:
            self.n_device_stored_at_port = int(n_device_stored_at_port)
        else:
            self.n_device_stored_at_port = 0

        try:
            self.wtg_layout = int(wtg_layout)
        except ValueError:
            self.wtg_layout = 1

        if rated_power is not None:
            self.rated_power = float(rated_power)
        if cut_in is not None:
            self.cut_in = float(cut_in)
        if cut_off is not None:
            self.cut_off = float(cut_off)
        if hub_height is not None:
            self.hub_height = float(hub_height)
        if pcurve_file is not None:
          self.pcurve_file = str(pcurve_file)
        if tow_string_shutdown is not None:
            self.tow_string_shutdown = tow_string_shutdown

        self._check_attributes()

        if out_dir is not None:
            self.to_yaml(out_dir)
            logging.info('WindTurbineGenerator: WTG attributes saved as "%s".' % os.path.join(out_dir, 'wtg.yaml'))


    def _check_attributes(self):
        """Validates :class:`WindTurbineGenerator` class attributes ranges."""
        if self.number_devices != 0 and any([
            self.rated_power == None,
            self.cut_in == None,
            self.cut_off == None,
            self.hub_height == None,
            self.pcurve_file == None,
            self.number_strings == None
        ]) is True:
            raise ValueError('if number_devices is defined, all arguments must be defined')
        if self.number_devices < 0:
            raise ValueError('"number_devices" must be greater than 0')
        if self.rated_power <= 0:
            raise ValueError('"rated_power" must be greater than 0')
        if self.cut_in < 0:
            raise ValueError('"cut_in" must not be negative')
        if self.cut_off <= 0:
            raise ValueError('"cut_off" must be greater than 0')
        if self.cut_in >= self.cut_off:
            raise ValueError('"cut_off" must be greater than "cut_in"')
        if self.hub_height <= 0:
            raise ValueError('"hub_height" must be greater than 0')
        if self.pcurve_file[-4:] != '.csv':
            raise ValueError('"pcurve_file" must be a .csv file')
        if self.tow_string_shutdown is not None and not isinstance(self.tow_string_shutdown, bool):
            raise ValueError('"tow_string_shutdown" must be a boolean')

        try:
            pd.read_csv(self.pcurve_file, sep=',')
        except FileNotFoundError:
            _e = 'WindTurbineGenerator: power curve file "%s"' % self.pcurve_file
            _e += ' could not be found.'
            raise FileNotFoundError(_e)

        if self.moorings < 0:
            raise ValueError('"moorings" must not be negative')

        if self.number_devices % self.number_strings !=0:
            if self.wtg_layout != 4:   #TODO insert string definition in excel file use if on this parameter != None
                raise ValueError('"number_devices" must be divisible by "number_strings"')

        logging.debug('WindTurbineGenerator: attributes within ranges and valid.')


    def get_wtg_from_yaml(
            file_path: str,
            out_dir: str=None
    ):
        """Reads a YAML file, fetches WTG information from it and returns
        a :class:`WindTurbineGenerator` item.

        Args:
            file_path (:obj:`str`): YAML file location.
            out_dir (:obj:`str`): directory to save the WTG parameters.
                Defaults to `None`.

        Raises:
            FileNotFoundError: if the keys in the YAML file are not expected.
            FileNotFoundError: if the units of any of the keys in the YAML
                file are not expected.

        Returns:
            :obj:`WindTurbineGenerator`: WTG parameters.
        """
        # Initialize expected inputs
        number_devices = None
        rated_power = None
        cut_in = None
        cut_off = None
        hub_height = None
        pcurve_file = None
        moorings = None
        number_strings = None
        n_string_to_connector = None
        number_substations = None
        number_exportcables = None
        n_device_at_port = None
        n_device_stored_at_port = None
        wtg_layout = None
        tow_string_shutdown = None

        # Read YAML file
        f_yaml = open(os.path.join(file_path), 'r')
        yaml = YAML(typ='safe')
        inputs_yaml = yaml.load(f_yaml)
        f_yaml.close()

        for key, _value in inputs_yaml.items():
            key = key.lower()
            value = _value["value"]
            try:
                units = _value["units"].lower()
            except AttributeError:
                units = _value["units"]
            if 'devices' in key:
                if number_devices is None:
                    number_devices = value
                else:
                    _e = '"number_devices" already defined. '
                    _e += 'Check if any of the other inputs have the word "devices".'
                    logging.error('WindTurbineGenerator: ' + _e)
                    raise FileNotFoundError(_e)
            if 'rated' in key and 'power' in key:
                if rated_power is None:
                    if 'mw' in units:
                        rated_power = value
                    elif 'kw' in units:
                        rated_power = round(value / 1000, 3)
                    elif 'w' in units:
                        rated_power = round(value / 1000000, 3)
                    else:
                        _e = 'Units of "rated_power" not recognized. '
                        _e += 'Please use "MW", "kW" or "W".'
                        logging.error('WindTurbineGenerator: ' + _e)
                        raise FileNotFoundError(_e)
                else:
                    _e = '"rated_power" already defined. '
                    _e += 'Check if any of the other inputs have the words '
                    _e += '"rated" and "power".'
                    logging.error('WindTurbineGenerator: ' + _e)
                    raise FileNotFoundError(_e)
            if 'cut-in' in key:
                if cut_in is None:
                    if 'm/s' in units:
                        cut_in = value
                    elif 'km/h' in units:
                        cut_in = round(value * 0.2778, 3)
                    elif 'kn' in units:
                        cut_in = round(value * 0.5144, 3)
                    else:
                        _e = 'Units of "cut_in" not recognized. '
                        _e += 'Please use "m/s", "km/h" or "knots".'
                        logging.error('WindTurbineGenerator: ' + _e)
                        raise FileNotFoundError(_e)
                else:
                    _e = '"cut_in" already defined. '
                    _e += 'Check if any of the other inputs have the words '
                    _e += '"cut-in".'
                    logging.error('WindTurbineGenerator: ' + _e)
                    raise FileNotFoundError(_e)
            if 'cut-off' in key:
                if cut_off is None:
                    if 'm/s' in units:
                        cut_off = value
                    elif 'km/h' in units:
                        cut_off = round(value * 0.2778, 3)
                    elif 'kn' in units:
                        cut_off = round(value * 0.5144, 3)
                    else:
                        _e = 'Units of "cut_off" not recognized. '
                        _e += 'Please use "m/s", "km/h" or "knots".'
                        logging.error('WindTurbineGenerator: ' + _e)
                        raise FileNotFoundError(_e)
                else:
                    _e = '"cut_off" already defined. '
                    _e += 'Check if any of the other inputs have the words '
                    _e += '"cut-off".'
                    logging.error('WindTurbineGenerator: ' + _e)
                    raise FileNotFoundError(_e)
            if 'hub' in key and 'height' in key:
                if hub_height is None:
                    if 'cm' in units:
                        hub_height = round(value / 100, 3)
                    elif 'm' in units:
                        hub_height = value
                    else:
                        _e = 'Units of "hub_height" not recognized. '
                        _e += 'Please use "m" or "cm".'
                        logging.error('WindTurbineGenerator: ' + _e)
                        raise FileNotFoundError(_e)
                else:
                    _e = '"hub_height" already defined. '
                    _e += 'Check if any of the other inputs have the words '
                    _e += '"hub" and "height".'
                    logging.error('WindTurbineGenerator: ' + _e)
                    raise FileNotFoundError(_e)
            if 'curve' in key and 'file' in key:
                if pcurve_file is None:
                    pcurve_file = value
                else:
                    _e = '"pcurve_file" already defined. '
                    _e += 'Check if any of the other inputs have the word '
                    _e += '"curve" and "file".'
                    logging.error('WindTurbineGenerator: ' + _e)
                    raise FileNotFoundError(_e)
            if 'moorings' in key:
                if moorings is None:
                    moorings = value
                else:
                    _e = '"moorings" already defined. '
                    _e += 'Check if any of the other inputs have the word "moorings".'
                    logging.error('WindTurbineGenerator: ' + _e)
                    raise FileNotFoundError(_e)
            if 'strings' in key and 'connector' not in key:
                if number_strings is None:
                    number_strings = value
                else:
                    _e = '"number_strings" alredy defined.'
                    _e += 'Check if any of the other inputs have the word "strings".'
                    logging.error('WindTurbineGenerator: ' + _e)
                    raise FileNotFoundError(_e)
            if 'string' in key and 'connector' in key:
                if n_string_to_connector is None:
                    n_string_to_connector = value
                else:
                    _e = '"n_string_to_connector" alredy defined.'
                    _e += 'Check if any of the other inputs have the word "n_string_to_connector".'
                    logging.error('WindTurbineGenerator: ' + _e)
                    raise FileNotFoundError(_e)
            if 'substations' in key:
                if number_substations is None:
                    number_substations = value
                else:
                    _e = '"number_substations" already defined.'
                    _e += 'Check if any of the other inputs have the word "substations".'
                    logging.error('WindTurbineGenerator: ' +_e)
                    raise FileNotFoundError(_e)
            if 'export' in key and 'cables' in key:
                if number_exportcables is None:
                    number_exportcables = value
                else:
                    _e = '"number_exportcables" already defined.'
                    _e += 'Check if any of the other inputs have the words "export" and "cables".'
                    logging.error('WindTurbineGenerator: ' +_e)
                    raise FileNotFoundError(_e)
            if 'device' in key and 'port' in key and not 'stored' in key:
                if n_device_at_port is None:
                    n_device_at_port = value
                else:
                    _e = '"n_device_at_port" already defined.'
                    _e += 'Check if any of the other inputs have the words "device" and "port" and not "stored".'
                    logging.error('WindTurbineGenerator: ' +_e)
                    raise FileNotFoundError(_e)
            if 'device' in key and 'port' in key and 'stored' in key:
                if n_device_stored_at_port is None:
                    n_device_stored_at_port = value
                else:
                    _e = '"n_device_stored_at_port" already defined.'
                    _e += 'Check if any of the other inputs have the words "device" and "port" and "stored".'
                    logging.error('WindTurbineGenerator: ' +_e)
                    raise FileNotFoundError(_e)
            if 'layout' in key:
                if wtg_layout is None:
                    wtg_layout = value
            if 'tow' in key and 'string':
                if tow_string_shutdown is None:
                    tow_string_shutdown = value

        wtg_inputs = WindTurbineGenerator(
                number_devices=number_devices,
                rated_power=rated_power,
                cut_in=cut_in,
                cut_off=cut_off,
                hub_height=hub_height,
                pcurve_file=pcurve_file,
                moorings=moorings,
                number_strings=number_strings,
                n_string_to_connector = n_string_to_connector,
                number_substations=number_substations,
                number_exportcables=number_exportcables,
                n_device_at_port=n_device_at_port,
                n_device_stored_at_port=n_device_stored_at_port,
                tow_string_shutdown = tow_string_shutdown,
                wtg_layout=wtg_layout,
                out_dir=out_dir
        )

        logging.info('WindTurbineGenerator: WTG inputs read from file: "%s"' % file_path)
        return wtg_inputs


    def to_yaml(
            self,
            out_dir: str
    ):
        """
        Write the Wave system parameters to a YAML file.

        Args:
            out_dir (:obj:`str`): The output directory where the YAML file will be saved.
        """
        f = open(os.path.join(out_dir, 'wtg.yaml'), 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        yaml.dump({
                "wtg devices": {"value": self.number_devices, "units": "-"},
                "wtg rated power": {"value": self.rated_power, "units": "MW"},
                "wtg cut-in": {"value": self.cut_in, "units": "m/s"},
                "wtg cut-off": {"value": self.cut_off, "units": "m/s"},
                "wtg hub height": {"value": self.hub_height, "units": "m"},
                "wtg power curve file": {"value": self.pcurve_file, "units": "-"},
                "moorings per wtg": {"value": self.moorings, "units": "-"},
                "wtg number of strings": {"value": self.number_strings, "units": "-"},
                "wtg n strings to connector": {"value": self.n_string_to_connector, "units": "-"},
                "wtg number of hub/substations": {"value": self.number_substations, "units": "-"},
                "wtg number of export cables": {"value": self.number_exportcables, "units": "-"},
                "wtg number of n device at port": {"value": self.n_device_at_port, "units": "-"},
                "wtg number of n device stored at port": {"value": self.n_device_stored_at_port, "units": "-"},
                "wtg tow string shutdown": {"value": self.tow_string_shutdown, "units": "-"},
                "wtg type of layout": {"value": self.wtg_layout, "units": "-"}
        }, f)
        f.close()


    def from_yaml(directory: str, name: str):
        """Recycle previous ~WindTurbineGenerator from a YAML file."""
        input_file_path = os.path.join(directory, str(name) + '.yaml')
        f = open(os.path.join(input_file_path), 'r')
        yaml=YAML(typ='safe')
        wtg_yaml = yaml.load(f)
        f.close()
        wtg_args = {
                "number_devices": wtg_yaml["wtg devices"]["value"],
                "rated_power": wtg_yaml["wtg rated power"]["value"],
                "cut_in": wtg_yaml["wtg cut-in"]["value"],
                "cut_off": wtg_yaml["wtg cut-off"]["value"],
                "hub_height": wtg_yaml["wtg hub height"]["value"],
                "pcurve_file": wtg_yaml["wtg power curve file"]["value"],
                "moorings": wtg_yaml["moorings per wtg"]["value"],
                "number_strings": wtg_yaml["wtg number of strings"]["value"],
                "n_string_to_connector": wtg_yaml["wtg n strings to connector"]["value"],
                "number_substations": wtg_yaml["wtg number of hub/substations"]["value"],
                "number_exportcables": wtg_yaml["wtg number of export cables"]["value"],
                "n_device_at_port": wtg_yaml["wtg number of n device at port"]["value"],
                "n_device_stored_at_port": wtg_yaml["wtg number of n device stored at port"]["value"],
                "tow_string_shutdown": wtg_yaml["wtg tow string shutdown"]["value"],
                "wtg_layout": wtg_yaml["wtg type of layout"]["value"]
        }

        for key, value in list(wtg_args.items()):
            if value is None:
                del wtg_args[key]

        wtg = WindTurbineGenerator(**wtg_args)

        logging.info('WindTurbineGenerator: WTG recycled from "%s".' % input_file_path)

        return wtg


if __name__ == '__main__':
    pass