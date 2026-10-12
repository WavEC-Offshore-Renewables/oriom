import os
import pandas as pd
import numpy as np
from copy import deepcopy

from oriom.utils import aux_functions
from oriom.core.functions.logs_timeseries import logs_timeseries_func


class VesselDayCounter():
    """
    Attr:
        self.dict_vess_long_term (dict): Dictionary of vessel with LT contract with subdict key month value nº vessels
        self.usage_records (dict): Dictionary of vessel and date and value the nº of vessel used
        self.vessels_calendar (pd.DataFrame): Calendar of vessel per each date
        self.log_event_day(pd.DataFrame): Dataframe of lof_events_date for only operations and inspection
        vessels (dict): Dictionary of month on which n_vessel are contracted
        first_counter (bool): Flag to consider if the preparation of the df has never been done. Default to True
        ST_used (bool): Flag to consider we are not interest in calculating the charting days. Default to True
    """

    def __init__(self, log_events_merged, vessels, first_counter = True, ST_used = True, prepare_df = True):
        """
        Arg:
            log_events_merged(pd.DataFrame): Dataframe of lof_events_merged data
            vessels (list): List of object with attribute `id` for class `Vessels`
            first_counter (bool): Flag to consider if the preparation of the df has never been done. Default to True
        """

        self.dict_vess_long_term = {}
        self.usage_records = {}
        self.vessels_calendar = pd.DataFrame()
        self.vessels = vessels
        self.first_counter = first_counter

        log_event_day = aux_functions.safe_copy_df(log_events_merged, ['id', 'comments'])
        log_event_day = aux_functions.log_event_convert_stringtime(log_event_day)
        if prepare_df:
            self.log_event_day = self.log_event_preparation(log_event_day, ST = ST_used)
        else:
            self.log_event_day = log_event_day
        self.create_dict_vessel_contract_month(vessels)


    def create_dict_vessel_contract_month(self, vessels):
        """
        Create a dict with vessel id and months with n_ves_contracted corrispective
            {ves.id: {month_1: n_ves_contract_month_1, month_2: ...]}
        """

        for v in vessels:
            ves_annual_contract = getattr(v, 'n_ves_annual_contract', 0)
            dict_months_vessel_contract = {month: ves_annual_contract for month in range(1,13)}

            monthly_contract = getattr(v, 'months_contract', [])
            for month in monthly_contract:
                dict_months_vessel_contract[month] += getattr(v, 'n_ves_monthly_contract', 0)

            if any(val > 0 for val in dict_months_vessel_contract.values()):
                self.dict_vess_long_term[v.id] = dict_months_vessel_contract


    def log_event_preparation(self, log_event_day, ST):
        """
        Filter the df only for the operations considering for campaign only start and end event

        If ST == False is used to counts the days of charts of vessel
        
        Return:
            pd.dataframe: Log_events_day filtered per operations
        """

        def manage_campaign_op(df, col, value, ST=True):
            """
            Find the first and last operation of each vessel campaign and concatenate the final row of the campaign with the start corrected.

            If ST=False, ensure that all vessels used in the campaign are represented in the final campaign rows. 
            If a vessel is missing, all rows belonging to the groups where that vessel was not represented in the final campaign rows are added.

            Returning df with:
                - all rows not in the campaign
                - only final row(s) of campaign with the start of the initial operation and end by the final operation
                - if ST=False, additional rows for vessels not represented in the final campaign rows
            """

            cols_to_update = ['d_trigger', 'd_end_leadtime', 'd_end_wait_start']
            group_by_date = 'd_end_stat_chart_orig' if not self.first_counter else 'd_end_stat_chart'

            def get_campaign_rows(df, vessel_number = 'vessel_1'):
                idx_min = df.groupby([vessel_number, group_by_date])['d_end'].idxmin()
                idx_max = df.groupby([vessel_number, group_by_date])['d_end'].idxmax()

                src = df.loc[idx_min, cols_to_update].copy()
                src.index = idx_max.values
                df.loc[idx_max.values, cols_to_update] = src

                return df.loc[idx_max.values].copy()
                        
            def find_vessel_missing(df, mask, campaign_final):
                """ Find if there is a second vessel not called in campaign final"""
                # Vessels used in the campaign
                vessel_used = set(df.loc[mask, 'vessel_1'].dropna())
                vessel_used.update(df.loc[mask, 'vessel_2'].dropna())
                vessel_present = set(campaign_final['vessel_1'].dropna())
                vessel_present.update(campaign_final['vessel_2'].dropna())
                return  vessel_used - vessel_present
            
            mask = df[col] == value
            if not mask.any():
                return df
            
            campaign_final = get_campaign_rows(df = df.loc[mask])
            # Remove original campaign rows and add final campaign rows
            out = pd.concat([df.loc[~mask], campaign_final]).sort_values(by='d_trigger')
            
            # If ST=False, make sure every vessel used in the campaign is represented in the final rows
            # ---------------------------------------------------------------
            if not ST:
                missing_vessels = find_vessel_missing(df, mask, campaign_final)
                
                for vessel in missing_vessels:
                    df_vessel = df.loc[mask & (df["vessel_2"] == vessel)].copy()
                    # Find first and last operation of each vessel campaign
                    campaign_final_add = get_campaign_rows(df = df_vessel, vessel_number = 'vessel_2')
                    # Final campaign first vessel elimination to avoid recount
                    campaign_final_add[['vessel_1', 'n_vessel_1']] = [None, None]
                    # add the additional rows of campaign_final_add to the dataframe output
                    out = pd.concat([out, campaign_final_add]).sort_values(by='d_trigger')

            return out

        # Filter only operations
        log_event_day = log_event_day[~log_event_day['event'].str.contains('fail|mobi', na=False)]

        # Find rows of each last op of 'operation_deferred_merged' campaign
        log_event_day = manage_campaign_op(df = log_event_day, col = 'event', value = 'operation_deferred_merged', ST = ST)
        log_event_day = manage_campaign_op(df = log_event_day, col = 'comments', value = 'inspection_site_campaign', ST = ST)

        return log_event_day


    def date_evaluation(self, row, event, ST):
        col_end_no_effective = "d_end" if ST else "d_end_stat_chart"
        col_start_no_effective = "d_end_wait_start" if ST else "d_end_leadtime"

        if event.startswith("inspection"):
            return row["d_trigger"], row[col_end_no_effective]
        else:
            return row[col_start_no_effective], row[col_end_no_effective]



    def allocate_vessels(self,  log_events_merged: pd.DataFrame, ST = False, contract_evaluation = True):
        """
        .. figure:: /_static/Flowchart/Vessel_Counter.png
            :width: 8000px
            :alt: example

            Vessel Counter logic diagram

        Account the number of vessels type for each day and select the dates of the operation

        This function has various type of use:
            1) ST = True & contract_evaluation = True
                - Evaluate calendar the TOTAL amount of vessels used and modify the log_events_merged ST
            2) ST = False & contract_evaluation = True
                - After the chart SA to evaluate in calendar the TOTAL amount of vessels used that do not
                    account for vessels that are reused for more operations
            3) ST = False & contract_evaluation = False
                - After the chart SA to evaluate in calendar ONLY the ST amount vessels that do not
                    account for vessels that have already been reused

        Args:
            log_events_merged (pd.DataFrame): Dataframe of lof_events_merged data
            ST (bool): Flag consider if update ST_contract column or add mobilisation
            contract_evaluation (bool): Flag consider to check vessel availability

        Return:
            pd.dataframe: log_events_merged updated with the ST_contract evaluation

        # NOTE TODO might be added the mobiliation here. Remove mobilisation creation from log_events_file if vessel
            has long term contract. Add here a mobilisation creation when a ST vessel is required
        """

        # Reorder firstly the inspection then by dates
        self.log_event_day["_is_insp"] = (self.log_event_day["event"].str.lower().str.startswith("insp", na=False))
        self.log_event_day["_deferred"] = self.log_event_day["event"].str.lower().str.contains("defer", na=False)
        self.log_event_day = self.log_event_day.sort_values(
            by=["_is_insp", "_deferred", "d_trigger"],
            ascending=[False, False, True]
        ).drop(columns=["_is_insp","_deferred"])

        for idx, row in self.log_event_day.iterrows():
            event = row["event"]

            if not ST:
                # Do not count if reuse a ST vessel when create the ultimate vessels_calendar
                n_vessel_1 = "n_vessel_1_effective"
                if row["d_end_stat_chart"] == 'reuse_vessel':
                    continue
            else: n_vessel_1 = "n_vessel_1"

            # Initially take effective day of vessel use
            start_date, end_date = self.date_evaluation(row = row, event = event, ST = ST)

            vessel_columns = {1: ("vessel_1", n_vessel_1, "ST_contract_1"), 2: ("vessel_2", "n_vessel_2", "ST_contract_2")}

            for vessel_slot, (vcol, ncol, ST_ch) in vessel_columns.items():
                vessel = row.get(vcol)
                n_vessel = row.get(ncol, 0)
                ST_chart = row.get(ST_ch)

                # When considering only ST vessel skip vessel that are not ST vessel called
                if not contract_evaluation:
                    if not ST_chart:
                        continue

                # skip if ficticious vessel
                if pd.isna(vessel) or n_vessel == 0 or vessel == 'v999':
                    continue

                while True:
                    if contract_evaluation:
                        days_needed = pd.date_range(start_date.normalize(), end_date.normalize())
                        LT_available = True

                        # Check for all the dates of use if vessel do not exceed LT availability
                        for d in days_needed:
                            used = self.usage_records.get((d, vessel), 0)
                            allowed = self.dict_vess_long_term.get(vessel, {}).get(d.month, 0)
                            if used + n_vessel > allowed:
                                LT_available = False
                                break

                        # Use Short term day contract to store the use of vessel
                        if not LT_available:
                            start_date, end_date = self.date_evaluation(row = row, event = event, ST = False)
                            if ST:
                                log_events_merged.loc[idx, f'ST_contract_{vessel_slot}'] = True

                    if end_date == 'reuse_vessel':
                        end_date = row['d_end_stat_chart_orig']
                    days_needed = pd.date_range(start_date.normalize(), end_date.normalize())
                    for d in days_needed:
                        key = (d, vessel)
                        self.usage_records[key] = self.usage_records.get(key, 0) + n_vessel

                        """ TODO ???? NOTE it must be tuned with the rest of the code...
                        HERE IS TO ADD MOBILISATION IN THIS PART
                        NOTE should be done only once, create flag on input to decide when to do

                        if not ST
                            if self.dict_vess_long_term.get(vessel, {}):

                                if mob_time != 0 and vessel.type not in vessel_to_merge:            # NOTE Mobilisation of merging vessel is considered in create_logs_merge
                                    mobilisation_date = date_op
                                    row_mob_line = logs_timeseries_func.create_mobilisation(
                                        df = log_events,
                                        mobilisation_date = mobilisation_date,
                                        end_mobi = mobilisation_date,
                                        event = 'mobilisation',
                                        vessel = vessel,
                                        oper_list = [oper.id],
                                        count_fail = row['id'],
                                        concat=False,
                                        n_vessel = oper.vessel1_qt
                                    ) """
                    break
        if self.usage_records:
            vessels_calendar_use = (
                pd.Series(self.usage_records)
                .unstack(fill_value=0)
                .sort_index()
                .astype(int)
            )
        else:
            vessels_calendar_use = pd.DataFrame([[0]*len(self.vessels)], columns=[ves.id for ves in self.vessels])

        self.vessels_calendar = vessels_calendar_use

        return log_events_merged


    def count_day_vessel(self, ves_id):
        """
        Take only the series of the vessel used and evaluate how many days the vessel is used

        Args:
            ves_id (string): Vessel id to consider

        Return:
            float: number of short term day to count
        """
        if ves_id in self.vessels_calendar.columns:
            days_vessel_used = self.vessels_calendar[ves_id].sum()
            return days_vessel_used
        else: return 0


if __name__ == '__main__':
    pass

