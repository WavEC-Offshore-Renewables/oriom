# tests/test_layout_wave.py
import unittest
from unittest.mock import patch
import networkx as nx

from oriom.classes.Layouts.Layouts_Wave import Layout_Wave


def count_nodes_by_level(G: nx.DiGraph, level: str) -> int:
    return sum(1 for _, d in G.nodes(data=True) if d.get("level") == level)


def edge_levels(G: nx.DiGraph):
    return list(nx.get_edge_attributes(G, "level").values())


def get_node_by_name(G: nx.DiGraph, name: str):
    for n, d in G.nodes(data=True):
        if d.get("name") == name:
            return n, d
    return None, None


class TestCheckInputWave(unittest.TestCase):
    def setUp(self):
        self.w = Layout_Wave()

    def test_valid(self):
        self.w.check_input_wave(n_wec=12, n_strings=3)

    def test_invalid_not_divisible_raises(self):
        with self.assertRaises(ValueError):
            self.w.check_input_wave(n_wec=10, n_strings=3)


@patch("oriom.classes.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
@patch("matplotlib.pyplot.show")
@patch("matplotlib.pyplot.savefig")
class TestLayout1Wave(unittest.TestCase):
    def setUp(self):
        self.w = Layout_Wave()

    def test_single_wec_chain(self, _sf, _sh, _draw):
        G = self.w.layout1_wave(n_wec=1, n_strings=1, substation_node=1, tow_string_shutdown = False, show_plot=False)
        # SHORE exist
        shore_n, shore_d = get_node_by_name(G, "SHORE")
        self.assertIsNotNone(shore_n)
        # Substation opn requested node
        sub_n, sub_d = get_node_by_name(G, "Sub")
        self.assertIsNotNone(sub_n)
        self.assertEqual(sub_n, 1)
        # only one device
        self.assertEqual(count_nodes_by_level(G, "device"), 1)
        # One array_cable exist
        self.assertIn("array_cable", edge_levels(G))

    def test_multiple_wec_strings(self, _sf, _sh, _draw):
        G = self.w.layout1_wave(n_wec=6, n_strings=3, substation_node=1, tow_string_shutdown = False, show_plot=False)
        self.assertEqual(count_nodes_by_level(G, "device"), 6)
        #Exiost connections array and connections substation
        levels = edge_levels(G)
        self.assertGreaterEqual(levels.count("array_cable"), 6 - 1)
        sub_n, _ = get_node_by_name(G, "Sub")
        self.assertIsNotNone(sub_n)


@patch("oriom.classes.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
@patch("matplotlib.pyplot.show")
@patch("matplotlib.pyplot.savefig")
class TestLayout2Wave(unittest.TestCase):
    def setUp(self):
        self.w = Layout_Wave()

    def test_invalid_division_raises(self, _sf, _sh, _draw):
        with self.assertRaises(ValueError):
            self.w.layout2_wave(n_wec=10, n_strings=2, n_substations=3, tow_string_shutdown = False, show_plot=False)

    def test_two_farms_redundant_links(self, _sf, _sh, _draw):
        # 12 WEC totals, 2 substations -> 6 each
        G = self.w.layout2_wave(n_wec=12, n_strings=3, n_substations=2, tow_string_shutdown = False, show_plot=False)
        # 2 substations
        self.assertEqual(count_nodes_by_level(G, "substation"), 2)
        # 12 device
        self.assertEqual(count_nodes_by_level(G, "device"), 12)
        # Redundant cables between substation (2 directions)
        levels = edge_levels(G)
        self.assertGreaterEqual(levels.count("redundant_cable"), 2)


@patch("oriom.classes.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
@patch("matplotlib.pyplot.show")
@patch("matplotlib.pyplot.savefig")
class TestLayout3Wave(unittest.TestCase):
    def setUp(self):
        self.w = Layout_Wave()

    def test_multiple_exports_add_dummy_nodes(self, _sf, _sh, _draw):
        # n_exports=3 => 2 dummy + 3 export cables to SHORE in total
        G = self.w.layout3_wave(n_wec=6, n_strings=3, n_exports=3, tow_string_shutdown = False, show_plot=False)
        # Dummy nodes created
        self.assertEqual(count_nodes_by_level(G, "dummy"), 2)
        # Export cables: base + (n_exports-1) created
        levels = edge_levels(G)
        self.assertGreaterEqual(levels.count("exp_cable"), 3)
        self.assertEqual(levels.count("exp_cable_dummy"), 2)


@patch("oriom.classes.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
@patch("matplotlib.pyplot.show")
@patch("matplotlib.pyplot.savefig")
class TestLayout4Wave(unittest.TestCase):
    def setUp(self):
        self.w = Layout_Wave()

    def test_invalid_corpower_count_raises(self, _sf, _sh, _draw):
        # With n_strings=2 order is [12,13]; n_wec isn't 25 => error
        with self.assertRaises(ValueError):
            self.w.layout4_wave(n_wec=24, n_strings=2, substation_node=1, show_plot=False)

    def test_valid_corpower_distribution(self, _sf, _sh, _draw):
        # n_strings=2 -> chunk 12 e 13 => n_wec=25 valid
        G = self.w.layout4_wave(n_wec=25, n_strings=2, substation_node=1, show_plot=False)
        # 25 device
        self.assertEqual(count_nodes_by_level(G, "device"), 25)
        # Exist one feeder and one array_cable
        levels = edge_levels(G)
        self.assertIn("exp_cable_island", levels)  # feeder_cable level
        self.assertIn("array_cable", levels)


@patch("oriom.classes.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
@patch("matplotlib.pyplot.show")
@patch("matplotlib.pyplot.savefig")
class TestLayout5Wave(unittest.TestCase):
    def setUp(self):
        self.w = Layout_Wave()

    def test_layout5_returns_graph(self, _sf, _sh, _draw):
        G = self.w.layout5_wave(n_wec=4, n_strings=3, substation_node=1, show_plot=False)
        self.assertIsInstance(G, nx.DiGraph)


@patch("oriom.classes.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
@patch("matplotlib.pyplot.show")
@patch("matplotlib.pyplot.savefig")
class TestDispatcher(unittest.TestCase):
    def setUp(self):
        self.w = Layout_Wave()

    def test_dispatch_layout1(self, _sf, _sh, _draw):
        G = self.w.layout_wave(n_layout=1, n_wec=6, n_strings=3, show_plot=False)
        self.assertIsInstance(G, nx.DiGraph)

    def test_dispatch_layout2(self, _sf, _sh, _draw):
        G = self.w.layout_wave(n_layout=2, n_wec=12, n_strings=3, n_substations=2, show_plot=False)
        self.assertIsInstance(G, nx.DiGraph)

    def test_dispatch_layout3(self, _sf, _sh, _draw):
        G = self.w.layout_wave(n_layout=3, n_wec=6, n_strings=3, n_exports=2, show_plot=False)
        self.assertIsInstance(G, nx.DiGraph)

    def test_dispatch_layout4(self, _sf, _sh, _draw):
        G = self.w.layout_wave(n_layout=4, n_wec=25, n_strings=2, show_plot=False)
        self.assertIsInstance(G, nx.DiGraph)

    def test_dispatch_layout5_returns_graph(self, _sf, _sh, _draw):
        G = self.w.layout_wave(n_layout=5, n_wec=4, n_strings=3, show_plot=False)
        self.assertIsInstance(G, nx.DiGraph)

    def test_dispatch_invalid_layout_raises(self, _sf, _sh, _draw):
        with self.assertRaises(ValueError):
            self.w.layout_wave(n_layout=99, n_wec=6, n_strings=3, show_plot=False)

if __name__ == "__main__":
    unittest.main(verbosity=2)
