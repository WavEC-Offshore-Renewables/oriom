import logging
import math
import pandas as pd
from datetime import timedelta, datetime

from logistic_tools.utils.aux_functions import safe_getattr
from logistic_tools.utils.read_dataframe_value import approximate_hourly_data

from logistic_tools.core.functions.logs_timeseries import logs_timeseries_func



class InspectionSiteCreation():
    """ Class to generate the Inspection at Site"""
    def __init__(self, inspection):
        self.inspection = inspection
        self.operation_completed = True
        self.inspection_campaign_flag = False

        # Get the operation schedules
        self.oper_schedule = safe_getattr(inspection, ["insp_class","ts_data","oper_sched"])


    def preventive_site_inspection(
        self,
        mother_vessel_inspection_campaign: dict,
        find_element_class: object,
        end_datetimes: list,
        end_stat_chart_datetimes: list,
        valid_datetimes: list,
        d: datetime
    ):
        """
        Main code to evaluate the inspection at site for all the devices
        
        The code evaluate for each device the tow to port, the inspection at port and the tow to site.
        To evaluate the date of start for each operation the code consider if there is an overlap with other operations
        in the same time interval, if there is an overlap the code reevaluate the date of start and date of end of the operation
        until there is no overlap with other operations.

        All the operations are stored in dict tow_at_port, insp_at_port and tow_at_site with key the device number
        and value a tuple with the date of end of the operation and the date of start of the operation.

        Add to the lists:
            - end_datetimes: end of the inspection operation for all the devices
            - end_stat_chart_datetimes: end of the inspection operation for statistical analysis
            - valid_datetimes: datetime of start of the inspection operation

        Args:
            mother_vessel_inspection_campaign (dict): Dictionary with mother vessel_id as first key year as second key and date of end of last inspection campaign as value.
                Only inspection with vessel 2 as mother vessel that have a periodicity > 1 year will be added to this dict
            find_element_class (object): Object from class :class:`FindElementClass`
            end_datetimes (list): List with the end datetimes of the inspection operations
            end_stat_chart_datetimes (list): List with the end datetimes for statistical analysis
            valid_datetimes (list): List with the valid datetimes of the inspection operations
            d (datetime): Datetime of start of the inspection operation
        """

        # Check if is an inspection campaing
        vessel_2_id = self.inspection.insp_class.vessel2_id
        if vessel_2_id and vessel_2_id in mother_vessel_inspection_campaign:
            self.inspection_campaign_flag = True
            year = d.year
            month = d.month
            day = d.day

            if (month,day) not in mother_vessel_inspection_campaign[vessel_2_id][year]:
                mother_vessel_inspection_campaign[vessel_2_id][year][(month,day)] = None

            # Take the date from the mother_vessel_inspection_campaign dict if is a inspection campaign
            if mother_vessel_inspection_campaign[vessel_2_id][year][(month,day)]:
                d = mother_vessel_inspection_campaign[vessel_2_id][year][(month,day)]
                d = approximate_hourly_data(data = d, round_up = True)

        date_continuous = d
        try:
            date_start = self.oper_schedule.loc[self.oper_schedule['datetime'] == date_continuous].iloc[0]
            dur_tot = date_start['dur_total']
            d_end_device = date_continuous + timedelta(hours=dur_tot)

            inspection_pmax = find_element_class.find_operation_stats_pmax(self.inspection.id)

            dur_total_perc = logs_timeseries_func.inspection_statistic_duration(self.oper_schedule, date_continuous, inspection_pmax)
            end_stat_chart_datetimes.append(date_continuous + timedelta(hours = dur_total_perc))
            date_continuous = d_end_device

        except (ValueError, IndexError) as e_:
            logging.warning(f'LogPreventive: Site inspection {self.inspection.id} not possible for at {date_continuous}: {e_}')
            self.operation_completed = False

        # Add the results to the lists if the inspection is completed
        if self.operation_completed:
            end_datetimes.append(d_end_device)
            valid_datetimes.append(d)
            if self.inspection_campaign_flag:
                mother_vessel_inspection_campaign[vessel_2_id][year][(month,day)] = d_end_device



if __name__ == '__main__':

    pass