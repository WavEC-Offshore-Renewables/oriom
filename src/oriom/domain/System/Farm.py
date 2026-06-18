


class Farm():

    """
    A class representing the phisical energy farm
    
    Attributes:
        id (str): The unique identifier of the farm
        name (str): The name of the farm
        description (str): A brief description of the farm
        farm_type (list): The type of farm being present
        location (dict): The location of the farm with x,y coordinates
        fleet (dict): A dictionary to hold the fleet of ships and their details
    """

    def __init__(self, inputs: object, farm_tech: object, layouts):
        """
        A class representing the phisical energy farm
        
        Args:
            inputs (object): Object of class ``Inputs``
            farm_tech (object): Object of class ``TechnologyBuilder``
        """
        self.id_ = str('farm01')
        self.farm_tech = farm_tech
        self.name = str('farm_name')
        self.farm_type = []
        self.location = {'lat': inputs.site_lat, 'lon': inputs.site_lon}
        self.layout = layouts

        self.fleet = {}

        self.farm_type.extend(
            farm_type for farm_type in ['wtg', 'wec', 'pv']
            if getattr(farm_tech, farm_type, None) is not None
        )

        self.description = (
            f"{self.name} is an offshore energy farm located at "
            f"({self.location['lat']}, {self.location['lon']}) "
            f"using {', '.join(self.farm_type)} technologies."
        )

        self.create_device()

    def __str__(self):
        return f"Farm: {self.name}, Farm Type: {self.farm_type}, Location: {self.location}, Description: {self.description}"
    
    def create_device(self):
        for tech_type in ['wtg', 'wec', 'pv']:
            if getattr(self.farm_tech, tech_type, None):
                """create device of the tech"""
                pass
                


