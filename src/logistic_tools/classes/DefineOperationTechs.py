# Import packages
import logging
import os
from ruamel.yaml import YAML
from copy import deepcopy

# Import classes
from logistic_tools.classes.Vessel import Vessel


class Define_operation():

    @staticmethod
    def define_vessels(
            operation,
            file_vessels: str,
            file_fuel_cons: str,
            file_load_factor: str,
            file_fuel_density: str,
            vessels: dict
    ):
        """
        Create Vessel object for the operation called for the operation that correspond to 
            operation.Vessel1 e operation.Vessel2. Update the vessels dictionary if needed

        Args:
            operation: Operation argument. It can be: :class:`OperationInspection`,
                :class:`OperationCorrective` or :class:`OperationTow`
            file_vessels (:obj:`str`): Vessels YAML file location.
            file_fuel_cons (:obj:`str`): YAML file path where vessels consumptions are defined.
            file_load_factor (:obj:`str`): YAML file path where load factors per operation are defined.
            file_fuel_density (:obj:`str`): YAML file path where fuel density per fuel type are defined.
            vessels (:obj:`dict`): Dictionary of vessel_id and Vessel object created

        Raises:
            IndexError: if :attr:`vessel1_id` is not found in
                :attr:`file_vessels` YAML file.
            IndexError: if there is more than 1 vessel with :attr:`vessel1_id`
                in :attr:`file_vessels` YAML file
            IndexError: if :attr:`vessel2_id` is not found in
                :attr:`file_vessels` YAML file.
            IndexError: if there is more than 1 vessel with :attr:`vessel2_id`
                in :attr:`file_vessels` YAML file

        """
        
        vessels_ops = {}

        # Read YAML file
        with open(file_vessels, 'r') as f_yaml:
            yaml = YAML(typ='safe')
            vessels_yaml = yaml.load(f_yaml)

        # All vessels keys to lower case
        vessels_yaml = [
                {key.lower(): val for key, val in vessel.items()}
                for vessel in vessels_yaml
        ]

        if operation.vessel1_id is not None:
            # Get only the vessel1 ID
            id1 = operation.vessel1_id

            vessel_list = []
            for vessel in vessels_yaml:
                if str(vessel["id"].lower()) == str(id1.lower()):
                    vessel_list.append(vessel)

            if len(vessel_list) == 0:
                _e = f'Vessel ID "{operation.vessel1_id}" was not found in "file_vessels" for {operation.id}'
                logging.error('OperationInspection: ' + _e)
                raise IndexError(_e)
            if len(vessel_list) != 1:
                _e = f'For vessel ID "{operation.vessel1_id}" there are more than one vessel in "file_vessels"'
                logging.error('OperationInspection: ' + _e)
                raise IndexError(_e)

            vessel1_keys = vessel_list[0]
            del vessel_list

            for key in [
                    'number_vessels',
                    'speed_towing',
                    'num_berths',
                    'power',
                    'overnight',
                    'mother_vessel',
                    'mobilisation_cost',
                    'mobilisation_time',
                    'fuel_type',
                    'fuel_cons_transit',
                    'fuel_cons_maneuver',
                    'fuel_cons_standby',
                    'annual_contract',
                    'n_ves_annual_contract',
                    'months_contract',
                    'monthly_contract_cost',
                    'n_ves_monthly_contract',
            ]:
                try:
                    vessel1_keys[key]
                except KeyError:
                    vessel1_keys[key] = None

            operation.vessel1 = Vessel(
                    id_=vessel1_keys["id"],
                    type_=vessel1_keys["type"],
                    speed_transit=vessel1_keys["speed_transit"],
                    power=vessel1_keys["power"],
                    daily_charter=vessel1_keys["daily_charter"],
                    annual_contract=vessel1_keys["annual_contract"],
                    n_ves_annual_contract = vessel1_keys['n_ves_annual_contract'],
                    months_contract = vessel1_keys['months_contract'],
                    monthly_contract_cost = vessel1_keys['monthly_contract_cost'],
                    n_ves_monthly_contract = vessel1_keys['n_ves_monthly_contract'],
                    crew_capacity=vessel1_keys["crew_capacity"],
                    overnight=vessel1_keys['overnight'],
                    mother_vessel=vessel1_keys['mother_vessel'],
                    n_vessels=vessel1_keys["number_vessels"],
                    crew_berths=vessel1_keys["num_berths"],
                    mobilisation_cost=vessel1_keys["mobilisation_cost"],
                    mobilisation_time=vessel1_keys["mobilisation_time"],
                    speed_tow=vessel1_keys["speed_towing"],
                    fuel_type=vessel1_keys["fuel_type"],
                    fuel_cons_transit=vessel1_keys["fuel_cons_transit"],
                    fuel_cons_maneuver=vessel1_keys["fuel_cons_maneuver"],
                    fuel_cons_standby=vessel1_keys["fuel_cons_standby"],
                    file_vessels=file_vessels,
                    file_fuel_cons=file_fuel_cons,
                    file_load_factor=file_load_factor,
                    file_fuel_density=file_fuel_density
            )

            vessels_ops[operation.vessel1.id] = operation.vessel1

        if operation.vessel2_id is not None:
            # Get only the vessel2 ID
            id2 = operation.vessel2_id

            vessel_list = []
            for vessel in vessels_yaml:
                if str(vessel["id"].lower()) == str(id2.lower()):
                    vessel_list.append(vessel)

            if len(vessel_list) == 0:
                _e = 'Vessel ID "%s" was not found in "file_vessels"' % operation.vessel2_id
                logging.error(_e)
                raise IndexError(_e)
            if len(vessel_list) != 1:
                _e = 'For vessel ID "%s" there are more than one vessel in "file_vessels"' % operation.vessel2_id
                logging.error(_e)
                raise IndexError(_e)

            vessel2_keys = vessel_list[0]
            del vessel_list

            for key in [
                    'number_vessels',
                    'speed_towing',
                    'power',
                    'annual_contract',
                    'n_ves_annual_contract',
                    'months_contract',
                    'monthly_contract_cost',
                    'n_ves_monthly_contract',
                    'num_berths',
                    'mother_vessel',
                    'daily_charter',
                    'mobilisation_cost',
                    'mobilisation_time',
                    'fuel_type',
                    'fuel_cons_transit',
                    'fuel_cons_maneuver',
                    'fuel_cons_standby'
            ]:
                try:
                    vessel2_keys[key]
                except KeyError:
                    vessel2_keys[key] = None

            operation.vessel2 = Vessel(
                    id_=vessel2_keys["id"],
                    type_=vessel2_keys["type"],
                    speed_transit=vessel2_keys["speed_transit"],
                    power=vessel2_keys["power"],
                    daily_charter=vessel2_keys["daily_charter"],
                    crew_capacity=vessel2_keys["crew_capacity"],
                    annual_contract=vessel2_keys["annual_contract"],
                    n_ves_annual_contract = vessel2_keys['n_ves_annual_contract'],
                    months_contract = vessel2_keys['months_contract'],
                    monthly_contract_cost = vessel2_keys['monthly_contract_cost'],
                    n_ves_monthly_contract = vessel2_keys['n_ves_monthly_contract'],
                    n_vessels=vessel2_keys["number_vessels"],
                    crew_berths=vessel2_keys["num_berths"],
                    overnight=vessel2_keys['overnight'],
                    mother_vessel=vessel2_keys['mother_vessel'],
                    mobilisation_cost=vessel2_keys["mobilisation_cost"],
                    mobilisation_time=vessel2_keys["mobilisation_time"],
                    speed_tow=vessel2_keys["speed_towing"],
                    fuel_type=vessel2_keys["fuel_type"],
                    fuel_cons_transit=vessel2_keys["fuel_cons_transit"],
                    fuel_cons_maneuver=vessel2_keys["fuel_cons_maneuver"],
                    fuel_cons_standby=vessel2_keys["fuel_cons_standby"],
                    file_vessels=file_vessels,
                    file_fuel_cons=file_fuel_cons,
                    file_load_factor=file_load_factor,
                    file_fuel_density=file_fuel_density
            )

            vessels_ops[operation.vessel2.id] = operation.vessel2

        for vessel_id, vessel in vessels_ops.items():
            if vessel_id not in vessels:
                vessels[vessel_id] = vessel
        
    @staticmethod
    def define_rovs(
            operation,
            rovs_drones: list
    ):
        """For an :attr:`operation`, it defines :class:`~logistic_tools.classes.RovDone.RovDrone`
        the respective :attr:`rov_drone`.

        Args:
            operation: Operation argument. It can be: :class:`OperationInspectionSite`,
                :class:`OperationCorrectiveMajor` or :class:`OperationCorrectiveMinor`
            rovs_drones (:obj:`list`): List of :class:`RovDrone`.
        Raises:
            NameError: if operation :attr:`rov_drone` is not found in
                :attr:`rovs_drones` list of rovs and drones.
        """
        rov_drone_found = False
        for rov_drone in rovs_drones:
            if rov_drone.id == operation.rov_drone:
                operation.rov_drone = deepcopy(rov_drone)
                rov_drone_found = True
                break

        if rov_drone_found is False:
            _e = 'For operation "%s", no ROV or Drone ' % operation.id
            _e += 'was found in "rovs_drones" list '
            _e += 'with ID "%s".' % operation.rov_drone
            logging.error('RovDrone: ' + _e)
            raise NameError(_e)
