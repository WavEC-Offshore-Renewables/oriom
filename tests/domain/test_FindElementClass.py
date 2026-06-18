import unittest
from oriom.domain.FindElementClass import Find_Element


# --- Dummies --------------------------------------------------------------

class DummyOp:
    def __init__(self, id_, tow_to_port=False):
        self.id = id_
        self.tow_to_port = tow_to_port
        # Find_Element.find_oper_schedule() reads 'ts_data' directly on the operation
        self.ts_data = f"data_{id_}"


class DummyOpStat:
    def __init__(self, id_):
        self.id = id_


class DummyVessel:
    def __init__(self, id_):
        self.id = id_


class DummyFailure:
    def __init__(self, id_, operation_triggered, name="failX"):
        # Find_Element builds failures_dict_id from 'id'
        self.id = id_
        self.operation_triggered = operation_triggered
        self.name = name


# --- Tests ----------------------------------------------------------------

class TestFindElement(unittest.TestCase):
    def setUp(self):
        # operations
        self.ops = [DummyOp("A1"), DummyOp("B2")]
        # stats (P50 / main)
        self.ops_stats = [DummyOpStat("A1"), DummyOpStat("B2")]
        # stats Pmax (P90)
        self.ops_stats_pmax = [DummyOpStat("A1"), DummyOpStat("B2")]
        # vessels (lookup is case-insensitive; dict stores lowercase ids)
        self.vessels = [DummyVessel("V1"), DummyVessel("CTV01")]
        # failures (both by operation_triggered and by id)
        self.failures = [DummyFailure("F1", operation_triggered="A1")]

        self.lookup = Find_Element(
            operations=self.ops,
            operations_stats=self.ops_stats,
            operations_stats_pmax=self.ops_stats_pmax,
            vessels=self.vessels,
            failures=self.failures,
        )

    # --- operations -------------------------------------------------------

    def test_find_operation_success(self):
        op = self.lookup.find_operation("A1")
        self.assertEqual(op.id, "A1")

    def test_find_operation_error(self):
        with self.assertRaises(NameError):
            self.lookup.find_operation("XYZ")

    # --- operation stats (P50/main) --------------------------------------

    def test_find_operation_stats_success(self):
        op_stat = self.lookup.find_operation_stats("A1")
        self.assertEqual(op_stat.id, "A1")

    def test_find_operation_stats_error(self):
        with self.assertRaises(NameError):
            self.lookup.find_operation_stats("ZZZ")

    # --- operation stats Pmax (P90) --------------------------------------

    def test_find_operation_stats_pmax_success(self):
        op_stat = self.lookup.find_operation_stats_pmax("B2")
        self.assertEqual(op_stat.id, "B2")

    def test_find_operation_stats_pmax_error(self):
        with self.assertRaises(NameError):
            self.lookup.find_operation_stats_pmax("NOPE")

    # --- vessels ----------------------------------------------------------

    def test_find_vessel_success(self):
        vessel = self.lookup.find_vessel("ctv01")  # case-insensitive
        self.assertEqual(vessel.id, "CTV01")

    def test_find_vessel_error(self):
        with self.assertRaises(NameError):
            self.lookup.find_vessel("MISSING")

    # --- failures ---------------------------------------------------------

    def test_find_failure_success_returns_list(self):
        failure_list = self.lookup.find_failure(self.ops[0])  # op id "A1"
        self.assertIsInstance(failure_list, list)
        self.assertEqual(len(failure_list), 1)
        self.assertEqual(failure_list[0].operation_triggered, "A1")

    def test_find_failure_tow_to_port_returns_zero(self):
        op_tow = DummyOp("Z9", tow_to_port=True)
        result = self.lookup.find_failure(op_tow)
        self.assertEqual(result, 0)

    def test_find_failure_error(self):
        with self.assertRaises(NameError):
            self.lookup.find_failure(DummyOp("ZZZ"))

    def test_find_failure_from_id_success(self):
        f = self.lookup.find_failure_from_id("F1")
        self.assertEqual(f.operation_triggered, "A1")

    def test_find_failure_from_id_error(self):
        with self.assertRaises(NameError):
            self.lookup.find_failure_from_id("NO_FAIL")

    # --- schedules --------------------------------------------------------

    def test_find_oper_schedule_success(self):
        # API expects an operation id; returns that operation's ts_data
        ts = self.lookup.find_oper_schedule("A1")
        self.assertEqual(ts, "data_A1")


if __name__ == '__main__':

    unittest.main(verbosity=2)
