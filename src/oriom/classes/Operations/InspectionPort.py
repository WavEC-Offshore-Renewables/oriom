# Import packages
import pandas as pd
import logging
import os
from ruamel.yaml import YAML
from distutils.util import strtobool

from oriom.core.functions.layout_power.aux_layout_power_func import find_highest_power_node


class InspectionPort():
    """
    A class representing a InspectionPort operation with various attributes and methods.

    Inspections at port are planned automatically in the
    :class:`~oriom.classes.OperationsStat.InspectionPortStat.InspectionPortStat`.

    Attributes:
        id (:obj:`str`): The unique identifier of the :class:`InspectionPort`.
        name (:obj:`str`): :class:`InspectionPort` short description.
        periodicity (:obj:`float`): Time interval between inspection campaings.
        months (:obj:`list`): Months when the inspection is preformed.
        day_start (int): Day on which the inspection should start
        tech_per_device (:obj:`int`): Number of technicians required to preform
            the inspection per device.
        dur_per_device (:obj:`float`): Amount of time to inspect one device [hours].
        op_tow_port (:obj:`str`): ID of the tow-to-port operation.
        op_tow_site (:obj:`str`): ID of the tow-to-site operation.
        op_tow_site_port (:obj:`str`): ID of the tow-to-site operation, connection of
            device, disconnection of another device, tow-to-port.
            Its value is :obj:`0.0` if not defided.
        intervened_devices (:obj:`int`): Number of devices that are intervened in case
            this inspection occurs.
        tech_cost (:obj:`float`): The daily cost of each technician [€/day].
            Its value is ``0`` if not defined.
        ws (:obj:`float`): Limit wind speed. Its value is ``None`` if there is no limit.
        light (:obj:`bool`, *optional*): If the operation is light. Default to ``False``
        level (:obj:`str`): Level at which the failure occurs for the graph.
        vessel1_id (:obj:`str`): The ID of the main vessel. Its value is
            ``None`` if not defided.
        vessel2_id (:obj:`str`): The ID of the auxiliary vessel. Its value is
            ``None`` if not defided.
        vessel1 (:class:`~oriom.classes.Vessel.Vessel`): Main vessel
            used in this operation. Its value is ``None`` if not defided.
        vessel2 (:class:`~oriom.classes.Vessel.Vessel`): Auxiliary
            vessel used in this operation. Its value is ``None`` if not
            defided.
        rov_drone (:class:`~oriom.classes.RovDrone.RovDone`): The ID of the ROV/Drone.
            Its value is ``None`` if not defided.
        parts_cost (:obj:`float`): Cost of replacement parts. Its value is
            :obj:`0.0` if not defided.
        other_costs (:obj:`float`): Other costs (port, cranes, insurance, etc.).
            Its value is :obj:`0.0` if not defided.
        port_costs (:obj:`float`): Daily port costs. Its value is :obj:`0.0` if not defided.
        n_device_at_port(:obj:`int`): Number of devices that can be mantained
            at port simultaneously
        n_device_stored_at_port(:obj:`int`): Number of devices that can be
            stored at port
        ts_data (:class:`~oriom.classes.OperationTimeSeriesData.OperationTimeSeriesData`):
            Timeseries data of the operation. Its value is ``None`` if not defided
        double_shift (bool): Boolean to specify if it can hold double shift inspection (day&night)
        towing_log (:obj:`pd.DataFrame`): Dataframe that log the towing to port and to site operation.
            Default to empty dataframe.
        insp_port_dir (:obj:`str`): Directory where the inspection port is stored.
            Default to None.
        n_device_at_port(:obj:`int`): Number of devices that can be mantained
            at port simultaneously. Defaults to :obj:`1`
        n_device_stored_at_port(:obj:`int`): Number of devices that can be
            stored at port when not in maintenance. Defaults to :obj:`0.0`
        n_days_main (:obj:`int`): Number of total days of shift needed to conclude the insp.
            Defaults to ``0``
        duration_main (:obj:`int`): Number of hours of duration_main days of main_shift.
            Defaults to ``0``
        n_days_last (:obj:`int`): Number of total days of shift needed to conclude the insp.
            Defaults to ``0``
        duration_last (:obj:`int`): Number of hours of duration_main days of main_shift.
            Defaults to ``0``
        n_crew_main (:obj:`int`): Number of crew members needed for main shift.
            Defaults to ``0``
        n_crew_last (:obj:`int`): Number of crew members needed for last shift.
            Defaults to ``0``

    Note:
        When the class is initialized, :func:`_check_attributes` is run.
    """
    def __init__(
            self,
            id_: str,
            name: str,
            periodicity: float,
            tech_per_device: int,
            dur_per_device: float,
            towing_ops: list,
            intervened_devices: int,
            tech_cost: float=0,
            months: str=None,
            day_start: int=None,
            wind_speed: float=None,
            light: bool=False,
            level: str = None,
            rov_drone: str=None,
            parts_cost: float=0,
            other_costs: float=0,
            port_costs: float=0,
            n_device_at_port: int=0,
            n_device_stored_at_port: int=0,
            double_shift: bool= True,
            towing_log: pd.DataFrame = pd.DataFrame()
    ):
        """Initializes :class:`InspectionPort` with various attributes and optional parameters.

        Args:
            id_ (:obj:`str`): The unique identifier of the InspectionPort.
            name (:obj:`str`): InspectionPort short description.
            tow_to_port (:obj:`bool`): This operation requires the device removal
                and redeploy.
            periodicity (:obj:`float`): Time interval between inspection campains [years].
            tech_per_device (:obj:`int`): Number of technicians required to
                preform the operation.
            dur_per_device (:obj:`float`): Amount of time to inspect one device [hours].
            towing_ops (:obj:`list`): List of all towing operations.
            intervened_devices (:obj:`int`): Number of devices that are
                intervened in case this operation occurs.
            tech_cost (:obj:`float`,*optional*): The daily cost of each technician [€/day].
                Defaults to ``0``.
            months (:obj:`str`, *optional*): Months when the operation is preformed.
                Defaults to an empty list for corrective operations and to
                [1,2,3,4,5,6,7,8,9,10,11,12] for preventive if not defined..
            day_start (int, *optional*): Day on which the inspection should start
                Default to ``None``.
            wind_speed (:obj:`float`, *optional*): Limit wind speed. Defaults to ``None``.
            light (:obj:`bool`, *optional*): If the operation is light. Default to ``False``
            level (:obj:`str`): Level at which the failure occurs for the graph.
            rov_drone (:obj:`str`, *optional*): The ID of the ROV/Drone.
                Defaults to ``None``.
            parts_cost (:obj:`float`, *optional*): Cost of replacement parts.
                Defaults to :obj:`0.0`.
            other_costs (:obj:`float`, *optional*): Other costs (port, cranes,
                insurance, etc.). Defaults to :obj:`0.0`.
            port_costs (:obj:`float`, *optional*): Daily port costs. Defaults to :obj:`0.0`.
            n_device_at_port(:obj:`int`): Number of devices that can be mantained
                at port simultaneously. Defaults to :obj:`1`
            n_device_stored_at_port(:obj:`int`): Number of devices that can be
                stored at port when not in maintenance. Defaults to :obj:`0.0`
            days_main (:obj:`int`): Number of total days of shift needed to conclude the insp.
                Defaults to ``0``
            duration_main (:obj:`int`): Number of hours of duration_main days of main_shift.
                Defaults to ``0``
            days_last (:obj:`int`): Number of total days of shift needed to conclude the insp.
                Defaults to ``0``
            duration_last (:obj:`int`): Number of hours of duration_main days of main_shift.
                Defaults to ``0``
            double_shift (bool): Boolean to specify if it can hold double shift inspection (day&night)
                Default to True
            towing_log (:obj:`pd.DataFrame`): Dataframe that log the towing to port and to site operation.
                Default to empty dataframe.

        Raises:
            ValueError: if any of :attr:`months` values is not an integer.
            ValueError: if :attr:`light` is not a boolean value.
        """
        # Default Value
        self.id = str(id_).lower()
        self.name = str(name)
        self.periodicity = float(periodicity)
        self.tech_per_device = int(tech_per_device)
        self.dur_per_device = float(dur_per_device)
        self.intervened_devices = int(intervened_devices)
        self.tech_cost = 0
        self.months = list(range(1, 13))
        self.day_start = 1
        self.rov_drone = None
        self.level = str(level)
        self.vessel1_id = None
        self.vessel2_id = None
        self.ts_data = None
        self.ws = None
        self.light = None
        self.parts_cost = 0
        self.other_costs = 0
        self.port_costs = 0
        self.n_device_at_port = 1
        self.n_device_stored_at_port = 0
        self.vessel1 = None
        self.vessel2 = None
        self.op_tow_port = None
        self.op_tow_site = None
        self.op_tow_site_port = None
        self.days_main = 0
        self.duration_main = 0
        self.days_last = 0
        self.duration_last = 0
        self.n_crew_main = 0
        self.n_crew_last = 0
        self.double_shift = None
        self.towing_log = towing_log
        self.insp_port_dir = None

        # Assign value
        if tech_cost is not None and tech_cost != 0:
            self.tech_cost = float(tech_cost)
        if months is not None:
            try:
                try: self.months = [int(mnt) for mnt in months.split(',')]
                except: self.months = int(months)                           # TODO: Check which error the "try" resturn and write an exception only for that error
            except ValueError:
                _e = 'For inspection %s, "months" must be in the format ' % self.id
                _e += 'of "Month1, Month2, ..." (ex.: "06, 07, 08")'
                logging.error('InspectionPort: '+ _e)
                raise ValueError(_e)
        else:
            # If the months are not defined, all months should be considered
            _w = 'For inspection %s, "months" is not defined. ' % self.id
            _w += 'All months will be considered.'
            logging.warning('InspectionPort: '+ _w)

        if day_start is not None:
            self.day_start = int(day_start)
        if wind_speed is not None:
            self.ws = float(wind_speed)
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
                    e_ = f'InspectionPort: For operation {self.id}, "light" must be a boolean value'
                    logging.error(e_)
                    raise ValueError(_e)

        if rov_drone is not None:
            self.rov_drone = str(rov_drone).lower()
        if parts_cost is not None:
            self.parts_cost = float(parts_cost)
        if other_costs is not None:
            self.other_costs = float(other_costs)
        if port_costs is not None:
            self.port_costs = float(port_costs)
        if n_device_at_port is not None:
            self.n_device_at_port = int(n_device_at_port)
        if n_device_stored_at_port is not None:
            self.n_device_stored_at_port = int(n_device_stored_at_port)
        if double_shift is not None:
            if double_shift is True or double_shift is False:
                self.double_shift = double_shift
            elif double_shift == 1.0:
                self.double_shift = True
            elif double_shift == 0.0:
                self.double_shift = False
            else:
                try:
                    self.double_shift = bool(strtobool(str(double_shift)))
                except ValueError:
                    e_ = f'InspectionPort: For operation {self.id}, "double_shift" must be a boolean value'
                    logging.error(e_)
                    raise ValueError(_e)

        self._check_attributes()
        self._define_tow_operations(towing_ops)


    def _check_attributes(self):
        """
        This method validates the attributes of the `CorrectiveMajor` class to ensure they
        have valid values and fall within specified ranges.

        Raises errors if any attribute is outside the specified range.
        """

        day_dict = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}

        if self.id[0:3] not in ['oce','ofw','owc','opv']:
            raise ValueError('"prefix not recognized"')
        if self.periodicity <= 0:
            raise ValueError('"periodicity" must be positive')
        if self.tech_per_device < 1:
            raise ValueError('"tech_per_device" must be positive')
        if self.tech_cost < 0:
            raise ValueError('"tech_cost" must not be negative')
        if self.dur_per_device <= 0:
            raise ValueError('"dur_per_device" must be positive')
        if isinstance(self.months, int) is True and self.months in range(1,13) is False:
            raise NameError(' "month" must be between 1 and 12')
        if isinstance(self.months, int) is False and all([month in range(1, 13) for month in self.months]) is False:
            raise NameError('"months" must be between 1 and 12')
        if isinstance(self.months, int):
            if self.day_start not in range(1, day_dict[self.months]+1):
                    raise ValueError(f'"day_start" must be between 1 and {day_dict[self.months]} for the month {self.months}')
        if isinstance(self.months, list):
            last_day = 31
            for m in self.months:
                if m in day_dict:
                    last_day = min(day_dict[m], last_day)
            if self.day_start not in range(1, last_day+1):
                raise ValueError(f'"day_start" must be between 1 and {last_day} for the months considered {self.months}')
        # TODO modify this with an automatic list taken by the layout used
        if any([
            self.level == None,
            self.level == 'exp_cable',
            self.level == 'exp_cable_island',
            self.level == 'dyn_cable-sub',
            self.level == 'array_cable',
            self.level == 'cable_cb',
            self.level == 'cable_transf',
            self.level == 'cable_switch',
            self.level == 'cable_inv',
            self.level == 'string_cable',
            self.level == 'substation',
            self.level == 'mv_transformer',
            self.level == 'circuit_braker',
            self.level == 'switcher',
            self.level == 'inverter',
            self.level == 'device'
        ]) is False:
            raise ValueError('"level" must be "device", "array_cable", "string_cable", "exp_cable" or "dyn_cable-sub"')
        if self.intervened_devices < 0:
            raise ValueError('"intervened_devices" must not be negative')
        if self.ws is not None and self.ws < 0:
            raise ValueError('"wind_speed" must not be negative')
        if self.parts_cost is not None and self.parts_cost < 0:
            raise ValueError('"parts_cost" must not be negative')
        if self.other_costs is not None and self.other_costs < 0:
            raise ValueError('"other_costs" must not be negative')
        if self.port_costs is not None and self.port_costs < 0:
            raise ValueError('"port_costs" must not be negative')
        if self.n_device_at_port is not None and self.n_device_at_port < 0:
            raise ValueError('"n_device_at_port" must not be negative')
        if self.n_device_stored_at_port is not None and self.n_device_stored_at_port < 0:
            raise ValueError('"n_device_stored_at_port" must not be negative')

        logging.debug('InspectionPort: inspection %s attributes within ranges and valid.' % self.id)


    def _define_tow_operations(self, towing_ops:list):
        """
        Define tow operations based on the given towing operations and the technology identifier.

        Args:
            towing_ops (:obj:`list`): List of object :class:`OperationTow`.
        """
        if 'ofw' in self.id:
            tech_identifier = 'ofw'
        elif 'owc' in self.id:
            tech_identifier = 'owc'
        elif 'opv' in self.id:
            tech_identifier = 'opv'
        else:
            _e = 'For inspection %s, the technology identifier ' % self.id
            _e += 'prefix is not recognized.'
            raise TypeError(_e)

        for op in towing_ops:
            if tech_identifier in op.id:
                if 'remov' in op.name.lower() and 'deplo' not in op.name.lower():
                    self.op_tow_port = op.id
                elif 'deplo' in op.name.lower() and 'remov' not in op.name.lower():
                    self.op_tow_site = op.id
                elif 'deplo' in op.name.lower() and 'remov' in op.name.lower():
                    self.op_tow_site_port = op.id
                else:
                    _e = 'For operation %s, the tow operation ' % self.id
                    _e += '%s is not recogneized either as a device ' % op.id
                    _e += '"removal", "redeploy" or "redeploy" and "tow".'
                    raise TypeError(_e)

        # Check if both operation IDs were defined
        if self.op_tow_port is None:
            _e = 'For operation %s, could not define a tow-to-port operation.' % self.id
            raise NameError('InspectionPort: ' + _e)
        if self.op_tow_site is None:
            _e = 'For operation %s, could not define a tow-to-site operation.' % self.id
            raise NameError('InspectionPort: ' + _e)
        if self.op_tow_site_port is None:
            _w = 'For operation %s, could not define a tow-to-site operation.' % self.id
            logging.warning('InspectionPort: ' + _w)


    def define_level(self, G_layouts:dict):
        """
        If the level of the inspection is not defined, select the node with the power defined in the nx Graph.

        Args:
            G_layouts (dict): dictionary with the graph of the layouts for wind, wave and pv
        """
        if not self.level:
            tech = self.tech_finder()
            if tech:
                self.level = find_highest_power_node(G_layouts[tech])
            else:
                # oce common event case, take the level of the first  Graph that you find
                for tech in ["G_wind","G_wave","G_pv"]:
                    try:
                        self.level = find_highest_power_node(G_layouts[tech])
                        break
                    except AttributeError:
                        continue


    def get_inspections_from_yaml(
            file_path: object,
            towing_operations: list=None
    ) -> list:
        """
        Read a YAML file and extract operations from it.

        Args:
            file_path (:obj:`string`): The path to the YAML file.
            towing_operations (:obj:`list`, *optional*): A list containing 3 towing operations: tow-to-port and tow-to-site.
                The first item is the tow-to-port operation and the second item is the tow-to-site operation then also tow_port_site is present
                Defaults to None if not provided.
        Raises:
            KeyError: if one of the YAML entries does not have all the mandatory keys.
        Return:
            List of :class:`InspectionPort`.
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
                'periodicity',
                'tech_per_device',
                'dur_per_device',
        ]
        no_mandatory_keys = [
                'tech_cost',
                'months',
                'day_start',
                'level'
                'intervened_devices',
                'wind_speed',
                'light',
                'parts_cost',
                'ports_cost',
                'other_costs',
                'n_device_at_port',
                'n_device_stored_at_port',
                'days_main',
                'days_last',
                'duration_main',
                'duration_last',
                'double_shift'
        ]

        inspections_list = []
        for operation in operations_yaml:
            if any([
                    key not in operation.keys()
                    for key in keys_mandatory
            ]) is True:
                _e = '"id", "name", "periodicity", '
                _e += '"tech_per_device" and '
                _e += '"dur_per_device" are mandatory keys.'
                logging.error('InspectionPort: ' + _e)
                raise KeyError(_e)

            for key in no_mandatory_keys:
                try:
                    operation[key]
                except KeyError:
                    operation[key] = None
            inspections_list.append(
                InspectionPort(
                    id_=operation["id"],
                    name=operation["name"],
                    periodicity=operation["periodicity"],
                    tech_per_device=operation["tech_per_device"],
                    tech_cost=operation["tech_cost"],
                    dur_per_device=operation["dur_per_device"],
                    months=operation["months"],
                    day_start=operation["day_start"],
                    intervened_devices=operation["intervened_devices"],
                    wind_speed=operation["wind_speed"],
                    light=operation["light"],
                    level=operation["level"],
                    parts_cost=operation["parts_cost"],
                    port_costs=operation["ports_cost"],
                    other_costs=operation["other_costs"],
                    n_device_at_port=operation["n_device_at_port"],
                    n_device_stored_at_port=operation["n_device_stored_at_port"],
                    towing_ops=towing_operations,
                    double_shift=operation["double_shift"],
                )
            )

        logging.info('InspectionPort: inspections defined based on file "%s"' % file_path)
        return inspections_list


    def define_device_at_port(self, wtg, wec, pv):
        tech_op = self.id[:3]

        if tech_op == 'ofw':
            n_device_at_port = wtg.n_device_at_port
            n_device_stored_at_port = wtg.n_device_stored_at_port
        elif tech_op == 'owc':
            n_device_at_port = wec.n_device_at_port
            n_device_stored_at_port = wec.n_device_stored_at_port
        elif tech_op == 'opv':
            n_device_at_port = pv.n_device_at_port
            n_device_stored_at_port = pv.n_device_stored_at_port
        else:
            raise KeyError('The prefix of the operation is not well described. It must be one of ["ofw", "owc", "opv"]')

        if n_device_at_port is None or n_device_at_port == 0:
            n_device_at_port = 1
        if n_device_stored_at_port is None:
            n_device_stored_at_port = 0
        if n_device_at_port < 0 or n_device_stored_at_port < 0:
            raise ValueError('The n_device_at_port or n_device_stored_at_port cannot be negative')

        self.n_device_at_port = n_device_at_port
        self.n_device_stored_at_port = n_device_stored_at_port


    def assign_shift_attributes(self, data: dict):
        self.days_main = data.get('days_main', None) if data.get('days_main', None) is not None else data.get('number_shifts_main', None)
        self.duration_main = data.get('duration_main', None)
        self.days_last = data.get('days_last', None) if data.get('days_last', None) is not None else data.get('number_shifts_last', None)
        self.duration_last = data.get('duration_last', None)
        self.n_crew_main = data.get('n_crew_main', None)
        self.n_crew_last = data.get('n_crew_last', None)


    def tech_finder(self):
        """Return the type of the farm considered"""
        mapping = {"ofw": "G_wind","owc": "G_wave","opv": "G_pv"}

        for key, value in mapping.items():
            if key in self.id:
                return value
        return None


    def to_yaml(
            self,
            out_dir: str
    ):
        """
        Write the object attributes to a YAML file in the specified output directory.

        Args:
            out_dir (:obj:`str`): The directory where the YAML file will be saved.
        """
        vessel1 = self.vessel1
        if self.vessel1 is not None:
            vessel1 = {
                    "id": self.vessel1.id,
                    "number": self.vessel1.n_vessels
            }
        vessel2 = self.vessel2
        if self.vessel2 is not None:
            vessel2 = {
                    "id": self.vessel2.id,
                    "number": self.vessel2.n_vessels
            }
        rov_drone = self.rov_drone
        if self.rov_drone is not None:
            rov_drone = self.rov_drone.id

        f = open(os.path.join(out_dir, 'attributes.yaml'), 'w')
        yaml=YAML()
        yaml.default_flow_style = None
        yaml.dump({
                "id": self.id,
                "name": self.name,
                "periodicity": self.periodicity,
                "months": self.months,
                "day_start": self.day_start,
                "tech_per_device": self.tech_per_device,
                "tech_cost": self.tech_cost,
                "dur_per_device": self.dur_per_device,
                "op_tow_port": self.op_tow_port,
                "op_tow_site": self.op_tow_site,
                "vessel1": vessel1,
                "vessel2": vessel2,
                "intervened_devices": self.intervened_devices,
                "ws": self.ws,
                "light": self.light,
                "level": self.level,
                "rov_drone": rov_drone,
                "parts_cost": self.parts_cost,
                "other_costs": self.other_costs,
                "port_costs": self.port_costs,
                "n_device_at_port": self.n_device_at_port,
                "n_device_stored_at_port": self.n_device_stored_at_port,
                "op_tow_port": self.op_tow_port,
                "op_tow_site": self.op_tow_site,
                "op_tow_site_port": self.op_tow_site_port,
                "days_main": self.days_main,
                "days_last": self.days_last,
                "duration_main": self.duration_main,
                "duration_last": self.duration_last,
                "double_shift": self.double_shift,
        }, f)
        f.close()
