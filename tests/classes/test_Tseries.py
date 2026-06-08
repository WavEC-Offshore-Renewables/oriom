import unittest
import os
from copy import deepcopy

from oriom.classes.Inputs.Inputs import Inputs


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
                f(self, *args, **kwargs)
        return wrapper
    return deco

class Scenario:
    def __init__(self):
        sc
class TestInputsTimeSeries(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.test_file_tseries = os.path.join(
            os.getcwd(), 'tests', 'test_files', 'inputs', 'inputs_tseries.yaml'
        )

    def std_asserts(self, inputs):
        # Geographic and metocean file
        self.assertIsInstance(inputs.site_lat["value"], float)
        self.assertEqual(inputs.site_lat["value"], 41.0)
        self.assertIsInstance(inputs.site_lon["value"], float)
        self.assertEqual(inputs.site_lon["value"], -9.0)
        self.assertIsInstance(inputs.file_metocean["value"], str)

        # Distance to port
        self.assertIsInstance(inputs.distance["value"], float)
        self.assertEqual(inputs.distance["value"], 6.0)
        self.assertEqual(inputs.distance["units"], 'km')

        # Time between devices (per tech)
        self.assertIsInstance(inputs.time_between_devices_pv["value"], float)
        self.assertEqual(inputs.time_between_devices_pv["value"], 0.01)
        self.assertEqual(inputs.time_between_devices_pv["units"], 'hours')

        self.assertIsInstance(inputs.time_between_devices_wec["value"], float)
        self.assertEqual(inputs.time_between_devices_wec["value"], 0.1)
        self.assertEqual(inputs.time_between_devices_wec["units"], 'hours')

        self.assertIsInstance(inputs.time_between_devices_wt["value"], float)
        self.assertEqual(inputs.time_between_devices_wt["value"], 0.1)
        self.assertEqual(inputs.time_between_devices_wt["units"], 'hours')

        # Surface roughness and wind speed height
        self.assertIsInstance(inputs.surface_roughness["value"], float)
        self.assertEqual(inputs.surface_roughness["value"], 0.0002)

        self.assertIsInstance(inputs.metocean_ws_height["value"], float)
        self.assertEqual(inputs.metocean_ws_height["value"], 10)

        # Max wait
        self.assertIsInstance(inputs.max_wait["value"], int)
        self.assertEqual(inputs.max_wait["value"], 16)

        # Monte Carlo percentage (note: API name stored as 'montecarlo_percent')
        self.assertIsInstance(inputs.montecarlo_percent["value"], float)
        self.assertEqual(inputs.montecarlo_percent["value"], 0.3)

        # Shift duration
        self.assertIn("shift_duration", inputs.__dict__, "Missing 'shift_duration' in Inputs.TimeSeries.")
        self.assertIsInstance(inputs.shift_duration["value"], (int, float))
        self.assertEqual(int(inputs.shift_duration["value"]), 12)
        self.assertEqual(inputs.shift_duration["units"], 'hours')

        # Scenarios
        self.assertIsInstance(inputs.scenario[0].scenario, int)
        self.assertEqual(inputs.scenario[0].scenario, 0)
        self.assertIsInstance(inputs.scenario[0].percentage_month, list)
        self.assertEqual(sum(inputs.scenario[0].percentage_month), 1)

        # Merge vessel (string list -> list normalization acceptable)
        self.assertIn("merge_vessel", inputs.__dict__, "Missing 'merge_vessel' in Inputs.TimeSeries.")
        mv_val = inputs.merge_vessel["value"]
        if isinstance(mv_val, list):
            self.assertEqual(mv_val, ['v001'])
        elif isinstance(mv_val, str):
            self.assertIn(['v001'], mv_val)
        else:
            self.fail(f"Unexpected type for merge_vessel: {type(mv_val)}")
        # Units can be '-' or absent; do not strictly assert units here.

    @skipIfNotLocal()
    def test_from_file(self):
        inputs = Inputs.TimeSeries(file_inputs=self.test_file_tseries)
        self.std_asserts(inputs)

    def test_by_hand(self):
        inputs = Inputs.TimeSeries(
            site_latitude='41',
            site_longitude='-9',
            file_metocean=os.path.join(
                os.getcwd(),
                'tests', 'test_files', 'metocean', 'metocean_dummy.csv'
            ),
            dist_port='6',
            time_between_devices_pv=0.01,
            time_between_devices_wt=0.1,
            time_between_devices_wec=0.1,
            surface_roughness=0.0002,
            metocean_ws_height=10,
            max_wait=16,
            montecarlo_percentage=0.3,
            shift_duration=12,
            merge_vessel=['v001'],
        )
        self.std_asserts(inputs)

    def test_errors(self):
        args = {}
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)
        args["site_latitude"] = 41
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)
        args["site_longitude"] = -9
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)
        args["file_metocean"] = os.path.join(
            os.getcwd(),
            'tests', 'test_files', 'metocean', 'metocean_dummy.csv'
        )
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

    def test_errors_ranges(self):
        args_def = {
            "site_latitude": 41,
            "site_longitude": -9,
            "file_metocean": os.path.join(
                os.getcwd(),
                'tests', 'test_files', 'metocean', 'metocean_dummy.csv'
            ),
            "dist_port": 6,
            "time_between_devices_pv": 0.01,
            "time_between_devices_wec": 0.1,
            "time_between_devices_wt": 0.1,
            "surface_roughness": 0.0002,
            "metocean_ws_height": 10,
            "max_wait": 16,
            "montecarlo_percentage": 0.3,
            # --- NEW extras baseline valid values ---
            "shift_duration": 12,
            "merge_vessel": "['v001']",
            "failure_scenario": 0,
            "file_metocean_tow_number": 0,
            "file_metocean_tow_location_1": os.path.join(
                os.getcwd(),
                'tests', 'test_files', 'metocean', 'metocean_dummy.csv'
            ),
            "file_metocean_tow_distance_1": 50
        }

        # Latitude out of range
        args = deepcopy(args_def)
        args["site_latitude"] = 91
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        # Longitude out of range
        args = deepcopy(args_def)
        args["site_longitude"] = 181
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        # Metocean file missing
        args = deepcopy(args_def)
        args["file_metocean"] = 'some other directory'
        self.assertRaises(FileNotFoundError, Inputs.TimeSeries, **args)

        # Surface roughness invalid (<=0)
        args = deepcopy(args_def)
        args["surface_roughness"] = 0
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        # Distance to port invalid (<=0)
        args = deepcopy(args_def)
        args["dist_port"] = 0
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        # TB devices invalid (<=0)
        args = deepcopy(args_def)
        args["time_between_devices_pv"] = 0
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        args = deepcopy(args_def)
        args["time_between_devices_wec"] = 0
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        args = deepcopy(args_def)
        args["time_between_devices_wt"] = 0
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        # Max wait invalid (<0)
        args = deepcopy(args_def)
        args["max_wait"] = -1
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        # Montecarlo invalid (<=0)
        args = deepcopy(args_def)
        args["montecarlo_percentage"] = 0
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        # --- NEW: extras invalid ranges ---

        # Shift duration invalid (<=0)
        args = deepcopy(args_def)
        args["shift_duration"] = 0
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        # metocean file tow number invalid (<=0)
        args = deepcopy(args_def)
        args["file_metocean_tow_number"] = -1
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        # metocean file tow number not corrispondent to file metocean file tow
        args = deepcopy(args_def)
        args["file_metocean_tow_number"] = 1
        args.pop("file_metocean_tow_location_1")
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        # metocean file tow number not corrispondent to file metocean file tow
        args = deepcopy(args_def)
        args["file_metocean_tow_number"] = 0
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        # Metocean file missing
        args = deepcopy(args_def)
        args["file_metocean_tow_location_1"] = 'some other directory'
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        # Failure scenario invalid (<=0)
        args = deepcopy(args_def)
        args["failure_scenario"] = -1
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        # Distance to previous point negative (<=0)
        args = deepcopy(args_def)
        args["file_metocean_tow_distance_1"] = -1
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        # Distance to previous point different from number of tow metocean file
        args = deepcopy(args_def)
        args["file_metocean_tow_number"] = 2
        args["file_metocean_tow_location_2"] = os.path.join(
                os.getcwd(),
                'tests', 'test_files', 'metocean', 'metocean_dummy.csv'
            )
        self.assertRaises(ValueError, Inputs.TimeSeries, **args)

        # Electric losses file missing
        args = deepcopy(args_def)
        args["file_metocean_tow_location_1"] = None
        args["file_electrical_losses"] = 'some other directory'
        self.assertRaises(FileNotFoundError, Inputs.TimeSeries, **args)

        # Wake losses file missing
        args = deepcopy(args_def)
        args["file_metocean_tow_location_1"] = None
        args["file_wake_losses"] = 'some other directory'
        self.assertRaises(FileNotFoundError, Inputs.TimeSeries, **args)

if __name__ == '__main__':

    test_dir = os.path.join(os.getcwd(), 'tmp', 'test')
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    unittest.main()
    os.remove(test_dir)
