import pandas as pd
from datetime import timedelta
from copy import deepcopy

from oriom.utils.aux_functions import log_event_convert_stringtime

class Stat_chart_inspection_campaign():

    """
    Class to manage the statistical analysis of charting vessel for inspection_campaign

    The class receive `InspectionsSiteStat`, build various dictionaries used to map
    the groups of inspection campaign based on day and month of start. Then value the
    statistical analysis of duration for each group of inspection_campaign and
    return the updated dataframe

    Attributes:
        inspections_site_stat (list): List of object :class:`InspectionsSiteStat`.
        campaign_inspection_dict (dict):
            Dict with key `(month, day)` value `list` of `inspection.id`
            represent group of inspections belonging to the same campagna.
        id_to_groups (dict):
            Inverted map that associate `inspection.id` → list of tuple `(month, day)`.
        id_month_to_group (dict):
            Map `(inspection.id, inspection.month)` → `(inspection.month, inspection.day)`.
    """


    def __init__(
            self,
            inspections_site_stat: list
    ):
        """
        Initialize the class and build the dictionaries of inspection campaign
        Args:
            inspections_site_stat (:obj:`list`): List of object :class:`InspectionsSiteStat`.
        """
        self.inspections_site_stat = inspections_site_stat
        self.campaign_inspection_dict = {}
        self.id_to_groups = {}
        self.id_month_to_group = {}

        # Create dict group_insp
        self.create_campaign_inspection_dict()
        # Invert insp_group
        self.create_id_to_groups()
        # map id -> campaign group key
        self.map_id_campaign_group_key()


    def create_campaign_inspection_dict(self):
        """ Create a dictionary with key the tuple (inspection.month, inspection.day) of start inspection and value list of inspection.id"""
        for inspection_stat in self.inspections_site_stat:
            inspection = inspection_stat.insp_class
            if getattr(inspection, 'vessel2', None):
                if inspection.vessel2.mother_vessel:
                    month = inspection.months
                    day = inspection.day_start
                    for m in month if isinstance(month, list) else [month]:
                        if (m, day) not in self.campaign_inspection_dict:
                            self.campaign_inspection_dict[(m, day)] = [inspection.id]
                        else:
                            self.campaign_inspection_dict[(m, day)].append(inspection.id)


    def create_id_to_groups(self):
        """ Create a dictionary with key the inspection.id and value list of tuple (inspection.month, inspection.day)"""
        for key, ids in self.campaign_inspection_dict.items():
            for _id in ids:
                if _id in self.id_to_groups:
                    self.id_to_groups[_id].append(key)
                else:
                    self.id_to_groups[_id] = [key]


    def map_id_campaign_group_key(
            self
    ):
        """Create dict of key tuple(inspection.id, inspection.month) and value tuple (inspection.month, inspection.day)"""
        for key, ids in self.campaign_inspection_dict.items():
            for id_ in ids:
                self.id_month_to_group[(id_, key[0])] = key


    def map_campaign_group(self, row:pd.Series):
        """ take row of df as parameter and return campaign of the group"""
        _id = row["id"]
        month = row["month"]
        groups = self.id_to_groups[_id]

        if len(groups) == 1:
            # id unique, ignore the month
            return groups[0]
        else:
            # id multiple, return (id, month)
            campaign_group = self.id_month_to_group.get((_id, month), None)
            # id d_trigger_month different from the scheduled start (due to previous inspection)
            if not campaign_group:
                # return the last campaign scheduled before d_trigger_month NOTE not very precise if many campaign are presents
                for group in groups:
                    if group[0] > month:
                        break
                    month_check = group[0]
                campaign_group = self.id_month_to_group.get((_id, month_check), None)

            return campaign_group


    def create_stat_chart_inspection_campaign(
            self,
            df:pd.DataFrame,
            vessels: list,
            percentile: float = 0.9
    )->pd.DataFrame:
        """
        Create the statistic chart date for the 'operation_deferred_merged' or 'inspection_site'
            that are inside mother vessel campaign. Considering statistical durations
            of the entire campaign operations insthead of single operations.

        Algorithm work:
            - Group the df by year and campaign_group, evaluate start and end of deferred op for each month,year
            - Evaluate duration of deferred operations in days for each campaign_group
            - Evaluate the percentile of the duration between bloc with the same start_key (same d_trigger)
            - Evaluate the stat_end of the block = min_trigger + ceil(q_days)
            - Mask the df with the stat_end of the block

        Args:
            df (:obj:`pd.DataFrame`): Dataframe of log_events_merged
            vessels (list): list of class `~oriom.classes.Vessel.Vessel`
            percentile (:obj:`float`): percentile value to calculate the statistic

        Returns:
            pd.DataFrame: dataframe with all the failures.
        """

        if percentile > 1:
            percentile = percentile / 100

        # Filter the df for deferred_merged_operation
        df_deferred = deepcopy(df[df['comments'] == 'inspection_site_campaign'])
        if df_deferred.empty:
            return df

        df_deferred = log_event_convert_stringtime(df_deferred)
        df_deferred.sort_values(by=["d_trigger", "d_end"], inplace=True)
        df_deferred["month"] = df_deferred["d_trigger"].dt.month
        # apply map df
        df_deferred["campaign_group"] = df_deferred.apply(self.map_campaign_group, axis=1)

        # remove inspcetion that are not considere as deferred campaign
        df_deferred = df_deferred[df_deferred["id"].isin({_id for _id, _ in self.id_month_to_group.keys()})]
        df_deferred['year'] = df_deferred['d_trigger'].dt.year

        # iterate for vessel used
        for vessel in vessels:
            df_deferred_vessel = df_deferred[df_deferred['vessel_2'] == vessel.id]

            if df_deferred_vessel.empty:
                continue

            # Regroup by year and month, evaluate start and end of deferred op for each month, year
            grouped = df_deferred_vessel.groupby(['year', 'campaign_group']).agg(
                min_trigger=('d_trigger', 'min'),
                max_end=('d_end', 'max')
            ).reset_index()

            # Evaluate duration of deferred operations in days for each deferred month
            grouped['duration_days'] = (grouped['max_end'] - grouped['min_trigger']).dt.total_seconds() / 86400  # in days

            # CHIAVE DI RAGGRUPPAMENTO: "stesso d_trigger iniziale"
            # uso la data normalizzata (00:00) per evitare problemi di ore/minuti
            grouped["start_key"] = list(zip(grouped["min_trigger"].dt.month,
                                            grouped["min_trigger"].dt.day))

            # percentile della durata tra blocchi con lo stesso start_key
            q = (grouped
                .groupby("start_key")["duration_days"]
                .quantile(percentile)
                .reset_index(name="q_days"))

            # unisci la durata-quantile al singolo blocco tramite la sua start_key
            grouped = grouped.merge(q, on="start_key", how="left")

            # stat_end del blocco = min_trigger + ceil(q_days)
            grouped["stat_end"] = [
                row["min_trigger"] + timedelta(days=row["q_days"] if not pd.isna(row["q_days"]) else 0)
                for _, row in grouped.iterrows()
            ]

            # mask the df
            block_to_date = dict(
                ((row["year"], row["campaign_group"]), row["stat_end"])
                for _, row in grouped.iterrows()
            )

            # create series that map the original index
            stat_series = df_deferred_vessel.apply(
                lambda r: block_to_date.get((r["year"], r["campaign_group"])), axis=1
            )
            # write directly in df on original index
            df.loc[df_deferred_vessel.index, "d_end_stat_chart"] = stat_series.values
            df = log_event_convert_stringtime(df)

        return df


if __name__ == "__main__":
    pass
