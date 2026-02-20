# Import packages
import pandas as pd
import logging
import os
from ruamel.yaml import YAML
from distutils.util import strtobool


class CorrectiveMinor():
    """
    A class representing a CorrectiveMinor operation with various attributes and methods.

    Note:
        Minor corrective operations only allow for on-site intervention.
        Duration shall always be lower than a shift duration.

    Attributes:

        id (:obj:`str`): The unique identifier of the :class:`CorrectiveMinor`.
        name (:obj:`str`): :class:`CorrectiveMinor` short description.
        duration_net (:obj:`float`): Total net duration of the operation.
        device_shutdown (:obj:`bool`): If the inspection requires to shutdown the device
            while the operation is undergoing.
        level (:obj;`str`): Level for the electrical layout (device, string_cable, array_cable,
            exp_cable or dyn_cable-sub).
        months (:obj:`list`): Months when the operation is preformed.
        technology (:obj:`str`): Type of technology (wtg, wec or pv)
        tech_required (:obj:`int`): Number of technicians required to preform
            the operation.
        tech_cost (:obj:`float`): The daily cost of each technician [€/day]. Its value
            is ``0`` if not defined.
        hs (:obj:`float`): Limit wave height. Its value is ``None`` if there is no limit.
        tp (:obj:`float`): Limit wave period. Its value is ``None`` if there is no limit.
        ws (:obj:`float`): Limit wind speed. Its value is ``None`` if there is no limit.
        ws_hub (:obj:`float`): Limit wind speed at hub height. Its value is ``None`` if there is no limit.
        cs (:obj:`float`): Limit current speed. Its value is ``None`` if there is no limit.
        light (:obj:`bool`, *optional*): If the operation is light. Default to ``False``
        vessel1_id (:obj:`str`): The ID of the main vessel.
        vessel1_qt (:obj:`int`): Number of main vessel.
            Its value is ``1`` if not defined.
        vessel2_id (:obj:`str`): The ID of the auxiliary vessel.
            Its value is ``None`` if not defided.
        vessel2_qt (:obj:`int`): Number of secondary vessel.
            Its value is ``1`` if not defined.
        other_costs (:obj:`float`): Other costs (port, cranes, insurance, etc.).
            Its value is :obj:`0.0` if not defided.
        vessel1 (:class:`~oriom.classes.Vessel.Vessel`): Main vessel
            used in this operation.
        vessel2 (:class:`~oriom.classes.Vessel.Vessel`): Auxiliary
            vessel used in this operation. Its value is ``None`` if not
            defided.
        failures (:class:`~oriom.classes.Failure.Failure`): List of
            :class:`~oriom.classes.Failure.Failure`.
        rov_drone (:class:`~oriom.classes.RovDrone.RovDone`): Rov/Drone
            used in this operation. Its value is ``None`` if not
            defided.
        ts_data (:class:`~oriom.classes.OperationTimeSeriesData.OperationTimeSeriesData`):
            Timeseries data of the operation. Its value is ``None`` if not defided
        double_shift (bool): Boolean to specify if it can hold double shift inspection (day&night)


    Note:
        When the class is initialized, :func:`_check_attributes` is run.
    """
    def __init__(
            self,
            id_: str,
            name: str,
            duration_net: float,
            device_shutdown: bool,
            level: str,
            tech_required: int,
            vessel1_id: str,
            vessel1_qt: int=1,
            tech_cost: float=0,
            rov_drone: str=None,
            tech_wtg: bool=False,
            tech_wec: bool=False,
            tech_pv: bool=False,
            wave_height: float=None,
            wave_period: float=None,
            wind_speed: float=None,
            wind_speed_hub: float=None,
            current_speed: float=None,
            light: bool=False,
            month: int=None,
            vessel2_id: str=None,
            vessel2_qt: int=None,
            other_costs: float=0,
            double_shift: bool=False
    ):
        """
        Initialize the :class:`CorrectiveMinor` with various attributes and parameters.

        Args:
            id_ (:obj:`str`): The unique identifier of the CorrectiveMinor.
            name (:obj:`str`): Short description of the CorrectiveMinor.
            duration_net (:obj:`float`): Total net duration of the operation.
            device_shutdown (:obj:`bool`): If the operation requires to shutdown the device.
            level (:obj;`str`): Level for the electrical layout (device, array_cable, exp_cable, or dyn_cable-sub, string_cable).
            tech_required (:obj:`int`): Number of technicians required to perform the operation.
            vessel1_id (:obj:`str`): The ID of the main vessel.
            vessel1_qt (:obj:`int`): Number of main vessel.
                Defaults to ``1``.
            tech_cost (:obj:`float`,*optional*): The daily cost of each technician [€/day].
                Defaults to ``0``.
            rov_drone (:obj:`str`, *optional*): the ID of the ROV/Drone.
                Defaults to ``None``.
            tech_wtg (:obj:`bool`, *optional*): Operation to a WTG device.
                Defaults to ``None``.
            tech_wec (:obj:`bool`, *optional*): Operation to a WEC device.
                Defaults to ``None``.
            tech_pv (:obj:`bool`, *optional*): Operation to a PV device.
                Defaults to ``None``.
            wave_height (:obj:`float`, *optional*): Limit wave height.
                Defaults to ``None``.
            wave_period (:obj:`float`, *optional*): Limit wave period.
                Defaults to ``None``.
            wind_speed (:obj:`float`, *optional*): Limit wind speed.
                Defaults to ``None``.
            wind_speed_hub (:obj:`float`, *optional*): Limit wind speed at hub height.
            wind_speed_hub: float=None,
                Defaults to ``None``.
            current_speed (:obj:`float`, *optional*): Limit current speed.
                Defaults to ``None``.
            light (:obj:`bool`, *optional*): If the operation is light.
                Default to ``False``
            month (:obj:`int`, *optional*): Month when the operation is preformed.
                Defaults to ``None``.
            vessel2_id (:obj:`str`, *optional*): The ID of the auxiliary vessel.
                Defaults to ``None``.
            vessel2_qt (:obj:`int`): Number of second vessel.
                Defaults to ``1`` if vesse_id not ´´None´´.
            other_costs (:obj:`float`, *optional*): Other costs (port, cranes,
                insurance, etc.). Defaults to :obj:`0.0`.
            double_shift (bool): Boolean to specify if it can hold double shift inspection (day&night)
                Forced to False

        Raises:
            ValueError: if any of :attr:`months` values is not an integer.
            ValueError: if more than one technology is defined.
            ValueError: if :attr:`light` is not a boolean value.
        """
        self.id = str(id_).lower()
        self.name = str(name)
        self.duration_net = float(duration_net)
        self.device_shutdown = bool(device_shutdown)
        self.level = str(level).lower()
        self.tech_required = int(tech_required)

        self.vessel1_id = str(vessel1_id).lower()
        self.vessel1_qt = 1
        self.tech_cost = 0
        self.vessel2_id = None
        self.vessel2_qt = None
        self.other_costs = 0

        self.ts_data = None

        self.hs = None
        self.tp = None
        self.ws = None
        self.ws_hub = None
        self.cs = None
        self.light = None

        self.technology = None
        self.vessel1 = None
        self.vessel2 = None
        self.rov_drone = None

        self.failures = None
        self.double_shift = False

        if month is not None:
            self.months = [int(month)]
        else:
            # If the months are not defined, all months should be considered
            self.months = list(range(1,13))
            _w = 'For operation %s, "months" is not defined. ' % self.id
            _w += 'All months will be considered.'
            logging.warning('CorrectiveMinor: '+ _w)
        if sum([
                1
                if tech is True
                else 0
                for tech in [tech_wtg, tech_wec, tech_pv]
        ]) > 1:
            _e = 'For operation %s, only one technology can be defined.' % self.id
            logging.error('CorrectiveMinor: ' + _e)
            raise ValueError(_e)

        if tech_cost is not None and tech_cost != 0:
            self.tech_cost = float(tech_cost)
        if tech_wtg is True:
            self.technology = 'wtg'
        elif tech_wec is True:
            self.technology = 'wec'
        elif tech_pv is True:
            self.technology = 'pv'

        if wave_height is not None:
            self.hs = float(wave_height)
        if wave_period is not None:
            self.tp = float(wave_period)
        if wind_speed is not None:
            self.ws = float(wind_speed)
        if wind_speed_hub is not None:
            self.ws_hub = float(wind_speed_hub)
        if current_speed is not None:
            self.cs = float(current_speed)
        if light is not None:
            if light is True or light is False:
                self.light = light
            elif light == 1.0:
                self.light = True
            elif light == 0.0:
                self.light = False
            else:
                try:
                    self.light = bool(strtobool(str(light)))
                except ValueError:
                    e_ = f'CorrectiveMinor: For operation {self.id}, "light" must be a boolean value'
                    logging.error(e_)
                    raise ValueError(_e)
        if vessel1_qt is not None:
            self.vessel1_qt = int(vessel1_qt)
        if vessel2_id is not None:
            self.vessel2_id = str(vessel2_id).lower()
            if vessel2_qt is not None:
                self.vessel2_qt = int(vessel2_qt)
            else:
                self.vessel2_qt = int(1)
        if rov_drone is not None:
            self.rov_drone = str(rov_drone).lower()
        if other_costs is not None:
            self.other_costs = float(other_costs)
        if rov_drone is not None:
            self.rov_drone = str(rov_drone).lower()


        self._check_attributes()


    def _check_attributes(self):
        """
        Validate the attributes of the `CorrectiveMinor` class to ensure they are within acceptable ranges.

        Raises errors if any attribute is outside the specified range.
        """
        if self.id[0:3] not in ['ofw','owc','opv']:
            raise ValueError('"prefix not recognized"')
        if self.duration_net <= 0:
            raise ValueError('"duration_net" must be positive')
        if any([
            self.level == 'exp_cable',
            self.level == 'exp_cable_island',
            self.level == 'dyn_cable-sub',
            self.level == 'cable_cb',
            self.level == 'cable_transf',
            self.level == 'cable_switch',
            self.level == 'cable_inv',
            self.level == 'array_cable',
            self.level == 'string_cable',
            self.level == 'substation',
            self.level == 'mv_transformer',
            self.level == 'circuit_braker',
            self.level == 'switcher',
            self.level == 'inverter',
            self.level == 'device'
        ]) is False:
            raise ValueError('"level" must be “exp_cable”, “dyn_cable-sub”, “cable_cb”, “string_cable”, “cable_transf”, “cable_switch”, “cable_inv”, “array_cable”, “substation”, “mv_transformer”, “circuit_braker”, “switcher”, “inverter”, “device”')
        if self.tech_required < 1:
            raise ValueError('"tech_required" must be positive')
        if self.tech_cost < 0:
            raise ValueError('"tech_cost" must not be negative')
        if isinstance(self.months, int) is True and self.months in range(1,13) is False:
            raise NameError(' "month" must be between 1 and 12')
        if isinstance(self.months, int) is False and all([month in range(1, 13) for month in self.months]) is False:
            raise NameError('"months" must be between 1 and 12')
        if self.hs is not None and self.hs < 0:
            raise ValueError('"wave_height" must not be negative')
        if self.tp is not None and self.tp < 0:
            raise ValueError('"wave_period" must not be negative')
        if self.ws is not None and self.ws < 0:
            raise ValueError('"wind_speed" must not be negative')
        if self.ws_hub is not None and self.ws_hub < 0:
            raise ValueError('"wind_speed_hub" must not be negative')
        if self.cs is not None and self.cs < 0:
            raise ValueError('"current_speed" must not be negative')
        if self.other_costs is not None and self.other_costs < 0:
            raise ValueError('"other_costs" must not be negative')
        if self.vessel1_qt < 1:
            raise ValueError('"vessel1_qt" must be positive')
        if self.vessel2_id is not None:
            if self.vessel2_qt < 1:
                raise ValueError('"vessel2_qt" must be positive if a "vessel2_id" is defined')


        logging.debug('CorrectiveMinor: operation %s attributes within ranges and valid.' % self.id)


    def get_operations_from_yaml(
            file_path: object
        ) -> list:
        """
        Read a YAML file and extract operations from it, ensuring all mandatory keys are present.

        Args:
            file_path (:obj:`string`): The path to the YAML file.
        Raises:
            KeyError: if any mandatory keys are missing in the YAML entries.
        Return:
            List of :class:`CorrectiveMinor`.
        """

        # Gets operations from a YAML file
        f_yaml = open(os.path.join(file_path), 'r')
        yaml = YAML(typ='safe')
        operations_yaml = yaml.load(f_yaml)
        f_yaml.close()
        # All operations keys to lower case
        operations_yaml = [
                {key.lower(): val for key, val in op.items()}
                for op in operations_yaml
        ]

        keys_mandatory = [
                'id',
                'name',
                'duration_net',
                'device_shutdown',
                'vessel1_id',
                'vessel1_qt',
                'tech_required',
                'level'
        ]
        no_mandatory_keys = [
                'tech_wtg',
                'tech_wec',
                'tech_pv',
                'tech_cost',
                'wave_height',
                'wave_period',
                'wind_speed',
                'wind_speed_hub',
                'current_speed',
                'light',
                'vessel2_id',
                'vessel2_qt',
                'rov_drone',
                'other_costs',
                'double_shift'
        ]

        operations_list = []
        for operation in operations_yaml:
            if any([
                    key not in operation.keys()
                    for key in keys_mandatory
            ]) is True:
                _e = '"id", "name", "duration_net", "device_shutdown", '
                _e += '"vessel1_id", "vessel1_qt", "tech_required" and "level" '
                _e += 'are mandatory keys.'
                logging.error('CorrectiveMinor: ' + _e)
                raise KeyError(_e)

            for key in no_mandatory_keys:
                try:
                    operation[key]
                except KeyError:
                    operation[key] = None

            operations_list.append(
                CorrectiveMinor(
                id_=operation["id"],
                name=operation["name"],
                tech_wtg=operation["tech_wtg"],
                tech_wec=operation["tech_wec"],
                tech_pv=operation["tech_pv"],
                duration_net=operation["duration_net"],
                device_shutdown=operation["device_shutdown"],
                wave_height=operation["wave_height"],
                wave_period=operation["wave_period"],
                wind_speed=operation["wind_speed"],
                wind_speed_hub=operation["wind_speed_hub"],
                current_speed=operation["current_speed"],
                light=operation["light"],
                vessel1_id=operation["vessel1_id"],
                vessel1_qt=operation["vessel1_qt"],
                vessel2_id=operation["vessel2_id"],
                vessel2_qt=operation["vessel2_qt"],
                rov_drone=operation["rov_drone"],
                tech_required=operation["tech_required"],
                tech_cost=operation["tech_cost"],
                other_costs=operation["other_costs"],
                level=operation["level"],
                double_shift=operation["double_shift"],
                )
            )

        logging.info('CorrectiveMinor: operations defined based on file "%s"' % file_path)
        return operations_list


    def define_months_operations(self):
        """
        Define the months in which corrective operations may take place based on operation failures.
        If any failure is to be immediately corrected, all months are considered.
        If a failure is to be corrected in a specific month, only that month is included.
        """
        if self.failures is None:
            return

        months = []
        for fail in self.failures:
            if 'specific' in fail.maintenance_strategy:
                months.append(fail.preferred_month)

        if len(months) > 0:
            self.months = months


    def to_yaml(
            self,
            out_dir: str
    ):
        """
        Write the object attributes to a YAML file in the specified output directory.

        Args:
            out_dir (:obj:`str`): The directory where the YAML file will be saved.
        """
        vessel1 = self.vessel1_id
        if self.vessel1 is not None:
            vessel1 = {
                    "id": self.vessel1.id,
                    "number": self.vessel1_qt
            }
        vessel2 = self.vessel2_id
        if self.vessel2 is not None:
            vessel2 = {
                    "id": self.vessel2.id,
                    "number": self.vessel2_qt
            }
        rov_drone = self.rov_drone
        if self.rov_drone is not None and isinstance(self.rov_drone,list) is False:
            rov_drone = self.rov_drone.id
        else:
            rov_drone = self.rov_drone

        f = open(os.path.join(out_dir, 'attributes.yaml'), 'w')
        yaml=YAML()
        yaml.default_flow_style = None
        yaml.dump({
                "id": self.id,
                "name": self.name,
                "duration_net": self.duration_net,
                "device_shutdown": self.device_shutdown,
                "level": self.level,
                "months": self.months,
                "technology": self.technology,
                "tech_required": self.tech_required,
                "tech_cost": self.tech_cost,
                "hs": self.hs,
                "tp": self.tp,
                "ws": self.ws,
                "ws_hub": self.ws_hub,
                "cs": self.cs,
                "light": self.light,
                "vessel1": vessel1,
                "vessel2": vessel2,
                "other_costs": self.other_costs,
                "rov_drone": rov_drone,
                "double_shift": self.double_shift,
                "failures": self.failures
        }, f)
        f.close()