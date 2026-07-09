# tests/core/builders/test_user_input_overwrite.py

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, sentinel

import oriom.inputs.user_inputs as user_input_overwrite_module


# ------------------------------------------------------------------
# Test doubles
# ------------------------------------------------------------------

class DummyTseriesInputs:
    """Minimal tseries inputs object used by ST_switcher."""

    def __init__(self):
        self.file_metocean = {"value": "original_metocean.csv"}


class DummyInputs:
    """Minimal inputs object used by run_overwrite and ST_switcher."""

    def __init__(self):
        self.tseries_inputs = DummyTseriesInputs()


class DummyDirs:
    """Minimal dirs object used by ST_switcher."""

    def __init__(self, base_dir):
        self.base_dir = base_dir


class DummyDataObject:
    """Generic object with an id and editable attributes."""

    def __init__(self, id_, **attributes):
        self.id = id_
        for key, value in attributes.items():
            setattr(self, key, value)

    def __str__(self):
        return f"DummyDataObject({self.id})"


class DummyForecast:
    """Forecast test double that avoids calling the real forecast service."""

    def __init__(
        self,
        forecast_client,
        forecast_password,
        name_point,
        addr,
        save_dir,
    ):
        self.forecast_client = forecast_client
        self.forecast_password = forecast_password
        self.name_point = name_point
        self.addr = addr
        self.save_dir = save_dir
        self.timeseries_file = "forecast_timeseries.csv"


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def write_yaml_file(folder, file_name, content):
    """Write a YAML file and return its path."""
    file_path = Path(folder) / file_name
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

class TestReadUserData(unittest.TestCase):
    """Tests for read_user_data."""

    def test_read_user_data_lowercases_keys_and_selected_string_values(self):
        """YAML keys and selected string attributes should be converted to lowercase."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = write_yaml_file(
                tmp_dir,
                "failures_user.yaml",
                """
                - ID: FAIL_001
                  Level: DEVICE
                  Level_Failure: WTG
                  Name: Major Failure
                  Custom_Field: Keep This Case
                  Duration_Net: 12
                """,
            )

            manager = user_input_overwrite_module.user_input_overwrite()
            result = manager.read_user_data(file_path)

        self.assertEqual(
            result,
            {
                "fail_001": {
                    "id": "fail_001",
                    "level": "device",
                    "level_failure": "wtg",
                    "name": "major failure",
                    "custom_field": "Keep This Case",
                    "duration_net": 12,
                }
            },
        )

    def test_read_user_data_returns_empty_dict_for_missing_file(self):
        """Missing user YAML files should be treated as empty overwrite data."""
        manager = user_input_overwrite_module.user_input_overwrite()

        result = manager.read_user_data("missing_file.yaml")

        self.assertEqual(result, {})

    def test_read_user_data_returns_empty_dict_for_empty_yaml(self):
        """Empty YAML files should be treated as empty overwrite data."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = write_yaml_file(tmp_dir, "empty.yaml", "")

            manager = user_input_overwrite_module.user_input_overwrite()
            result = manager.read_user_data(file_path)

        self.assertEqual(result, {})


class TestDataFinderAndOverwrite(unittest.TestCase):
    """Tests for data_finder and overwrite_user_data."""

    def test_data_finder_returns_matching_object(self):
        """data_finder should return the object matching the requested id."""
        objects = [
            DummyDataObject("fail_001", duration_net=1),
            DummyDataObject("fail_002", duration_net=2),
        ]

        manager = user_input_overwrite_module.user_input_overwrite()
        result = manager.data_finder(objects, "fail_002")

        self.assertIs(result, objects[1])

    def test_data_finder_raises_key_error_when_id_is_missing(self):
        """data_finder should raise KeyError when the id is not found."""
        objects = [
            DummyDataObject("fail_001", duration_net=1),
        ]

        manager = user_input_overwrite_module.user_input_overwrite()

        with self.assertRaises(KeyError):
            manager.data_finder(objects, "missing_id")

    def test_overwrite_user_data_updates_existing_attributes(self):
        """overwrite_user_data should update existing attributes only."""
        failures = [
            DummyDataObject(
                "fail_001",
                duration_net=10,
                level="device",
                name="old name",
            )
        ]

        overwrite_data = {
            "FAIL_001": {
                "id": "fail_001",
                "duration_net": 20,
                "level": "component",
                "name": "new name",
            }
        }

        manager = user_input_overwrite_module.user_input_overwrite()
        manager.overwrite_user_data(failures, overwrite_data)

        self.assertEqual(failures[0].duration_net, 20)
        self.assertEqual(failures[0].level, "component")
        self.assertEqual(failures[0].name, "new name")

    def test_overwrite_user_data_raises_key_error_for_missing_attribute(self):
        """overwrite_user_data should raise KeyError if the target attribute does not exist."""
        failures = [
            DummyDataObject(
                "fail_001",
                duration_net=10,
            )
        ]

        overwrite_data = {
            "fail_001": {
                "unknown_attribute": 99,
            }
        }

        manager = user_input_overwrite_module.user_input_overwrite()

        with self.assertRaises(KeyError):
            manager.overwrite_user_data(failures, overwrite_data)

    def test_overwrite_user_data_raises_key_error_for_missing_object(self):
        """overwrite_user_data should raise KeyError if the target id is not found."""
        failures = [
            DummyDataObject(
                "fail_001",
                duration_net=10,
            )
        ]

        overwrite_data = {
            "fail_999": {
                "duration_net": 20,
            }
        }

        manager = user_input_overwrite_module.user_input_overwrite()

        with self.assertRaises(KeyError):
            manager.overwrite_user_data(failures, overwrite_data)

    def test_overwrite_user_data_does_nothing_when_overwrite_dict_is_empty(self):
        """Empty overwrite data should leave the original objects unchanged."""
        failures = [
            DummyDataObject(
                "fail_001",
                duration_net=10,
            )
        ]

        manager = user_input_overwrite_module.user_input_overwrite()
        manager.overwrite_user_data(failures, {})

        self.assertEqual(failures[0].duration_net, 10)


class TestShortTermMode(unittest.TestCase):
    """Tests for ST O&M mode helpers."""

    def test_st_data_object_overwrite_filters_objects_using_user_data_order(self):
        """ST_data_object_overwrite should keep only objects listed in the user data."""
        objects = [
            DummyDataObject("fail_001"),
            DummyDataObject("fail_002"),
            DummyDataObject("fail_003"),
        ]

        user_data = {
            "fail_003": {},
            "fail_001": {},
        }

        manager = user_input_overwrite_module.user_input_overwrite()
        result = manager.ST_data_object_overwrite(objects, user_data)

        self.assertEqual([obj.id for obj in result], ["fail_003", "fail_001"])

    @patch.object(user_input_overwrite_module, "Forecast", DummyForecast)
    @patch.dict(
        os.environ,
        {
            "IPMA_USERNAME": "test_user",
            "IPMA_PASSWORD": "test_password",
        },
        clear=False,
    )
    def test_st_switcher_filters_failures_and_operations_and_updates_metocean_file(self):
        """ST_switcher should filter selected objects and replace the metocean file."""
        inputs = DummyInputs()

        with tempfile.TemporaryDirectory() as tmp_dir:
            dirs = DummyDirs(base_dir=tmp_dir)

            failures = [
                DummyDataObject("fail_001"),
                DummyDataObject("fail_002"),
            ]

            operations = {
                "operations_tow": [
                    DummyDataObject("tow_001"),
                    DummyDataObject("tow_002"),
                ],
                "operations_corr_major": [
                    DummyDataObject("major_001"),
                    DummyDataObject("major_002"),
                ],
            }

            manager = user_input_overwrite_module.user_input_overwrite()
            manager.failure_dict_value = {
                "fail_002": {},
            }
            manager.oper_dict_value = {
                "operations_tow": {
                    "tow_001": {},
                },
                "operations_corr_major": {
                    "major_002": {},
                },
            }

            filtered_failures, filtered_operations = manager.ST_switcher(
                inputs=inputs,
                dirs=dirs,
                failures=failures,
                operations=operations,
            )

        self.assertEqual([failure.id for failure in filtered_failures], ["fail_002"])
        self.assertEqual([op.id for op in filtered_operations["operations_tow"]], ["tow_001"])
        self.assertEqual([op.id for op in filtered_operations["operations_corr_major"]], ["major_002"])
        self.assertEqual(inputs.tseries_inputs.file_metocean["value"], "forecast_timeseries.csv")


class TestRunOverwrite(unittest.TestCase):
    """Tests for run_overwrite."""

    def test_run_overwrite_updates_failures_operations_and_vessels_without_st(self):
        """
        run_overwrite should reproduce the manual workflow:
        - read user YAML files
        - update failures
        - update operation lists
        - update vessels
        - return the modified objects
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            inputs = DummyInputs()
            dirs = DummyDirs(base_dir=tmp_dir)

            failures = [
                DummyDataObject(
                    "fail_001",
                    duration_net=10,
                    level="device",
                    name="old failure",
                ),
                DummyDataObject(
                    "fail_002",
                    duration_net=5,
                    level="device",
                    name="unused failure",
                ),
            ]

            operations = {
                "operations_tow": [
                    DummyDataObject(
                        "tow_001",
                        duration_net=3,
                        vessel1_id="old_vessel",
                        name="old tow",
                    )
                ],
                "operations_inspect_site": [
                    DummyDataObject(
                        "inspection_001",
                        duration_net=4,
                        level="device",
                        name="old inspection",
                    )
                ],
                "operations_corr_major": [
                    DummyDataObject(
                        "major_001",
                        duration_net=20,
                        maintenance_strategy="old_strategy",
                        name="old major",
                    )
                ],
            }

            vessels = [
                DummyDataObject(
                    "vessel_001",
                    fuel_type="diesel",
                    name="old vessel",
                )
            ]

            failure_path = write_yaml_file(
                tmp_dir,
                "failures_user.yaml",
                """
                - id: FAIL_001
                  duration_net: 15
                  level: COMPONENT
                  name: Updated Failure
                """,
            )

            operations_tow_path = write_yaml_file(
                tmp_dir,
                "operations_tow_user.yaml",
                """
                - id: TOW_001
                  duration_net: 6
                  vessel1_id: AHTS_001
                  name: Updated Tow
                """,
            )

            operations_inspect_site_path = write_yaml_file(
                tmp_dir,
                "operations_inspections_site_user.yaml",
                """
                - id: INSPECTION_001
                  duration_net: 7
                  level: HUB
                  name: Updated Inspection
                """,
            )

            operations_corr_major_path = write_yaml_file(
                tmp_dir,
                "operations_corrective_major_user.yaml",
                """
                - id: MAJOR_001
                  duration_net: 25
                  maintenance_strategy: CorrectiveMajor
                  name: Updated Major
                """,
            )

            vessels_path = write_yaml_file(
                tmp_dir,
                "vessels_user.yaml",
                """
                - id: VESSEL_001
                  fuel_type: MGO
                  name: Updated Vessel
                """,
            )

            files_paths = {
                "failure_path": failure_path,
                "operations_path": {
                    "operations_tow": operations_tow_path,
                    "operations_inspect_site": operations_inspect_site_path,
                    "operations_corr_major": operations_corr_major_path,
                },
                "vessels_path": vessels_path,
            }

            result_failures, result_operations, result_vessels = (
                user_input_overwrite_module.user_input_overwrite.run_overwrite(
                    inputs=inputs,
                    dirs=dirs,
                    failures=failures,
                    operations=operations,
                    vessels=vessels,
                    files_paths=files_paths,
                    ST=False,
                )
            )

        self.assertIs(result_failures, failures)
        self.assertIs(result_operations, operations)
        self.assertIs(result_vessels, vessels)

        self.assertEqual(failures[0].duration_net, 15)
        self.assertEqual(failures[0].level, "component")
        self.assertEqual(failures[0].name, "updated failure")

        self.assertEqual(operations["operations_tow"][0].duration_net, 6)
        self.assertEqual(operations["operations_tow"][0].vessel1_id, "ahts_001")
        self.assertEqual(operations["operations_tow"][0].name, "updated tow")

        self.assertEqual(operations["operations_inspect_site"][0].duration_net, 7)
        self.assertEqual(operations["operations_inspect_site"][0].level, "hub")
        self.assertEqual(operations["operations_inspect_site"][0].name, "updated inspection")

        self.assertEqual(operations["operations_corr_major"][0].duration_net, 25)
        self.assertEqual(operations["operations_corr_major"][0].maintenance_strategy, "correctivemajor")
        self.assertEqual(operations["operations_corr_major"][0].name, "updated major")

        self.assertEqual(vessels[0].fuel_type, "mgo")
        self.assertEqual(vessels[0].name, "updated vessel")

    @patch.object(user_input_overwrite_module, "Forecast", DummyForecast)
    def test_run_overwrite_with_st_filters_objects_and_updates_forecast_file(self):
        """
        run_overwrite with ST=True should:
        - update objects from user YAML
        - keep only user-defined failures and operations
        - update the metocean file using Forecast
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            inputs = DummyInputs()
            dirs = DummyDirs(base_dir=tmp_dir)

            failures = [
                DummyDataObject("fail_001", duration_net=10),
                DummyDataObject("fail_002", duration_net=20),
            ]

            operations = {
                "operations_tow": [
                    DummyDataObject("tow_001", duration_net=3),
                    DummyDataObject("tow_002", duration_net=4),
                ],
                "operations_inspect_site": [
                    DummyDataObject("inspection_001", duration_net=5),
                ],
                "operations_corr_major": [
                    DummyDataObject("major_001", duration_net=8),
                    DummyDataObject("major_002", duration_net=9),
                ],
            }

            vessels = [
                DummyDataObject("vessel_001", fuel_type="diesel"),
            ]

            failure_path = write_yaml_file(
                tmp_dir,
                "failures_user.yaml",
                """
                - id: FAIL_002
                  duration_net: 30
                """,
            )

            operations_tow_path = write_yaml_file(
                tmp_dir,
                "operations_tow_user.yaml",
                """
                - id: TOW_002
                  duration_net: 11
                """,
            )

            operations_corr_major_path = write_yaml_file(
                tmp_dir,
                "operations_corrective_major_user.yaml",
                """
                - id: MAJOR_001
                  duration_net: 12
                """,
            )

            vessels_path = write_yaml_file(
                tmp_dir,
                "vessels_user.yaml",
                """
                - id: VESSEL_001
                  fuel_type: MGO
                """,
            )

            missing_inspection_path = str(Path(tmp_dir) / "missing_inspection_user.yaml")

            files_paths = {
                "failure_path": failure_path,
                "operations_path": {
                    "operations_tow": operations_tow_path,
                    "operations_inspect_site": missing_inspection_path,
                    "operations_corr_major": operations_corr_major_path,
                },
                "vessels_path": vessels_path,
            }

            result_failures, result_operations, result_vessels = (
                user_input_overwrite_module.user_input_overwrite.run_overwrite(
                    inputs=inputs,
                    dirs=dirs,
                    failures=failures,
                    operations=operations,
                    vessels=vessels,
                    files_paths=files_paths,
                    ST=True,
                )
            )

        self.assertEqual([failure.id for failure in result_failures], ["fail_002"])
        self.assertEqual(result_failures[0].duration_net, 30)

        self.assertEqual([op.id for op in result_operations["operations_tow"]], ["tow_002"])
        self.assertEqual(result_operations["operations_tow"][0].duration_net, 11)

        self.assertEqual([op.id for op in result_operations["operations_corr_major"]], ["major_001"])
        self.assertEqual(result_operations["operations_corr_major"][0].duration_net, 12)

        self.assertEqual(result_operations["operations_inspect_site"], [])

        self.assertEqual(result_vessels[0].fuel_type, "mgo")
        self.assertEqual(inputs.tseries_inputs.file_metocean["value"], "forecast_timeseries.csv")

    def test_run_overwrite_raises_key_error_for_missing_operation_user_path_key(self):
        """run_overwrite should raise KeyError when an operation type has no user file path entry."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            inputs = DummyInputs()
            dirs = DummyDirs(base_dir=tmp_dir)

            failures = []
            operations = {
                "operations_tow": [],
                "operations_corr_major": [],
            }
            vessels = []

            empty_failure_path = write_yaml_file(tmp_dir, "failures_user.yaml", "")
            empty_vessels_path = write_yaml_file(tmp_dir, "vessels_user.yaml", "")

            files_paths = {
                "failure_path": empty_failure_path,
                "operations_path": {
                    "operations_tow": write_yaml_file(tmp_dir, "operations_tow_user.yaml", ""),
                },
                "vessels_path": empty_vessels_path,
            }

            with self.assertRaises(KeyError):
                user_input_overwrite_module.user_input_overwrite.run_overwrite(
                    inputs=inputs,
                    dirs=dirs,
                    failures=failures,
                    operations=operations,
                    vessels=vessels,
                    files_paths=files_paths,
                    ST=False,
                )


class TestManualMainWorkflow(unittest.TestCase):
    """Tests reproducing the original manual workflow using temporary user YAML files."""

    @patch.object(user_input_overwrite_module, "Forecast", DummyForecast)
    def test_manual_main_workflow_with_temporary_user_yaml_files(self):
        """
        This test reproduces the original manual workflow implemented after
        if __name__ == "__main__", but creates the user YAML files in a
        temporary directory instead of reading them from a fixed local folder.

        Expected printed output:
        - Failure fail_rate is overwritten from 0.00576436 to 1
        - CorrectiveMajor name is overwritten from Cable Disconnection to cable disconnection
        - CorrectiveMajor tech_cost is overwritten from 300.0 to 10000
        - ST mode keeps only the user-defined failure and corrective major operation
        """
        import io
        from contextlib import redirect_stdout

        class ManualWorkflowObject:
            """Generic object used to reproduce the original manual workflow."""

            def __init__(self, id_, object_name, **attributes):
                self.id = id_
                self.object_name = object_name

                for key, value in attributes.items():
                    setattr(self, key, value)

            def __str__(self):
                return self.object_name

        with tempfile.TemporaryDirectory() as tmp_dir:
            inputs = DummyInputs()
            dirs = DummyDirs(base_dir=tmp_dir)

            failures = [
                ManualWorkflowObject(
                    id_="ofw_cb_dyn_fail",
                    object_name="Failure",
                    name="Dynamic cable",
                    n_element=25,
                    fail_rate=0.00576436,
                    maintenance_strategy="immediately",
                    level_failure="dyn_cable-sub",
                    operation_triggered="ofw_op002",
                    bath_tub=False,
                    fail_variation=False,
                    potential_shutdown=True,
                    perc_shutdown=100,
                ),
                ManualWorkflowObject(
                    id_="ofw_other_fail",
                    object_name="Failure",
                    name="Other failure",
                    n_element=1,
                    fail_rate=0.2,
                    maintenance_strategy="immediately",
                    level_failure="device",
                    operation_triggered="ofw_op999",
                    bath_tub=False,
                    fail_variation=False,
                    potential_shutdown=True,
                    perc_shutdown=100,
                ),
            ]

            operations = {
                "operations_tow": [
                    ManualWorkflowObject(
                        id_="ofw_tow001",
                        object_name="OperationTow",
                        name="Tow operation",
                        duration_net=10,
                    )
                ],
                "operations_inspect_site": [
                    ManualWorkflowObject(
                        id_="ofw_insp001",
                        object_name="InspectionSite",
                        name="Inspection site",
                        duration_net=5,
                    )
                ],
                "operations_corr_major": [
                    ManualWorkflowObject(
                        id_="ofw_mj1",
                        object_name="CorrectiveMajor",
                        name="Cable Disconnection",
                        tow_to_port=False,
                        tech_required=18,
                        tech_cost=300.0,
                        vessel1_id="v004",
                        vessel1_qt=1,
                        rov_drone="eva_rov_2",
                    ),
                    ManualWorkflowObject(
                        id_="ofw_mj2",
                        object_name="CorrectiveMajor",
                        name="Other major operation",
                        tow_to_port=False,
                        tech_required=10,
                        tech_cost=500.0,
                        vessel1_id="v004",
                        vessel1_qt=1,
                        rov_drone="eva_rov_2",
                    ),
                ],
            }

            vessels = [
                ManualWorkflowObject(
                    id_="vessel_001",
                    object_name="Vessel",
                    name="Vessel 001",
                    fuel_type="diesel",
                ),
                ManualWorkflowObject(
                    id_="vessel_002",
                    object_name="Vessel",
                    name="Vessel 002",
                    fuel_type="diesel",
                ),
            ]

            failure_path = write_yaml_file(
                tmp_dir,
                "failures_user.yaml",
                """
                - id: ofw_cb_dyn_fail
                  name: Dynamic cable
                  n_element: 25
                  fail_rate: 1
                  maintenance_strategy: Immediately
                  level_failure: dyn_cable-sub
                  operation_triggered: ofw_op002
                  bath_tub: false
                  fail_variation: false
                  potential_shutdown: true
                  perc_shutdown: 100
                """,
            )

            operations_corr_major_path = write_yaml_file(
                tmp_dir,
                "operations_corrective_major_user.yaml",
                """
                - id: ofw_MJ1
                  name: Cable Disconnection
                  tow_to_port: false
                  tech_required: 18
                  tech_cost: 10000
                  vessel1_id: V004
                  vessel1_qt: 1
                  rov_drone: EVA_ROV_2
                """,
            )

            operations_tow_path = write_yaml_file(
                tmp_dir,
                "operations_tow_user.yaml",
                """
                []
                """,
            )

            operations_inspect_site_path = write_yaml_file(
                tmp_dir,
                "operations_inspections_site_user.yaml",
                """
                []
                """,
            )

            vessels_path = write_yaml_file(
                tmp_dir,
                "vessels_user.yaml",
                """
                []
                """,
            )

            files_paths = {
                "failure_path": failure_path,
                "operations_path": {
                    "operations_corr_major": operations_corr_major_path,
                    "operations_tow": operations_tow_path,
                    "operations_inspect_site": operations_inspect_site_path,
                },
                "vessels_path": vessels_path,
            }

            stdout_buffer = io.StringIO()

            with redirect_stdout(stdout_buffer):
                result_failures, result_operations, result_vessels = (
                    user_input_overwrite_module.user_input_overwrite.run_overwrite(
                        inputs=inputs,
                        dirs=dirs,
                        failures=failures,
                        operations=operations,
                        vessels=vessels,
                        files_paths=files_paths,
                        ST=True,
                    )
                )

        self.assertEqual(
            [failure.id for failure in result_failures],
            ["ofw_cb_dyn_fail"],
        )

        selected_failure = result_failures[0]

        self.assertEqual(selected_failure.fail_rate, 1)
        self.assertEqual(selected_failure.name, "dynamic cable")
        self.assertEqual(selected_failure.maintenance_strategy, "immediately")
        self.assertEqual(selected_failure.level_failure, "dyn_cable-sub")
        self.assertEqual(selected_failure.operation_triggered, "ofw_op002")

        self.assertEqual(result_operations["operations_tow"], [])
        self.assertEqual(result_operations["operations_inspect_site"], [])

        self.assertEqual(
            [operation.id for operation in result_operations["operations_corr_major"]],
            ["ofw_mj1"],
        )

        selected_major_operation = result_operations["operations_corr_major"][0]

        self.assertEqual(selected_major_operation.name, "cable disconnection")
        self.assertEqual(selected_major_operation.tech_cost, 10000)

        self.assertIs(result_vessels, vessels)

        self.assertEqual(
            inputs.tseries_inputs.file_metocean["value"],
            "forecast_timeseries.csv",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)