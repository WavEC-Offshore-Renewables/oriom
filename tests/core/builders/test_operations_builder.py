# tests/core/builders/test_operations_builder.py

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch, sentinel

import oriom.core.builders.operations_builder as operations_builder_module


# ------------------------------------------------------------------
# Test doubles
# ------------------------------------------------------------------

class DummyActivity:
    """Minimal activity object used to test activity CSV saving."""

    def __init__(self):
        self.save_activities_as_csv = MagicMock()


class DummyOperation:
    """Minimal operation object used by aux_operation_builder."""

    def __init__(
        self,
        op_id,
        duration_net=1,
        vessel1_id=None,
        rov_drone=None,
        addition_op_tow=None,
    ):
        self.id = op_id
        self.duration_net = duration_net
        self.vessel1_id = vessel1_id
        self.rov_drone = rov_drone
        self.addition_op_tow = addition_op_tow
        self.activities = [DummyActivity()]

        self.define_months_operations = MagicMock()
        self.define_level = MagicMock()
        self.define_previous_op_tow = MagicMock()
        self.to_yaml = MagicMock()


class TestAuxOperationBuilder(unittest.TestCase):
    """Tests for aux_operation_builder."""

    def setUp(self):
        """Create common fake inputs for aux_operation_builder."""
        self.Config = SimpleNamespace(
            OPERATION_FILES=sentinel.operation_files,
        )

        self.inputs = SimpleNamespace(
            general=sentinel.general_inputs,
            tseries=SimpleNamespace(
                shift_duration={"value": 8},
                distance={"value": 25.0},
                max_wait={"value": 72},
                find_time_between_devices=MagicMock(return_value=3.5),
            ),
        )

        self.files = SimpleNamespace(
            rovs_drones_file="rovs_drones.yaml",
            operations_tow_file="operations_tow.yaml",
            operations_insp_site_file="operations_insp_site.yaml",
            operations_insp_port_file="operations_insp_port.yaml",
            operations_corr_major_file="operations_corr_major.yaml",
            operations_corr_minor_file="operations_corr_minor.yaml",
            vessels_file="vessels.yaml",
            vessels_fuel_cons_file="fuel_consumption.yaml",
            vessels_load_factor_file="load_factor.yaml",
            vessels_fuel_density_file="fuel_density.yaml",
            operations_activities_file="activities.yaml",
        )

        self.dirs = SimpleNamespace(
            operation_dir="fake/operation_dir",
        )

        self.failures = [sentinel.failure]

        self.farm_technologies = SimpleNamespace(
            wtg=sentinel.wtg,
            wec=sentinel.wec,
            pv=sentinel.pv,
        )

        self.G_layouts = {
            "ofw": sentinel.wind_layout,
        }

        self.rov_drone = sentinel.rov_drone

        self.tow_operation = DummyOperation(
            op_id="tow_001",
            addition_op_tow=sentinel.additional_tow_operation,
        )
        self.inspect_site_operation = DummyOperation(
            op_id="inspect_site_001",
        )
        self.inspect_port_operation = DummyOperation(
            op_id="inspect_port_001",
        )
        self.corrective_major_operation = DummyOperation(
            op_id="corrective_major_001",
            vessel1_id="vessel_001",
            rov_drone="rov_001",
        )
        self.corrective_minor_operation = DummyOperation(
            op_id="corrective_minor_001",
            duration_net=2,
        )

    def run_builder_with_patches(self):
        """Run aux_operation_builder with all external dependencies mocked."""
        with patch.object(
            operations_builder_module.RovDrone,
            "get_rovdrones_from_yaml",
            return_value=[self.rov_drone],
        ) as mock_get_rovdrones, patch.object(
            operations_builder_module.OperationTow,
            "get_operations_from_yaml",
            return_value=[self.tow_operation],
        ) as mock_get_tow_operations, patch.object(
            operations_builder_module.InspectionSite,
            "get_inspections_from_yaml",
            return_value=[self.inspect_site_operation],
        ) as mock_get_site_inspections, patch.object(
            operations_builder_module.InspectionPort,
            "get_inspections_from_yaml",
            return_value=[self.inspect_port_operation],
        ) as mock_get_port_inspections, patch.object(
            operations_builder_module.CorrectiveMajor,
            "get_operations_from_yaml",
            return_value=[self.corrective_major_operation],
        ) as mock_get_major_operations, patch.object(
            operations_builder_module.CorrectiveMinor,
            "get_operations_from_yaml",
            return_value=[self.corrective_minor_operation],
        ) as mock_get_minor_operations, patch.object(
            operations_builder_module.aux_functions,
            "create_run_folder_operation",
        ) as mock_create_run_folder, patch.object(
            operations_builder_module.aux_operation,
            "get_failures",
        ) as mock_get_failures, patch.object(
            operations_builder_module.Define_operation,
            "define_vessels",
        ) as mock_define_vessels, patch.object(
            operations_builder_module.Define_operation,
            "define_rovs",
        ) as mock_define_rovs, patch.object(
            operations_builder_module.aux_operation,
            "define_device_at_port",
        ) as mock_define_device_at_port, patch.object(
            operations_builder_module.aux_operation,
            "define_activities",
        ) as mock_define_activities, patch.object(
            operations_builder_module.aux_operation,
            "level_component_check",
        ) as mock_level_component_check, patch.object(
            operations_builder_module.aux_operation,
            "operation_check_identities",
        ) as mock_operation_check_identities, patch.object(
            operations_builder_module,
            "check_files",
            None,
        ):
            result = operations_builder_module.aux_operation_builder(
                Config=self.Config,
                inputs=self.inputs,
                files=self.files,
                dirs=self.dirs,
                failures=self.failures,
                farm_technologies=self.farm_technologies,
                G_layouts=self.G_layouts,
            )

            mocks = SimpleNamespace(
                get_rovdrones=mock_get_rovdrones,
                get_tow_operations=mock_get_tow_operations,
                get_site_inspections=mock_get_site_inspections,
                get_port_inspections=mock_get_port_inspections,
                get_major_operations=mock_get_major_operations,
                get_minor_operations=mock_get_minor_operations,
                create_run_folder=mock_create_run_folder,
                get_failures=mock_get_failures,
                define_vessels=mock_define_vessels,
                define_rovs=mock_define_rovs,
                define_device_at_port=mock_define_device_at_port,
                define_activities=mock_define_activities,
                level_component_check=mock_level_component_check,
                operation_check_identities=mock_operation_check_identities,
            )

        return result, mocks

    def test_aux_operation_builder_returns_expected_dictionary(self):
        """The builder should return all operation groups and the vessel cache."""
        result, _mocks = self.run_builder_with_patches()

        self.assertEqual(
            result,
            {
                "rovs_drones": [self.rov_drone],
                "vessels": {},
                "operations_tow": [self.tow_operation],
                "operations_corr_major": [self.corrective_major_operation],
                "operations_corr_minor": [self.corrective_minor_operation],
                "operations_inspect_port": [self.inspect_port_operation],
                "operations_inspect_site": [self.inspect_site_operation],
                "total_operations": [
                    self.tow_operation,
                    self.inspect_site_operation,
                    self.inspect_port_operation,
                    self.corrective_major_operation,
                    self.corrective_minor_operation,
                ],
            },
        )

    def test_aux_operation_builder_loads_operations_from_expected_files(self):
        """The builder should load all operation types from the expected input files."""
        _result, mocks = self.run_builder_with_patches()

        mocks.get_rovdrones.assert_called_once_with(self.files.rovs_drones_file)

        mocks.get_tow_operations.assert_called_once_with(
            file_path=self.files.operations_tow_file,
        )

        mocks.get_site_inspections.assert_called_once_with(
            file_path=self.files.operations_insp_site_file,
        )

        mocks.get_port_inspections.assert_called_once_with(
            file_path=self.files.operations_insp_port_file,
            towing_operations=[self.tow_operation],
        )

        mocks.get_major_operations.assert_called_once_with(
            file_path=self.files.operations_corr_major_file,
            towing_operations=[self.tow_operation],
        )

        mocks.get_minor_operations.assert_called_once_with(
            file_path=self.files.operations_corr_minor_file,
        )

    def test_aux_operation_builder_populates_operations(self):
        """The builder should populate failures, folders, vessels, ROVs, levels and device-at-port data."""
        _result, mocks = self.run_builder_with_patches()

        self.corrective_major_operation.define_months_operations.assert_called_once()
        self.corrective_minor_operation.define_months_operations.assert_called_once()

        self.assertEqual(mocks.get_failures.call_count, 2)
        mocks.get_failures.assert_has_calls(
            [
                call(self.corrective_major_operation, self.failures),
                call(self.corrective_minor_operation, self.failures),
            ],
            any_order=False,
        )

        self.assertEqual(mocks.create_run_folder.call_count, 5)

        mocks.define_vessels.assert_called_once_with(
            operation=self.corrective_major_operation,
            file_vessels=self.files.vessels_file,
            file_fuel_cons=self.files.vessels_fuel_cons_file,
            file_load_factor=self.files.vessels_load_factor_file,
            file_fuel_density=self.files.vessels_fuel_density_file,
            vessels={},
        )

        mocks.define_rovs.assert_called_once_with(
            operation=self.corrective_major_operation,
            rovs_drones=[self.rov_drone],
        )

        self.assertEqual(mocks.define_device_at_port.call_count, 2)
        mocks.define_device_at_port.assert_has_calls(
            [
                call(
                    oper=self.inspect_port_operation,
                    wtg=self.farm_technologies.wtg,
                    wec=self.farm_technologies.wec,
                    pv=self.farm_technologies.pv,
                    inspection=True,
                ),
                call(
                    oper=self.corrective_major_operation,
                    wtg=self.farm_technologies.wtg,
                    wec=self.farm_technologies.wec,
                    pv=self.farm_technologies.pv,
                    inspection=False,
                ),
            ],
            any_order=False,
        )

        self.inspect_port_operation.define_level.assert_called_once_with(
            G_layouts=self.G_layouts,
        )
        self.inspect_site_operation.define_level.assert_called_once_with(
            G_layouts=self.G_layouts,
        )

    def test_aux_operation_builder_defines_activities_and_saves_files(self):
        """The builder should define activities for major corrective and tow operations."""
        _result, mocks = self.run_builder_with_patches()

        self.assertEqual(self.inputs.tseries.find_time_between_devices.call_count, 2)
        self.inputs.tseries.find_time_between_devices.assert_has_calls(
            [
                call(operation_obj_id=self.corrective_major_operation.id),
                call(operation_obj_id=self.tow_operation.id),
            ],
            any_order=False,
        )

        self.assertEqual(mocks.define_activities.call_count, 2)
        mocks.define_activities.assert_has_calls(
            [
                call(
                    operation=self.corrective_major_operation,
                    file_activities=self.files.operations_activities_file,
                    distance_to_site=self.inputs.tseries.distance["value"],
                    transit_between_devices=3.5,
                    tow_op=False,
                ),
                call(
                    operation=self.tow_operation,
                    file_activities=self.files.operations_activities_file,
                    distance_to_site=self.inputs.tseries.distance["value"],
                    transit_between_devices=3.5,
                    tow_op=True,
                ),
            ],
            any_order=False,
        )

        self.corrective_major_operation.activities[0].save_activities_as_csv.assert_called_once()
        self.tow_operation.activities[0].save_activities_as_csv.assert_called_once()

    def test_aux_operation_builder_runs_final_checks_and_writes_yaml(self):
        """The builder should check levels, write attributes and check operation identities."""
        _result, mocks = self.run_builder_with_patches()

        all_operations = [
            self.tow_operation,
            self.inspect_site_operation,
            self.inspect_port_operation,
            self.corrective_major_operation,
            self.corrective_minor_operation,
        ]

        for operation in all_operations:
            operation.to_yaml.assert_called_once()

        self.tow_operation.define_previous_op_tow.assert_called_once_with(
            [self.corrective_major_operation],
        )

        mocks.operation_check_identities.assert_called_once_with(all_operations)

    def test_aux_operation_builder_raises_when_minor_duration_is_too_long(self):
        """Minor corrective operations longer than the shift duration should raise ValueError."""
        self.corrective_minor_operation.duration_net = 8

        with self.assertRaises(ValueError):
            self.run_builder_with_patches()


class TestAuxOperationStatsBuilder(unittest.TestCase):
    """Tests for aux_operation_stats_builder."""

    def setUp(self):
        """Create common fake inputs for aux_operation_stats_builder."""
        self.inputs = SimpleNamespace(
            stats=sentinel.stats_inputs,
            tseries=SimpleNamespace(
                shift_duration={"value": 8},
            ),
        )

        self.dirs = SimpleNamespace(
            operation_dir="fake/operation_dir",
        )

        self.farm_technologies = SimpleNamespace(
            wtg=SimpleNamespace(n_device_at_port=2),
            wec=SimpleNamespace(n_device_at_port=3),
            pv=SimpleNamespace(n_device_at_port=4),
        )

        self.operations = {
            "operations_tow": ["tow_operation"],
            "operations_corr_major": ["major_operation"],
            "operations_corr_minor": ["minor_operation"],
            "operations_inspect_port": ["port_inspection"],
            "operations_inspect_site": ["site_inspection"],
            "total_operations": ["operation_001"],
        }

        self.vessels = ["vessel_001"]
        self.failures = ["failure_001"]

    @staticmethod
    def make_stats(prefix):
        """Return a side effect function that creates percentile-specific stats."""
        def _stats_side_effect(*args, **kwargs):
            percentile = kwargs["PERCENTILE"]
            return [f"{prefix}_{percentile}"]

        return _stats_side_effect

    @patch.object(operations_builder_module, "find_percentiles")
    @patch.object(operations_builder_module.OperationsTowStat, "get_towing_statistics")
    @patch.object(operations_builder_module.CorrectiveStat, "get_corrective_statistics")
    @patch.object(operations_builder_module.InspectionSiteStat, "get_inspection_statistics")
    @patch.object(operations_builder_module.InspectionPortStat, "get_inspection_statistics")
    @patch.object(operations_builder_module.Find_Element, "create")
    def test_aux_operation_stats_builder_returns_stats_and_find_element(
        self,
        mock_find_element_create,
        mock_port_stats,
        mock_site_stats,
        mock_corrective_stats,
        mock_tow_stats,
        mock_find_percentiles,
    ):
        """The stats builder should create all percentile statistics and the Find_Element object."""
        mock_find_percentiles.return_value = {
            "pmain": 50,
            "pmax": 90,
        }

        mock_tow_stats.side_effect = self.make_stats("tow")
        mock_corrective_stats.side_effect = self.make_stats("corrective")
        mock_site_stats.side_effect = self.make_stats("site")
        mock_port_stats.side_effect = self.make_stats("port")
        mock_find_element_create.return_value = sentinel.find_element

        result, find_element = operations_builder_module.aux_operation_stats_builder(
            inputs=self.inputs,
            dirs=self.dirs,
            farm_technologies=self.farm_technologies,
            operations=self.operations,
            vessels=self.vessels,
            failures=self.failures,
        )

        self.assertEqual(find_element, sentinel.find_element)

        self.assertEqual(
            result,
            {
                "inspections_port_stats": {
                    "pmain": ["port_50"],
                    "pmax": ["port_90"],
                },
                "inspections_site_stats": {
                    "pmain": ["site_50"],
                    "pmax": ["site_90"],
                },
                "operations_corrective_stats": {
                    "pmain": ["corrective_50"],
                    "pmax": ["corrective_90"],
                },
                "operations_tow_stats": {
                    "pmain": ["tow_50"],
                    "pmax": ["tow_90"],
                },
            },
        )

        mock_find_percentiles.assert_called_once_with(
            inputs_stats=self.inputs.stats,
        )

        self.assertEqual(mock_tow_stats.call_count, 2)
        self.assertEqual(mock_corrective_stats.call_count, 2)
        self.assertEqual(mock_site_stats.call_count, 2)
        self.assertEqual(mock_port_stats.call_count, 2)

        mock_port_stats.assert_has_calls(
            [
                call(
                    insepctions_port=self.operations["operations_inspect_port"],
                    PERCENTILE=50,
                    run_dir=self.dirs.operation_dir,
                    n_port_inspections={"ofw": 2, "owc": 3, "opv": 4},
                    operations_tow_stat=["tow_50"],
                    shift=self.inputs.tseries.shift_duration["value"],
                ),
                call(
                    insepctions_port=self.operations["operations_inspect_port"],
                    PERCENTILE=90,
                    run_dir=self.dirs.operation_dir,
                    n_port_inspections={"ofw": 2, "owc": 3, "opv": 4},
                    operations_tow_stat=["tow_90"],
                    shift=self.inputs.tseries.shift_duration["value"],
                ),
            ],
            any_order=False,
        )

        mock_find_element_create.assert_called_once_with(
            operations=self.operations["total_operations"],
            operations_stats=[
                "tow_50",
                "site_50",
                "port_50",
                "corrective_50",
            ],
            operations_stats_pmax=[
                "tow_90",
                "site_90",
                "port_90",
                "corrective_90",
            ],
            vessels=self.vessels,
            failures=self.failures,
        )


class TestOperationTimeseriesBuilder(unittest.TestCase):
    """Tests for operation_timeseries_builder."""

    def setUp(self):
        """Create common fake inputs for operation_timeseries_builder."""
        self.inputs = SimpleNamespace(
            tseries=SimpleNamespace(
                max_wait={"value": 72},
                shift_duration={"value": 8},
            ),
        )

        self.dirs = SimpleNamespace(
            operation_dir="fake/operation_dir",
        )

        self.operations = {
            "operations_tow": ["tow_operation"],
            "operations_inspect_site": ["site_inspection"],
            "operations_inspect_port": ["port_inspection"],
            "operations_corr_major": ["major_operation"],
            "operations_corr_minor": ["minor_operation"],
        }

        self.metocean = SimpleNamespace(
            df_timeseries=sentinel.site_metocean_df,
        )

        self.metocean_port = SimpleNamespace(
            df_timeseries=sentinel.port_metocean_df,
        )

        self.metocean_tow = sentinel.metocean_tow
        self.metocean_tow_distance = sentinel.metocean_tow_distance
        self.timesteps = [sentinel.timestep_1, sentinel.timestep_2]
        self.Config = sentinel.Config

    @patch.object(operations_builder_module, "operation_tow_manager")
    @patch.object(operations_builder_module, "inspect_site_manager")
    @patch.object(operations_builder_module, "operation_inspect_port_manager")
    @patch.object(operations_builder_module, "operation_major_manager")
    @patch.object(operations_builder_module, "opeartion_minor_manager")
    def test_operation_timeseries_builder_calls_all_managers(
        self,
        mock_minor_manager,
        mock_major_manager,
        mock_inspect_port_manager,
        mock_inspect_site_manager,
        mock_tow_manager,
    ):
        """The timeseries builder should call all operation managers with the expected inputs."""
        operations_builder_module.operation_timeseries_builder(
            inputs=self.inputs,
            dirs=self.dirs,
            operations=self.operations,
            metocean=self.metocean,
            metocean_port=self.metocean_port,
            metocean_tow=self.metocean_tow,
            metocean_tow_distance=self.metocean_tow_distance,
            timesteps=self.timesteps,
            Config=self.Config,
        )

        mock_tow_manager.assert_called_once_with(
            operation_dir=self.dirs.operation_dir,
            df_metocean=self.metocean.df_timeseries,
            max_wait=self.inputs.tseries.max_wait["value"],
            operations_tow=self.operations["operations_tow"],
            timesteps=self.timesteps,
            Config=self.Config,
            inputs_tseries=self.inputs.tseries,
            metocean_tow=self.metocean_tow,
            metocean_tow_distance=self.metocean_tow_distance,
        )

        mock_inspect_site_manager.assert_called_once_with(
            operation_dir=self.dirs.operation_dir,
            df_metocean=self.metocean.df_timeseries,
            operations_inspect_site=self.operations["operations_inspect_site"],
            inputs_tseries=self.inputs.tseries,
            Config=self.Config,
        )

        mock_inspect_port_manager.assert_called_once_with(
            operation_dir=self.dirs.operation_dir,
            df_metocean=self.metocean_port.df_timeseries,
            duration_shift=self.inputs.tseries.shift_duration["value"],
            operations_inspect_port=self.operations["operations_inspect_port"],
            inputs_tseries=self.inputs.tseries,
        )

        mock_major_manager.assert_called_once_with(
            operation_dir=self.dirs.operation_dir,
            df_metocean=self.metocean.df_timeseries,
            df_metocean_port=self.metocean_port.df_timeseries,
            operations_corr_major=self.operations["operations_corr_major"],
            inputs_tseries=self.inputs.tseries,
            Config=self.Config,
            timesteps=self.timesteps,
        )

        mock_minor_manager.assert_called_once_with(
            operation_dir=self.dirs.operation_dir,
            df_metocean=self.metocean.df_timeseries,
            operations_corr_minor=self.operations["operations_corr_minor"],
            inputs_tseries=self.inputs.tseries,
            Config=self.Config,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)