from geopy.distance import geodesic
from networkx import edges, nodes

from oriom.domain.System.Devices import Device
from oriom.common.constants import TECH_TYPES


class Farm():

    """
    A class representing the phisical energy farm
    
    Attributes:
        description (str): A brief description of the farm
        farm_type (list): The type of farm being present
        location (dict): The location of the farm with x,y coordinates
        fleet (dict): A dictionary to hold the fleet of ships and their details
        id_ (str): The unique identifier of the farm
        name (str): The name of the farm
        device_dict (dict): A dictionary to hold the devices in the farm
        device_list_unavailable (list): A list to hold the devices that are unavailable

    Methods:
        create_device(layouts, failures): 
            Create devices based on the provided layouts and failures
        create_rerectangolar_farm(rows, spacing, number_devices, distance_from_port, nodes_dict): 
            Create a rectangular grid of points representing the layout of devices in a farm


    
    """

    def __init__(self, inputs: object, farm_tech: object, layouts, failures, id_ = None, name = None, ):
        """
        A class representing the phisical energy farm
        
        Args:
            inputs (object): Object of class ``Inputs``
            farm_tech (object): Object of class ``TechnologyBuilder``
            layouts (dict): Dictionary of layouts for the ORE famrs.
            failures (list): A list of failure events for this farm``
            id_ (str): The unique identifier of the farm. Default to ``None``
            name (str): The name of the farm. Default to ``None``
        """

        self.id_ = id_ if id_ is not None else 'ORE_1'
        self.farm_tech = farm_tech
        self.name = name if name is not None else 'WavEC_ORE_1'
        self.farm_type = []
        self.location = {'lat': inputs.tseries.site_lat['value'], 'lon': inputs.tseries.site_lon['value']}
        self.layout = layouts
        self.distance_to_port = inputs.tseries.distance['value'] 

        self.fleet, self.device_dict = {}, {}
        self.device_list_unavailable = []

        self.farm_type.extend(
            farm_type for farm_type in TECH_TYPES
            if getattr(farm_tech, farm_type, None) is not None
        )

        self.description = (
            f"{self.name} is an offshore energy farm located at "
            f"({self.location['lat']}, {self.location['lon']}) "
            f"using {', '.join(self.farm_type)} technologies."
        )

        self.create_device(layouts=layouts, failures = failures)


    def __str__(self):
        return f"Farm: {self.name}, Farm Type: {self.farm_type}, Location: {self.location}, Description: {self.description}"
    

    def create_device(self, layouts, failures):
        """ Find for each technology the corresponding devices
        Hypotize a rectangular grid of devices in the farm and evaluate coordinates and distances
         and create Device objects for each node in the layout and edges layout and store them into the Graphs"""
        nodes_dict, edges_dict = {}

        # Create devices for each technology type present in the farm
        for tech_type in TECH_TYPES:
            tech = getattr(self.farm_tech, tech_type, None)
            layout = layouts.get(tech_type, None)

            # If the technology is present, create devices based on the layout
            if tech:
                # Populate nodes_dict with node data from the layout
                nodes_dict = {node: data for node, data in layout.nodes(data=True)}
                edges_dict = {(u, v): data for u, v, data in layout.edges(data=True)}

                device_nodes = [node_id for node_id, attrs in nodes_dict.items() if attrs.get("level") == "device"]

                # Create a rectangular grid of points representing the layout of devices in the farm
                locations, distances = self.create_rerectangolar_farm(
                    rows = tech_type.number_strings ,
                    spacing = tech_type.spacing,
                    number_devices = tech_type.number_devices,
                    distance_from_port = self.distance_to_port,
                    nodes_dict = device_nodes
                )

                # Create Device instances for each node in the layout and store them in the device_dict and in layout nodes and edges
                for items, graph_obj, is_edge in ((nodes_dict.items(), layout.nodes, False),(edges_dict.items(), layout.edges, True)):
                    for key, data in items:
                        # Create a Device instance for each node or edge in the layout
                        device = Device(
                            name=data["name"],
                            key_node = key,
                            ore_type=tech_type,
                            locations=locations,
                            distances=distances,
                            failures = failures,
                            data_node=data,
                            edge=is_edge,
                        )

                        self.device_dict[device.id_] = device

                        # Add the object to the graph node or edge attributes
                        graph_obj[key].update({"device": device})


    def create_rerectangolar_farm(
        self,
        rows,
        spacing,
        number_devices,
        distance_from_port,
        nodes_dict
    ):
        """
        Create a rectangular grid of points representing the layout of devices in a farm.

        Args:
            center (tuple): (x, y) central point of the farm.
            rows (int): Number of strings.
            spacing (float): Distance between points.
            number_devices (int): Number of devices to create.
            distance_from_port (float): Distance from the port.
            nodes_dict (list): List containing node IDs.

        Returns:
            tuple: A tuple containing the dictionary of points and the distance from the port.
        """
        columns = number_devices // rows

        offset_x = (columns - 1) / 2
        offset_y = (rows - 1) / 2

        points, distances = {}, {}
        i = 0
        points[0] = self.location
        distances[0] = distance_from_port

        for r in range(rows):
            for c in range(columns):
                # East-west displacement (bearing 90°)
                east_offset = (c - offset_x) * spacing
                east_point = geodesic(meters=east_offset).destination((self.location['lat'], self.location['lon']), 90)

                # North-south displacement (bearing 0°)
                north_offset = (r - offset_y) * spacing
                final_point = geodesic(meters=north_offset).destination((east_point.latitude, east_point.longitude), 0)
                coord = (final_point.latitude, final_point.longitude)
                points[str(nodes_dict[i])] = coord

                # Distance from port
                offset_distance = geodesic((self.location['lat'], self.location['lon']), coord).km

                # Combine center distance with local displacement effect
                distances[str(nodes_dict[i])] = distance_from_port + offset_distance

                i += 1

        return points, distances