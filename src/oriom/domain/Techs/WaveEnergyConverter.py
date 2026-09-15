# Import packages
import pandas as pd
import os
import logging
from ruamel.yaml import YAML


class WaveEnergyConverter():
    """WaveEnergyConverter class.

    Note:
        If the "number_devices" is defined, the technology has to be defined and most attributes become mandatory.
        To not include the technology --> "number_devices" = 0 or None

    Attributes:
        number_devices (int): Number of WEC devices. Defaults to ``None``.
        rated_power (float): Rated power of each WEC, in kW. Defaults to ``None``.
        pmatrix_file (str): WEC power matrix file path. Defaults to ``None``.
        number_strings (int): Number of strings of WEC devices. Defaults to ``None``.
        number_substations (int): Number of substations of WEC farm. Defaults to ``1``.
        number_exportcables (int): Number of export cables of WEC farm. Defaults to ``1``.
        n_string_to_connector (int): Number of strings for hub. Defaults to ``1``
        n_device_at_port (int): Number of device that can be mantained simultaneously at port. Defaults to ``1``
        n_device_stored_at_port (int): Number of device that can be stored when not in maintenance. Defaults to ``0``
        wec_layout (int): Type layout. Defaults to ``1``.
        tow_string_shutdown (:obj:`bool`): Define if the electrical layout can sustain a tow without disconnect the string.
            Defaults to ``None``
        spacing (float): Spacing between devices in meters. Defaults to ``0.150`` km.
    Note:
        When the class is initialized, :func:`_check_attributes` is run.

    Example:
        >>> wec = WaveEnergyConverter(
        >>>         number_devices=10,
        >>>         rated_power=500,
        >>>         pmatrix_file=os.path.join(
        >>>                     os.getcwd(),
        >>>                     'tests',
        >>>                     'test_files',
        >>>                     'pmatrix_wave.csv'
        >>>         ),
        >>>         number_strings=1,
        >>>         wec_layout=1
        >>> )
    """
    def __init__(
            self,
            number_devices: int=None,
            rated_power: float=None,
            pmatrix_file: str=None,
            number_strings: int=None,
            n_string_to_connector: int=None,
            number_substations: int=1,
            number_exportcables: int=1,
            n_device_at_port: int=None,
            n_device_stored_at_port: int=None,
            tow_string_shutdown: bool = None,
            wec_layout: int=1,
            spacing: float=0.150,
            out_dir: str=None
    ):
        """Initializes :class:`WaveEnergyConverter` class.

        Args:
            number_devices (int): Number of WEC devices. Defaults to ``None``.
            rated_power (float): Rated power of each WEC (in kW). Defaults to ``None``.
            pmatrix_file (str): WEC power matrix file path. Defaults to ``None``.
            out_dir (str): Directory to save the WEC parameters. Defaults to `None`.
            number_strings (int): Number of strings of WEC devices. Defaults to ``None``.
            n_string_to_connector (int): Number of strings for hub. Defaults to ``None``.
            wec_layout (int): Type layout. Defaults to ``1``.
            number_substations (int): Number of substations of WEC farm. Defaults to ``1``.
            number_exportcables (int): Number of export cables of WEC farm. Defaults to ``1``.
            n_device_at_port (int): Number of device that can be mantained simultaneously at port. Defaults to ``None``
            n_device_stored_at_port (int): Number of device that can be stored when not in maintenance. Defaults to ``None``
            tow_string_shutdown (:obj:`bool`): Define if the electrical layout can sustain a tow without disconnect the string.
                Defaults to ``None``
            spacing (float): Spacing between devices in meters. Defaults to ``0.150`` km.
            out_dir (str): Directory to save the WEC parameters. Defaults to `None`.
        """
        if number_devices != 0 and number_devices is not None:
            self.number_devices = int(number_devices)
            self.tow_string_shutdown = None
        else:
            logging.debug('WaveEnergyConverter: Wave farm is not defined')
            return

        if rated_power is not None:
            self.rated_power = float(rated_power)
        else:
            self.rated_power = rated_power
        if pmatrix_file is not None:
            self.pmatrix_file = str(pmatrix_file)
        else:
            self.pmatrix_file = pmatrix_file

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
            try:
                self.n_device_at_port = int(n_device_at_port)
            except ValueError:
                self.n_device_at_port = 1
        else:
            self.n_device_at_port = 1

        if n_device_stored_at_port != 0 and n_device_stored_at_port is not None:
            try:
                self.n_device_stored_at_port = int(n_device_stored_at_port)
            except ValueError:
                self.n_device_stored_at_port = 0
        else:
            self.n_device_stored_at_port = 0

        try:
            self.wec_layout = int(wec_layout)
        except ValueError:
            self.wec_layout = 1

        if tow_string_shutdown is not None:
            self.tow_string_shutdown = tow_string_shutdown

        if spacing is not None:
            self.spacing = float(spacing)
        else:
            self.spacing = 0.150

        self._check_attributes()

        self.rated_power = float(rated_power)
        self.pmatrix_file = str(pmatrix_file)

        if out_dir is not None:
            self.to_yaml(out_dir)
            logging.info('WaveEnergyConverter: WEC attributes saved as "%s".' % os.path.join(out_dir, 'wec.yaml'))


    def _check_attributes(self):
        """Validates :class:`WaveEnergyConverter` class attributes ranges."""
        if self.number_devices != 0 and any([
            self.rated_power == None,
            self.pmatrix_file == None,
            self.number_strings == None
        ]) is True:
            raise ValueError('if number_devices is defined, all arguments must be defined')
        if self.number_devices < 0:
            raise ValueError('"number_devices" must be greater than 0')
        if self.rated_power <= 0:
            raise ValueError('"rated_power" must be greater than 0')
        if self.pmatrix_file[-4:] != '.csv':
            raise ValueError('"pmatrix_file" must be a .csv file')
        if self.tow_string_shutdown is not None and not isinstance(self.tow_string_shutdown, bool):
            raise ValueError('"tow_string_shutdown" must be a boolean')
        if self.spacing <= 0:
            raise ValueError('"spacing" must be greater than 0')
        try:
            pd.read_csv(self.pmatrix_file, sep=',')
        except FileNotFoundError:
            _e = 'WaveEnergyConverter: power matrix file "%s"' % self.pmatrix_file
            _e += ' could not be found.'
            raise FileNotFoundError('Power matrix file could not be found.')

        if self.number_devices % self.number_strings !=0:
            if self.wec_layout != 5:   #TODO insert string definition in excel file use if on this parameter != None
                raise ValueError('"number_devices" must be divisible by "number_strings"')

        logging.debug('WaveEnergyConverter: attributes within ranges and valid.')


    def get_wec_from_yaml(
            file_path: str,
            out_dir: str=None
    ):
        """Reads a YAML file, fetches WEC information from it and returns
        a :class:`WaveEnergyConverter` item.

        Args:
            file_path (str): YAML file location.
            out_dir (str): Directory to save the WEC parameters. Defaults to `None`.

        Raises:
            FileNotFoundError: if the keys in the YAML file are not expected.
            FileNotFoundError: if the units of any of the keys in the YAML
                file are not expected.

        Returns:
            :obj:`WaveEnergyConverter`: WEC parameters.
        """
        # Initialize expected inputs
        number_devices = None
        rated_power = None
        pmatrix_file = None
        number_strings = None
        n_string_to_connector = None
        number_substations = None
        number_exportcables = None
        n_device_at_port = None
        n_device_stored_at_port = None
        wec_layout = None
        tow_string_shutdown = None
        spacing = None

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
                    logging.error('WaveEnergyConverter: ' + _e)
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
                        logging.error('WaveEnergyConverter: ' + _e)
                        raise FileNotFoundError(_e)
                else:
                    _e = '"rated_power" already defined. '
                    _e += 'Check if any of the other inputs have the words '
                    _e += '"rated" and "power".'
                    logging.error('WaveEnergyConverter: ' + _e)
                    raise FileNotFoundError(_e)
            if 'matrix' in key and 'file' in key:
                if pmatrix_file is None:
                    pmatrix_file = value
                else:
                    _e = '"pmatrix_file" already defined. '
                    _e += 'Check if any of the other inputs have the word '
                    _e += '"matrix" and "file".'
                    logging.error('WaveEnergyConverter: ' + _e)
                    raise FileNotFoundError(_e)
            if 'strings' in key and 'connector' not in key:
                if number_strings is None:
                    number_strings = value
                else:
                    _e = '"number_strings" alredy defines '
                    _e += 'Check if any of the other inputs have the word "strings".'
                    logging.error('WaveEnergyConverter: ' + _e)
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
                    logging.error('WaveEnergyConverter: ' +_e)
                    raise FileNotFoundError(_e)
            if 'export' in key and 'cables' in key:
                if number_exportcables is None:
                    number_exportcables = value
                else:
                    _e = '"number_exportcables" already defined.'
                    _e += 'Check if any of the other inputs have the words "export" and "cables".'
                    logging.error('WaveEnergyConverter: ' +_e)
                    raise FileNotFoundError(_e)
            if 'device' in key and 'port' in key and not 'stored' in key:
                if n_device_at_port is None:
                    n_device_at_port = value
                else:
                    _e = '"n_device_at_port" already defined.'
                    _e += 'Check if any of the other inputs have the words "device" and "port" and not "stored".'
                    logging.error('WaveEnergyConverter: ' +_e)
                    raise FileNotFoundError(_e)
            if 'device' in key and 'port' in key and 'stored' in key:
                if n_device_stored_at_port is None:
                    n_device_stored_at_port = value
                else:
                    _e = '"n_device_stored_at_port" already defined.'
                    _e += 'Check if any of the other inputs have the words "device" and "port" and "stored".'
                    logging.error('WaveEnergyConverter: ' +_e)
                    raise FileNotFoundError(_e)
            if 'layout' in key:
                if wec_layout is None:
                    wec_layout = value
            if 'tow' in key and 'string':
                if tow_string_shutdown is None:
                    tow_string_shutdown = value
            if 'spacing' in key:
                if spacing is None:
                    spacing = value
                else:
                    _e = '"spacing" already defined.'
                    _e += 'Check if any of the other inputs have the words "spacing"'
                    logging.error('WaveEnergyConverter: ' +_e)
                    raise FileNotFoundError(_e)

        wec_inputs = WaveEnergyConverter(
                number_devices=number_devices,
                rated_power=rated_power,
                pmatrix_file=pmatrix_file,
                number_strings=number_strings,
                n_string_to_connector = n_string_to_connector,
                number_substations=number_substations,
                number_exportcables=number_exportcables,
                n_device_at_port=n_device_at_port,
                n_device_stored_at_port=n_device_stored_at_port,
                tow_string_shutdown = tow_string_shutdown,
                wec_layout=wec_layout,
                spacing = spacing,
                out_dir=out_dir
        )

        _i = 'WaveEnergyConverter: WEC inputs read from file: "%s"' % file_path
        logging.info(_i)
        return wec_inputs


    def to_yaml(
            self,
            out_dir: str
    ):
        """
        Write the Wave system parameters to a YAML file.

        Args:
            out_dir (str): The output directory where the YAML file will be saved.
        """
        f = open(os.path.join(out_dir, 'wec.yaml'), 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        yaml.dump({
                "wec devices": {"value": self.number_devices, "units": "-"},
                "wec rated power": {"value": self.rated_power, "units": "MW"},
                "wec power matrix file": {"value": self.pmatrix_file, "units": "-"},
                "wec number of strings": {"value": self.number_strings, "units": "-"},
                "wec n strings to connector": {"value": self.n_string_to_connector, "units": "-"},
                "wec number of hub/substations": {"value": self.number_substations, "units": "-"},
                "wec number of export cables": {"value": self.number_exportcables, "units": "-"},
                "wec number of n device at port": {"value": self.n_device_at_port, "units": "-"},
                "wec number of n device stored at port": {"value": self.n_device_stored_at_port, "units": "-"},
                "wec tow string shutdown": {"value": self.tow_string_shutdown, "units": "-"},
                "wec type of layout": {"value": self.wec_layout, "units": "-"},
                "wec spacing": {"value": self.spacing, "units": "km"}
        }, f)
        f.close()


    def from_yaml(directory: str, name: str):
        """Recycle previous ~WaveEnergyConverter from a CSV file."""
        input_file_path = os.path.join(directory, str(name) + '.yaml')
        f = open(os.path.join(input_file_path), 'r')
        yaml=YAML(typ='safe')
        wec_yaml = yaml.load(f)
        f.close()
        wec_args = {
                "number_devices": wec_yaml["wec devices"]["value"],
                "rated_power": wec_yaml["wec rated power"]["value"],
                "pmatrix_file": wec_yaml["wec power matrix file"]["value"],
                "number_strings": wec_yaml["wec number of strings"]["value"],
                "n_string_to_connector": wec_yaml["wec n strings to connector"]["value"],
                "number_substations": wec_yaml["wec number of hub/substations"]["value"],
                "number_exportcables": wec_yaml["wec number of export cables"]["value"],
                "n_device_at_port": wec_yaml["wec number of n device at port"]["value"],
                "n_device_stored_at_port": wec_yaml["wec number of n device stored at port"]["value"],
                "tow_string_shutdown": wec_yaml["wec tow string shutdown"]["value"],
                "wec_layout": wec_yaml["wec type of layout"]["value"],
                "spacing": wec_yaml["wec spacing"]["value"],
        }
        for key, value in list(wec_args.items()):
            if value is None:
                del wec_args[key]
        wec = WaveEnergyConverter(**wec_args)

        logging.info('WaveEnergyConverter: WEC recycled from "%s".' % input_file_path)

        return wec


if __name__ == '__main__':

    wec = WaveEnergyConverter(
            number_devices=3,
            rated_power=8,
            pmatrix_file=os.path.join(
                    os.getcwd(),
                    'tests',
                    'test_files',
                    'pmatrix_wave.csv'
            ),
            number_strings=1,
            wec_layout=1,
            out_dir=os.path.join(os.getcwd(), 'tmp')
    )
    wec = WaveEnergyConverter.get_wec_from_yaml(
            file_path=os.path.join(
                    os.getcwd(),
                    'tests',
                    'test_files',
                    'inputs',
                    'wec.yaml'
            )
    )

    wec = WaveEnergyConverter.from_yaml(
            dir=os.path.join(os.getcwd(), 'tmp'),
            name='wec'
    )
