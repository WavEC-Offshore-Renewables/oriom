import random
import logging
from datetime import datetime, timedelta
import pandas as pd

from oriom.core.functions.logs_timeseries.logs_timeseries_func import create_mobilisation
from oriom.utils.read_dataframe_value import approximate_hourly_data


# ===========================
# BASE CLASS
# ===========================
class BaseCorrection:
    """
    Base class for all corrections.

    Attributes:
        date_failure (datetime): Date to consider as start of the operation (failure date or end of tow)
        vessel (:obj:`object`): Objectts :class:`Vessel`
        oper (:obj:`list`): Objectts :class:`OperationMinor` or `OperationMajor`
        time_fail_op_immediately (:obj:`float`): Time between failure and immediate operations.
        date_op (datetime): date to consider for start of the operation after raction time
        date_end_leadtime (datetime): date to consider for start of the operation after leadtime
        idx_end_leadtime (int):index of date_end_leadtime
    """
    def __init__(
        self,
        date_failure: datetime,
        vessel: object,
        oper: object,
        time_fail_op_immediately: float = 0
    ):
        self.date_failure = date_failure
        self.vessel = vessel
        self.oper = oper
        self.time_fail_op_immediately = time_fail_op_immediately

        self.date_op = None
        self.date_end_leadtime = None
        self.idx_end_leadtime = None


    def mobilitate_vessel(self, log_events: pd.DataFrame, row: pd.Series, date_start = None):
        """Create mobilisation of vessel"""
        row_mob_line = create_mobilisation(
            df=log_events,
            mobilisation_date=date_start if date_start else self.date_op,
            end_mobi=self.date_op,
            event='mobilisation',
            vessel=self.vessel,
            oper_list=[self.oper.id],
            count_fail=row['id'],
            concat=False
        )
        return row_mob_line


    def add_hours_for_noon_shift(self, fail_index: int, lead_mob_time: float, oper_sched: pd.DataFrame):
        """Add hours if the failure occurs in the noon to schedule at 5AM of next day"""
        self.idx_end_leadtime = fail_index + lead_mob_time + int(self.time_fail_op_immediately)
        h_to_add = 0

        if lead_mob_time == 0:
            if self.vessel and getattr(self.vessel, "id", None) != 'v999':
                hour_end_leadtime = int(oper_sched.iat[self.idx_end_leadtime, 0].hour)
                if hour_end_leadtime > 12:
                    h_to_add = int((5 - hour_end_leadtime) % 24)

        self.idx_end_leadtime += h_to_add


    def leadtime_evaluation(self, lead_mob_time: float):
        """Add the leadtime if the deferred date for the correction is lower then any leadtime"""
        diff = (self.date_op - (self.date_failure + timedelta(hours=self.time_fail_op_immediately))).total_seconds() / 3600
        lead_mob_time = max(lead_mob_time - diff, 0)
        self.date_end_leadtime = self.date_op + timedelta(hours=lead_mob_time)


    def check_leadtime_index(self, oper_sched: pd.DataFrame, CUTOFF_DATE: datetime):
        """Check if leadtime index has a valid row"""
        if self.date_end_leadtime > CUTOFF_DATE:
            return False
        try:
            self.date_end_leadtime = approximate_hourly_data(self.date_end_leadtime)
            self.idx_end_leadtime = oper_sched.index[oper_sched['datetime'] == self.date_end_leadtime][0]
            return True
        except IndexError as e_:
            logging.error(f'Leadtime index not found for {self.date_end_leadtime}')
            raise


# ===========================
# IMMEDIATE CORRECTION
# ===========================
class CorrectionImmediate(BaseCorrection):
    """
    CorrectionImmediate class for immediate corrections.

    Attributes:
        tow_op (bool): Flag to reconnize if a towing operation have been conducted
    """

    def __init__(self, date_failure, vessel, oper, time_fail_op_immediately, tow_op=False):
        super().__init__(date_failure, vessel, oper, time_fail_op_immediately)
        self.tow_op = tow_op
        if not self.tow_op:
            self.date_op = self.date_failure + timedelta(hours=self.time_fail_op_immediately)
        else:
            self.date_op = self.date_failure


# ===========================
# DEFERRED CORRECTION
# ===========================
class CorrectionDeferred(BaseCorrection):
    """
    CorrectionDeferred class for deferred corrections.

    Attributes:
        tow_op (bool): Flag to reconnize if a towing operation have been conducted
    """
    def __init__(self, date_failure, vessel, oper, preferred_month, time_fail_op_immediately=0, tow_op=False):
        super().__init__(date_failure, vessel, oper, time_fail_op_immediately)
        # Calculate date in base on deferred month
        self.tow_op = tow_op

        if not self.tow_op:
            self.time_fail_op_immediately = time_fail_op_immediately
        else:
            self.time_fail_op_immediately = 0
        self.date_op = datetime(
            year=self.date_failure.year if preferred_month > self.date_failure.month else self.date_failure.year + 1,
            month=preferred_month,
            day=1,
            hour=5,
            minute=0,
            second=0
        )

    def add_leadtime_tow(self, lead_mob_time: float):
        self.date_end_leadtime = self.date_op + timedelta(hours=lead_mob_time)



# ===========================
# CORRECTION TOW / PORT
# ===========================
class CorrectionTowPort(BaseCorrection):
    """
    CorrectionTowPort class for tow to port.
    """
    def __init__(self, date_failure, vessel, oper, failure, time_fail_op_immediately=0):
        super().__init__(date_failure, vessel, oper, time_fail_op_immediately)
        self.tow_deferred = False
        if failure.maintenance_strategy == "immediately":
            self.date_op = self.date_failure + timedelta(hours=time_fail_op_immediately)
        else:
            # Calculate deferred for tow
            self.tow_deferred = True
            preferred_months = failure.preferred_month
            if isinstance(preferred_months, list):
                preferred_month = random.choice(preferred_months)
            else:
                preferred_month = preferred_months
            year_op = self.date_failure.year if preferred_month > self.date_failure.month else self.date_failure.year + 1
            self.date_op = datetime(year_op, preferred_month, 1, 5, 0, 0)


# ===========================
# CORRECTION TOW / SITE
# ===========================
class CorrectionTowSite(BaseCorrection):
    """
    CorrectionTowSite class for tow to port.
    Attributes:
        date_end_leadtime (datetime): date to consider for start of the operation after leadtime
    """
    def __init__(self, date_failure, vessel, oper, date_start):
        super().__init__(date_failure, vessel, oper)
        self.date_end_leadtime = date_start
