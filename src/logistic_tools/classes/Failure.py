import os
import pandas as pd
import logging
from distutils.util import strtobool
from ruamel.yaml import YAML


class Failure():
    """Failure class.

    Note:
        It reads all failure rates.
        All failures must have a prefix and the followings are recognized:
            - ofw: Offshore Floating Wind
            - owc: Offshore Wave Converter
            - opv: Offshore PhotoVoltaic
            - oce: Offshore Common Events

        Individual failures can follow a bath tub trend.
    
    Attributes:
        id_(:obj:`str`): The unique identifier of the Failure.
        name (:obj:`str`): Failure name.
        n_element (:obj:`int`) : Number of element to refer the failure rate.
        fail_rate (:obj:`float`): The operation failure rate per year per
            element, in failures per year.
        maintenance_strategy (:obj:`str`): When the failure occurs it can
            lead to the following strategies: never repair, specific month,
            immediately.
        level_failure (:obj:`str`): Level at which the failure occurs for
                the graph.
        potential_shutdown (:obj:`bool`): If the failure could lead to potential
            shutdown it should be marked as True.
        operation_triggered (:obj:`str`): Operation that is triggered
            when this failure happens. Its value is ``None`` if not defined.
        preferred_month (:obj:`int`): In case the strategy is to schedule the
            operation in a specific month. Its value is ``None`` if not defined.
        lead_time (:obj:`int`): Defines lead time in h. Its value
            is 0 if not defined.
        parts_cost (:obj:`float`, *optional*): Cost of replacement parts.
                Defaults to :obj:`0.0`.
        bath_tub (:obj:`bool`): True if the failure rate follows a
            bath-tub trend during the lifetime, False if it doesn't. Its value
                is False if not defined.
        fail_variation (:obj:`bool`): True if the failure rate will variate in the 
            sensitivity analysis. Its value is False if not defined.
        perc_shutdown (:obj:`int`): Is the probability that the component shut
            down, or the percentage reduction of power output due to the failure. Use int value between 0 and 100.
        
    
    Note:
        When the class is initialized, :func:`_check_inputs` is run.
    """
    def __init__(
            self,
            id_: str,
            name: str,
            n_element: int,
            fail_rate: float,
            maintenance_strategy: str,
            level_failure: str,
            potential_shutdown: bool,
            operation_triggered: str=None,
            parts_cost: float=0,
            preferred_month: int=None,
            lead_time: int=None,
            bath_tub: bool=None,
            fail_variation: bool = None,
            perc_shutdown: int=100
    ):
        """Initializes :class:`Failure` class.

        Args:
            id_(:obj:`str`): The unique identifier of the Failure.
            name (:obj:`str`): Failure name.
            n_element (:obj:`int`) : Number of element to refer the failure rate.
            fail_rate (:obj:`float`): The operation failure rate per year per
                element.
            maintenance_strategy (:obj:`str`): When the failure occurs it can
                lead to the following strategies: never repair, specific month,
                immediately.
            level_failure (:obj:`str`): Level at which the failure occurs for
                the graph.
            potential_shutdown (:obj:`bool`): If the failure could lead to potential
                shutdown it should be marked as True.
            operation_triggered (:obj:`str`, *optional*): Operation that is
                triggered when this failure happens. Defaults to ``None``.
            parts_cost (:obj:`float`): Cost of replacement parts. Its value is
                :obj:`0.0` if not defided.
            preferred_month (:obj:`int`, *optional*): In case the strategy is
                to schedule the operation in a specific month. Defaults to
                ``None``.
            lead_time (:obj:`int`, *optional*): On the case of part replacement,
                the lead time can be defined. Defaults to ``0``.
            bath_tub (:obj:`bool`, *optional*): True if the failure rate follows a
                bath-tub trend during the lifetime, False if it doesn't. Defaults
                to ``False``.
            fail_variation (:obj:`bool`, *optional*): True if the failure rate will variate in the 
                sensitivity analysis. Defaults to ``False``.
            perc_shutdown_fail (:obj:`int`, *optional*): Is the probability that the component shut
                down, or the percentage reduction of power output due to the failure. Use int value

        Raises:
            ValueError: If the "bath_tub" arguemnt is not a boolean value.
        """
        self.id = str(id_).lower()
        self.name = str(name).lower()
        self.n_element = int(n_element)
        self.fail_rate = float(fail_rate)
        self.maintenance_strategy = str(maintenance_strategy).lower()
        self.level_failure = str(level_failure)
        self.potential_shutdown = bool(potential_shutdown)
        self.operation_triggered = None
        self.preferred_month = None
        self.lead_time = 0
        self.parts_cost = 0
        self.bath_tub = False
        self.fail_variation = False
        self.perc_shutdown = 100

        if operation_triggered is not None:
            self.operation_triggered = str(operation_triggered).lower()
        if preferred_month is not None:
            self.preferred_month = int(preferred_month)
        if lead_time is not None:
            self.lead_time = int(lead_time)
        if bath_tub is not None:
            if bath_tub is True or bath_tub is False:
                self.bath_tub = bath_tub
            elif bath_tub == 1.0:
                self.bath_tub = True
            elif bath_tub == 0.0:
                self.bath_tub = False
            else:
                try:
                    self.bath_tub = bool(strtobool(str(bath_tub)))
                except ValueError:
                    _e = '"Bath Tub" has to be a boolean value.'
                    logging.error('Failure:' + _e)
                    raise ValueError(_e)
        if fail_variation is not None:
            if fail_variation is True or fail_variation is False:
                self.fail_variation = fail_variation
            elif fail_variation == 1.0:
                self.fail_variation = True
            elif fail_variation == 0.0:
                self.fail_variation = False
            else:
                try:
                    self.fail_variation = bool(strtobool(str(fail_variation)))
                except ValueError:
                    _e = '"fail_variation" has to be a boolean value.'
                    logging.error('Failure:' + _e)
                    raise ValueError(_e)
            if isinstance(perc_shutdown, bool):
                self.perc_shutdown = 100 if perc_shutdown else 0
            elif perc_shutdown is not None:
                try:
                    self.perc_shutdown = int(perc_shutdown)
                except ValueError:
                    _e = '"perc_shutdown" has to be a int value.'
                    logging.error('Failure:' + _e)
                    raise ValueError(_e)
        if parts_cost is not None:
            self.parts_cost = float(parts_cost)

        self._check_inputs()

    def _check_inputs(self):
        """
        This method validates the inputs of the `Failure` class to ensure they 
        have valid values and fall within specified ranges.
        
        Raises errors if any attribute is outside the specified range.
        """
        if self.id[0:3] not in ['oce','ofw','owc','opv']:
            raise ValueError('"prefix not recognized"')
        if self.fail_rate < 0:
            _e = '"failure rate" must be positive.'
            logging.error('Failure:' + _e)
            raise ValueError(_e)
        if any([
                self.maintenance_strategy == 'never repair',
                self.maintenance_strategy == 'specific month',
                self.maintenance_strategy == 'immediately'
        ]) is False:
            _e = 'Specified maintenance strategy is not recognized.'
            logging.error('Failure:' + _e)
            raise ValueError(_e)
        if self.maintenance_strategy == 'never repair':
            if self.operation_triggered is not None:
                _e = 'For a "Never repair" strategy, the argument '
                _e += '"operation_triggered" cannot be defined.'
                #logging.error('Failure:' + _e)                         ######
                logging.info('Failure:' + _e)
                #raise ValueError(_e)
            if self.preferred_month is not None:
                _e = 'For a "Never repair" strategy, the argument '
                _e += '"preferred_month" cannot be defined.'
                #logging.error('Failure:' + _e)                         ######
                logging.info('Failure:' + _e)
                #raise ValueError(_e)
        if (self.maintenance_strategy == 'immediately' and
            self.preferred_month is not None):
            _e = 'For an "Immediately" strategy, the argument '
            _e += '"preferred_month" cannot be defined.'
            logging.error('Failure:' + _e)
            raise ValueError(_e)
        # TODO modify this with an automatic list taken by the layout used
        if any([
            self.level_failure == 'exp_cable',
            self.level_failure == 'exp_cable_island',
            self.level_failure == 'dyn_cable-sub',
            self.level_failure == 'array_cable',
            self.level_failure == 'cable_cb',
            self.level_failure == 'cable_transf',
            self.level_failure == 'cable_switch',
            self.level_failure == 'cable_inv',
            self.level_failure == 'string_cable',
            self.level_failure == 'substation',
            self.level_failure == 'mv_transformer',
            self.level_failure == 'circuit_braker',         
            self.level_failure == 'switcher',
            self.level_failure == 'inverter',
            self.level_failure == 'device'
        ]) is False:
            _e = f'level_failure not recognized {self.level_failure}'
            logging.error('Failure:' + _e)
            raise ValueError(_e)
        if self.lead_time < 0:
            _e = '"Lead time" must be greater or equal to 0.'
            logging.error('Failure:' + _e)
            raise ValueError(_e)
        if any([
            self.potential_shutdown == True,
            self.potential_shutdown == False
        ]) is False:
            _e = '"Potential failure" must be a boolean'
            logging.error('Failure:' + _e)
            raise ValueError(_e)
        if self.perc_shutdown < 0 or self.perc_shutdown > 100:
            _e = '"perc_shutdown" must be between 0 and 100.'
            logging.error('Failure:' + _e)
            raise ValueError(_e)
        if self.parts_cost is not None and self.parts_cost < 0:
            raise ValueError('"parts_cost" must not be negative')
        

    def get_failures_from_yaml(file_path: str) -> list:
        """Returns a list of :class:`Failure` based on a YAML file.

        Args:
            file_path (:obj:`str`): YAML file path with failures.
        Raises:
            KeyError: if some of the mandatory keys of the YAML are
                not provided.
        Returns:
            :obj:`list`: :obj:`list` of :class:`Failure`.
        """
        # Gets failures from a YAML file
        f_yaml = open(os.path.join(file_path), 'r')
        yaml = YAML(typ='safe')
        failures_yaml = yaml.load(f_yaml)
        f_yaml.close()
        # All failures keys to lower case
        failures_yaml = [
                {key.lower(): val for key, val in fail.items()}
                for fail in failures_yaml
        ]

        keys_mandatory = [
                'id',
                'name',
                'number_of_element_farm',
                'probability_failure',
                'maintenance_strategy',
                'level_failure'
        ]
        no_mandatory_keys = [
                'op_trigger',
                'preferred_month',
                'lead_time',
                'bath_tub',
                'parts_cost',
                'potential_shutdown'
                'perc_shutdown',
                'fail_variation'
        ]

        failures_list = []
        for failure in failures_yaml:
            if any([
                    key not in failure.keys()
                    for key in keys_mandatory
            ]) is True:
                _e = '"id", "name", "number_of_element_farm", '
                _e += '"probability_failure", "maintenance_strategy" and '
                _e += '"level_failure" are mandatory keys.'
                logging.error('Failure: ' + _e)
                raise KeyError(_e)

            for key in no_mandatory_keys:
                try:
                    failure[key]
                except KeyError:
                    failure[key] = None

            failures_list.append(
                    Failure(
                        id_ = failure["id"],
                        name = failure["name"],
                        n_element = failure["number_of_element_farm"],
                        fail_rate = failure["probability_failure"],
                        maintenance_strategy = failure["maintenance_strategy"],
                        level_failure = failure["level_failure"],
                        potential_shutdown=failure["potential_shutdown"],
                        operation_triggered = failure["op_trigger"],
                        parts_cost=failure["parts_cost"],
                        preferred_month = failure["preferred_month"],
                        lead_time = failure["lead_time"],
                        bath_tub = failure["bath_tub"],
                        fail_variation = failure["fail_variation"],
                        perc_shutdown = failure["perc_shutdown"]
                    )
            )

        logging.info('Failure: failures defined based on file "%s"' % file_path)
        return failures_list


if __name__ == '__main__':
    file_path = os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'failures.yaml')
    failures = Failure.get_failures_from_yaml(file_path)
