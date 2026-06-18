#test_Inputs

import unittest
from unittest.mock import Mock

from oriom.classes.Inputs.Inputs import Inputs
from oriom.classes.Inputs.Generals import General
from oriom.classes.Inputs.Statisticals import Statistical
from oriom.classes.Inputs.Costs import Cost
from oriom.classes.Inputs.Timeseries import TimeSeries


class TestInputs(unittest.TestCase):

    def test_exposes_input_classes(self):
        self.assertIs(Inputs.General, General)
        self.assertIs(Inputs.Statistical, Statistical)
        self.assertIs(Inputs.Cost, Cost)
        self.assertIs(Inputs.TimeSeries, TimeSeries)

    def test_constructor_stores_objects_without_rebuilding_them(self):
        general = Mock(spec=General)
        stats = Mock(spec=Statistical)
        cost = Mock(spec=Cost)
        tseries = Mock(spec=TimeSeries)

        inputs = Inputs(
            general=general,
            stats=stats,
            cost=cost,
            tseries=tseries,
        )

        self.assertIs(inputs.general, general)
        self.assertIs(inputs.stats, stats)
        self.assertIs(inputs.cost, cost)
        self.assertIs(inputs.tseries, tseries)

    def test_constructor_supports_positional_arguments(self):
        general = Mock(spec=General)
        stats = Mock(spec=Statistical)
        cost = Mock(spec=Cost)
        tseries = Mock(spec=TimeSeries)

        inputs = Inputs(general, stats, cost, tseries)

        self.assertIs(inputs.general, general)
        self.assertIs(inputs.stats, stats)
        self.assertIs(inputs.cost, cost)
        self.assertIs(inputs.tseries, tseries)

    def test_expected_calling_style_is_available(self):
        self.assertTrue(hasattr(Inputs, "General"))
        self.assertTrue(hasattr(Inputs, "Statistical"))
        self.assertTrue(hasattr(Inputs, "Cost"))
        self.assertTrue(hasattr(Inputs, "TimeSeries"))

        self.assertTrue(callable(Inputs.General))
        self.assertTrue(callable(Inputs.Statistical))
        self.assertTrue(callable(Inputs.Cost))
        self.assertTrue(callable(Inputs.TimeSeries))


if __name__ == "__main__":
    unittest.main()