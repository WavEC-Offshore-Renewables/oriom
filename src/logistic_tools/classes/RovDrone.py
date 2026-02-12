# Import packages
import pandas as pd
import os
import logging
from ruamel.yaml import YAML


class RovDrone():
    """RovDrone class.

    Attributes:
        id (:obj:`str`): The rov/drone unique identifier.
        name (:obj:`str`): The rov/drone name.
        type (:obj:`str`): Rov/drone type.
        daily_charter (:obj:`float`): Rov/drone daily charter rate, in €/day.
        weight (:obj:`float`): Rov/drone weight in kg.
            Defaults to ``None``.
        dimensions (:obj:`float`): Rov/drone dimensions in m.
            Defaults to ``None``.
        useful_capacity (:obj:`float`): Rov/drone useful capacity in kg.
            Defaults to ``None``.
        speed_transit (:obj:`float`): Vessel transit speed, in km/h.
            Defaults to ``None``.
        battery_capacity (:obj:`float`): Rov/drone battery capacity in kWh.
            Defaults to ``None``.
        recharging_duration (:obj:`float`): Rov/drone recharging duration in h.
            Defaults to ``None``.
        max_distance (:obj:`float`): Rov/drone maximum distance in km.
            Defaults to ``None``.
        avg_autonomy (:obj:`float`): Rov/drone average autonomy in h.
            Defaults to ``None``.
        on_site (:obj:`bool`): True if rov/drone stays on site.
            Defaults to ``False``.
        support_vessel (:obj:`str`): Rov/drone support vessel.
            Defaults to ``None``.
        nr_technicians (:obj:`int`): Rov/drone technicians required.
            Defaults to ``0``.
        ws_max (:obj:`float`): Rov/drone max wind speed in m/s.
            Defaults to ``None``.
        hs_max (:obj:`float`): Rov/drone max wave height in m.
            Defaults to ``None``.
        daylight (:obj:`bool`): Rov/drone daylight needed.
            Defaults to ``False``.
        precipitation_max (:obj:`float`): Rov/drone max precitiation in mm.
            Defaults to ``None``.
        rov_costs (:class:`~logistic_tools.classes.Rovs_costs.Rovs_costs`): Cost
            associated to the rov use. Defaults to ``None``.

    Note:
        When the class is initialized, :func:`_check_attributes` is run.

    Example:
        >>> rov_dron = RovDrone(
        >>>         id_='stork_1',
        >>>         name='Stork',
        >>>         type_='aerial',
        >>>         daily_charter=4920,
        >>>         weight=200,
        >>>         dimensions=1.5,
        >>>         useful_capacity=5,
        >>>         speed_transit=17,
        >>>         battery_capacity=0.4,
        >>>         recharging_duration=3,
        >>>         max_distance=10.2,
        >>>         avg_autonomy=0.6,
        >>>         on_site=True,
        >>>         support_vessel=CTV,
        >>>         nr_technicians=2,
        >>>         ws_max=10,
        >>>         hs_max=1.5,
        >>>         daylight=True,
        >>>         precipitation_max=5
        >>> )
    """
    def __init__(
            self,
            id_: str,
            name: str,
            type_: str,
            daily_charter: float,
            weight: float=None,
            dimensions: float=None,
            useful_capacity: float=None,
            speed_transit: float=None,
            battery_capacity: float=None,
            recharging_duration: float=None,
            max_distance: float=None,
            avg_autonomy: float=None,
            on_site: bool=False,
            support_vessel: str=None,
            nr_technicians: int=0,
            ws_max: float=None,
            hs_max: float=None,
            daylight: bool=False,
            precipitation_max: float=None

    ):
        """Initializes :class:`RovDrone` class.

        Args:
            id_ (:obj:`str`): The rov/drone unique identifier.
            name (:obj:`str`): The rov/drone name.
            type_ (:obj:`str`): Rov/drone type.
            daily_charter (:obj:`float`): Rov/drone daily charter rate, in €/day.
            weight (:obj:`float`,*optional*): Rov/drone weight in kg.
                Defaults to ``None``.
            dimensions (:obj:`float`,*optional*): Rov/drone dimensions in m.
                Defaults to ``None``.
            useful_capacity (:obj:`float`,*optional*): Rov/drone useful capacity in kg.
                Defaults to ``None``.
            speed_transit (:obj:`float`,*optional*): Vessel transit speed, in km/h.
                Defaults to ``None``.
            battery_capacity (:obj:`float`,*optional*): Rov/drone battery capacity in kWh.
                Defaults to ``None``.
            recharging_duration (:obj:`float`,*optional*): Rov/drone recharging duration in h.
                Defaults to ``None``.
            max_distance (:obj:`float`,*optional*): Rov/drone maximum distance in km.
                Defaults to ``None``.
            avg_autonomy (:obj:`float`,*optional*): Rov/drone average autonomy in h.
                Defaults to ``None``.
            on_site (:obj:`bool`,*optional*): True if rov/drone stays on site.
                Defaults to ``False``.
            support_vessel (:obj:`str`,*optional*): Rov/drone support vessel.
                Defaults to ``None``.
            nr_technicians (:obj:`int`,*optional*): Rov/drone technicians required.
                Defaults to ``0``.
            ws_max (:obj:`float`,*optional*): Rov/drone max wind speed in m/s.
                Defaults to ``None``.
            hs_max (:obj:`float`,*optional*): Rov/drone max wave height in m.
                Defaults to ``None``.
            daylight (:obj:`bool`,*optional*): Rov/drone daylight needed.
                Defaults to ``False``.
            precipitation_max (:obj:`float`,*optional*): Rov/drone max precitiation in mm.
                Defaults to ``None``.

        """
        self.id = str(id_).lower()
        self.name = str(name).lower()
        self.type = str(type_).lower()
        self.daily_charter = float(daily_charter)

        try: self.weight = float(weight)
        except TypeError: self.weight=None
        try: self.dimensions = float(dimensions)
        except TypeError: self.dimensions=None
        try: self.useful_capacity = float(useful_capacity)
        except TypeError: self.useful_capacity=None
        try: self.speed_transit = float(speed_transit)
        except TypeError: self.speed_transit=None
        try: self.battery_capacity = float(battery_capacity)
        except TypeError: self.battery_capacity=None
        try: self.recharging_duration = float(recharging_duration)
        except TypeError: self.recharging_duration=None
        try: self.max_distance = float(max_distance)
        except TypeError: self.max_distance=None
        try: self.avg_autonomy = float(avg_autonomy)
        except TypeError: self.avg_autonomy=None
        try:
            self.on_site = bool(on_site)
        except TypeError:
            self.on_site = False
            _w = 'RovDrone: rov/drone %s on site not defined. ' % self.id
            _w = 'Defaults to False.'
            logging.debug(_w)
        if pd.isna(support_vessel) is False and support_vessel is not None:
            self.support_vessel=str(support_vessel).lower()
        else: self.support_vessel=None
        try:
            self.nr_technicians = int(nr_technicians)
        except TypeError:
            self.nr_technicians = 0
            _w = 'RovDrone: rov/drone %s number of technicians not defined. ' % self.id
            _w = 'Defaults to 0.'
            logging.debug(_w)
        try: self.ws_max = float(ws_max)
        except TypeError: self.ws_max=None
        try: self.hs_max = float(hs_max)
        except TypeError: self.hs_max=None
        try: self.daylight = bool(daylight)
        except TypeError: self.daylight=False
        try: self.precipitation_max = float(precipitation_max)
        except TypeError: self.precipitation_max=None

        self._check_attributes()

        self.rov_costs = None


    def _check_attributes(self):
        """Validates :class:`RovDone` class attributes ranges."""
        if self.daily_charter < 0:
            raise ValueError('"daily_charter" must not be negative')
        logging.debug('Vessel: vessel %s attributes within ranges and valid.' % self.id)

    def get_rovdrones_from_yaml(file_path: str) -> list:
        """Reads a YAML file, fetches ROVs and Drones from it and
        returns them as :class:`RovDrone` items.

        Args:
            file_path (:obj:`str`): YAML file location.

        Raises:
            KeyError: if the keys in the YAML file are not expected.

        Returns:
            :obj:`list`: list of created :class:`RovDone`.
        """
        # Read YAML file
        f_yaml = open(os.path.join(file_path), 'r')
        yaml = YAML(typ='safe')
        rovs_drones_yaml = yaml.load(f_yaml)
        f_yaml.close()

        # All ROVs and Drones keys to lower case
        rovs_drones_yaml = [
                {key.lower(): val for key, val in rov_drone.items()}
                for rov_drone in rovs_drones_yaml
        ]

        keys_mandatory = ['id', 'name', 'type', 'daily_charter']
        no_mandatory_keys = [
                'weight',
                'dimensions',
                'useful_capacity',
                'speed_transit',
                'battery_capacity',
                'recharging_duration',
                'max_distance',
                'avg_autonomy',
                'on_site',
                'support_vessel',
                'nr_technicians',
                'ws_max',
                'hs_max',
                'daylight',
                'precipitation_max'
        ]

        rovs_drones_list = []
        for rov_drone in rovs_drones_yaml:
            if any([
                    key not in rov_drone.keys()
                    for key in keys_mandatory
            ]) is True:
                _e = '"id", "name", "type" and "daily_charter" '
                _e += 'are mandatory keys.'
                logging.error('RovDrone: ' + _e)
                raise KeyError(_e)

            for key in no_mandatory_keys:
                try:
                    rov_drone[key]
                except KeyError:
                    rov_drone[key] = None

            rovs_drones_list.append(
                    RovDrone(
                            id_=rov_drone["id"],
                            name=rov_drone["name"],
                            type_=rov_drone["type"],
                            daily_charter=rov_drone["daily_charter"],
                            weight=rov_drone["weight"],
                            dimensions=rov_drone["dimensions"],
                            useful_capacity=rov_drone["useful_capacity"],
                            speed_transit=rov_drone["speed_transit"],
                            battery_capacity=rov_drone["battery_capacity"],
                            recharging_duration=rov_drone["recharging_duration"],
                            max_distance=rov_drone["max_distance"],
                            avg_autonomy=rov_drone["avg_autonomy"],
                            on_site=rov_drone["on_site"],
                            support_vessel=rov_drone["support_vessel"],
                            nr_technicians=rov_drone["nr_technicians"],
                            ws_max=rov_drone["ws_max"],
                            hs_max=rov_drone["hs_max"],
                            daylight=rov_drone["daylight"],
                            precipitation_max=rov_drone["precipitation_max"]
                    )
            )

        logging.info('RovDrone: rov/drone read from file: "%s".' % file_path)
        return rovs_drones_list


if __name__ == '__main__':

    rov_dron_min = RovDrone(
            id_='stork_1',
            name='Stork',
            type_='aerial',
            daily_charter=4920,
    )

    rovs_drones = RovDrone.get_rovdrones_from_yaml(
            os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'rovs.yaml')
    )
