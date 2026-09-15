# test_TowData
import unittest
import pandas as pd

from oriom.domain.TowData import TowData


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
        try:
            a = self.operations[op_id]
        except KeyError:
            raise NameError()
        return a

    def find_operation_stats_pmax(self, op_id):
        return self.stats.get(op_id, None)

class DummyFail:
    def __init__(self, level_failure):
        self.level_failure = level_failure

class DummyMainOper:
    def __init__(self, port, site, site_port, level_failure):
        self.op_tow_port = port
        self.op_tow_site = site
        self.op_tow_site_port = site_port
        self.failures = [DummyFail(level_failure)]


# ---------------------------
# Test class
# ---------------------------
class TestTowData(unittest.TestCase):

    def setUp(self, a=str(1), b=str(2), c=str(3), d=str(10), e=str(20), f='device', g = False):
        """Create reusable objects for tests"""

        # Base operations
        self.op_port = DummyOperation(a)
        self.op_site = DummyOperation(b)
        self.op_site_port = DummyOperation(c)

        # Additional operations
        self.add_port = DummyOperation(d.split('_')[0])
        self.add_site = DummyOperation(e.split('_')[0])

        self.op_port.addition_op_tow = self.add_port
        self.op_site.addition_op_tow = self.add_site

        # Stats
        self.stats = {
            a: "stat_port",
            b: "stat_site",
            c: "stat_site_port",
            d: "stat_add_port",
            e: "stat_add_site",
        }

        # Finder
        self.finder = DummyFinder(
            operations={
                a: self.op_port,
                b: self.op_site,
                c: self.op_site_port,
                d.split('_')[0]: self.add_port,
                e.split('_')[0]: self.add_site,
                '10_last_string_device': DummyOperation('10_last_string_device'),
                '20_last_string_device': DummyOperation('20_last_string_device'),
            },
            stats=self.stats
        )

        self.main_oper = DummyMainOper(a, b, c, f)

    # ---------------------------
    # Test __post_init__
    # ---------------------------
    def test_post_init_dictionaries(self):
        tow_data = TowData.from_operation(self.finder, self.main_oper)

        # Check schedule dictionary
        self.assertIn(str(1), tow_data.dict_tow_oper_sched)
        self.assertIn(str(2), tow_data.dict_tow_oper_sched)
        self.assertIn(str(3), tow_data.dict_tow_oper_sched)

        # Check last index dictionary
        self.assertEqual(tow_data.dict_tow_oper_last_idx[str(1)], 1)
        self.assertEqual(tow_data.dict_tow_oper_last_idx[str(2)], 1)
        self.assertEqual(tow_data.dict_tow_oper_last_idx[str(3)], 1)

        # Check stats dictionary
        self.assertEqual(tow_data.dict_oper_stat[str(1)], "stat_port")
        self.assertEqual(tow_data.dict_oper_stat[str(2)], "stat_site")
        self.assertEqual(tow_data.dict_oper_stat[str(3)], "stat_site_port")

    # ---------------------------
    # Test id_dict_oper
    # ---------------------------
    def test_id_dict_oper(self):
        tow_data = TowData.from_operation(self.finder, self.main_oper)

        oper_dict = {}
        op_at_port = DummyOperation(str(99))

        tow_data.id_dict_oper(oper_dict, op_at_port)

        # All operations should be registered
        expected_ids = {str(99), str(1), str(2), str(10), str(20)}
        self.assertEqual(set(oper_dict.keys()), expected_ids)

    # ---------------------------
    # Test from_operation
    # ---------------------------
    def test_from_operation_basic(self):
        tow_data = TowData.from_operation(self.finder, self.main_oper)

        # Check main operations
        self.assertEqual(tow_data.tow_op_port.id, str(1))
        self.assertEqual(tow_data.tow_op_site.id, str(2))
        self.assertEqual(tow_data.tow_site_port.id, str(3))

        # Check additional operations
        self.assertEqual(tow_data.add_op_tow_port.id, str(10))
        self.assertEqual(tow_data.add_op_tow_site.id, str(20))

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

    # ---------------------------
    # Test from_operation WITH LAST DEVICE
    # ---------------------------
    def test_from_operation_basic_last_device(self, g = True):
        self.setUp(d = '10_last_string_device', f = 'last_string_device')
        tow_data = TowData.from_operation(self.finder, self.main_oper)

        # Check main operations
        self.assertEqual(tow_data.tow_op_port.id, str(1))
        self.assertEqual(tow_data.tow_op_site.id, str(2))
        self.assertEqual(tow_data.tow_site_port.id, str(3))

        # Check additional operations
        self.assertEqual(tow_data.add_op_tow_port.id, '10_last_string_device')
        self.assertEqual(tow_data.add_op_tow_site.id, '20_last_string_device')

        # Check stats
        self.assertEqual(tow_data.tow_op_port_stat, "stat_port")
        self.assertEqual(tow_data.oper_stat_op_tow_port, "stat_add_port")

    # ---------------------------
    # Test from_operation WITH LAST DEVICE error name
    # ---------------------------
    def test_NameError_from_operation_basic_last_device(self):
        self.setUp(f = 'last_string_device', g = True)
        self.finder = DummyFinder(
            operations={
                self.op_port.id: self.op_port,
                self.op_site.id: self.op_site,
                self.op_site_port.id: self.op_site_port,
                self.add_port.id: self.add_port,
                self.add_site.id: self.add_site,
            },
            stats={
            self.op_port.id: "stat_port",
            self.op_site.id: "stat_site",
            self.op_site_port.id: "stat_site_port",
            self.add_port.id: "stat_add_port",
            self.add_site.id: "stat_add_site",
            }
        )

        tow_data = TowData.from_operation(self.finder, self.main_oper)

        self.assertEqual(tow_data.add_op_tow_port.id, '10')



if __name__ == "__main__":
    unittest.main()