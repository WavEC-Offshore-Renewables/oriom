from oriom.domain.System.Farm import Farm
from oriom.domain.System.Ports import Port
from oriom.domain.System.Storages import Storage


def system_builder(
    inputs: object,
    farm_technologies: object,
    G_layouts: dict,
    failures: list
)->tuple[Farm, Port, Storage]:
    
    """ Creation of System objects.
    Args:
        inputs (object): Object of class ``Inputs``
        farm_tech (object): Object of class ``TechnologyBuilder``
        layouts (dict): Dictionary of layouts for the ORE famrs.
        failures (list): A list of failure events for this farm``
        id_ (str): The unique identifier of the farm. Default to ``None``
        name (str): The name of the farm. Default to ``None``

    Returns:
        tuple[Farm, Port, Storage]: objects of Farm, Port and Storage
    """

    farm = Farm(
        inputs = inputs,
        farm_tech = farm_technologies,
        layouts = G_layouts,
        failures = failures
    )

    port = Port(
        id_= 'port_id',
        name = 'My_Port',
        location = {'lat': inputs.tseries.site_lat["value"], 'lon': inputs.tseries.site_lon["value"]}
    )

    storage = Storage(
        id_ = 'storage_id',
        max_space = 5
    )

    return farm, port, storage