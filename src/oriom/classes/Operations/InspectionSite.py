# Import packages
import logging
import os
from ruamel.yaml import YAML
from distutils.util import strtobool

from oriom.core.functions.layout_power.aux_layout_power_func import find_highest_power_node


class InspectionSite():
    """
    A class representing a InspectionSite operation with various attributes and methods.

    Note:
        - If it is a common inspection at the export cable ('oce_exp'):
            intervened_wtg = 0,
            intervened_wec = 0,
            intervened_pv = 0
        - If an inspections is to be grouped with another here are the possible actions:
            1. The merging function in the cost inputs class (:class:`Inputs.Cost`) has to be set to TRUE
            2. The :attr:`to_be_grouped` attributes has to be set to TRUE
            3. If the inspection that has to be grouped with is known the :attr:`to_group_with`
                attribute can be filled with the id of the inspection that we want it to be
                grouped with (it has to be a site inspection). Otherwise we can leave the
                :attr:`to_group_with` empty and the code will look for a feasible inspection.
            If some inspections do not have to be grouped together then we set the :attr:`to_be_grouped`
            to FALSE.
        - Be aware that the number of devices intervened shall be not higher than the total amount of
            devices declared in the technologies classess (wtg, wec, pv)

    Attributes:
        id (:obj:`str`): The unique identifier of the :class:`InspectionSite`.
        name (:obj:`str`): :class:`InspectionSite` short description.
        overnight (:obj:`bool`): Consider that the crew stays on the vessel
            over the nigth. **NOT USED**
        periodicity (:obj:`float`): Time interval between inspection campaings.
        months (:obj:`list`): Months when the inspection is preformed.
        day_start (int): Day on which the inspection should start
        tech_per_device (:obj:`int`): Number of technicians required to preform
            the inspection.
        tech_cost (:obj:`float`): The daily cost of each technician [€/day].
        dur_per_device (:obj:`float`): Amount of time to inspect one device [hours].
        device_shutdown (:obj:`bool`): If the inspection requires to shutdown the device.
        level (:obj:`str`): Level for the electrical layout (device, array_cable, string_cable,
            exp_cable or dyn_cable-sub).
        vessel1_id (:obj:`str`): The ID of the main vessel.
        vessel1_qt (:obj:`int`): Number of main vessels available along the inspection.
            Its value is ``1`` if not defined.
        vessel2_id (:obj:`str`): The ID of the auxiliary vessel. Its value is
            ``None`` if not defided.
        vessel2_qt (:obj:`int`): Number of secondary vessels available along the inspection .
            Its value is ``None`` if not defined.
        intervened_wtg (:obj:`int`): Number of WTG that are intervened in case
            this inspection occurs. Its value is ``None`` if not defided.
        intervened_wec (:obj:`int`): Number of WEC that are intervened in case
            this inspection occurs. Its value is ``None`` if not defided.
        intervened_pv (:obj:`int`): Number of PV panels that are intervened in
            case this inspection occurs. Its value is ``None`` if not defided.
        hs (:obj:`float`): Limit wave height. Its value is ``None`` if there is no limit.
        tp (:obj:`float`): Limit wave period. Its value is ``None`` if there is no limit.
        ws (:obj:`float`): Limit wind speed. Its value is ``None`` if there is no limit.
        ws_height (:obj:`float`): Limit wind speed at hub height. Its value is ``None`` if there is no limit.
        cs (:obj:`float`): Limit current speed. Its value is ``None`` if there is no limit.
        light (:obj:`bool`, *optional*): If the operation is light. Default to ``False``
        vessel1 (:class:`~oriom.classes.Vessel.Vessel`): Main vessel
            used in this inspection. Its value is ``None`` if not defided.
        vessel2 (:class:`~oriom.classes.Vessel.Vessel`): Auxiliary
            vessel used in this inspection. Its value is ``None`` if not
            defided.
        rov_drone (:class:`~oriom.classes.RovDrone.RovDone`): Rov/Drone
            used in this operation. Its value is ``None`` if not
            defided.
        parts_cost (:obj:`float`): Cost of replacement parts. Its value is
            :obj:`0.0` if not defided.
        other_costs (:obj:`float`): Other costs (port, cranes, insurance, etc.).
            Its value is :obj:`0.0` if not defided.
        to_be_grouped (:obj:`bool`): True or False weather the inspection can be
            grouped. Its value is ``False`` if not defined.
        to_group_with : Inspection at site id that can be performed with. It can be a string or a
            :class:`~oriom.classes.Operations.InspectionSite`
            Its value is ``None`` if not defined.
        n_vessel_main (:obj:`int`): Number of vessels used for the main part of the
            inspections. Its values is ``None`` if not defined.
        n_vessel_last (:obj:`int`): Number of vessels used for the last part of the
            inspections. Its values is ``None`` if not defined.
        ts_data (:class:`~oriom.classes.OperationTimeSeriesData.OperationTimeSeriesData`):
            Timeseries data of the operation. Its value is ``None`` if not defided
        double_shift (bool): Boolean to specify if it can hold double shift inspection (day&night)
            Default to True
        days_main (:obj:`int`): Number of total days of shift needed to conclude the insp.
            Defaults to ``0``
        duration_main (:obj:`int`): Number of hours of duration_main days of main_shift.
            Defaults to ``0``
        days_last (:obj:`int`): Number of total days of shift needed to conclude the insp.
            Defaults to ``0``
        duration_last (:obj:`int`): Number of hours of duration_main days of main_shift.
            Defaults to ``0``
        crew_main (:obj:`int`): Number of crew members for main shift. Defaults to ``0``
        crew_last (:obj:`int`): Number of crew members for last shift. Defaults to ``0``
        n_dev_done_main_shift (:obj:`int`): Number of devices inspected during main shift
            Defaults to ``0``
        n_dev_done_last_shift (:obj:`int`): Number of devices inspected during last shift
            Defaults to ``0``


    Note:
        When the class is initialized, :func:`_check_attributes` is run.
    """
    def __init__(
            self,
            id_: str,
            name: str,
            overnight_stay: bool,
            periodicity: float,
            tech_per_device: int,
            dur_per_device: float,
            device_shutdown: bool,
            level: str,
            vessel1_id: str,
            vessel1_qt: int=1,
            tech_cost: float=0,
            months: str=None,
            day_start: int=None,
            intervened_wtg: int=None,
            intervened_wec: int=None,
            intervened_pv: int=None,
            wave_height: float=None,
            wave_period: float=None,
            wind_speed: float=None,
            wind_speed_hub: float=None,
            current_speed: float=None,
            light: bool=False,
            vessel2_id: str=None,
            vessel2_qt: int=None,
            rov_drone: str=None,
            parts_cost: float=0,
            other_costs: float=0,
            to_be_grouped: bool=False,
            n_vessel_main: int=None,
            n_vessel_last: int=None,
            to_group_with= None,
            double_shift: bool= True

    ):
        """Initializes :class:`InspectionSite` with various attributes and optional parameters.

        Args:
            id_ (:obj:`str`): The unique identifier of the InspectionSite.
            name (:obj:`str`): InspectionSite short description.
            overnight_stay (:obj:`bool`): Consider that the crew stays on the vessel
                over the nigth. Two shifts of 12 hours are considered.
            periodicity (:obj:`float`): Time interval between inspection campains [years].
            tech_per_device (:obj:`int`): Number of technicians required to
                preform the inspection.
            dur_per_device (:obj:`float`): Amount of time to inspect one device [hours].
            level (:obj:`str`): Level for the electrical layout (device, array_cable, string_cable, exp_cable or dyn_cable-sub).
            device_shutdown (:obj:`bool`): If the inspection requires to shutdown the device.
            tech_cost (:obj:`float`, *optional*): The daily cost of each technician[€/day].
                Defaults to ``0``.
            months (:obj:`str`, *optional*): Months when the inspection is preformed.
                Defaults to an empty list for corrective inspection and to
                [1,2,3,4,5,6,7,8,9,10,11,12] for preventive if not defined.
            day_start (int, *optional*): Day on which the inspection should start
                Default to ``None``.
            intervened_wtg (:obj:`int`, *optional*): Number of WTG that are
                intervened in case this inspection occurs.
                Defaults to ``None``.
            intervened_wec (:obj:`int`, *optional*): Number of WEC that are
                intervened in case this inspection occurs.
                Defaults to ``None``.
            intervened_pv (:obj:`int`, *optional*): Number of PV panels that
                are intervened in case this inspection occurs.
                Defaults to ``None``.
            wave_height (:obj:`float`, *optional*): Limit wave height. Defaults to ``None``.
            wave_period (:obj:`float`, *optional*): Limit wave period. Defaults to ``None``.
            wind_speed (:obj:`float`, *optional*): Limit wind speed. Defaults to ``None``.
            wind_speed_hub (:obj:`float`, *optional*): Limit wind speed at hub height. Defaults to ``None``.
            current_speed (:obj:`float`, *optional*): Limit current speed. Defaults to ``None``.
            light (:obj:`bool`, *optional*): If the operation is light. Default to ``False``
            vessel1_id (:obj:`str`): The ID of the main vessel.
            vessel1_qt (:obj:`int`): Number of main vessels available for the inspection.
                Defaults to ``1``.
            vessel2_id (:obj:`str`, *optional*): The ID of the auxiliary vessel.
                Defaults to ``None``.
            vessel2_qt (:obj:`int`): Number of second vessels available for the inspection.
                Defaults to ``1`` if vesse_id not ´´None´´.
            rov_drone (:obj:`str`, *optional*): The ID of the ROV/Drone.
                Defaults to ``None``.
            parts_cost (:obj:`float`, *optional*): Cost of replacement parts.
                Defaults to :obj:`0.0`.
            other_costs (:obj:`float`, *optional*): Other costs (port, cranes,
                insurance, etc.). Defaults to :obj:`0.0`.
            to_group_with: Inspection at site id that can be performed with.
                Its value is ``None`` if not defined.
            to_be_grouped (:obj:`False`): True or False if the inspection can be grouped.
                Its value is ``False`` if not defined.
            n_vessel_main (:obj:`int`): Number of vessels used for the main part of the
                inspections. Its values is ``0`` if not defined.
            n_vessel_last (:obj:`int`): Number of vessels used for the last part of the
                inspections. Its values is ``0`` if not defined.
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

        Raises:
            ValueError: if any of :attr:`months` values is not an integer.
            ValueError: if :attr:`light` is not a boolean value.
        """
        self.id = str(id_).lower()
        self.name = str(name)
        self.overnight = bool(overnight_stay)
        self.periodicity = float(periodicity)
        self.tech_per_device = int(tech_per_device)
        self.dur_per_device = float(dur_per_device)
        self.device_shutdown = bool(device_shutdown)
        self.level = str(level).lower()
        self.months = list(range(1, 13))
        self.day_start = 1
        self.vessel1_id = str(vessel1_id).lower()
        self.vessel1_qt = 1
        self.tech_cost = 0
        self.vessel2_id = None
        self.vessel2_qt = None
        self.rov_drone = None
        self.intervened_wtg = 0
        self.intervened_wec = 0
        self.intervened_pv = 0
        self.hs = None
        self.tp = None
        self.ws = None
        self.ws_hub = None
        self.cs = None
        self.light = None

        self.parts_cost = 0
        self.other_costs = 0

        self.ts_data = None

        self.vessel1 = None
        self.vessel2 = None

        self.to_group_with = None
        self.to_be_grouped = False
        self.double_shift = None


        self.days_main = 0
        self.duration_main = 0
        self.days_last = 0
        self.duration_last = 0
        self.n_vessel_main = 0
        self.n_vessel_last = 0
        self.n_crew_main = 0
        self.n_crew_last = 0
        self.n_dev_done_main_shift = 0
        self.n_dev_done_last_shift = 0

        if tech_cost is not None and tech_cost != 0:
            self.tech_cost = float(tech_cost)
        if months is not None:
            try:
                try: self.months = [int(mnt) for mnt in months.split(',')]
                except AttributeError: self.months = int(months)
            except ValueError:
                _e = 'For inspection %s, "months" must be in the format ' % self.id
                _e += 'of "Month1, Month2, ..." (ex.: "06, 07, 08")'
                logging.error('InspectionSite: '+ _e)
                raise ValueError(_e)
        else:
            # If the months are not defined, all months should be considered
            _w = 'For inspection %s, "months" is not defined. ' % self.id
            _w += 'All months will be considered.'
            logging.warning('InspectionSite: '+ _w)
        if day_start is not None:
            self.day_start = int(day_start)
        if intervened_wtg is not None:
            self.intervened_wtg = int(intervened_wtg)
        if intervened_wec is not None:
            self.intervened_wec = int(intervened_wec)
        if intervened_pv is not None:
            self.intervened_pv = int(intervened_pv)

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
                    e_ = f'InspectionSite: For operation {self.id}, "light" must be a boolean value'
                    logging.error(e_)
                    raise ValueError(_e)
        else:
            self.light = False
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
        if parts_cost is not None:
            self.parts_cost = float(parts_cost)
        if other_costs is not None:
            self.other_costs = float(other_costs)
        if to_group_with is not None:
            if isinstance(to_group_with,str):
                self.to_group_with = str(to_group_with).lower()
            else:
                self.to_group_with = to_group_with

        if to_be_grouped is not None:
            self.to_be_grouped = bool(to_be_grouped)

        if n_vessel_main is not None:
            self.n_vessel_main = n_vessel_main
        if n_vessel_last is not None:
            self.n_vessel_last = n_vessel_last
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
                    e_ = f'InspectionSite: For operation {self.id}, "double_shift" must be a boolean value'
                    logging.error(e_)
                    raise ValueError(_e)

        self._check_attributes()


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
        if isinstance(self.months, int) is True and self.months in range(1,13) is False:
            raise NameError('"months" must be between 1 and 12')
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
        if self.intervened_wtg is not None and self.intervened_wtg < 0:
            raise ValueError('"intervened_wtg" must not be negative')
        if self.intervened_wec is not None and self.intervened_wec < 0:
            raise ValueError('"intervened_wec" must not be negative')
        if self.intervened_pv is not None and self.intervened_pv < 0:
            raise ValueError('"intervened_pv" must not be negative')
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
        if self.parts_cost is not None and self.parts_cost < 0:
            raise ValueError('"parts_cost" must not be negative')
        if self.other_costs is not None and self.other_costs < 0:
            raise ValueError('"other_costs" must not be negative')
        if self.vessel1_qt < 1:
            raise ValueError('"vessel1_qt" must be positive')
        if self.vessel2_id is not None:
            if self.vessel2_qt < 1:
                raise ValueError('"vessel2_qt" must be positive if a "vessel2_id" is defined')


        logging.debug('InspectionSite: inspection %s attributes within ranges and valid.' % self.id)


    def get_inspections_from_yaml(file_path: object) -> list:
        """
        Read a YAML file and extract operations from it.

        Args:
            file_path (:obj:`string`): The path to the YAML file.

        Raises:
            KeyError: if one of the YAML entries does not have all the mandatory keys.

        Return:
            List of :class:`InspectionSite`.
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
                'overnight_stay',
                'periodicity',
                'tech_per_device',
                'dur_per_device',
                'device_shutdown',
                'level',
                'vessel1_id',
        ]
        no_mandatory_keys = [
                'months',
                'day_start',
                'tech_cost',
                'intervened_wtg',
                'intervened_wec',
                'intervened_pv',
                'wave_height',
                'wave_period',
                'wind_speed',
                'wind_speed_hub',
                'current_speed',
                'light',
                'vessel1_qt',
                'vessel2_id',
                'vessel2_qt',
                'rov_drone',
                'parts_cost',
                'other_costs',
                'to_group_with',
                'to_be_grouped',
                'n_vessel_main',
                'n_vessel_last',
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
                _e = '"id", "name", "overnight_stay", "periodicity", '
                _e += '"tech_per_device", "vessel1_id"'
                _e += '"dur_per_device", "device_shutdown" and "level" '
                _e += 'are mandatory keys.'
                logging.error('InspectionSite: ' + _e)
                raise KeyError(_e)

            for key in no_mandatory_keys:
                try:
                    operation[key]
                except KeyError:
                    operation[key] = None

            inspections_list.append(
                InspectionSite(
                    id_=operation["id"],
                    name=operation["name"],
                    overnight_stay=operation["overnight_stay"],
                    periodicity=operation["periodicity"],
                    tech_per_device=operation["tech_per_device"],
                    tech_cost=operation["tech_cost"],
                    dur_per_device=operation["dur_per_device"],
                    device_shutdown=operation["device_shutdown"],
                    level=operation["level"],
                    months=operation["months"],
                    day_start=operation["day_start"],
                    intervened_wtg=operation["intervened_wtg"],
                    intervened_wec=operation["intervened_wec"],
                    intervened_pv=operation["intervened_pv"],
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
                    parts_cost=operation["parts_cost"],
                    other_costs=operation["other_costs"],
                    to_group_with=operation["to_group_with"],
                    to_be_grouped=operation["to_be_grouped"],
                    n_vessel_main=operation["n_vessel_main"],
                    n_vessel_last=operation["n_vessel_last"],
                    double_shift=operation["double_shift"],
                )
            )


        logging.info('InspectionSite: inspections defined based on file "%s"' % file_path)
        return inspections_list


    def assign_shift_attributes(self, data: dict):
        """ Module to assign shift related  attributes to the inspection from a dictionary."""
        self.days_main = data.get('days_main', None) if data.get('days_main', None) is not None else data.get('number_shifts_main', None)
        self.duration_main = data.get('duration_main', None) if data.get('duration_main', None) is not None else data.get('duration_shift_main', None)
        self.days_last = data.get('days_last', None) if data.get('days_last', None) is not None else data.get('number_shifts_last', None)
        self.duration_last = data.get('duration_last', None) if data.get('duration_last', None) is not None else data.get('duration_shift_last', None)
        self.n_vessel_main = data.get('n_vessel_main', None) if data.get('n_vessel_main', None) is not None else data.get('n_vessels_main', None)
        self.n_vessel_last = data.get('n_vessel_last', None) if data.get('n_vessel_last', None) is not None else data.get('n_vessels_last', None)
        self.n_crew_main = data.get('n_crew_main', None)
        self.n_crew_last = data.get('n_crew_last', None)
        self.n_dev_done_main_shift = data.get('n_dev_inspected_main_shift', None)
        self.n_dev_done_last_shift = data.get('n_dev_inspected_last_shift', None)


    def tech_finder(self):
        """Return the type of the farm considered"""
        mapping = {"ofw": "G_wind","owc": "G_wave","opv": "G_pv"}

        for key, value in mapping.items():
            if key in self.id:
                return value
        return None


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
        if self.rov_drone is not None:
            rov_drone = self.rov_drone.id
        vessel2 = self.vessel2_id
        to_group_with = self.to_group_with
        if self.to_group_with is not None and isinstance(self.to_group_with, str) is False:
            if self.to_group_with.rov_drone is not None:
                rov_group_operation = self.to_group_with.rov_drone.id
            else:
                rov_group_operation = None
            to_group_with = {
                    "id": self.to_group_with.id,
                    "dur_per_device": self.to_group_with.dur_per_device,
                    "tech_per_device": self.to_group_with.tech_per_device,
                    "tech_cost": self.to_group_with.tech_cost,
                    "rov": rov_group_operation
            }

        f = open(os.path.join(out_dir, 'attributes.yaml'), 'w')
        yaml=YAML()
        yaml.default_flow_style = None
        yaml.dump({
                "id": self.id,
                "name": self.name,
                "overnight": self.overnight,
                "periodicity": self.periodicity,
                "months": self.months,
                "day_start": self.day_start,
                "tech_per_device": self.tech_per_device,
                "tech_cost": self.tech_cost,
                "dur_per_device": self.dur_per_device,
                "device_shutdown": self.device_shutdown,
                "level": self.level,
                "vessel1": vessel1,
                "vessel2": vessel2,
                "intervened_wtg": self.intervened_wtg,
                "intervened_wec": self.intervened_wec,
                "intervened_pv": self.intervened_pv,
                "hs": self.hs,
                "tp": self.tp,
                "ws": self.ws,
                "ws_hub": self.ws_hub,
                "cs": self.cs,
                "light": self.light,
                "rov_drone": rov_drone,
                "parts_cost": self.parts_cost,
                "other_costs": self.other_costs,
                "to_be_grouped": self.to_be_grouped,
                "to_group_with": to_group_with,
                "n_vessel_main": self.n_vessel_main,
                "n_vessel_last": self.n_vessel_last,
                "days_main": self.days_main,
                "days_last": self.days_last,
                "duration_main": self.duration_main,
                "duration_last": self.duration_last,
                "double_shift": self.double_shift,
        }, f)
        f.close()
