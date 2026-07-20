import unittest
import os
from copy import deepcopy

from oriom.domain.Techs.WindTurbineGenerator import WindTurbineGenerator


class TestWindTurbineGenerator(unittest.TestCase):
        @classmethod
        def setUpClass(self):
                self.yaml_file = os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'wtg.yaml')

        def test_init(self):
                wtg = WindTurbineGenerator(
                        number_devices=10,
                        rated_power=8,
                        cut_in=3,
                        cut_off=25,
                        hub_height=100,
                        pcurve_file=os.path.join(
                                os.getcwd(),
                                'tests',
                                'test_files',
                                'pcurve_wind.csv'
                        ),
                        moorings=3,
                        number_strings=1,
                        n_string_to_connector=1
                )
                self.assertIsInstance(wtg.number_devices, int)
                self.assertEqual(wtg.number_devices, 10)
                self.assertIsInstance(wtg.rated_power, float)
                self.assertEqual(wtg.rated_power, 8)
                self.assertIsInstance(wtg.cut_in, float)
                self.assertEqual(wtg.cut_in, 3.0)
                self.assertIsInstance(wtg.cut_off, float)
                self.assertEqual(wtg.cut_off, 25.0)
                self.assertIsInstance(wtg.hub_height, float)
                self.assertEqual(wtg.hub_height, 100.0)
                self.assertIsInstance(wtg.pcurve_file, str)
                self.assertIsInstance(wtg.moorings, int)
                self.assertEqual(wtg.moorings, 3)
                self.assertIsInstance(wtg.number_strings, int)
                self.assertEqual(wtg.number_strings, 1)
                self.assertIsInstance(wtg.wtg_layout, int)
                self.assertEqual(wtg.wtg_layout, 1)
                self.assertEqual(wtg.number_substations, 1)
                self.assertEqual(wtg.number_exportcables, 1)
                self.assertEqual(wtg.spacing, 1.650)

        def test_conversions(self):
                wtg = WindTurbineGenerator(
                        number_devices=10,
                        rated_power=8,
                        cut_in=3,
                        cut_off=25,
                        hub_height=100,
                        number_strings=1,
                        pcurve_file=os.path.join(
                                os.getcwd(),
                                'tests',
                                'test_files',
                                'pcurve_wind.csv'
                        )
                )
                self.assertIsInstance(wtg.number_devices, int)
                self.assertEqual(wtg.number_devices, 10)
                self.assertIsInstance(wtg.rated_power, float)
                self.assertEqual(wtg.rated_power, 8)
                self.assertIsInstance(wtg.cut_in, float)
                self.assertEqual(wtg.cut_in, 3.0)
                self.assertIsInstance(wtg.cut_off, float)
                self.assertEqual(wtg.cut_off, 25.0)
                self.assertIsInstance(wtg.hub_height, float)
                self.assertEqual(wtg.hub_height, 100.0)
                self.assertIsInstance(wtg.pcurve_file, str)
                self.assertIsInstance(wtg.moorings, int)
                self.assertEqual(wtg.moorings, 0)
                self.assertIsInstance(wtg.wtg_layout, int)
                self.assertEqual(wtg.wtg_layout, 1)
                self.assertEqual(wtg.number_substations, 1)
                self.assertEqual(wtg.number_exportcables, 1)
                self.assertEqual(wtg.spacing, 1.650)
        def test_errors(self):
                args_def = {
                        'number_devices': 10,
                        'rated_power': 8,
                        'cut_in': 3,
                        'cut_off': 25,
                        'hub_height': 100,
                        'pcurve_file': os.path.join(
                                os.getcwd(),
                                'tests',
                                'test_files',
                                'pcurve_wind.csv'
                        ),
                        'moorings': 3,
                        'number_strings': 1
                }

                args = deepcopy(args_def)
                args["rated_power"] = 0
                self.assertRaises(ValueError, WindTurbineGenerator, **args)

                args = deepcopy(args_def)
                args["cut_in"] = -0.1
                self.assertRaises(ValueError, WindTurbineGenerator, **args)

                args = deepcopy(args_def)
                args["cut_off"] = 0
                self.assertRaises(ValueError, WindTurbineGenerator, **args)

                args = deepcopy(args_def)
                args["cut_in"] = 3.0
                args["cut_off"] = 3.0
                self.assertRaises(ValueError, WindTurbineGenerator, **args)

                args = deepcopy(args_def)
                args["hub_height"] = 0
                self.assertRaises(ValueError, WindTurbineGenerator, **args)

                args = deepcopy(args_def)
                args["pcurve_file"] = 'other_file'
                self.assertRaises(ValueError, WindTurbineGenerator, **args)

                args = deepcopy(args_def)
                args["pcurve_file"] = 'other_file.csv'
                self.assertRaises(FileNotFoundError, WindTurbineGenerator, **args)

                args = deepcopy(args_def)
                args["moorings"] = -1
                self.assertRaises(ValueError, WindTurbineGenerator, **args)

                args = deepcopy(args_def)
                args["number_devices"] = 20
                args["number_strings"] = 3
                self.assertRaises(ValueError, WindTurbineGenerator, **args)

                args = deepcopy(args_def)
                args["spacing"] = -10
                self.assertRaises(ValueError, WindTurbineGenerator, **args)

        def test_default_values(self):
                wtg = WindTurbineGenerator(
                        number_devices=10,
                        rated_power=8,
                        cut_in=3,
                        cut_off=25,
                        hub_height=100,
                        pcurve_file=os.path.join(
                                os.getcwd(),
                                'tests',
                                'test_files',
                                'pcurve_wind.csv'
                        ),
                        moorings=3,
                        number_strings=1
                )
                self.assertEqual(wtg.number_substations, 1)
                self.assertEqual(wtg.number_exportcables, 1)
                self.assertEqual(wtg.wtg_layout, 1)
                self.assertEqual(wtg.moorings, 3)
                self.assertEqual(wtg.spacing, 1.650)

        def test_yaml(self):
                wtg = WindTurbineGenerator.get_wtg_from_yaml(self.yaml_file)
                self.assertIsInstance(wtg.number_devices, int)
                self.assertEqual(wtg.number_devices, 40)
                self.assertEqual(wtg.rated_power, 8.3)
                self.assertIsInstance(wtg.pcurve_file, str)
                self.assertIsInstance(wtg.cut_in, float)
                self.assertEqual(wtg.hub_height, 200.0)
                self.assertEqual(wtg.moorings, 3)
                self.assertEqual(wtg.spacing, 1.650)

if __name__ == '__main__':
        unittest.main()
