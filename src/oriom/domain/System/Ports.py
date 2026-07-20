


class Port():
    """
    A class representing the phisical Port
    
    Attributes:
        id_ (str): The unique identifier of the port
        name (str): The name of the port
        location (dict): The location of the port with x,y coordinates in meters
        hub (dict): A dictionary to hold device to inspect or correct
        fleet (dict): A dictionary to hold the fleet of ships and their details
    """
    
    def __init__(self, id_, name, location):
        self.id_ = id_
        self.name = name
        self.location = location
        self.hub = {}
        self.fleet = {}


    def __str__(self):
        return f"ID: {self.id_}, Port: {self.name}, Location: {self.location}"
