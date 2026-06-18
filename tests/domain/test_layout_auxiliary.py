# tests/test_layout_aux.py
import os
import tempfile
import unittest

import matplotlib
matplotlib.use("Agg")  # headless
import networkx as nx

from oriom.domain.Layouts.Layout_Auxiliary import Layout_Aux


class TestLayoutAuxAddSubstationAndShore(unittest.TestCase):
    def test_add_substation_and_shore_wind_defaults(self):
        G = nx.DiGraph()
        out = Layout_Aux.add_substation_and_shore(G, n_strings=4, substation_node=5, pv=False)

        # nodes exist
        self.assertIn(0, out.nodes)
        self.assertIn(5, out.nodes)

        # attributes
        shore = out.nodes[0]
        sub = out.nodes[5]
        self.assertEqual(shore["name"], "SHORE")
        self.assertEqual(shore["level"], "shore")
        self.assertEqual(shore["power"], 0)
        # (n_strings-1)/2 = 1.5; shore_y = -3; sub_y = -1 for pv=False
        self.assertEqual(shore["coords"], ((4 - 1) / 2, -3))
        self.assertEqual(sub["coords"], ((4 - 1) / 2, -1))
        self.assertEqual(sub["name"], "Sub")
        self.assertEqual(sub["level"], "substation")

        # edge and edge attributes
        self.assertIn((5, 0), out.edges)
        e = out.edges[(5, 0)]
        self.assertEqual(e["name"], "export_cable")
        self.assertEqual(e["level"], "exp_cable")
        self.assertTrue(e["visible"])
        self.assertIsNone(e["p_limit"])

    def test_add_substation_and_shore_pv_offsets(self):
        G = nx.DiGraph()
        out = Layout_Aux.add_substation_and_shore(G, n_strings=3, substation_node=2, pv=True)
        shore = out.nodes[0]
        sub = out.nodes[2]
        # pv=True -> shore_y=-7, sub_y=-6
        self.assertEqual(shore["coords"], ((3 - 1) / 2, -7))
        self.assertEqual(sub["coords"], ((3 - 1) / 2, -6))


class TestLayoutAuxDrawLayout(unittest.TestCase):
    def test_draw_layout_saves_file_and_handles_arc_edges(self):
        # Build a small graph with an arc edge attribute 'rad'
        G = nx.DiGraph()
        G.add_node(0, name="A", coords=(0, 0))
        G.add_node(1, name="B", coords=(1, 0))
        G.add_edge(0, 1, name="e1")
        G.add_edge(1, 0, name="e2", rad=0.2)  # triggers arc drawing branch

        with tempfile.TemporaryDirectory() as tmp:
            title = "layout_snapshot"
            Layout_Aux.draw_layout(G, save_dir=tmp, show_plot=False, title=title)
            out_path = os.path.join(tmp, f"{title}.jpg")
            self.assertTrue(os.path.exists(out_path), "Expected saved JPG not found")


class TestIntervalExtractNewBehaviour(unittest.TestCase):
    def test_even_split(self):
        # [1..6] into 3 chunks -> equal sizes
        out = Layout_Aux.interval_extract([1, 2, 3, 4, 5, 6], n_times=3)
        self.assertEqual(out, [[1, 2], [3, 4], [5, 6]])

    def test_uneven_split_remainder_goes_first(self):
        # 7 items, 3 chunks -> sizes [3,2,2]
        out = Layout_Aux.interval_extract([1, 2, 3, 4, 5, 6, 7], n_times=3)
        self.assertEqual(out, [[1, 2], [3, 4], [5, 6], [7]])

    def test_more_chunks_than_items(self):
        # Empties are filtered out
        out = Layout_Aux.interval_extract([10, 11], n_times=5)
        self.assertEqual(out, [[10,11]])

    def test_single_chunk(self):
        out = Layout_Aux.interval_extract([3, 1], n_times=1)
        self.assertEqual(out, [[1, 3]])

    def test_empty_input(self):
        out = Layout_Aux.interval_extract([], n_times=3)
        self.assertEqual(out, [])

    def test_zero_chunks_raises(self):
        with self.assertRaises(ZeroDivisionError):
            Layout_Aux.interval_extract([1, 2, 3], n_times=0)

if __name__ == "__main__":
    unittest.main(verbosity=2)

