import logging
import os
import shutil
import math as mt
from ruamel.yaml import YAML
from oriom.utils.yaml_manager import inputs_to_yaml


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
        logevents_file (:obj:`dict`): Path to a log_events.csv and
            log_events_merged.csv file.
            Its value is ``None`` if not defined.
            **keys**: *value*: :obj:`str` ; *units*: :obj:`str`.
        failureevent_file (:obj:`dict`): Path to a failure_events.csv file.
            Its value is ``None`` if not defined.
            **keys**: *value*: :obj:`str` ; *units*: :obj:`str`.
        powerevent_file (:obj:`dict`): Path to wave_corrective_energy.csv 
            and wave_preventive_energy file.
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
            failureevent_file (:obj:`str`,*optional*): Path to a failure_event_file.csv file.
                Default to ``None``.
            powerevent_file (:obj:`str`,*optional*): Path to a failure_event_file.csv file.
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
        self.inputs["powerevent_file"] = {"value": None, "units": None}

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
                            "value": str(value) if value else None,
                            "units": None
                    }
                elif ('fail' in name and 'file' in name):
                    self.inputs["failureevent file"] = {
                            "value": str(value) if value else None,
                            "units": None
                    }
                elif ('power' in name and 'file' in name):
                    self.inputs["powerevent file"] = {
                            "value": str(value) if value else None,
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
                            "value": str(value) if value else None,
                            "units": None
                    }
                elif key.lower() == 'failureevent_file':
                    self.inputs["failureevent file"] = {
                            "value": str(value) if value else None,
                            "units": None
                    }
                elif key.lower() == 'powerevent_file':
                    self.inputs["powerevent file"] = {
                            "value": str(value) if value else None,
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
        self.powerevent_file = self.inputs.get('powerevent file')

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
        def error_path_reuse(error_file, dependency):
            _e = f'If "{error_file}" is to be used, you must define "{dependency}"'
            logging.error('Inputs.General: ' + _e)
            raise FileNotFoundError(_e)
        
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
            error_path_reuse('Previous Timeseries', "Previous run dir")
        if (
                self.failureevent_file is not None and
                self.failureevent_file["value"] is None and
                self.logevents_file["value"] is not None
        ):
            error_path_reuse('Log_events file', "Failure events file")
        if (
                self.powerevent_file is not None and
                self.powerevent_file["value"] is not None and
                (self.failureevent_file is None or self.failureevent_file["value"] is None or 
                    self.logevents_file is None or self.logevents_file["value"] is None)
        ):
            error_path_reuse('Power events file', 'Log_events file" or "Failure events file')
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