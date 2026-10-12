import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

from oriom.core.functions.graphs.final_economic_graphs import (
    plot_ctv_annual_chart_strategy,
    lifetime_cost,
    yearly_vessel_cost,
    pie_chart,
)


class DummyFindElementClass:
    def find_vessel(self, vessel_id):
        return SimpleNamespace(type='CTV' if vessel_id == 'ctv_1' else 'SOV')


class TestFinalRunStatistics(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.df_ctv = {
            'P10': pd.DataFrame({
                'n_vessel': [1, 2, 3],
                'short_term_cost': [100000, 90000, 80000],
                'long_term_cost': [200000, 180000, 160000],
                'tot_cost': [300000, 270000, 240000],
            }),
            'AVG': pd.DataFrame({
                'n_vessel': [1, 2, 3],
                'short_term_cost': [120000, 110000, 100000],
                'long_term_cost': [220000, 200000, 180000],
                'tot_cost': [340000, 310000, 280000],
            }),
            'P90': pd.DataFrame({
                'n_vessel': [1, 2, 3],
                'short_term_cost': [140000, 130000, 120000],
                'long_term_cost': [240000, 220000, 200000],
                'tot_cost': [380000, 350000, 320000],
            }),
        }

        cls.df_lifetime = pd.DataFrame({
            'cost_type': [
                'lifetime_vessels_cost €',
                'lifetime_technician_cost €',
                'lifetime_other_cost €',
                'lifetime_fixed_port_cost €',
            ],
            'P10': [800, 400, 0, 1800],
            'AVG': [1000, 500, 0, 2000],
            'P90': [1200, 600, 0, 2200],
        })

        columns = pd.MultiIndex.from_tuples([
            ('vessel_id', ''),
            ('2025', 'direct_costs'),
            ('2026', 'direct_costs'),
        ])

        cls.df_yearly_vessels = pd.DataFrame([
            ['ctv_1', 1000, 1500],
            ['sov_1', 2000, 2500],
            ['fixed_annual_cost', 500, 500],
            ['oper_port', 300, 400],
        ], columns=columns)

        cls.df_pie = pd.DataFrame({
            'category': ['Vessels', 'Technicians', 'Repairs'],
            'cost': [1000, 2000, 500],
        })

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.save_dir = self.temp_dir.name

    def tearDown(self):
        plt.close('all')
        self.temp_dir.cleanup()

    def assert_plot_saved(self, filename):
        path = os.path.join(self.save_dir, filename)
        self.assertTrue(os.path.isfile(path), f'Plot not saved: {filename}')
        self.assertGreater(os.path.getsize(path), 0)

    def test_plot_ctv_annual_chart_strategy(self):
        plot_ctv_annual_chart_strategy(
            df_ctv=self.df_ctv,
            title='Test',
            save_dir=self.save_dir,
        )

        self.assert_plot_saved('CTV Long Term Chart strategy.png')

    def test_plot_ctv_annual_chart_strategy_without_percentiles(self):
        df_ctv = {'AVG': self.df_ctv['AVG'].copy()}

        plot_ctv_annual_chart_strategy(
            df_ctv=df_ctv,
            title='Test',
            save_dir=self.save_dir,
        )

        self.assert_plot_saved('CTV Long Term Chart strategy.png')

    def test_lifetime_cost(self):
        lifetime_cost(
            df=self.df_lifetime,
            title='Lifetime costs',
            save_dir=self.save_dir,
        )

        self.assert_plot_saved('lifetime_cost.png')

    def test_lifetime_cost_custom_filename(self):
        lifetime_cost(
            df=self.df_lifetime,
            title='Yearly costs',
            file_name='yearly_costs',
            save_dir=self.save_dir,
        )

        self.assert_plot_saved('yearly_costs.png')

    def test_lifetime_cost_without_saving(self):
        with patch('matplotlib.pyplot.show') as mock_show:
            lifetime_cost(
                df=self.df_lifetime,
                title='Lifetime costs',
                save_dir=None,
            )

        mock_show.assert_called_once()

    def test_yearly_vessel_cost(self):
        yearly_vessel_cost(
            df=self.df_yearly_vessels,
            title='Yearly vessel costs',
            find_element_class=DummyFindElementClass(),
            save_dir=self.save_dir,
        )

        self.assert_plot_saved('yearly_vessels_cost.png')

    def test_yearly_vessel_cost_without_saving(self):
        with patch('matplotlib.pyplot.show') as mock_show:
            yearly_vessel_cost(
                df=self.df_yearly_vessels,
                title='Yearly vessel costs',
                find_element_class=DummyFindElementClass(),
                save_dir=None,
            )

        mock_show.assert_called_once()

    def test_pie_chart(self):
        pie_chart(
            df=self.df_pie,
            description='category',
            value='cost',
            title='Cost distribution',
            save_dir=self.save_dir,
            file_name_save='cost_distribution.png',
        )

        self.assert_plot_saved('cost_distribution.png')

    def test_pie_chart_total_in_title(self):
        pie_chart(
            df=self.df_pie,
            description='category',
            value='cost',
            title='Cost distribution',
            tot_in_title=True,
            title_unit='€',
            coefficient_number=1000,
            save_dir=self.save_dir,
            file_name_save='cost_distribution_total.png',
        )

        self.assert_plot_saved('cost_distribution_total.png')


if __name__ == '__main__':
    unittest.main()