#test_metoceans_builder.py

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, sentinel

import oriom.core.builders.metoceans_builder as metocean_builder_module


class TestMetoceanBuilder(unittest.TestCase):
    """Tests for metocean_builder."""

    def setUp(self):
        """Create minimal input objects required by metocean_builder."""
        self.run_dir = Path("fake/run/dir")

        self.dirs = SimpleNamespace(
            run_dir=self.run_dir,
        )

        self.tseries_inputs = SimpleNamespace(
            surface_roughness={"value": 0.03},
        )

        self.inputs = SimpleNamespace(
            tseries=self.tseries_inputs,
            stats=sentinel.stat_inputs,
        )

        self.farm_technologies = SimpleNamespace(
            power=sentinel.power_farm,
            wtg=sentinel.wtg,
        )

    @patch.object(metocean_builder_module, "Metocean")
    def test_builds_site_port_and_tow_metocean(self, mock_metocean_class):
        """
        The builder should:
        - create site metocean
        - create port metocean using site metocean
        - create tow metocean and tow distance
        - attach power columns to site metocean
        - return all objects in the expected dictionary
        """
        site_metocean = sentinel.site_metocean
        port_metocean = sentinel.port_metocean
        tow_metocean = sentinel.tow_metocean
        tow_distance = sentinel.tow_distance
        site_metocean_with_power = sentinel.site_metocean_with_power

        mock_metocean_class.from_run_dir.side_effect = [
            (site_metocean, sentinel.site_metadata),
            (port_metocean, sentinel.port_metadata),
            (tow_metocean, tow_distance),
        ]

        mock_metocean_class.attach_power_columns.return_value = site_metocean_with_power

        result = metocean_builder_module.metocean_builder(
            dirs=self.dirs,
            inputs=self.inputs,
            farm_technologies=self.farm_technologies,
        )

        self.assertEqual(
            result,
            {
                "metocean": site_metocean_with_power,
                "metocean_port": port_metocean,
                "metocean_tow": tow_metocean,
                "metocean_tow_distance": tow_distance,
            },
        )

        self.assertEqual(mock_metocean_class.from_run_dir.call_count, 3)

        site_call = mock_metocean_class.from_run_dir.call_args_list[0]
        port_call = mock_metocean_class.from_run_dir.call_args_list[1]
        tow_call = mock_metocean_class.from_run_dir.call_args_list[2]

        self.assertEqual(
            site_call.kwargs,
            {
                "run_dir": self.run_dir,
                "tseries_inputs": self.tseries_inputs,
                "power_farm": self.farm_technologies.power,
                "wtg": self.farm_technologies.wtg,
                "z0": 0.03,
                "stat_inputs": self.inputs.stats,
            },
        )

        self.assertEqual(
            port_call.kwargs,
            {
                "run_dir": self.run_dir,
                "tseries_inputs": self.tseries_inputs,
                "stat_inputs": self.inputs.stats,
                "port_metocean": True,
                "site_metocean": site_metocean,
            },
        )

        self.assertEqual(
            tow_call.kwargs,
            {
                "run_dir": self.run_dir,
                "tseries_inputs": self.tseries_inputs,
                "stat_inputs": self.inputs.stats,
                "tow_metocean": True,
            },
        )

        mock_metocean_class.attach_power_columns.assert_called_once_with(
            metocean=site_metocean,
            power_farm=self.farm_technologies.power,
            out_dir=self.run_dir,
        )

    @patch.object(metocean_builder_module, "Metocean")
    def test_uses_surface_roughness_value_as_z0(self, mock_metocean_class):
        """
        The site metocean call should pass inputs.tseries.surface_roughness["value"]
        as z0.
        """
        self.inputs.tseries.surface_roughness["value"] = 0.12

        mock_metocean_class.from_run_dir.side_effect = [
            (sentinel.site_metocean, sentinel.site_metadata),
            (sentinel.port_metocean, sentinel.port_metadata),
            (sentinel.tow_metocean, sentinel.tow_distance),
        ]

        mock_metocean_class.attach_power_columns.return_value = sentinel.site_metocean_with_power

        metocean_builder_module.metocean_builder(
            dirs=self.dirs,
            inputs=self.inputs,
            farm_technologies=self.farm_technologies,
        )

        site_call = mock_metocean_class.from_run_dir.call_args_list[0]

        self.assertEqual(site_call.kwargs["z0"], 0.12)

    @patch.object(metocean_builder_module, "Metocean")
    def test_propagates_from_run_dir_errors(self, mock_metocean_class):
        """
        The builder should not hide errors raised by Metocean.from_run_dir.
        """
        mock_metocean_class.from_run_dir.side_effect = RuntimeError("Failed to build metocean")

        with self.assertRaises(RuntimeError):
            metocean_builder_module.metocean_builder(
                dirs=self.dirs,
                inputs=self.inputs,
                farm_technologies=self.farm_technologies,
            )

        mock_metocean_class.attach_power_columns.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)