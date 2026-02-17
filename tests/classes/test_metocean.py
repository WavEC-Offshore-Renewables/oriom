import unittest
import os
from copy import deepcopy
import pandas as pd

from oriom.classes.Metocean import Metocean


class stat_inputs():
     def __init__(self,start_year,lifetime):
          self.start_year = {"value": start_year}
          self.lifetime = {"value": lifetime}

class TestMetocean(unittest.TestCase):
    @classmethod
    def setUpClass(self):
            self.test_file = os.path.join(os.getcwd(), 'tests', 'test_files', 'metocean', 'metocean_dummy.csv')
            self.test_file_hour = os.path.join(os.getcwd(), 'tests', 'test_files', 'metocean', 'metocean_dummy_hourly.csv')
            self.metocean = Metocean(
                    file_=self.test_file,
                    latitude=41.615065,
                    longitude=-9.348514,
                    stat_inputs = stat_inputs(2018,1)
            )

    def test_minimal(self):
        metocean = Metocean(
                file_=self.test_file,
                latitude='41.615065',
                longitude='-9.348514',
                stat_inputs = stat_inputs(2018,1)
        )
        self.assertIsInstance(metocean.latitude, float)
        self.assertIsInstance(metocean.longitude, float)
        self.assertEqual(metocean.latitude, 41.615065)
        self.assertEqual(metocean.longitude, -9.348514)
        self.assertIsInstance(metocean.df_timeseries, pd.DataFrame)

        self.assertEqual(
                metocean.df_timeseries.columns.tolist(),
                ['hs', 'tp', 'ws', 'ws_hub', 'cs', 'light', 'te']
        )
        self.assertEqual(metocean.df_timeseries.index.name, 'datetime')

    def test_interpolation(self):
        metocean = deepcopy(self.metocean)
        metocean.interpolate()
        # Index - datetime
        df_index = pd.DataFrame(metocean.df_timeseries.index)
        self.assertEqual(int(df_index.diff().mean().values[0]), 60 * 60 * 10**9)

        # Wave height
        self.assertEqual(metocean.df_timeseries['hs'].iloc[0], 2.5)
        self.assertEqual(metocean.df_timeseries['hs'].iloc[2], 2.3)
        self.assertEqual(metocean.df_timeseries['hs'].iloc[9], 1.75)
        self.assertEqual(metocean.df_timeseries['hs'].iloc[14], 1.6)
        self.assertEqual(metocean.df_timeseries['hs'].iloc[23], 0.6)
        # Wave period
        self.assertEqual(metocean.df_timeseries['tp'].iloc[6], 16.6)
        self.assertEqual(metocean.df_timeseries['tp'].iloc[10], 14.2)
        self.assertEqual(metocean.df_timeseries['tp'].iloc[20], 12.0)
        # Wind speed
        self.assertEqual(metocean.df_timeseries['ws'].iloc[9], 4.3)
        self.assertEqual(metocean.df_timeseries['ws'].iloc[19], 5.5)
        # Current speed
        self.assertEqual(metocean.df_timeseries['cs'].iloc[-1], 0.3)
        self.assertEqual(metocean.df_timeseries['cs'].iloc[-6], 0.3)
        self.assertEqual(metocean.df_timeseries['cs'].iloc[-16], 0.6)

    def test_daylight(self):
        # For the equator
        metocean = Metocean(
                file_=self.test_file_hour,
                latitude=0,
                longitude=0,
                stat_inputs = stat_inputs(2018,1)
        )
        metocean.get_daylight_timesteps()
        self.assertTrue(metocean.df_timeseries['light'].iloc[0])
        self.assertFalse(metocean.df_timeseries['light'].iloc[7])
        self.assertTrue(metocean.df_timeseries['light'].iloc[-6])

        # For the north pole
        metocean = Metocean(
                file_=self.test_file_hour,
                latitude=77,
                longitude=0,
                stat_inputs = stat_inputs(2018,1)
        )
        metocean.get_daylight_timesteps()
        self.assertTrue(metocean.df_timeseries['light'].iloc[0])
        self.assertFalse(metocean.df_timeseries['light'].iloc[3])
        self.assertFalse(metocean.df_timeseries['light'].iloc[-4])
        self.assertTrue(metocean.df_timeseries['light'].iloc[-3])

    def test_generateTe(self):
        metocean = Metocean(
                file_=self.test_file_hour,
                latitude=0,
                longitude=0,
                stat_inputs = stat_inputs(2018,1)
        )
        metocean.generateTe()
        self.assertTrue('te' in metocean.df_timeseries.columns)
        self.assertEqual(metocean.df_timeseries['te'].iloc[0], 13.6)
        self.assertAlmostEqual(metocean.df_timeseries['tp'].sum() * 0.85, metocean.df_timeseries['te'].sum(), 6)

        metocean.df_timeseries['te'].iloc[0] = 12
        metocean.generateTe()
        self.assertEqual(metocean.df_timeseries['te'].iloc[0], 12)
        metocean.generateTe(overwrite=True)
        self.assertEqual(metocean.df_timeseries['te'].iloc[0], 13.6)

        # Errors
        metocean = Metocean(
                file_=self.test_file_hour,
                latitude=0,
                longitude=0,
                stat_inputs = stat_inputs(2018,1)
        )
        metocean.df_timeseries.drop(columns=['tp'], inplace=True)
        self.assertRaises(TypeError, metocean.generateTe)


    def test_errors(self):
        # Input types
        self.assertRaises(ValueError, Metocean, self.test_file, 'forty', -9, stat_inputs(2018,1))
        self.assertRaises(ValueError, Metocean, self.test_file, 40, 'nine', stat_inputs(2018,1))

        # Input ranges
        self.assertRaises(ValueError, Metocean, self.test_file, 91, 0, stat_inputs(2018,1))
        self.assertRaises(ValueError, Metocean, self.test_file, 0, -181, stat_inputs(2018,1))

        # File path
        self.assertRaises(FileNotFoundError, Metocean, 'other_path', 0, 0, stat_inputs(2018,1))

        # Wrong timesteps in the timeseries
        test_file_wrong = os.path.join(os.getcwd(), 'tests', 'test_files', 'metocean', 'metocean_dummy_wrong1.csv')
        self.assertRaises(ValueError, Metocean, test_file_wrong, 0, 0, stat_inputs(2018,1))
        test_file_wrong = os.path.join(os.getcwd(), 'tests', 'test_files', 'metocean', 'metocean_dummy_wrong2.csv')
        self.assertRaises(ValueError, Metocean, test_file_wrong, 0, 0, stat_inputs(2018,1))


    def test_check_timestep_consistency_irregular_steps(self):
        """
        Verify that a timestep series that not include the years of the project raise
        the error 'There is some inconsitency in timesteps'.
        """
        metocean = deepcopy(self.metocean)

        # Serie with step 1h, 2h -> not regular
        idx = pd.to_datetime(
            ["2025-01-01 00:00", "2025-01-01 01:00", "2025-01-01 03:00"]
        )
        df = pd.DataFrame({"hs": [0.0, 0.0, 0.0]}, index=idx)
        df.index.name = "datetime"
        metocean.df_timeseries = df

        class DummyStatInputs:
            start_year = 2100
            lifetime = 1

        with self.assertRaisesRegex(ValueError, "inconsitency in timesteps"):
            metocean._check_timestep_consistency(DummyStatInputs)

    def test_check_timestep_consistency_subhourly_steps(self):
        """
        Verify that a a timeseries with a mean time stamp < 1 raise
        the error 'Metocean timestep is lower than 1 hour'.
        """
        metocean = deepcopy(self.metocean)

        # Regular Serie but with 30 minutes step
        idx = pd.date_range("2025-01-01 00:00", periods=4, freq="30min")
        df = pd.DataFrame({"hs": [0.0, 0.0, 0.0, 0.0]}, index=idx)
        df.index.name = "datetime"
        metocean.df_timeseries = df

        class DummyStatInputs:
            start_year = 2100
            lifetime = 1

        with self.assertRaisesRegex(ValueError, "timestep is lower than 1 hour"):
            metocean._check_timestep_consistency(DummyStatInputs)

    def test_check_timestep_consistency_lifetime_not_included(self):
        """
        Verify that if the project period (start_year..end_year)
        is included in the time series' temporal coverage, the function
        raises the error 'project duration is not included
        in timeseries timestep' (as per the current implementation).
        """
        metocean = deepcopy(self.metocean)

        idx = pd.to_datetime(["2020-01-01", "2030-01-01"])
        df = pd.DataFrame({"hs": [0.0, 0.0]}, index=idx)
        df.index.name = "datetime"
        metocean.df_timeseries = df

        class DummyStatInputs:
            # projet 2025-2026 between range 2020-2030
            start_year = {"value": 1990}
            lifetime = {"value": 2} # end year 2026

        with self.assertRaisesRegex(
            ValueError, "lifetime of the project is not included"
        ):
            metocean._check_timestep_consistency(DummyStatInputs)


if __name__ == "__main__":
    unittest.main()



