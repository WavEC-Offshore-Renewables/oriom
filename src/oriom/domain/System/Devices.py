import logging

# TODO you need to take component list from technologies 
# (define in wtg, wec, opv new attribute)
# Such list will be used to create the device in Farm considering components 
# present by tech, so like this we create different devices

# TODO location need to create a class that manage disctances and evaluate all in x,y from coordinates
class Device():
    """
    A class representing the a device
    
    Attributes:
        id (str): The unique identifier of the device
        name (str): The name of the device
        ore_type (str): The type of ORE being present
        location (dict): The location of the device with x,y coordinates in meters
        level_failure (:obj:`str`): Level at which the failure occurs for
            the graph.
    """

    def __init__(self, id_: str, name: str, ore_type: str, location: dict, level_failure: str):
        self.id_ = str(id_)
        self.name = str(name)
        self.ore_type = str(ore_type)
        self.location = location
        self.level_failure = str(level_failure)
        self.components = []

        self._check_inputs()

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
        
        if any([
                self.level_failure == 'exp_cable',
                self.level_failure == 'exp_cable_island',
                self.level_failure == 'dyn_cable-sub',
                self.level_failure == 'array_cable',
                self.level_failure == 'cable_cb',
                self.level_failure == 'cable_transf',
                self.level_failure == 'cable_switch',
                self.level_failure == 'cable_inv',
                self.level_failure == 'string_cable',
                self.level_failure == 'substation',
                self.level_failure == 'hub',
                self.level_failure == 'mv_transformer',
                self.level_failure == 'circuit_braker',
                self.level_failure == 'switcher',
                self.level_failure == 'inverter',
                self.level_failure == 'device'
            ]) is False:
                _e = f'level_failure not recognized {self.level_failure}'
                logging.error('Failure:' + _e)
                raise ValueError(_e)
