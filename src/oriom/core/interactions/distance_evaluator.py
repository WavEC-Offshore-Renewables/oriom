

from numpy import sqrt


def calculate_distance(loc1, loc2):
    """
    Calculate the distance between two locations 

    Parameters:
        loc1 (dict): A dictionary with x and y position in meters.
        loc2 (dict): A dictionary with x and y position in meters.
    
    Returns:
        float: The distance between the two locations in meters.
    """

    dx = loc2['x'] - loc1['x']
    dy = loc2['y'] - loc1['y']

    return sqrt(dx**2 + dy**2)