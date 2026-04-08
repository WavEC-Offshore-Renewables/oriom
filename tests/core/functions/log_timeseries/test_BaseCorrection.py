# test_corrections_unittest.py
import unittest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Import classes from your module
from oriom.core.functions.logs_timeseries.BaseCorrection import (
    BaseCorrection,
    CorrectionImmediate,
    CorrectionDeferred,
    CorrectionTowPort,
    CorrectionTowSite,
    create_mobilisation,
    approximate_hourly_data
)


class TestBaseCorrection(unittest.TestCase):

    def setUp(self):
        """Setup common objects for all tests."""
        self.sample_vessel = MagicMock()
        self.sample_vessel.id = "v001"
        self.sample_oper = MagicMock()
        self.sample_oper.id = "op001"
        self.sample_dataframe = pd.DataFrame({
            "datetime": [datetime(2026, 4, 7, h) for h in range(24)],
            "id": list(range(24))
        })
        self.sample_row = pd.Series({"id": 1})

    def test_base_correction_initialization(self):
        date_fail = datetime(2026, 4, 7, 8)
        base_corr = BaseCorrection(date_fail, self.sample_vessel, self.sample_oper, 2)
        self.assertEqual(base_corr.date_failure, date_fail)
        self.assertEqual(base_corr.vessel.id, "v001")
        self.assertEqual(base_corr.oper.id, "op001")
        self.assertEqual(base_corr.time_fail_op_immediately, 2)
        self.assertIsNone(base_corr.date_op)
        self.assertIsNone(base_corr.date_end_leadtime)

    @patch("oriom.core.functions.logs_timeseries.BaseCorrection.create_mobilisation")
    def test_mobilitate_vessel(self, mock_create):
        base_corr = BaseCorrection(datetime(2026, 4, 7, 8), self.sample_vessel, self.sample_oper)
        mock_create.return_value = "mobilisation_row"
        result = base_corr.mobilitate_vessel(self.sample_dataframe, self.sample_row)
        self.assertEqual(result, "mobilisation_row")
        mock_create.assert_called_once()

    def test_add_hours_for_noon_shift(self):
        base_corr = BaseCorrection(datetime(2026, 4, 7, 8), self.sample_vessel, self.sample_oper)
        oper_sched = pd.DataFrame({0: [datetime(2026, 4, 7, h) for h in range(24)]})
        base_corr.add_hours_for_noon_shift(fail_index=10, lead_mob_time=0, oper_sched=oper_sched)
        self.assertIsNotNone(base_corr.idx_end_leadtime)

    def test_leadtime_evaluation(self):
        date_fail = datetime(2026, 4, 7, 8)
        base_corr = BaseCorrection(date_fail, self.sample_vessel, self.sample_oper, 2)
        base_corr.date_op = date_fail + timedelta(hours=5)
        base_corr.leadtime_evaluation(lead_mob_time=10)
        self.assertGreater(base_corr.date_end_leadtime, base_corr.date_op)

    @patch("oriom.core.functions.logs_timeseries.BaseCorrection.approximate_hourly_data", lambda x: x)
    def test_check_leadtime_index(self):
        base_corr = BaseCorrection(datetime(2026, 4, 7, 8), self.sample_vessel, self.sample_oper)
        base_corr.date_op = datetime(2026, 4, 7, 8)
        base_corr.date_end_leadtime = datetime(2026, 4, 7, 8)
        idx_valid = base_corr.check_leadtime_index(self.sample_dataframe, datetime(2026, 4, 8))
        self.assertTrue(idx_valid)
        self.assertEqual(base_corr.idx_end_leadtime, 8)


class TestCorrectionImmediate(unittest.TestCase):

    def setUp(self):
        self.vessel = MagicMock()
        self.vessel.id = "v001"
        self.oper = MagicMock()
        self.oper.id = "op001"

    def test_with_tow(self):
        date_fail = datetime(2026, 4, 7, 8)
        corr = CorrectionImmediate(date_fail, self.vessel, self.oper, 2, tow_op=True)
        self.assertEqual(corr.date_op, date_fail)

    def test_without_tow(self):
        date_fail = datetime(2026, 4, 7, 8)
        corr = CorrectionImmediate(date_fail, self.vessel, self.oper, 2, tow_op=False)
        self.assertEqual(corr.date_op, date_fail + timedelta(hours=2))


class TestCorrectionDeferred(unittest.TestCase):

    def setUp(self):
        self.vessel = MagicMock()
        self.vessel.id = "v001"
        self.oper = MagicMock()
        self.oper.id = "op001"

    def test_initialization(self):
        date_fail = datetime(2026, 4, 7, 8)
        corr = CorrectionDeferred(date_fail, self.vessel, self.oper, preferred_month=5)
        self.assertEqual(corr.date_op.month, 5)
        self.assertEqual(corr.date_op.hour, 5)

    def test_add_leadtime_tow(self):
        date_fail = datetime(2026, 4, 7, 8)
        corr = CorrectionDeferred(date_fail, self.vessel, self.oper, preferred_month=5)
        corr.add_leadtime_tow(10)
        self.assertEqual(corr.date_end_leadtime, corr.date_op + timedelta(hours=10))


class TestCorrectionTowPort(unittest.TestCase):

    def setUp(self):
        self.vessel = MagicMock()
        self.vessel.id = "v001"
        self.oper = MagicMock()
        self.oper.id = "op001"

    def test_immediate_strategy(self):
        date_fail = datetime(2026, 4, 7, 8)
        failure = MagicMock()
        corr = CorrectionTowPort(date_fail, self.vessel, self.oper, failure, maintenance_strategy="immediately", time_fail_op_immediately=2)
        self.assertEqual(corr.date_op, date_fail + timedelta(hours=2))
        self.assertFalse(corr.tow_deferred)

    def test_deferred_strategy(self):
        date_fail = datetime(2026, 4, 7, 8)
        failure = MagicMock()
        failure.preferred_month = [6,7]
        corr = CorrectionTowPort(date_fail, self.vessel, self.oper, failure)
        self.assertIn(corr.date_op.month, [6,7])
        self.assertTrue(corr.tow_deferred)


class TestCorrectionTowSite(unittest.TestCase):

    def setUp(self):
        self.vessel = MagicMock()
        self.vessel.id = "v001"
        self.oper = MagicMock()
        self.oper.id = "op001"

    def test_initialization(self):
        date_fail = datetime(2026, 4, 7, 8)
        date_start = datetime(2026, 4, 8, 5)
        corr = CorrectionTowSite(date_fail, self.vessel, self.oper, date_start)
        self.assertEqual(corr.date_end_leadtime, date_start)


if __name__ == "__main__":
    unittest.main(verbosity=2)