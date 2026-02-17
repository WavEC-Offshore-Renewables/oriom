import unittest
import os
from copy import deepcopy

from oriom.classes.Activity import Activity


class TestActivity(unittest.TestCase):
    @classmethod
    def setUpClass(self):
            pass

    def test_minimal(self):
        activity_no_olc = Activity(
                id_='ACT_001_00',
                name='Vessel preparation',
                duration=2.0,
                location='port'
        )
        self.assertEqual(activity_no_olc.wtg_shutdown_dur, 0)
        self.assertEqual(activity_no_olc.wec_shutdown_dur, 0)
        self.assertEqual(activity_no_olc.pv_shutdown_dur, 0)
        self.assertIsNone(activity_no_olc.hs)
        self.assertIsNone(activity_no_olc.tp)
        self.assertIsNone(activity_no_olc.ws)
        self.assertIsNone(activity_no_olc.ws_hub)
        self.assertIsNone(activity_no_olc.cs)
        self.assertFalse(activity_no_olc.light)

    def test_complete(self):
        activity_complete = Activity(
                id_='ACT_003_00',
                name='Very precise activity',
                duration=1.5,
                location='site',
                wtg_shutdown_dur=True,
                wec_shutdown_dur='',
                pv_shutdown_dur='',
                wave_height='1.5',
                wave_period='15',
                wind_speed='18.5',
                wind_speed_hub='22',
                current_speed='0.5',
                light='1'
        )
        self.assertEqual(activity_complete.wtg_shutdown_dur, True)
        self.assertEqual(activity_complete.wec_shutdown_dur, False)
        self.assertEqual(activity_complete.pv_shutdown_dur, False)
        self.assertEqual(activity_complete.hs, 1.5)
        self.assertEqual(activity_complete.tp, 15.0)
        self.assertEqual(activity_complete.ws, 18.5)
        self.assertEqual(activity_complete.ws_hub, 22.0)
        self.assertEqual(activity_complete.cs, 0.5)
        self.assertTrue(activity_complete.light)

    def test_conversion(self):
        activity_dummy = Activity(
                id_=1,
                name='Dummy',
                wec_shutdown_dur='1',
                duration=1,
                location='port'
        )
        self.assertIsInstance(activity_dummy.id, str)
        self.assertEqual(activity_dummy.wtg_shutdown_dur, False)
        self.assertIsInstance(activity_dummy.wec_shutdown_dur, bool)
        self.assertEqual(activity_dummy.wec_shutdown_dur, True)
        self.assertIsInstance(activity_dummy.duration, float)

    def test_errors_type(self):
        args_default = {
                'id_': 'id',
                'name': 'dummy_name',
                'duration': 2.0,
                'location': 'port',
                'wtg_shutdown_dur': 2,
                'wec_shutdown_dur': 0,
                'pv_shutdown_dur': 0,
                'wave_height': 1.5,
                'wave_period': 15,
                'wind_speed': 18.5,
                'current_speed': 0.5,
                'light': True
        }
        args = deepcopy(args_default)
        args["duration"] = None
        self.assertRaises(TypeError, Activity, **args)
        args["duration"] = '2 hours'
        self.assertRaises(ValueError, Activity, **args)

        args = deepcopy(args_default)
        args["location"] = 'None'
        self.assertRaises(ValueError, Activity, **args)

        args = deepcopy(args_default)
        args["wave_height"] = '1 and half meter'
        self.assertRaises(ValueError, Activity, **args)

        args = deepcopy(args_default)
        args["wave_period"] = 'fifteen meter'
        self.assertRaises(ValueError, Activity, **args)

        args = deepcopy(args_default)
        args["wind_speed"] = 'eighteen point five meter per second'
        self.assertRaises(ValueError, Activity, **args)

        args = deepcopy(args_default)
        args["current_speed"] = 'half meter per second'
        self.assertRaises(ValueError, Activity, **args)

        args = deepcopy(args_default)
        args["light"] = 'one'
        self.assertRaises(ValueError, Activity, **args)

    def test_errors_ranges(self):
        args_default = {
                'id_': 'id',
                'name': 'dummy_name',
                'duration': 2.0,
                'location': 'port',
                'wtg_shutdown_dur': 0,
                'wec_shutdown_dur': 2,
                'pv_shutdown_dur': 0,
                'wave_height': 1.5,
                'wave_period': 15,
                'wind_speed': 18.5,
                'current_speed': 0.5,
                'light': True
        }
        args = deepcopy(args_default)
        args["duration"] = -1
        self.assertRaises(ValueError, Activity, **args)

        args = deepcopy(args_default)
        args["location"] = 'other'
        self.assertRaises(ValueError, Activity, **args)

        args = deepcopy(args_default)
        args["wave_height"] = -1
        self.assertRaises(ValueError, Activity, **args)

        args = deepcopy(args_default)
        args["wave_period"] = -1
        self.assertRaises(ValueError, Activity, **args)

        args = deepcopy(args_default)
        args["wind_speed"] = -1
        self.assertRaises(ValueError, Activity, **args)

    def test_get_activities_from_csv(self):
        file_activities = os.path.join(os.getcwd(), 'tests', 'test_files', 'op_activities_dummy.csv')
        Activity.get_activities_from_csv(file_activities)
        # TODO


if __name__ == '__main__':

    unittest.main()
