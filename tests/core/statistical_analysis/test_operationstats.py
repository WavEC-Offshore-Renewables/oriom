import unittest
import pandas as pd
import os

from oriom.core.statistical_analysis.operation_stats import *


class Testaoperation_stat(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        file_op = os.path.join(os.getcwd(),'tests','test_files','inputs','operation_schedule.csv')
        df_op_schedule = pd.read_csv(file_op)
        df_op_schedule['datetime'] = pd.to_datetime(df_op_schedule['datetime'])
        self.df_percentiles = operation_stats(df_op_schedule,50, None)

    def test_percentiles(self):

        self.assertEqual(self.df_percentiles[1].loc[0], 918.25)
        self.assertAlmostEqual(self.df_percentiles[1].loc[2:8].sum(),918.25)

        self.assertEqual(self.df_percentiles[12].loc[0], 292.25)
        self.assertAlmostEqual(self.df_percentiles[12].loc[2:8].sum(),292.25)

if __name__ == '__main__':
    unittest.main()

