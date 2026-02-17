import unittest
import pandas as pd
import os

from oriom.classes.Power import Curve, Matrix
from oriom.classes.Metocean import Metocean
from oriom.core.timeseries_analysis.timestep_power import add_power_columns
from oriom.core.statistical_analysis.power_stats import average_pwind, average_pwave

class Testapower_stat(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        pcurve_wind = Curve(
        file_=os.path.join(os.getcwd(), 'tests', 'test_files', 'pcurve_wind.csv'),
        c_in=4,
        c_off=25,
        rated=8000
        )

        pmatrix_wave = Matrix(
                file_=os.path.join(os.getcwd(), 'tests', 'test_files', 'pmatrix_wave.csv'),
                rated=450
        )

        class DummyStatInputs:
            start_year = {"value": 2018}
            lifetime = {"value": 1}

        metocean = Metocean(
                file_=os.path.join(os.getcwd(), 'tests', 'test_files', 'metocean', 'metocean_dummy.csv'),
                latitude=41.0,
                longitude=-9.0,
                stat_inputs = DummyStatInputs,
                h_ws_measurements=10
        )
        metocean.generateTe()
        metocean.add_wind_speed_h_hub_column()

        metocean_w_power_columns = add_power_columns(
            df_metocean=metocean.df_timeseries,
            pcurve_wind=pcurve_wind,
            pmatrix_wave=pmatrix_wave,
            ndevices_wind=3,
            ndevices_wave=10,
        )

        self.dict_power_wind = average_pwind(metocean_w_power_columns)
        self.dict_power_wave = average_pwave(metocean_w_power_columns)
        self.m1 = metocean_w_power_columns['p_wind'].sum()/metocean_w_power_columns['p_wind'].shape
        self.m2 = metocean_w_power_columns['p_wave'].sum()/metocean_w_power_columns['p_wave'].shape

    def test_average(self):

        #self.assertEqual(self.dict_power_wind[1], nan)
        self.assertAlmostEqual(self.dict_power_wind[2], self.m1)
        self.assertAlmostEqual(self.dict_power_wave[2], self.m2)

if __name__ == '__main__':
    unittest.main()
