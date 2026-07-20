import logging
import os
import math as mt
import pandas as pd
from ruamel.yaml import YAML
from oriom.utils.yaml_manager import inputs_to_yaml


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
                elif 'fail' in name and 'ratio' in name and 'sensitivity' not in name:
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
