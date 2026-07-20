# tests/core/builders/test_system_builder.py

import unittest
from types import SimpleNamespace
from unittest.mock import patch, sentinel

import oriom.core.builders.systems_builder as system_builder_module


class TestSystemBuilder(unittest.TestCase):
    """Tests for system_builder."""

    def setUp(self):
        """Create minimal input objects required by system_builder."""
        self.inputs = SimpleNamespace(
            tseries=SimpleNamespace(
                site_lat={"value": 41.123},
                site_lon={"value": -8.456},
            )
        )

        self.farm_technologies = sentinel.farm_technologies
        self.G_layouts = sentinel.G_layouts
        self.failures = [sentinel.failure_1, sentinel.failure_2]

    @patch.object(system_builder_module, "Storage")
    @patch.object(system_builder_module, "Port")
    @patch.object(system_builder_module, "Farm")
    def test_creates_farm_port_and_storage(
        self,
        mock_farm_class,
        mock_port_class,
        mock_storage_class,
    ):
        """
        The builder should create Farm, Port and Storage objects
        with the expected arguments.
        """
        mock_farm_class.return_value = sentinel.farm
        mock_port_class.return_value = sentinel.port
        mock_storage_class.return_value = sentinel.storage

        farm, port, storage = system_builder_module.system_builder(
            inputs=self.inputs,
            farm_technologies=self.farm_technologies,
            G_layouts=self.G_layouts,
            failures=self.failures,
        )

        self.assertEqual(farm, sentinel.farm)
        self.assertEqual(port, sentinel.port)
        self.assertEqual(storage, sentinel.storage)

        mock_farm_class.assert_called_once_with(
            inputs=self.inputs,
            farm_tech=self.farm_technologies,
            layouts=self.G_layouts,
            failures=self.failures,
        )

        mock_port_class.assert_called_once_with(
            id_="port_id",
            name="My_Port",
            location={
                "lat": 41.123,
                "lon": -8.456,
            },
        )

        mock_storage_class.assert_called_once_with(
            id_="storage_id",
            max_space=5,
        )

    @patch.object(system_builder_module, "Storage")
    @patch.object(system_builder_module, "Port")
    @patch.object(system_builder_module, "Farm")
    def test_uses_site_coordinates_from_inputs(
        self,
        mock_farm_class,
        mock_port_class,
        mock_storage_class,
    ):
        """
        The Port location should use inputs.tseries.site_lat["value"]
        and inputs.tseries.site_lon["value"].
        """
        self.inputs.tseries.site_lat["value"] = 39.75
        self.inputs.tseries.site_lon["value"] = -9.25

        system_builder_module.system_builder(
            inputs=self.inputs,
            farm_technologies=self.farm_technologies,
            G_layouts=self.G_layouts,
            failures=self.failures,
        )

        port_call = mock_port_class.call_args

        self.assertEqual(
            port_call.kwargs["location"],
            {
                "lat": 39.75,
                "lon": -9.25,
            },
        )

    @patch.object(system_builder_module, "Storage")
    @patch.object(system_builder_module, "Port")
    @patch.object(system_builder_module, "Farm")
    def test_propagates_farm_creation_errors(
        self,
        mock_farm_class,
        mock_port_class,
        mock_storage_class,
    ):
        """
        The builder should not hide errors raised while creating the Farm object.
        """
        mock_farm_class.side_effect = RuntimeError("Failed to create farm")

        with self.assertRaises(RuntimeError):
            system_builder_module.system_builder(
                inputs=self.inputs,
                farm_technologies=self.farm_technologies,
                G_layouts=self.G_layouts,
                failures=self.failures,
            )

        mock_port_class.assert_not_called()
        mock_storage_class.assert_not_called()

    @patch.object(system_builder_module, "Storage")
    @patch.object(system_builder_module, "Port")
    @patch.object(system_builder_module, "Farm")
    def test_propagates_port_creation_errors(
        self,
        mock_farm_class,
        mock_port_class,
        mock_storage_class,
    ):
        """
        The builder should not hide errors raised while creating the Port object.
        """
        mock_farm_class.return_value = sentinel.farm
        mock_port_class.side_effect = RuntimeError("Failed to create port")

        with self.assertRaises(RuntimeError):
            system_builder_module.system_builder(
                inputs=self.inputs,
                farm_technologies=self.farm_technologies,
                G_layouts=self.G_layouts,
                failures=self.failures,
            )

        mock_storage_class.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)