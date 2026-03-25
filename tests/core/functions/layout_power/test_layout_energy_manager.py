# test_layout_energy_manager
import unittest
from unittest.mock import patch, Mock
import pandas as pd
import networkx as nx 

from oriom.core.functions.layout_power import layout_energy_manager as lem


class TestShutWindWave(unittest.TestCase):
    """
    Test of the shut function for wind/wave cases.
    """

    def setUp(self):
        # Simple graph: device -> SHORE
        self.G = nx.DiGraph()
        self.G.add_node(0, level="SHORE", power=0.0)
        self.G.add_node(1, level="device", power=1.0)
        self.G.add_edge(1, 0, visible=True)

        self.component_level_power = "device"
        # In line with return_percentage: levels without power, excluding component_level_power
        self.levels_no_power = {"SHORE"}

    def test_shut_wind_device_sets_power_zero_and_power_farm_zero(self):
        """
        For tech='wind' and loc int (device node):
        - node power must become 0
        - the path remains visible (device not in levels_no_power)
        - power_farm must become 0
        """
        G_out, power_farm = lem.shut(
            loc=1,
            shutdown=True,
            G=self.G,
            component_level_power=self.component_level_power,
            levels_component_no_power=self.levels_no_power,
            tech="wind",
            names_tech="device",
        )

        self.assertEqual(G_out.nodes[1]["power"], 0.0)
        self.assertTrue(G_out.edges[1, 0]["visible"])
        self.assertEqual(power_farm, 0.0)

    def test_shut_wind_edge_failure_closes_edge_and_keeps_other_paths(self):
        """
        For tech='wind' and loc tuple (edge):
        - the selected edge must become visible=False
        - power_farm considers only nodes with still visible paths
        """
        # Add a second device with power=1.0
        self.G.add_node(2, level="device", power=1.0)
        self.G.add_edge(2, 0, visible=True)

        G_out, power_farm = lem.shut(
            loc=(1, 0),
            shutdown=True,
            G=self.G,
            component_level_power=self.component_level_power,
            levels_component_no_power=self.levels_no_power,
            tech="wind",
            names_tech="array_cable",
        )

        # Edge (1,0) closed, (2,0) still open
        self.assertFalse(G_out.edges[1, 0]["visible"])
        self.assertTrue(G_out.edges[2, 0]["visible"])
        # Power farm = only node 2
        self.assertEqual(power_farm, 1.0)


class TestShutPV(unittest.TestCase):
    """
    Test of the shut function for PV cases (inverter, string, cable 'x','x').
    """

    def setUp(self):
        # PV graph: inverter -> SHORE
        self.G = nx.DiGraph()
        self.G.add_node(0, level="SHORE", power=0.0)
        self.G.add_node(10, level="inverter", power=10.0)
        self.G.add_edge(10, 0, visible=True)

        self.component_level_power = "inverter"
        # In line with return_percentage: all levels except inverter
        self.levels_no_power = {"SHORE"}

    def test_shut_pv_device_failure_reduces_inverter_power_by_one(self):
        """
        PV device-level: names_tech contains 'device':
        - decrease inverter power by 1
        - power_farm = new inverter power
        """
        G_out, power_farm = lem.shut(
            loc=10,
            shutdown=True,
            G=self.G,
            component_level_power=self.component_level_power,
            levels_component_no_power=self.levels_no_power,
            tech="PV",
            names_tech="opv_fail_device",
            n_pv_per_string=4,
            max_failure_module=3,
            device_shutted_string_level={},
            list_failed=set(),
            string_inverter=set(),
        )

        self.assertEqual(G_out.nodes[10]["power"], 9.0)
        self.assertEqual(power_farm, 9.0)
        self.assertTrue(G_out.edges[10, 0]["visible"])

    def test_shut_pv_string_failure_reduces_inverter_power_by_n_pv_per_string(self):
        """
        PV string-level: names_tech contains 'string':
        - decrease inverter power by n_pv_per_string
        """
        G_out, power_farm = lem.shut(
            loc=10,
            shutdown=True,
            G=self.G,
            component_level_power=self.component_level_power,
            levels_component_no_power=self.levels_no_power,
            tech="PV",
            names_tech="opv_fail_string",
            n_pv_per_string=4,
            max_failure_module=3,
            device_shutted_string_level={},
            list_failed=set(),
            string_inverter=set(),
        )

        self.assertEqual(G_out.nodes[10]["power"], 6.0)
        self.assertEqual(power_farm, 6.0)

    @patch("oriom.core.functions.layout_power.layout_energy_manager.string_location")
    @patch("oriom.core.functions.layout_power.layout_energy_manager.random.choice")
    def test_shut_pv_cable_xx_reassigns_to_inverter_and_closes_string(
        self, mock_choice, mock_string_location
    ):
        """
        PV array cable not implemented: loc == ('x','x'):
        - chooses an inverter with random.choice
        - uses string_location to choose the string
        - marks device_shutted_string_level[loc][k] = True
        - reduces inverter power by (n_pv_per_string - pv_failed_in_string)
        """
        # Add a second inverter to test the choice
        self.G.add_node(20, level="inverter", power=5.0)
        self.G.add_edge(20, 0, visible=True)

        # random.choice must always return inverter 10
        mock_choice.return_value = 10
        # string_location must always return string 1
        mock_string_location.return_value = 1

        device_shutted_string_level = {}
        string_inverter = {1, 2, 3}
        n_pv_per_string = 10

        G_out, power_farm = lem.shut(
            loc=("x", "x"),
            shutdown=True,
            G=self.G,
            component_level_power=self.component_level_power,
            levels_component_no_power=self.levels_no_power,
            tech="PV",
            names_tech="string_cable",
            n_pv_per_string=n_pv_per_string,
            max_failure_module=3,
            device_shutted_string_level=device_shutted_string_level,
            list_failed=set(),
            string_inverter=string_inverter,
        )

        # Check that the chosen inverter is 10 and string 1 is closed
        self.assertIn(10, device_shutted_string_level)
        self.assertTrue(device_shutted_string_level[10][1])

        # Power decreases by (n_pv_per_string - pv_failed_in_string) = 10 - 0
        self.assertEqual(G_out.nodes[10]["power"], 0.0)
        # Total power = inverter 10 (0) + inverter 20 (5)
        self.assertEqual(power_farm, 5.0)


class TestFix(unittest.TestCase):
    """
    Test of the fix function for wind/wave and PV.
    """

    def setUp(self):
        # Base graph
        self.G = nx.DiGraph()
        self.G.add_node(0, level="SHORE", power=0.0)
        self.G.add_node(1, level="device", power=0.0)
        self.G.add_edge(1, 0, visible=False)

    def test_fix_wind_device_restores_power_to_one(self):
        """
        For tech='wind' and device node:
        - if level == 'device', power must become 1
        - with levels_component_no_power NOT including 'device',
          edges remain as is (here: still False)
        """
        component_level_power = "device"
        levels_no_power = {"SHORE"}  # 'device' not included

        G_out, power_farm = lem.fix(
            loc=1,
            G=self.G,
            component_level_power=component_level_power,
            levels_component_no_power=levels_no_power,
            tech="wind",
            names_tech="device",
            n_pv_per_string=None,
        )

        self.assertEqual(G_out.nodes[1]["power"], 1.0)
        self.assertFalse(G_out.edges[1, 0]["visible"])
        # No visible path → power_farm=0
        self.assertEqual(power_farm, 0.0)

    def test_fix_wind_device_restores_edges_if_level_in_no_power(self):
        """
        If level is in levels_component_no_power:
        - edges incident to the node must become visible
        """
        G = self.G.copy()
        component_level_power = "device"
        levels_no_power = {"device"}  # force branch that reopens edges

        G_out, power_farm = lem.fix(
            loc=1,
            G=G,
            component_level_power=component_level_power,
            levels_component_no_power=levels_no_power,
            tech="wind",
            names_tech="device",
            n_pv_per_string=None,
        )

        self.assertTrue(G_out.edges[1, 0]["visible"])
        self.assertEqual(power_farm, 1.0)

    def test_fix_edge_tuple_restores_visibility(self):
        """
        For loc tuple (edge):
        - if edge is visible=False it must return True
        """
        component_level_power = "device"
        levels_no_power = {"SHORE"}

        G_out, power_farm = lem.fix(
            loc=(1, 0),
            G=self.G,
            component_level_power=component_level_power,
            levels_component_no_power=levels_no_power,
            tech="wind",
            names_tech="array_cable",
            n_pv_per_string=None,
        )

        self.assertTrue(G_out.edges[1, 0]["visible"])
        # path 1->0 visible, node 1 power=0 → power_farm=0
        self.assertEqual(power_farm, 0.0)

    def test_fix_pv_device_increments_power_by_one(self):
        """
        For tech='PV' and names_tech containing 'device':
        - increment node power by 1
        """
        G = nx.DiGraph()
        G.add_node(0, level="SHORE", power=0.0)
        G.add_node(10, level="inverter", power=5.0)
        G.add_edge(10, 0, visible=True)

        component_level_power = "inverter"
        levels_no_power = {"SHORE"}

        G_out, power_farm = lem.fix(
            loc=10,
            G=G,
            component_level_power=component_level_power,
            levels_component_no_power=levels_no_power,
            tech="PV",
            names_tech="opv_fail_device",
            n_pv_per_string=4,
        )

        self.assertEqual(G_out.nodes[10]["power"], 6.0)
        self.assertEqual(power_farm, 6.0)


class TestReassignLoc(unittest.TestCase):
    """
    Test for reassign_loc: Loc reassignment and DataFrame update.
    """

    @patch("oriom.core.functions.layout_power.layout_energy_manager.choose_loc")
    def test_reassign_loc_updates_failure_and_operation_rows(self, mock_choose_loc):
        """
        reassign_loc must:
        - call choose_loc to get a new Loc
        - update df.loc[index, 'Loc'] for the failure
        - update df.loc[operation_row, 'Loc'] for the correlated operation
        """
        # choose_loc will always return 99
        mock_choose_loc.return_value = 99

        # DataFrame with a failure and a correlated operation
        df = pd.DataFrame(
            {
                "id": ["ofw.001", "op_corr_001"],
                "Comments": ["", "oper_ofw.001"],
                "Shut/Fix": ["shut", "fix"],
                "Loc": [1, 1],
            },
            index=[0, 1],
        )

        # fake failure object
        failure = Mock()
        failure.level_failure = "device"

        class DummyFindElement:
            def find_operation(self, id_fail):
                # id_fail = 'ofw.001' → return failure
                return failure

        find_element_class = DummyFindElement()

        # minimal graph: only needed for signature
        G = nx.DiGraph()
        G.add_node(0, level="SHORE", power=0.0)
        G.add_node(1, level="device", power=1.0)

        device_shutted = []

        # failure row
        row = df.loc[0].copy()

        new_loc = lem.reassign_loc(
            row=row,
            df=df,
            find_element_class=find_element_class,
            G=G,
            device_shutted=device_shutted,
            index=0,
            tech="wind",
        )

        # New loc must be 99
        self.assertEqual(new_loc, 99)
        # Failure updated
        self.assertEqual(df.loc[0, "Loc"], 99)
        # Correlated operation updated
        self.assertEqual(df.loc[1, "Loc"], 99)
        # choose_loc must have been called once
        mock_choose_loc.assert_called_once()


class TestEnergyFunctions(unittest.TestCase):

    # ---------------------------
    # TEST count_nodes_power
    # ---------------------------
    def test_count_nodes_power_visible_path(self):
        G = nx.DiGraph()

        # structure: 1 -> 2 -> 0
        G.add_edge(1, 2, visible=True)
        G.add_edge(2, 0, visible=True)

        G.nodes[1]['level'] = 'device'
        G.nodes[2]['level'] = 'other'
        G.nodes[0]['level'] = 'root'

        result = lem.count_nodes_power(G, 'device')

        self.assertEqual(result, [1])

    def test_count_nodes_power_invisible_edge(self):
        G = nx.DiGraph()

        G.add_edge(1, 2, visible=False)
        G.add_edge(2, 0, visible=True)

        G.nodes[1]['level'] = 'device'
        G.nodes[2]['level'] = 'other'
        G.nodes[0]['level'] = 'root'

        result = lem.count_nodes_power(G, 'device')

        self.assertEqual(result, [])  # path not valid

    def test_count_nodes_power_wrong_level(self):
        G = nx.DiGraph()

        G.add_edge(1, 0, visible=True)

        G.nodes[1]['level'] = 'not_device'
        G.nodes[0]['level'] = 'root'

        result = lem.count_nodes_power(G, 'device')

        self.assertEqual(result, [])


    # ---------------------------
    # TEST manage_string_tow_operation
    # ---------------------------
    def test_manage_string_tow_operation_tuple(self):
        G = nx.DiGraph()
        G.add_edge(1, 2, visible=False)

        lem.manage_string_tow_operation(G, (1, 2), True)

        self.assertTrue(G.edges[1, 2]['visible'])

    def test_manage_string_tow_operation_node(self):
        G = nx.DiGraph()

        # 3 -> 1 (smallest neighbor = 1)
        G.add_edge(3, 1, visible=False)

        lem.manage_string_tow_operation(G, 3, True)

        self.assertTrue(G.edges[3, 1]['visible'])

    def test_manage_string_tow_operation_no_neighbors(self):
        G = nx.DiGraph()
        G.add_node(5)

        # should not crash
        lem.manage_string_tow_operation(G, 5, True)


    # ---------------------------
    # TEST check_previous_fix
    # ---------------------------
    def test_check_previous_fix_tow(self):
        G = nx.DiGraph()
        G.add_edge(1, 2, visible=False)

        op_add_tow = {
            "10_tow": {
                "f1": (1, 2)
            }
        }

        r = {'id': 10, 'failure_id': 'f1'}

        lem.check_previous_fix(G, op_add_tow, r, type_id='tow')

        # edge must be visibile
        self.assertTrue(G.edges[1, 2]['visible'])
        self.assertNotIn("10_tow", op_add_tow)

    def test_check_previous_fix_non_tow(self):
        G = nx.DiGraph()
        G.add_node(5, power=0)

        op_add_tow = {
            "20_other": {
                "f2": 5
            }
        }

        r = {'id': 20, 'failure_id': 'f2'}

        lem.check_previous_fix(G, op_add_tow, r, type_id='other')

        # power restored
        self.assertEqual(G.nodes[5]['power'], 1)
        self.assertNotIn("20_other", op_add_tow)

    def test_check_previous_fix_no_match(self):
        G = nx.DiGraph()

        op_add_tow = {}
        r = {'id': 1, 'failure_id': 'x'}

        # should not crash
        lem.check_previous_fix(G, op_add_tow, r, type_id='tow')

        self.assertEqual(op_add_tow, {})



if __name__ == "__main__":
    unittest.main(verbosity=2)
