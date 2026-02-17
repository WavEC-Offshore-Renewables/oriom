# Import packages
import pandas as pd
import math as mt
import os
import shutil
import logging
from ruamel.yaml import YAML

from oriom.utils.yaml_manager import inputs_to_yaml

try:
    from oriom.core.functions.private.check_files import check_file_exists
except ImportError:
    check_file_exists = None

class Inputs():
    class General():
        """Project general inputs. Project :class:`Inputs.General` can be defined either
        with a YAML file or one-by-one. If `file_inputs` parameters is given,
        the other parameters will not be considered.

        Note:
            Possible actions:

            - Use previous run directory:
                A previous directory is used to copy the files related to the metocean and technologies.
                If "consider_tseries" is True per operations the "activity", "workability", "startability",
                and "operation_schedule" file are copied.
                If the code only finds some of the mentioned files or finds them for only some of the operations,
                the missing ones will be studied.
                This is relevant when only the statistical analysis wants to be studied or if some attributes of
                some operations were changed for which only those need to be analysed.
            - Number of runs:
                If this is higher than 1, for the same timeseries the O&M plan (log_event file) is produced as many times as the
                number of runs, associated costs are calculated and then avaraged.
            - Overwrite the previous directory:
                If a previous directory is used instead of creating a new out_dir copying all relevant files,
                that same previous directory can be used and updated with the new results.
            - Use a previous logevents_file:
                To avoid new randomness the path to an existing log_event file can be provided. If a path is provided, the number
                of runs is set automatically to 1.
            - Use a previous failureevent_file:
                To avoid new randomness of failure generation the path to an existing failure file can be provided. If a path is provided, the number
                of runs is set automatically to 1.

        Attributes:
            previous_run_dir (:obj:`dict`): Path to a previous run directory
                to be considered. Its value is ``None`` if not defined.
                **keys**: *value*: :obj:`str` ; *units*: :obj:`str`.
            number_runs (:obj:`int`): Number of times running for the same
                statistical analysis. Its values is ``1`` if not defined.
                **keys**: *value*: :obj:`int` ; *units*: :obj:`str`.
            overwrite_previous (:obj:`dict`): True if results want to be
                saved in the previous run path.
                **keys**: *value*: :obj:`bool` ; *units*: :obj:`str`.
            consider_tseries (:obj:`dict`): Path to a previous TimeSeries
                to be considered. Its value is ``None`` if not defined.
                **keys**: *value*: :obj:`bool` ; *units*: :obj:`str`.
            shift_doube (:obj:`bool`): If True the timeseries analysis is not
                constrained to a shift duration for scheduling the operations.
                **keys**: *value*: :obj:`bool ; *units*: :obj:`bool`.
            logevents_file (:obj:`dict`): Path to a log_events.csv file.
                Its value is ``None`` if not defined.
                **keys**: *value*: :obj:`str` ; *units*: :obj:`str`.
            failureevent_file (:obj:`dict`): Path to a failure_events.csv file.
                Its value is ``None`` if not defined.
                **keys**: *value*: :obj:`str` ; *units*: :obj:`str`.

        Note:
            When the class is initialized :func:`_check_attributes` is run.

        Example:
            >>> args = {
            >>>         "previous_run_dir": <path/to/directory>,
            >>>         "number_runs" : 1,
            >>>         "overwrite_runs": True,
            >>>         "consider_tseries": True,
            >>>         "shift_double": False,
            >>>         "logevents_file": <path/to/directory>
            >>>         "failureevent_file": <path/to/directory>
            >>> }
            >>> inputs = Inputs.General(**args)
            >>> logging.info('Path for the previous run directory: %s.' % inputs.previous_run_dir["value"])
        """

        def __init__(self, **kwargs):
            """Initializes :class:`Inputs.General`.

            Args:
                **kwargs: Arbitrary keyword arguments.

            Keyword Args:
                previous_run_dir (:obj:`str`,*optional*): Path to a previous run directory
                    to be considered. Defaults to ``None``.
                number_runs (:obj:`int`,*optional*): Number of times running for the same
                    statistical analysis. Its values is ``1`` if not defined.
                overwrite_previous (:obj:`dict`,*optional*): True if results want to be
                    saved in the previous run path. Defaults to ``None``.
                consider_tseries (:obj:`bool`,*optional*): Consider the TimeSeries
                    from the "previous_run_dir" directory.
                shift_double (;obj;`bool`,*optional*): If True the timeseries analysis is not
                    constrained to a shift duration for scheduling the operations.
                logevents_file (:obj:`str`,*optional*): Path to a log_events.csv file.
                    Default to ``None``.
                failureevent_file (:obj:`str`,*optional*): Path to a failureevent_file.csv file.
                    Default to ``None``.
            """
            self.out_dir = kwargs.get('out_dir', None)
            self.inputs = {}

            # Default values
            self.inputs["number_runs"] = {"value": 1, "units": None}
            self.inputs["overwrite_previous"] = {"value": None, "units": None}
            self.inputs["consider double shifts"] = {"value" : False, "units": None}
            self.inputs["logevents_file"] = {"value": None, "units": None}
            self.inputs["failureevent_file"] = {"value": None, "units": None}

            file_path = kwargs.get('file_inputs', None)
            if file_path is not None:
                # Gets inputs from a yaml file
                f_yaml = open(os.path.join(file_path), 'r')
                yaml = YAML(typ='safe')
                inputs_yaml = yaml.load(f_yaml)
                f_yaml.close()

                # Verify inputs in inputs_yaml and organize them in dictionaries
                for key, values in inputs_yaml.items():
                    name = key.lower()
                    value = values['value']
                    try:
                        if mt.isnan(float(value)) is True:
                            continue
                    except TypeError: pass
                    except ValueError: pass

                    if 'previous' in name and ('path' in name or 'dir' in name):
                        self.inputs["previous run dir"] = {
                                "value": str(value),
                                "units": None
                        }
                    elif ('consider' in name and ('tseries' in name or ('time' in name and 'series' in name))):
                        self.inputs["consider tseries"] = {
                                "value": bool(value),
                                "units": None
                        }
                    elif ('number' in name and 'runs' in name):
                        self.inputs["number_runs"] = {
                                "value": int(value),
                                "units": None
                        }
                    elif 'overwrite' in name:
                        self.inputs["overwrite"] = {
                                "value": bool(value),
                                "units": None
                        }
                    elif ('double' in name and 'shift' in name):
                        self.inputs["consider double shifts"] = {
                                "value": bool(value),
                                "units": None
                        }
                    elif ('log' in name and 'file' in name):
                        self.inputs["logevents file"] = {
                                "value": str(value),
                                "units": None
                        }
                    elif ('fail' in name and 'file' in name):
                        self.inputs["failureevent file"] = {
                                "value": str(value),
                                "units": None
                        }
                    else:
                        logging.warning('Inputs.General: input "%s" not recognized. Ignored.' % key)
                logging.info('Inputs.General: inputs read from a YAML file: "%s".' % file_path)

            # If a yaml file is not provided, gets inputs from **kwargs
            else:
                for key, value in kwargs.items():
                    if key.lower() == 'previous_run_dir':
                        self.inputs["previous run dir"] = {
                                "value": str(value),
                                "units": None
                        }
                    elif key.lower() == 'consider_tseries':
                        self.inputs["consider tseries"] = {
                                "value": bool(value),
                                "units": None
                        }
                    elif key.lower() == 'number_runs':
                        self.inputs["number_runs"] = {
                                "value": int(bool),
                                "units": None
                        }
                    elif key.lower() == 'overwrite_previous':
                        self.inputs["overwrite"] = {
                                "value": bool(value),
                                "units": None
                        }
                    elif key.lower() == 'shift_double':
                        self.inputs["consider double shifts"] = {
                                "value": bool(value),
                                "units": None
                        }
                    elif key.lower() == 'logevents_file':
                        self.inputs["logevents file"] = {
                                "value": str(value),
                                "units": None
                        }
                    elif key.lower() == 'failureevent_file':
                        self.inputs["failureevent file"] = {
                                "value": str(value),
                                "units": None
                        }
                    else:
                        logging.warning('Inputs.General: input "%s" not recognized. Ignored.' % key)
                logging.info('Inputs.General: inputs read from arguments.')

            # Set values inside the inputs dict as direct attributes
            # from the Inputs class
            self.previous_run_dir = self.inputs.get('previous run dir')
            self.consider_tseries = self.inputs.get('consider tseries')
            self.number_runs = self.inputs.get('number_runs')
            self.overwrite_previous = self.inputs.get('overwrite')
            self.shift_double = self.inputs.get('consider double shifts')
            self.logevents_file = self.inputs.get('logevents file')
            self.failureevent_file = self.inputs.get('failureevent file')

            self._check_attributes()

            # Save inputs as a YAML file
            inputs_to_yaml(self, self.out_dir, 'inputs_gen')

            base_folder = os.path.join(self.out_dir, 'base_files')
            # Copy files from one directory to other
            if self.previous_run_dir is not None:
                # Copy input files from source folder to destination folder
                destination_folder = self.out_dir
                source_folder = self.previous_run_dir["value"]
                files = [
                        'wtg.yaml',
                        'wec.yaml',
                        'pv.yaml'
                ]
                for file_name in files:
                    source = os.path.join(source_folder, file_name)
                    destination = os.path.join(destination_folder, file_name)
                    try:
                        shutil.copy(source, destination)
                        logging.info('Inputs.General: "%s" file copied from "%s".' % (file_name, source))
                        os.remove(os.path.join(base_folder, file_name))
                        _i = 'Inputs.General: "%s" file removed ' % file_name
                        _i += 'from base folder "%s".' % base_folder
                        logging.info(_i)
                    except FileNotFoundError:
                        logging.warning('Inputs.General: "%s" file not copied from "%s".' % (file_name, source))

            if self.consider_tseries is not None and self.consider_tseries["value"] is True:
                # Copy input files from source folder to destination folder
                destination_folder = self.out_dir
                source_folder = self.previous_run_dir["value"]
                files = [
                        'inputs_tseries.yaml',
                        'timeseries.csv'
                ] + [f'timeseries_{i}.csv' for i in range(1, 10)]
                for file_name in files:
                    source = os.path.join(source_folder, file_name)
                    destination = os.path.join(destination_folder, file_name)
                    try:
                        shutil.copy(source, destination)
                        os.remove(os.path.join(base_folder, file_name))
                        _i = 'Inputs.General: "%s" file removed ' % file_name
                        _i += 'from base folder "%s".' % base_folder
                        logging.info(_i)
                        logging.info('Inputs.General: "%s" file copied from "%s".' % (file_name, source))
                    except FileNotFoundError:
                        if file_name not in [f'timeseries_{i}.csv' for i in range(1, 10)]:
                            logging.warning('Inputs.General: "%s" file not copied from "%s".' % (file_name, source))

        def _check_attributes(self):
            """
            This method validates the attributes of the `Inputs.General` class to ensure they
            have valid values and fall within specified ranges.

            Raises errors if any attribute is outside the specified range.
            """
            if self.out_dir is None:
                _e = '"out_dir" must be defined.'
                logging.error('Inputs.General: ' + _e)
                raise AttributeError(_e)
            if (
                    self.previous_run_dir is not None and
                    not os.path.exists(self.previous_run_dir["value"])
            ):
                _e = f'Previous run directory {self.previous_run_dir["value"]} does not exist.'
                logging.error('Inputs.General: ' + _e)
                raise FileNotFoundError(_e)
            if (
                    self.previous_run_dir is None and
                    self.consider_tseries is not None and
                    self.consider_tseries["value"] is True
            ):
                _e = 'If "Previous Timeseries is to be used, you must define "Previous run dir"'
                logging.error('Inputs.General: ' + _e)
                raise AttributeError(_e)
            if (
                    self.consider_tseries is not None and
                    self.consider_tseries["value"] is True and
                    not os.path.exists(os.path.join(self.previous_run_dir["value"], 'timeseries.csv'))
            ):
                _e = 'Previous TimeSeries file does not exist.'
                logging.error('Inputs.General: ' + _e)
                raise FileNotFoundError(_e)
            if (
                    self.overwrite_previous is True and
                    self.previous_run_dir is not None
            ):
                _e = 'Not possible to overwrite because previous run not provided'
                logging.error('Inputs.General: ' + _e)

            logging.debug('Inputs.General: attributes within ranges and valid.')


        def get_inputs(self):
            """Prints :class:`Inputs.General` to the command line."""
            for input, value in self.inputs.items():
                logging.info('%s - value: %s ; units: %s' % (input, value["value"], value["units"]))


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
            file_metocean (:obj:`dict`): Path location of the metocean date timeseries.
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
            merge_vessel (:obj:`dict`): Vessel type that can be merged in corrective operation
                **keys**: *value*: :obj:`str` ; *units*: :obj:`str`.
            file_inputs (:obj:`str`): Path for the file with all previous mandatory inputs.
                Its value is ``None`` if not defined.
            time_between_devices_dict (:obj:`dict`): Time between device per each tech
            file_metocean_tow_location (:obj:`dict`): Dictionary of X Path location of the metocean date timeseries X  file between site and port.
                **keys**: dict(X :obj:`int`: *value*: :obj:`str` ; *units*: :obj:`str`.)
            file_metocean_tow_number (:obj:`dict`): Path location of the metocean date timeseries.
                **keys**: *value*: :obj:`int` ; *units*: :obj:`str`.

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
                file_metocean (:obj:`str`): Path location of the metocean date timeseries.
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
                merge_vessel (:obj:`str`,*optional*): Vessel type that can be merged in corrective operation.
                file_inputs (:obj:`str`,*optional*): Path for the file with all previous mandatory inputs. Defaults to ``None``.
                file_metocean_tow_location (:obj:`dict`): Dictionary of Path location of the X metocean date timeseries from site to port.
                file_metocean_tow_number (:obj:`int`): Number of Path location of the X metocean date timeseries from site to port.


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
            self.inputs["metocean file tow location"] = {}

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

                    elif 'metocean' in name and 'file' in name and 'tow' not in name:
                        self.inputs["metocean file location"] = {"value": value, "units": None}

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
                        self.inputs["merge vessel"] = {"value": str(value), "units": str(units)}

                    elif 'metocean' in name and 'file' in name and 'tow' in name and 'number' in name:
                        self.inputs["metocean file tow number"] = {"value": int(value), "units": None}

                    elif 'metocean' in name and 'file' in name and 'tow' in name and 'number' not in name:
                        if value:
                            key_n = name[-1]
                            self.inputs["metocean file tow location"][int(key_n)] = {"value": value, "units": None}
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
                                "value": str(value).lower(),
                                "units": None
                        }
                    elif key.lower() == 'out_dir':
                        pass
                    elif key.lower().startswith('file_metocean_tow_location'):
                        if value:
                            key_n = key[-1]
                            self.inputs["metocean file tow location"][int(key_n)] = {"value": value, "units": None}
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
            self.file_metocean_tow_number = self.inputs.get('metocean file tow number')
            if self.inputs.get('metocean file tow location'):
                self.file_metocean_tow_location = self.inputs.get('metocean file tow location')
            else:
                self.inputs.pop('metocean file tow location')
            self.scenario = 0
            self.time_between_devices_dict = {
                'opv': self.time_between_devices_pv["value"],
                'ofw': self.time_between_devices_wt["value"],
                'owc': self.time_between_devices_wec["value"]
            }

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
            if (
                    self.montecarlo_percent is not None and
                    (
                            self.montecarlo_percent["value"] <= 0 or
                        self.montecarlo_percent["value"] > 1
                    )
            ):
                raise ValueError('"Timeseries analysed percentage (montecarlo)" must be between 0 and 1')
            if self.length_export["value"] < 0:
                raise ValueError('"Length of export cable" must not be negative')
            if self.failure_scenario["value"] < 0:
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
                else:
                    raise ValueError('"Metocean file path tow" must be defined if "Metocean tow file number" is defined')
            if getattr(self, "file_metocean_tow_location", None) and self.file_metocean_tow_number["value"] == 0:
                raise ValueError('"Metocean tow file number" must be defined if ""Metocean file path tow"" are defined')
            logging.debug('Inputs.TimeSeries: attributes within ranges and valid.')

        @classmethod
        def from_yaml(cls, dir: str, name: str):
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
            }

            number_tow_file = input_yaml["metocean file tow number"]["value"]
            if number_tow_file > 0:
                for i in range(1, number_tow_file + 1):
                    input_args[f"file_metocean_tow_location_{i}"] = input_yaml[f"metocean file tow location {i}"]["value"]


            input_args = {k: v for k, v in input_args.items() if v is not None}

            inputs = cls(**input_args)

            logging.info('Inputs.TimeSeries: inputs recycled from "%s"', input_file_path)

            return inputs


        @classmethod
        def from_run_dir(cls, run_dir, file_inputs):
            """
            Build a TimeSeries instance from a run directory.

            - If 'inputs_tseries.yaml' exists under run_dir, reuse it with from_yaml().
            - Otherwise, create a new instance from the provided file_inputs.

            Args:
                run_dir (str): Path to the simulation run directory.
                file_inputs (str): Path to the TimeSeries YAML file to use if not already present.

            Returns:
                TimeSeries: A fully constructed instance.
            """
            if check_file_exists and check_file_exists(run_dir, file_name="inputs_tseries.yaml"):
                return cls.from_yaml(dir=run_dir, name="inputs_tseries")
            return cls(file_inputs=file_inputs, out_dir=run_dir)


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


    class Statistical():
        """Project inputs related with the Statistical analysis.
        Project :class:`Inputs.Statistical` can be defined either with
        a YAML file or one-by-one. If `file_inputs` parameters is given,
        the other parameters will not be considered.

        Note:
            last_day_operation:
                When assessing the lifetime costs, the statistical monthly durations of the operations are used
                (output of the statistical analysis module). Setting the "last_day_operation" potentially avoids
                using a monthly durations for an event that is considered to be happening towards the end of the months
                (where the statistical representation is less representative). 15 is suggested.
            failure_ratio:
                The overall failure rate of the farm(s) can be assumed to follow a bath tub in the overall lifetime
                of the project (in years). For this the "failure_ratio" expresses the ratio between the number of failures
                happening in the "period_infant_mortality" years + "period_wear_out" years, and the number of failures
                happening in the constant section of the  bath tub (corresponding to the lifetime of the project minus the
                "period_infant_mortality" and "period_wear_out").

        Attributes:
            lifetime (:obj:`dict`): Project lifetime, in years.
                **keys**: *value*: :obj:`int` ; *units*: :obj:`str`.
            start_year (:obj:`int`): Start year of the project.
                **keys**: *value*: :obj:`int` ; *units*: :obj:`int`
            start_month (:obj:`int`): Start month of the project.
                **keys**: *value*: :obj:`int` ; *units*: :obj:`int`
            last_day_operation (:obj:`int`): Last day of the month for scheduling an operation.
                **keys**: *value*: :obj:`int` ; *units*: :obj:`int`
            percentile_main (:obj:`list`): Main percentile to perform a statistical analysis with. Its value is ``[50]`` if not defined.
                **keys**: *value*: :obj:`list` ; *units*: :obj:`str`
            percentiles (:obj:`list`): List of percentiles to perform a statistical analysis with. Its value is ``[50]`` if not defined.
                **keys**: *value*: :obj:`list` ; *units*: :obj:`str`
            period_infant_mortality (:obj:`int`): Number of years in the begining of the project with a higher probability of failure. Its value is ``0`` if not defined.
                **keys**: *value*: :obj:`int` ; *units*: :obj:`str`
            period_wear_out (:obj:`int`): Number of years in the end of the project with a higher probability of failure. Its value is ``0`` if not defined.
                **keys**: *value*: :obj:`int` ; *units*: :obj:`str`
            failure_ratio (:obj:`float`): Failure ratio for the above periods. Its value is ``None`` if not defined.
                **keys**: *value*: :obj:`float` ; *units*: :obj:`str`
            failure_ratio_sensitivity (:obj:`float`): Failure ratio sentitivity factor. Its value is ``1`` if not defined.
                **keys**: *value*: :obj:`float` ; *units*: :obj:`str`
            file_inputs (:obj:`str`): Path for the file with all previous mandatory inputs. Its value is ``None`` if not defined.

        Note:
            When the class is initialized :func:`_check_attributes` is run.

        Example:
            >>> args = {
            >>>         "project_lifetime": 20,
            >>>         "start_year": 2023,
            >>>         "start_month": 7,
            >>>         "percentile_main": 50,
            >>>         "percentile_1": 75,
            >>>         "last_day_operation": 15,
            >>>         "period_infant_mortality": 2,
            >>>         "period_wear_out": 3,
            >>>         "failure_ratio": 2.5
            >>> }
            >>> inputs = Inputs.Statistical(**args)
            >>> logging.info('The project start year is %d' % \
            >>>         (inputs.start_year["value"]))
        """

        def __init__(self, **kwargs):
            """Initializes :class:`Inputs.Statistical`.

            Args:
                **kwargs: Arbitrary keyword arguments.

            Keyword Args:
                project_lifetime (:obj:`int`): Project lifetime, in years.
                start_year (:obj:`int`): Start year of the project.
                start_month (:obj:`int`): Start month of the project.
                percentile_main (:obj:`int`): Main percentile for the statistical analysis.
                last_day_operation (:obj:`int`): Last day for scheduling operation.
                percentile_1 (:obj:`int`,*optional*): First optional percentile for the statistical analysis. Defaults to ``None``.
                percentile_2 (:obj:`int`,,*optional*): Second optional percentile for the statistical analysis. Defaults to ``None``.
                period_infant_mortality (:obj:`int`,*optional*): Number of years in the begining of the project with a higher
                    probability of failure. Defaults to ``0``.
                period_wear_out (:obj:`int`,*optional*): Number of years in the end of the project with a higher probability of
                    failure. Defaults to ``0``.
                failure_ratio (:obj:`float`,*optional*): Failure ratio for the above periods. Defaults to ``None``.
                failure_ratio_sensitivity (:obj:`float`, *optional*): Failure ratio sentitivity factor. Default to ``1``
                file_inputs (:obj:`str`,*optional*): Path for the file with all previous mandatory inputs. Defaults to ``None``.

            Raises:
                PermissionError: if the inputs YAML file is open with other software.
            """
            self.inputs = {}

            # Default values
            self.inputs["percentile main"] = {"value": 50, "units" : None}
            self.inputs["percentiles"] = {"value": [], "units" : None}
            self.inputs["period infant mortality"] = {"value": 0, "units" : 'years'}
            self.inputs["period wear out"] = {"value": 0, "units" : 'years'}
            self.inputs["failure ratio"]  = {"value": 0, "units" : None}
            self.inputs["failure ratio sensitivity"]  = {"value": 1, "units" : None}

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
                    except ValueError:
                        pass
                    except TypeError:
                        pass

                    units = str(values['units'])

                    if 'lifetime' in name:
                        if units.lower() != 'years':
                            raise NameError('Units "%s" not recognized for Project Lifetime input.' % units)
                        self.inputs["lifetime"] = {"value": int(value), "units": str(units)}

                    elif 'start' in name and 'year' in name:
                        self.inputs['start year'] = {"value": int(value), "units": None}
                    elif 'start' in name and 'month' in name:
                        self.inputs['start month'] = {"value": int(value), "units": None}

                    elif 'last' in name and 'day ' in name and 'operation' in name:
                        self.inputs['last day operation'] = {"value": int(value), "units": None}

                    elif 'percentile' in name and 'main' in name:
                        self.inputs['percentile main'] = {"value": int(value), "units": None}
                        self.inputs['percentiles']["value"].append(int(value))
                        self.inputs['percentiles']["value"].sort()
                    elif 'percentiles' in name:
                        self.inputs['percentiles'] = {"value": list(value), "units": None}

                    elif 'infant' in name and 'mortality' in name:
                        if units.lower() != 'years':
                            raise NameError('Units "%s" not recognized for Period of Infant Mortality input.' % units)
                        if pd.isna(value) or value == 0:
                            self.inputs['period infant mortality'] = {"value": 0, "units": units}
                        else:
                            self.inputs['period infant mortality'] = {"value": int(value), "units": units}
                    elif 'wear' in name and 'out' in name:
                        if units.lower() != 'years':
                            raise NameError('Units "%s" not recognized for Period of Wear Out input.' % units)
                        if pd.isna(value) or value == 0:
                            self.inputs['period wear out'] = {"value": 0, "units": units}
                        else:
                            self.inputs['period wear out'] = {"value": int(value), "units": units}
                    elif 'fail' in name and 'ratio' in name and not 'sensitivity' in name:
                        if pd.isna(value) or value == 0:
                            self.inputs['failure ratio'] = {"value": 0, "units": None}
                        else:
                            self.inputs['failure ratio'] = {"value": float(value), "units": None}
                    elif 'fail' in name and 'ratio' in name and 'sensitivity' in name:
                        if pd.isna(value) or value == 0:
                            self.inputs['failure ratio sensitivity'] = {"value": 1, "units": None}
                        else:
                            self.inputs['failure ratio sensitivity'] = {"value": float(value), "units": None}
                    else:
                        logging.warning('Inputs.Statistical: input "%s" not recognized. Ignored.' % key)
                logging.info('Inputs.Statistical: inputs read from a YAML file: "%s".' % file_path)

            # If a yaml file is not provided, gets inputs from **kwargs
            else:
                for key, value in kwargs.items():
                    if key.lower() == 'project_lifetime':
                        self.inputs["lifetime"] = {
                                "value": int(value),
                                "units": 'years'
                        }
                    elif key.lower() == 'start_year':
                        self.inputs["start year"] = {
                                "value": int(value),
                                "units": None
                        }
                    elif key.lower() == 'start_month':
                        self.inputs["start month"] = {
                                "value": int(value),
                                "units": None
                        }
                    elif key.lower() == 'percentile_main':
                        self.inputs['percentile main'] = {
                                "value": int(value),
                                "units": None
                        }
                        self.inputs["percentiles"]["value"].append(int(value))
                    elif key.lower() == 'percentile_1':
                        self.inputs["percentiles"]["value"].append(int(value))
                    elif key.lower() == 'percentile_2':
                        self.inputs["percentiles"]["value"].append(int(value))
                    elif key.lower() == 'last_day_operation':
                        self.inputs["last day operation"] = {
                                "value": int(value),
                                "units": None
                        }
                    elif key.lower() == 'period_infant_mortality':
                        self.inputs["period infant mortality"] = {
                                "value": int(value),
                                "units": 'years'
                        }
                    elif key.lower() == 'period_wear_out':
                        self.inputs["period wear out"] = {
                                "value": int(value),
                                "units": 'years'
                        }
                    elif key.lower() == 'failure_ratio':
                        self.inputs["failure ratio"] = {
                                "value": float(value),
                                "units": None
                        }
                    elif key.lower() == 'failure_ratio_sensitivity':
                        self.inputs["failure ratio sensitivity"] = {
                                "value": float(value),
                                "units": None
                        }
                    elif key.lower() == 'out_dir':
                        pass
                    else:
                        logging.warning('Inputs.Statistical: input "%s" not recognized. Ignored.' % key)
                logging.info('Inputs.Statistical: inputs read from arguments')

            # Set values inside the inputs dict as direct attributes
            # from the Inputs.Statistical class
            self.lifetime = self.inputs.get('lifetime')
            self.start_year = self.inputs.get('start year')
            self.start_month = self.inputs.get('start month')
            self.last_day_operation = self.inputs.get('last day operation')
            self.percentile_main = self.inputs.get('percentile main')
            self.percentiles = self.inputs.get('percentiles')
            self.percentiles["value"].sort()
            self.period_infant_mortality = self.inputs.get('period infant mortality')
            self.period_wear_out = self.inputs.get('period wear out')
            self.failure_ratio = self.inputs.get('failure ratio')
            self.failure_ratio_sensitivity = self.inputs.get('failure ratio sensitivity')

            self._check_attributes()

            # Save inputs as a YAML file
            out_dir = kwargs.get('out_dir')
            if out_dir is not None:
                inputs_to_yaml(self, out_dir, 'inputs_stats')


        def _check_attributes(self):
            """
            This method validates the attributes of the `Inputs.Statistical` class to ensure they
            have valid values and fall within specified ranges.

            Raises errors if any attribute is outside the specified range.
            """
            if self.lifetime is None:
                raise ValueError('"Project lifetime" must be defined')
            if self.start_year is None:
                raise ValueError('"Start year of the project" must be defined')
            if self.start_month is None:
                raise ValueError('"Start month of the project" must be defined')
            if self.last_day_operation is None:
                raise ValueError('"Last day for scheduling an operation" must be defined')

            if self.lifetime["value"] < 1:
                raise ValueError('"Project lifetime" must be greater than 0')
            if self.start_month["value"] < 1:
                raise ValueError('"Start month" must be higher than 1')
            if self.start_month["value"] > 12:
                raise ValueError('"Start month" must be lower than 12')
            for percent in self.percentiles["value"]:
                if percent <= 0 or percent >= 100:
                    raise ValueError('Percentiles must be greater than 0 and lower than 100')
            if self.last_day_operation is not None and self.last_day_operation["value"] < 1:
                raise ValueError("Min value is the first day of the month")
            if self.last_day_operation is not None and self.last_day_operation["value"] > 31:
                raise ValueError("Max value is the last day of the month")
            if self.period_infant_mortality["value"] < 0:
                raise ValueError('"Period of infant mortality" must not be negative')
            if self.period_wear_out["value"] < 0:
                raise ValueError('"Period of wear out" must not be negative')
            if self.failure_ratio["value"] < 0:
                raise ValueError('"Failure ratio" must be greater than 0')
            if self.failure_ratio_sensitivity["value"] <= 0:
                raise ValueError('"Failure ratio sensitivity" must be greater than 0')
            if self.failure_ratio["value"] !=0 and (
                    self.period_infant_mortality["value"] == 0 and self.period_wear_out["value"] == 0
            ):
                _e = 'If "Failure ratio" is defined, "Period of infant mortality" or '
                _e += '"Period of wear out" must be defined'
                raise ValueError(_e)
            logging.debug('Inputs.Statistical: attributes within ranges and valid.')


        def get_inputs(self):
            """Prints :class:`Inputs.Statistical` to the command line."""
            for input, value in self.inputs.items():
                logging.info('%s - value: %s ; units: %s' % (input, value["value"], value["units"]))


    class Cost():
        """Project inputs related with the Cost analysis. Project :class:`Inputs.Cost`
        can be defined either with a YAML file or one-by-one. If `file_inputs`
        parameter is given, the other parameters will not be considered.

        Note:
            merge:
                If this is True al functions in the "merging_fcn" are enabled. Also the attribute
                "time_between_merge" must be defined and corresponds to the number of days between two
                corrective maintenances that we are willing to wait in order to merge them and be performed
                as one offshore interventation.

        Attributes:
            fuel_cost_HFO (:obj:`dict`): Heavy Fuel Oil cost, in euros/ton.
                **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
            fuel_cost_MGO (:obj:`dict`): Marine Gas Oil cost, in euros/ton.
                **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
            fuel_cost_MDO (:obj:`dict`): Marine Diesel Oil cost, in euros/ton.
                **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
            electricity_selling_price (:obj:`dict`): Electricity selling price in euros/Mwh.
                **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
            port_cost_year (:obj:`dict`): Cost of a dedicated port terminal per year.
                **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
            merge (:obj:`dict`): Boolean, if True the log_dates will look for operation to merge.
                **keys**: *value*: :obj:`bool` ; *units*: : obj:``
            time_between_merge (:obj:`dict`): Number of days within which the operation can be merged. Its value is ``None`` if not defined.
            insurance_annual (:obj:`dict`): Cost of Insurance per year.
                **keys**: *value*: :obj:`float` ; *units*: : obj:``
            electricity_price (:obj:`dict`): Electricity selling price.
                **keys**: *value*: :obj:`float` ; *units*: : obj:``
            electricity_price pv (:obj:`dict`): Electricity selling price per pv tech.
                **keys**: *value*: :obj:`float` ; *units*: : obj:``
            electricity_price wt (:obj:`dict`): Electricity selling priceper wt tech.
                **keys**: *value*: :obj:`float` ; *units*: : obj:``
            electricity_price wec (:obj:`dict`): Electricity selling price per wec tech.
                **keys**: *value*: :obj:`float` ; *units*: : obj:``
            technicians_year (:obj:`dict`): Cost of Technicians per year.
                **keys**: *value*: :obj:`float` ; *units*: : obj:``
            file_inputs (:obj:`str`): Path for the file with all previous mandatory inputs.
                Its value is ``None`` if not defined.
            electricity_price_dict (:obj:`dict`): Electricity price per each tech

        Note:
            When the class is initialized :func:`_check_attributes` is run.

        Example:
            >>> args = {
            >>>         "fuel_cost_MDO": 700,
            >>>         "vessel_cost_year": 10000
            >>> }
            >>> inputs = Inputs.Cost(**args)
            >>> logging.info('The yearly cost of a dedicated vessel is %.3f %s.' % \
            >>>         (inputs.vessel_cost_year["value"], inputs.vessel_cost_year["units"]))
        """

        def __init__(self, **kwargs):
            """Initializes :class:`Inputs.Cost`.

            Args:
                **kwargs: Arbitrary keyword arguments.

            Keyword Args:
                electricity_selling_price (:obj:`float`): Electricity selling price in euros/Mwh.
                fuel_cost_HFO (:obj:`float`): Heavy Fuel Oil cost, in euros/ton.
                fuel_cost_MGO (:obj:`float`): Marine Gas Oil cost, in euros/ton.
                fuel_cost_MDO (:obj:`float`): Marine Diesel Oil cost, in euros/ton.
                port_cost_year (:obj:`float`,*optional*): Cost of a dedicated port terminal per year, in euros. Defaults to ``0.0``.
                merge (:obj:`dict`,*optional*): Boolean, if True the log_dates will look for operation to merge. Defaults to ``False``.
                time_between_merge (:obj:`int`,*optional*): Number of days within which the operation can be merged. Defaults to ``None``.
                insurance_annual (:obj:`float`,*optional*): Cost of Insurance per year, in euros. Defaults to ``0.0``.
                electricity_price (:obj:`dict`,*optional*): Dictionary Electricity selling price for each tech, in euros/MWh. Defaults to ``None``.
                technicians_year (:obj:`float`,*optional*): Cost of Technicians per year, in euros. Defaults to ``0.0``.
                file_inputs (:obj:`str`,*optional*): Path for the file with all previous mandatory inputs. Defaults to ``None``.

            Raises:
                NameError: units of :attr:`fuel_cost_hfo` not recognized.
                NameError: units of :attr:`fuel_cost_mgo` not recognized.
                NameError: units of :attr:`fuel_cost_mdo` not recognized.
            """
            self.inputs = {}

            # Default values
            self.inputs["vessel cost year"] = {"value" : 0.0, "units": 'euros'}
            self.inputs["port cost year"] = {"value": 0.0, "units": 'euros'}
            self.inputs["merge"] = {"value": False, "units": ""}
            self.inputs["time between merge"] = {"value": None, "units": 'days'}
            self.inputs["insurance annual"] = {"value": 0.0, "units": 'euros'}
            self.inputs["electricity price"] = {"value": None, "units": 'euros/mwh'}
            self.inputs["electricity price pv"] = {"value": None, "units": 'euros/mwh'}
            self.inputs["electricity price wec"] = {"value": None, "units": 'euros/mwh'}
            self.inputs["electricity price wt"] = {"value": None, "units": 'euros/mwh'}
            self.inputs["technicians year"] = {"value": 0.0, "units": 'euros'}

            file_path = kwargs.get('file_inputs', None)
            if file_path is not None:
                # Gets inputs from a yaml file
                f_yaml = open(os.path.join(file_path), 'r')
                yaml = YAML(typ='safe')
                inputs_yaml = yaml.load(f_yaml)
                f_yaml.close()

                # Verify inputs in inputs_yaml and organize them in dictionaries
                for key, values in inputs_yaml.items():
                    name = key.lower()
                    value = values['value']
                    try:
                        if mt.isnan(float(value)) is True:
                            continue
                    except ValueError:
                        pass

                    units = str(values['units'])

                    if 'fuel' in name:
                        if (
                                units.lower() == 'euros/ton' or
                                units.lower() == 'euro/ton' or
                                units.lower() == 'euros per ton' or
                                units.lower() == 'euro per ton'
                        ):
                            units = 'euros/ton'
                        else:
                            raise NameError('Units "%s" not recognized for fuel cost inputs.' % units)
                        if 'hfo' in name:
                            self.inputs["fuel cost hfo"] = {"value": float(value), "units": str(units)}
                        elif 'mgo' in name:
                            self.inputs["fuel cost mgo"] = {"value": float(value), "units": str(units)}
                        elif 'mdo' in name:
                            self.inputs["fuel cost mdo"] = {"value": float(value), "units": str(units)}
                        else:
                            logging.warning('Inputs.Cost: fuel type "%s" not recognized. Ignored.' % key)
                    elif ('port' in name or 'terminal' in name) and ('annual' in name or 'year' in name):
                        if units.lower() != 'euros':
                            raise NameError('Units "%s" not recognized for a Dedicated Port Terminal annual cost input.' % units)
                        self.inputs["port cost year"] = {"value": float(value), "units": str(units)}
                    elif 'time' in name and 'between' in name and 'merge' in name:
                        if pd.isna(value) is True:
                            self.inputs["time between merge"] = {"value": None, "units": str(units)}
                        else:
                            self.inputs["time between merge"] = {"value": int(value), "units": str(units)}
                    elif 'merge' in name:
                        self.inputs["merge"] = {"value": bool(value), "units": None}
                    elif 'insurance' in name and ('annual' in name or 'year' in name):
                        if units.lower() != 'euros':
                            raise NameError('Units "%s" not recognized for a Insurance annual cost input.' % units)
                        self.inputs["insurance annual"] = {"value": float(value), "units": str(units)}
                    elif 'electricity' in name and 'price' in name:
                        if units.lower() != 'euros/mwh':
                            raise NameError('Units "%s" not recognized for the Electricity Selling Price input.' % units)
                        if name == 'electricity price':
                            self.inputs["electricity price"] = {"value": float(value), "units": str(units)}
                        elif 'pv' in name:
                            self.inputs["electricity price pv"] = {"value": float(value), "units": str(units)}
                        elif 'wec' in name:
                            self.inputs["electricity price wec"] = {"value": float(value), "units": str(units)}
                        elif 'wt' in name:
                            self.inputs["electricity price wt"] = {"value": float(value), "units": str(units)}
                        else:
                            raise NameError('Tech "%s" not recognized for the Electricity Selling Price input.' % name)
                    elif 'technicians' in name and ('annual' in name or 'year' in name):
                        if units.lower() != 'euros':
                            raise NameError('Units "%s" not recognized for a Technicians annual cost input.' % units)
                        self.inputs["technicians year"] = {"value": float(value), "units": str(units)}
                    else:
                        logging.warning('Inputs.Cost: input "%s" not recognized. Ignored.' % key)
                logging.info('Inputs.Cost: inputs read from a YAML file: "%s".' % file_path)

            # If a yaml file is not provided, gets inputs from **kwargs
            else:
                for key, value in kwargs.items():
                    if key.lower() == 'fuel_cost_hfo':
                        self.inputs["fuel cost hfo"] = {
                                "value": float(value),
                                "units": 'euros/ton'
                        }
                    elif key.lower() == 'fuel_cost_mgo':
                        self.inputs["fuel cost mgo"] = {
                                "value": float(value),
                                "units": 'euros/ton'
                        }
                    elif key.lower() == 'fuel_cost_mdo':
                        self.inputs["fuel cost mdo"] = {
                                "value": float(value),
                                "units": 'euros/ton'
                        }
                    elif key.lower() == 'port_cost_year':
                        self.inputs["port cost year"] = {
                                "value": float(value),
                                "units": 'euros'
                        }
                    elif key.lower() == 'merge':
                        self.inputs["merge"] = {
                                "value": bool(value),
                                "units": None
                        }
                    elif key.lower() == 'time_between_merge':
                        self.inputs["time between merge"] = {
                                "value": int(value),
                                "units": "day"
                        }
                    elif key.lower() == 'insurance_annual':
                        self.inputs["insurance annual"] = {
                                "value": float(value),
                                "units": "euros"
                        }
                    elif 'electricity_price' in key.lower():
                        if key.lower() == "electricity_price":
                            self.inputs["electricity price"] = {
                                    "value": float(value),
                                    "units": "euros/mwh"
                                }
                        elif 'pv' in key.lower():
                            self.inputs["electricity price pv"] = {
                                    "value": float(value),
                                    "units": "euros/mwh"
                                }
                        elif 'wec' in key.lower():
                            self.inputs["electricity price wec"] = {
                                    "value": float(value),
                                    "units": "euros/mwh"
                                }
                        elif 'wt' in key.lower():
                            self.inputs["electricity price wt"] = {
                                    "value": float(value),
                                    "units": "euros/mwh"
                                }
                    elif key.lower() == 'technicians_year':
                        self.inputs["technicians year"] = {
                                "value": float(value),
                                "units": "euros"
                        }
                    elif key.lower() == 'out_dir':
                        pass
                    else:
                        logging.warning('Inputs.Cost: input "%s" not recognized. Ignored.' % key)
                logging.info('Inputs.Cost: inputs read from arguments')

            # Set values inside the inputs dict as direct attributes
            # from the Inputs class
            self.fuel_cost_hfo = self.inputs.get('fuel cost hfo')
            self.fuel_cost_mdo = self.inputs.get('fuel cost mdo')
            self.fuel_cost_mgo = self.inputs.get('fuel cost mgo')
            self.insurance_cost_year = self.inputs.get('insurance annual')
            self.port_cost_year = self.inputs.get('port cost year')
            self.merge = self.inputs.get("merge")
            self.time_between_merge = self.inputs.get("time between merge")
            self.electricity_price = self.inputs.get('electricity price')
            self.electricity_price_pv = self.inputs.get('electricity price pv')
            self.electricity_price_wec = self.inputs.get('electricity price wec')
            self.electricity_price_wt = self.inputs.get('electricity price wt')
            self.technicians_year = self.inputs.get('technicians year')

            if any([
                self.electricity_price_pv["value"] is not None,
                self.electricity_price_wt["value"] is not None,
                self.electricity_price_wec["value"] is not None
            ]):
                self.electricity_price_dict = {
                    'pv': self.electricity_price_pv["value"],
                    'wt': self.electricity_price_wt["value"],
                    'wec': self.electricity_price_wec["value"]
                }
            else:
                self.electricity_price_dict = {
                    'pv': self.electricity_price["value"],
                    'wt': self.electricity_price["value"],
                    'wec': self.electricity_price["value"]
                }


            self._check_attributes()

            # Save inputs as a YAML file
            out_dir = kwargs.get('out_dir')
            if out_dir is not None:
                inputs_to_yaml(self, out_dir, 'inputs_cost')


        def _check_attributes(self):
            """
            This method validates the attributes of the `Inputs.Cost` class to ensure they
            have valid values and fall within specified ranges.

            Raises errors if any attribute is outside the specified range.
            """
            if self.fuel_cost_hfo is not None and self.fuel_cost_hfo["value"] < 0:
                raise ValueError('"Fuel cost HFO" cannot be negative')
            if self.fuel_cost_mdo is not None and self.fuel_cost_mdo["value"] < 0:
                raise ValueError('"Fuel cost MDO" cannot be negative')
            if self.fuel_cost_mgo is not None and self.fuel_cost_mgo["value"] < 0:
                raise ValueError('"Fuel cost MGO" cannot be negative')
            if self.port_cost_year is not None and self.port_cost_year["value"] < 0:
                raise ValueError('"Dedicated port terminal annual cost" cannot be negative')
            if self.insurance_cost_year is not None and self.insurance_cost_year["value"] < 0:
                raise ValueError('"Insurance Cost per year" cannot be negative')
            if self.merge is True and self.time_between_merge is None:
                raise ValueError('If "Merge" is True the limit time between operaition must be defined')
            if self.technicians_year is not None and self.technicians_year["value"] < 0:
                raise ValueError('"Technicians Cost per year" cannot be negative')
            if self.electricity_price['value'] is not None and self.electricity_price["value"] < 0:
                raise ValueError('"Electricity Price" cannot be negative')
            if self.electricity_price_pv['value'] is not None and self.electricity_price_pv["value"] < 0:
                raise ValueError('"Electricity Price PV" cannot be negative')
            if self.electricity_price_wt['value'] is not None and self.electricity_price_wt["value"] < 0:
                raise ValueError('"Electricity Price WT" cannot be negative')
            if self.electricity_price_wec['value'] is not None and self.electricity_price_wec["value"] < 0:
                raise ValueError('"Electricity Price WEC" cannot be negative')
            if self.time_between_merge['value'] is not None and self.time_between_merge["value"] < 0:
                raise ValueError('"Time distance between operations to merge" cannot be negative')

            logging.debug('Inputs.Cost: attributes within ranges and valid.')


        def get_inputs(self):
            """Prints :class:`Inputs.Cost` to the command line."""
            for input, value in self.inputs.items():
                logging.info('%s - value: %s ; units: %s' % (input, value["value"], value["units"]))


    def __init__(self, general, stats, cost, tseries):
        self.general = general
        self.stats = stats
        self.cost = cost
        self.tseries = tseries


if __name__ == '__main__':
    logging.info('General inputs from arguments')
    args_gen = {
            "previous_run_dir": os.path.join(os.getcwd(), 'tmp', '<path/to/directory>'),
            "consider_tseries": False,
            "overwrite_previous": False,
            "out_dir": os.path.join(os.getcwd(), 'tmp')
    }
    inputs_gen = Inputs.General(**args_gen)
    inputs_gen.get_inputs()

    logging.info('General inputs from YAML files')
    args_gen = {
            "file_inputs": os.path.join(
                    os.getcwd(),
                    'tests',
                    'test_files',
                    'inputs',
                    'inputs_gen.yaml'
            ),
            "out_dir": os.path.join(os.getcwd(), 'tmp')
    }
    inputs_gen = Inputs.General(**args_gen)
    inputs_gen.get_inputs()

    logging.info('TimeSeries inputs from arguments')
    args_tseries = {
            "site_latitude": 41,
            "site_longitude": -9,
            "file_metocean": os.path.join(
                    os.getcwd(),
                    'tests', 'test_files', 'metocean', 'metocean_dummy.csv'
            ),
            "metocean_ws_height": 10,
            "surface_roughness": 0.0002,
            "dist_port": 50,
            "time_between_devices_pv": 0.01,
            "time_between_devices_wt": 0.1,
            "time_between_devices_wec": 0.1,
            "max_wait": 8,
            "montecarlo_percentage": 0.3
    }
    inputs_tseries = Inputs.TimeSeries(**args_tseries)
    inputs_tseries.get_inputs()

    logging.info('TimeSeries inputs from YAML files')
    args_tseries = {
            "file_inputs": os.path.join(
                    os.getcwd(),
                    'tests',
                    'test_files',
                    'inputs',
                    'inputs_tseries.yaml'
            )
    }
    inputs_tseries = Inputs.TimeSeries(**args_tseries)
    inputs_tseries.get_inputs()

    logging.info('Statistical inputs from arguments')
    args_stats = {
            "project_lifetime": 20,
            "start_year": 2023,
            "start_month": 7,
            "percentile_main": 50,
            "percentile_1": 75,
            "last_day_operation": 15
    }
    inputs_stats = Inputs.Statistical(**args_stats)
    inputs_stats.get_inputs()

    logging.info('Statistical inputs from YAML files')
    args_stats = {
            "file_inputs": os.path.join(
                    os.getcwd(),
                    'tests',
                    'test_files',
                    'inputs',
                    'inputs_stats.yaml'
            )
    }
    inputs_stats = Inputs.Statistical(**args_stats)
    inputs_stats.get_inputs()

    logging.info('Cost inputs from arguments')
    args_costs = {
            "fuel_cost_MDO": 700,
            "merge" : False,
            "time_between_merge": 30
    }
    inputs_costs = Inputs.Cost(**args_costs)
    inputs_costs.get_inputs()

    logging.info('Cost inputs from YAML files')
    args_costs = {
            "file_inputs": os.path.join(
                    os.getcwd(),
                    'tests',
                    'test_files',
                    'inputs',
                    'inputs_costs.yaml'
            )
    }
    inputs_costs = Inputs.Cost(**args_costs)
    inputs_costs.get_inputs()
