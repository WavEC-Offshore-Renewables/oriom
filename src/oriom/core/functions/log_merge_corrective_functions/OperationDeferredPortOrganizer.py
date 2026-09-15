import logging
import pandas as pd
from datetime import timedelta, datetime
from copy import deepcopy

from oriom.utils.aux_functions import safe_getattr
from oriom.utils.read_dataframe_value import approximate_hourly_data
from oriom.core.functions.logs_timeseries import logs_preventive_aux
from oriom.core.functions.logs_timeseries.logs_corrective_aux import  compute_operation_datetimes, _check_index_row_validity
from oriom.core.functions.logs_timeseries.logs_timeseries_func import create_mobilisation


class OperationDeferredPortCreation():
    """
    Class to generate and manage the Deferred Operation at Port considering towing, operations, WoW, n_vessels and port spaces

    .. figure:: /_static/Flowchart/TTP_Deferred.png
        :width: 8000px
        :alt: example

        TTP Operation deferred logic diagram

    Attributes:
        oper_port_dict (dict): Dict of object of class ``OperationMajor`` that will be conducted at port
        oper_port (dict): Object of OperationMajor operations under specific analysis
        oper_dict_tow (dict): Dict of operation that must be deferred with tow op
        tow_at_port_date (dict): Dictionary storing towing to port operations; keys are device indices, values are tuples (end_datetime, start_datetime).
        tow_at_site_date (dict): Dictionary storing towing to site operations; keys are device indices, values are tuples (end_datetime, start_datetime).
        oper_at_port_date (dict): Dictionary storing oper_port at port operations; keys are device indices, values are tuples (end_datetime, start_datetime).
        operation_completed (bool): Flag indicating whether the entire oper_port operation was completed successfully.
        tot_device (int): Total number of devices to be inspected.
        dev_idx_station_port (int): Index for port stage of the current device being processed for port operations.
        dict_oper_sched (dict): Dictionary containing oper_sched for towing op
        dict_oper_last_idx(dict): Dictionary containing last_valid_index for towing op
        actual_df_port_inspection_log (pd.DataFrame): log_events created of deferred tow
        vessels (dict): Dictionary of vessel_1 used
        vessels_2 (dict): Dictionary of vessel_2 used
        vessel_available (dict): Dictionary of vessels number available
        vessels_mobilidated (dict): Dictionary of vessels number mobilitated per each campaign
        vessels_mobilidated_per_device (dict): Dictionary of vessels number mobilitated per each campaign for each device operated
        find_element_class (object) callable used to find objects.
        n_device (int): Index (1-based) of the device being processed.
        period (: pd.Period): Period of the deferred campaign


        NOTE:
            The utilization of device to store at port (wet storage) must be implemented
    """

    def __init__(
            self,
            log_events_tow_def: pd.DataFrame,
            oper_port_dict: dict,
            oper_dict_tow: dict,
            find_element_class: object
        ):
        """
        Args:
            log_events_tow_def (pd.DataFrame): Events related to deferred towing corrective op
            oper_port_dict (dict): Dict of object of class ``OperationMajor`` that will be conducted at port
            oper_dict_tow (dict): Dict of operation that must be deferred with tow op
            find_element_class (object) callable used callable used to find objects.
        """
        self.dict_oper_sched, self.dict_oper_last_idx, self.dict_oper_stat, self.vessels_mobilitated = {}, {}, {}, {}

        self.find_element_class = find_element_class
        self.log_events_tow_def = log_events_tow_def.sort_values(by=['d_trigger', 'd_end'])
        self.df_port_oper_def_log = pd.DataFrame(columns=self.log_events_tow_def.columns)

        self.oper_port_dict = oper_port_dict
        self.oper_dict_tow = oper_dict_tow
        self.n_device_at_port = next(iter(oper_port_dict.values())).n_device_at_port
        self.n_device_stored_at_port = next(iter(oper_port_dict.values())).n_device_stored_at_port
        self.vessels = {o.vessel1_id : o.vessel1 for o in self.oper_dict_tow.values() if o.vessel1_id is not None}
        self.vessels_2 = {o.vessel2_id : o.vessel2 for o in self.oper_dict_tow.values() if o.vessel2_id is not None}
        self.vessels_per_op = {o.vessel1_id : o.vessel1 for o in self.oper_dict_tow.values() if o.vessel1_id is not None}
        self.vessels_per_op_2 = {o.vessel2_id : o.vessel2 for o in self.oper_dict_tow.values() if o.vessel2_id is not None}
        self.oper_port = None
        self.n_device = 0

        self.reset_data_period()

        self.operation_completed, self.reuse_logs = True, True
        
        self.vessel_available = {v.id: v.n_vessels for v in list(self.vessels.values())+list(self.vessels_2.values())}

        # Building dict opeartions
        for oper_port in oper_port_dict.values():
            for k, v in oper_port.tow_data.dict_tow_oper_sched.items():
                self.dict_oper_sched.setdefault(k, v)

            for k, v in oper_port.tow_data.dict_tow_oper_last_idx.items():
                self.dict_oper_last_idx.setdefault(k, v)

            for k, v in oper_port.tow_data.dict_oper_stat.items():
                self.dict_oper_stat.setdefault(k, v)

            for op_add in [oper_port, oper_port.tow_data.add_op_tow_port, oper_port.tow_data.add_op_tow_site]:
                if op_add and op_add.id not in self.dict_oper_sched:
                    self.dict_oper_sched[op_add.id] = safe_getattr(op_add, ['ts_data', 'oper_sched'])

                if op_add and op_add.id not in self.dict_oper_last_idx:
                    self.dict_oper_last_idx[op_add.id] = safe_getattr(op_add, ['ts_data', 'last_valid_index'])

                if op_add and op_add.id not in self.dict_oper_stat:
                    self.dict_oper_stat[op_add.id] = find_element_class.find_operation_stats(op_add.id)


    def reset_data_period(self, period = None):
        """ Reset the dictionaries for a new period
        Args:
            period (pd.Period): Period of the campaign under analysis. Default to None
        """
        self.dev_idx_station_port = 0
        self.tow_at_port_date = {v.id: {} for v in self.vessels.values()}
        self.tow_at_site_date = {v.id: {} for v in self.vessels.values()}
        self.oper_at_port_date = {}
        self.vessels_mobilitated = {v.id: 0 for v in list(self.vessels.values()) + list(self.vessels_2.values())}
        self.vessels_mobilitated_per_device = {v.id: {} for v in list(self.vessels.values()) + list(self.vessels_2.values())}
        self.reuse_logs = True
        self.period = period


    def write_event_row(self, row_dates_tow):
        """Save the event created"""
        self.df_port_oper_def_log = pd.concat(
            [self.df_port_oper_def_log, row_dates_tow],
            axis=0, ignore_index=False
        )

        
    def overlap_shift_tow(
        self,
        overlap_date: datetime,
        tow_at_site_date: dict,
        n_vess_row: int,
        oper_schedule: pd.DataFrame,
        row_dates: dict,
        idx_oper_sched: int,
        last_valid_idx: int,
        row: pd.Series,
    ):
        """
        Verify and resolve overlaps between a proposed towing interval and existing tow intervals.

        NOTE: 
            Operated only for Vessel_1 

        Take the operation under analysis and the dict_towing operations presents,
        If overlaps are found that would exceed the number of available vessels/devices at port
        new dates set for looking of possible operation is at the end of oldes operation conducted
        Algorithm repeated until it finds a non-overlapping interval

        Args:
            overlap_date (: bool): Initial flag used to enter the overlap resolution loop.
            tow_at_site_date (dict): Dictionary of existing tow intervals; values are tuples (end_datetime, start_datetime).
            n_vess_row (int): Number of vessel available in total.
            oper_schedule (pd.DataFrame): Dataframe of the operation schedule of the operation.
            row_dates (dict): Dict with all dates.
            idx_oper_sched(int): Index of the datetime at wich op start for oper_schedule.
            last_valid_idx (int): Int of the last valid index of oper_schedule simbolizing last op possible.
            row (: pd.Series): row of the df_log original.

        Returns:
            pd.DataFrame
                updated event to a non-overlapping interval, or
                empty DataFrame if a schedule could not be obtained from op_schedule.
        """

        while overlap_date:
            overlap_date_count = 0
            overlap_date = False
            for dates_presents in tow_at_site_date.values():
                for dates in dates_presents:
                    if dates is None:
                        continue
                    end_2, start_2, n_vess_busy = dates
                    overlap_day = logs_preventive_aux.date_ranges_overlap(row_dates['date_end_wait_start'], row_dates['date_end'], start_2, end_2)
                    if overlap_day:
                        overlap_date_count += n_vess_busy
                    # If overlap exceed calculate new date
                    if overlap_date_count + row['n_vessel_1'] > n_vess_row :
                        # Take new index
                        idx_oper_sched = self.dict_oper_sched[row['id']].index[
                            self.dict_oper_sched[row['id']]['datetime'] == approximate_hourly_data(row_dates['date_end'])
                        ][0]

                        df_filtered_start_tow = _check_index_row_validity(
                            idx_end_leadtime = idx_oper_sched,
                            last_valid_idx= last_valid_idx,
                            r = row,
                            oper_sched = oper_schedule
                        )

                        if df_filtered_start_tow.empty:
                            self.operation_completed = False
                            return pd.DataFrame()
                        row_dates = compute_operation_datetimes(df_filtered_start_tow, self.dict_oper_stat[row['id']])
                        overlap_date = True
                        break
                if overlap_date:
                    break

        return pd.DataFrame([[
            row['d_trigger'],
            row['d_end_leadtime'],
            row_dates['date_end_wait_start'],
            row_dates['date_end_dur_net_port'],
            row_dates['date_end_transit_ts'],
            row_dates['date_end_wait_site'],
            row_dates['date_end_dur_net_site'],
            row_dates['date_end_transit_tp'],
            row_dates['date_end'],
            row_dates['date_end_stat_chart'],
            row['event'],
            row['id'],
            row['vessel_1'],
            row['n_vessel_1'],
            row['vessel_2'],
            row['n_vessel_2'],
            row['comments'],
            True,
            False,
            False,
            self.period
        ]],columns=self.df_port_oper_def_log.columns)

    def tow_to_port(
        self,
        row: pd.Series,
        same_vessel: bool,
        date_start_op: datetime = None
    ):
        """
        Schedule the TTP/operation of a single device and return the computed event datetime.

        This method computes the start candidate for the tow operation.

        Call op_schedule and overlap_shift_tow methods.

        Args:
            row (: pd.Series): row of the df_log simbolizing an operation
            same_vessel (bool): Boolean to consider same vessel for Towing and additional op
            date_start_op (:datetime): Candidate datetime for starting the operations.
                (*optional*) Default to None
            
        Returns
            pd.DataFrame, bool
                updated event to a non-overlapping interval, or
                empty DataFrame if a schedule could not be obtained from op_schedule.
        """

        vessel_used = row['vessel_1']
        vessel_used_qt = row['n_vessel_1']
        id_row = row['id']
        write_event = True
        diff = 1

        # If the spots are free to the port take tow to port oper_schedule
        if self.n_device == 1 or vessel_used_qt*self.n_device <= self.vessel_available[vessel_used]:
            self.dev_idx_station_port = self.n_device
            row_dates_tow = row.to_frame().T
        else:
            self.reuse_logs = False
            # If the space at port are full take the oldest date
            if self.dev_idx_station_port > self.n_device_at_port:
                self.dev_idx_station_port = min(self.tow_at_site_date[vessel_used], key=lambda k: self.tow_at_site_date[vessel_used][k][0])
                diff = 0
            # recreate row event
            if date_start_op:
                start_day_op = date_start_op
            # else take the end date of last tow remove
            else:
                start_day_op = self.tow_at_port_date[vessel_used][self.dev_idx_station_port-diff][0][1]

            start_day_op_approx = approximate_hourly_data(start_day_op)
            
            idx_oper_sched = self.dict_oper_sched[id_row].index[self.dict_oper_sched[id_row]['datetime'] == start_day_op_approx][0]

            df_filtered_start_tow = _check_index_row_validity(
                idx_end_leadtime = idx_oper_sched,
                last_valid_idx= self.dict_oper_last_idx[id_row],
                r = row,
                oper_sched = self.dict_oper_sched[id_row]
            )

            if df_filtered_start_tow.empty:
                self.operation_completed = False
                return pd.DataFrame()

            row_dates = compute_operation_datetimes(df_filtered_start_tow, self.dict_oper_stat[id_row])

            # Check overlap vessel
            overlap_date = True
            overlap_dict = {
                **{f"port_{k}": v for k, v in self.tow_at_port_date[vessel_used].items()},
                **{f"site_{k}": v for k, v in self.tow_at_site_date[vessel_used].items()}
            }

            row_dates_tow = self.overlap_shift_tow(
                overlap_date = overlap_date,
                tow_at_site_date = overlap_dict, 
                n_vess_row = self.vessel_available[vessel_used],
                oper_schedule = self.dict_oper_sched[id_row],
                row_dates = row_dates,
                idx_oper_sched = idx_oper_sched,
                last_valid_idx = self.dict_oper_last_idx[id_row],
                row = row,
            )
            if row_dates_tow.empty:
                self.operation_completed = False
                return pd.DataFrame()
        if self.dev_idx_station_port not in self.tow_at_port_date[vessel_used]:
            self.tow_at_port_date[vessel_used][self.dev_idx_station_port] = [(None), (None)]
        if not same_vessel:
            self.tow_at_port_date[vessel_used][self.dev_idx_station_port][0] = (row_dates_tow['d_end'].iloc[0], row_dates_tow['d_end_wait_start'].iloc[0], vessel_used_qt)
        else:
            self.tow_at_port_date[vessel_used][self.dev_idx_station_port][1] = (row_dates_tow['d_end'].iloc[0], row_dates_tow['d_end_wait_start'].iloc[0], vessel_used_qt)


        return row_dates_tow, write_event


    def operation_at_port(
        self,
        row: pd.Series,
        date_start_op: pd.Period
    ):
        """
        Code to inspect the device at port, return the date of event for device operated at port

        Args:
            row (: pd.Series): row of the df_log.
            date_start_op (:datetime): Candidate datetime for starting the operations.

        Returns
            pd.DataFrame
                updated event to a non-overlapping interval, or
                empty DataFrame if a schedule could not be obtained from op_schedule.
        """
        if self.n_device == 1:
            self.dev_idx_station_port = self.n_device
            row_dates_tow = row.to_frame().T

        else:
            # recreate row event
            start_day_op_approx = approximate_hourly_data(date_start_op)
            
            idx_oper_sched = self.dict_oper_sched[row['id']].index[self.dict_oper_sched[row['id']]['datetime'] == start_day_op_approx][0]

            df_filtered_start_tow = _check_index_row_validity(
                idx_end_leadtime = idx_oper_sched,
                last_valid_idx= self.dict_oper_last_idx[row['id']],
                r = row,
                oper_sched = self.dict_oper_sched[row['id']]
            )

            if df_filtered_start_tow.empty:
                self.operation_completed = False
                return pd.DataFrame()

            row_dates = compute_operation_datetimes(df_filtered_start_tow, self.dict_oper_stat[row['id']])

            row_dates_tow = pd.DataFrame([[
                row['d_trigger'],
                row['d_end_leadtime'],
                row_dates['date_end_wait_start'],
                row_dates['date_end_dur_net_port'],
                row_dates['date_end_transit_ts'],
                row_dates['date_end_wait_site'],
                row_dates['date_end_dur_net_site'],
                row_dates['date_end_transit_tp'],
                row_dates['date_end'],
                row_dates['date_end_stat_chart'],
                row['event'],
                row['id'],
                row['vessel_1'],
                row['n_vessel_1'],
                row['vessel_2'],
                row['n_vessel_2'],
                row['comments'],
                row['shutdown'],
                False,
                False,
                self.period
            ]],columns=self.df_port_oper_def_log.columns)
        
        self.oper_at_port_date[self.dev_idx_station_port] = row_dates_tow['d_end'].iloc[0], row_dates_tow['d_end_wait_start'].iloc[0]

        return row_dates_tow
    

    def tow_to_site(
        self,
        row: pd.Series,
        tts: bool,
        date_start_op: datetime,
        same_vessel: bool
    ):
        """
        Smilarly to tow_op_port method schedule the towing of a single device to port and return the computed event.

        Args:
            row (: pd.Series): row of the df_log simbolizing an operation
            tts (: bool): Boolean that flag if is additional op or TTS operation
            date_start_op (:datetime): Candidate datetime for starting the operations.
            same_vessel (bool): Boolean to consider same vessel for Towing and additional op

        Returns
            pd.DataFrame
                updated event to a non-overlapping interval, or
                empty DataFrame if a schedule could not be obtained from op_schedule.
        """
        vessel_used = row['vessel_1']
        vessel_used_qt = row['n_vessel_1']
        id_row = row['id']

        if self.reuse_logs:
            self.dev_idx_station_port = self.n_device
            row_dates_tow = row.to_frame().T
        else:
            if tts:
                # Only site tow (only TTS device)
                oper_schedule_tow_site = self.oper_port.tow_data.tow_site_oper_sched
                oper_last_valid_idx = self.oper_port.tow_data.last_valid_idx_tow_site
            else:
                oper_schedule_tow_site = self.dict_oper_sched[id_row]
                oper_last_valid_idx = self.dict_oper_last_idx[id_row]

            start_day_op_approx = approximate_hourly_data(date_start_op)
            
            idx_oper_sched = oper_schedule_tow_site.index[oper_schedule_tow_site['datetime'] == start_day_op_approx][0]

            df_filtered_start_tow = _check_index_row_validity(
                idx_end_leadtime = idx_oper_sched,
                last_valid_idx= oper_last_valid_idx,
                r = row,
                oper_sched = oper_schedule_tow_site
            )

            if df_filtered_start_tow.empty:
                self.operation_completed = False
                return pd.DataFrame()

            row_dates = compute_operation_datetimes(df_filtered_start_tow, self.dict_oper_stat[id_row])

            # Check overlap vessel
            overlap_date = True
            if self.tow_at_site_date[vessel_used]:
                overlap_dict = {
                    **{f"port_{k}": v for k, v in self.tow_at_port_date[vessel_used].items()},
                    **{f"site_{k}": v for k, v in self.tow_at_site_date[vessel_used].items()}
                }

                row_dates_tow = self.overlap_shift_tow(
                    overlap_date = overlap_date,
                    tow_at_site_date = overlap_dict, 
                    n_vess_row = self.vessel_available[vessel_used],
                    oper_schedule = self.dict_oper_sched[id_row],
                    row_dates = row_dates,
                    idx_oper_sched = idx_oper_sched,
                    last_valid_idx = oper_last_valid_idx,
                    row = row,
                )

            if row_dates_tow.empty:
                self.operation_completed = False
                return pd.DataFrame()

        if self.dev_idx_station_port not in self.tow_at_site_date[vessel_used]:
            self.tow_at_site_date[vessel_used][self.dev_idx_station_port] = [(None), (None)]
        if not same_vessel:
            self.tow_at_site_date[vessel_used][self.dev_idx_station_port][0] = (row_dates_tow['d_end'].iloc[0], row_dates_tow['d_end_wait_start'].iloc[0], vessel_used_qt)
        else:
            self.tow_at_site_date[vessel_used][self.dev_idx_station_port][1] = (row_dates_tow['d_end'].iloc[0], row_dates_tow['d_end_wait_start'].iloc[0], vessel_used_qt)

        return row_dates_tow


    def create_mobi(
        self,
        row: pd.Series,
        time_fail_op_immediately: float,
        vessel: object,
        n_vess: int
    ):
        """ Create mobilisation row and save them on the self.df_port_oper_def_log"""

        mobilisation_date = row['d_trigger'] + timedelta(hours=time_fail_op_immediately)
        row_mobi = create_mobilisation(
            df = self.df_port_oper_def_log.drop(columns=['year_month'], errors='ignore'),
            mobilisation_date = mobilisation_date,
            end_mobi = row['d_end_wait_start'],
            event = 'mobilisation_merged',
            vessel = vessel,
            oper_list = [row['id']],
            count_fail = row['comments'].split("_", 1)[1],
            concat = False,
            n_vessel = n_vess
        )
        return row_mobi

    
    def mobilitate_manager(
        self, 
        row: pd.Series, 
        vessel_: str, 
        n_vessel: int, 
        time_fail_op_immediately: float, 
    ):
        """
        Method to manage creation of mobilisation of vessel. 
        Evaluate if:
            - A mobilisation is required
            - Maximum number of vessels are already mobilised

        Args:
            row (pd.Series): Series of the dataframe under analysis.
            vessel_ (str): String to define if vessel_1 or vessel_2 mobilisation.
            n_vessel (str): String to define if n_vessel_1 or n_vessel_2 is analysed.
            time_fail_op_immediately (float): Reaction time considered.
        """
        vessel_id = row[vessel_]
        requested_vessels = row[n_vessel]

        if vessel_id is None or pd.isna(vessel_id):
            return
        if requested_vessels is None or pd.isna(requested_vessels) or requested_vessels <= 0:
            return

        try:
            vessel = self.vessels[vessel_id]
        except KeyError:
            vessel = self.vessels_2.get(vessel_id)

        if vessel is None or vessel.mobilisation_time == 0 or row["id"] == self.oper_port.id:
            return

        total_already_mobilitated = self.vessels_mobilitated.get(vessel.id, 0)
        available_vessels = self.vessel_available[vessel.id]
        device_already_mobilitated = self.vessels_mobilitated_per_device[vessel.id].get(self.n_device, 0)

        required_for_this_device = max(0, requested_vessels - device_already_mobilitated)
        available_for_campaign = max(0, available_vessels - total_already_mobilitated)
        n_vessel_mobilitate = min(required_for_this_device, available_for_campaign)

        if n_vessel_mobilitate > 0:
            row_mobi = self.create_mobi(
                row=row[:-1],
                time_fail_op_immediately=time_fail_op_immediately,
                vessel=vessel,
                n_vess=n_vessel_mobilitate,
            )
            self.vessels_mobilitated[vessel.id] += n_vessel_mobilitate
            self.vessels_mobilitated_per_device[vessel.id][self.n_device] = (device_already_mobilitated + n_vessel_mobilitate)
            row_mobi["year_month"] = self.period
            self.write_event_row(row_mobi)


    def add_recommission(
        self,
        row_dates_tow_recom: pd.DataFrame,
        row: pd.Series,
        recommission: int
    ):
        """ Add recommissioning row"""
        row_dates_tow_recom['event'] = 'recommissioning'
        row_dates_tow_recom[["vessel_1", "n_vessel_1", "vessel_2", "n_vessel_2"]] = None                        
        modified_date = row_dates_tow_recom['d_end_dur_net_site'] + timedelta(hours=recommission)                  
        for ev in ['d_end_dur_net_site', 'd_end_transit_tp', 'd_end']:
            row_dates_tow_recom[ev] = modified_date

        if self.tow_at_site_date[row['vessel_1']][self.dev_idx_station_port][1]:
            location_disconnection = 1
        else:
            location_disconnection = 0
        current_values = list(self.tow_at_site_date[row['vessel_1']][self.dev_idx_station_port][location_disconnection])
        current_values[0] = row_dates_tow_recom['d_end'].iloc[0]
        self.tow_at_site_date[row['vessel_1']][self.dev_idx_station_port][1] = tuple(current_values)

        return row_dates_tow_recom


    def deferred_port_manager(
        self,
        time_fail_op_immediately: float
    ):
        """
        Main code to evaluate the oper_port at port for all the devices

        The code evaluate for each operation the tow to port, the oper_port at port and the tow to site.
        To evaluate the date of start for each operation the code consider if there is an overlap with other operations
        in the same time interval, if there is an overlap the code reevaluate the date of start and date of end of the operation
        until there is no overlap with other operations.

        All the operations are stored in dict tow_at_port_date, oper_at_port and tow_at_site_date with key the vessel and device number
        and value a tuple with the date of end of the operation and the date of start of the operation.

        NOTE: 
            Mobilitate vessel only on towing to port, vessel wait the operation to be completed at port

        Args:
            time_fail_op_immediately (float): Time between failure and immediate operations.

        Return:
            pd.DataFrame: log_events_tow_deferred with mobilisation
        """

        # Extract failure type and number
        suffix = self.log_events_tow_def['comments'].str.split('_', n=1).str[-1]
        # Evaluate year_month from the first operation of failure type
        self.log_events_tow_def['year_month'] = (
            self.log_events_tow_def
            .groupby(suffix)['d_trigger']
            .transform(lambda x: x.iloc[0].to_period('M'))
        )
        total_failure_to_correct = set(suffix.dropna())

        # For each period of deferred campaign
        for period, df_group in self.log_events_tow_def.groupby('year_month', sort=False):
            failures_to_correct = {c.split('_', 1)[1] for c in df_group['comments'] if '_' in c}
            self.reset_data_period(period = period)

            # For each failure to correct associated to an operation needed
            for n_device, failure in enumerate(failures_to_correct, start = 1):
                self.n_device = n_device
                fail_obj = self.find_element_class.find_failure_from_id(failure.split('.')[0])
                self.oper_port = self.find_element_class.find_operation(fail_obj.operation_triggered)
                row_dates_tow_recom = pd.DataFrame()
                df_failure = df_group[df_group['comments'].str.endswith(failure)]
                write_event, ttp, tts = True, True, True
                recommission = 0
                vessel_add_op, vessel_TTP, vessel_TTS = None, None, None
                same_vessel_TTP_add_op, same_vessel_TTS_add_op = False, False

                for _, row in df_failure.iterrows():
                    ## Correct the device at port ##
                    if row['id'] in self.oper_port_dict:
                        row_dates_tow = self.operation_at_port(
                            row = row, 
                            date_start_op = row_dates_tow['d_end'].iloc[0],
                        )
                        ttp = False

                    ## Tow the device to port ##
                    elif ttp:
                        if self.oper_port.tow_data.add_op_tow_port:
                            if row['id'] != self.oper_port.tow_data.add_op_tow_port.id:
                                date_start_op = row_dates_tow['d_end'].iloc[0]
                                vessel_TTP = row['vessel_1']
                            else:
                                date_start_op = None
                                vessel_add_op = row['vessel_1']
                        else:
                            date_start_op = None
        
                        # Check if TTP use same vessel of additional operation
                        same_vessel_TTP_add_op = (
                            vessel_add_op is not None
                            and vessel_TTP is not None
                            and vessel_add_op == vessel_TTP
                        )

                        row_dates_tow, write_event = self.tow_to_port(
                            row = row, 
                            same_vessel = same_vessel_TTP_add_op, 
                            date_start_op = date_start_op
                        )

                    ## Tow the device to site ##
                    else:
                        # Check if TTS use same vessel of additional operation
                        if not tts and vessel_TTS == row['vessel_1']:
                            same_vessel_TTS_add_op = True
                        if tts:
                            vessel_TTS = row['vessel_1']
                        row_dates_tow = self.tow_to_site(
                            row = row, 
                            tts = tts,
                            date_start_op = row_dates_tow['d_end'].iloc[0],
                            same_vessel = same_vessel_TTS_add_op
                        )

                        if getattr(self.oper_dict_tow[row['id']], 'recommissioning_time', None):
                            recommission = self.oper_dict_tow[row['id']].recommissioning_time
                        if not tts and not row_dates_tow.empty:
                            if recommission > 0:
                                row_dates_tow_recom = self.add_recommission(
                                    deepcopy(row_dates_tow), 
                                    row, 
                                    recommission,
                                )
                        tts = False

                    # Store data
                    if not self.operation_completed:
                        break
                    if write_event:
                        self.write_event_row(row_dates_tow)
                        if not row_dates_tow_recom.empty:
                            self.write_event_row(row_dates_tow_recom)
                        # Mobilitate vessel only on towing to port until reached max nº vessel considered, vessel not demobilised till TTP completed
                        for vessel_, n_vessel in zip(['vessel_1'], ['n_vessel_1']):
                            if ttp:
                                self.mobilitate_manager(
                                    row = row, 
                                    vessel_ = vessel_, 
                                    n_vessel = n_vessel,
                                    time_fail_op_immediately = time_fail_op_immediately,
                                )

                if not self.operation_completed:
                    break

                total_failure_to_correct.discard(failure)
                self.dev_idx_station_port+=1
            
            if not self.operation_completed:
                logging.error(
                    f"Log event merged: TTP operation deferred not completed\n"
                    f"Failures remaining uncorrected: {total_failure_to_correct}"
                )

        return self.df_port_oper_def_log


if __name__ == "__main__":
    pass