# Import packages
import pandas as pd
import os
import logging
from ruamel.yaml import YAML


class PVProduction():
    """PVProduction class.

    Note:
        If the "number_devices" is defined, the technology has to be defined and most attributes become mandatory.
        To not include the technology --> "number_devices" = 0 or None
        If "max_failure_module" not defined is set to 10000 and will not influence the code

    Attributes:
        number_devices (:obj:`int`): Number of PV devices. Defaults to ``None``.
        number_strings (:obj:`int`): Number of PV strings. Defaults to ``None``.
        number_inverters (:obj:`int`): Number of PV island. Defaults to ``None``.
        number_mv_transformers (:obj:`int`): Number of MV transformer. Defaults to ``None``.
        number_substations (:obj:`int`): Number of substations. Defaults to ``1``.
        number_export_cable (:obj:`int`): Number of number export cable. Defaults to ``1``.
        number_island_per_array_cable (:obj:`int`): Number of n_island_per_array_cable cable. Defaults to ``1``.
        device_power (:obj:`float`): Device power of each PV, in kW. Defaults to ``None``.
        pvprod_file (:obj:`str`): PV power matrix file path. Defaults to ``None``.
        degradation_rate (:obj:`float`): Yearly degradation rate of the panel. Defaults to ``0``.
        n_device_at_port (:obj:`int`): Number of island that can be mantained simultaneously at port.
            Defaults to ``1``
        n_device_stored_at_port (:obj:`int`): Number of island that can be stored when not in
            maintenance. Defaults to ``0``
        tow_string_shutdown (:obj:`bool`): Define if the electrical layout can sustain a tow without disconnect the string.
                Defaults to ``None``
        pv_layout (:obj:`int`): Type layout. Defaults to ``1``.
        max_failure_module (:obj:`int`): Max failure module on a string that can occure. Defaults to ``0``.
    Note:
        When the class is initialized, :func:`_check_attributes` is run.

    Example:
        >>> pv = PVProduction(
        >>>         number_devices=100,
        >>>         number_strings=10,
        >>>         number_inverters=2,
        >>>         number_mv_transformers=1,
        >>>         number_substations=1,
        >>>         number_export_cable=1,
        >>>         device_power=0.4,
        >>>         pvprod_file=os.path.join(
        >>>                     os.getcwd(),
        >>>                     'tests',
        >>>                     'test_files',
        >>>                     'pv_prod_month_hour.csv'
        >>>         ),
        >>>         pv_layout=1
        >>> )
    """

    def __init__(
            self,
            number_devices: int=None,
            number_strings: int=None,
            number_inverters: int=None,
            number_mv_transformers: int=None,
            number_substations: int=1,
            number_island_per_array_cable: int=1,
            number_export_cables: int=1,
            max_failure_module: int=None,
            device_power: float=None,
            pvprod_file: str=None,
            n_device_at_port: int=None,
            n_device_stored_at_port: int=None,
            tow_string_shutdown: bool = None,
            pv_layout: int=1,
            degradation_rate: float=None,
            out_dir: str=None
    ):
        """Initializes :class:`PVProduction` class.

        Args:
            number_devices (:obj:`int`): Number of PV devices. Defaults to ``None``.
            number_strings (:obj:`int`): Number of PV strings. Defaults to ``None``.
            number_inverters (:obj:`int`): Number of PV island. Defaults to ``None``.
            number_mv_transformers (:obj:`int`): Number of MV transformer. Defaults to ``None``.
            number_substations (:obj:`int`): Number of substations. Defaults to ``1``.
            number_export_cables (:obj:`int`): number of export cables. Defaults to ``1``.
            number_island_per_array_cable (:obj:`int`): Number of n_island_per_array_cable cable. Defaults to ``1``.
            max_failure_module (:obj:`int`): Max failure module on a string that can occure. Defaults to ``0``.
            device_power (:obj:`float`): Device power of each PV (in kW). Defaults to ``None``.
            pvprod_file (:obj:`str`): PV power matrix file path. Defaults to ``None``.            out_dir (:obj:`str`): directory to save the pv parameters. Defaults to `None`.
            pv_layout (:obj:`int`): Type layout. Defaults to ``1``.
            degradation_rate (:obj:`float`): Yearly degradation rate of the panel. Defaults to ``0``.
            n_device_at_port (:obj:`int`): Number of island that can be mantained simultaneously at port.
                Defaults to ``None``
            n_device_stored_at_port (:obj:`int`): Number of island that can be stored when not in
                maintenance. Defaults to ``None``
            tow_string_shutdown (:obj:`bool`): Define if the electrical layout can sustain a tow without disconnect the string.
                Defaults to ``None``
            out_dir (:obj:`str`): Directory to save the pv parameters. Defaults to `None`.
        """
        if number_devices != 0 and number_devices is not None:
            self.number_devices = int(number_devices)
            self.tow_string_shutdown = None
        else:
            logging.debug('PVProduction: PV farm is not defined')
            return

        if device_power is not None:
            self.device_power = float(device_power)
        else:
            self.device_power = device_power
        if pvprod_file is not None:
            self.pvprod_file = str(pvprod_file)
        else:
            self.pvprod_file = pvprod_file
        if number_strings != 0 and number_strings is not None:
            self.number_strings = int(number_strings)
        else:
            self.number_strings = 1
        if number_inverters != 0 and number_inverters is not None:
            self.number_inverters = int(number_inverters)
        else:
            self.number_inverters = None
        if number_mv_transformers != 0 and number_mv_transformers is not None:
            self.number_mv_transformers = int(number_mv_transformers)
        else:
            self.number_mv_transformers = None
        if number_substations != 0 and number_substations is not None:
            self.number_substations = int(number_substations)
        else:
            self.number_substations = 1
        if number_export_cables != 0 and number_export_cables is not None:
            self.number_export_cables = int(number_export_cables)
        else:
            self.number_export_cables = 1
        if number_island_per_array_cable != 0 and number_island_per_array_cable is not None:
            self.number_island_per_array_cable = int(number_island_per_array_cable)
        else:
            self.number_island_per_array_cable = 1
        if max_failure_module != 0 and max_failure_module is not None:
            self.max_failure_module = int(max_failure_module)
        else:
            self.max_failure_module = int(number_devices/2)
        if degradation_rate != 0 and degradation_rate is not None:
            self.degradation_rate = float(degradation_rate)
        else:
            self.degradation_rate = 0
        if n_device_at_port != 0 and n_device_at_port is not None:
            self.n_device_at_port = int(n_device_at_port)
        else:
            self.n_device_at_port = 1
        if n_device_stored_at_port != 0 and n_device_stored_at_port is not None:
            self.n_device_stored_at_port = int(n_device_stored_at_port)
        else:
            self.n_device_stored_at_port = 0
        if pv_layout !=0 and pv_layout is not None:
            self.pv_layout = int(pv_layout)
        else:
            self.pv_layout = 1
        if tow_string_shutdown is not None:
            self.tow_string_shutdown = tow_string_shutdown

        self._check_attributes()

        self.device_power = float(device_power)
        self.pvprod_file = str(pvprod_file)

        if out_dir is not None:
            self.to_yaml(out_dir)
            logging.info('PVProduction: pv attributes saved as "%s".' % os.path.join(out_dir, 'pv.yaml'))

    def _check_attributes(self):
        """Validates :class:`PVProduction` class attributes ranges."""
        if self.number_devices != 0 and any([
            self.number_strings == None,
            self.device_power == None,
            self.pvprod_file == None,
            self.number_inverters == None
        ]) is True:
            raise ValueError('if number_devices is defined, all arguments must be defined')
        if self.number_devices < 0:
            raise ValueError('"number_devices" must be greater than 0')
        if self.number_mv_transformers is not None and self.number_mv_transformers > self.number_inverters:
            raise ValueError('"number_mv_transformers" cannot be higher than "number_inverters"')
        if self.device_power <= 0:
            raise ValueError('"device_power" must be greater than 0')
        if self.pvprod_file[-4:] != '.csv':
            raise ValueError('"pmatrix_file" must be a .csv file')
        try:
            pd.read_csv(self.pvprod_file, sep=',')
        except FileNotFoundError:
            _e = 'PVProduction: power matrix file "%s"' % self.pvprod_file
            _e += ' could not be found.'
            raise FileNotFoundError('Power file could not be found.')
        if self.number_devices % self.number_inverters !=0:
            raise ValueError('"number_devices" must be divisible by "number_inverters"')
        if (self.number_devices/self.number_inverters) % self.number_strings !=0:
            raise ValueError('"number_devices/number_inverters" must be divisible by "number_strings"')
        if self.number_mv_transformers is not None and (self.number_inverters % self.number_mv_transformers) !=0:
            raise ValueError('"number_inverters" must be divisible by "number_mv_transformers"')
        if self.number_mv_transformers is not None and (self.number_mv_transformers % self.number_substations) != 0:
            raise ValueError('"number_mv_transformers" must be divisible by "number_substations"')
        if self.tow_string_shutdown is not None and not isinstance(self.tow_string_shutdown, bool):
            raise ValueError('"tow_string_shutdown" must be a boolean')

        logging.debug('PVProduction: attributes within ranges and valid.')

    def get_pv_from_yaml(
            file_path: str,
            out_dir: str=None
    ):
        """Reads a YAML file, fetches PV information from it and returns
        a :class:`PVProduction` item.

        Args:
            file_path (:obj:`str`): YAML file location.
            out_dir (:obj:`str`): Directory to save the PV parameters. Defaults to `None`.

        Raises:
            KeyError: if one of the YAML keys is input.
            KeyError: if one of the YAML keys is duplicated.

        Returns:
            :obj:`PVProduction`: PV parameters.
        """
        # Initialize expected inputs
        number_devices = None
        device_power = None
        pvprod_file = None
        number_strings = None
        number_inverters = None
        number_mv_transformers = None
        number_substations = None
        degradation_rate = None
        pv_layout = None
        max_failure_module = None
        number_export_cables = None
        number_island_per_array_cable = None
        n_device_at_port = None
        n_device_stored_at_port = None
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
                    logging.error('PVProduction: ' + _e)
                    raise KeyError(_e)
            if 'rated' in key and 'power' in key:
                if device_power is None:
                    if 'kw' in units:
                        device_power = value
                    elif 'w' in units:
                        device_power = round(value / 1000, 3)
                    else:
                        _e = 'Units of "rated_power" not recognized.'
                        _e += 'Please use "kW/device" or "W/device".'
                        logging.error('PVProduction: ' + _e)
                        raise KeyError(_e)
                else:
                    _e = '"rated_power" already defined. '
                    _e += 'Check if any of the other inputs have the words '
                    _e += '"device" and "power".'
                    logging.error('PVProduction: ' + _e)
                    raise KeyError(_e)
            if 'power' in key and 'file' in key:
                if pvprod_file is None:
                    pvprod_file = value
                else:
                    _e = '"pvprod_file" already defined. '
                    _e += 'Check if any of the other inputs have the word '
                    _e += '"power" and "file".'
                    logging.error('PVProduction: ' + _e)
                    raise KeyError(_e)
            if 'strings' in key:
                if number_strings is None:
                    number_strings = value
                else:
                    _e = '"number_strings" already defined.'
                    _e += 'Check if any of the other inputs have the wor "strings".'
                    logging.error('PVProduction: ' +_e)
                    raise KeyError(_e)
            if 'inverters' in key:
                if number_inverters is None:
                    number_inverters = value
                else:
                    _e = '"number_inverters" alredy defined,'
                    _e += 'Check if any of the other inputs have the word "inverters".'
                    logging.error('PVProduction: ' + _e)
                    raise FileNotFoundError(_e)
            if 'transformers' in key and 'mv' in key:
                if number_mv_transformers is None:
                    number_mv_transformers = value
                else:
                    _e = '"number_mv_transformers" alredy defined,'
                    _e += 'Check if any of the other inputs have the word "transformers".'
                    logging.error('PVProduction: ' + _e)
                    raise FileNotFoundError(_e)
            if 'substations' in key:
                if number_substations is None:
                    number_substations = value
                else:
                    _e = '"number_substations" alredy defined,'
                    _e += 'Check if any of the other inputs have the word "substations".'
                    logging.error('PVProduction: ' + _e)
                    raise FileNotFoundError(_e)
            if 'export' in key:
                if number_export_cables is None:
                    number_export_cables = value
                else:
                    _e = '"number_export_cables" alredy defined,'
                    _e += 'Check if any of the other inputs have the word "export".'
                    logging.error('PVProduction: ' + _e)
                    raise FileNotFoundError(_e)
            if 'island' in key and 'array' in key:
                if number_island_per_array_cable is None:
                    number_island_per_array_cable = value
                else:
                    _e = '"number_island_per_array_cable" alredy defined,'
                    _e += 'Check if any of the other inputs have the word "island" and "array".'
                    logging.error('PVProduction: ' + _e)
                    raise FileNotFoundError(_e)
            if 'degradation' in key:
                if degradation_rate is None:
                    degradation_rate = value
                else:
                    _e = '"degradation_rate" already defined.'
                    _e += 'Check if any of the other inputs have the words "degradation".'
                    logging.error('PVProduction: ' +_e)
                    raise KeyError(_e)
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
                if pv_layout is None:
                    pv_layout = value
            if 'tow' in key and 'string':
                if tow_string_shutdown is None:
                    tow_string_shutdown = value
            if 'max failure module' in key:
                if max_failure_module is None:
                    max_failure_module = value
                else:
                    _e = '"max failure module" alredy defined,'
                    _e += 'Check if any of the other inputs have the word "max failure module".'
                    max_failure_module = 10000

        pv_inputs = PVProduction(
                number_devices=number_devices,
                device_power=device_power,
                pvprod_file=pvprod_file,
                number_strings=number_strings,
                number_inverters=number_inverters,
                number_mv_transformers=number_mv_transformers,
                number_substations=number_substations,
                number_export_cables=number_export_cables,
                number_island_per_array_cable=number_island_per_array_cable,
                degradation_rate=degradation_rate,
                n_device_at_port=n_device_at_port,
                n_device_stored_at_port=n_device_stored_at_port,
                tow_string_shutdown = tow_string_shutdown,
                pv_layout=pv_layout,
                out_dir=out_dir,
                max_failure_module = max_failure_module
        )

        _i = 'PVProduction: PV inputs read from file: "%s".' % file_path
        logging.info(_i)
        return pv_inputs


    def to_yaml(
            self,
            out_dir: str
    ):
        """
        Write the PV system parameters to a YAML file.

        Args:
            out_dir (:obj:`str`): The output directory where the YAML file will be saved.
        """
        f = open(os.path.join(out_dir, 'pv.yaml'), 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        yaml.dump({
                "pv devices": {"value": self.number_devices, "units": "-"},
                "pv device power": {"value": self.device_power, "units": "kW"},
                "pv power matrix file": {"value": self.pvprod_file, "units": "-"},
                "pv number of strings": {"value": self.number_strings, "units": "-"},
                "pv number of inverters": {"value": self.number_inverters, "units": "-"},
                "pv number mv transformers": {"value": self.number_mv_transformers, "units":"-"},
                "pv number substations": {"value": self.number_substations, "units":"-"},
                "pv number export cables": {"value": self.number_export_cables, "units":"-"},
                "pv number island per array": {"value": self.number_island_per_array_cable, "units":"-"},
                "pv degradation rate": {"value": self.degradation_rate, "units": "-"},
                "pv number of n device at port": {"value": self.n_device_at_port, "units": "-"},
                "pv number of n device stored at port": {"value": self.n_device_stored_at_port, "units": "-"},
                "pv tow string shutdown": {"value": self.tow_string_shutdown, "units": "-"},
                "pv type layout": {"value": self.pv_layout, "units": "-"},
                "pv max failure module": {"value": self.max_failure_module, "units": "-"}
        }, f)
        f.close()


    def from_yaml(directory: str, name: str):
        """Recycle previous ~PVProduction from a YAML file."""
        input_file_path = os.path.join(directory, str(name) + '.yaml')
        f = open(os.path.join(input_file_path), 'r')
        yaml=YAML(typ='safe')
        pv_yaml = yaml.load(f)
        f.close()
        pv_args = {
                "number_devices": pv_yaml["pv devices"]["value"],
                "device_power": pv_yaml["pv device power"]["value"],
                "pvprod_file": pv_yaml["pv power matrix file"]["value"],
                "number_strings": pv_yaml["pv number of strings"]["value"],
                "number_inverters": pv_yaml["pv number of inverters"]["value"],
                "number_mv_transformers": pv_yaml["pv number mv transformers"]["value"],
                "number_substations": pv_yaml["pv number substations"]["value"],
                "number_export_cables": pv_yaml["pv number export cables"]["value"],
                "number_island_per_array_cable": pv_yaml["pv number island per array"]["value"],
                "degradation_rate": pv_yaml["pv degradation rate"]["value"],
                "n_device_at_port": pv_yaml["pv number of n device at port"]["value"],
                "n_device_stored_at_port": pv_yaml["pv number of n device stored at port"]["value"],
                "tow_string_shutdown": pv_yaml["pv tow string shutdown"]["value"],
                "pv_layout": pv_yaml["pv type layout"]["value"],
                "max_failure_module": pv_yaml["pv max failure module"]["value"]
        }
        for key, value in list(pv_args.items()):
            if value is None:
                del pv_args[key]
        pv = PVProduction(**pv_args)

        logging.info('PVProduction: pv recycled from "%s".' % os.path.join(dir, input_file_path))

        return pv


    def pv_farm_statistical_analysis(
            pvprod_file: str,
            number_devices: int
    ):
        '''
        Args:
            pvprod_file (:obj:`str`): File path of the production per month per hour for one device in W.
            number_devices (:obj:`int`): Total number of devices in the PV farm.
        Returns:
            :obj:`pd.DataFrame` production per month per hour of whole farm in kw
        '''
        df_pv = pd.read_csv(pvprod_file,sep=',', index_col=False)
        df_pv.columns = ['hour'] + list(range(1,13))

        for i in df_pv.columns:
            if i != 'hour':
                df_pv[i] = df_pv[i]*number_devices/1000 # in kW
            else: continue
        return df_pv



if __name__ == '__main__':

    pv = PVProduction(
            number_devices=100,
            number_strings=25,
            device_power=None,
            pvprod_file=os.path.join(
                    os.getcwd(),
                    'tests',
                    'test_files',
                    'pv_prod_month_hour.csv'
            ),
            number_inverters=2,
            out_dir=os.path.join(os.getcwd(), 'tmp')
    )
    pv = PVProduction.get_pv_from_yaml(
            file_path=os.path.join(
                    os.getcwd(),
                    'tests',
                    'test_files',
                    'inputs',
                    'pv.yaml'
            )
    )

    pv = PVProduction.from_yaml(
            dir=os.path.join(os.getcwd(), 'tmp'),
            name='pv'
    )
