import datetime
import math
import pandas as pd

from logistic_tools.core.functions.operation_scheduler.shift_functions import operation_consecutive
from logistic_tools.core.functions.operation_scheduler.shift_functions import operation_consecutive_simultaneously
from logistic_tools.core.functions.operation_scheduler.shift_functions import last_oper
from logistic_tools.core.functions.operation_scheduler.shift_functions import results_data


def merge_shift_deferred(
    duration_shift:float, 
    duration_inspection:float, 
    transit_between_devices:float, 
    operation_total_duration:float,
    n_vessel:int,
    n_oper: int,
    operation_concluded:int, 
    end_wait_start_list_idx:list,
    day_start_idx:int,
    N_technicians_on_vessel:int,
    N_technicians_per_inspection:int,
    vessel_type:str,
    rov:bool,
    day_start_oper:datetime
):
    """
    Function to evaluate the merging of deferred operations. If they are not merged anyway the deferred operations
    will be conducted cronologically one after the other and not all together simultaneously.
    
    Args:
        duration_shift (:obj:`float`): The total duration of one working shift in hours taken into consideration. 
            TODO implement different lengh duration for overnight stay
        duration_inspection (:obj:`float`): The time required to perform an inspection on a single device (in hours).
        transit_between_devices (:obj:`float`): The transit time needed to move between devices (in hours).
        operation_total_duration (:obj:`float`): Time of inspection duration + transit_to_site + transit_to port (in hours).
        n_vessel (:obj:`int`): The number of vessels for that type of vessel.
        n_oper (:obj:`int`): The total number of operations to be performed.
        operation_concluded (:obj:`int`, optional): The number of operations already completed previously (for MERGE DEFERRED). 
            Defaults to None.
        end_wait_start_list_idx (:obj:`list`, optional): List of indices marking the end of waiting and start of operations
            (for MERGE DEFERRED). Defaults to None.
        day_start_idx (:obj:`int`, optional): The index indicating the start of the current day in the timeline. 
            (for MERGE DEFERRED) Defaults to None.
        N_technicians_on_vessel (:obj:`int`, optional): Number of technicians on board the vessel. Defaults to None.
        N_technicians_per_inspection (:obj:`int`, optional): Number of technicians required for each inspection. Defaults to None.
        vessel_type (:obj:`str`, optional): Type of vessel used for the operation. Defaults to None.
        rov (:obj:`bool`, optional): Indicates if ROV is used. Defaults to False.
        day_start_oper (:obj:`datetime`, optional): Start time of the operation. Defaults to None.

    Returns:
        tuple: Contains
            - operation_concluded (int): The number of operations completed till now.
            - day_start_idx (int): The index indicating the start of the current day in the timeline.
            - day_shift_end (datetime): End time of the shift.
            - total_device_this_shift (int): Total number of devices done in this shift.
            - number_technicians (int): Number of technicians required for this shift.
            - n_vessel_used (int): Number of vessels used in this shift.
    """
    hours = 0

    ## if rov are needed than the vessel must be there present, if is a special vessel the vessel must be present
    ## Only consecutive operations can be conducted
    if rov is True or 'ctv' not in vessel_type or transit_between_devices >= duration_inspection:       # IMPORTANT NOTE, modify here the type name, need to come from inputs
        # Calculate how many device can be done consecutively in the same shift
        hours, n_device_shift = operation_consecutive(
            duration_shift = duration_shift, 
            duration_inspection = duration_inspection, 
            transit_between_devices = transit_between_devices, 
            hours = hours,
            n_oper = n_oper,
            operation_concluded = operation_concluded, 
            end_wait_start_list_idx = end_wait_start_list_idx, 
            day_start_idx = day_start_idx
        )

        max_crew=1
    else:
        crew = math.floor(N_technicians_on_vessel/N_technicians_per_inspection)
        # First adding the max number of crew on vessel, then consider how many other inspection can be done after the first one in the same timeshift
        hours, n_device_shift, max_crew = operation_consecutive_simultaneously(
            duration_shift = duration_shift, 
            duration_inspection = duration_inspection, 
            crew = crew, 
            transit_between_devices = transit_between_devices, 
            hours = hours, 
            n_oper = n_oper,
            operation_concluded = operation_concluded,
            end_wait_start_list_idx = end_wait_start_list_idx, 
            day_start_idx = day_start_idx
        )
    # Evaluate how many vessels (shifts) are conducted in this shift and if are lefted device to correct
    n_shifts, dev_left = divmod((n_oper-operation_concluded),n_device_shift)
    if n_shifts == 0:
        hours = 0

    last_shift, dev_left, left_hours, n_shifts, last_max_crew = last_oper(
        n_vessel = n_vessel, 
        dev_left = dev_left, 
        duration_inspection = duration_inspection, 
        operation_total_duration = operation_total_duration, 
        transit_between_devices = transit_between_devices, 
        max_crew = max_crew, 
        n_shifts = n_shifts
    )
    
    operation_concluded, day_start_idx, day_shift_end, total_device_this_shift, number_technicians, n_vessel_used = results_data(
        n_device_shift = n_device_shift, 
        dev_left = dev_left, 
        n_shifts = n_shifts, 
        last_shift = last_shift, 
        operation_concluded = operation_concluded, 
        N_technicians_per_inspection = N_technicians_per_inspection, 
        hours = hours, 
        left_hours = left_hours, 
        day_start_idx = day_start_idx, 
        day_start_oper = day_start_oper, 
        max_crew = max_crew, 
        last_max_crew = last_max_crew,
        operation_total_duration = operation_total_duration
    )


    return operation_concluded, day_start_idx, day_shift_end, total_device_this_shift, number_technicians, n_vessel_used


def output_working_shifts(
        N_devices: int,
        duration_shift: float,
        duration_inspection: float,
        rov: bool,
        transit: float,
        transit_between_devices: float,
        vessel_type: str,
        N_technicians_on_vessel: int,
        N_technicians_per_inspection: int,
        N_vessels: int,
    )->dict:

    """
    Calculate the number of working shifts required based on the number of devices, inspection duration, and other parameters.
    It takes into account if more crew can be brought on the vessels and if each crew can conduct more than one inspection along the shift
    
    Args:
        N_devices (:obj:`int`): Number of devices to inspect
        duration_shift (:obj:`float`): Maximum hours of working shift.
        duration_inspection (:obj:`float`): Duration of each inspection
        rov (:obj:`bool`): Boolean indicating if ROV is used
        transit (:obj:`float`): Hours for the transit to site.
        transit_between_devices (:obj:`float`): Hours for transit between devices.
        vessel_type (:obj:`str`): Type of vessel used for the operation.
        N_technicians_on_vessel (:obj:`int`): Maximum number of technicians on the vessel.
        N_technicians_per_inspection (:obj:`int`): Number of technicians per inspection.
        N_vessels (:obj:`int`): Number of vessels available/considered.

    Returns:
        :obj:`dict`: Dictionary containing information about the main and last working shifts, 
        including the number of shifts, duration, number of inspections per shift, and number of technicians needed.
    """

    inspection_based_on_time = 0
    hours = duration_inspection + 2*transit
    operation_total_duration = hours


    ## NOTE if rov are needed than the vessel must be there present, if is a special vessel the vessel must be present
    if rov is True or 'ctv' not in vessel_type or transit_between_devices >= duration_inspection: 
        hours, inspection_based_on_time = operation_consecutive(
            duration_shift = duration_shift, 
            duration_inspection = duration_inspection, 
            transit_between_devices = transit_between_devices, 
            hours = hours,
        )
        max_crew=1
    else:
        crew = math.floor(N_technicians_on_vessel/N_technicians_per_inspection)
        # First adding the max number of crew on vessel, then consider how many other inspection can be done after the first one in the same timeshift
        hours, inspection_based_on_time, max_crew = operation_consecutive_simultaneously(
            duration_shift = duration_shift, 
            duration_inspection = duration_inspection, 
            crew = crew, 
            transit_between_devices = transit_between_devices, 
            hours = hours
        )

    device_per_shift = inspection_based_on_time*N_vessels
    n_shifts, dev_left = divmod(N_devices, device_per_shift)

    n_main_vess = N_vessels
    normal_insp_per_shift = inspection_based_on_time

    main_h_last_shift = 0
    last_shift_operation = 0
    n_last_vess_shift = 0
    normal_insp_per_last_shift = 0

    if dev_left != 0:
        last_shift_operation = 1
        # Calculate how many vessel effectuate a main shift in the last shift and reduce device_left
        n_last_vess_shift = dev_left//inspection_based_on_time
        if n_last_vess_shift != 0:
            main_h_last_shift = hours
            normal_insp_per_last_shift = normal_insp_per_shift

        # Calculate effective dev_left with differences in the shift
        dev_left -= n_last_vess_shift*inspection_based_on_time

    # Case in which no main shift are conducted reset main value
    if n_shifts == 0:
        n_main_vess = 0
        hours = 0
        normal_insp_per_shift = 0

    last_shift, dev_left, left_hours, _, number_crew_last = last_oper(
        n_vessel = N_vessels-n_last_vess_shift, 
        dev_left = dev_left, 
        duration_inspection = duration_inspection, 
        operation_total_duration = operation_total_duration, 
        transit_between_devices = transit_between_devices,
        max_crew = max_crew 
    )
    # If more than one vessel are out, take the longest duration of the shift
    left_hours = max(left_hours, main_h_last_shift)

    dict_working_shift = {
            'main_working_shift': {
                    'number_shifts': int(n_shifts),
                    'duration_shift': round(hours, 2),
                    'number_inspections_per_shift': int(max(normal_insp_per_shift, inspection_based_on_time)) if n_shifts > 0 else 0,
                    'number_vessels': int(n_main_vess),
                    'number_crew': max_crew
            },
            'last_working_shift': {
                    'number_shifts': int(max(last_shift_operation,last_shift)),
                    'duration_shift': round(left_hours, 2),
                    'number_inspections_per_shift': int(max(normal_insp_per_last_shift,dev_left)) if int(max(last_shift_operation,last_shift)) > 0 else 0,
                    'number_vessels': int(n_last_vess_shift+last_shift),
                    'number_crew': max(number_crew_last, max_crew)
            }
    }

    return dict_working_shift
    
if __name__ == '__main__':
    pass