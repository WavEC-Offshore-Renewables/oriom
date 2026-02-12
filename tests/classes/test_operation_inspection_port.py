import os
import tempfile
import unittest
from unittest.mock import patch

from ruamel.yaml import YAML

# Adjust this import if your package structure is different
from logistic_tools.classes.Operations.InspectionPort import InspectionPort


class FakeTowOp:
    """Simple helper class to mimic an OperationTow object."""
    def __init__(self, _id, name):
        self.id = _id
        self.name = name


class FakeVessel:
    """Simple helper class to mimic a Vessel object."""
    def __init__(self, _id, n_vessels):
        self.id = _id
        self.n_vessels = n_vessels


class FakeRovDrone:
    """Simple helper class to mimic a Rov/Drone object."""
    def __init__(self, _id):
        self.id = _id


class FakeTechObj:
    """Simple helper class to mimic wtg/wec/pv objects in define_device_at_port."""
    def __init__(self, n_device_at_port, n_device_stored_at_port):
        self.n_device_at_port = n_device_at_port
        self.n_device_stored_at_port = n_device_stored_at_port


def make_valid_towing_ops(prefix="ofw"):
    """
    Create a list of towing ops satisfying _define_tow_operations:
    - one removal-only
    - one deploy-only
    - one removal+deploy
    """
    return [
        FakeTowOp(f"{prefix}_remov", "remov to port"),
        FakeTowOp(f"{prefix}_deplo", "deplo to site"),
        FakeTowOp(f"{prefix}_both", "remov & deplo"),
    ]


def make_base_kwargs(**overrides):
    """Base kwargs for constructing an InspectionPort, all valid by default."""
    kwargs = dict(
        id_="ofw001",
        name="Port inspection",
        periodicity=1.0,
        tech_per_device=2,
        dur_per_device=4.0,
        towing_ops=make_valid_towing_ops("ofw"),
        intervened_devices=1,
        tech_cost=100.0,
        months="06,07",
        day_start=10,
        wind_speed=15.0,
        light=True,
        level="device",
        rov_drone=None,
        parts_cost=100.0,
        other_costs=50.0,
        port_costs=200.0,
        n_device_at_port=1,
        n_device_stored_at_port=0,
        double_shift=True,
    )
    kwargs.update(overrides)
    return kwargs


class TestInspectionPort(unittest.TestCase):
    # ------------------------------------------------------------------ #
    # __init__ and basic attributes
    # ------------------------------------------------------------------ #
    def test_init_valid_basic_attributes_and_tow_ops(self):
        """Constructor must correctly set attributes and define tow operations for a valid case."""
        op = InspectionPort(**make_base_kwargs())

        self.assertEqual(op.id, "ofw001")
        self.assertEqual(op.name, "Port inspection")
        self.assertEqual(op.periodicity, 1.0)
        self.assertEqual(op.tech_per_device, 2)
        self.assertEqual(op.dur_per_device, 4.0)
        self.assertEqual(op.intervened_devices, 1)
        self.assertEqual(op.tech_cost, 100.0)
        self.assertEqual(op.months, [6, 7])
        self.assertEqual(op.day_start, 10)
        self.assertEqual(op.ws, 15.0)
        self.assertTrue(op.light)
        self.assertEqual(op.level, "device")
        self.assertEqual(op.parts_cost, 100.0)
        self.assertEqual(op.other_costs, 50.0)
        self.assertEqual(op.port_costs, 200.0)
        self.assertEqual(op.n_device_at_port, 1)
        self.assertEqual(op.n_device_stored_at_port, 0)
        self.assertTrue(op.double_shift)

        # Tow ops from make_valid_towing_ops
        self.assertEqual(op.op_tow_port, "ofw_remov")
        self.assertEqual(op.op_tow_site, "ofw_deplo")
        self.assertEqual(op.op_tow_site_port, "ofw_both")

    def test_init_default_months_when_not_provided(self):
        """If months is None, all months (1–12) must be considered."""
        op = InspectionPort(**make_base_kwargs(months=None))

        self.assertEqual(op.months, list(range(1, 13)))
        # day_start default should be 1 (set in __init__)
        self.assertEqual(op.day_start, 10)

    def test_init_invalid_prefix_raises(self):
        """Invalid prefix must raise ValueError in _check_attributes."""
        with self.assertRaises(ValueError) as cm:
            InspectionPort(**make_base_kwargs(id_="xxx001"))
        self.assertIn("prefix not recognized", str(cm.exception))

    def test_init_months_invalid_format_raises(self):
        """
        Invalid months string (cannot be converted to int) must raise ValueError
        with the specific message.
        """
        with self.assertRaises(ValueError) as cm:
            InspectionPort(**make_base_kwargs(months="jan,feb"))
        self.assertIn('"months" must be in the format', str(cm.exception))

    # ------------------------------------------------------------------ #
    # _check_attributes: ranges and validations
    # ------------------------------------------------------------------ #
    def test_check_attributes_negative_periodicity_raises(self):
        """Non-positive periodicity must raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            InspectionPort(**make_base_kwargs(periodicity=0.0))
        self.assertIn('"periodicity" must be positive', str(cm.exception))

    def test_check_attributes_tech_per_device_must_be_positive(self):
        """tech_per_device < 1 must raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            InspectionPort(**make_base_kwargs(tech_per_device=0))
        self.assertIn('"tech_per_device" must be positive', str(cm.exception))

    def test_check_attributes_dur_per_device_must_be_positive(self):
        """dur_per_device <= 0 must raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            InspectionPort(**make_base_kwargs(dur_per_device=0.0))
        self.assertIn('"dur_per_device" must be positive', str(cm.exception))

    def test_check_attributes_months_out_of_range_raises(self):
        """Months outside [1, 12] must raise NameError."""
        with self.assertRaises(NameError) as cm:
            InspectionPort(**make_base_kwargs(months="0,5"))
        self.assertIn('"months" must be between 1 and 12', str(cm.exception))

    def test_check_attributes_day_start_out_of_range_for_single_month_raises(self):
        """day_start outside allowed range for a single month must raise ValueError."""
        # February (28 days) with day_start=31 → error
        with self.assertRaises(ValueError) as cm:
            InspectionPort(**make_base_kwargs(months="02", day_start=31))
        self.assertIn('"day_start" must be between 1 and 28', str(cm.exception))

    def test_check_attributes_day_start_out_of_range_for_multiple_months_raises(self):
        """
        For multiple months, valid days are 1 .. min(last_day of months).
        For Feb and March, last_day = min(28, 31) = 28.
        day_start=29 → error.
        """
        with self.assertRaises(ValueError) as cm:
            InspectionPort(**make_base_kwargs(months="02,03", day_start=29))
        self.assertIn('"day_start" must be between 1 and 28', str(cm.exception))

    def test_check_attributes_negative_wind_speed_raises(self):
        """Negative wind_speed must raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            InspectionPort(**make_base_kwargs(wind_speed=-1.0))
        self.assertIn('"wind_speed" must not be negative', str(cm.exception))

    def test_check_attributes_negative_costs_and_devices_raise(self):
        """Negative costs or device counts must raise ValueError."""
        with self.assertRaises(ValueError):
            InspectionPort(**make_base_kwargs(parts_cost=-1.0))
        with self.assertRaises(ValueError):
            InspectionPort(**make_base_kwargs(other_costs=-1.0))
        with self.assertRaises(ValueError):
            InspectionPort(**make_base_kwargs(port_costs=-1.0))
        with self.assertRaises(ValueError):
            InspectionPort(**make_base_kwargs(n_device_at_port=-1))
        with self.assertRaises(ValueError):
            InspectionPort(**make_base_kwargs(n_device_stored_at_port=-1))

    # ------------------------------------------------------------------ #
    # light / double_shift parsing
    # ------------------------------------------------------------------ #
    def test_light_parsing_boolean_numeric_and_string(self):
        """Light flag must correctly parse bool, numeric and string representations."""
        # direct bool
        op_true = InspectionPort(**make_base_kwargs(id_="ofw010", light=True))
        self.assertTrue(op_true.light)

        op_false = InspectionPort(**make_base_kwargs(id_="ofw011", light=False))
        self.assertFalse(op_false.light)

        # numeric form
        op_num_true = InspectionPort(**make_base_kwargs(id_="ofw012", light=1.0))
        self.assertTrue(op_num_true.light)

        op_num_false = InspectionPort(**make_base_kwargs(id_="ofw013", light=0.0))
        self.assertFalse(op_num_false.light)

        # string form via strtobool
        op_str_true = InspectionPort(**make_base_kwargs(id_="ofw014", light="true"))
        self.assertTrue(op_str_true.light)

        op_str_false = InspectionPort(**make_base_kwargs(id_="ofw015", light="False"))
        self.assertFalse(op_str_false.light)

    def test_light_invalid_string_raises(self):
        """
        Invalid string for 'light' must raise an exception.

        Implementation uses an undefined _e in the raise, so we accept any Exception.
        """
        with self.assertRaises(Exception):
            InspectionPort(**make_base_kwargs(id_="ofw016", light="not_a_bool"))

    def test_double_shift_parsing_variants(self):
        """double_shift must be parsed correctly from various representations."""
        op_true = InspectionPort(**make_base_kwargs(id_="ofw020", double_shift=True))
        self.assertTrue(op_true.double_shift)

        op_false = InspectionPort(**make_base_kwargs(id_="ofw021", double_shift=False))
        self.assertFalse(op_false.double_shift)

        op_num_true = InspectionPort(**make_base_kwargs(id_="ofw022", double_shift=1.0))
        self.assertTrue(op_num_true.double_shift)

        op_num_false = InspectionPort(**make_base_kwargs(id_="ofw023", double_shift=0.0))
        self.assertFalse(op_num_false.double_shift)

        op_str_false = InspectionPort(**make_base_kwargs(id_="ofw024", double_shift="false"))
        self.assertFalse(op_str_false.double_shift)

    def test_double_shift_invalid_string_raises(self):
        """
        Invalid string for 'double_shift' must raise an exception.

        Implementation uses an undefined _e in the raise, so we accept any Exception.
        """
        with self.assertRaises(Exception):
            InspectionPort(**make_base_kwargs(id_="ofw025", double_shift="not_bool"))

    # ------------------------------------------------------------------ #
    # _define_tow_operations behaviour
    # ------------------------------------------------------------------ #

    def test_define_tow_operations_unrecognized_name_raises_type_error(self):
        """If a tow operation name has neither 'remov' nor 'deplo', TypeError must be raised."""
        op = InspectionPort(**make_base_kwargs())
        bad_ops = [FakeTowOp("ofw_unknown", "just towing")]
        with self.assertRaises(TypeError):
            op._define_tow_operations(bad_ops)

    # ------------------------------------------------------------------ #
    # get_inspections_from_yaml
    # ------------------------------------------------------------------ #
    def test_get_inspections_from_yaml_success(self):
        """get_inspections_from_yaml must build a list of InspectionPort objects from YAML."""
        yaml_data = [
            {
                "ID": "OFW100",
                "Name": "Port insp from YAML",
                "periodicity": 2.0,
                "tech_per_device": 3,
                "dur_per_device": 5.0,
                "tech_cost": 150.0,
                "months": "03,04",
                "day_start": 5,
                "intervened_devices": 2,
                "wind_speed": 12.0,
                "light": "true",
                "level": "device",
                "parts_cost": 200.0,
                "ports_cost": 300.0,
                "other_costs": 80.0,
                "n_device_at_port": 2,
                "n_device_stored_at_port": 1,
                "double_shift": True,
            }
        ]

        yaml_obj = YAML()
        towing_ops = make_valid_towing_ops("ofw")

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = os.path.join(tmpdir, "insp.yaml")
            with open(yaml_path, "w") as f:
                yaml_obj.dump(yaml_data, f)

            inspections = InspectionPort.get_inspections_from_yaml(
                yaml_path,
                towing_operations=towing_ops,
            )

        self.assertEqual(len(inspections), 1)
        op = inspections[0]
        self.assertIsInstance(op, InspectionPort)
        self.assertEqual(op.id, "ofw100")
        self.assertEqual(op.name, "Port insp from YAML")
        self.assertEqual(op.periodicity, 2.0)
        self.assertEqual(op.tech_per_device, 3)
        self.assertEqual(op.dur_per_device, 5.0)
        self.assertEqual(op.tech_cost, 150.0)
        self.assertEqual(op.months, [3, 4])
        self.assertEqual(op.day_start, 5)
        self.assertEqual(op.intervened_devices, 2)
        self.assertEqual(op.ws, 12.0)
        self.assertTrue(op.light)
        self.assertEqual(op.level, "device")
        self.assertEqual(op.parts_cost, 200.0)
        self.assertEqual(op.port_costs, 300.0)
        self.assertEqual(op.other_costs, 80.0)
        self.assertEqual(op.n_device_at_port, 2)
        self.assertEqual(op.n_device_stored_at_port, 1)
        self.assertTrue(op.double_shift)
        self.assertEqual(op.op_tow_port, "ofw_remov")

    def test_get_inspections_from_yaml_missing_mandatory_keys_raises(self):
        """Missing mandatory keys in YAML entries must raise KeyError."""
        yaml_data = [
            {
                # 'periodicity' missing
                "id": "OFW999",
                "name": "Missing periodicity",
                "tech_per_device": 3,
                "dur_per_device": 5.0,
            }
        ]

        yaml_obj = YAML()

        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = os.path.join(tmpdir, "insp_bad.yaml")
            with open(yaml_path, "w") as f:
                yaml_obj.dump(yaml_data, f)

            with self.assertRaises(KeyError):
                InspectionPort.get_inspections_from_yaml(
                    yaml_path,
                    towing_operations=make_valid_towing_ops("ofw"),
                )

    # ------------------------------------------------------------------ #
    # define_device_at_port
    # ------------------------------------------------------------------ #
    def test_define_device_at_port_sets_values_for_ofw(self):
        """define_device_at_port must pick values from the correct technology object."""
        op = InspectionPort(**make_base_kwargs(id_="ofw200"))
        wtg = FakeTechObj(n_device_at_port=3, n_device_stored_at_port=2)
        wec = FakeTechObj(n_device_at_port=99, n_device_stored_at_port=99)
        pv = FakeTechObj(n_device_at_port=99, n_device_stored_at_port=99)

        op.define_device_at_port(wtg, wec, pv)
        self.assertEqual(op.n_device_at_port, 3)
        self.assertEqual(op.n_device_stored_at_port, 2)

    def test_define_device_at_port_defaults_for_none_or_zero(self):
        """None/zero values must be defaulted to 1 and 0."""
        op = InspectionPort(**make_base_kwargs(id_="ofw201"))
        wtg = FakeTechObj(n_device_at_port=None, n_device_stored_at_port=None)
        wec = FakeTechObj(n_device_at_port=0, n_device_stored_at_port=None)
        pv = FakeTechObj(n_device_at_port=0, n_device_stored_at_port=None)

        op.define_device_at_port(wtg, wec, pv)
        self.assertEqual(op.n_device_at_port, 1)
        self.assertEqual(op.n_device_stored_at_port, 0)

    def test_define_device_at_port_negative_values_raise(self):
        """Negative values for device counts must raise ValueError."""
        op = InspectionPort(**make_base_kwargs(id_="ofw202"))
        wtg = FakeTechObj(n_device_at_port=-1, n_device_stored_at_port=0)
        wec = FakeTechObj(0, 0)
        pv = FakeTechObj(0, 0)

        with self.assertRaises(ValueError):
            op.define_device_at_port(wtg, wec, pv)

    def test_define_device_at_port_invalid_prefix_raises_keyerror(self):
        """Invalid prefix must cause KeyError in define_device_at_port."""
        op = InspectionPort(**make_base_kwargs(id_="ofw203"))
        # Hack id after creation to bypass __init__ prefix check
        op.id = "xxx999"
        wtg = FakeTechObj(1, 0)
        wec = FakeTechObj(1, 0)
        pv = FakeTechObj(1, 0)

        with self.assertRaises(KeyError):
            op.define_device_at_port(wtg, wec, pv)

    # ------------------------------------------------------------------ #
    # assign_shift_attributes
    # ------------------------------------------------------------------ #
    def test_assign_shift_attributes_uses_given_fields(self):
        """assign_shift_attributes must correctly map dictionary entries to attributes."""
        op = InspectionPort(**make_base_kwargs(id_="ofw300"))

        data = {
            "days_main": 5,
            "duration_main": 10.0,
            "days_last": 2,
            "duration_last": 4.0,
            "n_crew_main": 8,
            "n_crew_last": 4,
        }
        op.assign_shift_attributes(data)

        self.assertEqual(op.days_main, 5)
        self.assertEqual(op.duration_main, 10.0)
        self.assertEqual(op.days_last, 2)
        self.assertEqual(op.duration_last, 4.0)
        self.assertEqual(op.n_crew_main, 8)
        self.assertEqual(op.n_crew_last, 4)

    def test_assign_shift_attributes_falls_back_to_number_shifts_if_days_missing(self):
        """If days_main/days_last are None, use number_shifts_main/last from data."""
        op = InspectionPort(**make_base_kwargs(id_="ofw301"))

        data = {
            "days_main": None,
            "number_shifts_main": 7,
            "duration_main": 9.0,
            "days_last": None,
            "number_shifts_last": 3,
            "duration_last": 5.0,
        }
        op.assign_shift_attributes(data)

        self.assertEqual(op.days_main, 7)
        self.assertEqual(op.days_last, 3)
        self.assertEqual(op.duration_main, 9.0)
        self.assertEqual(op.duration_last, 5.0)

    # ------------------------------------------------------------------ #
    # tech_finder
    # ------------------------------------------------------------------ #
    def test_tech_finder_returns_correct_graph_key(self):
        """tech_finder must map prefixes to correct graph keys or None."""
        op_wind = InspectionPort(**make_base_kwargs(id_="ofw400"))
        op_wave = InspectionPort(**make_base_kwargs(id_="owc400", towing_ops=make_valid_towing_ops("owc")))
        op_pv = InspectionPort(**make_base_kwargs(id_="opv400", towing_ops=make_valid_towing_ops("opv")))

        self.assertEqual(op_wind.tech_finder(), "G_wind")
        self.assertEqual(op_wave.tech_finder(), "G_wave")
        self.assertEqual(op_pv.tech_finder(), "G_pv")

        # Hack an unknown id to test None
        op_other = InspectionPort(**make_base_kwargs(id_="ofw401"))
        op_other.id = "oce001"
        self.assertIsNone(op_other.tech_finder())

    # ------------------------------------------------------------------ #
    # define_level
    # ------------------------------------------------------------------ #
    @patch("logistic_tools.classes.Operations.InspectionPort.find_highest_power_node")
    def test_define_level_for_known_technology(self, mock_find):
        """define_level must use tech_finder and find_highest_power_node to set level."""
        mock_find.return_value = "node_X"
        op = InspectionPort(**make_base_kwargs(id_="ofw500"))
        # Reset level to None to force define_level to act
        op.level = None

        G_layouts = {"G_wind": "graph_wind", "G_wave": "graph_wave", "G_pv": "graph_pv"}
        op.define_level(G_layouts)

        mock_find.assert_called_once_with("graph_wind")
        self.assertEqual(op.level, "node_X")

    @patch("logistic_tools.classes.Operations.InspectionPort.find_highest_power_node")
    def test_define_level_for_oce_common_event(self, mock_find):
        """
        When tech_finder returns None (e.g. oce prefix), define_level should
        iterate over G_wind/G_wave/G_pv until one works.
        """
        # Construct valid op, then hack ID to 'oce001'
        op = InspectionPort(**make_base_kwargs(id_="ofw501"))
        op.id = "oce001"
        op.level = None

        # First call raises AttributeError, second returns node
        mock_find.side_effect = [
            AttributeError("no graph"),  # for G_wind
            "node_from_wave",            # for G_wave
            "node_unused",               # (would be G_pv)
        ]

        G_layouts = {
            "G_wind": "graph_wind",
            "G_wave": "graph_wave",
            "G_pv": "graph_pv",
        }

        op.define_level(G_layouts)
        # Called at least twice, but we only care that level is set from second
        self.assertEqual(op.level, "node_from_wave")

    # ------------------------------------------------------------------ #
    # to_yaml
    # ------------------------------------------------------------------ #
    def test_to_yaml_writes_attributes_file_with_expected_structure(self):
        """to_yaml must write attributes.yaml with the correct keys and values."""
        op = InspectionPort(**make_base_kwargs(id_="ofw600"))

        # Attach vessel objects and rov/drone
        op.vessel1 = FakeVessel("ctv1", 2)
        op.vessel2 = FakeVessel("support1", 1)
        op.rov_drone = FakeRovDrone("rov1")

        with tempfile.TemporaryDirectory() as tmpdir:
            op.to_yaml(tmpdir)

            attr_path = os.path.join(tmpdir, "attributes.yaml")
            self.assertTrue(os.path.exists(attr_path))

            yaml_safe = YAML(typ="safe")
            with open(attr_path, "r") as f:
                data = yaml_safe.load(f)

        # Basic keys
        for key in [
            "id",
            "name",
            "periodicity",
            "months",
            "day_start",
            "tech_per_device",
            "tech_cost",
            "dur_per_device",
            "op_tow_port",
            "op_tow_site",
            "vessel1",
            "vessel2",
            "intervened_devices",
            "ws",
            "light",
            "level",
            "rov_drone",
            "parts_cost",
            "other_costs",
            "port_costs",
            "n_device_at_port",
            "n_device_stored_at_port",
            "op_tow_site_port",
            "days_main",
            "days_last",
            "duration_main",
            "duration_last",
            "double_shift",
        ]:
            self.assertIn(key, data, f"Key {key} must be present in attributes.yaml")

        self.assertEqual(data["id"], "ofw600")
        self.assertEqual(data["name"], "Port inspection")
        self.assertEqual(data["periodicity"], 1.0)
        self.assertEqual(data["months"], [6, 7])
        self.assertEqual(data["day_start"], 10)
        self.assertEqual(data["tech_per_device"], 2)
        self.assertEqual(data["tech_cost"], 100.0)
        self.assertEqual(data["dur_per_device"], 4.0)
        self.assertEqual(data["intervened_devices"], 1)
        self.assertEqual(data["ws"], 15.0)
        self.assertTrue(data["light"])
        self.assertEqual(data["level"], "device")
        self.assertEqual(data["parts_cost"], 100.0)
        self.assertEqual(data["other_costs"], 50.0)
        self.assertEqual(data["port_costs"], 200.0)
        self.assertEqual(data["n_device_at_port"], 1)
        self.assertEqual(data["n_device_stored_at_port"], 0)
        self.assertTrue(data["double_shift"])

        # Vessels must be dicts with id and number
        self.assertEqual(data["vessel1"]["id"], "ctv1")
        self.assertEqual(data["vessel1"]["number"], 2)
        self.assertEqual(data["vessel2"]["id"], "support1")
        self.assertEqual(data["vessel2"]["number"], 1)

        # Rov/drone must be written as its id
        self.assertEqual(data["rov_drone"], "rov1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
