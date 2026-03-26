# test_TowData
import unittest
import pandas as pd

from oriom.classes.TowData import TowData


# ---------------------------
# Dummy helper classes
# ---------------------------
class DummyOperation:
    def __init__(self, op_id, addition_op_tow=None):
        self.id = op_id
        self.addition_op_tow = addition_op_tow
        self.ts_data = DummyTSData()


class DummyTSData:
    def __init__(self):
        self.oper_sched = pd.DataFrame({"a": [1, 2]})
        self.last_valid_index = 1


class DummyFinder:
    def __init__(self, operations, stats):
        self.operations = operations
        self.stats = stats

    def find_operation(self, op_id):
        return self.operations[op_id]

    def find_operation_stats_pmax(self, op_id):
        return self.stats.get(op_id, None)


class DummyMainOper:
    def __init__(self, port, site, site_port):
        self.op_tow_port = port
        self.op_tow_site = site
        self.op_tow_site_port = site_port


# ---------------------------
# Test class
# ---------------------------
class TestTowData(unittest.TestCase):

    def setUp(self):
        """Create reusable objects for tests"""

        # Base operations
        self.op_port = DummyOperation(1)
        self.op_site = DummyOperation(2)
        self.op_site_port = DummyOperation(3)

        # Additional operations
        self.add_port = DummyOperation(10)
        self.add_site = DummyOperation(20)

        self.op_port.addition_op_tow = self.add_port
        self.op_site.addition_op_tow = self.add_site

        # Stats
        self.stats = {
            1: "stat_port",
            2: "stat_site",
            3: "stat_site_port",
            10: "stat_add_port",
            20: "stat_add_site",
        }

        # Finder
        self.finder = DummyFinder(
            operations={
                1: self.op_port,
                2: self.op_site,
                3: self.op_site_port,
            },
            stats=self.stats
        )

        self.main_oper = DummyMainOper(1, 2, 3)

    # ---------------------------
    # Test __post_init__
    # ---------------------------
    def test_post_init_dictionaries(self):
        tow_data = TowData.from_operation(self.finder, self.main_oper)

        # Check schedule dictionary
        self.assertIn(1, tow_data.dict_tow_oper_sched)
        self.assertIn(2, tow_data.dict_tow_oper_sched)
        self.assertIn(3, tow_data.dict_tow_oper_sched)

        # Check last index dictionary
        self.assertEqual(tow_data.dict_tow_oper_last_idx[1], 1)
        self.assertEqual(tow_data.dict_tow_oper_last_idx[2], 1)
        self.assertEqual(tow_data.dict_tow_oper_last_idx[3], 1)

        # Check stats dictionary
        self.assertEqual(tow_data.dict_oper_stat[1], "stat_port")
        self.assertEqual(tow_data.dict_oper_stat[2], "stat_site")
        self.assertEqual(tow_data.dict_oper_stat[3], "stat_site_port")

    # ---------------------------
    # Test id_dict_oper
    # ---------------------------
    def test_id_dict_oper(self):
        tow_data = TowData.from_operation(self.finder, self.main_oper)

        oper_dict = {}
        op_at_port = DummyOperation(99)

        tow_data.id_dict_oper(oper_dict, op_at_port)

        # All operations should be registered
        expected_ids = {99, 1, 2, 10, 20}
        self.assertEqual(set(oper_dict.keys()), expected_ids)

    # ---------------------------
    # Test from_operation
    # ---------------------------
    def test_from_operation_basic(self):
        tow_data = TowData.from_operation(self.finder, self.main_oper)

        # Check main operations
        self.assertEqual(tow_data.tow_op_port.id, 1)
        self.assertEqual(tow_data.tow_op_site.id, 2)
        self.assertEqual(tow_data.tow_site_port.id, 3)

        # Check additional operations
        self.assertEqual(tow_data.add_op_tow_port.id, 10)
        self.assertEqual(tow_data.add_op_tow_site.id, 20)

        # Check stats
        self.assertEqual(tow_data.tow_op_port_stat, "stat_port")
        self.assertEqual(tow_data.oper_stat_op_tow_port, "stat_add_port")

    def test_from_operation_without_additional_ops(self):
        # Remove additional operations
        self.op_port.addition_op_tow = None
        self.op_site.addition_op_tow = None

        tow_data = TowData.from_operation(self.finder, self.main_oper)

        self.assertIsNone(tow_data.add_op_tow_port)
        self.assertIsNone(tow_data.add_op_tow_site)
        self.assertIsNone(tow_data.oper_stat_op_tow_port)
        self.assertIsNone(tow_data.oper_stat_op_site)

    def test_safe_getattr_data_extraction(self):
        tow_data = TowData.from_operation(self.finder, self.main_oper)

        # Ensure DataFrame is correctly extracted
        self.assertIsInstance(tow_data.tow_port_oper_sched, pd.DataFrame)
        self.assertEqual(tow_data.last_valid_idx_tow_port, 1)


if __name__ == "__main__":
    unittest.main()