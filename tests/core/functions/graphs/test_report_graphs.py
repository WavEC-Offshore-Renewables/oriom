# test_report_graphs.py

import os
import tempfile
import unittest
from types import SimpleNamespace

import pandas as pd

import oriom.core.functions.graphs.report_graphs as report_graphs_module


class TestReportGraphs(unittest.TestCase):

    def test_distribution_failures_saves_file(self):
        """distribution_failures deve salvare distribution_failure.jpg nel save_dir."""
        df = pd.DataFrame(
            {
                "datetime": pd.to_datetime(
                    ["2020-01-01 00:00:00", "2021-06-15 12:00:00"]
                ),
                "id": ["F1", "F2"],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            report_graphs_module.distribution_failures(df=df, save_dir=tmpdir)
            out_path = os.path.join(tmpdir, "distribution_failure.jpg")
            self.assertTrue(os.path.exists(out_path))

    def test_energy_yield_creates_two_files(self):
        """energy_yield deve creare i file energy_maximum_<name>.jpg ed energy_produced_<name>.jpg."""
        months = list(range(1, 13))
        df = pd.DataFrame(
            {
                "Months": months,
                "En_max_kWh": [1000.0] * 12,
                "En_loss_kWh": [100.0] * 12,
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            report_graphs_module.energy_yield(
                df=df,
                name_file="wind",
                save_dir=tmpdir,
            )
            max_path = os.path.join(tmpdir, "energy_maximum_wind.jpg")
            prod_path = os.path.join(tmpdir, "energy_produced_wind.jpg")
            self.assertTrue(os.path.exists(max_path))
            self.assertTrue(os.path.exists(prod_path))

    def test_energy_yield_combined_creates_files(self):
        """energy_yield_combined deve creare energy_maximum_total.jpg ed energy_produced_total.jpg."""
        months = list(range(1, 13))
        base_df = pd.DataFrame(
            {
                "Months": months,
                "En_max_kWh": [2000.0] * 12,
                "En_loss_kWh": [200.0] * 12,
            }
        )
        dfs = {
            "availability_year_wave": base_df,
            "availability_year_wind": base_df,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_graphs_module.energy_yield_combined(dfs=dfs, save_dir=tmpdir)
            max_path = os.path.join(tmpdir, "energy_maximum_total.jpg")
            prod_path = os.path.join(tmpdir, "energy_produced_total.jpg")
            self.assertTrue(os.path.exists(max_path))
            self.assertTrue(os.path.exists(prod_path))

    def test_direct_costs_per_year_saves_file(self):
        """direct_costs_per_year deve creare yearly_direct_costs.jpg."""
        df = pd.DataFrame(
            {
                "cost_type": ["A", "B", "C"],
                "2020": [1e6, 2e6, 3e6],
                "2021": [1.5e6, 2.5e6, 3.5e6],
                "total": [0.0, 0.0, 0.0],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            report_graphs_module.direct_costs_per_year(df=df, save_dir=tmpdir)
            out_path = os.path.join(tmpdir, "yearly_direct_costs.jpg")
            self.assertTrue(os.path.exists(out_path))

    def test_indirect_costs_per_year_saves_file(self):
        """indirect_costs_per_year deve creare yearly_indirect_costs_<name>.jpg."""
        df = pd.DataFrame(
            {
                "Years": [1, 2, 3],
                "En_loss_kWh": [1000.0, 2000.0, 3000.0],
                "En_availability": [99.0, 98.0, 100.0],  # ultimo = 100 -> viene scartato
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            report_graphs_module.indirect_costs_per_year(
                df=df,
                electricity_price=50.0,
                name_file="wind",
                save_dir=tmpdir,
            )
            out_path = os.path.join(tmpdir, "yearly_indirect_costs_wind.jpg")
            self.assertTrue(os.path.exists(out_path))

    def test_farm_availability_saves_files(self):
        """farm_availability deve creare time_availability_<name>.jpg e energy_availability_<name>.jpg."""
        df = pd.DataFrame(
            {
                "Years": [1, 2, 3],
                "En_availability": [95.0, 96.0, 100.0],   # ultimo 100 -> scartato
                "Time_availability": [94.0, 95.0, 100.0],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            report_graphs_module.farm_availability(
                df=df,
                name_file="wind",
                save_dir=tmpdir,
            )
            time_path = os.path.join(tmpdir, "time_availability_wind.jpg")
            en_path = os.path.join(tmpdir, "energy_availability_wind.jpg")
            self.assertTrue(os.path.exists(time_path))
            self.assertTrue(os.path.exists(en_path))

    def test_direct_cost_pie_saves_file(self):
        """direct_cost_pie deve creare pie_direct_costs.jpg."""
        df = pd.DataFrame(
            {
                "operation_id": ["total"],
                "tot_vessel_costs": [2e6],
                "tot_mobilization_costs": [5e5],
                "tot_port_costs": [1e6],
                "tot_repair_costs": [1.5e6],
                "tot_technicians_costs": [8e5],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            report_graphs_module.direct_cost_pie(df=df, save_dir=tmpdir)
            out_path = os.path.join(tmpdir, "pie_direct_costs.jpg")
            self.assertTrue(os.path.exists(out_path))

    def test_compare_quartiles_direct_costs_saves_file(self):
        """compare_quartiles_direct_costs deve creare lifetime_direct_costs_percentiles.jpg."""
        df_25 = pd.DataFrame(
            {
                "operation_id": ["total"],
                "tot_port_costs": [5e5],
                "tot_technicians_costs": [4e5],
                "tot_repair_costs": [3e5],
                "tot_vessel_costs": [6e5],
                "tot_mobilization_costs": [2e5],
                "lifetime_direct_costs": [2.0e6],
            }
        )
        df_50 = pd.DataFrame(
            {
                "operation_id": ["total"],
                "tot_port_costs": [6e5],
                "tot_technicians_costs": [5e5],
                "tot_repair_costs": [4e5],
                "tot_vessel_costs": [7e5],
                "tot_mobilization_costs": [3e5],
                "lifetime_direct_costs": [2.5e6],
            }
        )
        df_75 = pd.DataFrame(
            {
                "operation_id": ["total"],
                "tot_port_costs": [7e5],
                "tot_technicians_costs": [6e5],
                "tot_repair_costs": [5e5],
                "tot_vessel_costs": [8e5],
                "tot_mobilization_costs": [4e5],
                "lifetime_direct_costs": [3.0e6],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            report_graphs_module.compare_quartiles_direct_costs(
                df_25=df_25,
                df_50=df_50,
                df_75=df_75,
                save_dir=tmpdir,
            )
            out_path = os.path.join(tmpdir, "lifetime_direct_costs_percentiles.jpg")
            self.assertTrue(os.path.exists(out_path))

    def test_distribution_mobilization_saves_file(self):
        """distribution_mobilization deve creare <name>.jpg quando esistono mobilisations."""
        # log_events con due mobilisations dello stesso vessel in anni diversi
        df_logs = pd.DataFrame(
            {
                "event": ["mobilisation", "mobilisation"],
                "d_trigger": pd.to_datetime(
                    ["2020-01-01 00:00:00", "2020-01-03 00:00:00"]
                ),
                "vessel_1": ["v1", "v1"],
            }
        )

        # Vessel con tempo e costo di mobilizzazione
        vessel = SimpleNamespace(
            id="v1",
            mobilisation_time=48.0,  # ore -> 2 giorni
            mobilisation_cost=1000.0,
        )
        vessels = [vessel]

        # KPI OM con lifetime_direct_costs
        df_kpi_om = pd.DataFrame(
            {
                "operation_id": ["total"],
                "lifetime_direct_costs": [1.0e6],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            report_graphs_module.distribution_mobilization(
                df_logs=df_logs,
                vessels=vessels,
                df_kpi_om=df_kpi_om,
                name="mobilisation_test",
                save_dir=tmpdir,
            )
            out_path = os.path.join(tmpdir, "mobilisation_test.jpg")
            self.assertTrue(os.path.exists(out_path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
