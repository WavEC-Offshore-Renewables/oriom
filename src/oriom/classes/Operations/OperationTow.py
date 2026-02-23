# Import packages
import pandas as pd
import logging
import os
from ruamel.yaml import YAML


# Import classes
class OperationTow():
    """
    A class representing a OperationTow operation with various attributes and methods.

    Note:
        **Activities sheet to be filled**

        Here it is only to defined per technology:
            - Transiting to site to remove the device from site and tow it back to port
            - Tow the device to site to redeploy and transit back to port
            - Tow the device to site to redeploy and remove another device to tow it back to port

    Attributes:
        id (:obj:`str`): The unique identifier of the :class:`OperationTow`.
        name (:obj:`str`): :class:`OperationTow` short description.
        tech_required (:obj:`int`): Number of technicians required to preform
            the operation.
        tech_cost (:obj:`float`): The daily cost of each technician [€/day].
            Its value is ``0`` if not defined.
        vessel1_id (:obj:`str`): The ID of the main vessel.
        vessel1_qt (:obj:`int`): Number of main vessel. Its value is
            ``1`` if not defined.
        vessel2_id (:obj:`str`): The ID of the auxiliary vessel. Its value is
            ``None`` if not defided.
        vessel2_qt (:obj:`int`): Number of secondary vessel. Its value is
            ``1`` if not defined.
        other_costs (:obj:`float`): Other costs (port, cranes, insurance, etc.).
            Its value is :obj:`0.0` if not defided.
        addition_op_tow (:obj: CorrectiveMajor): Major operation object to conduct
            before or after the towing operation. Its value is ``None`` if not defided
        activities (:obj:`list`): List of
            :class:`~oriom.classes.Activity.Activity` preformed during
            the logistic operation.
        vessel1 (:class:`~oriom.classes.Vessel.Vessel`): Main vessel
            used in this operation. Its value is ``None`` if not defided.
        vessel2 (:class:`~oriom.classes.Vessel.Vessel`): Auxiliary
            vessel used in this operation. Its value is ``None`` if not
            defided.
        ts_data (:class:`~oriom.classes.OperationTimeSeriesData.OperationTimeSeriesData`):
            Timeseries data of the operation. Its value is ``None`` if not defided
        tow_operation (:obj:`bool`): Define if is a towing opreation. Default to ``True``


    Note:
        When the class is initialized, :func:`_check_attributes` is run.
    """
    def __init__(
            self,
            id_: str,
            name: str,
            tech_required: int,
            tech_cost: float,
            vessel1_id: str,
            vessel1_qt: int=1,
            vessel2_id: str=None,
            vessel2_qt: int=None,
            addition_op_tow: str = None,
            other_costs: float=0
    ):
        """Initializes :class:`OperationTow` with various attributes and optional parameters.

        Args:
            id_ (:obj:`str`): The unique identifier of the OperationTow.
            name (:obj:`str`): OperationTow short description.
            tech_required (:obj:`int`): Number of technicians required to
                preform the operation.
            vessel1_id (:obj:`str`): The ID of the main vessel.
            tech_cost (:obj:`float`,*optional*): The daily cost of each technician[€/day].
                Defaults to ``0``.
            addition_op_tow (:obj:`str`, *optional*): Major_operation.id object to conduct
                before the towing opeartion. Default to ``None``.
            vessel2_id (:obj:`str`, *optional*): The ID of the auxiliary vessel.
                Defaults to ``None``.
            vessel1_qt (:obj:`int`): Number of main vessel.
                Defaults to ``1``.
            vessel2_qt (:obj:`int`): Number of second vessel.
                Defaults to ``1`` if vesse_id not ´´None´´.
            other_costs (:obj:`float`, *optional*): Other costs (port, cranes,
                insurance, etc.). Defaults to :obj:`0.0`.
        """
        self.id = str(id_).lower()
        self.name = str(name)
        self.tech_required = int(tech_required)
        self.vessel1_id = str(vessel1_id)

        self.tech_cost = 0
        self.vessel2_id = None
        self.vessel1_qt = 1
        self.vessel2_qt = None
        self.other_costs = 0
        self.addition_op_tow = None

        self.activities = None
        self.vessel1 = None
        self.vessel2 = None

        self.ts_data = None
        self.tow_operation = True

        if tech_cost is not None and tech_cost !=0:
            self.tech_cost = float(tech_cost)
        if vessel2_id is not None:
            self.vessel2_id = str(vessel2_id).lower()
            if vessel2_qt is not None:
                self.vessel2_qt = int(vessel2_qt)
            else:
                self.vessel2_qt = int(1)
        if vessel1_qt is not None:
            self.vessel1_qt = int(vessel1_qt)
        if other_costs is not None:
            self.other_costs = float(other_costs)
        if addition_op_tow is not None:
            self.addition_op_tow = str(addition_op_tow).lower()

        self._check_attributes()
        

    def _check_attributes(self):
        """
        This method validates the attributes of the `CorrectiveMajor` class to ensure they
        have valid values and fall within specified ranges.

        Raises errors if any attribute is outside the specified range.
        """
        if self.id[0:3] not in ['oce','ofw','owc','opv']:
            raise ValueError('"prefix not recognized"')
        if self.tech_required < 1:
            raise ValueError('"tech_required" must be positive')
        if self.tech_cost < 0:
            raise ValueError('"tech_cost" must not be negative')
        if self.other_costs is not None and self.other_costs < 0:
            raise ValueError('"other_costs" must not be negative')
        if self.vessel1_qt < 1:
            raise ValueError('"vessel1_qt" must be positive')
        if self.vessel2_id is not None:
            if self.vessel2_qt < 1:
                raise ValueError('"vessel2_qt" must be positive if a "vessel2_id" is defined')

        logging.debug('OperationTow: operation %s attributes within ranges and valid.' % self.id)


    def get_operations_from_yaml(file_path: str) -> list:
        """
        Read a YAML file and extract operations from it.

        Args:
            file_path (:obj:`string`): The path to the YAML file.
        Raises:
            KeyError: if one of the YAML entries does not have all the mandatory keys.
        Return:
            List of :class:`OperationTow`.
        """

        # Gets operations from a YAML file
        with open(file_path, "r") as f_yaml:
            yaml = YAML(typ="safe")
            operations_yaml = yaml.load(f_yaml)

        # All operations keys to lower case
        operations_yaml = [
                {key.lower(): val for key, val in op.items()}
                for op in operations_yaml
        ]

        keys_mandatory = [
                'id',
                'name',
                'tech_required',
                'tech_cost',
                'vessel1_id'
        ]
        no_mandatory_keys = [
                'vessel2_id',
                'vessel1_qt',
                'vessel2_qt',
                'other_costs',
                'addition_op_tow'
        ]

        operations_list = []
        for operation in operations_yaml:
            if any([
                    key not in operation.keys()
                    for key in keys_mandatory
            ]) is True:
                _e = '"id", "name" and "tech_required", '
                _e += '"tech_cost" and "vessel1_id" are '
                _e += 'mandatory keys.'
                logging.error('OperationTow: ' + _e)
                raise KeyError(_e)

            for key in no_mandatory_keys:
                try:
                    operation[key]
                except KeyError:
                    operation[key] = None

            operations_list.append(
                OperationTow(
                    id_=operation["id"],
                    name=operation["name"],
                    tech_required=operation["tech_required"],
                    tech_cost=operation["tech_cost"],
                    vessel1_id=operation["vessel1_id"],
                    vessel1_qt=operation["vessel1_qt"],
                    vessel2_id=operation["vessel2_id"],
                    vessel2_qt=operation["vessel2_qt"],
                    addition_op_tow=operation["addition_op_tow"],
                    other_costs=operation["other_costs"]
                )
            )

        logging.info('OperationTow: operations defined based on file "%s"' % file_path)
        return operations_list


    def define_previous_op_tow(
            self,
            operations_corr_major: list
    ):
        """Assign an operation if a previous operation is required with towing operation"""

        op_found = False
        for op in operations_corr_major:
            if op.id == self.addition_op_tow:
                self.addition_op_tow = op
                op_found = True
                break
        if not op_found:
            raise ValueError(f"OperationTow: addition_op_tow {self.addition_op_tow} not found in CorrectiveMajor")


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

        f = open(os.path.join(out_dir, 'attributes.yaml'), 'w')
        yaml=YAML()
        yaml.default_flow_style = None
        yaml.dump({
                "id": self.id,
                "name": self.name,
                "tech_required": self.tech_required,
                "tech_cost": self.tech_cost,
                "vessel1": vessel1,
                "vessel2": vessel2,
                "other_costs": self.other_costs,
                "addition_op_tow": getattr(self.addition_op_tow, 'id', None),
                "activities": activities
        }, f)
        f.close()
