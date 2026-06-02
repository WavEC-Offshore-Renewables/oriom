import unittest
import os
import pandas as pd
import numpy as np
from copy import deepcopy

# Import classes
from oriom.classes.Metocean import Metocean

# Import functions
from oriom.core.timeseries_analysis.timestep_power import (
    add_power_columns,
    apply_power_loss,
)


class DummyPowerLosses:
    def __init__(self, power_loss=False, wake_loss=None, electric_loss=None):
        self.power_loss = power_loss
        self.wake_loss = wake_loss if wake_loss is not None else pd.DataFrame()
        self.electric_loss = electric_loss if electric_loss is not None else pd.DataFrame()


class TestTimestepPower(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class Curve:
            array = None
            c_in = None
            c_off = None

        class Matrix:
            matrix = None

        class DummyStatInputs:
            start_year = {"value": 2018}
            lifetime = {"value": 1}

        file_metocean = os.path.join(
            os.getcwd(),
            "tests",
            "test_files",
            "metocean",
            "metocean_dummy_hourly.csv",
        )

        cls.metocean = Metocean(
            file_=file_metocean,
            latitude=41.615065,
            longitude=-9.348514,
            stat_inputs=DummyStatInputs,
        )
        cls.metocean.generateTe()

        cls.wind_curve = Curve
        cls.wind_curve.array = np.array(
            [0, 0, 0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.1, 1.3, 1.5, 1.65,
             1.85, 1.92, 1.95, 2, 2, 2, 2, 2, 2, 0]
        )
        cls.wind_curve.c_in = 3
        cls.wind_curve.c_off = 15

        cls.wave_matrix = Matrix
        cls.wave_matrix.matrix = pd.DataFrame(
            {
                "(3,5)": [0, 100, 160, 200],
                "(5,7)": [0, 200, 200, 240],
                "(7,9)": [300, 350, 400, 0],
                "(9,11)": [250, 300, 380, 0],
                "(11,13)": [150, 260, 0, 0],
            },
            index=["(0,2)", "(2,4)", "(4,6)", "(6,8)"],
        )
        cls.wave_matrix.matrix.index = list(map(eval, cls.wave_matrix.matrix.index))
        cls.wave_matrix.matrix.columns = list(map(eval, cls.wave_matrix.matrix.columns))

        cls.no_power_losses = DummyPowerLosses(power_loss=False)

    def test_add_power_columns_one_device_without_losses(self):
        metocean = deepcopy(self.metocean)

        new_metocean = add_power_columns(
            df_metocean=metocean.df_timeseries.copy(deep=True),
            power_losses=self.no_power_losses,
            pcurve_wind=self.wind_curve,
            pmatrix_wave=self.wave_matrix,
            ndevices_wind=1,
            ndevices_wave=1,
        )

        self.assertAlmostEqual(new_metocean["p_wind"].iloc[0], 1.25)
        self.assertAlmostEqual(new_metocean["p_wind"].iloc[1], 1.126)
        self.assertAlmostEqual(new_metocean["p_wind_per_device"].iloc[1], 1.126)

        self.assertAlmostEqual(new_metocean["p_wave"].iloc[5], 0)
        self.assertAlmostEqual(new_metocean["p_wave"].iloc[11], 150)
        self.assertAlmostEqual(new_metocean["p_wave"].iloc[-6], 150)
        self.assertAlmostEqual(new_metocean["p_wave"].iloc[-1], 0.0)
        self.assertAlmostEqual(new_metocean["p_wave_per_device"].iloc[-1], 0.0)

    def test_add_power_columns_multiple_devices_without_losses(self):
        metocean = deepcopy(self.metocean)

        new_metocean = add_power_columns(
            df_metocean=metocean.df_timeseries.copy(deep=True),
            power_losses=self.no_power_losses,
            pcurve_wind=self.wind_curve,
            pmatrix_wave=self.wave_matrix,
            ndevices_wind=5,
            ndevices_wave=5,
        )

        self.assertAlmostEqual(new_metocean["p_wind"].iloc[0], 6.25)
        self.assertAlmostEqual(new_metocean["p_wind_per_device"].iloc[0], 1.25)
        self.assertAlmostEqual(new_metocean["p_wave"].iloc[-6], 750.0)
        self.assertAlmostEqual(new_metocean["p_wave_per_device"].iloc[-6], 150)

    def test_apply_power_loss_empty_losses_returns_unchanged_dataframe(self):
        df = pd.DataFrame(
            {
                "ws": [5.0, 10.0],
                "p_wind": [100.0, 200.0],
                "p_wind_per_device": [50.0, 100.0],
                "system_power_loss": [0.0, 0.0],
            }
        )

        result = apply_power_loss(
            df_metocean=df.copy(deep=True),
            p_losses=pd.DataFrame(),
            affecting_variable="ws",
            power_column=["p_wind", "p_wind_per_device"],
        )

        pd.testing.assert_frame_equal(result, df)

    def test_apply_power_loss_interpolates_and_applies_loss(self):
        df = pd.DataFrame(
            {
                "ws": [0.0, 5.0, 10.0],
                "p_wind": [100.0, 200.0, 300.0],
                "p_wind_per_device": [50.0, 100.0, 150.0],
                "system_power_loss": [0.0, 0.0, 0.0],
            }
        )

        wake_losses = pd.DataFrame(
            {
                "ws": [0.0, 10.0],
                "power_loss": [0.0, 0.20],
            }
        )

        result = apply_power_loss(
            df_metocean=df.copy(deep=True),
            p_losses=wake_losses,
            affecting_variable="ws",
            power_column=["p_wind", "p_wind_per_device"],
        )

        expected = pd.DataFrame(
            {
                "ws": [0.0, 5.0, 10.0],
                "p_wind": [100.0, 180.0, 240.0],
                "p_wind_per_device": [50.0, 90.0, 120.0],
                "system_power_loss": [0.0, 0.10, 0.20],
            }
        )

        electric_losses = pd.DataFrame(
            {
                "p_wind": [0.0, 10.0],
                "power_loss": [0.0, 0.20],
            }
        )

        result = apply_power_loss(
            df_metocean=result,
            p_losses=electric_losses,
            affecting_variable="p_wind",
            power_column=["p_wind", "p_wind_per_device"],
        )

        expected = pd.DataFrame(
            {
                "ws": [0.0, 5.0, 10.0],
                "p_wind": [80.0, 144.0, 192.0],
                "p_wind_per_device": [40.0, 72.0, 96.0],
                "system_power_loss": [0.2, 0.3, 0.4],
            }
        )

        pd.testing.assert_frame_equal(result, expected)

    def test_apply_power_loss_missing_affecting_variable_raises_key_error(self):
        df = pd.DataFrame(
            {
                "ws": [5.0, 10.0],
                "p_wind": [100.0, 200.0],
                "p_wind_per_device": [50.0, 100.0],
                "system_power_loss": [0.0, 0.0],
            }
        )

        losses = pd.DataFrame(
            {
                "wrong_column": [0.0, 10.0],
                "power_loss": [0.0, 0.20],
            }
        )

        with self.assertRaises(KeyError):
            apply_power_loss(
                df_metocean=df,
                p_losses=losses,
                affecting_variable="ws",
                power_column=["p_wind", "p_wind_per_device"],
            )

    def test_add_power_columns_with_wake_and_electric_losses(self):
        metocean = deepcopy(self.metocean)

        baseline = add_power_columns(
            df_metocean=metocean.df_timeseries.copy(deep=True),
            power_losses=self.no_power_losses,
            pcurve_wind=self.wind_curve,
            pmatrix_wave=self.wave_matrix,
            ndevices_wind=5,
            ndevices_wave=5,
        )

        wake_loss = pd.DataFrame(
            {
                "ws": [0.0, 100.0],
                "power_loss": [0.10, 0.10],
            }
        )

        electric_loss = pd.DataFrame(
            {
                "p_wind": [0.0, 10000.0],
                "p_wave": [0.0, 10000.0],
                "power_loss": [0.05, 0.05],
            }
        )

        power_losses = DummyPowerLosses(
            power_loss=True,
            wake_loss=wake_loss,
            electric_loss=electric_loss,
        )

        result = add_power_columns(
            df_metocean=metocean.df_timeseries.copy(deep=True),
            power_losses=power_losses,
            pcurve_wind=self.wind_curve,
            pmatrix_wave=self.wave_matrix,
            ndevices_wind=5,
            ndevices_wave=5,
        )

        # Wind: wake loss 10%, then electric loss 5%
        np.testing.assert_allclose(
            result["p_wind"].to_numpy(),
            baseline["p_wind"].to_numpy() * 0.90 * 0.95,
            rtol=1e-6,
            atol=1e-6,
        )

        np.testing.assert_allclose(
            result["p_wind_per_device"].to_numpy(),
            baseline["p_wind_per_device"].to_numpy() * 0.90 * 0.95,
            rtol=1e-6,
            atol=1e-6,
        )

        # Wave: only electric loss 5%
        np.testing.assert_allclose(
            result["p_wave"].to_numpy(),
            baseline["p_wave"].to_numpy() * 0.95,
            rtol=1e-6,
            atol=1e-6,
        )

        np.testing.assert_allclose(
            result["p_wave_per_device"].to_numpy(),
            baseline["p_wave_per_device"].to_numpy() * 0.95,
            rtol=1e-6,
            atol=1e-6,
        )

    def test_add_power_columns_raises_error_if_wind_curve_without_wind_devices(self):
        metocean = deepcopy(self.metocean)

        with self.assertRaises(ValueError):
            add_power_columns(
                df_metocean=metocean.df_timeseries.copy(deep=True),
                power_losses=self.no_power_losses,
                pcurve_wind=self.wind_curve,
                pmatrix_wave=None,
                ndevices_wind=0,
                ndevices_wave=0,
            )

    def test_add_power_columns_raises_error_if_wave_matrix_without_wave_devices(self):
        metocean = deepcopy(self.metocean)

        with self.assertRaises(ValueError):
            add_power_columns(
                df_metocean=metocean.df_timeseries.copy(deep=True),
                power_losses=self.no_power_losses,
                pcurve_wind=None,
                pmatrix_wave=self.wave_matrix,
                ndevices_wind=0,
                ndevices_wave=0,
            )


if __name__ == "__main__":
    unittest.main()