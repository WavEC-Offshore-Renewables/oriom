from copy import deepcopy
import unittest
import os

from logistic_tools.classes.Scenario import Scenario

class TestaScenario(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.file_scenario = os.path.join(
                os.getcwd(),
                'tests',
                'test_files',
                'inputs',
                'scenarios.yaml'
        )

    def std_asserts(self,scenario):
        self.assertIsInstance(scenario[0].scenario, str)
        self.assertEqual(scenario[0].scenario, 'scenario_0')
        self.assertEqual(scenario[1].scenario, 'scenario_1')
        self.assertIsInstance(scenario[0].percentage_month, list)
        self.assertEqual(sum(scenario[0].percentage_month), 1)
        self.assertEqual(sum(scenario[1].percentage_month), 1)


    def test_from_file(self):
        scenario = Scenario.get_scenarios_from_yaml(self.file_scenario)
        self.std_asserts(scenario)


if __name__ == '__main__':
    unittest.main()