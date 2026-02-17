import unittest
import os
from copy import deepcopy

from oriom.classes.WaveEnergyConverter import WaveEnergyConverter


 
class TestWaceEnergyConverter(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.yaml_file = os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'wec.yaml')

    def test_init(self):
        wec = WaveEnergyConverter(
                number_devices=10,
                rated_power=300,
                pmatrix_file=os.path.join(
                        os.getcwd(),
                        'tests',
                        'test_files',
                        'pmatrix_wave.csv'
                ),
                number_strings=2
        )
        self.assertIsInstance(wec.number_devices, int)
        self.assertEqual(wec.number_devices, 10)
        self.assertIsInstance(wec.rated_power, float)
        self.assertEqual(wec.rated_power, 300)
        self.assertIsInstance(wec.pmatrix_file, str)
        self.assertIsInstance(wec.number_strings, int)
        self.assertEqual(wec.number_strings, 2)

    def test_conversions(self):
        wec = WaveEnergyConverter(
                number_devices=10,
                rated_power=300,
                number_strings=2,
                pmatrix_file=os.path.join(
                        os.getcwd(),
                        'tests',
                        'test_files',
                        'pmatrix_wave.csv'
                )
        )
        self.assertIsInstance(wec.number_devices, int)
        self.assertEqual(wec.number_devices, 10)
        self.assertIsInstance(wec.rated_power, float)
        self.assertEqual(wec.rated_power, 300)
        self.assertIsInstance(wec.pmatrix_file, str)
        self.assertIsInstance(wec.number_strings, int)
        self.assertEqual(wec.number_strings, 2)
        self.assertIsInstance(wec.wec_layout, int)
        self.assertEqual(wec.wec_layout, 1)
        self.assertEqual(wec.number_substations,1)
        self.assertEqual(wec.number_exportcables,1)

    def test_errors(self):
        args_def = {
                'number_devices': 10,
                'rated_power': 300,
                'pmatrix_file': os.path.join(
                        os.getcwd(),
                        'tests',
                        'test_files',
                        'pmatrix_wave.csv'
                ),
                'number_strings': 2
        }

        args = deepcopy(args_def)
        args["rated_power"] = 0
        self.assertRaises(ValueError, WaveEnergyConverter, **args)

        args = deepcopy(args_def)
        args["number_devices"] = -2
        self.assertRaises(ValueError, WaveEnergyConverter, **args)

        args = deepcopy(args_def)
        args["rated_power"] = None
        self.assertRaises(ValueError, WaveEnergyConverter, **args)

        args = deepcopy(args_def)
        args["pmatrix_file"] = 'other_file'
        self.assertRaises(ValueError, WaveEnergyConverter, **args)

        args = deepcopy(args_def)
        args["pmatrix_file"] = 'other_file.csv'
        self.assertRaises(FileNotFoundError, WaveEnergyConverter, **args)

    def test_yaml(self):
        wec = WaveEnergyConverter.get_wec_from_yaml(self.yaml_file)
        self.assertIsInstance(wec.number_devices, int)
        self.assertEqual(wec.number_devices, 100)
        self.assertEqual(wec.rated_power, 0.5)
        self.assertIsInstance(wec.pmatrix_file, str)
        self.assertIsInstance(wec.number_substations, int)
        self.assertEqual(wec.number_substations, 1)
        self.assertEqual(wec.number_exportcables, 1)


if __name__ == '__main__':
    unittest.main()