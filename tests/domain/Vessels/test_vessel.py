import unittest
import os
from copy import deepcopy
from unittest import skip

from oriom.domain.Vessels.Vessel import Vessel


class TestVessel(unittest.TestCase):
    def test_init(self):
        # Test without file_consumption_path and fuel parameters
        args_def = {
                'id_': 'id',
                'type_': 'preventive',
                'speed_transit': 3,
                'power': 300,
                'daily_charter': 1000,
                'crew_capacity': 3,
                'overnight' : False
        }
        args = deepcopy(args_def)
        self.assertRaises(ValueError, Vessel, **args)

        # Test minimal
        vessel_min = Vessel(
                id_='V001',
                type_='CTV',
                speed_transit=3,
                daily_charter=1000,
                crew_capacity=3,
                overnight=False,
                file_vessels=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels.yaml'),
                file_fuel_cons=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_fuels.yaml'),
                file_fuel_density=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_densities.yaml'),
                file_load_factor=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_loads.yaml')
        )
        self.assertIsInstance(vessel_min.id, str)
        self.assertEqual(vessel_min.id, 'v001')
        self.assertIsInstance(vessel_min.type, str)
        self.assertEqual(vessel_min.type, 'ctv')
        self.assertIsInstance(vessel_min.speed_transit, float)
        self.assertEqual(vessel_min.speed_transit, 3.0)
        self.assertAlmostEqual(vessel_min.power, 1431, 0)
        self.assertIsInstance(vessel_min.charter, float)
        self.assertEqual(vessel_min.charter, 1000.0)
        self.assertIsInstance(vessel_min.crew_capacity, int)
        self.assertEqual(vessel_min.crew_capacity, 3)
        self.assertIsInstance(vessel_min.crew_berths, int)
        self.assertEqual(vessel_min.crew_berths, 0)
        self.assertIsNone(vessel_min.speed_tow)
        self.assertIsInstance(vessel_min.fuel_cons_transit, float)
        self.assertAlmostEqual(vessel_min.fuel_cons_transit, 238, 0)
        self.assertIsInstance(vessel_min.fuel_cons_maneuver, float)
        self.assertAlmostEqual(vessel_min.fuel_cons_maneuver, 119, 0)
        self.assertIsInstance(vessel_min.fuel_cons_standby, float)
        self.assertAlmostEqual(vessel_min.fuel_cons_standby, 60, 0)
        self.assertEqual(vessel_min.annual_contract, 0)


        # Test full
        vessel_full = Vessel(
                id_='V002',
                type_='Tug',
                speed_transit='3',
                speed_tow='1',
                power='300',
                daily_charter='1200',
                crew_capacity=10,
                overnight=False,
                crew_berths=6,
                fuel_type='hfo',
                density='1010',
                fuel_cons_transit='320',
                fuel_cons_maneuver='120',
                fuel_cons_standby='50'
        )
        self.assertIsInstance(vessel_full.id, str)
        self.assertEqual(vessel_full.id, 'v002')
        self.assertIsInstance(vessel_full.type, str)
        self.assertEqual(vessel_full.type, 'tug')
        self.assertIsInstance(vessel_full.speed_transit, float)
        self.assertEqual(vessel_full.speed_transit, 3.0)
        self.assertIsInstance(vessel_full.speed_tow, float)
        self.assertEqual(vessel_full.speed_tow, 1.0)
        self.assertIsInstance(vessel_full.power, float)
        self.assertEqual(vessel_full.power, 300.0)
        self.assertIsInstance(vessel_full.charter, float)
        self.assertEqual(vessel_full.charter, 1200.0)
        self.assertIsInstance(vessel_full.crew_capacity, int)
        self.assertEqual(vessel_full.crew_capacity, 10)
        self.assertIsInstance(vessel_full.crew_berths, int)
        self.assertEqual(vessel_full.crew_berths, 6)
        self.assertIsInstance(vessel_full.fuel_type, str)
        self.assertEqual(vessel_full.fuel_type, 'hfo')
        self.assertIsInstance(vessel_full.fuel_cons_transit, float)
        self.assertEqual(vessel_full.fuel_cons_transit, 320.0)
        self.assertIsInstance(vessel_full.fuel_cons_maneuver, float)
        self.assertEqual(vessel_full.fuel_cons_maneuver, 120)
        self.assertIsInstance(vessel_full.fuel_cons_standby, float)
        self.assertEqual(vessel_full.fuel_cons_standby, 50)
        self.assertIsInstance(vessel_full.density, float)
        self.assertEqual(vessel_full.density, 1010)

    def test_get_vessel_fuel_consumption(self):
        vessel_ctv = Vessel(
                id_='V001',
                type_='CTV',
                speed_transit=3,
                power=None,
                daily_charter=1000,
                crew_capacity=3,
                overnight=False,
                file_vessels=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels.yaml'),
                file_fuel_cons=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_fuels.yaml'),
                file_fuel_density=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_densities.yaml'),
                file_load_factor=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_loads.yaml')
        )
        self.assertEqual(vessel_ctv.fuel_type, 'hfo')

    def test_get_fuel_density(self):
        vessel_ctv = Vessel(
                id_='V001',
                type_='CTV',
                crew_capacity=8,
                overnight=False,
                speed_transit=3,
                power=None,
                daily_charter=1000,
                file_vessels=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels.yaml'),
                file_fuel_cons=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_fuels.yaml'),
                file_fuel_density=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_densities.yaml'),
                file_load_factor=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_loads.yaml')
        )

        self.assertEqual(vessel_ctv.density, 1010)

    def test_calc_vessel_fuel_cons(self):
        vessel_ctv = Vessel(
                id_='V001',
                type_='CTV',
                speed_transit=3,
                daily_charter=1000,
                crew_capacity=3,
                overnight=False,
                power = 300,
                file_vessels=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels.yaml'),
                file_fuel_cons=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_fuels.yaml'),
                file_fuel_density=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_densities.yaml'),
                file_load_factor=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_loads.yaml')
        )
        self.assertAlmostEqual(vessel_ctv.fuel_cons_transit, 49.90, 2)
        self.assertAlmostEqual(vessel_ctv.fuel_cons_maneuver, 24.95, 2)
        self.assertAlmostEqual(vessel_ctv.fuel_cons_standby, 12.48, 2)

    def test_errors(self):
        vessels_file = os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels.yaml')
        fuel_cons_file=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_fuels.yaml')
        load_factor_file=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_loads.yaml')
        fuel_density_file=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_densities.yaml')

        args_def = {
                'id_': 'V001',
                'type_': 'CTV',
                'speed_transit': 3,
                'daily_charter': 1000,
                'crew_capacity': 3,
                'overnight': False,
                'power': 300,
                'density': 860,
                'speed_tow': 1,
                'fuel_type': 'mdo',
                'fuel_cons_transit': 300,
                'fuel_cons_maneuver': 100,
                'fuel_cons_standby': 80,
                'file_vessels': vessels_file,
                'file_fuel_cons': fuel_cons_file,
                'file_load_factor': load_factor_file,
                'file_fuel_density': fuel_density_file
        }

        args = deepcopy(args_def)
        args["speed_transit"] = -1
        self.assertRaises(ValueError, Vessel, **args)

        args = deepcopy(args_def)
        args["daily_charter"] = -1
        self.assertRaises(ValueError, Vessel, **args)

        args = deepcopy(args_def)
        args["crew_capacity"] = 0
        self.assertRaises(ValueError, Vessel, **args)

        args = deepcopy(args_def)
        args["crew_berths"] = -1
        self.assertRaises(ValueError, Vessel, **args)

        args = deepcopy(args_def)
        args["power"] = 0
        self.assertRaises(ValueError, Vessel, **args)

        args = deepcopy(args_def)
        args["speed_tow"] = 0
        self.assertRaises(ValueError, Vessel, **args)

        args = deepcopy(args_def)
        args["speed_transit"] = -1
        self.assertRaises(ValueError, Vessel, **args)

        args = deepcopy(args_def)
        args["daily_charter"] = -1
        self.assertRaises(ValueError, Vessel, **args)

        args = deepcopy(args_def)
        args["power"] = None
        args["fuel_cons_transit"] = -1
        self.assertRaises(ValueError, Vessel, **args)

        args = deepcopy(args_def)
        args["power"] = None
        args["fuel_cons_maneuver"] = -1
        self.assertRaises(ValueError, Vessel, **args)

        args = deepcopy(args_def)
        args["power"] = None
        args["fuel_cons_standby"] = -1
        self.assertRaises(ValueError, Vessel, **args)

        args = deepcopy(args_def)
        args["fuel_type"] = None
        args["file_fuel_cons"] = 'other_file_name'
        self.assertRaises(FileNotFoundError, Vessel, **args)

        args = deepcopy(args_def)
        args["fuel_cons_transit"] = None
        args["file_load_factor"] = 'other_file_name'
        self.assertRaises(FileNotFoundError, Vessel, **args)

        args = deepcopy(args_def)
        args["fuel_cons_transit"] = None
        args["file_load_factor"] = deepcopy(args_def["file_load_factor"])
        args["file_fuel_density"] = 'other_file_name'
        self.assertRaises(FileNotFoundError, Vessel, **args)


if __name__ == '__main__':
    unittest.main()
