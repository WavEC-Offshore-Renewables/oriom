import pandas as pandas
import math
from datetime import timedelta


def operation_consecutive(
        duration_shift:float,
        duration_inspection:float,
        transit_between_devices:float,
        hours:float,
        n_oper: int = None,
        operation_concluded:int = None,
        end_wait_start_list_idx:list = None,
        day_start_idx:int = None,
    ):

    """
    This function calculate consecutive operations that can be conducted in a day shift. Has two use:
        Preventive shift calculation:
            - The duration of the shift must not be exceeded.

        Deferred merging calculation.
            - The duration of the shift must not be exceeded.
            - The leadtime of the next merged operations must be lower than the time of the operation
                (compare index of wait to start with hours of work conducted, leadtime is higher merge cannot be done)

        NOTE For now the max duration of the shift is 12 h
        TODO vessel with overnight could stay longer wihout the need of return to port

    Args:
        duration_shift (:obj:`float`): The available duration of one working shift in hours taken into consideration.
            For shifts creation use = The total duration of one working shift
            For deferred merging use = The hours of delay of the op scheduled on which op can start
                (Ex: scheduled at 8.00, op can start till 11, duration_shift = 3 hours of delay)
        TODO implement different lengh duration for overnight stay
        duration_inspection (:obj:`float`): The time required to perform an inspection on a single device (in hours).
        transit_between_devices (:obj:`float`): The transit time needed to move between devices (in hours).
        hours (:obj:`float`): Time of duration for single operation shift (in hours).
            For shifts creation use (inspections and minor correction) = inspection duration + transit_to_site + transit_to port
            For deferred merging use = 0 as the shift duration is the extra time available (hours of delay on which op can start)
        n_oper (:obj:`int`): The total number of operations to be performed.
        operation_concluded (:obj:`int`, optional): The number of operations already completed (for MERGE DEFERRED).
            Defaults to None.
        end_wait_start_list_idx (:obj:`list`, optional): List of indices marking the end of waiting and start of operations
            (for MERGE DEFERRED). Defaults to None.
        day_start_idx (:obj:`int`, optional): The index indicating the start of the current day in the timeline.
            (for MERGE DEFERRED) Defaults to None.

    Returns:
        float: hours of the operations conducted, int: number of device inspected in the shift.
    """
    # Add first device conducted
    n_device_shift = 1

    while hours <= duration_shift:
        n_device_shift += 1
        hours += duration_inspection + transit_between_devices

        if end_wait_start_list_idx:
            # Index of temporal position on the end_wait_start_list_idx
            act_idx_pos_end_wait_start_list = operation_concluded+(n_device_shift-1)
            # Check if merging the O&M we exceed some limitations
            if hours > duration_shift or (                                  # Exceed the shift duration
                (operation_concluded+n_device_shift) > n_oper or            # Exceed the device to inspect
                (end_wait_start_list_idx[act_idx_pos_end_wait_start_list]-day_start_idx > hours)    # Leadtime of the operation is higher
            ):
                hours -= duration_inspection + transit_between_devices
                n_device_shift -=1
                break
        else:
            #if hours > duration_shift or n_device_shift > n_oper: TODO CHECK IN WORKING SHIFT HOW TO TUNE THIS IF WE NEED n_oper
            if hours > duration_shift:
                hours -= duration_inspection + transit_between_devices
                n_device_shift -= 1
                break

    return hours, n_device_shift


def operation_consecutive_simultaneously(
        duration_shift:float,
        duration_inspection:float,
        crew: int,
        transit_between_devices:float ,
        hours:float,
        n_oper: int = None,
        operation_concluded: int = None,
        end_wait_start_list_idx: list = None,
        day_start_idx: int = None
    ):

    """
    This function calculate consecutive operations that can be conducted in a day shift with simultaneous operations
    on devices dropping off the personnel, reaching a maximum number of crew members on board.

    It merge operations:
        - The leadtime of the next merged operations are respected
        - The duration of the shift is not exceeded.

        NOTE For now the max duration of the shift is 12 h,
        TODO vessel with overnight could stay longer wihout the need of return to port
        TODO Check as fix the case that the accumulation of transit between devices exceed the duration_inspection
            In such case the first crew end the first inspection before that the vessel is ready to take
            them and bring them in a new device

    It returns the hours of the operations, the number of device inspected and the crew list on the vessel

    Args:
        duration_shift (:obj:`float`): The available duration of one working shift in hours taken into consideration.
            For shifts creation use = The total duration of one working shift
            For deferred merging use = The hours of delay of the op scheduled on which op can start
                (Ex: scheduled at 8.00, op can start till 11, duration_shift = 3 hours of delay)
            TODO implement different lengh duration for overnight stay
        duration_inspection (:obj:`float`): The time required to perform an inspection on a single device (in hours).
        crew (:obj:`int`): Number of crew group that can be present on the vessel for the specific maintenance
            operation under analysis. Example if tech_per_dev = 2 and vessel.tech_capacity = 12, crew = 6
        transit_between_devices (:obj:`float`): The transit time needed to move between devices (in hours).
        hours (:obj:`float`): Time of duration for single operation shift (in hours).
            For shifts creation use (inspections and minor correction) = inspection duration + transit_to_site + transit_to port
            For deferred merging use = 0 as the shift duration is the extra time available (hours of delay on which op can start)
        n_oper (:obj:`int`): The total number of operations to be performed. Defaults to None
        operation_concluded (:obj:`int`, optional): The number of operations already completed previously (for MERGE DEFERRED).
            Defaults to None.
        end_wait_start_list_idx (:obj:`list`) List of index of oper_schedule on which end the leadtime of the
            components for the deferred operations
            TODO implement it only for component leadtime, remove vessel leadtime in case the vessel was already called for
            the deferred maintenance. Default to None
        day_start_idx (:obj:`int`): Index of oper_schedule on which the O&M are taking place (temporal line of the
            deferred maintenance operations). Default to None.

    Returns:
        number of last shifts, number of devices left, number of hours left, number of main shift
    """

    crew_list = []
    n_device_shift = 0

    # Till the hours of worked for the shift are lower than the maximum shift duration
    while hours <= duration_shift:
        n_device_shift += 1
        end_shift = False
        act_crew = 1

        # Till the crew limit of the vessel is not limited
        while act_crew < crew:
            # Add new device operation
            crew_list.append(act_crew)
            n_device_shift +=1
            act_crew +=1
            hours += transit_between_devices

            # Check if overcome merging limitations
            if end_wait_start_list_idx:
                # Index of temporal position on the end_wait_start_list_idx
                act_idx_pos_end_wait_start_list = operation_concluded+(n_device_shift-1)
                # Check if merging the O&M we exceed some limitations
                if hours > duration_shift or (                                  # Exceed the shift duration
                    (operation_concluded+n_device_shift) > n_oper or            # Exceed the device to inspect
                    (end_wait_start_list_idx[act_idx_pos_end_wait_start_list]-day_start_idx > hours)    # Leadtime of the operation is higher
                ):
                    act_crew -= 1
                    n_device_shift -= 1
                    hours -= transit_between_devices
                    end_shift = True
                    break
            else:
                if hours > duration_shift:
                    act_crew -= 1
                    n_device_shift -= 1
                    hours -= transit_between_devices
                    end_shift = True
                    break

            crew_list.append(act_crew)

        # If limitations are exceeded
        if end_shift:
            break
        else:
            if n_oper:
                if operation_concluded+n_device_shift >= n_oper:
                    break
            # Add new consecutive operation
            hours += transit_between_devices + duration_inspection
            if hours > duration_shift:
                hours -= transit_between_devices + duration_inspection
                break

    if n_device_shift==0:
        n_device_shift = 1
        crew_list.append(1)

    max_crew = max(crew_list)

    return hours, n_device_shift, max_crew


def last_oper(
    n_vessel:int,
    dev_left:int,
    duration_inspection:float,
    operation_total_duration:float,
    transit_between_devices:float,
    max_crew: int=1,
    n_shifts:int=None,

):
    """
    This function evaluate the last operations needed to conclude the shifts corrections after the operation_consecutive func only.
    If the operations end with this shift the funcion evaluate the specifications of the last shift.
    If the number of shift conducted exceed the number of vessel defined, reduce the shift conducted

    Returns the number of last shift needed, the number of device done, the durations of the last shift, the number_technicians_last,
    the number of normal shift conducted

    Args:
        n_vessel (:obj:`int`): The number of vessels for that type of vessel.
        dev_left (:obj:`int`): The number of total devices left to correct.
        n_device_shift (:obj:`int`): The numebr of devices done each main shift of work
        duration_inspection (:obj:`float`): The time required to perform an inspection on a single device (in hours).
        operation_total_duration (:obj:`float`): Time of inspection duration + transit_to_site + transit_to port (in hours).
        transit_between_devices (:obj:`float`): The transit time needed to move between devices (in hours).
        n_oper (:obj:`int`): The total number of operations to be performed.
        max_crew (:obj:`int`): The total number of crew on the vessels, if not passed as argument we are analyzing consecutive op.
            Default to 1.
        n_shifts (:obj:`int`): The number of shift simultaneously (n_vessel) that are made on a day of operation. If not passed as argument
            is an inspection working shift. Default to None.


    Returns:
        number of last shifts, number of devices left, number of hours left, number of main shift
    """

    # If all device are not corrected along this day of work, use max n_vessel as n_shift and last shift = 0
    if n_shifts:
        if n_shifts >= n_vessel:
            n_shifts = n_vessel
            dev_left = 0
            last_shift = 0
            left_hours = 0

    # If deferred corrections can be concluded on this day with a last shift
    if dev_left != 0:
        last_shift = 1
        if max_crew>1:
            # If the number of crew is lower than the number of devices to correct, we need to do a last shift
            if dev_left > max_crew:
                consecutive_oper = math.ceil(dev_left/max_crew)
                left_hours = operation_total_duration + duration_inspection*(consecutive_oper-1) + transit_between_devices*(dev_left-1)
                last_max_crew = max_crew
            else:
                left_hours = operation_total_duration + transit_between_devices*(dev_left-1)
                last_max_crew = dev_left
        else:
            left_hours = operation_total_duration + duration_inspection*(dev_left-1) + transit_between_devices*(dev_left-1)
            last_max_crew = 1

    else:
        last_shift = 0
        left_hours = 0
        last_max_crew = 0

    return last_shift, dev_left, left_hours, n_shifts, last_max_crew


def results_data(
        n_device_shift,
        dev_left,
        n_shifts,
        last_shift,
        operation_concluded,
        N_technicians_per_inspection,
        hours,
        left_hours,
        day_start_idx,
        day_start_oper,
        operation_total_duration,
        max_crew=None,
        last_max_crew = 1,
    ):
    """
    Function to evaluate results and return them

    Args:
        n_device_shift (:obj:`int`): The number of devices done in the shift.
        dev_left (:obj:`int`): The number of devices left to correct.
        n_shifts (:obj:`int`): The number of shifts conducted in the day.
        last_shift (:obj:`int`): The number of last shifts needed to conclude the operations.
        operation_concluded (:obj:`int`): The number of operations already completed previously (for MERGE DEFERRED).
        N_technicians_per_inspection (:obj:`int`): Number of technicians required for each inspection.
        hours (:obj:`float`): Hours worked in the shift.
        left_hours (:obj:`float`): Hours left for the last shift.
        day_start_idx (:obj:`int`): The index indicating the start of the current day in the timeline (for MERGE DEFERRED).
        day_start_oper (:obj:`datetime`): Start time of the operation. Defaults to None.
        max_crew (:obj:`int`, optional): Maximum crew on board. If not passed is consecutive operation. Defaults to None.
        last_max_crew (:obj:`int`, optional): Maximum crew on board for the last shift. Defaults to 1.

    Returns:
        tuple: Contains
            - operation_concluded (int): The number of operations already completed previously (for MERGE DEFERRED).
            - day_start_idx (int): The index indicating the start of the current day in the timeline.
            - day_shift_end (datetime): End time of the shift.
            - total_device_this_shift (int): Total number of devices done in this shift.
            - number_technicians (int): Number of technicians required for this shift.
            - n_vessel_used (int): Number of vessels used in this shift.
    """

    n_vessel_used = n_shifts+last_shift

    total_device_this_shift = n_device_shift * n_shifts + dev_left
    operation_concluded += total_device_this_shift

    if max_crew:
        number_technicians = N_technicians_per_inspection*(max_crew*n_shifts+last_max_crew*last_shift)
    else:
        # One crew each vessel as no simultaneous operation are conducted
        number_technicians = N_technicians_per_inspection*(n_vessel_used)
    hours_worked = max(hours, left_hours)
    day_start_idx += math.ceil(hours_worked + operation_total_duration)
    day_shift_end = day_start_oper + timedelta(hours = hours_worked + operation_total_duration)

    return operation_concluded, day_start_idx, day_shift_end, total_device_this_shift, number_technicians, n_vessel_used

if __name__ == '__main__':
    pass