#test_reduce_distance_to_site

import unittest
from unittest.mock import MagicMock, patch

from oriom.core.functions.operation_scheduler.reduce_distance_to_site import (
    modify_distance_to_site,
    modify_distance,
)


class TestModifyDistanceToSite(unittest.TestCase):

    def test_minor_correction_returns_transit(self):
        """
        Minor corrective operation:
        - operation has attribute 'failures'
        - operation has NO attribute 'activities'
        => function must return transit duration
        """
        operation = MagicMock()
        setattr(operation, "failures", True)   # mark as corrective minor (no activities)
        delattr(operation, 'activities')
        vessel = MagicMock()
        vessel.speed_transit = 10  # m/s

        duration = modify_distance_to_site(
            operation=operation,
            vessel_1=vessel,
            KM_DISTANCE=5,
        )

        expected = ((5000) / 10) / 3600
        self.assertAlmostEqual(duration, expected, places=6)

    def test_major_correction_modifies_activity_durations(self):
        """
        Major corrective operation:
        - operation has 'failures' and 'activities'
        - activities with location='transit' must be modified
        """
        operation = MagicMock()
        setattr(operation, "failures", True)

        expected = ((5000) / 20) / 3600

        # Mock activities
        a1 = MagicMock(location="transit", duration = expected)
        a2 = MagicMock(location="site", duration = 1)
        a1.name = 'alfa1'
        a2.name = 'alfa2'
        operation.activities = [a1, a2]

        vessel = MagicMock()
        vessel.speed_transit = 20  # m/s
    
        duration = modify_distance_to_site(operation, vessel, KM_DISTANCE=5)

        # Activity 1 must be updated
        self.assertAlmostEqual(operation.activities[0].duration, expected, places=6)
        # Activity 2 must NOT be updated
        self.assertAlmostEqual(operation.activities[1].duration, 1, places=6)

        # Major returns None
        self.assertIsNone(duration)

    def test_inspection_operation_returns_transit(self):
        """
        Inspection site:
        - operation does NOT have attribute 'failures'
        => return transit duration
        """
        operation = MagicMock()
        delattr(operation, 'failures')
        self.assertFalse(hasattr(operation, "failures"))

        vessel = MagicMock()
        vessel.speed_transit = 5

        duration = modify_distance_to_site(operation, vessel, KM_DISTANCE=5)

        expected = ((5000) / 5) / 3600
        self.assertAlmostEqual(duration, expected, places=6)


class TestModifyDistance(unittest.TestCase):

    def make_config(self):
        """Utility: returns a fully mocked Config object."""
        cfg = MagicMock()
        cfg.DIFF_DISTANCE = False
        cfg.DIFF_KM_DISTANCE = 2
        cfg.VESSEL_DIST_REDUCED_LIST = ["typeA"]
        cfg.KM_MOTHER_VESSEL = 8
        return cfg

    def make_operation(self):
        """Utility: returns a mock operation object with id + vessels."""
        op = MagicMock()
        op.id = "mockOP"
        op.vessel1 = MagicMock()
        op.vessel2 = MagicMock()
        op.vessel1.speed_transit = 12
        op.vessel1.type = "typeA"
        op.vessel2.mother_vessel = False
        return op

    @patch("oriom.core.functions.operation_scheduler.reduce_distance_to_site.modify_distance_to_site")
    def test_case1_reduced_distance(self, m_calc):
        """
        Case 1: vessel1 is in the reduced-distance list
        => modify_distance_to_site should be called with Config.DIFF_KM_DISTANCE
        """
        config = self.make_config()
        config.DIFF_DISTANCE = True

        op = self.make_operation()
        op.vessel1.type = "typeA"  # matches reduced list

        m_calc.return_value = 999.0

        out = modify_distance(
            Config=config,
            operation=op,
            default_distance=7.0
        )

        m_calc.assert_called_once_with(
            operation=op,
            vessel_1=op.vessel1,
            KM_DISTANCE=config.DIFF_KM_DISTANCE
        )
        self.assertEqual(out, 999.0)

    def test_default_case_fallback(self):
        """
        Default case:
        - vessel1 not in reduced list
        => transit = default_distance / speed_transit / 3.6
        """
        config = self.make_config()
        config.DIFF_DISTANCE = False

        op = self.make_operation()
        op.vessel1.type = "OTHER"

        out = modify_distance(
            Config=config,
            operation=op,
            default_distance=18.0,
        )

        expected = 18.0 / op.vessel1.speed_transit / 3.6
        self.assertAlmostEqual(out, expected, places=6)

    @patch("oriom.core.functions.operation_scheduler.reduce_distance_to_site.modify_distance_to_site")
    def test_case2_mother_vessel(self, m_calc):
        """
        Case 2:
        - vessel2.mother_vessel = True
        => modify_distance_to_site must be used with Config.KM_MOTHER_VESSEL
        """
        config = self.make_config()

        op = self.make_operation()
        op.vessel2.mother_vessel = True

        m_calc.return_value = 123.45

        out = modify_distance(
            Config=config,
            operation=op,
            default_distance=10.0,
        )

        m_calc.assert_called_with(
            operation=op,
            vessel_1=op.vessel1,
            KM_DISTANCE=config.KM_MOTHER_VESSEL
        )
        self.assertEqual(out, 123.45)

    @patch("oriom.core.functions.operation_scheduler.reduce_distance_to_site.modify_distance_to_site")
    def test_reduced_distance_overridden_by_mother_vessel(self, m_calc):
        """
        If both conditions apply:
        - vessel1 in reduced list AND vessel2 is mother vessel
        mother vessel rule should override everything.
        """
        config = self.make_config()
        config.DIFF_DISTANCE = True

        op = self.make_operation()
        op.vessel1.type = "typeA"            # reduced list
        op.vessel2.mother_vessel = True      # override

        m_calc.return_value = 999.99

        out = modify_distance(config, op, default_distance=20.0)

        # Last call must be for mother-vessel rule
        m_calc.assert_called_with(
            operation=op,
            vessel_1=op.vessel1,
            KM_DISTANCE=config.KM_MOTHER_VESSEL
        )
        self.assertEqual(out, 999.99)

    def test_no_vessel1_returns_none(self):
        """
        If operation has no vessel1:
        - first and default cases cannot run
        - returns None unless overridden by mother vessel rule
        """
        config = self.make_config()
        op = MagicMock()
        op.vessel1 = None
        op.vessel2 = None

        out = modify_distance(config, op, default_distance=15.0)
        self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
