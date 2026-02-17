import unittest
from unittest import skip
import os
import pandas as pd
import numpy as np

from oriom.core.timeseries_analysis.montecarlo import f_montecarlo


class MonteCarloTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        test_file = os.path.join(os.getcwd(), 'tests', 'test_files', 'metocean', 'metocean_1year.csv')
        hindcast = pd.read_csv(test_file, sep=',')
        hindcast2 = hindcast.drop(axis=0, index=0)
        hindcast2['datetime'] = pd.to_datetime(hindcast2['datetime'], dayfirst=True)
        hindcast2.set_index('datetime', inplace=True)

        self.data_panda1 = hindcast2.iloc[:,:]
        # self.data_panda2 = hindcast2.iloc[0:100, :]
        # self.data_panda3 = hindcast2.iloc[:, :]

    def test_f_montecarlo_1(self):
        # This test also proves that the random selection is non-repeatable
        dt = self.data_panda1
        ts_p = 1
        ts_ids, data = f_montecarlo(dt, ts_p)
        self.assertEqual(list(np.sort(ts_ids)), list(dt.reset_index().index))

    def test_f_montecarlo_0(self):
        # For zero percent, one simulation per month is run
        dt = self.data_panda1
        ts_p = 0
        ts_ids, data = f_montecarlo(dt, ts_p)
        self.assertEqual(len(ts_ids), 12)

    def test_f_montecarlo_very_low(self):
        # For zero percent, one simulation per month is run
        dt = self.data_panda1
        ts_p = 0.00001
        ts_ids, data = f_montecarlo(dt, ts_p)
        self.assertEqual(len(ts_ids), 12)

    @skip
    def test_f_montecarlo_incompleteyear(self):
        # This case should produce an error due to incomplete year of data
        dt = self.data_panda2
        ts_p = 1
        with self.assertRaises(Exception) as context:
            ts_ids, data = f_montecarlo(dt, ts_p)
        self.assertTrue('At least one year of data is required to perform the analysis' in str(context.exception))

    @skip
    def test_f_montecarlo_multipleyears(self):
        # Repeat previous tests for multiple years of data in timeseries
        dt = self.data_panda3
        ts_p = 1
        ts_ids, data = f_montecarlo(dt, ts_p)
        self.assertEqual(list(np.sort(ts_ids)), list(dt.index))
        ts_p = 0
        ts_ids, data = f_montecarlo(dt, ts_p)
        self.assertEqual(len(ts_ids), 12)
        ts_p = 0.00001
        ts_ids, data = f_montecarlo(dt, ts_p)
        self.assertEqual(len(ts_ids), 12)


if __name__ == '__main__':
    unittest.main()
