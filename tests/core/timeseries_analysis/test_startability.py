import unittest
import os
import pandas as pd
from copy import deepcopy

# Import classes
from logistic_tools.classes.Activity import Activity

# Import functions
from logistic_tools.core.timeseries_analysis.startability import startability


class TestStartability(unittest.TestCase):
    @classmethod
    def setUpClass(self):
            file_workability = os.path.join(os.getcwd(), 'tests', 'test_files', 'workability_dummy.csv')
            file_activities = os.path.join(os.getcwd(), 'tests', 'test_files', 'op_activities_dummy.csv')

            df_workability = pd.read_csv(file_workability, sep=',')
            df_workability['datetime'] = pd.to_datetime(df_workability['datetime'])
            df_workability.set_index('datetime', inplace=True)

            self.df_workability = df_workability
            self.activities = Activity.get_activities_from_csv(file_activities)

    def test_main(self):
        df_workability = deepcopy(self.df_workability)
        df_startability = startability(
                activities=self.activities,
                df_workability=df_workability
        )
        self.assertTrue(df_startability.iloc[3:17, 0].all())
        self.assertFalse(df_startability.iloc[0:2, 0].any())
        self.assertTrue(df_startability.iloc[34:39, 0].all())

        self.assertTrue(df_startability.iloc[:, 1].all())
        self.assertTrue((df_startability.iloc[47:, 1].isna()).all())

        self.assertFalse(df_startability.iloc[30:44:, 2].any())

        self.assertTrue(df_startability.iloc[:, 3].all())

        self.assertFalse(df_startability.iloc[:20, 4].any())
        self.assertTrue(df_startability.iloc[20:30, 4].all())
        self.assertFalse(df_startability.iloc[31:44, 4].any())

        self.assertTrue((df_startability.iloc[48:, 5].isna()).all())
        self.assertTrue((df_startability.iloc[48:, 6].isna()).all())

    def test_single_activity(self):
        df_workability = deepcopy(self.df_workability)
        # Select one activity workability
        df_workability = df_workability.iloc[:, 2:3]
        activities = [deepcopy(self.activities[2])]
        df_startability = startability(
                activities=activities,
                df_workability=df_workability
        )

    def test_save(self):
        df_workability = deepcopy(self.df_workability)
        tmp_dir = os.path.join(os.getcwd(), 'tmp', 'test')
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        startability(
                activities=self.activities,
                df_workability=df_workability,
                out_dir=tmp_dir
        )
        open(os.path.join(os.getcwd(), 'tmp', 'test', 'startability.csv'), 'r')
        os.remove(os.path.join(os.getcwd(), 'tmp', 'test', 'startability.csv'))

    def test_errors(self):
        df_workability = deepcopy(self.df_workability)
        df_workability.index.name = 'other'
        self.assertRaises(KeyError, startability, self.activities, df_workability)


if __name__ == '__main__':
    unittest.main()
