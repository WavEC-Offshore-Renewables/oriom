# Import packages
import pandas as pd
import logging
from distutils.util import strtobool


class Activity():
    """Operations are decomposed in Activities. Each Activity has a specific
    duration, Operating Limit Criteria, etc.

    Note:
        CorrectiveMajor and OperationTow are composed by activities.

        For defining the shutdown use the boolean True only if the activity is at the location
        "transit" so that it will consider the device shutdwon for the whole duration
        of the activity.

    Attributes:
        id (str): Activity ID.
        name (str): Activity description.
        duration (float): The amount of time to preform this activity.
        location (str): Where this activity takes place: port, site or transit.
        wtg_shutdown_dur (:obj:`bool`): Duration of the activity related with WTGs.
        wec_shutdown_dur (:obj:`bool`): Duration of the activity related with WECs.
        pv_shutdown_dur (:obj:`bool`): Duration of the activity related with PV panels.
        hs (float): Limit wave height. Its value is None if there is no limit.
        tp (float): Limit wave period. Its value is None if there is no limit.
        ws (float): Limit wind speed. Its value is None if there is no limit.
        ws_hub (float): Limit wind speed at hub height. Its value is None if there is no limit.
        cs (float): Limit current speed. Its value is None if there is no limit.
        light (:obj:`bool`): The need of day light to preform the activity.
        towing (:obj:`bool`): Indicates if this activity is performing a towing operation.

    Note:
        When the class is initialized, :func:`_check_attributes` is run.

    Example:
        >>> activity = Activity(
        >>>         id_='ACT_001_0',
        >>>         name='Vessel preparation',
        >>>         duration=4,
        >>>         wave_height=5,
        >>>         light=False
        >>> )
    """
    def __init__(
            self,
            id_: str,
            name: str,
            duration: float,
            location: str,
            wtg_shutdown_dur: bool=False,
            wec_shutdown_dur: bool=False,
            pv_shutdown_dur: bool=False,
            wave_height: float=None,
            wave_period: float=None,
            wind_speed: float=None,
            wind_speed_hub: float=None,
            current_speed: float=None,
            light: bool=False,
            towing: bool=False
    ):
        """Initializes :class:`Activity`.

        Args:
            id_ (str): Activity ID.
            name (str): Activity description.
            duration (float): The amount of time to preform this activity.
            location (str): Where the activity takes place (port, transit, site or mobilization).
            wtg_shutdown_dur (:obj:`bool`, *optional*): Duration of the activity related with WTGs.. Defaults to ``False``.
            wec_shutdown_dur (:obj:`bool`, *optional*): Duration of the activity related with WECs.. Defaults to ``False``.
            pv_shutdown_dur (:obj:`bool`, *optional*): Duration of the activity related with PV panels.. Defaults to ``False``.
            wave_height (:obj:`float`, *optional*): Limit wave height. Defaults to ``None``.
            wave_period (:obj:`float`, *optional*): Limit wave period. Defaults to ``None``.
            wind_speed (:obj:`float`, *optional*): Limit wind speed. Defaults to ``None``.
            wind_speed_hub (:obj:`float`, *optional*): Limit wind speed at hub height. Defaults to ``None``.
            current_speed (:obj:`float`, *optional*): Limit current speed. Defaults to ``None``.
            light (:obj:`bool`, *optional*): The need of day light to preform the activity. Defaults to ``False``.
            towing (:obj:`bool`): Indicates if this activity is performing a towing operation. . Defaults to ``False``


        Raises:
            ValueError: if :attr:`light` is not a boolean value.
        """
        self.id = str(id_)
        self.name = str(name).lower()
        self.duration = float(duration)
        self.location = str(location).lower()

        self.wtg_shutdown_dur = 0
        self.wec_shutdown_dur = 0
        self.pv_shutdown_dur = 0
        self.hs = None
        self.tp = None
        self.ws = None
        self.ws_hub = None
        self.cs = None
        self.light = False
        self.towing = False

        if wtg_shutdown_dur is not None:
            self.wtg_shutdown_dur = bool(wtg_shutdown_dur)
        if wec_shutdown_dur is not None:
            self.wec_shutdown_dur = bool(wec_shutdown_dur)
        if pv_shutdown_dur is not None:
            self.pv_shutdown_dur = bool(pv_shutdown_dur)

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
                    e_ = f'Activity: For activity {self.id}, "light" must be a boolean value'
                    logging.error(e_)
                    raise ValueError(e_)
        else:
            self.light = False
        if towing is not None:
            self.towing = bool(towing)

        self._check_attributes()

    def _check_attributes(self):
        """
        This method validates the attributes of the `Activity` class to ensure they
        have valid values and fall within specified ranges.

        Raises errors if any attribute is outside the specified range.
        """
        if self.duration < 0:
            raise ValueError('"duration" must not be negative')
        if self.location not in ['port', 'transit', 'site']:
            raise ValueError('"location" must be "port", "transit" or "site"')
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
        if self.wtg_shutdown_dur is not None and not isinstance(self.wtg_shutdown_dur, bool):
            raise TypeError("wtg_shutdown_dur must be bool type")
        if self.wec_shutdown_dur is not None and not isinstance(self.wec_shutdown_dur, bool):
            raise TypeError("wec_shutdown_dur must be bool type")
        if self.pv_shutdown_dur is not None and not isinstance(self.pv_shutdown_dur, bool):
            raise TypeError("pv_shutdown_dur must be bool type")
        if all([
                self.location == 'transit',
                'tow' not in self.name,
                any([
                        self.wtg_shutdown_dur > 0,
                        self.wec_shutdown_dur > 0,
                        self.pv_shutdown_dur > 0
                ])
        ]):
            _e = '"wtg_shutdown_dur", "wec_shutdown_dur" or "pv_shutdown_dur" cannot '
            _e += 'be defined for "transit" activities'
            raise ValueError(_e)

        logging.debug('Activity: activity "%s - %s" attributes within ranges and valid.' % (self.id, self.name))

    def get_activities_from_csv(file_csv: str) -> list:
        """Returns a list of :class:`Activity` based on a CSV file.

        Args:
            file_csv (str): CSV file path with activities.

        Returns:
            :obj:`list`: :obj:`list` of :class:`Activity`.
        """
        df_activities = pd.read_csv(file_csv, sep=',')
        df_activities.fillna('NA', inplace=True)

        list_activities = []
        for _, row in df_activities.iterrows():
            row_dict = dict(row)
            for key, value in row_dict.items():
                if value == 'NA':
                    row_dict[key] = None
            wtg_shutdown_dur = 0
            wec_shutdown_dur = 0
            pv_shutdown_dur = 0
            if row_dict["wtg_shutdown_dur"] is True:
                wtg_shutdown_dur = row_dict["duration"]
            if row_dict["wec_shutdown_dur"] is True:
                wec_shutdown_dur = row_dict["duration"]
            if row_dict["pv_shutdown_dur"] is True:
                pv_shutdown_dur = row_dict["duration"]
            list_activities.append(
                    Activity(
                            id_=row_dict["id"],
                            name=row_dict["name"],
                            duration=row_dict["duration"],
                            location=row_dict["location"],
                            wtg_shutdown_dur=wtg_shutdown_dur,
                            wec_shutdown_dur=wec_shutdown_dur,
                            pv_shutdown_dur=pv_shutdown_dur,
                            wave_height=row_dict["hs"],
                            wave_period=row_dict["tp"],
                            wind_speed=row_dict["ws"],
                            wind_speed_hub=row_dict["ws_hub"],
                            current_speed=row_dict["cs"],
                            light=row_dict["light"],
                            towing=row_dict["towing"],
                    )
            )
        logging.info('Activity: activities read from file: "%s".' % file_csv)
        return list_activities

    @staticmethod
    def save_activities_as_csv(operation, output_file: str):
        """
        Saves set of :class:`~oriom.domain.Activity.Activity` as a
        CSV file.

        Args:
            output_file (str): The file path to save the activities as a CSV file.
        """
        if operation.activities is None or operation.activities == []:
            _e = 'Operation activities not defined yet. Run OperationTow.define_activities first.'
            logging.error(_e)
            raise TypeError(_e)

        acts_list = []
        tow_op = False
        for activity in operation.activities:
            act_dict = {}
            act_dict["id"] = activity.id
            act_dict["name"] = activity.name
            act_dict["duration"] = activity.duration
            act_dict["location"] = activity.location
            act_dict["wtg_shutdown_dur"] = activity.wtg_shutdown_dur
            act_dict["wec_shutdown_dur"] = activity.wec_shutdown_dur
            act_dict["pv_shutdown_dur"] = activity.pv_shutdown_dur
            act_dict["hs"] = activity.hs
            act_dict["tp"] = activity.tp
            act_dict["ws"] = activity.ws
            act_dict["ws_hub"] = activity.ws_hub
            act_dict["cs"] = activity.cs
            act_dict["light"] = activity.light
            act_dict["towing"] = activity.towing
            if activity.towing:
                tow_op = True
            acts_list.append(act_dict)
            del act_dict

        df_acts = pd.DataFrame(acts_list)
        df_acts.to_csv(output_file, index=False)
        if tow_op:
            logging.info('OperationTow: operation %s activities saved as "%s".' % (operation.id, output_file))
        else:
            logging.info('CorrectiveMajor: operation %s activities saved as "%s".' % (operation.id, output_file))


if __name__ == '__main__':

    activity = Activity(
            id_='ACT_001_0',
            name='Vessel preparation',
            duration=4,
            location='port',
            wtg_shutdown_dur = True,
            wave_height=5,
            light=False
    )