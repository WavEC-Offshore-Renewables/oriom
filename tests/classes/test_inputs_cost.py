import unittest
import os
import tempfile
import shutil
from unittest.mock import patch

from oriom.classes.Inputs import Inputs


def skipIfNotLocal():
    """
    Decorator to skip tests when running in remote runners.
    It checks if 'runner' is part of the current working directory path.
    """
    def deco(f):
        def wrapper(self, *args, **kwargs):
            cur_path = os.getcwd()
            if 'runner' in cur_path.lower():
                self.skipTest('running in a remote repository')
            else:
                return f(self, *args, **kwargs)
        return wrapper
    return deco


class TestInputsCost(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Output dir for class under test
        cls.test_dir = os.path.join(os.getcwd(), 'tmp', 'test')
        os.makedirs(cls.test_dir, exist_ok=True)

        # Path to source YAML
        cls.src_yaml = os.path.join(
            os.getcwd(), 'tests', 'test_files', 'inputs', 'inputs_costs.yaml'
        )

        # Create sanitized temp YAML
        cls.tempdir = tempfile.mkdtemp()
        cls.test_file = os.path.join(cls.tempdir, 'inputs_costs.yaml')

        with open(cls.src_yaml, 'r', encoding='utf-8') as f_in, \
             open(cls.test_file, 'w', encoding='utf-8') as f_out:
            text = f_in.read()
            text = text.replace(
                "electricity price:\n    value:\n",
                "electricity price:\n    value: 0.0\n"
            )
            f_out.write(text)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tempdir, ignore_errors=True)

    def std_asserts(self, inputs):
        self.assertEqual(inputs.fuel_cost_hfo["value"], 450.0)
        self.assertEqual(inputs.fuel_cost_mgo["value"], 655.0)
        self.assertEqual(inputs.fuel_cost_mdo["value"], 550.0)

        self.assertEqual(inputs.port_cost_year["value"], 300000.0)
        self.assertEqual(inputs.insurance_cost_year["value"], 5000000.0)
        self.assertEqual(inputs.technicians_year["value"], 100000.0)

        self.assertEqual(inputs.merge["value"], False)
        self.assertEqual(int(inputs.time_between_merge["value"]), 30)

        self.assertEqual(float(inputs.electricity_price["value"]), 0.0)
        self.assertEqual(inputs.electricity_price_pv["value"], 140.0)
        self.assertEqual(inputs.electricity_price_wec["value"], 200.0)
        self.assertEqual(inputs.electricity_price_wt["value"], 185.0)

    @patch("oriom.classes.Inputs.logging.getLogger")
    @skipIfNotLocal()
    def test_from_file(self, mock_logger):
        inputs = Inputs.Cost(
            file_inputs=self.test_file,
            out_dir=self.test_dir
        )
        inputs.get_inputs()
        self.std_asserts(inputs)

    @patch("oriom.classes.Inputs.logging.getLogger")
    def test_by_hand(self, mock_logger):
        inputs = Inputs.Cost(
            fuel_cost_HFO=450,
            fuel_cost_MGO=655,
            fuel_cost_MDO=550,
            port_cost_year=300000,
            insurance_annual=5000000,
            technicians_year=100000,
            merge=False,
            time_between_merge=30,
            electricity_price=0.0,
            electricity_price_pv=140.0,
            electricity_price_wec=200.0,
            electricity_price_wt=185.0,
            out_dir=self.test_dir,
        )
        inputs.get_inputs()
        self.std_asserts(inputs)

    @patch("oriom.classes.Inputs.logging.getLogger")
    def test_errors(self, mock_logger):
        base = dict(out_dir=self.test_dir)

        bad_kwargs_list = [
            {"fuel_cost_HFO": -0.1},
            {"fuel_cost_MDO": -0.1},
            {"fuel_cost_MGO": -0.1},
            {"port_cost_year": -1},
            {"insurance_annual": -1},
            {"technicians_year": -1},
            {"electricity_price": -0.01},
            {"electricity_price_pv": -0.01},
            {"electricity_price_wec": -0.01},
            {"electricity_price_wt": -0.01},
            {"time_between_merge": -1},
        ]

        for bad in bad_kwargs_list:
            with self.assertRaises(ValueError):
                Inputs.Cost(**base, **bad)

    @patch("oriom.classes.Inputs.logging.getLogger")
    def test_minimal_valid_set(self, mock_logger):
        inputs = Inputs.Cost(
            fuel_cost_HFO=0,
            fuel_cost_MGO=0,
            fuel_cost_MDO=0,
            port_cost_year=0,
            insurance_annual=0,
            technicians_year=0,
            electricity_price=0,
            electricity_price_pv=0,
            electricity_price_wec=0,
            electricity_price_wt=0,
            merge=False,
            time_between_merge=0,
            out_dir=self.test_dir,
        )
        inputs.get_inputs()

        self.assertIn("fuel_cost_hfo", inputs.__dict__)
        self.assertIn("merge", inputs.__dict__)


if __name__ == "__main__":
    unittest.main()
