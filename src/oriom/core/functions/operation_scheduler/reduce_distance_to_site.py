import logging
import re


def modify_distance_to_site(
        operation: object, 
        vessel_1: object,
        KM_DISTANCE: int = 5
):
    """
    Modify the distance to site for an operation
    
    Args:
        operation (object): object from class ´CorrectiveMinor´, ´CorrectiveMajor´ or ´InspectionSite´
        vessel_1 (object): vessel 1 used in the operation, element for class ´Vessels´
        KM_DISTANCE (int): distance of the mother vessel to site. Default to 5 km

    Return:
        float: duration of transit if the operation is not ´CorrectiveMajor´
        """
    
    duration_transit = ((KM_DISTANCE * 1000) / vessel_1.speed_transit) / 3600

    if hasattr(operation, 'failures'):
        # If the distance changes for the vessel considered
        if hasattr(operation, 'activities'):
            # Major correction
            for activity in operation.activities:
                if activity.location == 'transit':
                    activity.duration = duration_transit
                elif re.search(r'\btow\b', activity.name.lower()) is not None:
                    # This is a towing activity
                    activity.duration = ((KM_DISTANCE * 1000) / vessel_1.speed_tow) / 3600
        else:
            # Minor correction
            return duration_transit
    else:
        # Inspection site
        return duration_transit


def modify_distance(
        Config: object, 
        operation: object, 
        default_distance: float
)-> float: 
    """
    Calculate and modify the transit distance for vessels in an operation.

    Args:
        Config (object): Object class `Config_run`
        operation (list): object of class `InspectSite`, `CorrectiveMinor`, `CorrectiveMajor`
        default_distance (flaot): Default distance of the port to site

    Returns:
        float: transit from the port to the site for the considered operation
    """

    transit_duration = None
    vessel1 = getattr(operation, 'vessel1', None)
    vessel2 = getattr(operation, 'vessel2', None)

    # Case 1: vessel1 with reduced distance
    if Config.DIFF_DISTANCE and vessel1 and vessel1.type in getattr(Config, 'VESSEL_DIST_REDUCED_LIST', []):
        transit_duration = modify_distance_to_site(
            operation=operation,
            vessel_1=vessel1,
            KM_DISTANCE=Config.DIFF_KM_DISTANCE
        )
        logging.info(
            f"For operation {operation.id} with vessel ({vessel1.type}), "
            f"distance to site modified to {Config.DIFF_KM_DISTANCE} km"
        )

    # Default case if vessel1 doesn't meet criteria
    if transit_duration is None and vessel1:
        transit_duration = (default_distance / vessel1.speed_transit) / 3.6

    # Case 2: mother vessel
    if vessel2 and getattr(vessel2, 'mother_vessel', False):
        transit_duration = modify_distance_to_site(
            operation=operation,
            vessel_1=vessel1,
            KM_DISTANCE=Config.KM_MOTHER_VESSEL
        )
        logging.info(
            f"For operation {operation.id}, using mother vessel ({vessel2.type}), "
            f"distance to site modified to {Config.KM_MOTHER_VESSEL} km"
        )

    return transit_duration
