import unittest
import os
import pandas as pd
from datetime import timedelta

class TestaLayoutpercentage(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        file_df_wind = os.path.join(os.getcwd(),'tests','test_files','df_wind.csv')
        file_df_wind_prev = os.path.join(os.getcwd(),'tests','test_files','df_wind_prev.csv')
        file_energy_availability = os.path.join(os.getcwd(),'tests','test_files','Availability_year_wind.csv')
        self.df_wind = pd.read_csv(file_df_wind)
        self.df_wind_prev = pd.read_csv(file_df_wind_prev)
        self.availability = pd.read_csv(file_energy_availability)

    def test_corrective_layout(self):
        full_production = self.df_wind[self.df_wind['Perc_availability']==100.00]
        self.assertEqual((full_production['En_loss_kWh'] == 0).all(),True)
        for i,r in self.df_wind.iterrows():
            if i==0:
                pass
            else:
                self.assertAlmostEqual(r['Time_operation'],r['hour_diff_next']*r['Perc_availability']/100)
                self.assertAlmostEqual(r['En_loss_kWh'],r['Power_loss_kW']*r['hour_diff_next'])

    def test_preventive_energy(self):
        no_losses = self.df_wind_prev[self.df_wind_prev['Time_shutdown'] == 0.0]
        self.assertEqual((no_losses['En_loss_kWh'] == 0).all(), True)

    def test_availability(self):
        for _,r in self.availability.iterrows():
            self.assertGreater(100, r['En_availability'])
            self.assertGreater(100,r['Time_availability'])
            self.assertAlmostEqual(r['En_availability'],(r['En_max_kWh']-r['En_loss_kWh'])/r['En_max_kWh']*100)

if __name__ == '__main__':
    unittest.main()