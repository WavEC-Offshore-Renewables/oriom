import logging

from oriom.common.constants import FAILURE_LEVEL_LIST
from oriom.domain.System.Components import Component

# TODO you need to take component list from technologies 
# (define in wtg, wec, opv new attribute)
# Such list will be used to create the device in Farm considering components 
# present by tech, so like this we create different devices

# TODO location need to create a class that manage disctances and evaluate all in x,y from coordinates
class Device():
    """
    A class representing the a device
    
    Attributes:
        id_ (str): The unique identifier of the device
        name (str): The name of the device
        key_node (str): The key node of the device in the graph
        ore_type (str): The type of ORE being present
        locations (dict): The location of the device with x,y coordinates
        distances (dict): The distance of the device with x,y in km
        node (:obj:`dict`): Dictionary of attribute node of the graph
        edge (bool): Boolean to indicate if the device is an edge device or not
        failure_list (list): A list of failure events for this device

    Methods:
        _check_inputs(): 
            Validates the inputs of the `Device` class to ensure they have valid values and fall within specified ranges.
        location_assign(locations, distances, key_node): 
            Assigns location and distance to the device based on the provided locations and distances dictionaries.
        
    """

    def __init__(self, name: str, key_node: str, ore_type: str, locations: dict, distances: dict, failures: list, node: dict, edge: bool = False):
        self.failure_list = []

        self.id_ = f"{str(ore_type)}_{str(key_node)}"
        self.name = str(name)
        self.key_node = str(key_node)
        self.ore_type = str(ore_type)
        self.level_failure = str(node['level'])
        self.edge = edge

        self.location_assign(locations = locations, distances = distances)

        self._check_inputs()

        # Associate failures to the device based on the node's level
        for fail in failures:
            if fail['level_failure '] == self.level_failure:
                self.failure_list.append(fail)


    def __str__(self):
        return f"Device: {self.name}, Type: {self.ore_type}, Location: {self.location}"


    def _check_inputs(self):
        """
        This method validates the inputs of the `Device` class to ensure they
        have valid values and fall within specified ranges.

        Raises errors if any attribute is outside the specified range.
        """
        if self.id_[0:3] not in ['oce','ofw','owc','opv']:
            raise ValueError('"prefix not recognized"')
        
        if self.level_failure not in FAILURE_LEVEL_LIST:
            _e = f'level_failure not recognized {self.level_failure}'
            logging.error('Failure:' + _e)
            raise ValueError(_e)
        

    def location_assign(self, locations: dict, distances: dict, key_node: str = None):
        """ Assign location and distance to the device based on the provided locations and distances dictionaries.
        If the device is an WTG, WEC or OPV, it will use the key_node to assign specific location and distance."""

        # Inizialize with center value of the farm for all the components
        self.location = distances.get(str(0), None)
        self.distances = distances.get(str(0), None)

        #Specify specific location and distance for the devices only (WTG, WEC, OPV)
        if not self.edge:
            if key_node in locations:
                self.location = locations.get(str(key_node), None)
                self.distance = distances.get(str(key_node), None)
        else:
            # Export cable
            if key_node == (1,0) or key_node == (0,1):
                self.distance = self.distances/2