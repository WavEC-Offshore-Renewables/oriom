

class Component():
    """
    A class representing a component of a device
    
    Attributes:
        id_ (str): The unique identifier of the component.
        name (str): The name of the component.
        device_id (str): The device ID this component belongs to.
        n_element (:obj:`int`) : Number of element present on the device.
        level_failure (:obj:`str`): Level at which the component is defined
        failures (list): A list of failure events for this component.
    """

    def __init__(self, id_, name: str, device_id: str, n_element: int = 1):
        self.id_ = str(id_)
        self.name = str(name)
        self.device_id = str(device_id)
        self.n_element = int(n_element)

        self.failures = []
        

    def __str__(self):
        return f"ID: {self.id_}, Component: {self.name}, Device: {self.device_id}"

