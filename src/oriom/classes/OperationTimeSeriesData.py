import pandas as pd
import os
import logging

from oriom.utils.aux_functions import convert_stringtime


class OperationTimeSeriesData:
    """
    A class representing the oper_schedul class of the operations and some of their info.
    It takes the oper_sched of the operations and save the first value encountered for
    the transits and the duration_net as these are constant values.

    Attributes:
        id (:obj:`str`): The unique identifier of the :class:`CorrectiveMinor`, :class:`CorrectiveMajor`,
            :class:`OperationTow`, :class:`InspectionPort`, :class:`InspectionSite`, :class:`CorrectiveMinor`.
        oper_sched (:obj:`pd.DataFrame`): DataFrame of the corrispective operation_schedule of the operation id
        startability (:obj:`pd.DataFrame`): DataFrame of the corrispective startability of the operation id
        dur_net_site (:obj:`float`): Total net duration of the operation at site
        dur_net_port (:obj:`float`): Total net duration of the operation at port
        transit_tp (:obj:`float`): Total transit duration to port
        transit_ts (:obj:`float`): Total transit duration to site
        last_valid_index (:obj:`int`): Last index valid to conduct op of oper_sched

    Note:
        When the class is initialized, :func:`_extract_from_sched` is run.
    """

    def __init__(self, operation, id: str, oper_sched: pd.DataFrame, startability: pd.DataFrame = pd.DataFrame()):
        self.operation = operation
        self.id = id
        self.oper_sched = oper_sched
        if not startability.empty:
            self.startability = startability

        self.dur_net_site = None
        self.dur_net_port = 0
        self.transit_tp = None
        self.transit_ts = None
        self.last_valid_index = None

        self.duration_main_shift = None
        self.days_main_shift = None

        self._extract_from_sched()  # automatic call to the function

        self.dur_total = self.transit_ts + self.transit_tp + self.dur_net_port + self.dur_net_site


    def _extract_from_sched(self):
        if self.oper_sched.empty:
            raise ValueError(f"The oper_sched file for the operation {self.id} is empty")

        self.dur_net_site = self.oper_sched['dur_net_site'].iloc[0]
        self.transit_tp = self.oper_sched['transit_to_port'].iloc[0]
        self.transit_ts = self.oper_sched['transit_to_site'].iloc[0]
        self.last_valid_index = self.oper_sched.iloc[:, 1:].dropna(how='all').last_valid_index()
        if 'dur_net_port' in self.oper_sched.columns:
            self.dur_net_port = self.oper_sched['dur_net_port'].iloc[0]
        else:
            self.dur_net_port = 0


    @classmethod
    def create_timeseries_data(cls, operation, file_name_dir, op_dir, save = None):
        """ The save argument is used in case we want to return the df to save it in the folder (in case we recycle files from other operations)"""
        startability_df = pd.DataFrame()
        if isinstance(file_name_dir, str):
            try:
                file_name_dir= os.path.join(op_dir, file_name_dir)
                oper_sched = pd.read_csv(file_name_dir)
                try:
                    startability_df = pd.read_csv(os.path.join(op_dir, 'startability.csv'))
                except FileNotFoundError:
                    pass
            except FileNotFoundError:
                raise FileNotFoundError(f'Operation schedule not found for the operation {operation.id}')
        elif isinstance(file_name_dir, pd.DataFrame):
            oper_sched = file_name_dir
            try:
                startability_df = pd.read_csv(os.path.join(op_dir, 'startability.csv'))
            except FileNotFoundError:
                pass
        else:
            raise TypeError(f'Error in class definition for operation: {operation.id} file_name_dir must be a path to a CSV (str) or a pandas DataFrame.')

        if 'datetime' not in oper_sched.columns:
            oper_sched.rename(columns={oper_sched.columns[0]: 'datetime'}, inplace=True)
        oper_sched = convert_stringtime(oper_sched,'datetime')

        if save:
            df_workability = pd.read_csv(os.path.join(op_dir, 'workability.csv'))
            return cls(operation, operation.id, oper_sched, startability_df), oper_sched, df_workability
        else:
            return cls(operation, operation.id, oper_sched, startability_df)



if __name__ == '__main__':

    pass