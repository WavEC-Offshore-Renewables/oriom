# tests/test_layout_wind.py
import unittest
from unittest.mock import patch
import networkx as nx

from oriom.domain.Layouts.Layouts_Wind import Layout_Wind


# --------- helpers ---------
def count_nodes_by_level(G: nx.DiGraph, level: str) -> int:
    return sum(1 for _, d in G.nodes(data=True) if d.get("level") == level)


def edge_levels(G: nx.DiGraph):
    return list(nx.get_edge_attributes(G, "level").values())


def get_node_by_name(G: nx.DiGraph, name: str):
    for n, d in G.nodes(data=True):
        if d.get("name") == name:
            return n, d
    return None, None


# --------- check_input_wind ---------
class TestCheckInputWind(unittest.TestCase):
    def setUp(self):
        self.w = Layout_Wind()

    def test_valid_divisible(self):
        # n_turbines divisible by n_strings -> no exception
        self.w.check_input_wind(n_turbines=12, n_strings=3)

    def test_not_divisible_raises(self):
        # Not divisible -> ValueError
        with self.assertRaises(ValueError):
            self.w.check_input_wind(n_turbines=10, n_strings=3)


# Patch draw operations to avoid IO and GUI during tests
@patch("oriom.domain.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
@patch("matplotlib.pyplot.show")
@patch("matplotlib.pyplot.savefig")
class TestLayout1Wind(unittest.TestCase):
    def setUp(self):
        self.w = Layout_Wind()

    def test_single_turbine_chain(self, _sf, _sh, _draw):
        G = self.w.layout1_wind(n_turbines=1, n_strings=1, substation_node=1, tow_string_shutdown = True, show_plot=False)
        # Shore exists
        shore_n, _ = get_node_by_name(G, "SHORE")
        self.assertIsNotNone(shore_n)
        # Substation at requested id
        sub_n, _ = get_node_by_name(G, "Sub")
        self.assertEqual(sub_n, 1)
        # Exactly one device
        self.assertEqual(count_nodes_by_level(G, "device"), 1)
        # Array cable present
        self.assertIn("array_cable", edge_levels(G))

    def test_multiple_turbines_multiple_strings(self, _sf, _sh, _draw):
        G = self.w.layout1_wind(n_turbines=6, n_strings=3, substation_node=1, tow_string_shutdown = True, show_plot=False)
        # Six devices created
        self.assertEqual(count_nodes_by_level(G, "device"), 6)
        # At least the chain cables between devices (array_cable)
        self.assertIn("array_cable", edge_levels(G))


@patch("oriom.domain.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
@patch("matplotlib.pyplot.show")
@patch("matplotlib.pyplot.savefig")
class TestLayout2Wind(unittest.TestCase):
    def setUp(self):
        self.w = Layout_Wind()

    def test_invalid_division_raises(self, _sf, _sh, _draw):
        with self.assertRaises(ValueError):
            self.w.layout2_wind(n_turbines=10, n_strings=2, n_substations=3, tow_string_shutdown = True, show_plot=False)

    def test_two_farms_with_redundant_links(self, _sf, _sh, _draw):
        # 12 total turbines, 2 substations -> 6 per farm
        G = self.w.layout2_wind(n_turbines=12, n_strings=3, n_substations=2, tow_string_shutdown = True, show_plot=False)
        # Two substations
        self.assertEqual(count_nodes_by_level(G, "substation"), 2)
        # 12 devices
        self.assertEqual(count_nodes_by_level(G, "device"), 12)
        # Redundant cables between substations (two directions)
        levels = edge_levels(G)
        self.assertGreaterEqual(levels.count("redundant_cable"), 2)
        # Single shore node present
        shore_n, _ = get_node_by_name(G, "SHORE")
        self.assertIsNotNone(shore_n)


@patch("oriom.domain.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
@patch("matplotlib.pyplot.show")
@patch("matplotlib.pyplot.savefig")
class TestLayout3Wind(unittest.TestCase):
    def setUp(self):
        self.w = Layout_Wind()

    def test_multiple_exports_add_dummy_nodes_and_cables(self, _sf, _sh, _draw):
        # n_exports=3 -> 2 dummy nodes + base export cable + 2 additional export cables
        G = self.w.layout3_wind(n_turbines=6, n_strings=3, n_exports=3, tow_string_shutdown = True, show_plot=False)
        # Two dummy nodes created
        self.assertEqual(count_nodes_by_level(G, "dummy"), 2)
        # Export cables include the base one plus (n_exports-1) added -> >= n_exports
        levels = edge_levels(G)
        self.assertGreaterEqual(levels.count("exp_cable"), 3)
        # exp_cable_dummy count matches (n_exports-1)
        self.assertEqual(levels.count("exp_cable_dummy"), 2)


@patch("oriom.domain.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
@patch("matplotlib.pyplot.show")
@patch("matplotlib.pyplot.savefig")
class TestLayout4Wind(unittest.TestCase):
    def setUp(self):
        self.w = Layout_Wind()

    def test_custom_string_list_valid(self, _sf, _sh, _draw):
        # Custom non-uniform split: 10 turbines into 3 strings [3,3,4]
        G = self.w.layout4_wind(
            n_turbines=10, n_strings=3, substation_node=1, string_list=[3, 3, 4], tow_string_shutdown = True, show_plot=False
        )
        self.assertEqual(count_nodes_by_level(G, "device"), 10)
        self.assertIn("array_cable", edge_levels(G))

    def test_custom_string_list_len_mismatch_raises(self, _sf, _sh, _draw):
        # len(string_list) != n_strings -> ValueError
        with self.assertRaises(ValueError):
            self.w.layout4_wind(
                n_turbines=9, n_strings=3, substation_node=1, string_list=[3, 6], tow_string_shutdown = True, show_plot=False
            )

    def test_custom_string_list_sum_mismatch_raises(self, _sf, _sh, _draw):
        # Sum of sizes does not match total turbines -> ValueError
        with self.assertRaises(ValueError):
            self.w.layout4_wind(
                n_turbines=9, n_strings=3, substation_node=1, string_list=[2, 3, 3], tow_string_shutdown = True, show_plot=False
            )

@patch("oriom.domain.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
@patch("matplotlib.pyplot.show")
@patch("matplotlib.pyplot.savefig")
class TestLayout5Wind(unittest.TestCase):
    def setUp(self):
        self.w = Layout_Wind()

    def test_list_valid_5(self, _sf, _sh, _draw):
        # Custom non-uniform split: 10 turbines into 3 strings [3,3,4]
        G = self.w.layout5_wind(
            n_turbines=12, n_strings=4, substation_node=1, n_string_to_connector = 2, tow_string_shutdown = True, show_plot=False
        )
        self.assertEqual(count_nodes_by_level(G, "device"), 12)
        self.assertEqual(count_nodes_by_level(G, "hub"), 2)
        self.assertIn("dyn_cable-sub", edge_levels(G))


@patch("oriom.domain.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
@patch("matplotlib.pyplot.show")
@patch("matplotlib.pyplot.savefig")
class TestLayout6Wind(unittest.TestCase):
    def setUp(self):
        self.w = Layout_Wind()

    def test_list_valid_6(self, _sf, _sh, _draw):
        # Custom non-uniform split: 10 turbines into 3 strings [3,3,4]
        G_ = self.w.layout6_wind(
            n_turbines=15, n_strings=15, substation_node=1, n_string_to_connector = 5, tow_string_shutdown = True, show_plot=False
        )
        self.assertEqual(count_nodes_by_level(G_, 'device'), 15)
        self.assertEqual(count_nodes_by_level(G_, "hub"), 3)
        self.assertIn("dyn_cable-sub", edge_levels(G_))

@patch("oriom.domain.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
@patch("matplotlib.pyplot.show")
@patch("matplotlib.pyplot.savefig")
class TestDispatcher(unittest.TestCase):
    def setUp(self):
        self.w = Layout_Wind()

    def test_dispatch_layout1(self, _sf, _sh, _draw):
        G = self.w.layout_wind(n_layout=1, n_turbines=6, n_strings=3, show_plot=False)
        self.assertIsInstance(G, nx.DiGraph)

    def test_dispatch_layout2(self, _sf, _sh, _draw):
        G = self.w.layout_wind(n_layout=2, n_turbines=12, n_strings=3, n_substations=2, show_plot=False)
        self.assertIsInstance(G, nx.DiGraph)

    def test_dispatch_layout3(self, _sf, _sh, _draw):
        G = self.w.layout_wind(n_layout=3, n_turbines=6, n_strings=3, n_exports=2, show_plot=False)
        self.assertIsInstance(G, nx.DiGraph)

    def test_dispatch_layout4_default_equal_split(self, _sf, _sh, _draw):
        # Not 73 or 40; divisible -> equal split is used
        G = self.w.layout_wind(n_layout=4, n_turbines=12, n_strings=3, show_plot=False)
        self.assertIsInstance(G, nx.DiGraph)
        self.assertEqual(count_nodes_by_level(G, "device"), 12)

    def test_dispatch_layout4_known_pattern_40(self, _sf, _sh, _draw):
        # Triggers predefined string_list for 40 turbines
        G = self.w.layout_wind(n_layout=4, n_turbines=40, n_strings=6, show_plot=False)
        self.assertIsInstance(G, nx.DiGraph)
        self.assertEqual(count_nodes_by_level(G, "device"), 40)

    def test_dispatch_invalid_layout_raises(self, _sf, _sh, _draw):
        with self.assertRaises(ValueError):
            self.w.layout_wind(n_layout=99, n_turbines=6, n_strings=3, show_plot=False)

    def test_dispatch_invalid_layout_5_raises(self, _sf, _sh, _draw):
        # Sum of sizes does not match total turbines -> ValueError
        with self.assertRaises(ValueError):
            self.w.layout_wind(
                n_layout = 5, n_turbines=12, n_strings=5, n_substations=1, n_string_to_connector = 2, tow_string_shutdown = True, show_plot=True
            )

    def test_dispatch_invalid_layout_6_raises(self, _sf, _sh, _draw):
        # Sum of sizes does not match total turbines -> ValueError
        with self.assertRaises(ValueError):
            self.w.layout_wind(
                n_layout = 6, n_turbines=15, n_strings=2, n_substations=1, n_string_to_connector = 2, tow_string_shutdown = True, show_plot=True
            )

if __name__ == "__main__":
    unittest.main(verbosity=2)
