import random
import logging
import pandas as pd

from logistic_tools.utils.aux_functions import safe_getattr
from dateutil.relativedelta import relativedelta
from datetime import datetime


def take_op_schedule_tow(
    inspection: object, 
    find_element_class: object, 
    op_tow: str
)->pd.DataFrame:
    
    """ Take the operation_scheduler for the towing operation required"""

    tow_id = safe_getattr(inspection, ['insp_class', op_tow])
    tow_op_stat =  find_element_class.find_operation_stats(tow_id)
    oper_schedule_tow = safe_getattr(tow_op_stat, ['op_class', 'ts_data', 'oper_sched'])

    return oper_schedule_tow


def create_sublists(numbers, n):
    """This function splits a list of elements (numbers) into n sublists with sizes as evenly distributed as possible. 
    If the number of elements in the original list is not perfectly divisible by n, the remaining elements are 
    distributed one by one to the first few sublists.

    Args:
        numbers (list): The original list of elements to be divided.
        n (int): The number of sublists to create.

    Returns:
        list of lists: A list containing n sublists where each sublist contains a subset of the original elements. 
        The first sublists may contain one more element than the others to ensure that all elements are included.
        
    """
    sublist_length = len(numbers) // n
    remainder = len(numbers) % n
    sublists = []

    index = 0
    n = int(n)
    for i in range(n):
        sublist_size = sublist_length + (1 if i < remainder else 0)
        sublist_size = int(sublist_size)
        if sublist_size !=1:
            sublist = list(numbers[index : index + sublist_size])
            sublists.append(sublist)
        else:
            sublist = [numbers[index]]
            sublists.append(sublist)
        index += int(sublist_size)
    return sublists


def reciprocal(n):
    return(1.0/n)


def date_ranges_overlap(start1, end1, start2, end2):
    """
    Verify if two interval of time for tow intersecate
    To consider more more than one vessel for the towing operation add here a count.
    """
    if start1 == end2:
        return False
    else:
        return max(start1, start2) <= min(end1, end2)
    

def start_date_inspection(
    inspection: object,
    start_year: int, 
    start_month: int,
    n_lifetime: int,
)->list:
    """ 
    This function create a list of dates on which the all the 
    preventive maintenances of the lifetime will starts

    Args:
        inspections (:class:`~logistic_tools.classes.Operations.InspectionPort/Site`)
        start_year (int): Year of the start of the simulation
        start_month (int): Month of the start of the simulation
        n_lifetime (int): Number of years of the lifetime of the farm

    Returns:
        list
    """
    # Evaluation of starting of all the inspections along the lifetime
    if isinstance(inspection.insp_class.months,list) is True or inspection.insp_class.months is None:
        if inspection.insp_class.months is None:
            inspection.insp_class.months = list(range(1,13))
        if inspection.insp_class.months[-1] > start_month:
            y = start_year
            tot_years = n_lifetime
        else:
            y = start_year +1
            tot_years = n_lifetime-1
    else:
        if inspection.insp_class.months > start_month:
            y = start_year
            tot_years = n_lifetime
        else:
            y = start_year +1
            tot_years = n_lifetime-1
    start_date = datetime(start_year,start_month,1,8,0,0)                   ##### TODO HERE to add the day of start for deferred maintenance
    end_date = start_date + relativedelta(years=tot_years)

    # Take the dates to start preventive maintenance. If more months are selected to start it take the one with the lowest duration from statistic file 
    if inspection.insp_class.periodicity >=1:
        random.seed()
        if isinstance(inspection.insp_class.months,list) is True:
            months_insp = [str(c) for c in inspection.insp_class.months]
            filtered_dict = dict((key, value) for key, value in inspection.dur_total_dict.items() if key in months_insp)
            month = [k for k,v in filtered_dict.items()
                    if v == min(filtered_dict.values())]
            month = random.choice(month)
        else:
            month = inspection.insp_class.months

        list_year = [y]
        while y < start_year + tot_years:
            y = y + int(inspection.insp_class.periodicity)
            if y <=start_year + n_lifetime:
                list_year.append(y)
            else:
                continue
        datetimes = []
        
        day = inspection.insp_class.day_start                              # NOTE putted start of inspection of start of the month
        for i in list_year:
            month = int(month)
            if datetime(i,month,day,0,0,0) < end_date:
                datetimes.append(datetime(i,month,day,8,0,0))

    else:
        n_times = reciprocal(inspection.insp_class.periodicity)
        month_list = inspection.insp_class.months if isinstance(inspection.insp_class.months, list) else [inspection.insp_class.months]
        n_times = int(n_times)

        if len(month_list) < n_times:
            _e = 'Preferred months should be at least as many as the occurrence per year for '+str(inspection.id)
            logging.error('LogDates: '+_e)
            raise ValueError('LogDates: '+_e)
        month_split = create_sublists(month_list,n_times)
        datetimes = []
        list_year = list(range(y,y+n_lifetime))               # NOTE added here that tow to port in last year is not conducted
        for n in range(n_times):
            month_n = month_split[n]
            month_n_str = [str(c) for c in month_n]
            filtered_dict = dict((key, value) for key, value in inspection.dur_total_dict.items() if key in month_n_str)
            month_n = [k for k,v in filtered_dict.items()
                    if v == min(filtered_dict.values())]
            random.seed(n)
            month_n = random.choice(month_n)
            day = inspection.insp_class.day_start                            
            for i in list_year:
                month_n = int(month_n)
                if datetime(i,month_n,day,0,0,0) < end_date:
                    datetimes.append(datetime(i, month_n, day,6,0,0))           ##### IMPORTANT NOTE the hour choosen is at 6 AM, might put it at 00 of the day choosen
    
    return datetimes



if __name__ == '__main__':

    pass