# tests/inputs/test_user_inputs.py

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ruamel.yaml import YAML

import pandas as pd

from oriom.core.functions.private import user_inputs as user_inputs_module


class DummyObject:
    """Minimal mutable domain object with a stable identifier."""

    def __init__(self, object_id, **attributes):
        self.id = object_id
        for name, value in attributes.items():
            setattr(self, name, value)

    def __str__(self):
        return f"DummyObject({self.id})"


class DummyInputs:
    """Minimal inputs hierarchy modified by the short-term workflow."""

    def __init__(self, port_metocean="original_port.csv"):
        self.tseries = SimpleNamespace(
            file_metocean={"value": "original_site.csv"},
            file_metocean_port={"value": port_metocean},
            file_metocean_tow_number={"value": 3},
            ST_O_M=False,
        )
        self.stats = SimpleNamespace(
            period_infant_mortality={"value": 3},
            period_wear_out={"value": 5},
            start_year={"value": 2020},
            lifetime={"value": 20},
        )
        self.general = SimpleNamespace(
            powerevent_file={"value": "power.csv"},
            logevents_file={"value": "logs.csv"},
            failureevent_file={"value": "old_failures.csv"},
        )
        self.cost = SimpleNamespace(
            port_cost_year={"value": 1000},
            insurance_cost_year={"value": 2000},
            technicians_year={"value": 3000},
            fuel_cost_mgo={"value": 1.5},
        )


class DummyForecastManager:
    """Deterministic replacement for the external forecast service."""

    calls = []

    def __init__(self, forecast_user_data, save_dir):
        type(self).calls.append((forecast_user_data, save_dir))
        self.timeseries_file = "forecast_timeseries.csv"
        self.forecast_df = pd.DataFrame(
            {"Hs": [1.2, 1.3]},
            index=pd.to_datetime(["2027-04-15 00:00", "2027-04-15 01:00"]),
        )


def make_failure(object_id, operation_triggered, **overrides):
    """Create a representative failure used by short-term processing."""
    attributes = dict(
        operation_triggered=operation_triggered,
        name="Original failure",
        fail_rate=0.01,
        lead_time=24,
        maintenance_strategy="specific month",
        fail_variation=True,
        bath_tub=True,
    )
    attributes.update(overrides)
    return DummyObject(object_id, **attributes)


def make_operation(object_id, *, tow_to_port=False, failures=None, **attributes):
    """Create an operation with optional TTP references and failure links."""
    values = dict(tow_to_port=tow_to_port, failures=failures or [])
    values.update(attributes)
    return DummyObject(object_id, **values)


def make_vessel(object_id="vessel_001"):
    """Create a vessel with attributes modified and preserved in ST mode."""
    return DummyObject(
        object_id,
        mobilisation_time=12,
        mobilisation_cost=5000,
        n_ves_annual_contract=2,
        n_ves_monthly_contract=1,
        fuel_type="diesel",
    )


def write_yaml(folder, name, contents):
    """Write valid YAML fixtures, avoiding indentation errors in multiline strings."""
    path = Path(folder) / name
    if isinstance(contents, str):
        path.write_text(contents, encoding="utf-8")
    else:
        with path.open("w", encoding="utf-8") as stream:
            YAML(typ="safe").dump(contents, stream)
    return str(path)


def make_ttp_operations(selected_failure):
    """Build a TTP operation plus tow, optional port, additional and unrelated operations."""
    additional_port = make_operation("ofw_add_port")
    additional_site = make_operation("ofw_add_site")
    additional_site_port = make_operation("ofw_add_site_port")
    tow_port = make_operation("ofw_tow_port", addition_op_tow=additional_port)
    tow_site = make_operation("ofw_tow_site", addition_op_tow=additional_site)
    tow_site_port = make_operation("ofw_tow_site_port", addition_op_tow=additional_site_port)
    primary = make_operation(
        "ofw_main",
        tow_to_port=True,
        op_tow_port=tow_port.id,
        op_tow_site=tow_site.id,
        op_tow_site_port=tow_site_port.id,
        failures=[selected_failure],
    )
    unrelated = make_operation("ofw_unused")
    operations = {
        "operations_corr_major": [primary, unrelated],
        "operations_tow": [tow_port, tow_site, tow_site_port, unrelated],
        "operations_additional": [additional_port, additional_site, additional_site_port],
        "total_operations": [
            primary, tow_port, tow_site, tow_site_port,
            additional_port, additional_site, additional_site_port, unrelated,
        ],
    }
    return operations


class TestReadUserData(unittest.TestCase):
    """Verify actual YAML parsing, normalisation and fallback behaviour."""

    def setUp(self):
        self.manager = user_inputs_module.user_input_overwrite()

    def test_normalises_ids_fields_and_selected_values(self):
        """Only failure YAML entries are normalised when fail=True."""
        with tempfile.TemporaryDirectory() as tmp:
            path = write_yaml(tmp, "failures.yaml", [
                {
                    "ID": "FAIL_001",
                    "Level": "DEVICE",
                    "Name": "Major Failure",
                    "Maintenance_Strategy": "IMMEDIATELY",
                    "Operation_Triggered": "OFW_MAIN",
                    "Extra_Comment": "Keep Uppercase",
                    "Fail_Rate": 0.25,
                },
                {"ID": "FAIL_002", "Name": "Another Failure"},
            ])
            data = self.manager.read_user_data(path, fail=True)

        self.assertEqual(set(data), {"fail_001", "fail_002"})
        self.assertEqual(data["fail_001"]["id"], "fail_001")
        self.assertEqual(data["fail_001"]["level"], "device")
        self.assertEqual(data["fail_001"]["name"], "major failure")
        self.assertEqual(data["fail_001"]["maintenance_strategy"], "immediately")
        self.assertEqual(data["fail_001"]["operation_triggered"], "ofw_main")
        self.assertEqual(data["fail_001"]["extra_comment"], "Keep Uppercase")
        self.assertEqual(data["fail_001"]["fail_rate"], 0.25)
        self.assertEqual(data["fail_002"]["name"], "another failure")

    def test_vessel_yaml_without_fail_flag_keeps_string_case(self):
        """Vessel overrides must not receive failure-only normalisation."""
        with tempfile.TemporaryDirectory() as tmp:
            path = write_yaml(tmp, "vessels.yaml", [
                {"id": "vessel_001", "fuel_type": "MGO", "name": "Supply Vessel"},
            ])
            data = self.manager.read_user_data(path)

        self.assertEqual(data, {
            "vessel_001": {
                "id": "vessel_001",
                "fuel_type": "MGO",
                "name": "Supply Vessel",
            },
        })

    def test_forecast_yaml_without_id_returns_plain_dictionary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_yaml(tmp, "forecast.yaml", """
- type_forecast: IPMA
  name_point: AB
""")
            data = self.manager.read_user_data(path)
        self.assertEqual(data, {"type_forecast": "IPMA", "name_point": "AB"})

    def test_ttp_flags_yaml_preserves_original_flag_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_yaml(tmp, "ttp.yaml", """
- TTP: true
  additional: true
""")
            data = self.manager.read_user_data(path)
        self.assertEqual(data, {"TTP": True, "additional": True})

    def test_missing_file_returns_empty_dictionary(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = self.manager.read_user_data(str(Path(tmp) / "missing.yaml"))
        self.assertEqual(data, {})

    def test_empty_yaml_and_empty_list_return_empty_dictionary(self):
        with tempfile.TemporaryDirectory() as tmp:
            for filename, content in (("empty.yaml", ""), ("list.yaml", "[]")):
                with self.subTest(filename=filename):
                    path = write_yaml(tmp, filename, content)
                    self.assertEqual(self.manager.read_user_data(path), {})


class TestDataFinderAndOverwrite(unittest.TestCase):
    """Verify record lookup and allowed user overrides."""

    def setUp(self):
        self.manager = user_inputs_module.user_input_overwrite()

    def test_data_finder_returns_matching_object_identity(self):
        objects = [DummyObject("fail_001"), DummyObject("fail_002")]
        self.assertIs(self.manager.data_finder(objects, "fail_002"), objects[1])

    def test_data_finder_raises_key_error_if_not_found(self):
        with self.assertRaisesRegex(KeyError, "not found"):
            self.manager.data_finder([DummyObject("fail_001")], "missing")

    def test_overwrite_updates_existing_fields_and_normalises_lookup_id(self):
        failure = make_failure("fail_001", "ofw_original")
        self.manager.overwrite_user_data(
            [failure],
            {"FAIL_001": {"id": "fail_001", "fail_rate": 0.4, "name": "new name"}},
        )
        self.assertEqual(failure.fail_rate, 0.4)
        self.assertEqual(failure.name, "new name")

    def test_overwrite_with_empty_dictionary_does_not_change_objects(self):
        failure = make_failure("fail_001", "ofw_main")
        self.manager.overwrite_user_data([failure], {})
        self.assertEqual(failure.fail_rate, 0.01)

    def test_overwrite_missing_object_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.manager.overwrite_user_data(
            [make_failure("fail_001", "ofw_main")],
            {"fail_999": {"fail_rate": 0.5}},
        )


class TestFilteringOperations(unittest.TestCase):
    """Check failure-driven operation selection, including all TTP dependencies."""

    def test_regular_operation_filters_out_unrelated_operations(self):
        failure = make_failure("fail_001", "ofw_repair")
        selected = make_operation("ofw_repair")
        unused = make_operation("ofw_unused")
        operations = {
            "operations_corr_major": [selected, unused],
            "total_operations": [selected, unused],
        }
        manager = user_inputs_module.user_input_overwrite()
        identifiers = manager.filter_id_list_useful_operation([failure], operations)
        self.assertEqual(identifiers, {"ofw_repair"})
        self.assertEqual([op.id for op in operations["total_operations"]], ["ofw_repair"])
        self.assertIs(manager.operations_by_id["ofw_repair"], selected)

    def test_ttp_includes_tow_port_site_site_port_and_additional_operations(self):
        failure = make_failure("fail_001", "ofw_main")
        operations = make_ttp_operations(failure)
        manager = user_inputs_module.user_input_overwrite()
        identifiers = manager.filter_id_list_useful_operation([failure], operations)
        expected = {
            "ofw_main", "ofw_tow_port", "ofw_tow_site", "ofw_tow_site_port",
            "ofw_add_port", "ofw_add_site", "ofw_add_site_port",
        }
        self.assertEqual(identifiers, expected)
        self.assertEqual({op.id for op in operations["total_operations"]}, expected)
        self.assertNotIn("ofw_unused", identifiers)

    def test_unknown_operation_triggered_raises_key_error(self):
        manager = user_inputs_module.user_input_overwrite()
        operations = {"total_operations": [make_operation("other")], "operations_corr_major": []}
        failure = make_failure("fail_001", "missing_operation")
        with self.assertRaises(KeyError):
            manager.filter_id_list_useful_operation([failure], operations)


class TestShortTermSwitcher(unittest.TestCase):
    """Check the ST selection flow separately from the classmethod entry point."""

    def setUp(self):
        DummyForecastManager.calls.clear()
        self.manager = user_inputs_module.user_input_overwrite()
        self.inputs = DummyInputs()

    @patch.object(user_inputs_module, "Forecast_manager", DummyForecastManager)
    def test_switcher_filters_failures_and_operations_and_changes_inputs(self):
        chosen = make_failure("fail_002", "ofw_repair")
        unselected = make_failure("fail_001", "ofw_other")
        selected_op = make_operation("ofw_repair", failures=[chosen])
        other_op = make_operation("ofw_other", failures=[unselected])
        operations = {
            "operations_corr_major": [selected_op, other_op],
            "total_operations": [selected_op, other_op],
        }
        self.manager.failure_dict_value = {"fail_002": {}}
        with tempfile.TemporaryDirectory() as tmp:
            failures_out, operations_out = self.manager.ST_switcher(
                inputs=self.inputs,
                dirs=SimpleNamespace(run_dir=tmp),
                failures=[unselected, chosen],
                operations=operations,
                forecast_file={"type_forecast": "IPMA", "name_point": "AB"},
            )
            self.assertEqual(DummyForecastManager.calls, [({"type_forecast": "IPMA", "name_point": "AB"}, tmp)])
            self.assertEqual(self.inputs.general.failureevent_file["value"], tmp)
        self.assertEqual([fail.id for fail in failures_out], ["fail_002"])
        self.assertEqual([op.id for op in operations_out["operations_corr_major"]], ["ofw_repair"])
        self.assertEqual([op.id for op in operations_out["total_operations"]], ["ofw_repair"])
        self.assertEqual(chosen.maintenance_strategy, "specific month")
        self.assertTrue(self.inputs.tseries.ST_O_M)
        self.assertEqual(self.inputs.tseries.file_metocean["value"], "forecast_timeseries.csv")
        self.assertEqual(self.inputs.stats.start_year["value"], 2027)

    @patch.object(user_inputs_module, "Forecast_manager", DummyForecastManager)
    def test_switcher_raises_when_no_operations_are_selected(self):
        failure = make_failure("fail_001", "ofw_missing")
        self.manager.failure_dict_value = {}  # No user-selected failures.
        operations = {"operations_corr_major": [], "total_operations": []}
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "No operations are defined"):
                self.manager.ST_switcher(
                self.inputs, SimpleNamespace(run_dir=tmp), [failure],
                operations, forecast_file={"type_forecast": "IPMA"},
            )
        self.assertEqual(DummyForecastManager.calls, [])

    @patch.object(user_inputs_module, "Forecast_manager", DummyForecastManager)
    def test_ttp_authorisation_uses_site_when_ttp_flag_is_true(self):
        failure = make_failure("fail_001", "ofw_main")
        operations = make_ttp_operations(failure)
        self.manager.failure_dict_value = {"fail_001": {}}
        self.manager.oper_TTP_dict_value = {"TTP": True, "additional": True}
        with tempfile.TemporaryDirectory() as tmp:
            failures_out, operations_out = self.manager.ST_switcher(
                self.inputs, SimpleNamespace(run_dir=tmp), [failure], operations,
                forecast_file={"type_forecast": "IPMA"},
            )
        self.assertEqual(self.manager.list_op_TTP, ["TTP", "additional"])
        self.assertEqual(self.manager.op_authorized_ST_TTP, ["ofw_add_port"])
        self.assertEqual({op.id for op in operations_out["total_operations"]}, {
            "ofw_main", "ofw_tow_port", "ofw_tow_site", "ofw_tow_site_port",
            "ofw_add_port", "ofw_add_site", "ofw_add_site_port",
        })
        self.assertEqual(failures_out[0].maintenance_strategy, "immediately")

    @patch.object(user_inputs_module, "Forecast_manager", DummyForecastManager)
    def test_ttp_authorisation_is_empty_when_ttp_flag_is_false(self):
        failure = make_failure("fail_001", "ofw_main")
        operations = make_ttp_operations(failure)
        self.manager.failure_dict_value = {"fail_001": {}}
        self.manager.oper_TTP_dict_value = {"TTP": False, "additional": False}
        with tempfile.TemporaryDirectory() as tmp:
            self.manager.ST_switcher(
                self.inputs, SimpleNamespace(run_dir=tmp), [failure], operations,
                forecast_file={"type_forecast": "IPMA"},
            )
        self.assertEqual(self.manager.list_op_TTP, [])
        self.assertEqual(self.manager.op_authorized_ST_TTP, [])

    @patch.object(user_inputs_module, "Forecast_manager", DummyForecastManager)
    def test_tts_authorisation_selects_site_tow(self):
        """TTS flag selects site tow, not port tow."""
        failure = make_failure("fail_001", "ofw_main")
        operations = make_ttp_operations(failure)
        self.manager.failure_dict_value = {"fail_001": {}}
        self.manager.oper_TTP_dict_value = {"TTS": True, "additional": False}
        with tempfile.TemporaryDirectory() as tmp:
            self.manager.ST_switcher(
                self.inputs, SimpleNamespace(run_dir=tmp), [failure], operations,
                forecast_file={"type_forecast": "IPMA"},
            )
        self.assertEqual(self.manager.op_authorized_ST_TTP, ["ofw_tow_site"])

    @patch.object(user_inputs_module, "Forecast_manager", DummyForecastManager)
    def test_tts_authorisation_selects_additional_site_operation(self):
        """Additional TTS selection authorises the additional site operation."""
        failure = make_failure("fail_001", "ofw_main")
        operations = make_ttp_operations(failure)
        self.manager.failure_dict_value = {"fail_001": {}}
        self.manager.oper_TTP_dict_value = {"TTS": True, "additional": True}
        with tempfile.TemporaryDirectory() as tmp:
            self.manager.ST_switcher(
                self.inputs, SimpleNamespace(run_dir=tmp), [failure], operations,
                forecast_file={"type_forecast": "IPMA"},
            )
        self.assertEqual(self.manager.op_authorized_ST_TTP, ["ofw_add_site"])

    @patch.object(user_inputs_module, "Forecast_manager", DummyForecastManager)
    def test_switcher_rebinds_both_vessel_slots_to_prepared_vessels(self):
        """ST switches operation vessel references to updated vessel instances."""
        failure = make_failure("fail_001", "ofw_repair")
        op = make_operation(
            "ofw_repair", failures=[failure],
            vessel1_id="vessel_001", vessel2_id="vessel_002",
            vessel1=object(), vessel2=object(),
        )
        operations = {
            "operations_corr_major": [op],
            "total_operations": [op],
        }
        first, second = make_vessel("vessel_001"), make_vessel("vessel_002")
        config = SimpleNamespace(TIME_FAIL_OP_IMMEDIATELY=3, STATISTICAL_CHART=True)
        self.manager.prepare_object_ST(config, self.inputs, [first, second])
        self.manager.failure_dict_value = {"fail_001": {}}
        with tempfile.TemporaryDirectory() as tmp:
            self.manager.ST_switcher(
                self.inputs, SimpleNamespace(run_dir=tmp), [failure], operations,
                forecast_file={"type_forecast": "IPMA"},
            )
        self.assertIs(op.vessel1, first)
        self.assertIs(op.vessel2, second)
        self.assertEqual(op.vessel1.mobilisation_cost, 0)
        self.assertEqual(op.vessel2.mobilisation_time, 0)

    @patch.object(user_inputs_module, "Forecast_manager", DummyForecastManager)
    def test_switcher_raises_if_operation_vessel_id_is_unknown(self):
        """A dangling vessel reference must not be silently accepted."""
        failure = make_failure("fail_001", "ofw_repair")
        op = make_operation("ofw_repair", failures=[failure], vessel1_id="missing_vessel")
        operations = {"operations_corr_major": [op], "total_operations": [op]}
        self.manager.failure_dict_value = {"fail_001": {}}
        self.manager.prepare_object_ST(
            SimpleNamespace(TIME_FAIL_OP_IMMEDIATELY=5, STATISTICAL_CHART=True),
            self.inputs, [make_vessel()],
        )
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(KeyError):
                self.manager.ST_switcher(
                    self.inputs, SimpleNamespace(run_dir=tmp), [failure], operations,
                    forecast_file={"type_forecast": "IPMA"},
                )
        self.assertEqual(DummyForecastManager.calls, [])

    def test_st_data_object_overwrite_keeps_user_order(self):
        objects = [DummyObject("fail_001"), DummyObject("fail_002"), DummyObject("fail_003")]
        selected = self.manager.ST_data_object_overwrite(
            objects, {"fail_003": {}, "fail_001": {}, "absent": {}},
        )
        self.assertEqual([obj.id for obj in selected], ["fail_003", "fail_001"])


class TestPrepareAndMetoceanST(unittest.TestCase):
    """Verify the additional ST preparation and conditional metocean updates."""

    def test_prepare_object_st_resets_config_vessels_failures_and_costs(self):
        """ST preparation resets costs and builds the vessel lookup."""
        config = SimpleNamespace(TIME_FAIL_OP_IMMEDIATELY=12, STATISTICAL_CHART=True)
        inputs = DummyInputs()
        vessel = make_vessel("VESSEL_001")
        manager = user_inputs_module.user_input_overwrite()

        manager.prepare_object_ST(Config=config, inputs=inputs, vessels=[vessel])

        self.assertEqual(config.TIME_FAIL_OP_IMMEDIATELY, 0)
        self.assertFalse(config.STATISTICAL_CHART)
        self.assertIs(manager.vessels_finder["vessel_001"], vessel)
        for attr in (
            "mobilisation_time", "mobilisation_cost",
            "n_ves_annual_contract", "n_ves_monthly_contract",
        ):
            self.assertEqual(getattr(vessel, attr), 0, attr)
        self.assertEqual(vessel.fuel_type, "diesel")
        self.assertEqual(inputs.cost.port_cost_year["value"], 0)
        self.assertEqual(inputs.cost.insurance_cost_year["value"], 0)
        self.assertEqual(inputs.cost.technicians_year["value"], 0)
        self.assertEqual(inputs.cost.fuel_cost_mgo["value"], 1.5)

    def test_overwrite_metocean_location_resets_period_and_input_paths(self):
        inputs = DummyInputs()
        user_inputs_module.user_input_overwrite().overwrite_metocean_location(
            inputs=inputs,
            metocean_file_path_new="new_forecast.csv",
            forecast_min_idx=pd.Timestamp("2028-03-01 12:00"),
            dirs_run="/some/run",
        )
        self.assertEqual(inputs.tseries.file_metocean["value"], "new_forecast.csv")
        self.assertEqual(inputs.tseries.file_metocean_port["value"], "new_forecast.csv")
        self.assertEqual(inputs.tseries.file_metocean_tow_number["value"], 0)
        self.assertEqual(inputs.stats.start_year["value"], 2028)
        self.assertEqual(inputs.stats.lifetime["value"], 1)
        self.assertEqual(inputs.stats.period_infant_mortality["value"], 0)
        self.assertEqual(inputs.stats.period_wear_out["value"], 0)
        self.assertIsNone(inputs.general.powerevent_file["value"])
        self.assertIsNone(inputs.general.logevents_file["value"])
        self.assertEqual(inputs.general.failureevent_file, {"value": "/some/run"})

    def test_overwrite_metocean_location_preserves_missing_port_series(self):
        inputs = DummyInputs(port_metocean=None)
        user_inputs_module.user_input_overwrite().overwrite_metocean_location(
            inputs=inputs,
            metocean_file_path_new="forecast.csv",
            forecast_min_idx=pd.Timestamp("2027-04-15"),
            dirs_run="/run",
        )
        self.assertIsNone(inputs.tseries.file_metocean_port["value"])
        self.assertEqual(inputs.tseries.file_metocean["value"], "forecast.csv")


class TestRunOverwrite(unittest.TestCase):
    """End-to-end orchestration tests using real YAML files and a mocked forecast."""

    def setUp(self):
        DummyForecastManager.calls.clear()

    @patch.object(user_inputs_module, "Forecast_manager", DummyForecastManager)
    def test_run_overwrite_returns_four_values_and_applies_reduced_st_workflow(self):
        """Integration path with real YAML files and a deterministic forecast."""
        config = SimpleNamespace(TIME_FAIL_OP_IMMEDIATELY=6, STATISTICAL_CHART=True)
        inputs = DummyInputs()
        selected_failure = make_failure("fail_001", "ofw_main")
        unused_failure = make_failure("fail_002", "ofw_unused")
        operations = make_ttp_operations(selected_failure)
        vessels = [make_vessel()]

        with tempfile.TemporaryDirectory() as tmp:
            files_paths = {
                "failure_path": write_yaml(tmp, "failure.yaml", [
                    {
                        "id": "FAIL_001",
                        "name": "Updated Failure",
                        "fail_rate": 0.25,
                        "operation_triggered": "OFW_MAIN",
                    },
                ]),
                "TTP_op_path": write_yaml(tmp, "ttp.yaml", [
                    {"TTP": True, "additional": True},
                ]),
                "forecast_path": write_yaml(tmp, "forecast.yaml", [
                    {"type_forecast": "IPMA", "name_point": "AB"},
                ]),
                "operations_path": {
                    "operations_corr_major": write_yaml(tmp, "ignored_operations.yaml", [
                        {"id": "ofw_main", "name": "SHOULD NOT BE APPLIED"},
                    ]),
                },
                "vessels_path": write_yaml(tmp, "vessels.yaml", [
                    {"id": "vessel_001", "fuel_type": "MGO"},
                ]),
            }
            failures_out, operations_out, vessels_out, manager = (
                user_inputs_module.user_input_overwrite.run_overwrite(
                    Config=config,
                    inputs=inputs,
                    dirs=SimpleNamespace(run_dir=tmp),
                    failures=[selected_failure, unused_failure],
                    operations=operations,
                    vessels=vessels,
                    files_paths=files_paths,
                )
            )
            self.assertEqual(DummyForecastManager.calls, [
                ({"type_forecast": "IPMA", "name_point": "AB"}, tmp),
            ])
            self.assertEqual(inputs.general.failureevent_file["value"], tmp)

        self.assertIsInstance(manager, user_inputs_module.user_input_overwrite)
        self.assertEqual([failure.id for failure in failures_out], ["fail_001"])
        self.assertIs(failures_out[0], selected_failure)
        self.assertEqual(selected_failure.name, "updated failure")
        self.assertEqual(selected_failure.fail_rate, 1)
        self.assertEqual(selected_failure.operation_triggered, "ofw_main")
        self.assertEqual(selected_failure.lead_time, 0)
        self.assertFalse(selected_failure.fail_variation)
        self.assertFalse(selected_failure.bath_tub)
        self.assertEqual(selected_failure.maintenance_strategy, "immediately")
        self.assertEqual({op.id for op in operations_out["total_operations"]}, {
            "ofw_main", "ofw_tow_port", "ofw_tow_site", "ofw_tow_site_port",
            "ofw_add_port", "ofw_add_site", "ofw_add_site_port",
        })
        self.assertEqual([op.id for op in operations_out["operations_corr_major"]], ["ofw_main"])
        self.assertEqual(manager.op_authorized_ST_TTP, ["ofw_add_port"])
        self.assertEqual(manager.list_op_TTP, ["TTP", "additional"])
        self.assertEqual(manager.forecast_dict_value, {"type_forecast": "IPMA", "name_point": "AB"})
        self.assertEqual(set(manager.failure_dict_value), {"fail_001"})
        self.assertIs(vessels_out, vessels)
        self.assertEqual(vessels_out[0].fuel_type, "mgo")
        self.assertIs(manager.vessels_finder["vessel_001"], vessels_out[0])
        self.assertEqual(vessels_out[0].mobilisation_time, 0)
        self.assertEqual(vessels_out[0].mobilisation_cost, 0)
        self.assertEqual(vessels_out[0].n_ves_annual_contract, 0)
        self.assertEqual(vessels_out[0].n_ves_monthly_contract, 0)
        self.assertEqual(config.TIME_FAIL_OP_IMMEDIATELY, 0)
        self.assertFalse(config.STATISTICAL_CHART)
        self.assertEqual(inputs.cost.port_cost_year["value"], 0)
        self.assertEqual(inputs.cost.insurance_cost_year["value"], 0)
        self.assertEqual(inputs.cost.technicians_year["value"], 0)
        self.assertTrue(inputs.tseries.ST_O_M)

    @patch.object(user_inputs_module, "Forecast_manager", DummyForecastManager)
    def test_run_overwrite_with_ttp_selection_authorises_port_tow(self):
        """Explicit TTP selection authorises the port tow without additional ops."""
        config = SimpleNamespace(TIME_FAIL_OP_IMMEDIATELY=4, STATISTICAL_CHART=True)
        inputs = DummyInputs()
        failure = make_failure("fail_001", "ofw_main")
        operations = make_ttp_operations(failure)
        with tempfile.TemporaryDirectory() as tmp:
            paths = {
                "failure_path": write_yaml(tmp, "failure.yaml", [{"id": "fail_001"}]),
                "TTP_op_path": write_yaml(tmp, "ttp.yaml", [{"TTP": True, "additional": False}]),
                "forecast_path": write_yaml(tmp, "forecast.yaml", [{"type_forecast": "IPMA", "name_point": "AB"}]),
                "vessels_path": write_yaml(tmp, "vessels.yaml", []),
            }
            result = user_inputs_module.user_input_overwrite.run_overwrite(
                config, inputs, SimpleNamespace(run_dir=tmp), [failure], operations,
                [make_vessel()], paths,
            )
        self.assertEqual(len(result), 4)
        self.assertEqual(result[3].op_authorized_ST_TTP, ["ofw_tow_port"])
        self.assertEqual(result[3].list_op_TTP, ["TTP"])

    @patch.object(user_inputs_module, "Forecast_manager", DummyForecastManager)
    def test_run_overwrite_without_ttp_selection_authorises_no_tow(self):
        """Disabled TTP/TTS flags produce no authorised tow operation."""
        config = SimpleNamespace(TIME_FAIL_OP_IMMEDIATELY=4, STATISTICAL_CHART=True)
        inputs = DummyInputs()
        failure = make_failure("fail_001", "ofw_main")
        operations = make_ttp_operations(failure)
        with tempfile.TemporaryDirectory() as tmp:
            paths = {
                "failure_path": write_yaml(tmp, "failure.yaml", [{"id": "fail_001"}]),
                "TTP_op_path": write_yaml(tmp, "ttp.yaml", [{"TTP": False, "TTS": False, "additional": False}]),
                "forecast_path": write_yaml(tmp, "forecast.yaml", [{"type_forecast": "IPMA", "name_point": "AB"}]),
                "vessels_path": write_yaml(tmp, "vessels.yaml", []),
            }
            result = user_inputs_module.user_input_overwrite.run_overwrite(
                config, inputs, SimpleNamespace(run_dir=tmp), [failure], operations,
                [make_vessel()], paths,
            )
        self.assertEqual(len(result), 4)
        self.assertEqual(result[3].op_authorized_ST_TTP, [])
        self.assertEqual(result[3].list_op_TTP, [])

    @patch.object(user_inputs_module, "Forecast_manager", DummyForecastManager)
    def test_manual_dynamic_cable_workflow_keeps_only_selected_major_operation(self):
        """Preserve the dynamic-cable example under the current always-ST API."""
        config = SimpleNamespace(TIME_FAIL_OP_IMMEDIATELY=12, STATISTICAL_CHART=True)
        inputs = DummyInputs()
        cable_failure = make_failure(
            "ofw_cb_dyn_fail", "ofw_mj1",
            name="dynamic cable", fail_rate=0.00576436,
        )
        unrelated_failure = make_failure("ofw_other_fail", "ofw_mj2")
        selected_major = make_operation(
            "ofw_mj1", failures=[cable_failure],
            name="Cable Disconnection", tech_cost=300.0,
        )
        other_major = make_operation("ofw_mj2", failures=[unrelated_failure])
        unrelated_tow = make_operation("ofw_tow001")
        operations = {
            "operations_corr_major": [selected_major, other_major],
            "operations_tow": [unrelated_tow],
            "total_operations": [selected_major, other_major, unrelated_tow],
        }
        vessels = [make_vessel("vessel_001"), make_vessel("vessel_002")]

        with tempfile.TemporaryDirectory() as tmp:
            paths = {
                "failure_path": write_yaml(tmp, "failure.yaml", [{
                    "id": "OFW_CB_DYN_FAIL",
                    "name": "Dynamic Cable",
                    "fail_rate": 1,
                    "maintenance_strategy": "Immediately",
                    "operation_triggered": "OFW_MJ1",
                }]),
                "TTP_op_path": write_yaml(tmp, "ttp.yaml", []),
                "forecast_path": write_yaml(tmp, "forecast.yaml", [
                    {"type_forecast": "IPMA", "name_point": "AB"},
                ]),
                "operations_path": {
                    "operations_corr_major": write_yaml(tmp, "major.yaml", [{
                        "id": "ofw_mj1", "name": "New Major Name", "tech_cost": 10000,
                    }]),
                },
                "vessels_path": write_yaml(tmp, "vessel.yaml", [{
                    "id": "vessel_001", "fuel_type": "MGO",
                }]),
            }
            failures, filtered_ops, returned_vessels, manager = (
                user_inputs_module.user_input_overwrite.run_overwrite(
                    Config=config,
                    inputs=inputs,
                    dirs=SimpleNamespace(run_dir=tmp),
                    failures=[cable_failure, unrelated_failure],
                    operations=operations,
                    vessels=vessels,
                    files_paths=paths,
                )
            )

        self.assertEqual([failure.id for failure in failures], ["ofw_cb_dyn_fail"])
        self.assertEqual(cable_failure.fail_rate, 1)
        self.assertEqual(cable_failure.name, "dynamic cable")
        self.assertEqual(cable_failure.maintenance_strategy, "specific month")
        self.assertEqual([op.id for op in filtered_ops["operations_corr_major"]], ["ofw_mj1"])
        self.assertEqual(filtered_ops["operations_tow"], [])
        self.assertEqual({op.id for op in filtered_ops["total_operations"]}, {"ofw_mj1"})
        self.assertEqual(selected_major.name, "Cable Disconnection")
        self.assertEqual(selected_major.tech_cost, 300.0)
        self.assertIs(returned_vessels, vessels)
        self.assertEqual(vessels[0].fuel_type, "mgo")
        self.assertEqual(vessels[1].fuel_type, "diesel")
        self.assertTrue(all(vessel.mobilisation_cost == 0 for vessel in vessels))
        self.assertTrue(all(vessel.mobilisation_time == 0 for vessel in vessels))
        self.assertEqual(manager.op_authorized_ST_TTP, [])
        self.assertEqual(config.TIME_FAIL_OP_IMMEDIATELY, 0)
        self.assertFalse(config.STATISTICAL_CHART)



if __name__ == "__main__":
    unittest.main(verbosity=2)