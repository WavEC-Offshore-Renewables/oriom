
# Import packages
import pandas as pd
import os
import logging
from ruamel.yaml import YAML
from distutils.util import strtobool


class Vessel():
    """Vessel class.

    Attributes:
        id (:obj:`str`): The vessel unique identifier.
        type (:obj:`str`): Vessel type.
        speed_transit (:obj:`float`): Vessel transit speed, in m/s.
        charter (:obj:`float`): Vessel daily charter rate, in €/day.
        mother_vessel (bool): boolean that define a mother vessel.
        annual_contract (:obj:`float`): Long term contract cost.
            Defaults to ``0``.
        speed_tow (:obj:`float`): Vessel tow speed, in m/s. Defaults to ``0.0``.
        crew_capacity (:obj:`int`): Maximum number of crew members.
        overnight (:obj:`bool`): True if the vessel can stay overnight.
        mobilisation_cost (:obj:`float`): Vessel mobilisation cost, in €.
            Defaults to ``0``
        mobilisation_time (:obj:`int`): Vessel mobilisation time, in h.
            Defaults to ``0``.
        n_vessels (:obj:`int`): Number of similar vessels.
            Defaults to ``1``.
        crew_berths (:obj:`int`): Maximum number of crew members overnight.
            Defaults to ``0``.
        fuel_type (:obj:`str`): Vessel fuel type. Defaults to ``None``.
        power (:obj:`float`): Vessel installed power (in kW).
            Defaults to ``None``.
        density (:obj:`int`): Density of the fuel type.
            Defaults to ``None``.
        fuel_cons_transit (:obj:`float`): Vessel fuel
            consumption during transit. Defaults to ``None``.
        fuel_cons_maneuver (:obj:`float`): Vessel fuel
            consumption during maneuver. Defaults to ``None``.
        fuel_cons_standby (:obj:`float`): Vessel fuel
            consumption when standing-by. Defaults to ``None``.
        file_vessels (:obj:`str`): Filepath to the YAML
            file containing the vessel data. Defaults to ``None``.
        file_fuel_cons (:obj:`str`): Name of the YAML file containing
            vessel fuel consumption per vessel type. Defaults to ``None``.
        file_load_factor (:obj:`str`): Name of the YAML file containing
            vessels load factor per operation. Defaults to ``None``.
        file_fuel_density (:obj:`str`): Name of the YAML file containing
            fuel densities per fuel type. Defaults to ``None``.
        vessel_cost (:class:`~oriom.classes.Vessels_costs.Vessels_costs`): Cost
            associated to the vessel use. Defaults to ``None``.


    Note:
        When the class is initialized, :func:`_check_attributes` is run.

    Example:
        >>> vessel = Vessel(
        >>>         id_='V001',
        >>>         type_='CTV',
        >>>         speed_transit=3,
        >>>         daily_charter=1000,
        >>>         overnight=False,
        >>>         annual_contract=900000,
        >>>         mobilisation_time=336,
        >>>         mobilisation_cost=10000,
        >>>         crew_capacity=6,
        >>>         power=300,
        >>>         file_vessels=file_vessels,
        >>>         file_fuel_cons=file_fuel_cons,
        >>>         file_load_factor=file_load_factor,
        >>>         file_fuel_density=file_fuel_density
        >>> )
    """
    def __init__(
            self,
            id_: str,
            type_: str,
            speed_transit: float,
            crew_capacity: int,
            overnight: bool,
            n_vessels: int=1,
            crew_berths: int=None,
            daily_charter: float=None,
            mother_vessel: bool = False,
            annual_contract: float=None,
            n_ves_annual_contract: int = 0,
            months_contract: list = [],
            monthly_contract_cost: float = 0,
            n_ves_monthly_contract: int = 0,
            mobilisation_cost: float=None,
            mobilisation_time: int=None,
            power: float=None,
            speed_tow: float=None,
            fuel_type: str=None,
            density: float=None,
            fuel_cons_transit: float=None,  # Fuel type and fuel cons are need OR File consumption path that contains this
            fuel_cons_maneuver: float=None,
            fuel_cons_standby: float=None,
            file_vessels: str=None,
            file_fuel_cons: str=None,
            file_load_factor: str=None,
            file_fuel_density: str=None
    ):
        """Initializes :class:`Vessel` class.

        Args:
            id_ (:obj:`str`): The vessel unique identifier.
            type_ (:obj:`str`): Vessel type.
            speed_transit (:obj:`float`): Vessel transit speed (in m/s).
            power (:obj:`float`): Vessel installed power (in kW).
            crew_capacity (:obj:`int`): Maximum size of crew for daily operations.
            overnight (:obj:`bool`): True if the vessel can stay overnight.
            n_vessels (:obj:`int`,*optional*): Number of similar vessels.
                Defaults to ``1``.
            crew_berths (:obj:`int`,*optional*): Maximum size of crew for overnight operations.
                Defaults to ``0``.
            daily_charter (:obj:`float`, *optional*): Vessel daily charter
                rate (in €/day). Defaults to ``0``.
            mother_vessel (bool): boolean that define a mother vessel.
                Defaults to ``False``.
            annual_contract (:obj:`float`, *optional*): Vessel annual contract cost (in €/year).
                Defaults to ``0``.
            n_ves_annual_contract (: int  *optional*): Number of vessel that are yearly contracted.
                Defaults to ``0``.
            months_contract (: list  *optional*): List of months on which the monthly contract are applied.
                Default to ``[]``.
            monthly_contract_cost (: float  *optional*): Monthly cost of the vessel contracted for 1 month.
                Defaults to ``0``.
            n_ves_monthly_contract (: int  *optional*): Number of vessel that are monthly contracted.
                Defaults to ``0``.
            mobilisation_time (:obj:`int`,*optional*): Vessel mobilisation time, in h.
                Defaults to ``0``.
            mobilisation_cost (:obj:`float`,*optional*): Vessel mobilisation cost (in €).
                Defaults to ``0``.
            speed_tow (:obj:`float`, *optional*): Vessel tow speed (in m/s).
                Defaults to ``None``.
            fuel_type (:obj:`str`, *optional*): Vessel fuel type.
                Defaults to ``None``.
            density (:obj:`int`,*optional*): Density of the fuel type (in kg/m^3).
                Defaults to ``None``.
            fuel_cons_transit (:obj:`float`, *optional*): Vessel fuel
                consumption during transit. Defaults to ``None``.
            fuel_cons_maneuver (:obj:`float`, *optional*): Vessel fuel
                consumption during maneuver. Defaults to ``None``.
            fuel_cons_standby (:obj:`float`, *optional*): Vessel fuel
                consumption when standing-by. Defaults to ``None``.
            file_vessels (:obj:`str`, *optional*): Filepath to the YAML
                file containing the vessel data. Defaults to ``None``.
            file_fuel_cons (:obj:`str`, *optional*): Name of the YAML file
                containing vessel fuel consumption per vessel type.
                Defaults to ``None``.
            file_load_factor (:obj:`str`, *optional*): Name of the YAML
                file containing vessels load factor per operation.
                Defaults to ``None``.
            file_fuel_density (:obj:`str`, *optional*): Name of the YAML
                file containing fuel densities per fuel type.
                Defaults to ``None``.
        """
        self.id = str(id_).lower()
        self.type = str(type_).lower()
        self.speed_transit = float(speed_transit)
        self.crew_capacity = int(crew_capacity)
        self.overnight = bool(overnight)
        self.mother_vessel = False

        if mother_vessel is not None:
            try:
                if isinstance(mother_vessel, bool):
                    self.mother_vessel = mother_vessel
                elif mother_vessel in (1, 1.0):
                    self.mother_vessel = True
                elif mother_vessel in (0, 0.0):
                    self.mother_vessel = False
                else:
                    self.mother_vessel = bool(strtobool(str(mother_vessel)))
            except (ValueError, AttributeError):
                msg = f'Vessel: For {self.id}, "mother_vessel" must be a boolean-equivalent value (true/false, yes/no, 1/0)'
                logging.error(msg)
                raise ValueError(msg)
        try:
            self.n_vessels = int(n_vessels)
        except TypeError:
            # n_vessels is None
            self.n_vessels = 1
            _w = 'Vessel: vessel %s number of vessels not defined. ' % self.id
            _w += 'Defaults to 1.'
            logging.debug(_w)
        try:
            self.crew_berths = int(crew_berths)
        except TypeError:
            # crew_berths is None
            self.crew_berths = 0
            _w = 'Vessel: vessel %s number of berths not defined. ' % self.id
            _w += 'Defaults to 0.'
            logging.debug(_w)
        except ValueError:
            if crew_berths.lower() != 'na':
                _e = 'Vessel: vessel %s number of berths could not ' % self.id
                _e += 'be converted to an integer.'
                logging.error(_e)
                raise ValueError(_e)
            # crew_berths is NA
            self.crew_berths = 0
            _w = 'Vessel: vessel %s number of berths not defined. ' % self.id
            _w += 'Defaults to 0.'
            logging.debug(_w)
        try:
            self.charter = float(daily_charter)
        except TypeError:
            # daily_charter is None
            self.charter = 0
            _w = 'Vessel: vessel %s daily charter not defined. ' % self.id
            _w = 'Defaults to 0.'
            logging.debug(_w)
        try:
            self.n_ves_annual_contract = int(n_ves_annual_contract)
        except TypeError:
            # annual_contract is None
            self.n_ves_annual_contract = 0
            _w = 'Vessel: vessel %s number annual contract not defined. ' % self.id
            _w = 'Defaults to 0.'
            logging.debug(_w)
        if months_contract is not None:
            try:
                if isinstance(months_contract, list):
                    self.months_contract = [int(m) for m in months_contract]
                elif isinstance(months_contract, str):
                    self.months_contract = [int(m.strip()) for m in months_contract.split(',')]
                else:
                    self.months_contract = [int(months_contract)]
                if any(m < 1 or m > 12 for m in self.months_contract):
                    raise ValueError(f'Invalid month values in {self.months_contract}. Must be between 1 and 12.')

            except (ValueError, TypeError) as e:
                _e = f'For Vessel {self.id}, "months_contract" must be a list or a comma-separated string (e.g. "06, 07")'
                raise ValueError(_e) from e
        else:
            self.months_contract = []
        try:
            self.monthly_contract_cost = float(monthly_contract_cost)
        except TypeError:
            # annual_contract is None
            self.monthly_contract_cost = 0
            _w = 'Vessel: vessel %s monthly contract cost not defined. ' % self.id
            _w = 'Defaults to 0.'
            logging.debug(_w)
        try:
            self.n_ves_monthly_contract = int(n_ves_monthly_contract)
        except TypeError:
            # annual_contract is None
            self.n_ves_monthly_contract = 0
            _w = 'Vessel: vessel %s number monthly contract not defined. ' % self.id
            _w = 'Defaults to 0.'
            logging.debug(_w)
        try:
            self.annual_contract = float(annual_contract)
        except TypeError:
            # annual_contract is None
            self.annual_contract = 0
            _w = 'Vessel: vessel %s annual contract cost not defined. ' % self.id
            _w = 'Defaults to 0.'
            logging.debug(_w)
        try:
            self.mobilisation_time = int(mobilisation_time)
        except TypeError:
            # mobilisation time is None
            self.mobilisation_time = 0
            _w = 'Vessel: vessel %s mobilisation time not defined. ' % self.id
            _w = 'Defaults to 0.'
            logging.debug(_w)
        try:
            self.mobilisation_cost = float(mobilisation_cost)
        except TypeError:
            # mobilisation_cost is None
            self.mobilisation_cost = 0.0
            _w = 'Vessel: vessel %s mobilisation cost not defined. ' % self.id
            _w += 'Defaults to 0.0.'
            logging.debug(_w)
        try:
            self.speed_tow = float(speed_tow)
        except TypeError:
            # speed_tow is None
            self.speed_tow = None
            logging.debug('Vessel: vessel %s tow speed not defined' % self.id)

        self.fuel_type = fuel_type

        try:
            self.power = float(power)
        except TypeError:
            # power is None
            self.power = None
            logging.debug('Vessel: vessel %s power not defined' % self.id)

        try:
            self.fuel_cons_transit = float(fuel_cons_transit)
        except TypeError:
            # fuel_cons_transit is None
            self.fuel_cons_transit = None
            logging.debug('Vessel: vessel %s fuel consumption in transit not defined' % self.id)

        try:
            self.fuel_cons_maneuver = float(fuel_cons_maneuver)
        except TypeError:
            # fuel_cons_maneuver is None
            self.fuel_cons_maneuver = None
            logging.debug('Vessel: vessel %s fuel consumption in maneuver not defined' % self.id)

        try:
            self.fuel_cons_standby = float(fuel_cons_standby)
        except TypeError:
            # fuel_cons_standby is None
            self.fuel_cons_standby = None
            logging.debug('Vessel: vessel %s fuel consumption in stand-by not defined' % self.id)

        self.file_vessels = str(file_vessels)
        self.file_fuel_cons = str(file_fuel_cons)
        self.file_load_factor = str(file_load_factor)
        self.file_fuel_density = str(file_fuel_density)

        if self.power is None:
            self._get_vessel_average_power()

        if self.fuel_type is None:
            self._get_vessel_fuel_type()
        else:
            self.fuel_type = str(fuel_type).lower()

        if density is None:
            self.density = self._get_fuel_density()
        else:
            self.density = float(density)

        if self.fuel_cons_transit is None:
            self.fuel_cons_transit = self._calc_fuel_consumption('transit')

        if self.fuel_cons_maneuver is None:
            # Define fuel consumption during maneuver per type of vessel
            self.fuel_cons_maneuver = self._calc_fuel_consumption('maneuver')

        if self.fuel_cons_standby is None:
            # Define fuel consumption during standby per type of vessel
            self.fuel_cons_standby = self._calc_fuel_consumption('standby')

        self._check_attributes()

        self.vessel_cost = None


    def _check_attributes(self):
        """Validates :class:`Vessel` class attributes ranges."""
        if self.speed_transit < 0:
            raise ValueError('"speed_transit" must not be negative')
        if self.charter < 0:
            raise ValueError('"daily_charter" must not be negative')
        if self.annual_contract < 0:
            raise ValueError('"annual_contract" must not be negative')
        if self.n_ves_annual_contract < 0:
            raise ValueError('"n_ves_annual_contract" must not be negative')
        if not all(month in range(1, 13) for month in self.months_contract):
            raise ValueError('"months_contract" must be between 1 and 12')
        if self.monthly_contract_cost < 0:
            raise ValueError('"monthly_contract_cost" must not be negative')
        if self.n_ves_monthly_contract < 0:
            raise ValueError('"n_ves_monthly_contract" must not be negative')
        if self.crew_capacity < 1:
            raise ValueError('"crew_capacity" must be greater or equal to 1')
        if self.overnight != False and self.overnight != True:
            raise ValueError('"overnight" must be a boolean')
        if self.mother_vessel != False and self.mother_vessel != True:
            raise ValueError('"mother_vessel" must be a boolean')
        if self.n_vessels < 1:
            raise ValueError('"n_vessels" must be greater or equal to 1')
        if self.crew_berths < 0:
            raise ValueError('"crew_berths" must not be negative')
        if self.mobilisation_time != 0 and self.mobilisation_cost == 0:
            raise ValueError('"mobilisation_time" defined and "mobilisation_cost" not defined')
        if self.mobilisation_cost != 0 and self.mobilisation_time == 0:
            raise ValueError('"mobilisation_cost" defined and "mobilisation_time" not defined')
        if self.mobilisation_cost < 0:
            raise ValueError('"mobilisation_cost" must not be negative')
        if self.power is not None and self.power <= 0:
            raise ValueError('"power" must not be negative')
        if self.density < 0:
            raise ValueError('"density" must not be negative')
        if self.speed_tow is not None and self.speed_tow <= 0:
            raise ValueError('"speed_tow" must be positive')
        if self.fuel_cons_transit < 0:
            raise ValueError('"fuel_cons_transit" must not be negative')
        if self.fuel_cons_maneuver < 0:
            raise ValueError('"fuel_cons_maneuver" must not be negative')
        if self.fuel_cons_standby < 0:
            raise ValueError('"fuel_cons_standby" must not be negative')
        logging.debug('Vessel: vessel %s attributes within ranges and valid.' % self.id)


    def _get_vessel_average_power(self):
        """Based on :class:`Vessel` class attribuites, gets the average rated power of this
        Vessel.

        Raises:
            ValueError: if :attr:`file_vessels` or :attr:`file_fuel_cons`
                are not defined.
            FileNotFoundError: if :attr:`file_fuel_cons` is not found in
                :attr:`file_vessels`.
            LookupError: if multiple vessels of the same type are found in
                the YAML file.
            LookupError: if no vessel of :attr:`type` is found in the
                YAML file.
        """
        if self.file_fuel_cons == 'None':
            _e = 'If "power" is not defined, '
            _e += 'the parameter "file_fuel_cons" must be provided.'
            logging.error('Vessel: ' + _e)
            raise ValueError(_e)
        try:
            # Read YAML file
            f_yaml = open(os.path.join(self.file_fuel_cons), 'r')
            yaml = YAML(typ='safe')
            inputs_yaml = yaml.load(f_yaml)
            f_yaml.close()
        except FileNotFoundError:
            _e = 'file_fuel_cons: %s not found.' % self.file_fuel_cons
            logging.error('Vessel: ' + _e)
            raise FileNotFoundError(_e)

        vessel_list = []
        for vessel in inputs_yaml:
            if str(vessel["vessel"].lower()) == self.type:
                vessel_list.append(vessel)

        if len(vessel_list) > 1:
            _e = 'More than 1 vessel of type %s found.' % self.type
            logging.error('Vessel: ' + _e)
            raise LookupError(_e)
        elif len(vessel_list) < 1:
            _e = 'No vessels of type %s found.' % self.type
            logging.error('Vessel: ' + _e)
            raise LookupError(_e)
        vessel_keys = vessel_list[0]
        self.power = float(vessel_keys["rated power"])
        logging.info('Vessel: vessel %s power assumed as %.1f kW' % (self.id, self.power))

    def _get_vessel_fuel_type(self):
        """Fetches the fuel type for a given :class:`Vessel` based on :attr:`file_vessels`
        and :attr:`file_fuel_cons` attributes and defines it as :attr:`fuel_type`.
        """
        if self.file_fuel_cons == 'None':
            _e = 'If "fuel_type" is not defined, '
            _e += 'the parameter "file_fuel_cons" must be provided.'
            logging.error('Vessel: ' + _e)
            raise ValueError(_e)
        try:
            # Read YAML file
            f_yaml = open(os.path.join(self.file_fuel_cons), 'r')
            yaml = YAML(typ='safe')
            inputs_yaml = yaml.load(f_yaml)
            f_yaml.close()
        except FileNotFoundError:
            _e = 'file_fuel_cons: %s not found.' % self.file_fuel_cons
            logging.error('Vessel: ' + _e)
            raise FileNotFoundError(_e)

        vessel_list = []
        for vessel in inputs_yaml:
            if str(vessel["vessel"].lower()) == self.type:
                vessel_list.append(vessel)

        if len(vessel_list) > 1:
            _e = 'More than 1 vessel of type %s found.' % self.type
            logging.error('Vessel: ' + _e)
            raise LookupError(_e)
        elif len(vessel_list) < 1:
            _e = 'No vessels of type %s found.' % self.type
            logging.error('Vessel: ' + _e)
            raise LookupError(_e)
        vessel_keys = vessel_list[0]
        self.fuel_type = str(vessel_keys["fuel type"]).lower()
        logging.info('Vessel: vessel %s fuel type defined as "%s"' % (self.id, self.fuel_type))

    def _get_fuel_density(self)->float:
        """Fetches the density of the fuel for a given :class:`Vessel` based on :attr:`file_vessels`
        and :attr:`file_fuel_density` attributes and defines it as :attr:`density`.
        """
        if self.file_fuel_density == None:
            _e = '"file_fuel_density" must be provided'
            logging.error('Vessel: ' + _e)
            raise ValueError(_e)
        try:
            # Read YAML file
            f_yaml = open(os.path.join(self.file_fuel_density), 'r')
            yaml = YAML(typ='safe')
            inputs_yaml = yaml.load(f_yaml)
            f_yaml.close()
        except FileNotFoundError:
            _e = 'file_fuel_density "%s" not found.' % self.file_fuel_density
            logging.error('Vessel: ' + _e)
            raise FileNotFoundError(_e)

        fuel_list = []
        for fuel in inputs_yaml:
            if str(fuel["fuel"].lower()) == self.fuel_type.lower():
                fuel_list.append(fuel)

        ### condition if density is None
        if len(fuel_list) > 1:
            _e = 'More than 1 fuel of type "%s" found.' % self.fuel_type
            logging.error('Vessel: ' + _e)
            raise LookupError(_e)
        elif len(fuel_list) < 1:
            _e = 'No fuel of type "%s" found.' % self.fuel_type
            logging.error('Vessel: ' + _e)
            raise LookupError(_e)

        fuel_keys = fuel_list[0]
        density = float(fuel_keys["density"])

        return density

    def _calc_fuel_consumption(self, operation: str, sfoc=210)->float:
        """Calculates the fuel consumption rate [l/h] for a given vessel and operation type,
        based on its fuel type and engine rated power.

        Args:
            operation (:obj:`str`): ID of the operation
            sfoc: Bu default ``210``
        Returns:
            Fuel consumption :obj:`float`
        """
        if (
                self.file_vessels == 'None' or
                self.file_fuel_cons == 'None' or
                self.file_fuel_density == 'None'
        ):
            _e = 'If "fuel_type" is not defined, '
            _e += 'the parameters "file_vessels", "file_fuel_cons" '
            _e += 'and "file_fuel_density" must be provided.'
            logging.error('Vessel: ' + _e)
            raise ValueError(_e)
        try:
            # Read YAML file
            f_yaml = open(os.path.join(self.file_fuel_density), 'r')
            yaml = YAML(typ='safe')
            inputs_yaml = yaml.load(f_yaml)
            f_yaml.close()
        except FileNotFoundError:
            _e = 'file_fuel_density "%s" not found.' % self.file_fuel_density
            logging.error('Vessel: ' + _e)
            raise FileNotFoundError(_e)

        fuels_list = []
        for fuel in inputs_yaml:
            if str(fuel["fuel"].lower()) == self.fuel_type:
                fuels_list.append(fuel)

        if len(fuels_list) > 1:
            _e = 'More than 1 fuel of type "%s" found.' % self.fuel_type
            logging.error('Vessel: ' + _e)
            raise LookupError(_e)
        elif len(fuels_list) < 1:
            _e = 'No fuel of type "%s" found.' % self.fuel_type
            logging.error('Vessel: ' + _e)
            raise LookupError(_e)

        fuel_keys = fuels_list[0]
        density = float(fuel_keys["density"])

        try:
            # Read YAML file
            f_yaml = open(os.path.join(self.file_load_factor), 'r')
            yaml = YAML(typ='safe')
            inputs_yaml = yaml.load(f_yaml)
            f_yaml.close()
        except FileNotFoundError:
            _e = 'file_load_factor "%s" not found' % self.file_load_factor
            logging.error('Vessel: ' + _e)
            raise FileNotFoundError(_e)

        loads_list = []
        for load in inputs_yaml:
            if str(load["operation"].lower()) == operation.lower():
                loads_list.append(load)

        if len(loads_list) > 1:
            _e = 'More than 1 operation of type "%s" found.' % operation
            logging('Vessel: ' + _e)
            raise LookupError(_e)
        elif len(loads_list) < 1:
            _e = 'No operation of type "%s" found.' % operation
            logging('Vessel: ' + _e)
            raise LookupError(_e)

        load_keys = loads_list[0]
        load_factor = float(load_keys["load_factor"])

        fuel_consumption = self.power * sfoc * load_factor / density        # liters/hour
        # l/h = kW * (g/kWh) * 1 / (kg/m^3)
        logging.info('Vessel: vessel %s consumption during "%s" is "%s" l/h' % (self.id, operation, fuel_consumption))

        return fuel_consumption

    def get_vessels_from_yaml(
            file_path: str,
            file_fuel_density: str,
            file_fuel_cons: str=None,
            file_load_factor: str=None
    ) -> list:
        """Reads a YAML file, fetches vessels from it and returns them as
        :class:`Vessel` items.

        Args:
            file_path (:obj:`str`): YAML file location.
            file_fuel_cons (:obj:`str`, *optional*): name of the YAML file
                with vessels fuel consumption. Defaults to ``None``.
            file_load_factor (:obj:`str`, *optional*): name of the YAML file
                with vessels load factor. Defaults to ``None``.
            file_fuel_density (:obj:`str`, *optional*): name of the YAML
                file with fuels densities.

        Raises:
            KeyError: if the keys in the YAML file are not expected.

        Returns:
            :obj:`list`: list of created :class:`Vessel`.
        """
        # Read YAML file
        f_yaml = open(os.path.join(file_path), 'r')
        yaml = YAML(typ='safe')
        vessels_yaml = yaml.load(f_yaml)
        f_yaml.close()

        # All vessels keys to lower case
        vessels_yaml = [
                {key.lower(): val for key, val in vessel.items()}
                for vessel in vessels_yaml
        ]

        keys_mandatory = ['id', 'type', 'speed_transit', "power","overnight"]

        vessels_list = []
        for vessel in vessels_yaml:
            if any([
                    key not in vessel.keys()
                    for key in keys_mandatory
            ]) is True:
                _e = '"id", "type", "speed_transit", '
                _e += '"power" and "overnight" are mandatory keys.'
                logging.error('Vessel: ' + _e)
                raise KeyError(_e)

            n_vessels = vessel.get("number_vessels",None)
            crew_berths = vessel.get("num_berths",None)
            charter = vessel.get("daily_charter",None)
            mother_vessel = vessel.get("mother_vessel",None)
            annual_contract = vessel.get("annual_contract",None)
            n_ves_annual_contract = vessel.get("n_ves_annual_contract",None)
            months_contract = vessel.get("months_contract",None)
            monthly_contract_cost = vessel.get("monthly_contract_cost",None)
            n_ves_monthly_contract = vessel.get("n_ves_monthly_contract",None)
            annual_contract = vessel.get("annual_contract",None)
            mobilisation_time = vessel.get("mobilisation_time",None)
            mobilisation_cost = vessel.get("mobilisation_cost",None)
            power = vessel.get("power",None)
            speed_towing = vessel.get("speed_towing",None)
            fuel_type = vessel.get("fuel_type",None)
            cons_transit = vessel.get("fuel_cons_transit",None)
            cons_maneuver = vessel.get("fuel_cons_maneuver",None)
            cons_standby = vessel.get("fuel_cons_standby",None)
            vessels_list.append(
                    Vessel(
                            id_=vessel["id"],
                            type_=vessel["type"],
                            speed_transit=vessel["speed_transit"],
                            crew_capacity=vessel["crew_capacity"],
                            overnight=vessel['overnight'],
                            n_vessels=n_vessels,
                            crew_berths=crew_berths,
                            daily_charter=charter,
                            mother_vessel = mother_vessel,
                            annual_contract=annual_contract,
                            n_ves_annual_contract = n_ves_annual_contract,
                            months_contract = months_contract,
                            monthly_contract_cost = monthly_contract_cost,
                            n_ves_monthly_contract = n_ves_monthly_contract,
                            mobilisation_time=mobilisation_time,
                            mobilisation_cost=mobilisation_cost,
                            power=power,
                            speed_tow=speed_towing,
                            fuel_type=fuel_type,
                            fuel_cons_transit=cons_transit,
                            fuel_cons_maneuver=cons_maneuver,
                            fuel_cons_standby=cons_standby,
                            file_vessels=file_path,
                            file_fuel_cons=file_fuel_cons,
                            file_load_factor=file_load_factor,
                            file_fuel_density=file_fuel_density
                    )
            )

        logging.info('Vessel: vessels read from file: "%s".' % file_path)
        return vessels_list

if __name__ == '__main__':

    vessel_min = Vessel(
            id_='V001',
            type_='CTV',
            speed_transit=3,
            daily_charter=1000,
            annual_contract=900000,
            crew_capacity=3,
            overnight=False,
            n_vessels=3,
            mobilisation_time=None,
            mobilisation_cost=None,
            power=300,
            density=860,
            file_vessels=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels.yaml'),
            file_fuel_cons=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_fuels.yaml'),
            file_load_factor=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_loads.yaml'),
            file_fuel_density=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_densities.yaml')
    )
