import logging
import math
import os
import pandas as pd
from datetime import timedelta, datetime

from logistic_tools.utils.aux_functions import safe_getattr
from logistic_tools.core.functions.logs_timeseries import logs_preventive_aux


class InspectionPortCreation():
    """
    Class to generate and manage the Inspection at Port considering towing, inspection, WoW, n_vessels and port spaces
    
    Attributes:
        inspection (: object): object of class ``InspectionPort`` containing inspection metadata and schedules.
        n_device_at_port (: int) Number of devices that can be handled at the port simultaneously.
        n_device_stored_at_port (: int): Number of devices that can be stored at the port.
        find_element_class (: object) callable used by logs_preventive_aux to find classes/elements in schedules.
        shutdown_col (: str) or NoneColumn name in the schedule DataFrame containing shutdown durations to be accumulated,
            or None if no shutdown column should be considered.
        tow_at_port (: dict): Dictionary storing towing to port operations; keys are device indices, values are tuples (end_datetime, start_datetime).
        tow_at_site (: dict): Dictionary storing towing to site operations; keys are device indices, values are tuples (end_datetime, start_datetime).
        insp_at_port (: dict): Dictionary storing inspection at port operations; keys are device indices, values are tuples (end_datetime, start_datetime).
        operation_completed (: bool): Flag indicating whether the entire inspection operation was completed successfully.
        tot_device (: int): Total number of devices to be inspected.
        dev_idx_station_port (: int): Index for port stage of the current device being processed for port operations.
        oper_schedule_insp (: pd.DataFrame): DataFrame containing the operation schedule for inspections at port.
        oper_schedule_tow_port (: pd.DataFrame): DataFrame containing the operation schedule for towing to port.
        oper_schedule_tow_site_only (: pd.DataFrame): DataFrame containing the operation schedule for towing to site.
        oper_schedule_tow_site_port (: pd.DataFrame): DataFrame containing the operation schedule for towing to site and port.

        NOTE: The utilization of device to store at port (wet storage) must be implemented
    """

    def __init__(self, inspection, n_device_at_port, n_device_stored_at_port, find_element_class, shutdown_col):
        """
        Args:
            inspection (: object): object of class ``InspectionPort`` containing inspection metadata and schedules.
            n_device_at_port (: int) Number of devices that can be handled at the port simultaneously.
            n_device_stored_at_port (: int): Number of devices that can be stored at the port.
            find_element_class (: object) callable used by logs_preventive_aux to find classes/elements in schedules.
            shutdown_col (: str) or NoneColumn name in the schedule DataFrame containing shutdown durations to be accumulated,
                or None if no shutdown column should be considered.
        """
        self.tow_at_port = {}
        self.tow_at_site = {}
        self.insp_at_port = {}

        self.inspection = inspection
        self.n_device_at_port = n_device_at_port
        self.n_device_stored_at_port = n_device_stored_at_port

        self.operation_completed = True
        self.shutdown_col = shutdown_col

        self.tot_device = safe_getattr(inspection, ["insp_class", "intervened_devices"])

        # Get the operation schedules
        self.oper_schedule_tow_port = logs_preventive_aux.take_op_schedule_tow(inspection = inspection, find_element_class = find_element_class, op_tow = 'op_tow_port')
        self.oper_schedule_insp = safe_getattr(inspection, ["insp_class", "ts_data", "oper_sched"])
        self.oper_schedule_tow_site_only = logs_preventive_aux.take_op_schedule_tow(inspection = inspection, find_element_class = find_element_class, op_tow = 'op_tow_site')
        self.oper_schedule_tow_site_port = logs_preventive_aux.take_op_schedule_tow(inspection = inspection, find_element_class = find_element_class, op_tow = 'op_tow_site_port')

        self.dev_idx_station_port = 1
            

    def tow_inspection_schedule(self, oper_schedule_tow, d, name_op):
        """
        Return end of total op duration and end wait time schedule datetimes for a tow/inspection operation starting at a given datetime.
        If the schedule cannot be found for the provided start datetime, returns (None, None, None) and logs a warning.
        Args:
            oper_schedule_tow (: pandas.DataFrame): Operation schedule dataframe of the operation.
            d (: datetime): The datetime at which the operation is considered to start.
            name_op (: str): Identifier/name of the operation used in warning messages.

        Returns:
            tuple:
                - d_insp (datetime): datetime of end of the total operation duration (start + dur_total rounded up).
                - d_wait (datetime): datetime of end of the wait_to_start (start + wait_start rounded up).
                - d (datetime): the original start datetime passed in.
        """
        try:
            date_start_tow_port = oper_schedule_tow.loc[oper_schedule_tow['datetime'] == d].iloc[0]
            dur_tot_tow_port = math.ceil(date_start_tow_port['dur_total'])
            wait_tow_port = math.ceil(date_start_tow_port['wait_start'])
        except (ValueError, IndexError) as e_:
            logging.warning(f'LogPreventive: {e_}')
            logging.warning(f'The inspection tow {name_op} cannot be completed at date {d}')
            return None, None, None
        
        d_insp = d + timedelta(hours=dur_tot_tow_port)
        d_wait = d + timedelta(hours=wait_tow_port)
        return d_insp, d_wait, d


    def overlap_shift_tow(
        self,
        overlap_date, 
        tow_at_site, 
        d_insp, 
        d_tow_port_wait, 
        inspection, 
        n_device_at_port,
        d_start_tow
    ):
        """
        Verify and resolve overlaps between a proposed towing interval and existing tow intervals.

        Take the operation under analysis and the dict_towing operations presents, 
        If overlaps are found that would exceed the number of available vessels/devices at port 
        new dates set for looking of possible operation is at the end of oldes operation conducted
        Algorithm repeated until it finds a non-overlapping interval

        Args:
            overlap_date (: bool): Initial flag used to enter the overlap resolution loop.
            tow_at_site (: dict): Dictionary of existing tow intervals; values are tuples (end_datetime, start_datetime).
            d_insp (: datetime): Proposed end datetime for the new operation.
            d_tow_port_wait (: datetime): Proposed wait-to-start datetime for the new operation.
            inspection (: object): Inspection object used to read attributes like id and number of vessels.
            n_device_at_port (: int): Maximum number of devices that can be handled concurrently at port.
            d_start_tow (: datetime): Current start datetime candidate for the tow operation.

        Returns:
            tuple
                (d_insp, d_tow_port_wait, d_start_tow) updated to a non-overlapping interval, or
                (None, None, None) if a schedule could not be obtained from tow_inspection_schedule.
        """

        inspection_id = inspection.id
        n_vessel = inspection.n_vessel_1

        if n_vessel>n_device_at_port:
            n_vessel = n_device_at_port

        while overlap_date:
            overlap_date_count = 0
            overlap_date = False
            for end_2, start_2 in tow_at_site.values():
                overlap_day = logs_preventive_aux.date_ranges_overlap(d_tow_port_wait, d_insp, start_2, end_2) 
                if overlap_day:
                    overlap_date_count +=1
                if overlap_date_count >= n_vessel:
                    d_insp, d_tow_port_wait, d_start_tow = self.tow_inspection_schedule(self.oper_schedule_tow_port, d_insp, inspection_id)
                    if d_insp is None or d_tow_port_wait is None:
                        return None, None, None
                    overlap_date = True
                    break
        return (d_insp, d_tow_port_wait, d_start_tow)


    def tow_to_port(
        self, 
        device_n, 
        date_continuous, 
        duration_shutdown_month,
        month_insp
    ):
        """
        Schedule the towing of a single device to port and return the computed end datetime.

        This method computes the start candidate for the tow operation.

        Call tow_inspection_schedule and overlap_shift_tow methods.
        If a shutdown column is provided the method aggregates shutdown duration 
        into `duration_shutdown_month` for the given month index.

        Args:
            device_n (: int): Index (1-based) of the device being processed.
            date_continuous (: datetime): Candidate datetime for starting the sequence of operations (used for the first device).
            duration_shutdown_month (: list): Mutable list that accumulates shutdown durations per month; this function may add to it.
            month_insp (: int): Index of the month in `duration_shutdown_month` to which shutdown durations should be added.

        Returns
            datetime: corresponding to the end of the tow-to-port operation for the device
            None: if the schedule could not be determined 
        """

        if device_n <= self.n_device_at_port:
            # If first shift tow to port take the oper_schedule of the tow
            if device_n == 1:
                start_day_op = date_continuous
                self.dev_idx_station_port = device_n
            else: start_day_op = self.tow_at_port[self.dev_idx_station_port-1][1]

            d_insp, d_tow_port_wait, d_start_tow_port = self.tow_inspection_schedule(self.oper_schedule_tow_port, start_day_op, self.inspection.id)
            
            if d_insp is None or d_tow_port_wait is None:
                self.operation_completed = False
                return
            
            # Check if there is an overlap of the tow
            overlap_date = True
            if self.tow_at_site:
                overlap_dict = {
                    **{f"port_{k}": v for k, v in self.tow_at_port.items()},
                    **{f"site_{k}": v for k, v in self.tow_at_site.items()}
                }
                
                d_insp, d_tow_port_wait, d_start_tow_port = self.overlap_shift_tow(overlap_date, overlap_dict, d_insp, d_tow_port_wait, self.inspection, self.n_device_at_port, start_day_op)
                if d_insp is None or d_tow_port_wait is None:
                    self.operation_completed = False
                    return

            self.tow_at_port[self.dev_idx_station_port] = d_insp, d_tow_port_wait
            # Add the shutdown to tow to port
            if self.shutdown_col:
                duration_shutdown_month[month_insp] += self.oper_schedule_tow_port.loc[self.oper_schedule_tow_port['datetime'] == d_start_tow_port, self.shutdown_col].values[0]
        else: 
            # else take the end date of last redeploy_remove
            self.dev_idx_station_port = min(self.tow_at_site, key=lambda k: self.tow_at_site[k][0])
            d_insp, d_tow_port_wait = self.tow_at_site[self.dev_idx_station_port]
            self.tow_at_port[self.dev_idx_station_port] = d_insp, d_tow_port_wait


        return d_insp


    def inspection_at_port(
        self,
        d_insp,
        duration_shutdown_month,
        month_insp
    ):
        """ 
        Code to inspect the device at port, return the date of end of end inspection device at port
        
        Args:
            d_insp (: datetime): Candidate datetime for starting the sequence of operations (used for the first device).
            duration_shutdown_month (: list): Mutable list that accumulates shutdown durations per month; this function may add to it.
            month_insp (: int): Index of the month in `duration_shutdown_month` to which shutdown durations should be added.
        """
        
        d_tow, d_insp_wait, _ = self.tow_inspection_schedule(self.oper_schedule_insp, d_insp, self.inspection.id)
        if d_tow is None or d_insp_wait is None:
            self.operation_completed = False
            return 
        self.insp_at_port[self.dev_idx_station_port] = d_tow, d_insp_wait
        # Add shutdown considered in port waiting to start inspection
        duration_shutdown_month[month_insp] += self.oper_schedule_insp.loc[self.oper_schedule_insp['datetime'] == d_insp, 'wait_start'].values[0]

        return d_tow


    def tow_to_site(
        self,
        device_n,
        d_tow,
        duration_shutdown_month,
        month_insp
    ):
        """ 
        Smilarly to tow_op_port method schedule the towing of a single device to port and return the computed end datetime.

        Args:
            device_n (: int): Index (1-based) of the device being processed.
            d_tow (: datetime): Candidate datetime for starting the sequence of operations (used for the first device).
            duration_shutdown_month (: list): Mutable list that accumulates shutdown durations per month; this function may add to it.
            month_insp (: int): Index of the month in `duration_shutdown_month` to which shutdown durations should be added.
        """
        
        if device_n > self.tot_device - self.n_device_at_port:
            # Only site tow (only connecting device)
            oper_schedule_tow_site = self.oper_schedule_tow_site_only
        else: 
            # Port-site tow (connecting and disconnecting device)
            oper_schedule_tow_site = self.oper_schedule_tow_site_port

        d_end_device, d_tow_site_wait, d_start_tow_site = self.tow_inspection_schedule(oper_schedule_tow_site, d_tow, self.inspection.id)
        if d_end_device is None or d_tow_site_wait is None:
            self.operation_completed = False
            return

        overlap_date = True
        if self.tow_at_site:
            d_end_device, d_tow_site_wait, d_start_tow_site = self.overlap_shift_tow(
                overlap_date, 
                self.tow_at_site, 
                d_end_device, 
                d_tow_site_wait, 
                self.inspection, 
                self.n_device_at_port,
                d_start_tow_site
            )

            if d_end_device is None or d_tow_site_wait is None:
                self.operation_completed = False
                return
            
        self.tow_at_site[self.dev_idx_station_port] = d_end_device, d_tow_site_wait
        # Add the shutdown to tow to port
        if self.shutdown_col:
            duration_shutdown_month[month_insp] += oper_schedule_tow_site.loc[oper_schedule_tow_site['datetime'] == d_start_tow_site, self.shutdown_col].values[0]

        return d_end_device


    def preventive_port_inspection(
        self,
        month_insp: int,
        duration_shutdown_month: list,
        end_datetimes: list,
        end_stat_chart_datetimes: list,
        valid_datetimes: list,
        d: datetime,
        df_port_inspection_log: pd.DataFrame
    ):
        """
        Main code to evaluate the inspection at port for all the devices
        
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
            month_insp (int): Month of the inspection
            duration_shutdown_month (list): List with the duration of shutdown for each month
            end_datetimes (list): List with the end datetimes of the inspection operations
            end_stat_chart_datetimes (list): List with the end datetimes for statistical analysis
            valid_datetimes (list): List with the valid datetimes of the inspection operations
            d (datetime): Datetime of start of the inspection operation
            df_port_inspection_log (pd.DataFrame): Dataframe to log the towing operations
        """

        actual_df_port_inspection_log = pd.DataFrame(columns=df_port_inspection_log.columns)
        date_continuous = d

        # For each day found for work
        for device_n in range(1, self.tot_device+1):
            ## Tow the device to port ##
            d_insp = self.tow_to_port(
                device_n = device_n, 
                date_continuous = date_continuous, 
                duration_shutdown_month = duration_shutdown_month,
                month_insp = month_insp
            )
            if self.operation_completed is False:
                break
            
            ## Inspect the device at port ##
            d_insp = self.inspection_at_port(
                d_insp = d_insp,
                duration_shutdown_month = duration_shutdown_month,
                month_insp = month_insp
            )
            if self.operation_completed is False:
                break
            
            ## Tow the device to site ##
            d_end_device = self.tow_to_site(
                device_n = device_n,
                d_tow = d_insp,
                duration_shutdown_month = duration_shutdown_month,
                month_insp = month_insp
            )
            if self.operation_completed is False:
                break
            
            actual_df_port_inspection_log.loc[len(actual_df_port_inspection_log)] = [d, self.tow_at_port[self.dev_idx_station_port][1], self.tow_at_site[self.dev_idx_station_port][0], device_n]
            self.dev_idx_station_port+=1
        
        # Add the results to the lists if the inspection is completed
        if self.operation_completed:
            end_datetimes.append(d_end_device)
            end_stat_chart_datetimes.append(d_end_device) # effectuate statistical analysis after
            valid_datetimes.append(d)
            df_port_inspection_log = pd.concat([df_port_inspection_log, actual_df_port_inspection_log], ignore_index=True)
            
        return df_port_inspection_log


if __name__ == "__main__":
    pass