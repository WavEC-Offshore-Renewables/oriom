# test_yaml_manager.py

import os
import unittest
import tempfile

from ruamel.yaml import YAML

from oriom.utils import yaml_manager
from oriom.utils.aux_functions import update_dict


class DummyInputs:
    """Simple helper class to mimic Inputs.X with an `inputs` dict."""
    def __init__(self, inputs_dict):
        self.inputs = inputs_dict


class TestInputsToYaml(unittest.TestCase):
    def test_inputs_to_yaml_creates_yaml_with_values_and_units(self):
        """inputs_to_yaml should write a YAML file with value/units per input key."""
        inputs_obj = DummyInputs(
            {
                "param_a": {"value": 10, "units": "m"},
                "param_b": {"value": 3.14, "units": "s"},
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_manager.inputs_to_yaml(inputs_obj, out_dir=tmpdir, out_name="test_inputs")

            path = os.path.join(tmpdir, "test_inputs.yaml")
            self.assertTrue(os.path.exists(path))

            yaml = YAML(typ="safe")
            with open(path, "r") as f:
                data = yaml.load(f)

            self.assertEqual(data["param_a"]["value"], 10)
            self.assertEqual(data["param_a"]["units"], "m")
            self.assertEqual(data["param_b"]["value"], 3.14)
            self.assertEqual(data["param_b"]["units"], "s")


class TestUpdateYamlEachAttribute(unittest.TestCase):
    def test_update_yaml_each_attribute_maps_shift_keys_and_ignores_olc(self):
        """
        update_yaml_each_attribute should:
        - map number_shifts_main -> days_main, etc.
        - ignore keys containing 'olc'
        - preserve existing keys.
        """
        initial_content = {
            "existing_key": 1,
            "olc_main": {"hs": 1.0},  # should not be overwritten
        }

        data = {
            "number_shifts_main": 2,
            "number_shifts_last": 1,
            "duration_shift_main": 12.0,
            "duration_shift_last": 4.0,
            "n_vessel_main": 3,
            "n_vessel_last": 1,
            "olc_main": {"hs": 2.0},  # must be ignored in update
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "attrs.yaml")
            yaml = YAML()
            with open(path, "w") as f:
                yaml.dump(initial_content, f)

            yaml_manager.update_yaml_each_attribute(
                file_dir=tmpdir,
                file_name="attrs.yaml",
                data=data
            )

            with open(path, "r") as f:
                updated = YAML(typ="safe").load(f)

        # Check mapped keys
        self.assertEqual(updated["existing_key"], 1)
        self.assertEqual(updated["days_main"], 2)
        self.assertEqual(updated["days_last"], 1)
        self.assertEqual(updated["duration_main"], 12.0)
        self.assertEqual(updated["duration_last"], 4.0)
        self.assertEqual(updated["n_vessel_main"], 3)
        self.assertEqual(updated["n_vessel_last"], 1)

        # olc_main must remain as in the original file
        self.assertEqual(updated["olc_main"], {"hs": 1.0})

    def test_update_yaml_each_attribute_raises_on_empty_file(self):
        """If YAML file is empty (None), update_yaml_each_attribute must raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "empty.yaml")
            # Create an empty file
            open(path, "w").close()

            with self.assertRaises(ValueError):
                yaml_manager.update_yaml_each_attribute(
                    file_dir=tmpdir,
                    file_name="empty.yaml",
                    data={"number_shifts_main": 1},
                )


class TestUpdateYaml(unittest.TestCase):
    def test_update_yaml_non_recursive_sets_data_key(self):
        """update_yaml with data_key and recursive=False should set/overwrite that section."""
        original = {"a": 1, "nested": {"x": 1}}
        new_data = {"b": 2}

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "file.yaml")
            yaml = YAML()
            with open(path, "w") as f:
                yaml.dump(original, f)

            yaml_manager.update_yaml(
                file_dir=tmpdir,
                file_name="file.yaml",
                data=new_data,
                data_key="new_section",
                recursive=False,
            )

            with open(path, "r") as f:
                updated = YAML(typ="safe").load(f)

        self.assertEqual(updated["a"], 1)
        self.assertEqual(updated["nested"]["x"], 1)
        self.assertEqual(updated["new_section"], {"b": 2})


class TestLoadShiftValuesFromYaml(unittest.TestCase):
    def test_load_shift_values_from_yaml_reads_all_keys(self):
        """load_shift_values_from_yaml should return a dict with all expected keys."""
        content = {
            "days_main": 1,
            "duration_main": 2.0,
            "days_last": 3,
            "duration_last": 4.0,
            "n_vessel_main": 5,
            "n_vessel_last": 6,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "shift.yaml")
            yaml = YAML()
            with open(path, "w") as f:
                yaml.dump(content, f)

            result = yaml_manager.load_shift_values_from_yaml(tmpdir, "shift.yaml")

        expected_keys = [
            "days_main",
            "duration_main",
            "days_last",
            "duration_last",
            "n_vessel_main",
            "n_vessel_last",
        ]
        for k in expected_keys:
            self.assertIn(k, result)

        self.assertEqual(result["days_main"], 1)
        self.assertEqual(result["duration_main"], 2.0)
        self.assertEqual(result["days_last"], 3)
        self.assertEqual(result["duration_last"], 4.0)
        self.assertEqual(result["n_vessel_main"], 5)
        self.assertEqual(result["n_vessel_last"], 6)

    def test_load_shift_values_from_yaml_defaults_to_none_if_missing(self):
        """Missing keys in YAML must yield None in result dict."""
        content = {
            "days_main": 10,
            # other keys omitted on purpose
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "shift.yaml")
            yaml = YAML()
            with open(path, "w") as f:
                yaml.dump(content, f)

            result = yaml_manager.load_shift_values_from_yaml(tmpdir, "shift.yaml")

        self.assertEqual(result["days_main"], 10)
        self.assertIsNone(result["duration_main"])
        self.assertIsNone(result["days_last"])
        self.assertIsNone(result["duration_last"])
        self.assertIsNone(result["n_vessel_main"])
        self.assertIsNone(result["n_vessel_last"])


class TestLoadSimilarOpYaml(unittest.TestCase):
    def test_load_similar_op_yaml_splits_op_and_working_shift_data(self):
        """
        load_similar_op_yaml should:
        - read op_working_shifts keys from root (except olc_* from working_shifts section)
        - read data_working_shifts from 'working_shifts' section only.
        """
        content = {
            "working_shifts": {
                "days_main": 1,
                "days_last": 2,
                "duration_main": 12.0,
                "duration_last": 4.0,
                "n_vessels_main": 3,
                "n_vessels_last": 1,
                "id_grouped": "grp_1",
                "days_grouped": 30,
                "duration_grouped": 40.0,
                "rov_main": True,
                "rov_grouped": False,
                "olc_main": {"hs": 1.0},  # special: must go in op_working_shifts
                "olc_last": {"hs": 2.0},
            },
            # working_shifts section
            "id_main": "op_A",
            "days_main": 3,  # should be used only for data_working_shifts, not for op_working_shifts
            "duration_main": 12.0,
            "id_grouped": "grp_1",
            "days_grouped": 30,
            "duration_grouped": 40.0,
            "rov_main": True,
            "rov_grouped": False,
            "n_vessel_main": 3,
            "n_vessel_last": 1,
            "n_dev_inspected_main_shift": 9,
            "n_dev_inspected_last_shift": 10,
            "n_crew_main": 5,
            "n_crew_last": 2,
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "similar.yaml")
            yaml = YAML()
            with open(path, "w") as f:
                yaml.dump(content, f)

            op_working_shifts, data_working_shifts = yaml_manager.load_similar_op_yaml(
                file_dir=tmpdir,
                file_name="similar.yaml",
                operation_id = "op_A"
            )

        # op_working_shifts: non-olc keys from root 'content', olc_* from 'working_shifts'
        self.assertNotIn("id_main", op_working_shifts)
        self.assertEqual(op_working_shifts["days_main"], 3)  # from root, not 10
        self.assertEqual(op_working_shifts["duration_main"], 12.0)
        self.assertEqual(op_working_shifts["n_vessel_main"], 3)
        self.assertEqual(op_working_shifts["n_vessel_last"], 1)
        self.assertEqual(op_working_shifts["n_crew_main"], 5)
        self.assertEqual(op_working_shifts["n_crew_last"], 2)
        self.assertEqual(
            op_working_shifts["n_dev_inspected_main_shift"], 9
        )
        self.assertEqual(
            op_working_shifts["n_dev_inspected_last_shift"], 10
        )

        # data_working_shifts: only from working_shifts section
        self.assertEqual(data_working_shifts["days_main"], 1)
        self.assertEqual(data_working_shifts["duration_main"], 12.0)
        self.assertEqual(data_working_shifts["id_grouped"], "grp_1")
        self.assertEqual(data_working_shifts["days_grouped"], 30)
        self.assertEqual(data_working_shifts["duration_grouped"], 40.0)
        self.assertEqual(data_working_shifts["rov_main"], True)
        self.assertEqual(data_working_shifts["rov_grouped"], False)
        self.assertEqual(data_working_shifts["n_vessels_main"], 3)
        self.assertEqual(data_working_shifts["n_vessels_last"], 1)
        self.assertEqual(data_working_shifts["olc_main"], {"hs": 1.0})
        self.assertEqual(data_working_shifts["olc_last"], {"hs": 2.0})

if __name__ == "__main__":
    unittest.main(verbosity=2)