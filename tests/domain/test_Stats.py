import unittest
import os

from oriom.domain.Inputs.Inputs import Inputs


def skipIfNotLocal():
    """
    Decorator to check if function is running locally or in some remote
    repository.
    If the current path includes "runner" string, it is assumed the fuction
    is not running locally.
    """
    def deco(f):
        def wrapper(self, *args, **kwargs):
            cur_path = os.getcwd()
            if 'runner' in cur_path.lower():
                self.skipTest('running in a remote repository')
            else:
                f(self, *args, **kwargs)
        return wrapper
    return deco

class TestInputsStatistical(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        test_dir = os.path.join(os.getcwd(), 'tmp', 'test')
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)
        self.test_file = os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'inputs_stats.yaml')
        self.test_dir = test_dir

    def std_asserts(self, inputs):
        self.assertIsInstance(inputs.lifetime["value"], int)
        self.assertEqual(inputs.lifetime["value"], 20)
        self.assertIsInstance(inputs.start_year["value"], int)
        self.assertEqual(inputs.start_year["value"], 2023)
        self.assertIsInstance(inputs.start_month["value"], int)
        self.assertEqual(inputs.start_month["value"], 7)
        self.assertIsInstance(inputs.last_day_operation["value"], int)
        self.assertEqual(inputs.last_day_operation["value"], 15)
        self.assertIsInstance(inputs.percentile_main["value"], int)
        self.assertEqual(inputs.percentile_main["value"], 50)
        self.assertIsInstance(inputs.percentiles["value"], list)
        self.assertEqual(inputs.percentiles["value"], [25,50,75])
        self.assertIsInstance(inputs.period_infant_mortality["value"], int)
        self.assertEqual(inputs.period_infant_mortality["value"], 2)
        self.assertIsInstance(inputs.period_wear_out["value"], int)
        self.assertEqual(inputs.period_wear_out["value"], 3)
        self.assertIsInstance(inputs.failure_ratio["value"], float)
        self.assertEqual(inputs.failure_ratio["value"], 3.5)
        self.assertIsInstance(inputs.failure_ratio_sensitivity["value"], float)
        self.assertEqual(inputs.failure_ratio_sensitivity["value"], 1)

    def test_from_file(self):
        inputs = Inputs.Statistical(
                file_inputs=self.test_file
        )
        self.std_asserts(inputs)

    def test_by_hand(self):
        inputs = Inputs.Statistical(
                project_lifetime='20',
                start_year = '2023',
                start_month = '7',
                percentile_main = '50',
                percentile_1 = '25',
                percentile_2 = '75',
                last_day_operation='15',
                period_infant_mortality='2',
                period_wear_out='3',
                failure_ratio='3.5',
                failure_ratio_sensitivity = 1
        )
        self.std_asserts(inputs)

    def test_errors(self):
        # Negative/invalid numeric fields should raise at construction time.
        base = dict(out_dir=self.test_dir)

        bad_kwargs_list = [
            {"project_lifetime": -1},
            {"last_day_operation": -1},
            {"last_day_operation": 32},
            {"percentiles": -1},
            {"percentiles": 150},
            {"start_month": -1},
            {"start_month": 15},
            {"failure_ratio_sensitivity": -1},
            {"period_infant_mortality": -1},
            {"period_wear_out": -0.01},
            {"failure_ratio": -0.01},
        ]

        for bad in bad_kwargs_list:
            with self.assertRaises(ValueError):
                Inputs.Statistical(**base, **bad)

        args = {}
        self.assertRaises(ValueError, Inputs.Statistical, **args)
        args["project_lifetime"] = 20
        self.assertRaises(ValueError, Inputs.Statistical, **args)
        args["start_year"] = 2030
        self.assertRaises(ValueError, Inputs.Statistical, **args)
        args["start_month"] = 6
        self.assertRaises(ValueError, Inputs.Statistical, **args)
        args["last_day_operation"] = 15

        args["project_lifetime"] = -1
        self.assertRaises(ValueError, Inputs.Statistical, **args)
        args["start_month"] = 0
        self.assertRaises(ValueError, Inputs.Statistical, **args)
        args["start_month"] = 13
        self.assertRaises(ValueError, Inputs.Statistical, **args)
        args["percentile_main"] = 0
        self.assertRaises(ValueError, Inputs.Statistical, **args)
        args["percentile_main"] = 100
        self.assertRaises(ValueError, Inputs.Statistical, **args)
        args["last_day_operation"] = 0
        self.assertRaises(ValueError, Inputs.Statistical, **args)
        args["last_day_operation"] = 32
        self.assertRaises(ValueError, Inputs.Statistical, **args)
        args["period_infant_mortality"] = 5
        args["period_wear_out"] = 16
        self.assertRaises(ValueError, Inputs.Statistical, **args)
        del args["period_infant_mortality"]
        del args["period_wear_out"]
        args["failure_ratio"] = 1
        self.assertRaises(ValueError, Inputs.Statistical, **args)
        args["failure_ratio_sensitivity"] = -1
        self.assertRaises(ValueError, Inputs.Statistical, **args)


if __name__ == '__main__':

    unittest.main()
