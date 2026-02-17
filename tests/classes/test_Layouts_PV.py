# tests/test_layout_pv.py
import unittest
from unittest.mock import patch
import networkx as nx

from oriom.classes.Layouts.Layouts_PV import Layout_PV


def count_nodes_by_level(G: nx.DiGraph, level: str) -> int:
    return sum(1 for _, d in G.nodes(data=True) if d.get("level") == level)


def sum_power_by_level(G: nx.DiGraph, level: str) -> int:
    return sum(d.get("power", 0) for _, d in G.nodes(data=True) if d.get("level") == level)


def get_node_by_name(G: nx.DiGraph, name: str):
    for n, d in G.nodes(data=True):
        if d.get("name") == name:
            return n, d
    return None, None


class TestCheckInputPV(unittest.TestCase):
    def setUp(self):
        self.pv = Layout_PV()

    def test_valid_inputs_pass(self):
        # n_panels divisible by n_inverters; (n_panels/n_inverters) divisible by n_strings
        self.pv.check_input_pv(n_panels=36, n_strings=3, n_inverters=6)

    def test_panels_not_divisible_by_inverters_raises(self):
        with self.assertRaises(ValueError):
            self.pv.check_input_pv(n_panels=37, n_strings=3, n_inverters=6)

    def test_panels_per_inverter_not_divisible_by_strings_raises(self):
        # 36/5 = 7.2 -> not divisible for 3
        with self.assertRaises(ValueError):
            self.pv.check_input_pv(n_panels=36, n_strings=3, n_inverters=5)

    def test_upstream_divisibility_with_substations_raises(self):
        # mvtransformers % n_substations != 0 -> error
        with self.assertRaises(ValueError):
            self.pv.check_input_pv(n_panels=36, n_strings=3, n_inverters=6,
                                   n_substations=2, n_mvtransformers=3)

        # inverters % mvtransformers != 0 -> error
        with self.assertRaises(ValueError):
            self.pv.check_input_pv(n_panels=36, n_strings=3, n_inverters=7,
                                   n_substations=1, n_mvtransformers=3)


@patch("oriom.classes.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
class TestLayout1PV(unittest.TestCase):
    def setUp(self):
        self.pv = Layout_PV()

    def test_layout1_basic_structure(self, _mock_draw):
        # 36 panels, 3 strings per inverter, 6 inverters => 6 panels/inverter, 2 per string
        G = self.pv.layout1_pv(n_panels=36, n_strings=3, n_inverters=6, tow_string_shutdown = False, save_dir=None, show_plot=False)

        # SHORE (node name) and substation presents
        shore_n, shore_d = get_node_by_name(G, "SHORE")
        self.assertIsNotNone(shore_n)
        self.assertEqual(shore_d.get("level"), "shore")

        # SHORE y for layout1 (pv=False) is -3
        self.assertEqual(shore_d.get("coords")[1], -3)

        # One substation
        self.assertEqual(count_nodes_by_level(G, "substation"), 1)

        # Inverter: must be n_inverters
        self.assertEqual(count_nodes_by_level(G, "inverter"), 6)

        # Panels as "device": must be n_panels
        self.assertEqual(count_nodes_by_level(G, "device"), 36)

        # Each inverter connected to substation (Exist at least one edge level dyn_cable-sub)
        edge_levels = nx.get_edge_attributes(G, "level").values()
        self.assertIn("dyn_cable-sub", edge_levels)

        # Exist cable array (opv-cable)
        self.assertIn("array_cable", edge_levels)


@patch("oriom.classes.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
class TestLayout3PV(unittest.TestCase):
    def setUp(self):
        self.pv = Layout_PV()

    def test_layout3_divisibility_checks(self, _mock_draw):
        # n_inverters not divisible for n_mvtransformers -> error
        with self.assertRaises(ValueError):
            self.pv.layout3_pv(n_strings=2, n_inverters=5,
                               n_mvtransformers=3, n_substations=1, tow_string_shutdown = False)

        # n_mvtransformers not divisible for n_substations -> error
        with self.assertRaises(ValueError):
            self.pv.layout3_pv(n_strings=2, n_inverters=6,
                               n_mvtransformers=5, n_substations=2, tow_string_shutdown = False)

    def test_layout3_counts(self, _mock_draw):
        G = self.pv.layout3_pv(n_strings=2, n_inverters=6,
                               n_mvtransformers=3, n_substations=3, tow_string_shutdown = False,
                               save_dir=None, show_plot=False)

        # SHORE exist
        shore_n, _ = get_node_by_name(G, "SHORE")
        self.assertIsNotNone(shore_n)

        # substation == 3
        self.assertEqual(count_nodes_by_level(G, "substation"), 3)

        # inverter == 6
        self.assertEqual(count_nodes_by_level(G, "inverter"), 6)

        # devices (array per stringa) == n_inverters * n_strings
        self.assertEqual(count_nodes_by_level(G, "device"), 6 * 2)


@patch("oriom.classes.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
class TestLayout2PV(unittest.TestCase):
    def setUp(self):
        self.pv = Layout_PV()

    def test_layout2_ok_and_array_cable_between_islands(self, _mock_draw):
        G = self.pv.layout2_pv(
            n_panels=36, n_strings=3, n_inverters=6,
            n_mvtransformers=3, n_substations=3, n_island_per_array_cable = 3,
            save_dir=None, show_plot=False
        )

        # islands == 3
        self.assertEqual(count_nodes_by_level(G, "island"), 3)

        # inverters == 6; power sum == 36
        self.assertEqual(count_nodes_by_level(G, "inverter"), 6)
        self.assertEqual(sum_power_by_level(G, "inverter"), 36)

        # SHORE y for PV=True is -7
        shore_n, shore_d = get_node_by_name(G, "SHORE")
        self.assertIsNotNone(shore_n)
        self.assertEqual(shore_d.get("coords")[1], -7)

        # Exist at least one 'array_cable' (connection between islands >1)
        edge_levels = nx.get_edge_attributes(G, "level").values()
        self.assertIn("array_cable", edge_levels)

    def test_layout2_rule_enforced_in_dispatcher(self, _mock_draw):
        with self.assertRaises(ValueError):
            self.pv.layout_pv(
                n_layout=2, n_panels=36, n_strings=3, n_inverters=6,
                n_mvtransformers=6, n_substations=4, n_island_per_array_cable = 3,
                save_dir=None, show_plot=False
            )


@patch("oriom.classes.Layouts.Layout_Auxiliary.Layout_Aux.draw_layout")
class TestDispatcher(unittest.TestCase):
    def setUp(self):
        self.pv = Layout_PV()

    def test_dispatch_layout1(self, _mock_draw):
        G = self.pv.layout_pv(
            n_layout=1, n_panels=36, n_strings=3, n_inverters=6,
            n_mvtransformers=0, n_substations=0, save_dir=None, show_plot=False
        )
        self.assertIsInstance(G, nx.DiGraph)
        # check: device == n_panels
        self.assertEqual(sum(1 for _, d in G.nodes(data=True) if d.get("level") == "device"), 36)

    def test_dispatch_layout3(self, _mock_draw):
        G = self.pv.layout_pv(
            n_layout=3, n_panels=0, n_strings=2, n_inverters=6,
            n_mvtransformers=3, n_substations=3, save_dir=None, show_plot=False
        )
        self.assertIsInstance(G, nx.DiGraph)

    def test_dispatch_layout2_ok(self, _mock_draw):
        G = self.pv.layout_pv(
            n_layout=2, n_panels=36, n_strings=3, n_inverters=6,
            n_mvtransformers=6, n_substations=3, save_dir=None, show_plot=False
        )
        self.assertIsInstance(G, nx.DiGraph)

    def test_dispatch_invalid_layout_raises(self, _mock_draw):
        with self.assertRaises(ValueError):
            self.pv.layout_pv(
                n_layout=99, n_panels=36, n_strings=3, n_inverters=6,
                n_mvtransformers=6, n_substations=3, save_dir=None, show_plot=False
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
