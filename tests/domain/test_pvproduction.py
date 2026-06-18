import unittest
import os
from copy import deepcopy

from oriom.domain.Techs.PVProduction import PVProduction


class TestPVProduction(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.yaml_file = os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'pv.yaml')

    def test_init1(self):
        pv = PVProduction(
            number_devices=100,
            device_power=0.4,
            pvprod_file=os.path.join(
                    os.getcwd(),
                    'tests',
                    'test_files',
                    'pv_prod_month_hour.csv'
            ),
            number_strings=10,
            number_inverters=2
        )
        self.assertIsInstance(pv.number_devices, int)
        self.assertEqual(pv.number_devices, 100)
        self.assertIsInstance(pv.device_power, float)
        self.assertEqual(pv.device_power, 0.4)
        self.assertIsInstance(pv.pvprod_file, str)
        self.assertIsInstance(pv.number_inverters, int)
        self.assertEqual(pv.number_inverters, 2)
        self.assertEqual(pv.degradation_rate, 0)
        self.assertEqual(pv.number_mv_transformers, None)

    def test_init2(self):
        pv = PVProduction(
            number_devices=100,
            device_power=0.4,
            pvprod_file=os.path.join(
                    os.getcwd(),
                    'tests',
                    'test_files',
                    'pv_prod_month_hour.csv'
            ),
            number_strings=10,
            number_inverters=2,
            number_mv_transformers=1,
            number_substations=1,
            degradation_rate=0.05,
        )
        self.assertIsInstance(pv.number_devices, int)
        self.assertEqual(pv.number_devices, 100)
        self.assertIsInstance(pv.device_power, float)
        self.assertEqual(pv.device_power, 0.4)
        self.assertIsInstance(pv.pvprod_file, str)
        self.assertIsInstance(pv.number_inverters, int)
        self.assertEqual(pv.number_inverters, 2)
        self.assertIsInstance(pv.degradation_rate, float)
        self.assertEqual(pv.degradation_rate, 0.05)
        self.assertIsInstance(pv.number_mv_transformers, int)
        self.assertEqual(pv.number_mv_transformers, 1)

    def test_errors(self):
        args_def = {
                'number_devices': 10,
                'device_power': 0.4,
                'pvprod_file': os.path.join(
                        os.getcwd(),
                        'tests',
                        'test_files',
                        'pv_prod_month_hour.csv'
                ),
                'number_strings' : 1,
                'number_inverters': 1
        }

        args = deepcopy(args_def)
        args["device_power"] = None
        self.assertRaises(ValueError, PVProduction, **args)

        args = deepcopy(args_def)
        args["number_devices"] = -1
        self.assertRaises(ValueError, PVProduction, **args)

        args = deepcopy(args_def)
        args["number_mv_transformers"] = 2
        args['number_inverters'] = 1
        self.assertRaises(ValueError, PVProduction, **args)

        args = deepcopy(args_def)
        args["device_power"] = 0
        self.assertRaises(ValueError, PVProduction, **args)

        args = deepcopy(args_def)
        args["pvprod_file"] = 'other_file'
        self.assertRaises(ValueError, PVProduction, **args)

        args = deepcopy(args_def)
        args["pvprod_file"] = 'other_file.csv'
        self.assertRaises(FileNotFoundError, PVProduction, **args)

    def test_yaml(self):
        pv = PVProduction.get_pv_from_yaml(self.yaml_file)
        self.assertIsInstance(pv.number_devices, int)
        self.assertEqual(pv.number_devices, 7500)
        self.assertEqual(pv.device_power, 0.4)
        self.assertIsInstance(pv.pvprod_file, str)
        self.assertIsInstance(pv.number_inverters, int)
        self.assertEqual(pv.number_inverters, 4)
        self.assertEqual(pv.degradation_rate, 1)
        self.assertEqual(pv.number_mv_transformers, None)



if __name__ == '__main__':

    unittest.main()