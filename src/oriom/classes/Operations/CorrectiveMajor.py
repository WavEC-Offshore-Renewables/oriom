# Import packages
import logging
import os
from ruamel.yaml import YAML

from oriom.utils.aux_operation import define_tow_operations


# Import classes
class CorrectiveMajor():
    """
    A class representing a CorrectiveMajor operation with various attributes and methods.

    Note:
        Major corrective operations are defined by activities (**fill the activities sheet**).
        It allows both on-site intervention and tow-to-port intervention.

    Attributes:

        id (:obj:`str`): The unique identifier of the :class:`CorrectiveMajor`.
        name (:obj:`str`): :class:`CorrectiveMajor` short description.
        tow_to_port (:obj:`bool`): This operation requires the device removal
            and redeploy.
        months (:obj:`list`): Months when the operation is preformed.
        tech_required (:obj:`int`): Number of technicians required to preform
            the operation.
        tech_cost (:obj:`float`): The daily cost of each technician [€/day]. Its value
            is ``0`` if not defined.
        op_tow_port (:obj:`str`): ID of the tow-to-port operation. Its value is
            ``None`` if not defined.
        op_tow_site (:obj:`str`): ID of the tow-to-site operation. Its value is
            ``None`` if not defined.
        op_tow_site_port (:obj:`str`): ID of the tow-to-site-port operation. Its value is
            ``None`` if not defined.
        vessel1_id (:obj:`str`): The ID of the main vessel. Its value is
            ``None`` if not defided.
        vessel1_qt (:obj:`int`): The number of the main vessel required. Its value si
            ``None`` if not defined.
        vessel2_id (:obj:`str`): The ID of the auxiliary vessel. Its value is
            ``None`` if not defided.
        vessel2_qt (:obj:`int`): The number of the secondary vessel required. Its value si
            ``None`` if not defined.
        other_costs (:obj:`float`): Other costs (port, cranes, insurance, etc.).
            Its value is :obj:`0.0` if not defided.
        port_costs (:obj:`float`): Daily port costs. Its value is :obj:`0.0` if not defided.
        activities (:class:`~oriom.classes.Activity.Activity`): List of
            :class:`~oriom.classes.Activity.Activity` preformed during
            the logistic operation.
        vessel1 (:class:`~oriom.classes.Vessel.Vessel`): Main vessel
            used in this operation. Its value is ``None`` if not defided.
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
        n_device_at_port(:obj:`int`): Number of devices that can be mantained
            at port simultaneously. Defaults to `None`
        n_device_stored_at_port(:obj:`int`): Number of devices that can be
                stored at port when not in maintenance. Defaults to `None`
    Note:
        When the class is initialized, :func:`_check_attributes` is run.
    """
    def __init__(
            self,
            id_: str,
            name: str,
            tow_to_port: bool,
            tech_required: int,
            months: str=None,
            tech_cost: float=0,
            vessel1_id: str=None,
            vessel1_qt: int=1,
            vessel2_id: str=None,
            vessel2_qt: int=None,
            other_costs: float=0,
            port_costs: float=0,
            towing_ops: list=None,
            rov_drone: str=None
    ):
        """
        Initialize the :class:`CorrectiveMajor` with various attributes and optional parameters.

        Args:
            id_ (:obj:`str`): The unique identifier of the CorrectiveMajor.
            name (:obj:`str`): CorrectiveMajor short description.
            tow_to_port (:obj:`bool`): Indicates if the operation requires device
                removal and redeployment.
            tech_required (:obj:`int`): Number of technicians required to
                preform the operation.
            tech_cost (:obj:`float`,*optional*): The daily cost of each technician[€/day].
                Defaults to ``0``.
            months (:obj:`str`, *optional*): Months when the operation is preformed.
                Defaults to an empty list for corrective operations and to
                [1,2,3,4,5,6,7,8,9,10,11,12] for preventive if not defined.
            vessel1_id (:obj:`str`): The ID of the main vessel.
                Defaults to ``None``.
            vessel2_id (:obj:`str`, *optional*): The ID of the auxiliary vessel.
                Defaults to ``None``.
            vessel1_qt (:obj:`int`): Number of main vessel required.
                Defaults to ``None``.
            vessel2_qt (:obj:`int`): Number of second vessel required.
                Defaults to ``1`` if vesse_id not ´´None´´.
            other_costs (:obj:`float`, *optional*): Other costs (port, cranes,
                insurance, etc.). Defaults to :obj:`0.0`.
            port_costs (:obj:`float`, *optional*): Daily port costs. Defaults to :obj:`0.0`.
            towing_ops (:obj:`list`, *optional*): List of all towing operations.
                Defaults to an empty list.
            rov_drone (:obj:`str`, *optional*): The ID of the ROV/Drone.
                Defaults to ``None``.
        Raises:
            ValueError: if any of :attr:`months` values is not an integer.
        """
        self.id = str(id_).lower()
        self.name = str(name)
        self.tow_to_port = bool(tow_to_port)
        self.tech_required = int(tech_required)

        self.tech_cost = 0
        self.months = list(range(1, 13))
        self.vessel1_id = None
        self.vessel2_id = None
        self.other_costs = 0
        self.port_costs = 0

        self.ts_data = None

        self.activities = None
        self.vessel1 = None
        self.vessel1_qt = None
        self.vessel2 = None
        self.vessel2_qt = None

        self.op_tow_port = None
        self.op_tow_site = None
        self.op_tow_site_port = None

        self.n_device_at_port = None
        self.n_device_stored_at_port = None

        self.failures = None

        self.rov_drone = None

        if tech_cost is not None and tech_cost != 0:
            self.tech_cost = float(tech_cost)
        if months is not None:
            try:
                try: self.months = [int(mnt) for mnt in months.split(',')]
                except: self.months = int(months)                           # TODO: Check which error the "try" resturn and write an exception only for that error
            except ValueError:
                _e = 'For operation %s, "months" must be in the format ' % self.id
                _e += 'of "Month1, Month2, ..." (ex.: "06, 07, 08")'
                logging.error('CorrectiveMajor: '+ _e)
                raise ValueError(_e)
        else:
            # If the months are not defined, all months should be considered
            _w = 'For operation %s, "months" is not defined. ' % self.id
            _w += 'All months will be considered.'
            logging.warning('CorrectiveMajor: '+ _w)

        if vessel1_id is not None:
            self.vessel1_id = str(vessel1_id).lower()
            if vessel1_qt is not None:
                self.vessel1_qt = int(vessel1_qt)
            else:
                self.vessel1_qt = int(1)
        if vessel2_id is not None:
            self.vessel2_id = str(vessel2_id).lower()
            if vessel2_qt is not None:
                self.vessel2_qt = int(vessel2_qt)
            else:
                self.vessel2_qt = int(1)
        if other_costs is not None:
            self.other_costs = float(other_costs)
        if port_costs is not None:
            self.port_costs = float(port_costs)
        if rov_drone is not None:
            self.rov_drone = str(rov_drone).lower()

        self._check_attributes()
        if self.tow_to_port:
            define_tow_operations(self, towing_ops, 'CorrectiveMajor')


    def _check_attributes(self):
        """
        This method validates the attributes of the `CorrectiveMajor` class to ensure they
        have valid values and fall within specified ranges.

        Raises errors if any attribute is outside the specified range.
        """
        if self.tech_required < 1:
            raise ValueError('"tech_required" must be positive')
        if self.tech_cost < 0:
            raise ValueError('"tech_cost" must not be negative')
        if isinstance(self.months, int) is True and self.months in range(1,13) is False:
            raise NameError('"month" must be between 1 and 12')
        if isinstance(self.months, int) is False and all([month in range(1, 13) for month in self.months]) is False:
            raise NameError('"months" must be between 1 and 12')
        if self.other_costs is not None and self.other_costs < 0:
            raise ValueError('"other_costs" must not be negative')
        if self.port_costs is not None and self.port_costs < 0:
            raise ValueError('"port_costs" must not be negative')
        if self.tow_to_port and (self.vessel1_id or self.vessel2_id):
            raise ValueError('Vessel must not be defined if is a port operation. Leave it empty "vessel1_id" and "vessel2_id"')
        if self.vessel1_id is not None:
            if self.vessel1_qt < 1:
                raise ValueError('"vessel1_qt" must be positive if a "vessel1_id" is defined')
        if self.vessel2_id is not None:
            if self.vessel2_qt < 1:
                raise ValueError('"vessel2_qt" must be positive if a "vessel2_id" is defined')
        logging.debug('CorrectiveMajor: operation %s attributes within ranges and valid.' % self.id)


    def get_operations_from_yaml(
            file_path: object,
            towing_operations: list=None
    ) -> list:
        """
        Read a YAML file and extract operations from it.

        Args:
            file_path (:obj:`string`): The path to the YAML file.
            towing_operations (:obj:`list`, *optional*): A list containing two towing operations: tow-to-port and tow-to-site.
                The first item is the tow-to-port operation and the second item is the tow-to-site operation.
                Defaults to None if not provided.

        Raises:
            KeyError: if one of the YAML entries does not have all the mandatory keys.

        Return:
            List of :class:`CorrectiveMajor`.
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
                'tow_to_port',
                'tech_required'
        ]
        no_mandatory_keys = [
                'tech_cost',
                'vessel1_id',
                'vessel2_id',
                'vessel1_qt',
                'vessel2_qt',
                'rov_drone',
                'port_costs',
                'other_costs'
        ]

        operations_list = []
        for operation in operations_yaml:
            if any([
                    key not in operation.keys()
                    for key in keys_mandatory
            ]) is True:
                _e = '"id", "name", "tow_to_port", '
                _e += 'and "tech_required"'
                _e += 'are mandatory keys.'
                logging.error('CorrectiveMajor: ' + _e)
                raise KeyError(_e)

            for key in no_mandatory_keys:
                try:
                    operation[key]
                except KeyError:
                    operation[key] = None

            operations_list.append(
                CorrectiveMajor(
                    id_=operation["id"],
                    name=operation["name"],
                    tow_to_port=operation["tow_to_port"],
                    tech_required=operation["tech_required"],
                    tech_cost=operation["tech_cost"],
                    vessel1_id=operation["vessel1_id"],
                    vessel1_qt=operation["vessel1_qt"],
                    vessel2_id=operation["vessel2_id"],
                    vessel2_qt=operation["vessel2_qt"],
                    rov_drone=operation["rov_drone"],
                    port_costs=operation["port_costs"],
                    other_costs=operation["other_costs"],
                    towing_ops=towing_operations
                )
            )

        logging.info('CorrectiveMajor: operations defined based on file "%s"' % file_path)
        return operations_list


    def define_months_operations(self):
        """
        Define the months in which corrective operations may take place based on operation failures.
        If any failure needs immediate correction, all months are considered.
        If a failure is to be corrected in a specific month, that month is included.
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
        activities = [activity.id for activity in self.activities]
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
                "tow_to_port": self.tow_to_port,
                "months": self.months,
                "tech_required": self.tech_required,
                "op_tow_port": self.op_tow_port,
                "op_tow_site": self.op_tow_site,
                "vessel1": vessel1,
                "vessel2": vessel2,
                "other_costs": self.other_costs,
                "port_costs": self.port_costs,
                "activities": activities,
                "rov_drone": rov_drone,
                "failures": [failure.id for failure in getattr(self, 'failures', []) or []]
        }, f)
        f.close()