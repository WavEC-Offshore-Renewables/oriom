import logging
import os
import math as mt
from ruamel.yaml import YAML
from oriom.utils.yaml_manager import inputs_to_yaml
from oriom.domain.Scenario import Scenario

try:
    from oriom.core.functions.private.check_files import check_file_exists
except ImportError:
    check_file_exists = None

class TimeSeries():
    """Project Time Series Analysis related inputs. Project :class:`Inputs.TimeSeries` can
    be defined either with a YAML file or one-by-one. If `file_inputs` parameter isgiven,
    the other parameters will not be considered.

    Note:
        The :attr:`max_wait` defines the maximum wait on weather allowed between activities
        (from :class:`activities`). If the wait is higher than the allowed time the operation
        cannot be scheduled and gets postponed.

    Attributes:
        site_lat (:obj:`dict`): Site latitude, in degrees.
            **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
        site_lon (:obj:`dict`): Site longitude, in degrees.
            **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
        file_metocean (:obj:`dict`): Path location of the site metocean date timeseries.
            **keys**: *value*: :obj:`str` ; *units*: :obj:`str`.
        file_metocean_port (:obj:`dict`): Path location of the port metocean date timeseries.
            **keys**: *value*: :obj:`str` ; *units*: :obj:`str`.
        metocean_ws_height (:obj:`dict`): Wind speed at measurement height, in meters.
            **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
        surface_roughness (:obj:`dict`): Sea surface roughness, in meters.
            **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
        distance (:obj:`dict`): Marine distance from site to port, in killometers.
            **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
        time_between_devices_PV (:obj:`dict`): Transit time to move from one PV device to anorther, in hours.
            **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
        time_between_devices_WT (:obj:`dict`): Transit time to move from one WT device to anorther, in hours.
            **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
        time_between_devices_WEC (:obj:`dict`): Transit time to move from one WEC device to anorther, in hours.
            **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
        max_wait (:obj:`dict`): Maximum waiting on weather time between activities, in hours. Its value is :obj:`8.0` hours if not defined.
            **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
        montecarlo_percent (:obj:`dict`): Ratio of metocean timesteps to be analyzed. Its value is :obj:`0.3` if not defined.
            **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
        failure_scenario (:obj:`dict`): Selection of failure scenario. Its value is :obj:`0` if not defined.
            **keys**: *value*: :obj:`int` ; *units*: :obj:`str`.
        shift_duration (:obj:`dict`): Duration of a working shift, in hours.
            **keys**: *value*: :obj:`int` ; *units*: :obj:`str`.
        merge_vessel (:obj:`list`): Vessel type that can be merged in corrective operation
            **keys**: *value*: :obj:`str` ; *units*: :obj:`str`.
        file_inputs (:obj:`str`): Path for the file with all previous mandatory inputs.
            Its value is ``None`` if not defined.
        time_between_devices_dict (:obj:`dict`): Time between device per each tech
        file_metocean_tow_location (:obj:`dict`): Dictionary of X Path location of the metocean date timeseries X  file between site and port.
            **keys**: dict(X :obj:`int`: *value*: :obj:`str` ; *units*: :obj:`str`.)
        file_metocean_tow_distance (:obj:`dict`): Dictionary of X distance from site of the metocean date timeseries X file between site and port.
            **keys**: dict(X :obj:`int`: *value*: :obj:`flaot` ; *units*: :obj:`str`.)
        file_metocean_tow_number (:obj:`dict`): Path location of the metocean date timeseries.
            **keys**: *value*: :obj:`int` ; *units*: :obj:`str`.
        file_electric_loss (:obj:`dict`): Path location of the electric losses file.
            **keys**: *value*: :obj:`str` ; *units*: :obj:`str`.
        file_wake_loss (:obj:`dict`): Path location of the wake losses file.
            **keys**: *value*: :obj:`str` ; *units*: :obj:`str`.

    Note:
        When the class is initialized :func:`_check_attributes` is run.

    Example:
        >>> args = {
        >>>         "site_latitude": 41,
        >>>         "site_longitude": -9,
        >>>         "file_metocean": os.path.join(
        >>>                 os.getcwd(),
        >>>                 'tests', 'test_files', 'metocean', 'metocean_dummy.csv'
        >>>         ),
        >>>         "metocean_ws_height": 10,
        >>>         "surface_roughness": 0.0002,
        >>>         "dist_port": 50,
        >>>         "time_between_devices_pv": 0.01,
        >>>         "time_between_devices_wt": 0.1,
        >>>         "time_between_devices_wec": 0.1,
        >>>         "max_wait": 8,
        >>>         "montecarlo_percentage": 0.3,
        >>>         "shift_duration": 12
        >>> }
        >>> inputs = Inputs.TimeSeries(**args)
        >>> logging.info('The site coordinates are (%.2f,%.2f)' % \
        >>>         (inputs.site_latitude["value"], inputs.site_longitude["units"]))
    """

    def __init__(self, **kwargs):
        """Initializes :class:`Inputs.TimeSeries`.

        Args:
            **kwargs: Arbitrary keyword arguments.

        Keyword Args:
            site_latitude (:obj:`float`): Site latitude, in degrees.
            site_longitude (:obj:`float`): Site longitude, in degrees.
            file_metocean (:obj:`str`): Path location of the site metocean date timeseries.
            file_metocean_port (:obj:`str`): Path location of the port metocean date timeseries.
            dist_port (:obj:`float`): Marine distance from site to port, in killometers.
            time_between_devices_PV (:obj:`float`): Transit time to move from one PV device to anorther, in hours.
            time_between_devices_WT (:obj:`float`): Transit time to move from one WT device to anorther, in hours.
            time_between_devices_WEC (:obj:`float`): Transit time to move from one WEC device to anorther, in hours.
            surface_roughness (:obj:`float`,*optional*): Surface roughness of sea. Defaults to ``0.0002``.
            metocean_ws_height (:obj:`float`,*optional*): Wind speed measurement height. Defaults to ``10.0``.
            max_wait (:obj:`float`,*optional*): Maximum waiting on weather time between activities, in hours. Defaults to ``8.0``.
            montecarlo_percentage (:obj:`float`,*optional*): Ratio of metocean timesteps to be analyzed. Defaults to ``0.3``.
            failure_scenario (:obj:`float`,*optional*): failure scenario selection. Defaults to ``0``.
            shift_duration (:obj:`int`,*optional*): Duration of a working shift. Defaults to ``12``.
            merge_vessel (:obj:`list`,*optional*): Vessel type that can be merged in corrective operation.
            file_inputs (:obj:`str`,*optional*): Path for the file with all previous mandatory inputs. Defaults to ``None``.
            file_metocean_tow_location (:obj:`dict`): Dictionary of Path location of the X metocean date timeseries from site to port.
            file_metocean_tow_distance (:obj:`dict`): Dictionary of X distance in km from site of the metocean timeseries X file.
            file_metocean_tow_number (:obj:`int`): Number of Path location of the X metocean date timeseries from site to port.
            file_electric_loss (:obj:`str`): Path location of the electric losses file.
            file_wake_loss (:obj:`str`): Path location of the wake losses file.
            scenarios_file (obj:`str`) Path location of the failure Scenarios file.


        Raises:
            NameError: units of :attr:`site_latitude` not recognized.
            NameError: units of :attr:`site_longitude` not recognized.
            NameError: units of :attr:`dist_port` not recognized.
            NameError: units of :attr:`time_between_devices` not recognized.
            NameError: units of :attr:`max_wait` not recognized.
        """
        self.inputs = {}

        # Default values
        self.inputs["surface roughness"] = {"value" : 0.0002, "units": 'metres'}
        self.inputs["time between devices pv"] = {"value": 0.015, "units": 'hours'}
        self.inputs["time between devices wt"] = {"value": 0.1, "units": 'hours'}
        self.inputs["time between devices wec"] = {"value": 0.1, "units": 'hours'}
        self.inputs["metocean ws height"] = {"value": 10.0, "units" : 'metres'}
        self.inputs["max wait"] = {"value": 8.0, "units": 'hours'}
        self.inputs["montecarlo percentage"] = {"value": 0.3, "units": None}
        self.inputs["length export cable"] = {"value": 0, "units": 'km'}
        self.inputs["shift duration"] = {"value": 12, "units": 'hours'}
        self.inputs["merge vessel"] = {"value": None, "units": 'vessel type'}
        self.inputs["failure scenario"] = {"value": 0, "units": None}
        self.inputs["metocean file tow number"] = {"value": 0, "units": None}
        self.inputs["metocean file port"] = {"value": None, "units": None}
        self.inputs["metocean file tow location"] = {}
        self.inputs["metocean file tow distance"] = {}
        self.inputs["electric file losses"] = {"value": None, "units": None}
        self.inputs["wake file losses"] = {"value": None, "units": None}
        self.inputs["scenarios_file"] = {"value": None, "units": None}

        file_path = kwargs.get('file_inputs', None)
        if file_path is not None:
            # Gets inputs from a yaml file
            f_yaml = open(os.path.join(file_path), 'r')
            yaml = YAML(typ='safe')
            inputs_yaml = yaml.load(f_yaml)
            f_yaml.close()

            # Verify inputs in df_inputs and organize them in dictionaries
            for key, values in inputs_yaml.items():
                name = key.lower()
                value = values['value']

                try:
                    if mt.isnan(float(value)) is True:
                        continue
                except (ValueError,TypeError):
                    pass

                units = str(values['units'])

                if 'site' in name and 'latitude' in name:
                    if 'degree' not in units.lower():
                        raise NameError('Units "%s" not recognized for Site Latitude input.' % units)
                    self.inputs["site latitude"] = {"value": float(value), "units": str(units)}

                elif 'site' in name and 'longitude' in name:
                    if 'degree' not in units.lower():
                        raise NameError('Units "%s" not recognized for Site Longitude input.' % units)
                    self.inputs["site longitude"] = {"value": float(value), "units": str(units)}

                elif 'metocean' in name and 'file' in name and 'tow' not in name and 'port' not in name:
                    self.inputs["metocean file location"] = {"value": value, "units": None}

                elif 'metocean' in name and 'file' in name and 'tow' not in name and 'port' in name:
                    self.inputs["metocean file port"] = {"value": value, "units": None}

                elif 'metocean' in name and any(word in name for word in ['windspeed', 'wind speed', 'ws']) and 'height' in name:
                    self.inputs["metocean ws height"] = {"value": float(value), "units": str(units)}

                elif 'surface' in name and 'roughness' in name:
                    self.inputs["surface roughness"] = {"value": float(value), "units": str(units)}

                elif 'distance' in name and 'port' in name:
                    if units.lower() == 'km' or 'kilometer' in units.lower() or 'kilometre' in units.lower():
                        units = 'km'
                    elif units.lower() == 'm':
                        value = value / 1000
                        units = 'km'
                    else:
                        raise NameError('Units "%s" not recognized for Distance to Port input.' % units)
                    self.inputs["distance to port"] = {"value": float(value), "units": str(units)}

                elif 'time' in name and 'between' in name and 'devices' in name and 'pv' in name:
                    if 'hour' in units.lower():
                        units = 'hours'
                    elif 'minute' in units.lower():
                        value = value / 60
                        units = 'hours'
                    else:
                        raise NameError('Units "%s" not recognized for Transit Time Between pv Devices input.' % units)
                    self.inputs["time between devices pv"] = {"value": float(value), "units": str(units)}

                elif 'time' in name and 'between' in name and 'devices' in name and 'wt' in name:
                    if 'hour' in units.lower():
                        units = 'hours'
                    elif 'minute' in units.lower():
                        value = value / 60
                        units = 'hours'
                    else:
                        raise NameError('Units "%s" not recognized for Transit Time Between wt Devices input.' % units)
                    self.inputs["time between devices wt"] = {"value": float(value), "units": str(units)}

                elif 'time' in name and 'between' in name and 'devices' in name and 'wec' in name:
                    if 'hour' in units.lower():
                        units = 'hours'
                    elif 'minute' in units.lower():
                        value = value / 60
                        units = 'hours'
                    else:
                        raise NameError('Units "%s" not recognized for Transit Time Between wec Devices input.' % units)
                    self.inputs["time between devices wec"] = {"value": float(value), "units": str(units)}

                elif 'max' in name and 'wait' in name:
                    if 'hour' not in units.lower():
                        raise NameError('Units "%s" not recognized for Max WoW between activities input.' % units)
                    self.inputs["max wait"] = {"value": int(value), "units": str(units)}

                elif 'montecarlo' in name and 'percent' in name:
                    self.inputs["montecarlo percentage"] = {"value": float(value), "units": None}

                elif 'failure' in name and 'scenario' in name:
                    self.inputs["failure scenario"] = {"value": int(value), "units": None}

                elif 'length' in name and 'export' in name:
                    self.inputs["length export cable"] = {"value": int(value), "units": str(units)}

                elif 'shift' in name and 'duration' in name:
                    self.inputs["shift duration"] = {"value": int(value), "units": str(units)}

                elif 'shifts' in name and 'double' in name:
                    self.inputs["double shifts"] = {"value": bool(value), "units": str(units)}

                elif 'merge' in name and 'vessel' in name:
                    self.inputs["merge vessel"] = {"value": list(value), "units": str(units)}

                elif 'metocean' in name and 'file' in name and 'tow' in name and 'number' in name:
                    self.inputs["metocean file tow number"] = {"value": int(value), "units": None}

                elif 'metocean' in name and 'file' in name and 'tow' in name and 'number' not in name and 'distance' not in name:
                    if value:
                        key_n = name[-1]
                        self.inputs["metocean file tow location"][int(key_n)] = {"value": value, "units": None}
                elif 'metocean' in name and 'tow' in name and 'distance' in name:
                    if value:
                        key_n = name[-1]
                        self.inputs["metocean file tow distance"][int(key_n)] = {"value": value, "units": None}
                elif 'electric' in name and 'losses' in name:
                    self.inputs["electric file losses"] = {"value": value, "units": None}
                elif 'wake' in name and 'losses' in name:
                    self.inputs["wake file losses"] = {"value": value, "units": None}
                else:
                    logging.warning('Inputs.TimeSeries: input "%s" not recognized. Ignored.' % key)
            logging.info('Inputs.TimeSeries: inputs read from a YAML file: "%s".' % file_path)

        # If a yaml file is not provided, gets inputs from **kwargs
        else:
            for key, value in kwargs.items():
                if key.lower() == 'site_latitude':
                    self.inputs["site latitude"] = {
                            "value": float(value),
                            "units": 'degree'
                    }
                elif key.lower() == 'site_longitude':
                    self.inputs["site longitude"] = {
                            "value": float(value),
                            "units": 'degree'
                    }
                elif key.lower() == 'file_metocean':
                    self.inputs["metocean file location"] = {
                            "value": str(value),
                            "units": None
                    }
                elif key.lower() == 'file_metocean_port':
                    self.inputs["metocean file port"] = {
                            "value": str(value),
                            "units": None
                    }
                elif key.lower() == 'metocean_ws_height':
                    self.inputs["metocean ws height"] = {
                            "value": float(value),
                            "units": 'm'
                    }
                elif key.lower() == 'surface_roughness':
                    self.inputs["surface roughness"] = {
                            "value": float(value),
                            "units": 'm'
                    }
                elif key.lower() == 'dist_port':
                    self.inputs["distance to port"] = {
                            "value": float(value),
                            "units": 'km'
                    }
                elif key.lower() == 'time_between_devices_pv':
                    self.inputs["time between devices pv"] = {
                            "value": float(value),
                            "units": 'hours'
                    }

                elif key.lower() == 'time_between_devices_wt':
                    self.inputs["time between devices wt"] = {
                            "value": float(value),
                            "units": 'hours'
                    }

                elif key.lower() == 'time_between_devices_wec':
                    self.inputs["time between devices wec"] = {
                            "value": float(value),
                            "units": 'hours'
                    }

                elif key.lower() == 'max_wait':
                    self.inputs["max wait"] = {
                            "value": int(value),
                            "units": 'hours'
                    }
                elif key.lower() == 'montecarlo_percentage':
                    self.inputs["montecarlo percentage"] = {
                            "value": float(value),
                            "units": None
                    }
                elif key.lower() == 'failure_scenario':
                    self.inputs["failure scenario"] = {
                            "value": int(value),
                            "units": None
                    }
                elif key.lower() == 'length_export_cable':
                    self.inputs["length export cable"] = {
                            "value": float(value),
                            "units": None
                    }
                elif key.lower() == 'shift_duration':
                    self.inputs["shift duration"] = {
                            "value": int(value),
                            "units": 'hours'
                    }
                elif key.lower() == 'double_shifts':
                    self.inputs["double shifts"] = {
                            "value": bool(value),
                            "units": 'hours'
                    }
                elif key.lower() == 'merge_vessel':
                    self.inputs["merge vessel"] = {
                            "value": list(value),
                            "units": None
                    }
                elif key.lower() == 'file_electrical_losses':
                    self.inputs["electric file losses"] = {
                            "value": str(value),
                            "units": None
                    }
                elif key.lower() == 'file_wake_losses':
                    self.inputs["wake file losses"] = {
                            "value": str(value),
                            "units": None
                    }
                elif key.lower() == 'out_dir':
                    pass
                elif key.lower().startswith('file_metocean_tow_location'):
                    if value:
                        key_n = key[-1]
                        self.inputs["metocean file tow location"][int(key_n)] = {"value": value, "units": None}
                elif key.lower().startswith('file_metocean_tow_distance'):
                    if value:
                        key_n = key[-1]
                        self.inputs["metocean file tow distance"][int(key_n)] = {"value": value, "units": None}
                elif key.lower() == 'file_metocean_tow_number':
                    self.inputs["metocean file tow number"] = {
                            "value": int(value),
                            "units": None
                    }
                else:
                    logging.warning('Inputs.TimeSeries: input "%s" not recognized. Ignored.' % key)
            logging.info('Inputs.TimeSeries: inputs read from arguments')

        # Set values inside the inputs dict as direct attributes
        # from the Inputs.TimeSeries class
        self.site_lat = self.inputs.get('site latitude')
        self.site_lon = self.inputs.get('site longitude')
        self.file_metocean = self.inputs.get('metocean file location')
        self.file_metocean_port = self.inputs.get('metocean file port')
        self.metocean_ws_height = self.inputs.get('metocean ws height')
        self.surface_roughness = self.inputs.get('surface roughness')
        self.distance = self.inputs.get('distance to port')
        self.time_between_devices_pv = self.inputs.get('time between devices pv')
        self.time_between_devices_wt = self.inputs.get('time between devices wt')
        self.time_between_devices_wec = self.inputs.get('time between devices wec')
        self.max_wait = self.inputs.get('max wait')
        self.montecarlo_percent = self.inputs.get('montecarlo percentage')
        self.failure_scenario = self.inputs.get('failure scenario')
        self.length_export = self.inputs.get('length export cable')
        self.shift_duration = self.inputs.get('shift duration')
        self.double_shifts = self.inputs.get('double shifts')
        self.merge_vessel = self.inputs.get('merge vessel')
        self.file_wake_loss = self.inputs.get('wake file losses')
        self.file_electrical_loss = self.inputs.get('electric file losses')
        self.merge_vessel = self.inputs.get('merge vessel')
        self.file_metocean_tow_number = self.inputs.get('metocean file tow number')
        if self.inputs.get('metocean file tow location'):
            self.file_metocean_tow_location = self.inputs.get('metocean file tow location')
        else:
            self.inputs.pop('metocean file tow location')
        if self.inputs.get('metocean file tow distance'):
            self.file_metocean_tow_distance = self.inputs.get('metocean file tow distance')
        else:
            self.inputs.pop('metocean file tow distance')
        self.scenario = 0
        self.time_between_devices_dict = {
            'opv': self.time_between_devices_pv["value"],
            'ofw': self.time_between_devices_wt["value"],
            'owc': self.time_between_devices_wec["value"]
        }

        # Define scenario for failure event
        if kwargs.get('scenarios_file'):
            self.scenario = Scenario.get_scenarios_from_yaml(file_path = kwargs['scenarios_file'])
        else:
            self.scenario = Scenario.create_equal_scenarios()
        

        self._check_attributes()

        # Save inputs as a YAML file
        out_dir = kwargs.get('out_dir')
        if out_dir is not None:
            inputs_to_yaml(self, out_dir, 'inputs_tseries')


    def _check_attributes(self):
        """
        This method validates the attributes of the `Inputs.TimeSeries` class to ensure they
        have valid values and fall within specified ranges.

        Raises errors if any attribute is outside the specified range.
        """
        if self.site_lat is None:
            raise ValueError('"Site latitude" must be defined')
        if self.site_lon is None:
            raise ValueError('"Site longitude" must be defined')
        if self.file_metocean is None:
            raise ValueError('"Metocean file path" must be defined')
        if self.distance is None:
            raise ValueError('"Distance to port" must be defined')

        if self.site_lat["value"] < -90 or self.site_lat["value"] > 90:
            raise ValueError('"Site latitude" must be between -90 and 90 degrees')
        if self.site_lon["value"] < -180 or self.site_lon["value"] > 180:
            raise ValueError('"Site longitude" must be between -180 and 180 degrees')
        open(self.file_metocean["value"], 'r')
        if self.file_metocean_port["value"]:
            open(self.file_metocean_port["value"], 'r')
        if self.metocean_ws_height["value"] <= 0:
            raise ValueError('"Metocean wind speed height" must be greater than 0')
        if self.surface_roughness["value"] <= 0:
            raise ValueError('"Surface roughness" must be greater than 0')
        if self.surface_roughness["value"] > 0.01:
            _w = "Surface roughness attribute attribute is higher than 0.01. "
            _w += "The industry standard for offshore wind sites is 0.0002"
            logging.warning('Inputs.TimeSeries: ' + _w)
        if self.distance["value"] <= 0:
            raise ValueError('"Distance to port" must be greater than 0')
        if self.time_between_devices_pv["value"] <= 0:
            raise ValueError('"Transit Time Between pv Devices" must be greater than 0')
        if self.time_between_devices_wt["value"] <= 0:
            raise ValueError('"Transit Time Between wt Devices" must be greater than 0')
        if self.time_between_devices_wec["value"] <= 0:
            raise ValueError('"Transit Time Between wec Devices" must be greater than 0')
        if self.max_wait is not None and self.max_wait["value"] < 0:
            raise ValueError('"Max WoW between activities" must not be negative')
        if self.file_wake_loss["value"]:
            open(self.file_wake_loss["value"], 'r')
        if self.file_electrical_loss["value"]:
            open(self.file_electrical_loss["value"], 'r')
        if (self.montecarlo_percent is not None and(
            self.montecarlo_percent["value"] <= 0 or self.montecarlo_percent["value"] > 1
            )
        ):
            raise ValueError('"Timeseries analysed percentage (montecarlo)" must be between 0 and 1')
        if self.length_export["value"] < 0:
            raise ValueError('"Length of export cable" must not be negative')
        if self.failure_scenario["value"] < 0:
            raise ValueError('"failure scenario selection" must not be negative')
        if self.failure_scenario["value"] not in self.scenario:
            raise ValueError('"failure scenario selection" must not be negative')
        if self.shift_duration["value"] <= 0:
            raise ValueError('"Duration of a shift" must be greater than 0')
        if self.file_metocean_tow_number["value"] < 0:
            raise ValueError('"Metocean tow file number" must not be negative')
        if self.file_metocean_tow_number["value"] > 0:
            if getattr(self, "file_metocean_tow_location", None):
                if len(self.file_metocean_tow_location) != self.file_metocean_tow_number["value"]:
                    raise ValueError('Number of "Metocean tow file location" and "Metocean tow file number" must coincide')
                for i in range(1, self.file_metocean_tow_number["value"]+1):
                    open(self.file_metocean_tow_location[i]["value"], 'r')
                if len(self.file_metocean_tow_distance) != len(self.file_metocean_tow_location):
                    raise ValueError('Number of "Metocean tow file location" and "Metocean tow file distance" must coincide')
                for i in range(1, self.file_metocean_tow_number["value"]+1):
                    if self.file_metocean_tow_distance[i]["value"] <= 0:
                        raise ValueError(f'"Metocean tow file distance" from site of the metocean location {i}" must be greater than 0')
            else:
                raise ValueError('"Metocean file path location tow" must be defined if "Metocean tow file number" is defined')
        if getattr(self, "file_metocean_tow_location", None) and self.file_metocean_tow_number["value"] == 0:
            raise ValueError('"Metocean tow file number" must be defined if ""Metocean file path tow"" are defined')
        logging.debug('Inputs.TimeSeries: attributes within ranges and valid.')

    @classmethod
    def from_yaml(cls, dir: str, name: str, scenarios_file:str):
        """Recycle previous ~Inputs.TimeSeries from a YAML file.

        Args:
            name (:obj:`str`): Name of the YAML file.
        """
        input_file_path = os.path.join(dir, str(name) + '.yaml')
        with open(input_file_path, "r") as f:
            yaml = YAML(typ="safe")
            input_yaml = yaml.load(f)
        number_tow_file = input_yaml["metocean file tow number"]["value"]
        input_args = {
                "site_latitude": input_yaml["site latitude"]["value"],
                "site_longitude": input_yaml["site longitude"]["value"],
                "file_metocean": input_yaml["metocean file location"]["value"],
                "file_metocean_port": input_yaml["metocean file port"]["value"],
                "surface_roughness": input_yaml["surface roughness"]["value"],
                "dist_port": input_yaml["distance to port"]["value"],
                "time_between_devices_pv": input_yaml["time between devices pv"]["value"],
                "time_between_devices_wt": input_yaml["time between devices wt"]["value"],
                "time_between_devices_wec": input_yaml["time between devices wec"]["value"],
                "max_wait": input_yaml["max wait"]["value"],
                "montecarlo_percentage": input_yaml["montecarlo percentage"]["value"],
                "length_export": input_yaml["length export cable"]["value"],
                "shift_duration": input_yaml["shift duration"]["value"],
                "double_shifts": input_yaml["double shifts"]["value"],
                "merge_vessel": input_yaml["merge vessel"]["value"],
                "metocean_ws_height": input_yaml["metocean ws height"]["value"],
                "file_metocean_tow_number": input_yaml["metocean file tow number"]["value"],
                "file_wake_losses": input_yaml["wake file losses"]["value"],
                "file_electrical_losses": input_yaml["electric file losses"]["value"],
                "scenarios_file": scenarios_file
        }

        number_tow_file = input_yaml["metocean file tow number"]["value"]
        if number_tow_file > 0:
            for i in range(1, number_tow_file + 1):
                input_args[f"file_metocean_tow_location_{i}"] = input_yaml[f"metocean file tow location {i}"]["value"]
                input_args[f"file_metocean_tow_distance_{i}"] = input_yaml[f"metocean file tow distance {i}"]["value"]

        input_args = {k: v for k, v in input_args.items() if v is not None}

        inputs = cls(**input_args)

        logging.info('Inputs.TimeSeries: inputs recycled from "%s"', input_file_path)

        return inputs


    @classmethod
    def from_run_dir(cls, run_dir: str, file_inputs: str, scenarios_file: str):
        """
        Build a TimeSeries instance from a run directory.

        - If 'inputs_tseries.yaml' exists under run_dir, reuse it with from_yaml().
        - Otherwise, create a new instance from the provided file_inputs.

        Args:
            run_dir (str): Path to the simulation run directory.
            file_inputs (str): Path to the TimeSeries YAML file to use if not already present.
            scenarios_file (str): Path to the Scenario YAML file to use.

        Returns:
            TimeSeries: A fully constructed instance.
        """
        if check_file_exists and check_file_exists(run_dir, file_name="inputs_tseries.yaml"):
            return cls.from_yaml(dir=run_dir, name="inputs_tseries", scenarios_file = scenarios_file)
        return cls(file_inputs=file_inputs, out_dir=run_dir, scenarios_file = scenarios_file)


    def get_inputs(self):
        """Prints :class:`Inputs.TimeSeries` to the command line."""
        for input, value in self.inputs.items():
            logging.info('%s - value: %s ; units: %s' % (input, value["value"], value["units"]))

    def find_time_between_devices(self, operation_obj_id):
        """ Find the time_between_devices of the technology corrispondent to the operation passed"""
        time_between_devices = next(
            (self.time_between_devices_dict[p] for p in ["opv", "ofw", "owc"] if p in operation_obj_id),
            None
        )
        if time_between_devices is None:
            logging.warning(
                "Time between devices not found for %s, value set at time_between_devices = 0.1",
                operation_obj_id
            )
            time_between_devices = 0.1
        return time_between_devices
