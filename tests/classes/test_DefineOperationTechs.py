import unittest
from unittest.mock import patch, MagicMock
import tempfile
import os
from ruamel.yaml import YAML
from copy import deepcopy

# SUT
from logistic_tools.classes.DefineOperationTechs import Define_operation


# ----------------- Helpers & Dummies -----------------

class DummyOperation:
    """Minimal operation object holding vessel IDs and target attributes."""
    def __init__(self, vessel1_id=None, vessel2_id=None, rov_drone=None, id_="op_001"):
        self.vessel1_id = vessel1_id
        self.vessel2_id = vessel2_id
        self.vessel1 = None
        self.vessel2 = None
        self.rov_drone = rov_drone
        self.id = id_


class DummyRovDrone:
    def __init__(self, id_, meta=None):
        self.id = id_
        self.meta = {} if meta is None else dict(meta)


def write_vessels_yaml(tmpdir, records):
    """
    Write a list[dict] YAML to a temp file and return its path.
    Normalizes keys the same way as the code under test does (lowercased downstream).
    """
    path = os.path.join(tmpdir, "vessels.yaml")
    yaml = YAML()
    with open(path, "w") as f:
        yaml.dump(records, f)
    return path


# ----------------- Tests -----------------

class TestDefineOperationVessels(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base_dir = self.tmp.name

        # Minimal other required file paths (not read by tests because Vessel is patched)
        self.fuel_cons = os.path.join(self.base_dir, "fuel_cons.yaml")
        self.load_factor = os.path.join(self.base_dir, "load_factor.yaml")
        self.fuel_density = os.path.join(self.base_dir, "fuel_density.yaml")
        for p in (self.fuel_cons, self.load_factor, self.fuel_density):
            open(p, "w").close()

        # Common vessel records for happy paths
        self.vessels_ok = [
            {
                "id": "CTV-01",
                "type": "CTV",
                "speed_transit": 20,
                "power": 1000,
                "daily_charter": 15000,
                "crew_capacity": 12,
                # optional keys (some intentionally omitted to exercise defaults)
                "number_vessels": 1,
                "speed_towing": 6,
                "num_berths": 8,
                "overnight": False,
                "mother_vessel": None,
                "mobilisation_cost": 10000,
                "mobilisation_time": 24,
                "fuel_type": "MGO",
                "fuel_cons_transit": 1.1,
                "fuel_cons_maneuver": 0.6,
                "fuel_cons_standby": 0.3,
                "annual_contract": False,
                "n_ves_annual_contract": None,
                "months_contract": None,
                "monthly_contract_cost": None,
                "n_ves_monthly_contract": None,
            },
            {
                "id": "SOV-77",
                "type": "SOV",
                "speed_transit": 13,
                "power": 4500,
                "daily_charter": 65000,
                "crew_capacity": 60,
                "number_vessels": 1,
                "speed_towing": 5,
                "num_berths": 40,
                "overnight": True,
                "mother_vessel": None,
                "mobilisation_cost": 50000,
                "mobilisation_time": 48,
                "fuel_type": "MGO",
                "fuel_cons_transit": 6.5,
                "fuel_cons_maneuver": 3.0,
                "fuel_cons_standby": 1.5,
                "annual_contract": True,
                "n_ves_annual_contract": 1,
                "months_contract": 12,
                "monthly_contract_cost": 500000,
                "n_ves_monthly_contract": 1,
            },
        ]
        self.file_vessels = write_vessels_yaml(self.base_dir, self.vessels_ok)

    @patch("logistic_tools.classes.DefineOperationTechs.Vessel")
    def test_define_vessels_creates_vessel1_and_updates_dict(self, VesselMock):
        """Happy path: vessel1 found uniquely -> constructs Vessel and stores into dict."""
        op = DummyOperation(vessel1_id="CTV-01")
        vessels_dict = {}

        # Make Vessel() return a light dummy so we can inspect attributes
        created = MagicMock()
        created.id = "CTV-01"
        VesselMock.return_value = created

        Define_operation.define_vessels(
            operation=op,
            file_vessels=self.file_vessels,
            file_fuel_cons=self.fuel_cons,
            file_load_factor=self.load_factor,
            file_fuel_density=self.fuel_density,
            vessels=vessels_dict,
        )

        self.assertIs(op.vessel1, created)
        self.assertIn("CTV-01", vessels_dict)
        self.assertIs(vessels_dict["CTV-01"], created)
        VesselMock.assert_called_once()  # called for vessel1 only

    @patch("logistic_tools.classes.DefineOperationTechs.Vessel")
    def test_define_vessels_creates_both_vessels(self, VesselMock):
        """When both IDs are present and unique, both Vessel objects are created."""
        op = DummyOperation(vessel1_id="CTV-01", vessel2_id="SOV-77")
        vessels_dict = {}

        v1 = MagicMock(); v1.id = "CTV-01"
        v2 = MagicMock(); v2.id = "SOV-77"
        VesselMock.side_effect = [v1, v2]

        Define_operation.define_vessels(
            operation=op,
            file_vessels=self.file_vessels,
            file_fuel_cons=self.fuel_cons,
            file_load_factor=self.load_factor,
            file_fuel_density=self.fuel_density,
            vessels=vessels_dict,
        )

        self.assertIs(op.vessel1, v1)
        self.assertIs(op.vessel2, v2)
        self.assertIn("CTV-01", vessels_dict)
        self.assertIn("SOV-77", vessels_dict)
        self.assertIs(vessels_dict["CTV-01"], v1)
        self.assertIs(vessels_dict["SOV-77"], v2)
        self.assertEqual(VesselMock.call_count, 2)

    @patch("logistic_tools.classes.DefineOperationTechs.Vessel")
    def test_existing_vessel_in_dict_is_not_overwritten(self, VesselMock):
        """
        If a vessel with same ID already exists in the dict, it should not be overwritten
        (the code only inserts when the key is missing).
        """
        op = DummyOperation(vessel1_id="CTV-01")
        sentinel = object()
        vessels_dict = {"CTV-01": sentinel}

        Define_operation.define_vessels(
            operation=op,
            file_vessels=self.file_vessels,
            file_fuel_cons=self.fuel_cons,
            file_load_factor=self.load_factor,
            file_fuel_density=self.fuel_density,
            vessels=vessels_dict,
        )

        self.assertIs(vessels_dict["CTV-01"], sentinel)
        # op.vessel1 is still created and assigned to operation (by design)
        VesselMock.assert_called_once()

    def test_vessel1_not_found_raises_IndexError(self):
        """If vessel1_id not present in YAML, IndexError is raised."""
        op = DummyOperation(vessel1_id="MISSING")
        vessels_dict = {}
        with self.assertRaises(IndexError):
            Define_operation.define_vessels(
                operation=op,
                file_vessels=self.file_vessels,
                file_fuel_cons=self.fuel_cons,
                file_load_factor=self.load_factor,
                file_fuel_density=self.fuel_density,
                vessels=vessels_dict,
            )

    def test_vessel2_duplicate_raises_IndexError(self):
        """If duplicates for vessel2_id exist in YAML, IndexError is raised."""
        # Create a YAML with duplicate entries for the same ID
        dup_records = self.vessels_ok + [deepcopy(self.vessels_ok[1])]
        dup_records[-1]["id"] = "SOV-77"  # same ID
        file_dup = write_vessels_yaml(self.base_dir, dup_records)

        op = DummyOperation(vessel2_id="SOV-77")
        vessels_dict = {}
        with self.assertRaises(IndexError):
            Define_operation.define_vessels(
                operation=op,
                file_vessels=file_dup,
                file_fuel_cons=self.fuel_cons,
                file_load_factor=self.load_factor,
                file_fuel_density=self.fuel_density,
                vessels=vessels_dict,
            )


class TestDefineOperationRovs(unittest.TestCase):

    def test_define_rovs_happy_path_deepcopy(self):
        """
        When a matching rov_drone ID exists, operation.rov_drone becomes a deepcopy
        of the original object.
        """
        op = DummyOperation(rov_drone="ROV_A")
        rovs = [DummyRovDrone("ROV_A", meta={"k": 1}), DummyRovDrone("ROV_B")]

        Define_operation.define_rovs(operation=op, rovs_drones=rovs)

        # It must be an independent copy (deepcopy)
        self.assertIsNot(op.rov_drone, rovs[0])
        self.assertEqual(op.rov_drone.id, "ROV_A")
        self.assertEqual(op.rov_drone.meta, {"k": 1})

        # Mutate source; copy should not change
        rovs[0].meta["k"] = 999
        self.assertEqual(op.rov_drone.meta, {"k": 1})

    def test_define_rovs_not_found_raises(self):
        """If no rov/drone with the requested ID exists, NameError is raised."""
        op = DummyOperation(rov_drone="NOPE")
        rovs = [DummyRovDrone("ROV_A"), DummyRovDrone("ROV_B")]
        with self.assertRaises(NameError):
            Define_operation.define_rovs(operation=op, rovs_drones=rovs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
