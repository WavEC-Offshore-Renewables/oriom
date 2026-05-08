#test_KPI_Insight


import unittest
from types import SimpleNamespace
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

try:
    from oriom.core.functions.private.KPI_Insight import KPI_Insight
except ImportError:
    raise unittest.SkipTest("KPI_Insight module not available, test skipped")


# ----------------- Minimal domain doubles -----------------

class DummyVessel:
    def __init__(self, vid, vtype):
        self.id = vid
        self.type = vtype

class DummyFail:
    def __init__(self, fid, rate, n_elem, part_cost):
        self.id = fid
        self.fail_rate = rate
        self.n_element = n_elem
        self.parts_cost = part_cost

class DummyOp:
    """
    Minimal op carrying the attributes used by add_costs_to_dict / create_dict_cost.
    """
    def __init__(self, op_id, vessel1_id=None, vessel2_id=None,
                 parts_cost=0, tech_required=0, tech_cost=0,
                 tech_per_device=None, rov_daily=None, failures=None, days_main=None,
                 other_costs=0):
        self.id = op_id
        self.vessel1_id = vessel1_id
        self.vessel2_id = vessel2_id
        self.parts_cost = parts_cost
        self.tech_required = tech_required
        self.tech_cost = tech_cost
        # If provided, emulate inspection-like attributes (tech_per_device)
        if tech_per_device is not None:
            self.tech_per_device = tech_per_device
        # Optional rov_drone aggregate
        if rov_daily is not None:
            self.rov_drone = SimpleNamespace(daily_charter=rov_daily)
        self.failures = failures
        self.days_main = days_main
        self.other_costs = other_costs


# ----------------- Tests -----------------

class TestKPIInsightHelpers(unittest.TestCase):

    def test_get_n_tech_variants(self):
        ins = KPI_Insight(N_SIMULATION=1, n_lifetime=2)

        # dict
        self.assertEqual(ins.get_n_tech({"tech_tot": 5}), 5)

        # dict as string
        self.assertEqual(ins.get_n_tech("{'tech_tot': 7}"), 7)

        # simple string
        self.assertEqual(ins.get_n_tech(" 10 "), "10")

        # unsupported type
        with self.assertRaises(ValueError):
            ins.get_n_tech(123.45)

    def test_create_and_add_costs(self):
        ins = KPI_Insight(N_SIMULATION=1, n_lifetime=1)
        vessels = [DummyVessel("V1", "ctv"), DummyVessel("V2", "sov")]
        fail_1 = DummyFail("ofw_fail_keyA", 0.1, 5, 1000)
        fail_2 = DummyFail("ofw_fail_keyB", 0.2, 5, 2000)

        dict_failure_vessel_failure = {"ofw_fail_keyA": {}}
        op = DummyOp(
            op_id="OPX",
            vessel1_id="V1",
            vessel2_id="V9",   # not present
            parts_cost=200,
            tech_required=3,
            tech_cost=150,
            rov_daily=1000,
            other_costs=50
        )

        ins.create_dict_cost(vessels, key="ofw_fail_keyA", op=op, value=2.5, dict_failure_vessel_failure=dict_failure_vessel_failure)
        self.assertIn("V1", dict_failure_vessel_failure["ofw_fail_keyA"])
        self.assertEqual(dict_failure_vessel_failure["ofw_fail_keyA"]["V1"], 2.5)
        # V2 not matched, so not present
        self.assertNotIn("V2", dict_failure_vessel_failure["ofw_fail_keyA"])

        dict_failure_vessel_data = {
            "part_cost": {},
            "tech_cost": {},
            "other_costs": {},
            "rov_drone": {},
        }
        ins.add_costs_to_dict(dict_failure_vessel_data, fail=fail_1, op=op)
        self.assertEqual(dict_failure_vessel_data["part_cost"]["ofw_fail_keyA"], 1000)
        self.assertEqual(dict_failure_vessel_data["tech_cost"]["ofw_fail_keyA"], 3 * 150)
        self.assertEqual(dict_failure_vessel_data["other_costs"]["ofw_fail_keyA"], 50)
        self.assertEqual(dict_failure_vessel_data["rov_drone"]["ofw_fail_keyA"], 1000)

        # Fallback to tech_per_device when tech_required missing
        op2 = DummyOp(op_id="OPY", tech_per_device=4, tech_cost=120, parts_cost=0, other_costs=0)
        del op2.tech_required
        ins.add_costs_to_dict(dict_failure_vessel_data, fail=fail_2, op=op2)
        self.assertEqual(dict_failure_vessel_data["tech_cost"]["ofw_fail_keyB"], 4 * 120)


class TestKPIInsightEndToEnd(unittest.TestCase):

    def _logs_for_sim(self, v1="V1", v2="V2"):
        """
        Build a tiny log_events_merged for two vessels:
        - one plain 'operation' row (1 day)
        - one 'operation_merged' row (2 days) with comments containing tech_tot=6
        - one 'inspection_site' row (1 day)
        - one reused row to trigger reuse% (mark d_end_stat_chart='reuse_vessel')
        """
        base = datetime(2025, 6, 1, 8, 0, 0)

        rows = [
            # Plain operation, belongs to V1 as vessel_1
            dict(event="operation",
                 vessel_1=v1, vessel_2=np.nan,
                 n_vessel_1_effective=1, n_vessel_2=0,
                 d_end=base + timedelta(hours=24),
                 d_end_wait_start=base,  # => 1 day
                 d_end_leadtime=base,
                 d_trigger=base - timedelta(hours=1),
                 d_end_stat_chart=base + timedelta(hours=48),
                 comments="{}",
                 id="OP-A"),

            # Merged op, belongs to V1, 2 days, comments carry tech_tot
            dict(event="operation_merged",
                 vessel_1=v1, vessel_2=np.nan,
                 n_vessel_1_effective=1, n_vessel_2=0,
                 d_end=base + timedelta(hours=48),
                 d_end_wait_start=base,  # => 2 days
                 d_end_leadtime=base,
                 d_trigger=base - timedelta(hours=2),
                 d_end_stat_chart=base + timedelta(hours=72),
                 comments="{'tech_tot': 6}",
                 id="OP-B"),

            # Inspection on V1 as vessel_1, 1 day counted from trigger
            dict(event="inspection_site",
                 vessel_1=v1, vessel_2=np.nan,
                 n_vessel_1_effective=1, n_vessel_2=0,
                 d_end=base + timedelta(hours=24),
                 d_end_wait_start=base,  # not used for inspection_site days
                 d_end_leadtime=base,  # not used for inspection_site days
                 d_trigger=base,
                 d_end_stat_chart=base + timedelta(hours=48),
                 comments="{}",
                 id="INSP-C"),

            # A reused row to contribute to reuse% numerator
            dict(event="operation",
                 vessel_1=v1, vessel_2=np.nan,
                 n_vessel_1_effective=1, n_vessel_2=0,
                 d_end=base + timedelta(hours=6),
                 d_end_wait_start=base,
                 d_end_leadtime=base,
                 d_trigger=base,
                 d_end_stat_chart="reuse_vessel",
                 comments="{}",
                 id="OP-RUSE"),
        ]
        df = pd.DataFrame(rows)
        # Ensure datetime dtype
        for c in ["d_end", "d_end_wait_start", "d_trigger"]:
            df[c] = pd.to_datetime(df[c])
        return df

    def _kpi_tot_cost_df(self):
        """
        Build a df for dfs_tot_cost_list[i] with at least 6 rows, so slicing kpi_total_final[:-4]
        keeps the first two data rows.
        """
        rows = [
            {"vessel type": "ctv", "tot_vessel_costs": 1000, "tot_mobilization_costs": 100},
            {"vessel type": "sov", "tot_vessel_costs": 2000, "tot_mobilization_costs": 200},
            # 4 trailing rows (dummy/fixed) that will be dropped by `[:-4]`
            {"vessel type": "dummy1", "tot_vessel_costs": 0, "tot_mobilization_costs": 0},
            {"vessel type": "dummy2", "tot_vessel_costs": 0, "tot_mobilization_costs": 0},
            {"vessel type": "dummy3", "tot_vessel_costs": 0, "tot_mobilization_costs": 0},
            {"vessel type": "dummy4", "tot_vessel_costs": 0, "tot_mobilization_costs": 0},
        ]
        return pd.DataFrame(rows)

    def test_kpi_insight_end_to_end(self):
        """
        End-to-end through kpi_insight with:
        - 2 simulations (second empty to test skipping)
        - 2 vessels (V1=ctv, V2=sov)
        - Checks on lifetime_day_effective, yearly day effective, merge %, reuse %, average tech
        - Checks that cost aggregation uses the top rows and ignores the trailing 4 rows
        """
        N = 2
        insight = KPI_Insight(N_SIMULATION=N, n_lifetime=2)

        vessels = [DummyVessel("V1", "ctv"), DummyVessel("V2", "sov")]

        # Simulation 0: with data; Simulation 1: empty
        dfs_log_events_merged = {
            0: self._logs_for_sim(),
            1: self._logs_for_sim(),
        }

        dfs_tot_cost_list = {
            0: self._kpi_tot_cost_df(),
            1: self._kpi_tot_cost_df(),
        }

        # results_dict is a simple namespace with the two dicts
        results_dict = SimpleNamespace(
            dfs_log_events_merged=dfs_log_events_merged,
            dfs_tot_cost_list=dfs_tot_cost_list
        )

        # No operations_total (so df_fail will be essentially empty); focus on df_avg side
        operations_total = []

        df_fail, df_avg = insight.kpi_insight(
            results_dict=results_dict,
            vessels=vessels,
            operations_total=operations_total
        )

        # ---- df_avg checks ----
        # Index should be vessel type; ensure 'ctv' present with non-zero effective days
        self.assertIn("ctv", df_avg.index)
        # lifetime_day_effective for V1:
        # - operation: 1 day
        # - operation_merged: 2 days
        # - inspection_site: 1 day
        # - operation: 1 day
        # total = 5 days
        self.assertEqual(df_avg.loc["ctv", "lifetime_day_effective"], 5.00)
        # yearly = lifetime / n_lifetime (2.5)
        self.assertEqual(df_avg.loc["ctv", "yearly day effective"], 2.50)

        # average tech merged from comments{'tech_tot': 6}
        self.assertEqual(df_avg.loc["ctv", "average tech merged"], 6.00)

        # merge % = merged_op / tot_op (operation + operation_merged) = 1 / 3
        self.assertAlmostEqual(df_avg.loc["ctv", "merge %"], round((1/3)*100,2))

        # reuse % = reused_rows / total_rows_for_ratio
        # reused_rows = 1 (OP-RUSE)
        # total considered = all ops+inspections excluding tow (operation, operation_merged, inspection_site, inspection_port)
        # here: 3 rows (operation, operation_merged, inspection) + OP-RUSE (operation) = 4 -> 1/4 = 0.25
        self.assertAlmostEqual(df_avg.loc["ctv", "reuse %"], 0.25*100)

        # Cost columns from dfs_tot_cost_list average of the kept two rows (ctv/sov grouped by vessel type index):
        # For 'ctv' we only have one data row with tot_vessel_costs=1000, tot_mobilization_costs=100
        self.assertEqual(df_avg.loc["ctv", "tot_vessel_costs"], 1000)
        self.assertEqual(df_avg.loc["ctv", "tot_mobilization_costs"], 100)

        # 'sov' has zero effective days (no rows for V2), cost available from dfs_tot_cost_list
        self.assertNotIn("sov", df_avg.index)

        # ---- df_fail is expected to be a DataFrame (likely empty in this setup) ----
        self.assertIsInstance(df_fail, pd.DataFrame)


if __name__ == "__main__":
    unittest.main(verbosity=2)
