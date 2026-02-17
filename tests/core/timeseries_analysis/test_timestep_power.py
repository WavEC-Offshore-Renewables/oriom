import unittest
import os
import pandas as pd
import numpy as np
from copy import deepcopy

# Import classes
from oriom.classes.Metocean import Metocean

# Import functions
from oriom.core.timeseries_analysis.timestep_power import add_power_columns



class TestWorkability(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        class curve:
            array = None
            c_in = None
            c_off = None
        class matrix:
            matrix = None
        class DummyStatInputs:
            start_year = {"value": 2018}
            lifetime = {"value": 1}
        file_metocean = os.path.join(os.getcwd(), 'tests', 'test_files', 'metocean', 'metocean_dummy_hourly.csv')
        self.metocean = Metocean(
                file_=file_metocean,
                latitude=41.615065,
                longitude=-9.348514,
                stat_inputs = DummyStatInputs
        )
        self.metocean.generateTe()
        self.wind_curve = curve
        self.wave_matrix = matrix
        self.wind_curve.array = np.array([0, 0, 0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.1, 1.3, 1.5, 1.65, 1.85, 1.92, 1.95, 2, 2, 2, 2, 2, 2, 0])
        self.wind_curve.c_in = 3
        self.wind_curve.c_off = 15
        self.wave_matrix.matrix = pd.DataFrame(
                {
                        "(3,5)": [0, 100, 160, 200],
                        "(5,7)": [0, 200, 200, 240],
                        "(7,9)": [300, 350, 400, 0],
                        "(9,11)": [250, 300, 380, 0],
                        "(11,13)": [150, 260, 0, 0]
                },
                index=['(0,2)', '(2,4)', '(4,6)', '(6,8)']
        )
        self.wave_matrix.matrix.index = list(map(eval, self.wave_matrix.matrix.index))
        self.wave_matrix.matrix.columns = list(map(eval, self.wave_matrix.matrix.columns))

    def test_main(self):
        metocean = deepcopy(self.metocean)
        new_metocean = add_power_columns(
                df_metocean=metocean.df_timeseries,
                pcurve_wind=self.wind_curve,
                pmatrix_wave=self.wave_matrix,
                ndevices_wind=1,
                ndevices_wave=1
        )
        self.assertEqual(new_metocean['p_wind'].iloc[0], 1.25)
        self.assertEqual(new_metocean['p_wind'].iloc[1], 1.126)
        self.assertEqual(new_metocean['p_wind_per_device'].iloc[1], 1.126)
        self.assertEqual(new_metocean['p_wave'].iloc[5], 0)
        self.assertEqual(new_metocean['p_wave'].iloc[11], 150)
        self.assertEqual(new_metocean['p_wave'].iloc[-6], 150)
        self.assertEqual(new_metocean['p_wave'].iloc[-1], 0.0)
        self.assertEqual(new_metocean['p_wave_per_device'].iloc[-1], 0.0)

        new_metocean = add_power_columns(
                df_metocean=metocean.df_timeseries,
                pcurve_wind=self.wind_curve,
                pmatrix_wave=self.wave_matrix,
                ndevices_wind=5,
                ndevices_wave=5
        )
        self.assertEqual(new_metocean['p_wind'].iloc[0], 6.25)
        self.assertEqual(new_metocean['p_wind_per_device'].iloc[0], 1.25)
        self.assertEqual(new_metocean['p_wave'].iloc[-6], 750.0)
        self.assertEqual(new_metocean['p_wave_per_device'].iloc[-6], 150)


    def test_errors(self):
        metocean = deepcopy(self.metocean)

        self.assertRaises(ValueError, add_power_columns, metocean.df_timeseries, self.wind_curve, None)
        self.assertRaises(ValueError, add_power_columns, metocean.df_timeseries, None, self.wave_matrix)
        #self.assertRaises(ValueError, add_power_columns, metocean.df_timeseries, None, None, self.wind_curve)


if __name__ == '__main__':
    unittest.main()
