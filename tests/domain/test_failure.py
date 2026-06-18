from copy import deepcopy
import unittest
import os

from oriom.domain.Failure import Failure


class TestaFailure(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.file_failures = os.path.join(
                os.getcwd(),
                'tests',
                'test_files',
                'inputs',
                'failures.yaml'
        )

    def std_asserts(self,failures):
        self.assertIsInstance(failures[0].id, str)
        self.assertEqual(failures[0].id, 'ofw_fail_001')
        self.assertEqual(failures[1].id, 'owc_fail_002')
        self.assertIsInstance(failures[0].name, str)
        self.assertEqual(failures[0].name, 'minor repair')
        self.assertEqual(failures[1].name, 'mooring line brake')
        self.assertIsInstance(failures[0].n_element, int)
        self.assertEqual(failures[0].n_element, 10)
        self.assertEqual(failures[1].n_element, 30)
        self.assertIsInstance(failures[0].fail_rate, float)
        self.assertEqual(failures[0].fail_rate, 0.9)
        self.assertEqual(failures[1].fail_rate, 0.015936)
        self.assertIsInstance(failures[0].maintenance_strategy, str)
        self.assertEqual(failures[0].maintenance_strategy,'specific month')
        self.assertEqual(failures[1].maintenance_strategy,'specific month')
        self.assertEqual(failures[0].level_failure,'device')
        self.assertEqual(failures[3].level_failure,'exp_cable')
        self.assertEqual(failures[0].operation_triggered, 'ofw_opm001')
        self.assertEqual(failures[1].operation_triggered, 'owc_op101')
        self.assertEqual(failures[0].preferred_month, 6)
        self.assertEqual(failures[1].preferred_month, 6)
        self.assertEqual(failures[0].lead_time, 0)
        self.assertEqual(failures[1].lead_time, 168)
        self.assertEqual(failures[2].lead_time, 96)
        self.assertEqual(failures[0].bath_tub, False)
        self.assertEqual(failures[1].bath_tub, False)
        self.assertEqual(failures[0].potential_shutdown, False)

    def test_from_file(self):
        failures = Failure.get_failures_from_yaml(self.file_failures)
        self.std_asserts(failures)

    def test_errors(self):
        args_default = {
                'id_': 'opv_f001',
                'name': 'dummy',
                'n_element': 5,
                'fail_rate': 0.01,
                'maintenance_strategy': 'immediately',
                'level_failure' : 'device',
                'operation_triggered': 'opv_op001',
                'lead_time': 100,
                'bath_tub' : False,
                'potential_shutdown' : False
        }
        args = deepcopy(args_default)
        args["preferred_month"] = 1
        self.assertRaises(ValueError, Failure, **args)

        args = deepcopy(args_default)
        args["maintenance_strategy"] = 'other'
        self.assertRaises(ValueError, Failure, **args)

        args = deepcopy(args_default)
        args["maintenance_strategy"] = 'no maintenace'
        self.assertRaises(ValueError, Failure, **args)

        args = deepcopy(args_default)
        args["operation_triggered"] = None
        args["preferred_month"] = 1
        self.assertRaises(ValueError, Failure, **args)

        args = deepcopy(args_default)
        args["lead_time"] = -1
        self.assertRaises(ValueError, Failure, **args)

        args = deepcopy(args_default)
        args["maintenance_strategy"] = 'specific month'
        args["avoid_month_correction"] = '1,2'
        self.assertRaises(ValueError, Failure, **args)

        args = deepcopy(args_default)
        args["avoid_month_correction"] = '1,2,3,4,5,6,7,8,9,10,11,12'
        self.assertRaises(ValueError, Failure, **args)

        args = deepcopy(args_default)
        args["preferred_month"] = '13'
        self.assertRaises(ValueError, Failure, **args)

        args = deepcopy(args_default)
        args["maintenance_strategy"] = 'specific month'
        args["preferred_month"] = '6'
        args["preferred_day"] = '31'
        self.assertRaises(ValueError, Failure, **args)


if __name__ == '__main__':

    unittest.main()
