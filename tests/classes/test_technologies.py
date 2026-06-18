# tests/domain/test_technologies.py

import os
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from oriom.domain.Techs.Technologies import (
    TechnologyBuilder,
    PowerTechResult,
    TechFarm,
)


class TestTechnologyBuilder(unittest.TestCase):
    def setUp(self):
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_ctx.cleanup)
        self.run_dir = self.tmp_ctx.name

        self.wtg_file = os.path.join(self.run_dir, "wtg.yaml")
        self.wec_file = os.path.join(self.run_dir, "wec.yaml")
        self.pv_file = os.path.join(self.run_dir, "pv.yaml")

        self.file_electrical_loss = os.path.join(self.run_dir, "electrical_loss.csv")
        self.file_wake_loss = os.path.join(self.run_dir, "wake_loss.csv")

    @patch("oriom.domain.Techs.Technologies.WindTurbineGenerator")
    @patch("oriom.domain.Techs.Technologies.WaveEnergyConverter")
    @patch("oriom.domain.Techs.Technologies.PVProduction")
    @patch("oriom.domain.Techs.Technologies.check_file_exists")
    def test_create_technologies_reuse_when_yaml_already_in_run_dir(
        self, m_check_exists, m_pv, m_wec, m_wtg
    ):
        m_check_exists.side_effect = lambda d, file_name: True

        wtg_inst = MagicMock(number_devices=3)
        wec_inst = MagicMock(number_devices=2)
        pv_inst = MagicMock(number_devices=10)

        m_wtg.from_yaml.return_value = wtg_inst
        m_wec.from_yaml.return_value = wec_inst
        m_pv.from_yaml.return_value = pv_inst

        wtg, wec, pv = TechnologyBuilder.create_technologies(
            self.run_dir, self.wtg_file, self.wec_file, self.pv_file
        )

        m_wtg.from_yaml.assert_called_once_with(directory=self.run_dir, name="wtg")
        m_wec.from_yaml.assert_called_once_with(directory=self.run_dir, name="wec")
        m_pv.from_yaml.assert_called_once_with(directory=self.run_dir, name="pv")

        self.assertIs(wtg, wtg_inst)
        self.assertIs(wec, wec_inst)
        self.assertIs(pv, pv_inst)

    @patch("oriom.domain.Techs.Technologies.WindTurbineGenerator")
    @patch("oriom.domain.Techs.Technologies.WaveEnergyConverter")
    @patch("oriom.domain.Techs.Technologies.PVProduction")
    @patch("oriom.domain.Techs.Technologies.check_file_exists")
    def test_create_technologies_build_when_yaml_not_in_run_dir(
        self, m_check_exists, m_pv, m_wec, m_wtg
    ):
        m_check_exists.side_effect = lambda d, file_name: False

        wtg_inst = MagicMock(number_devices=1)
        wec_inst = MagicMock(number_devices=1)
        pv_inst = MagicMock(number_devices=1)

        m_wtg.get_wtg_from_yaml.return_value = wtg_inst
        m_wec.get_wec_from_yaml.return_value = wec_inst
        m_pv.get_pv_from_yaml.return_value = pv_inst

        wtg, wec, pv = TechnologyBuilder.create_technologies(
            self.run_dir, self.wtg_file, self.wec_file, self.pv_file
        )

        m_wtg.get_wtg_from_yaml.assert_called_once_with(
            file_path=self.wtg_file,
            out_dir=self.run_dir
        )
        m_wec.get_wec_from_yaml.assert_called_once_with(
            file_path=self.wec_file,
            out_dir=self.run_dir
        )
        m_pv.get_pv_from_yaml.assert_called_once_with(
            file_path=self.pv_file,
            out_dir=self.run_dir
        )

        self.assertIs(wtg, wtg_inst)
        self.assertIs(wec, wec_inst)
        self.assertIs(pv, pv_inst)

    @patch("oriom.domain.Techs.Technologies.WindTurbineGenerator")
    @patch("oriom.domain.Techs.Technologies.WaveEnergyConverter")
    @patch("oriom.domain.Techs.Technologies.PVProduction")
    @patch("oriom.domain.Techs.Technologies.check_file_exists")
    def test_create_technologies_raises_if_no_number_devices_anywhere(
        self, m_check_exists, m_pv, m_wec, m_wtg
    ):
        m_check_exists.side_effect = lambda d, file_name: False

        m_wtg.get_wtg_from_yaml.return_value = SimpleNamespace()
        m_wec.get_wec_from_yaml.return_value = SimpleNamespace()
        m_pv.get_pv_from_yaml.return_value = SimpleNamespace()

        with self.assertRaises(ValueError):
            TechnologyBuilder.create_technologies(
                self.run_dir,
                self.wtg_file,
                self.wec_file,
                self.pv_file
            )

    @patch("oriom.domain.Techs.Technologies.save_file_csv")
    @patch("oriom.domain.Techs.Technologies.PVProduction")
    @patch("oriom.domain.Techs.Technologies.Power.Power_Losses")
    @patch("oriom.domain.Techs.Technologies.Power.Matrix")
    @patch("oriom.domain.Techs.Technologies.Power.Curve")
    def test_build_power_technologies_all_present(
        self,
        m_power_curve,
        m_power_matrix,
        m_power_losses,
        m_pv_prod,
        m_save_csv
    ):
        wtg = MagicMock(
            number_devices=4,
            pcurve_file="wtg_curve.csv",
            cut_in=3.5,
            cut_off=25.0,
            rated_power=8000,
        )
        wec = MagicMock(
            number_devices=6,
            pmatrix_file="wec_matrix.csv",
            rated_power=1000,
        )
        pv = MagicMock(
            number_devices=100,
            max_failure_module=5,
            degradation_rate=0.007,
            pvprod_file="pvprod.csv",
        )

        power_losses = MagicMock(name="power_losses")
        pcurve = MagicMock(name="pcurve")
        pmatrix = MagicMock(name="pmatrix")
        pv_stats_df = MagicMock(name="pv_stats_df")

        m_power_losses.return_value = power_losses
        m_power_curve.return_value = pcurve
        m_power_matrix.return_value = pmatrix
        m_pv_prod.pv_farm_statistical_analysis.return_value = pv_stats_df

        result = TechnologyBuilder.build_power_technologies(
            wtg=wtg,
            wec=wec,
            pv=pv,
            run_dir=self.run_dir,
            file_electrical_loss=self.file_electrical_loss,
            file_wake_loss=self.file_wake_loss,
        )

        m_power_losses.assert_called_once_with(
            file_electric_loss=self.file_electrical_loss,
            file_wake_loss=self.file_wake_loss,
        )

        m_power_curve.assert_called_once_with(
            file_="wtg_curve.csv",
            c_in=3.5,
            c_off=25.0,
            rated=8000
        )

        m_power_matrix.assert_called_once_with(
            file_="wec_matrix.csv",
            rated=1000
        )

        m_pv_prod.pv_farm_statistical_analysis.assert_called_once_with(
            pvprod_file="pvprod.csv",
            number_devices=100
        )

        m_save_csv.assert_called_once_with(
            pv_stats_df,
            self.run_dir,
            "power_pv_farm.csv"
        )

        self.assertIsInstance(result, PowerTechResult)
        self.assertIs(result.power_losses, power_losses)

        self.assertEqual(result.wtg_number_devices, 4)
        self.assertIs(result.wtg_pcurve, pcurve)

        self.assertEqual(result.wec_number_devices, 6)
        self.assertIs(result.wec_pmatrix, pmatrix)

        self.assertEqual(result.pv_number_devices, 100)
        self.assertIs(result.pv_farm_prod, pv_stats_df)
        self.assertEqual(result.degradation_rate, 0.007)
        self.assertEqual(result.pv_max_failure_module, 5)

    @patch("oriom.domain.Techs.Technologies.save_file_csv")
    @patch("oriom.domain.Techs.Technologies.PVProduction")
    @patch("oriom.domain.Techs.Technologies.Power.Power_Losses")
    @patch("oriom.domain.Techs.Technologies.Power.Matrix")
    @patch("oriom.domain.Techs.Technologies.Power.Curve")
    def test_build_power_technologies_missing_each_branch_sets_none(
        self,
        m_power_curve,
        m_power_matrix,
        m_power_losses,
        m_pv_prod,
        m_save_csv
    ):
        wtg = SimpleNamespace()
        wec = SimpleNamespace()
        pv = SimpleNamespace()

        power_losses = MagicMock(name="power_losses")
        m_power_losses.return_value = power_losses

        result = TechnologyBuilder.build_power_technologies(
            wtg=wtg,
            wec=wec,
            pv=pv,
            run_dir=self.run_dir,
            file_electrical_loss=None,
            file_wake_loss=None,
        )

        m_power_losses.assert_called_once_with(
            file_electric_loss=None,
            file_wake_loss=None,
        )

        m_power_curve.assert_not_called()
        m_power_matrix.assert_not_called()
        m_pv_prod.pv_farm_statistical_analysis.assert_not_called()
        m_save_csv.assert_not_called()

        self.assertIsInstance(result, PowerTechResult)
        self.assertIs(result.power_losses, power_losses)

        self.assertIsNone(result.wtg_number_devices)
        self.assertIsNone(result.wtg_pcurve)

        self.assertIsNone(result.wec_number_devices)
        self.assertIsNone(result.wec_pmatrix)

        self.assertIsNone(result.pv_number_devices)
        self.assertIsNone(result.pv_farm_prod)
        self.assertIsNone(result.degradation_rate)
        self.assertIsNone(result.pv_max_failure_module)

    @patch.object(TechnologyBuilder, "create_technologies")
    @patch.object(TechnologyBuilder, "build_power_technologies")
    def test_build_technologies_integration_returns_techfarm(
        self,
        m_build_power,
        m_create
    ):
        wtg = MagicMock(name="wtg")
        wec = MagicMock(name="wec")
        pv = MagicMock(name="pv")
        power = MagicMock(name="power")

        m_create.return_value = (wtg, wec, pv)
        m_build_power.return_value = power

        farm = TechnologyBuilder.build_technologies(
            run_dir=self.run_dir,
            wtg_file=self.wtg_file,
            wec_file=self.wec_file,
            pv_file=self.pv_file,
            file_electrical_loss=self.file_electrical_loss,
            file_wake_loss=self.file_wake_loss,
        )

        self.assertIsInstance(farm, TechFarm)
        self.assertIs(farm.wtg, wtg)
        self.assertIs(farm.wec, wec)
        self.assertIs(farm.pv, pv)
        self.assertIs(farm.power, power)

        m_create.assert_called_once_with(
            self.run_dir,
            self.wtg_file,
            self.wec_file,
            self.pv_file,
        )

        m_build_power.assert_called_once_with(
            wtg=wtg,
            wec=wec,
            pv=pv,
            run_dir=self.run_dir,
            file_electrical_loss=self.file_electrical_loss,
            file_wake_loss=self.file_wake_loss,
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)