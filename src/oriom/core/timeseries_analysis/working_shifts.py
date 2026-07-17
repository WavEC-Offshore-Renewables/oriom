import math
import logging

from oriom.core.functions.operation_scheduler.define_shift import output_working_shifts


def working_shifts(
    operation,
    duration_shift: float,
    transit: float,
    transit_between_devices: float,
    operation_to_group_with: bool=None,
    minor_op:bool=None
) -> dict:
    """
    Note:
        Working shift frunction returns a dictionary indicating the number of days needed to perform
        a campaign and the duration of the working day. Two possibilities:
            - One inspection:
                The inspection is studied in order ot understand how many days of work are needed. Since not all
                workdays are always identical, there is "main" number of days with its duration and one "last" day
                which may have a different durations if only some devices are left.
                The functions considers the possibility of dropping off personnel according to the shift and inspection
                time as well if any equipment (rob drone) is needed for which the vessel shall be nearby. Moreover multiple
                number of vessel can be dedicated to the campaign and overall duration is calculated accordingly.
            - Two inspections (if :attr:`merge` from :file:`C_inputs` is True):
                Two inspections are grouped and studied. Inspections are not required to have the same olcs, the operation
                schedule has a dedicated function that tries to schedule both inspections considering the different olcs
                requirements in the order that is more convenient based on the metocean conditions. In this case
                the "main" and "last" may refer to two inspections with different olcs to be studied in the timseseries.

    Args:
        operation (:class:`~oriom.classes.InspectionSite.InspectionSite`): Operation to be studied
        duration_shift (:obj:`float`): Maximum hours of working shift.
        transit (:obj:`float`): Hours for the transit to site.
        transit_between_devices (:obj:`float`): Hours for transit between
                devices.
        operation_to_group_with (:class:`~oriom.classes.InspectionSite.InspectionSite`):
            Default to ``None``.
        minor_op (:obj:`bool`): Flag to indicate minor correction operation. Default to ``False``.

    Raises:
        ValueError: If the number of technicians per inspection is higher
                than the maximum technicians transfered offshore.
        ValueError: If too many vessels are used.

    Returns:
        :obj:`dict`
    """

    def stricter_weather_limit(x1,x2)->float:
        """
        In case of two grouped inspections with different olcs, this function chooses the strictest set of olcs.

        Args:
            x1 (:obj:`float`): The first weather limit
            x2 (:obj: `float`) the second weather limit
        """
        if x1==None and x2!=None:
            y=x2
        elif x1!=None and x2==None:
            y=x1
        elif x1==None and x2==None:
            y=None
        else:
            y=max(x1,x2)
        return y


    def wt_inspection_within_shift(
            id_: str,
            N_devices_to_inspect:int,
            N_technicians_per_inspection: int,
            duration_shift: float,
            duration_inspection: float,
            N_vessels: int,
            rov: bool,
            minor_op: bool = False
        )-> dict:
        """
        This function calculates the number of working shifts, duration of shifts, number of inspections per shift, and number of technicians needed for a given inspection
        if the inspection time of each device is within the personnel shift.

        Args:
            id_ (:obj:`str`): Identifier for the inspection scenario.
            N_devices_to_inspect (:obj:`int`): Number of devices to inspect.
            N_technicians_per_inspection (:obj:`int`): Number of technicians per inspection.
            duration_shift (:obj:`float`): Maximum hours of working shift.
            duration_inspection (:obj:`float`): Duration of each inspection.
            N_vessels (:obj:`int`): Number of vessels available.
            rov (:obj:`bool`): Boolean indicating whether ROV is used.
            minor_op (:obj:`bool`): Flag to indicate minor correction operation. Default to ``False``.

        Returns:
            :obj:`dict`: A dictionary containing the working shifts and durations.
            :obj:`int`: Number of vessels used.
        """
        dict_operation_schedule={}

        # Check if is a minor operation, if so reduce the n_vessel to use and the device to correct/inspect
        if minor_op:
            N_devices_to_inspect = 1
            N_vessels = 1

        dict_operation_schedule_1 = output_working_shifts(
            N_devices_to_inspect,
            duration_shift,
            duration_inspection,
            rov,
            transit,
            transit_between_devices,
            vessel_type,
            N_technicians_on_vessel,
            N_technicians_per_inspection,
            N_vessels
        )

        dict_operation_schedule.update({f"{id_}{'-1'}":dict_operation_schedule_1})

        return dict_operation_schedule, N_vessels


    def wt_insepction_beyond_shift(
            op_: object,
            N_devices_to_inspect: int,
            N_technicians_per_inspection: int,
            duration_inspection: float,
            N_vessels: int
        ):
        """
        This function calculates the number of working shifts, duration of shifts, number of inspections per shift,
        and number of technicians needed for a given inspection if the inspection time of each device is beyond
        the personnel shift.

        NOTE: 
            This function is not used in the current version of the code. Anyway it could be taken into account
            the fact of using more crew on the vessel to conduct parallel inspections. Not mandatory as usually long inspection
            require high amout of personnel and the presence of the vessel itself along the operation

        Args:
            op_ (:obj:`Inspection_Site`): Class of inspection `Inspection_Site`.
            N_devices_to_inspect (:obj:`int`): Number of devices to inspect.
            N_technicians_per_inspection (:obj:`int`): Number of technicians per inspection.
            duration_inspection (:obj:`float`): Duration of each inspection.
            N_vessels (:obj:`int`): Number of vessels available.
        Returns:
            :obj:`dict`: A dictionary containing the working shifts and durations.
            :obj:`int`: Number of vessels used.
        """

        def output_working_shifts_beyond(
                N_devices: int,
                duration_inspection: float,
                op_: object
            ):
            """
            Calculate the number of working shifts required based on the number of devices, inspection duration, and other parameters.

            This function does not consider the number of vessels, as it is assumed that the number of vessels cause such
            parameter has been taken into consideration before the call of the function.

            Args:
                N_devices (:obj:`int`): Number of devices to inspect
                duration_inspection (:obj:`float`): Duration of each inspection
                op_ (:obj:`Inspection_Site`): Class of inspection `Inspection_Site`.

            Returns:
                :obj:`dict`: Dictionary containing information about the main and last working shifts,
                including the number of shifts, duration, number of inspections per shift, and number of technicians needed.
            """
            i = 1
            available_time = duration_shift - 2*transit
            n_shifts = 0
            while i <= N_devices:
                inspection_done = available_time
                n_shifts += 1
                left = duration_inspection - inspection_done
                while left > (duration_shift - 2*transit - transit_between_devices):
                    n_shifts += 1
                    left = left - (duration_shift - 2*transit)
                available_time = duration_shift - 2*transit - transit_between_devices - left
                i += 1

            last_shift = 0
            left_hours = 0
            if left!= 0:
                last_shift = 1
                left_hours = left + 2*transit
            try:
                number_crew = int(op_.tech_per_device)
            except AttributeError:
                number_crew = int(op_.tech_required)


            dict_operation_schedule = {
                    'main_working_shift': {
                            'number_shifts': n_shifts,
                            'duration_shift': round(duration_shift, 2),
                            'number_inspections_per_shift': 1,
                            'number_technicians_needed': int(N_technicians_per_inspection),
                            'number_crew': number_crew
                    },
                    'last_working_shift': {
                            'number_shifts': int(last_shift),
                            'duration_shift': round(left_hours, 2),
                            'number_inspections_per_shift': 1,
                            'number_technicians_needed': int(N_technicians_per_inspection),
                            'number_crew': number_crew

                    }
            }
            return dict_operation_schedule

        dict_operation_schedule = {}
        # Considering various number of vessels
        # if only one vessel is used

        if N_devices_to_inspect == 1:
            dict_operation_schedule_1 = output_working_shifts_beyond(1,duration_inspection, op_)
            dict_operation_schedule_1["main_working_shift"].update({'number_vessels':1})
            N_vessels = 1
            if dict_operation_schedule_1["last_working_shift"]['number_shifts'] != 0:
                dict_operation_schedule_1["last_working_shift"].update({'number_vessels':1})
                dict_operation_schedule.update({f"{op_.id}{'-1'}":dict_operation_schedule_1})
        else:
            # If more vessels are used and the number of devices is divisible by the number of vessels
            if (N_devices_to_inspect % N_vessels) == 0:
                N_devices = N_devices_to_inspect/N_vessels
                dict_operation_schedule_1 = output_working_shifts_beyond(N_devices,duration_inspection, op_)
                dict_operation_schedule_1["main_working_shift"].update({'number_vessels':N_vessels})
                if dict_operation_schedule_1["last_working_shift"]['number_shifts'] != 0:
                    dict_operation_schedule_1["last_working_shift"].update({'number_vessels':N_vessels})
                    dict_operation_schedule.update({f"{op_.id}{'-1'}":dict_operation_schedule_1})
            # In such case a new dict operation schedule is created for the shift with the remaining devices using the
            # same number of vessels as devices left to inspect
            else:
                N_devices = N_devices_to_inspect // N_vessels
                dict_operation_schedule_1 = output_working_shifts_beyond(N_devices,duration_inspection, op_)
                dict_operation_schedule_1["main_working_shift"].update({'number_vessels':N_vessels})
                if dict_operation_schedule_1["last_working_shift"]['number_shifts'] != 0:
                    dict_operation_schedule_1["last_working_shift"].update({'number_vessels':N_vessels})
                N_devices_left = N_devices_to_inspect - (N_devices*(N_vessels))
                dict_operation_schedule_2 = output_working_shifts_beyond(N_devices_left,duration_inspection, op_)
                dict_operation_schedule_2["main_working_shift"].update({'number_vessels':N_devices_left})
                if dict_operation_schedule_2["last_working_shift"]['number_shifts'] != 0:
                    dict_operation_schedule_2["last_working_shift"].update({'number_vessels':N_devices_left})
                dict_operation_schedule.update({f"{op_.id}{'-1'}":dict_operation_schedule_1})
                dict_operation_schedule.update({f"{op_.id}{'-2'}":dict_operation_schedule_2})

        return dict_operation_schedule, N_vessels


    # MAIN CODE
    try:
        N_devices_to_inspect_1 = sum([
                operation.intervened_wtg,
                operation.intervened_wec,
                operation.intervened_pv
        ])
        if N_devices_to_inspect_1 == 0:
            # It means that the inspected asset is a cable
            N_devices_to_inspect_1 = 1
            _w = 'OperationInspectionSite: total number of devices of operation '
            _w += '%s is considered 1 cable.' % operation.id
            logging.warning(_w)
        duration_inspection_1 = operation.dur_per_device
        N_technicians_per_inspection_1 = operation.tech_per_device
    except AttributeError:
        N_devices_to_inspect_1=1
        duration_inspection_1 = operation.duration_net
        N_technicians_per_inspection_1 = operation.tech_required
    N_vessels = operation.vessel1_qt
    vessel_type = operation.vessel1.type
    if N_devices_to_inspect_1 <= N_vessels:
        N_vessels == N_devices_to_inspect_1
    N_technicians_on_vessel = operation.vessel1.crew_capacity
    if N_technicians_per_inspection_1 > N_technicians_on_vessel:
        _e = 'Vessel crew capacity lower than technicians needed'
        logging.error('OperationInspection:'+_e)
        raise ValueError(_e)
    if operation.rov_drone is not None:
        rov_1 = True
    else:
        rov_1 = False
    if operation_to_group_with is not None:
        if operation_to_group_with.id[0:3] == 'oce':
            _e = 'Common inspections cannot be grouped'
            logging.error('OperationInspection:'+ _e)
            raise ValueError(_e)
        N_devices_to_inspect_2 = sum([
            operation_to_group_with.intervened_wtg,
            operation_to_group_with.intervened_wec,
            operation_to_group_with.intervened_pv
        ])
        if N_devices_to_inspect_2 == 0:
            _e = 'Export cable inspection cannot be grouped with another inspection'
            logging.error('OperationInspection: '+_e)
            raise ValueError(_e)

        duration_inspection_2 = operation_to_group_with.dur_per_device
        N_technicians_per_inspection_2 = operation_to_group_with.tech_per_device
        if operation_to_group_with.rov_drone is not None:
            rov_2 = True
        else:
            rov_2 = False
    else:
        N_devices_to_inspect_2 = None


    op_working_shifts = {}
    data_working_shifts = {}

    if N_devices_to_inspect_2 is None:
        if duration_inspection_1 < (duration_shift - 2*transit):
            dict_operation_schedule, N_vessels = wt_inspection_within_shift(operation.id,N_devices_to_inspect_1,N_technicians_per_inspection_1,duration_shift,duration_inspection_1,N_vessels,rov_1, minor_op)
        elif duration_inspection_1 > (duration_shift - 2*transit):
            dict_operation_schedule, N_vessels = wt_insepction_beyond_shift(operation,N_devices_to_inspect_1,N_technicians_per_inspection_1,duration_inspection_1,N_vessels)

        if N_technicians_per_inspection_1 > N_technicians_on_vessel*N_vessels:
            _e = ('Number of technicians per inspection cannot be higher than the maximum technicians transfered offshore')
            raise ValueError(_e)

        for _,k in dict_operation_schedule.items():
            if k['main_working_shift']['number_shifts'] < 0:
                _e = 'Too many vessels are used'
                raise ValueError(_e)

        main_ws, last_ws = 0, 0
        dur_main, dur_last = 0, 0
        N_vessels_last = 0
        crew_main, crew_last = 0, 0
        n_dev_inspected_main_shift, n_dev_inspected_last_shift = 0, 0
        for _,k in dict_operation_schedule.items():
            main_ws = max(main_ws, k['main_working_shift']['number_shifts'])
            last_ws = max(last_ws, k['last_working_shift']['number_shifts'])
            dur_main = max(dur_main, k['main_working_shift']['duration_shift'])
            dur_last = max(dur_last, k['last_working_shift']['duration_shift'])
            N_vessels_last = max(N_vessels_last, k['last_working_shift']['number_vessels'])
            N_vessels = k['main_working_shift']['number_vessels']
            crew_main = max(crew_main, k['main_working_shift']['number_crew'])
            crew_last = max(crew_last, k['last_working_shift']['number_crew'])
            n_dev_inspected_main_shift = max(n_dev_inspected_main_shift, k['main_working_shift']['number_inspections_per_shift'])
            n_dev_inspected_last_shift = max(n_dev_inspected_last_shift, k['last_working_shift']['number_inspections_per_shift'])

        olc_main = {'hs':operation.hs,'tp':operation.tp,'ws':operation.ws,'ws_hub':operation.ws_hub,'cs':operation.cs}
        data_working_shifts.update({
                'id_main': operation.id,
                'days_main':main_ws+last_ws,
                'duration_main': max(dur_main,dur_last),
                'rov_main': rov_1,
                'id_grouped': None,
                'days_grouped': None,
                'duration_grouped':None,
                'rov_grouped': None,
                'olc_main': olc_main,
                'olc_last': None,
                'n_vessels_main': N_vessels,
                'n_vessels_last': N_vessels_last
        })
        op_working_shifts.update({
                'number_shifts_main':main_ws,
                'number_shifts_last':last_ws,
                'duration_shift_main':dur_main,
                'duration_shift_last':dur_last,
                'olc_main': olc_main,
                'olc_last': None,
                'n_vessels_main': N_vessels,
                'n_vessels_last': N_vessels_last,
                'n_crew_main': crew_main,
                'n_crew_last': crew_last,
                'n_dev_inspected_main_shift': n_dev_inspected_main_shift,
                'n_dev_inspected_last_shift': n_dev_inspected_last_shift
        })
        try:
            operation.n_vessel_main = N_vessels
            operation.n_vessel_last = 0
        except AttributeError: pass
    else:
        if N_vessels == 1:
            _e = 'No shared vessel can be done with only one vessel'   # WHY NOT?
            raise ValueError(_e)
        else:
            vessel1 = math.ceil(N_vessels/2)
            vessel2 = N_vessels-vessel1
            if duration_inspection_1 < (duration_shift - 2*transit):
                dict_operation_schedule_1, _ = wt_inspection_within_shift(operation.id,N_devices_to_inspect_1,N_technicians_per_inspection_1,duration_shift,duration_inspection_1,N_vessels,rov_1,minor_op)
            elif duration_inspection_1 > (duration_shift - 2*transit):
                dict_operation_schedule_1, _ = wt_insepction_beyond_shift(operation,N_devices_to_inspect_1,N_technicians_per_inspection_1,duration_inspection_1,N_vessels)
            if duration_inspection_2 < (duration_shift - 2*transit):
                dict_operation_schedule_2, _ = wt_inspection_within_shift(operation_to_group_with.id,N_devices_to_inspect_2,N_technicians_per_inspection_2,duration_shift,duration_inspection_2,N_vessels,rov_2,minor_op)
            elif duration_inspection_2 > (duration_shift - 2*transit):
                dict_operation_schedule_2, _ = wt_insepction_beyond_shift(operation_to_group_with,N_devices_to_inspect_2,N_technicians_per_inspection_2,duration_inspection_2,N_vessels)

            number_shifts_main = 0
            number_s_1 = 0
            number_s_2 = 0
            for _, shifts in dict_operation_schedule_1.items():
                number_s_1 += shifts["main_working_shift"]["number_shifts"]+shifts["last_working_shift"]['number_shifts']
            number_shifts_main_1 = max(number_shifts_main, number_s_1)
            for _, shifts in dict_operation_schedule_2.items():
                number_s_2 += shifts["main_working_shift"]["number_shifts"]+shifts["last_working_shift"]['number_shifts']
            number_shifts_main_2 = max(number_shifts_main, number_s_2)
            left_dev = None
            if number_shifts_main_1 == number_shifts_main_2 and vessel1==vessel2:
                dict_operation_schedule = dict_operation_schedule_1
                for _, shifts in dict_operation_schedule_2.items():
                    shifts["main_working_shift"]["number_shifts"] = 0
                    shifts["last_working_shift"]["number_shifts"] = 0
                    shifts["main_working_shift"]["duration_shift"] = 0
                    shifts["last_working_shift"]["duration_shift"] = 0
                id_1 = operation.id
                id_2 = operation_to_group_with.id
                rov1 = rov_1
                rov2 = rov_2

                olc_main = {
                        'hs': stricter_weather_limit(operation.hs,operation_to_group_with.hs),
                        'tp': stricter_weather_limit(operation.tp,operation_to_group_with.tp),
                        'ws': stricter_weather_limit(operation.ws,operation_to_group_with.ws),
                        'ws_hub': stricter_weather_limit(operation.ws_hub,operation_to_group_with.ws_hub),
                        'cs': stricter_weather_limit(operation.cs,operation_to_group_with.cs)
                    }
                olc_last = {
                        'hs': None,
                        'tp': None,
                        'ws': None,
                        'ws_hub': None,
                        'cs': None
                    }
            else:
                if number_shifts_main_1 <= number_shifts_main_2:
                    id_1 = operation.id
                    id_2 = operation_to_group_with.id
                    duration1 = duration_inspection_1
                    Ndevice1 = N_devices_to_inspect_1
                    duration2 = duration_inspection_2
                    Ndevice2 = N_devices_to_inspect_2
                    rov1 = rov_1
                    rov2 = rov_2
                    tech1 = N_technicians_per_inspection_1
                    tech2 = N_technicians_per_inspection_2
                    olc_main = {
                            'hs': stricter_weather_limit(operation.hs,operation_to_group_with.hs),
                            'tp': stricter_weather_limit(operation.tp,operation_to_group_with.tp),
                            'ws': stricter_weather_limit(operation.ws,operation_to_group_with.ws),
                            'ws_hub': stricter_weather_limit(operation.ws_hub,operation_to_group_with.ws_hub),
                            'cs': stricter_weather_limit(operation.cs,operation_to_group_with.cs)
                    }
                    olc_last = {
                            'hs':operation_to_group_with.hs,
                            'tp':operation_to_group_with.tp,
                            'ws':operation_to_group_with.ws,
                            'ws_hub':operation_to_group_with.ws_hub,
                            'cs':operation_to_group_with.cs
                        }
                else:
                    op2 = operation
                    op1 = operation_to_group_with
                    duration1 = duration_inspection_2
                    Ndevice1 = N_devices_to_inspect_2
                    duration2 = duration_inspection_1
                    Ndevice2 = N_devices_to_inspect_1
                    rov1 = rov_2
                    rov2 = rov_1
                    tech1 = N_technicians_per_inspection_2
                    tech2 = N_technicians_per_inspection_1
                    olc_main = {
                        'hs': stricter_weather_limit(operation.hs,operation_to_group_with.hs),
                        'tp': stricter_weather_limit(operation.tp,operation_to_group_with.tp),
                        'ws': stricter_weather_limit(operation.ws,operation_to_group_with.ws),
                        'ws_hub': stricter_weather_limit(operation.ws_hub,operation_to_group_with.ws_hub),
                        'cs': stricter_weather_limit(operation.cs,operation_to_group_with.cs)
                    }
                    olc_last = {
                            'hs':operation.hs,
                            'tp':operation.tp,
                            'ws':operation.ws,
                            'ws_hub':operation.ws_hub,
                            'cs':operation.cs
                        }

                if duration1 < (duration_shift - 2*transit):
                    dict_operation_schedule_1, v1 = wt_inspection_within_shift(op1.id,Ndevice1,tech1,duration_shift,duration1,vessel1,rov1,minor_op)
                elif duration_inspection_1 > (duration_shift - 2*transit):
                    dict_operation_schedule_1, v1 = wt_insepction_beyond_shift(op1,Ndevice1,tech1,duration1,vessel1)
                if duration_inspection_2 < (duration_shift - 2*transit):
                    dict_operation_schedule_2, v2 = wt_inspection_within_shift(op2.id,Ndevice2,tech2,duration_shift,duration2,vessel2,rov2,minor_op)
                elif duration_inspection_2 > (duration_shift - 2*transit):
                    dict_operation_schedule_2, v2 = wt_insepction_beyond_shift(op2,Ndevice2,tech2,duration2,vessel2)

                vessel1 = v1+v2
                n_days = 0
                n_days_2 = 0
                for _,k in dict_operation_schedule_1.items():
                    n_days=max(n_days,k["main_working_shift"]['number_shifts']+k['last_working_shift']['number_shifts'])
                for _,k in dict_operation_schedule_2.items():
                    n_days_2=max(n_days,k["main_working_shift"]['number_shifts'])
                left_dev = Ndevice2-math.floor((Ndevice2 * n_days)/n_days_2)
                if duration_inspection_2 < (duration_shift - 2*transit):
                    dict_operation_schedule_2, vessel2 = wt_inspection_within_shift(op2.id,left_dev,tech2,duration_shift,duration2,N_vessels,rov2,minor_op)
                elif duration_inspection_2 > (duration_shift - 2*transit):
                    dict_operation_schedule_2, vessel2 = wt_insepction_beyond_shift(op2,left_dev,tech2,duration2,N_vessels)

            main_ws = 0
            last_ws = 0
            dur_main = 0
            dur_last = 0
            for i,k in dict_operation_schedule_1.items():
                main_ws = max(main_ws,k['main_working_shift']['number_shifts'])
                last_ws = max(last_ws,k['last_working_shift']['number_shifts'])
                dur_main = max(dur_main, k['main_working_shift']['duration_shift'])
                dur_last = max(dur_last, k['last_working_shift']['duration_shift'])
            main_ws_g = 0
            last_ws_g = 0
            dur_main_g = 0
            dur_last_g = 0
            for i,k in dict_operation_schedule_2.items():
                main_ws_g = max(main_ws_g,k['main_working_shift']['number_shifts'])
                last_ws_g = max(last_ws_g,k['last_working_shift']['number_shifts'])
                dur_main_g = max(dur_main_g, k['main_working_shift']['duration_shift'])
                dur_last_g = max(dur_last_g, k['last_working_shift']['duration_shift'])

            data_working_shifts.update({
                    'id_main': op1.id,
                    'days_main':main_ws+last_ws,
                    'duration_main': max(dur_main,dur_last),
                    'rov_main': rov1,
                    'id_grouped': op2.id,
                    'days_grouped': main_ws+last_ws+main_ws_g+last_ws_g,
                    'duration_grouped':max(dur_main_g,dur_last_g),
                    'rov_grouped': rov2,
                    'olc_main': olc_main,
                    'olc_last': olc_last,
                    'n_vessels_main': vessel1,
                    'n_vessels_last': vessel2
            })
            op_working_shifts.update({
                    'number_shifts_main':main_ws+last_ws,
                    'number_shifts_last':main_ws_g+last_ws_g,
                    'duration_shift_main':max(dur_main,dur_last),
                    'duration_shift_last':max(dur_main_g,dur_last_g),
                    'olc_main': olc_main,
                    'olc_last': olc_last,
                    'n_vessels_main': vessel1,
                    'n_vessels_last': vessel2
            })

            operation.n_vessel_main = vessel1
            operation.n_vessel_last = vessel2

    return op_working_shifts, data_working_shifts


if __name__ == '__main__':
    pass