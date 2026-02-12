import os
import re
import logging
import networkx as nx
from collections import Counter
from ruamel.yaml import YAML

from logistic_tools.classes.Activity import Activity


def get_graph_levels(G: nx.Graph) -> set:
    """ Take all the levels of the graphs and return it as a set""" 
    node_levels = {data.get('level', None) for _, data in G.nodes(data=True) if 'level' in data} 
    edge_levels = {data.get('level', None) for _, _, data in G.edges(data=True) if 'level' in data} 
    # Unite the levels and avoid None or empty values 
    all_levels = {lvl for lvl in node_levels.union(edge_levels) if lvl and lvl.strip()}
    return all_levels


def level_component_check(Gs: dict, operations: list, failure: bool = False):
    """
    Check if any object has a level that is not defined in the tech Graph.

    Args:
        Gs (dict): Dictionary of tech graphs (networkx.Graph)
        operations (list): List of objects to check (InspectionPort, InspectionSite, Failures)
        failure (bool): If True, check 'level_failure'; else 'level'
    """
    
    tech_map = {'G_wind': 'ofw', 'G_pv': 'opv', 'G_wave': 'owc'}
    attr_to_check = 'level_failure' if failure else 'level'
    object_name = 'failure' if failure else 'inspection'

    # Extrapolate all level for each graph
    level_dict = {tech: get_graph_levels(G) for gname, G in Gs.items() if (tech := tech_map.get(gname)) and G}

    # Check all levels
    for obj in operations:
        tech = obj.id[:3]
        level = getattr(obj, attr_to_check, None)
        if tech == 'oce':
            all_levels = set().union(*level_dict.values())
            if level not in all_levels:
                e_ = f"Level {object_name} '{level}' not found in graph for {obj.id}"

                logging.error(e_)
                raise KeyError(e_)
        else:
            if level not in level_dict.get(tech, set()):
                e_ = f"Level {object_name} '{level}' not found in graph for {obj.id}"
                logging.error(e_)
                raise KeyError(e_)


def operation_check_identities(total_operations: list):
    """
    Check if any operation has the same id.

    Args:
        total_operations (list): List of Operation objects

    Raise: 
        ValueError: If there are operations with the same id
    """

    ids = [op.id for op in total_operations]
    id_counts = Counter(ids)
    duplicate_ids = [id for id, count in id_counts.items() if count > 1]

    # Verifica se c'è almeno un id duplicato
    duplicate_found = any(count > 1 for count in id_counts.values())
    if duplicate_found:
        e_ = f"Duplicate operation id found: '{duplicate_ids}', please give unique id to the operations"
        logging.error(e_)
        raise ValueError(e_)
        
    
def define_activities(
        operation: object,
        file_activities: str,
        distance_to_site: float,
        transit_between_devices: float,
        tow_op: bool
    ):
        """
        Define activities for :class:`CorrectiveMajor` or :class:`OperationTow` based on a YAML file path :attr:`file_activities` if
        the operation ID of the activity matches the ID of this CorrectiveMajor, that 
        :class:`~logistic_tools.classes.Activity.Activity` is assumed as part
        of the :class:`CorrectiveMajor` or :class:`OperationTow`.
        
        Args:
            operation (:obj: `object`): Objects of class: ``OperationTow`` or class: ``CorrectiveMajor``
            file_activities (:obj:`str`): The path to the YAML file containing activities.
            distance_to_site (:obj:`float`): The distance from port to site in kilometers.
            transit_between_devices (:obj:`float`): Time between two devices in hours.
            tow_op (:obj: `bool`): Flag to define if is a operation under analysis is OperationTow or CorrectiveMajor
        Raises:
            KeyError: if the operation is not found in the :attr:`file_activities`.
            ValueError: if activities defined as "Repeated" are not consecutive.
        """
        operation_type = "OperationTow" if tow_op else "CorrectiveMajor"

        # Gets activities from a YAML file
        f_yaml = open(os.path.join(file_activities), 'r')
        yaml = YAML(typ='safe')
        activities_yaml = yaml.load(f_yaml)
        f_yaml.close()
        # Filter this operation activites
        op_found = False
        for op, acts in activities_yaml.items():
            if op.lower() == operation.id:
                activities_yaml = acts
                op_found = True
                break
        if op_found is False:
            _e = 'Could not find operation "%s" activities ' % operation.id
            _e += 'in "%s" activities file.' % file_activities
            logging.error(f'{operation_type}: {_e}')
            raise KeyError(_e)

        operation.activities = []
        for idx, act in enumerate(activities_yaml):
            towing = False
            act['id'] += '_%03d' % idx
            wtg_shutdown_dur = 0
            wec_shutdown_dur = 0
            pv_shutdown_dur = 0
            
            if tow_op and all([
                    'transit' in act["name"].lower(),
                    'next' in act["name"].lower()
            ]) is True:
                # This is a transit between devices activity
                duration = transit_between_devices
            # Duration
            elif 'transit' in act["name"].lower():
                # This is a transit activity
                duration = ((distance_to_site * 1000) / operation.vessel1.speed_transit) / 3600
            elif tow_op and re.search(r'\btow\b', act["name"].lower()) is not None:
                towing = True
                # This is a towing activity
                duration = ((distance_to_site * 1000) / operation.vessel1.speed_tow) / 3600
                # Incase of shutdown is needed, a <tech>_shutdown_dur must
                # be included in this activity
                try:
                    if act["wtg_shutdown_dur"] is True:
                        wtg_shutdown_dur = duration
                except KeyError:
                    pass
                try:
                    if act["wec_shutdown_dur"] is True:
                        wec_shutdown_dur = duration
                except KeyError:
                    pass
                try:
                    if act["pv_shutdown_dur"] is True:
                        pv_shutdown_dur = duration
                except KeyError:
                    pass
            else:
                try:
                    duration = float(act["duration"])
                except TypeError:
                    _e = 'Could not define the duration of activity %s.' % act["id"]
                    logging.error(f'{operation_type}: {_e}')
                    raise ValueError(_e)
                try:
                    wtg_shutdown_dur = act["wtg_shutdown_dur"]
                except KeyError:
                    wtg_shutdown_dur = 0
                try:
                    wec_shutdown_dur = act["wec_shutdown_dur"]
                except KeyError:
                    wec_shutdown_dur = 0
                try:
                    pv_shutdown_dur = act["pv_shutdown_dur"]
                except KeyError:
                    pv_shutdown_dur = 0
            duration = round(duration, 2)
            wtg_shutdown_dur = round(wtg_shutdown_dur, 2)
            wec_shutdown_dur = round(wec_shutdown_dur, 2)
            pv_shutdown_dur = round(pv_shutdown_dur, 2)

            # OLCs
            for key in ['hs', 'tp', 'ws', 'cs', 'light']:
                try:
                    act[key]
                except KeyError:
                    act[key] = None

            act = {
                    key: (value.lower() if isinstance(value, str) else value)
                    for key, value in act.items()
            }

            activity = Activity(
                    id_=act["id"],
                    name=act["name"],
                    duration=duration,
                    location=act["location"],
                    wtg_shutdown_dur=wtg_shutdown_dur,
                    wec_shutdown_dur=wec_shutdown_dur,
                    pv_shutdown_dur=pv_shutdown_dur,
                    wave_height=act["hs"],
                    wave_period=act["tp"],
                    wind_speed=act["ws"],
                    current_speed=act["cs"],
                    light=act["light"],
                    towing = towing
            )
            operation.activities.append(activity)
        logging.info(f'{operation_type}: operation "{operation}" activities defined based on file "{operation}"')


def recycle_activities(operation: object, dir: str, file_name: str, tow_op: bool):
    """
    Recycle previous ~Activity from a CSV file and update the current activities list.

    Args:
        operation (:obj: `object`): Objects of class: ``OperationTow`` or class: ``CorrectiveMajor``
        dir (:obj:`str`): The directory where the CSV file is located.
        file_name (:obj:`str`): The name of the CSV file to recycle activities from.
        tow_op (:obj: `bool`): Flag to define if is a operation under analysis is OperationTow or CorrectiveMajor
    """
    operation_type = "OperationTow" if tow_op else "CorrectiveMajor"

    operation.activities = Activity.get_activities_from_csv(
            file_csv=os.path.join(dir, file_name + '.csv')
    )
    logging.info(f'{operation_type}: operation {operation.id} activities recycled from {os.path.join(dir, file_name)}.')