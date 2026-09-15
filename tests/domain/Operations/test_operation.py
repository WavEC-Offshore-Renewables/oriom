import unittest
from unittest.case import skip
import os
from copy import deepcopy
from ruamel.yaml import YAML
import tempfile

from oriom.domain.Operations.InspectionSite import InspectionSite
from oriom.domain.Operations.InspectionPort import InspectionPort
from oriom.domain.Operations.CorrectiveMajor import CorrectiveMajor
from oriom.domain.Operations.CorrectiveMinor import CorrectiveMinor
from oriom.domain.Operations.OperationTow import OperationTow
from oriom.core.builders.DefineOperationTechs import Define_operation
from oriom.domain.Vessels.Vessel import Vessel
from oriom.domain.Vessels.RovDrone import RovDrone


class TestOperation(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        file_vessels=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels.yaml')
        file_vessels_fuels=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_fuels.yaml')
        file_vessels_loads=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_loads.yaml')
        file_vessels_densities=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_densities.yaml')
        self.op_inspect_site = InspectionSite(
                id_='ofw_OP1',
                name='Inspection_dummy',
                overnight_stay=False,
                periodicity=1,
                tech_per_device=3,
                tech_cost=200,
                dur_per_device=6.0,
                device_shutdown=True,
                level='device',
                vessel1_id='V001',
                rov_drone='stork_1',
                other_costs=1000
        )
        self.op_inspect_site.vessel1 = Vessel(
                id_='V001',
                type_='Multicat',
                speed_transit=3,
                power=500,
                daily_charter=4000,
                crew_capacity=3,
                overnight=False,
                file_vessels=file_vessels,
                file_fuel_cons=file_vessels_fuels,
                file_load_factor=file_vessels_loads,
                file_fuel_density=file_vessels_densities
        )
        self.op_inspect_site.rov_drone = RovDrone(
            id_='Stork_1',
            name='Stork',
            type_='aerial',
            daily_charter=1000
        )
        self.op_corr = CorrectiveMajor(
                id_='ofw_OP103',
                name='Corrective_dummy',
                tow_to_port=False,
                tech_required=3,
                tech_cost=300,
                other_costs=19000
        )
        self.op_tow_port = OperationTow(
                id_='ofw_removal_tow',
                name='WTG removal',
                tech_required=3,
                tech_cost=300,
                vessel1_id='V001',
                other_costs=19000
        )
        self.op_tow_site = OperationTow(
                id_='ofw_deploy_tow',
                name='WTG redeploy',
                tech_required=3,
                tech_cost=300,
                vessel1_id='V001',
                other_costs=1000
        )

        vessels_obj = Vessel.get_vessels_from_yaml(
                file_path = file_vessels,
                file_fuel_density = file_vessels_densities,
                file_fuel_cons = file_vessels_fuels,
                file_load_factor = file_vessels_loads
        )

        self.vessels = {ves.id: ves for ves in vessels_obj}


    def test_minimal(self):
        inspection_site_min = InspectionSite(
                id_='oce_OP_001',
                name='Inspection',
                overnight_stay=False,
                periodicity=2,
                tech_per_device=4,
                tech_cost=300,
                dur_per_device=4.0,
                device_shutdown=True,
                level='device',
                vessel1_id='V001'
        )
        self.assertEqual(inspection_site_min.months, list(range(1,13)))
        self.assertIsNone(inspection_site_min.vessel2_id)
        self.assertIsNone(inspection_site_min.rov_drone)
        self.assertEqual(inspection_site_min.other_costs, 0)

        self.assertEqual(inspection_site_min.intervened_wtg, 0)
        self.assertEqual(inspection_site_min.intervened_wec, 0)
        self.assertEqual(inspection_site_min.intervened_pv, 0)

        self.assertIsNone(inspection_site_min.vessel1)
        self.assertIsNone(inspection_site_min.vessel2)
        self.assertIsNone(inspection_site_min.hs)
        self.assertIsNone(inspection_site_min.tp)
        self.assertIsNone(inspection_site_min.ws)
        self.assertIsNone(inspection_site_min.ws_hub)
        self.assertIsNone(inspection_site_min.cs)

    def test_complete(self):
        inspection_site_full1 = InspectionSite(
                id_='ofw_OP_001',
                name='Inspection',
                overnight_stay=False,
                periodicity=2,
                tech_per_device=4,
                tech_cost=300,
                dur_per_device=6.0,
                device_shutdown=True,
                level='device',
                months='3, 4, 5',
                intervened_wtg=1,
                intervened_wec=2,
                intervened_pv=0,
                wave_height=2,
                wave_period=18,
                wind_speed=15,
                wind_speed_hub=20,
                current_speed=1.5,
                vessel1_id='V001',
                vessel2_id='V002',
                rov_drone='stork',
                other_costs=2000
        )
        self.assertIsInstance(inspection_site_full1.months, list)
        for month in inspection_site_full1.months:
                self.assertGreaterEqual(month, 1)
                self.assertLessEqual(month, 12)
        self.assertEqual(inspection_site_full1.hs, 2.0)
        self.assertEqual(inspection_site_full1.tp, 18.0)
        self.assertEqual(inspection_site_full1.ws, 15.0)
        self.assertEqual(inspection_site_full1.ws_hub, 20.0)
        self.assertEqual(inspection_site_full1.cs, 1.5)
        self.assertEqual(inspection_site_full1.parts_cost, 0)

        corrective_major_full = CorrectiveMajor(
                id_='ofw_OP_002',
                name='Replacement',
                tow_to_port=False,
                tech_required=5,
                tech_cost=600,
                months='5,6,7,8,9',
                vessel1_id='V003',
                vessel2_id='V004',
                other_costs=1000
        )
        self.assertListEqual(corrective_major_full.months, list(range(5, 10)))

    def test_conversion(self):
        operation = InspectionSite(
                id_='ofw_',
                name='Dummy',
                overnight_stay=False,
                periodicity='2',
                tech_per_device='3',
                tech_cost='300',
                dur_per_device='6',
                device_shutdown='1',
                level='device',
                vessel1_id=1,
                vessel2_id=2,
                months='03, 004, 05',
                other_costs='2000'
        )
        self.assertIsInstance(operation.id, str)
        self.assertEqual(operation.id, 'ofw_')
        self.assertIsInstance(operation.tech_per_device, int)
        self.assertEqual(operation.tech_per_device, 3)
        self.assertIsInstance(operation.tech_cost, float)
        self.assertEqual(operation.tech_cost, 300.0)
        self.assertIsInstance(operation.vessel1_id, str)
        self.assertEqual(operation.vessel1_id, '1')
        self.assertIsInstance(operation.vessel2_id, str)
        self.assertEqual(operation.vessel2_id, '2')
        self.assertIsInstance(operation.periodicity, float)
        self.assertEqual(operation.periodicity, 2.0)
        self.assertIsInstance(operation.device_shutdown, bool)
        self.assertEqual(operation.device_shutdown, True)
        self.assertIsInstance(operation.months, list)
        self.assertEqual(operation.months, [3, 4, 5])
        self.assertIsInstance(operation.other_costs, float)
        self.assertEqual(operation.other_costs, 2000.0)

        operation = CorrectiveMajor(
                id_='owc_',
                name='Dummy',
                tow_to_port=False,
                tech_required='4',
                tech_cost='500',
                vessel1_id=1,
        )
        self.assertIsInstance(operation.tech_required, int)
        self.assertEqual(operation.tech_required, 4)
        self.assertIsInstance(operation.tech_cost, float)
        self.assertEqual(operation.tech_cost, 500.0)

    def test_define_rovs(self):
        op_dummy = InspectionSite(
                id_='oce_',
                name='Dummy',
                overnight_stay=False,
                periodicity=2,
                tech_per_device=3,
                tech_cost=300,
                dur_per_device=6,
                device_shutdown=True,
                level='device',
                vessel1_id='V002',
                rov_drone='stork_1'
        )
        rovs_drones = RovDrone.get_rovdrones_from_yaml(
                file_path=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'rovs.yaml')
        )
        Define_operation.define_rovs(
                operation=op_dummy,
                rovs_drones=rovs_drones,
        )
        self.assertEqual(op_dummy.rov_drone.type, 'aerial')
        self.assertEqual(op_dummy.rov_drone.daily_charter, 4920)
        self.assertIsNone(op_dummy.rov_drone.battery_capacity)
        self.assertEqual(op_dummy.rov_drone.nr_technicians, 1)
        self.assertEqual(op_dummy.rov_drone.ws_max, 10)
        self.assertIsNone(op_dummy.rov_drone.hs_max)

    def test_define_vessels(self):
        # Only 1 vessel
        op_dummy = InspectionSite(
                id_='ofw_',
                name='Dummy',
                overnight_stay=False,
                periodicity=2,
                tech_per_device=3,
                tech_cost=300,
                dur_per_device=6,
                device_shutdown=True,
                level='device',
                vessel1_id='V002'
        )
        Define_operation.define_vessels(
                operation=op_dummy,
                file_vessels=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels.yaml'),
                file_fuel_cons=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_fuels.yaml'),
                file_load_factor=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_loads.yaml'),
                file_fuel_density=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_densities.yaml'),
                vessels = self.vessels
        )
        self.assertEqual(op_dummy.vessel1.type, 'multicat')
        self.assertEqual(op_dummy.vessel1.speed_transit, 4)
        self.assertIsNone(op_dummy.vessel1.speed_tow)
        self.assertEqual(op_dummy.vessel1.charter, 3000)
        self.assertEqual(op_dummy.vessel1.power, 350)
        self.assertIsNone(op_dummy.vessel2)

        # 2 vessels
        op_dummy.vessel2_id = 'v003'
        Define_operation.define_vessels(
                operation=op_dummy,
                file_vessels=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels.yaml'),
                file_fuel_cons=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_fuels.yaml'),
                file_load_factor=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_loads.yaml'),
                file_fuel_density=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_densities.yaml'),
                vessels = self.vessels
        )
        self.assertEqual(op_dummy.vessel2.type, 'ahts')
        self.assertEqual(op_dummy.vessel2.speed_transit, 5)
        self.assertEqual(op_dummy.vessel2.speed_tow, 2)
        self.assertEqual(op_dummy.vessel2.charter, 4500)
        self.assertEqual(op_dummy.vessel2.power, 750)

        # Errors
        op_dummy.vessel1_id = 'vwfew'
        self.assertRaises(
                IndexError,
                Define_operation.define_vessels,
                op_dummy,
                os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels.yaml'),
                os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_fuels.yaml'),
                os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_loads.yaml'),
                os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_densities.yaml'),
                self.vessels
        )
        op_dummy.vessel1_id = 'v003'
        op_dummy.vessel2_id = 'vwfew'
        self.assertRaises(
                IndexError,
                Define_operation.define_vessels,
                op_dummy,
                os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels.yaml'),
                os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_fuels.yaml'),
                os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_loads.yaml'),
                os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_densities.yaml'),
                self.vessels
        )


    def test_get_inspection_operations_from_yaml(self):
        file_path = os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'operations_inspections_site.yaml')

        operations = InspectionSite.get_inspections_from_yaml(file_path)
        self.assertEqual(operations[0].periodicity, 0.5)
        self.assertIsNone(operations[0].vessel2_id)

        # self.assertEqual(operations[6].rov_id, 'stork_1 - Stork (Aerial)')

        self.assertEqual(operations[11].months, list(range(1,13)))

        self.assertEqual(operations[12].intervened_wtg, 3)
        self.assertEqual(operations[12].intervened_wec, 10)


    def test_get_corrective_operations_from_yaml(self):
        file_path = os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'operations_corrective_major.yaml')

        operations = CorrectiveMajor.get_operations_from_yaml(
                file_path=file_path,
                towing_operations=[self.op_tow_port, self.op_tow_site]
        )

        self.assertEqual(operations[0].months, list(range(1,13)))
        self.assertIn('v003', operations[0].vessel1_id)
        self.assertIsNone(operations[0].vessel2_id)

        self.assertEqual(operations[1].months, list(range(1,13)))
        self.assertIsNone(operations[1].vessel1_id)
        self.assertIsNone(operations[1].vessel2_id)

        self.assertEqual(operations[2].months, list(range(1,13)))
        self.assertIsNone(operations[2].vessel2_id)

    @skip
    def test_get_failures(self):
        file_path = os.path.join(os.getcwd(), 'tests', 'test_files', 'failures_dummy.csv')
        operation = deepcopy(self.op_corr)
        operation.id = 'ofw_op103'
        operation.define_months_operations(
                failures_path=file_path
        )
        self.assertEqual(operation.months, [1, 2, 11, 12])

        operation.id = 'other'
        self.assertRaises(KeyError, operation.define_months_corrective_operations, file_path)
        self.assertRaises(TypeError, self.op_inspect_site.define_months_corrective_operations, None)


    def test_errors(self):
        args_default_inspection_site = {
                'id_': 'ofw_',
                'name': 'dummy_name',
                'overnight_stay': False,
                'periodicity': 2,
                'tech_per_device': 3,
                'tech_cost': 300,
                'dur_per_device': 6.0,
                'device_shutdown': True,
                'level' : 'device',
                'months': None,
                'intervened_wtg': None,
                'intervened_wec': None,
                'intervened_pv': None,
                'wave_height': 2.0,
                'wave_period': 18.0,
                'wind_speed': 15.0,
                'current_speed': 1.5,
                'vessel1_id': 'V001',
                'vessel2_id': None,
                'other_costs': 0
        }
        args = deepcopy(args_default_inspection_site)
        args["periodicity"] = 0
        self.assertRaises(ValueError, InspectionSite, **args)
        args = deepcopy(args_default_inspection_site)
        args["tech_per_device"] = 0
        self.assertRaises(ValueError, InspectionSite, **args)
        args = deepcopy(args_default_inspection_site)
        args["tech_cost"] = -0.1
        self.assertRaises(ValueError, InspectionSite, **args)
        args = deepcopy(args_default_inspection_site)
        args["dur_per_device"] = 0
        self.assertRaises(ValueError, InspectionSite, **args)
        args = deepcopy(args_default_inspection_site)
        args["months"] = '0, 1'
        self.assertRaises(NameError, InspectionSite, **args)
        args["months"] = '12, 13'
        self.assertRaises(NameError, InspectionSite, **args)
        args = deepcopy(args_default_inspection_site)
        args["intervened_wtg"] = -1
        self.assertRaises(ValueError, InspectionSite, **args)
        args = deepcopy(args_default_inspection_site)
        args["intervened_wec"] = -1
        self.assertRaises(ValueError, InspectionSite, **args)
        args = deepcopy(args_default_inspection_site)
        args["intervened_pv"] = -1
        self.assertRaises(ValueError, InspectionSite, **args)
        args = deepcopy(args_default_inspection_site)
        args["wave_height"] = -0.1
        self.assertRaises(ValueError, InspectionSite, **args)
        args = deepcopy(args_default_inspection_site)
        args["wave_period"] = -0.1
        self.assertRaises(ValueError, InspectionSite, **args)
        args = deepcopy(args_default_inspection_site)
        args["wind_speed"] = -0.1
        self.assertRaises(ValueError, InspectionSite, **args)
        args = deepcopy(args_default_inspection_site)
        args["current_speed"] = -0.1
        self.assertRaises(ValueError, InspectionSite, **args)
        args = deepcopy(args_default_inspection_site)
        args["parts_cost"] = -0.1
        self.assertRaises(ValueError, InspectionSite, **args)
        args = deepcopy(args_default_inspection_site)
        args["other_costs"] = -0.1
        self.assertRaises(ValueError, InspectionSite, **args)

        args_default_corrective = {
                'id_': 'ofw_id',
                'name': 'dummy_name',
                'tow_to_port': False,
                'tech_required': 4,
                'tech_cost': 500,
                'months': None,
                'vessel1_id': 'V002',
                'vessel2_id': None,
                'other_costs': 2000,
                'towing_ops': None
        }
        args = deepcopy(args_default_corrective)
        args["tow_to_port"] = True
        self.assertRaises(ValueError, CorrectiveMajor, **args)
        args = deepcopy(args_default_corrective)
        args = deepcopy(args_default_corrective)
        args["other_costs"] = -0.1
        self.assertRaises(ValueError, CorrectiveMajor, **args)

class FakeFailure:
    """Simple helper class to mimic a Failure object."""
    def __init__(self, operation_triggered, maintenance_strategy, preferred_month=None):
        self.operation_triggered = operation_triggered
        self.maintenance_strategy = maintenance_strategy
        self.preferred_month = preferred_month


class FakeVessel:
    """Simple helper class to mimic a Vessel object."""
    def __init__(self, _id, n_vessels):
        self.id = _id
        self.n_vessels = n_vessels


class FakeRovDrone:
    """Simple helper class to mimic a Rov/Drone object."""
    def __init__(self, _id):
        self.id = _id


class TestCorrectiveMinor(unittest.TestCase):
    # ------------------------------------------------------------------ #
    # __init__ and _check_attributes basic behaviour
    # ------------------------------------------------------------------ #
    def test_init_valid_minimal_and_defaults(self):
        """Constructor must correctly set basic attributes for a valid operation."""
        op = CorrectiveMinor(
            id_="ofw001",
            name="Minor corrective op",
            duration_net=4.0,
            device_shutdown=True,
            level="device",
            tech_required=2,
            vessel1_id="CTV1",
            tech_wtg=True,
            month=5,
        )

        self.assertEqual(op.id, "ofw001")
        self.assertEqual(op.name, "Minor corrective op")
        self.assertEqual(op.duration_net, 4.0)
        self.assertTrue(op.device_shutdown)
        self.assertEqual(op.level, "device")
        self.assertEqual(op.tech_required, 2)
        self.assertEqual(op.vessel1_id, "ctv1")  # lower-cased
        self.assertEqual(op.months, [5])
        self.assertEqual(op.technology, "wtg")
        self.assertIsNone(op.hs)
        self.assertIsNone(op.ws)

    def test_init_default_months_when_month_is_none(self):
        """
        When 'month' is None, all months (1-12) must be considered.
        """
        op = CorrectiveMinor(
            id_="ofw002",
            name="Op no month",
            duration_net=2.0,
            device_shutdown=False,
            level="device",
            tech_required=1,
            vessel1_id="CTV1",
        )

        self.assertEqual(op.months, list(range(1, 13)))

    def test_init_raises_if_more_than_one_technology_defined(self):
        """
        If more than one technology flag is True, constructor must raise ValueError.
        """
        with self.assertRaises(ValueError):
            CorrectiveMinor(
                id_="ofw003",
                name="Invalid tech",
                duration_net=3.0,
                device_shutdown=True,
                level="device",
                tech_required=1,
                vessel1_id="CTV1",
                tech_wtg=True,
                tech_wec=True,  # second technology → error
            )

    def test_check_attributes_invalid_prefix_raises(self):
        """Prefix must be ofw/owc/opv, otherwise ValueError."""
        with self.assertRaises(ValueError) as cm:
            CorrectiveMinor(
                id_="xxx001",  # invalid prefix
                name="Invalid prefix",
                duration_net=3.0,
                device_shutdown=True,
                level="device",
                tech_required=1,
                vessel1_id="CTV1",
            )
        self.assertIn("prefix not recognized", str(cm.exception))

    def test_check_attributes_invalid_level_raises(self):
        """Level must be one of the defined allowed values."""
        with self.assertRaises(ValueError) as cm:
            CorrectiveMinor(
                id_="ofw010",
                name="Invalid level",
                duration_net=3.0,
                device_shutdown=True,
                level="invalid_level",
                tech_required=1,
                vessel1_id="CTV1",
            )
        self.assertIn('"level" must be', str(cm.exception))

    def test_check_attributes_negative_duration_raises(self):
        """Negative duration_net must raise ValueError."""
        with self.assertRaises(ValueError) as cm:
            CorrectiveMinor(
                id_="ofw011",
                name="Neg duration",
                duration_net=-1.0,
                device_shutdown=True,
                level="device",
                tech_required=1,
                vessel1_id="CTV1",
            )
        self.assertIn('"duration_net" must be positive', str(cm.exception))

    # ------------------------------------------------------------------ #
    # Light flag parsing
    # ------------------------------------------------------------------ #
    def test_light_parsing_boolean_numeric_and_string(self):
        """Light flag must correctly parse bool, numeric and string representations."""
        # Direct booleans
        op_true = CorrectiveMinor(
            id_="ofw020",
            name="Light true",
            duration_net=1.0,
            device_shutdown=False,
            level="device",
            tech_required=1,
            vessel1_id="CTV1",
            light=True,
        )
        self.assertTrue(op_true.light)

        op_false = CorrectiveMinor(
            id_="ofw021",
            name="Light false",
            duration_net=1.0,
            device_shutdown=False,
            level="device",
            tech_required=1,
            vessel1_id="CTV1",
            light=False,
        )
        self.assertFalse(op_false.light)

        # Numeric 1.0 / 0.0
        op_num_true = CorrectiveMinor(
            id_="ofw022",
            name="Light numeric true",
            duration_net=1.0,
            device_shutdown=False,
            level="device",
            tech_required=1,
            vessel1_id="CTV1",
            light=1.0,
        )
        self.assertTrue(op_num_true.light)

        op_num_false = CorrectiveMinor(
            id_="ofw023",
            name="Light numeric false",
            duration_net=1.0,
            device_shutdown=False,
            level="device",
            tech_required=1,
            vessel1_id="CTV1",
            light=0.0,
        )
        self.assertFalse(op_num_false.light)

        # String values (parsed via strtobool)
        op_str_true = CorrectiveMinor(
            id_="ofw024",
            name="Light string true",
            duration_net=1.0,
            device_shutdown=False,
            level="device",
            tech_required=1,
            vessel1_id="CTV1",
            light="true",
        )
        self.assertTrue(op_str_true.light)

        op_str_false = CorrectiveMinor(
            id_="ofw025",
            name="Light string false",
            duration_net=1.0,
            device_shutdown=False,
            level="device",
            tech_required=1,
            vessel1_id="CTV1",
            light="False",
        )
        self.assertFalse(op_str_false.light)

    def test_light_invalid_string_raises(self):
        """
        Invalid light string must raise an exception.

        Note: implementation currently uses an undefined variable _e in the raise,
        so we accept any Exception here, not strictly ValueError.
        """
        with self.assertRaises(Exception):
            CorrectiveMinor(
                id_="ofw026",
                name="Light invalid",
                duration_net=1.0,
                device_shutdown=False,
                level="device",
                tech_required=1,
                vessel1_id="CTV1",
                light="not_a_bool",
            )

    # ------------------------------------------------------------------ #
    # get_operations_from_yaml
    # ------------------------------------------------------------------ #
    def test_get_operations_from_yaml_success(self):
        """get_operations_from_yaml must build a list of CorrectiveMinor from a YAML file."""
        yaml_data = [
            {
                "ID": "OFW100",  # mixed case
                "Name": "Minor from YAML",
                "duration_net": 4.0,
                "device_shutdown": True,
                "vessel1_id": "CTV1",
                "vessel1_qt": 1,
                "tech_required": 2,
                "level": "device",
                # some optional keys
                "tech_wtg": True,
                "wave_height": 2.0,
                "light": "true",
            }
        ]

        yaml_obj = YAML()
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = os.path.join(tmpdir, "ops.yaml")
            with open(yaml_path, "w") as f:
                yaml_obj.dump(yaml_data, f)

            ops = CorrectiveMinor.get_operations_from_yaml(yaml_path)

            self.assertEqual(len(ops), 1)
            op = ops[0]
            self.assertIsInstance(op, CorrectiveMinor)
            self.assertEqual(op.id, "ofw100")  # lower case
            self.assertEqual(op.name, "Minor from YAML")
            self.assertEqual(op.duration_net, 4.0)
            self.assertEqual(op.tech_required, 2)
            self.assertEqual(op.level, "device")
            self.assertEqual(op.vessel1_id, "ctv1")
            self.assertEqual(op.vessel1_qt, 1)
            self.assertEqual(op.technology, "wtg")
            self.assertEqual(op.hs, 2.0)
            self.assertTrue(op.light)

    def test_get_operations_from_yaml_missing_mandatory_keys_raises(self):
        """Missing mandatory keys in YAML entries must raise KeyError."""
        yaml_data = [
            {
                # "id" intentionally missing
                "name": "Missing id",
                "duration_net": 4.0,
                "device_shutdown": True,
                "vessel1_id": "CTV1",
                "tech_required": 2,
                "level": "device",
            }
        ]

        yaml_obj = YAML()
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = os.path.join(tmpdir, "ops_bad.yaml")
            with open(yaml_path, "w") as f:
                yaml_obj.dump(yaml_data, f)

            with self.assertRaises(KeyError):
                CorrectiveMinor.get_operations_from_yaml(yaml_path)


    # ------------------------------------------------------------------ #
    # to_yaml
    # ------------------------------------------------------------------ #
class FakeFailure_id:
    """Simple helper class to mimic a Failure object."""
    def __init__(self, id_):
        self.id = id_

    def test_to_yaml_writes_attributes_file_with_expected_structure(self):
        """to_yaml must write attributes.yaml with the correct keys and values."""
        op = CorrectiveMinor(
            id_="ofw060",
            name="To YAML",
            duration_net=3.0,
            device_shutdown=True,
            level="device",
            tech_required=2,
            vessel1_id="CTV1",
            vessel1_qt=2,
            vessel2_id="support1",
            vessel2_qt=1,
            tech_cost=500.0,
            wave_height=2.5,
            wave_period=8.0,
            wind_speed=15.0,
            wind_speed_hub=18.0,
            current_speed=1.0,
            light=True,
            other_costs=500.0,
        )

        # Attach vessel objects and rov/drone
        op.vessel1 = FakeVessel("ctv1", 2)
        op.vessel2 = FakeVessel("support1", 1)
        op.rov_drone = FakeRovDrone("rov1")
        op.technology = "wtg"
        op.failures = [FakeFailure_id(id_="dummy_failure_1")]

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
                "duration_net",
                "device_shutdown",
                "level",
                "months",
                "technology",
                "tech_required",
                "tech_cost",
                "hs",
                "tp",
                "ws",
                "ws_hub",
                "cs",
                "light",
                "vessel1",
                "vessel2",
                "other_costs",
                "rov_drone",
                "double_shift",
                "failures",
            ]:
                self.assertIn(key, data, f"Key {key} must be present in attributes.yaml")

            self.assertEqual(data["id"], "ofw060")
            self.assertEqual(data["name"], "To YAML")
            self.assertEqual(data["duration_net"], 3.0)
            self.assertEqual(data["level"], "device")
            self.assertEqual(data["tech_required"], 2)
            self.assertEqual(data["tech_cost"], 500.0)
            self.assertEqual(data["hs"], 2.5)
            self.assertEqual(data["tp"], 8.0)
            self.assertEqual(data["ws"], 15.0)
            self.assertEqual(data["ws_hub"], 18.0)
            self.assertEqual(data["cs"], 1.0)
            self.assertTrue(data["light"])
            self.assertEqual(data["other_costs"], 500.0)
            self.assertEqual(data["technology"], "wtg")
            self.assertEqual(data["failures"], ["dummy_failure_1"])

            # Vessel 1 and 2 should be dictionaries with id and number
            self.assertEqual(data["vessel1"]["id"], "ctv1")
            self.assertEqual(data["vessel1"]["number"], 2)
            self.assertEqual(data["vessel2"]["id"], "support1")
            self.assertEqual(data["vessel2"]["number"], 1)

            # Rov/drone should be written as its id
            self.assertEqual(data["rov_drone"], "rov1")


if __name__ == "__main__":
    unittest.main(verbosity=2)

