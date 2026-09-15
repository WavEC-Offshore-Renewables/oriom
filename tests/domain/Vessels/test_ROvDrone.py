import unittest
import os
from copy import deepcopy
from unittest import skip

from oriom.domain.Vessels.RovDrone import RovDrone


class TestRovDrone(unittest.TestCase):
    def test_init(self):
        # Test without file_consumption_path, sheet_name, and fuel parameters
        args_def = {
                'id_': 'id',
                'name': 'stork',
                'type_': 'aerial',
                'daily_charter': '-1000',
                'nr_technicians': '5'
        }
        args = deepcopy(args_def)
        self.assertRaises(ValueError, RovDrone, **args)

        # Test minimal
        rov_drone_min = RovDrone(
                id_='stork_1',
                name='Stork',
                type_='aerial',
                daily_charter=4920,
        )
        self.assertIsInstance(rov_drone_min.id, str)
        self.assertEqual(rov_drone_min.id, 'stork_1')
        self.assertIsInstance(rov_drone_min.name, str)
        self.assertEqual(rov_drone_min.name, 'stork')
        self.assertIsInstance(rov_drone_min.type, str)
        self.assertEqual(rov_drone_min.type, 'aerial')
        self.assertIsInstance(rov_drone_min.daily_charter, float)
        self.assertEqual(rov_drone_min.daily_charter, 4920.0)
        self.assertIsNone(rov_drone_min.speed_transit)
        self.assertIsInstance(rov_drone_min.nr_technicians, int)
        self.assertEqual(rov_drone_min.nr_technicians, 0)
        #self.assertIsNone(rov_drone_min.support_vessel)
        self.assertIsInstance(rov_drone_min.on_site, bool)
        self.assertEqual(rov_drone_min.on_site, False)

        # Test full
        rov_drone_full = RovDrone(
                id_='stork_1',
                name='Stork',
                type_='aerial',
                daily_charter='1000',
                weight='10',
                dimensions='1.5',
                useful_capacity='5',
                speed_transit='10.2',
                battery_capacity='0.4',
                recharging_duration='3',
                max_distance='17',
                avg_autonomy='0.6',
                on_site='True',
                support_vessel='CTV',
                nr_technicians='5',
                ws_max='10',
                hs_max='1.5',
                daylight='True',
                precipitation_max='5'

        )
        self.assertIsInstance(rov_drone_full.id, str)
        self.assertEqual(rov_drone_full.id, 'stork_1')
        self.assertIsInstance(rov_drone_full.name, str)
        self.assertEqual(rov_drone_full.name, 'stork')
        self.assertIsInstance(rov_drone_full.type, str)
        self.assertEqual(rov_drone_full.type, 'aerial')
        self.assertIsInstance(rov_drone_full.daily_charter, float)
        self.assertEqual(rov_drone_full.daily_charter, 1000)
        self.assertIsInstance(rov_drone_full.weight, float)
        self.assertEqual(rov_drone_full.weight, 10)
        self.assertIsInstance(rov_drone_full.dimensions, float)
        self.assertEqual(rov_drone_full.dimensions, 1.5)
        self.assertIsInstance(rov_drone_full.speed_transit, float)
        self.assertEqual(rov_drone_full.speed_transit, 10.2)
        self.assertIsInstance(rov_drone_full.battery_capacity, float)
        self.assertEqual(rov_drone_full.battery_capacity, 0.4)
        self.assertIsInstance(rov_drone_full.recharging_duration, float)
        self.assertEqual(rov_drone_full.recharging_duration, 3)
        self.assertIsInstance(rov_drone_full.max_distance, float)
        self.assertEqual(rov_drone_full.max_distance, 17.0)
        self.assertIsInstance(rov_drone_full.avg_autonomy, float)
        self.assertEqual(rov_drone_full.avg_autonomy, 0.6)
        self.assertIsInstance(rov_drone_full.on_site, bool)
        self.assertEqual(rov_drone_full.on_site, True)
        self.assertIsInstance(rov_drone_full.support_vessel, str)
        self.assertEqual(rov_drone_full.support_vessel, 'ctv')
        self.assertIsInstance(rov_drone_full.nr_technicians, int)
        self.assertEqual(rov_drone_full.nr_technicians, 5)
        self.assertIsInstance(rov_drone_full.ws_max, float)
        self.assertEqual(rov_drone_full.ws_max, 10.0)
        self.assertIsInstance(rov_drone_full.hs_max, float)
        self.assertEqual(rov_drone_full.hs_max, 1.5)
        self.assertIsInstance(rov_drone_full.daylight, bool)
        self.assertEqual(rov_drone_full.daylight, True)
        self.assertIsInstance(rov_drone_full.precipitation_max, float)
        self.assertEqual(rov_drone_full.precipitation_max, 5.0)


if __name__ == '__main__':

    unittest.main()
