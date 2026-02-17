# test_kpi_aux.py

import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


from oriom.core.functions.kpi_final.kpi_aux import (
    calculate_cost,
    count_day,
    safe_get_tech_tot,
    n_technicians,
    filter_df_events_per_vessel,
    remove_row_vessel_double,
    define_fuel_cost,
    tech_rov_cost,
)


# ----------------- Helpers / Dummies -----------------

class DummyVessel:
    """Minimal vessel with just the attributes used by the functions."""
    def __init__(
        self,
        vid="CTV",
        fuel_type="MGO",
        density=850,  # kg/m^3
        fuel_cons_transit=100,
        fuel_cons_maneuver=60,
        fuel_cons_standby=40,
    ):
        self.id = vid
        self.fuel_type = fuel_type
        self.density = density
        self.fuel_cons_transit = fuel_cons_transit
        self.fuel_cons_maneuver = fuel_cons_maneuver
        self.fuel_cons_standby = fuel_cons_standby


def _dt(h=0):
    return datetime(2025, 6, 1, 0, 0, 0) + timedelta(hours=h)


# ----------------- Tests -----------------

class TestCalculateCost(unittest.TestCase):
    def test_calculate_cost_basic(self):
        """
        Fuel costs are linear in time * consumption * (fuel_cost*density).
        """
        ves = DummyVessel(fuel_cons_transit=10, fuel_cons_maneuver=5, fuel_cons_standby=2)
        fcd = 0.85  # €/l equivalent (already density*cost)
        transit, maneuver, standby = calculate_cost(
            transit_time_merged=3.0,
            maneuver_time_merged=2.0,
            standby_time_merged=1.5,
            vessel=ves,
            fuel_cost_times_density=fcd,
        )
        self.assertEqual(transit, 3.0 * 10 * fcd)
        self.assertEqual(maneuver, 2.0 * 5 * fcd)
        self.assertEqual(standby, 1.5 * 2 * fcd)


class TestCountDay(unittest.TestCase):
    def test_count_day_stat_chart_with_reuse(self):
        """
        When end == 'd_end_stat_chart', if df[end] == 'reuse_vessel' it must be replaced by start.
        Vessel_1 uses [end - start], vessel_2 uses [d_end_stat_chart_orig - start].
        """
        ves = DummyVessel(vid="CTV")

        df = pd.DataFrame({
            "vessel_1": ["CTV", "OTHER"],
            "vessel_2": ["ZEE",  "CTV"],
            "n_vessel": [1, 2],
            "d_end_stat_chart": ["reuse_vessel", _dt(26)],           # first row "reuse" -> use start
            "d_end": [_dt(26), _dt(26)],           # first row "reuse" -> use start
            "d_trigger":  [_dt(10), _dt(15)],
            "d_end_leadtime": [_dt(10), _dt(15)],
        })

        # Row 1 (vessel_1 == CTV): days = ceil((start-start)/86400)=0 ; then * n_vessel(1)=0
        # Row 2 (CTV is vessel_2): days = ceil((30h-15h)/24h)=ceil(15/24)=1 ; * n_vessel(2)=2
        got_days = count_day(df)
        self.assertEqual(got_days, 6)

    def test_count_day_default_branch(self):
        """
        Default branch (end != 'd_end_stat_chart') uses d_end_stat_chart_orig - start.
        """
        ves = DummyVessel(vid="ANY")
        df = pd.DataFrame({
            "n_vessel": [1, 3],
            "d_trigger":  [_dt(10), _dt(15)],
            "d_end": [_dt(25), _dt(50)],
            "d_end_leadtime": [_dt(1), _dt(30)],
        })
        # Row1: (25 - 1) = 24h => ceil(24/24)=1 *1 =1
        # Row2: (50 - 30)=20h => ceil(20/24)=1 *3 =3  => total=4
        got_days = count_day(df)
        self.assertEqual(got_days, 8)


class TestSafeGetTechTot(unittest.TestCase):
    def test_dict_input(self):
        self.assertEqual(safe_get_tech_tot({"tech_cost": 123}), 123)

    def test_jsonish_string_input(self):
        self.assertEqual(safe_get_tech_tot("{'tech_cost': 456}"), 456)

    def test_invalid_string(self):
        self.assertIsNone(safe_get_tech_tot("oops"))


class TestNTechnicians(unittest.TestCase):
    def test_no_consecutive(self):
        """
        consecutive_inspections = round(devices / (n_vess*n_shifts)).
        If it rounds to 0, force 1.
        """
        self.assertEqual(n_technicians(10, 4, n_shifts=1000, n_vess=10), 10*4/1)

    def test_with_consecutive(self):
        """
        Example from docstring: 75 devices, 4 tech/device, 12 shifts, 3 vessels -> round(75/(36))=2
        => 300/2=150
        """
        self.assertEqual(n_technicians(75, 4, n_shifts=12, n_vess=3), 150)


class TestFilterDfEventsPerVessel(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({
            "id": ["op1", "op2", "op3", "op4"],
            "vessel_1": ["A", "B", "A", "X"],
            "vessel_2": ["B", "A", None,   "A"],
            "n_vessel_1": [1, 2, 1, 1],
            "n_vessel_1_effective": [1, 1, 0, 1],
            "n_vessel_2": [2, 0, 1, 3],
        })

    def test_include_second_vessel_true(self):
        """
        second_vessel=True:
          - include rows where vessel is either vessel_1 or vessel_2
          - n_vessel should be n_vessel_1_effective when vessel is v1, else n_vessel_2
        """
        out = filter_df_events_per_vessel(self.df, vessel_id="A", second_vessel=True)
        # rows: op1 (A as v1 -> 1), op2 (A as v2 -> 0), op3 (A as v1 -> 0), op4 (A as v2 -> 3)
        self.assertEqual(set(out["id"]), {"op1", "op2", "op3", "op4"})
        self.assertEqual(out.loc[out["id"] == "op1", "n_vessel"].iloc[0], 1)
        self.assertEqual(out.loc[out["id"] == "op2", "n_vessel"].iloc[0], 0)
        self.assertEqual(out.loc[out["id"] == "op3", "n_vessel"].iloc[0], 0)
        self.assertEqual(out.loc[out["id"] == "op4", "n_vessel"].iloc[0], 3)

    def test_only_first_vessel(self):
        """
        second_vessel=False:
          - include only rows where vessel is vessel_1
          - n_vessel should be n_vessel_1
        """
        out = filter_df_events_per_vessel(self.df, vessel_id="A", second_vessel=False)
        self.assertEqual(set(out["id"]), {"op1", "op3"})
        # Here n_vessel must come from n_vessel_1 (not 'effective')
        self.assertEqual(out.loc[out["id"] == "op1", "n_vessel"].iloc[0], 1)
        self.assertEqual(out.loc[out["id"] == "op3", "n_vessel"].iloc[0], 1)


class TestRemoveRowVesselDouble(unittest.TestCase):
    def test_remove_double_rows(self):
        """
        Drop rows where ves.id is present and the other vessel in the row
        is in rov_tech_vessel_count keys.
        """
        ves = DummyVessel(vid="A")
        df = pd.DataFrame({
            "id": ["r1", "r2", "r3"],
            "vessel_1": ["A", "A", "X"],
            "vessel_2": ["B", "C", "A"],
        })
        # Keys -> B only
        out = remove_row_vessel_double(df.copy(), ves, {"B": 1})
        # r1 has A & B -> drop; r2 has A & C (C not in keys) -> keep; r3 has X & A with X not in keys -> keep
        self.assertEqual(list(out["id"]), ["r2", "r3"])

    def test_no_filter_when_empty_dict(self):
        ves = DummyVessel(vid="A")
        df = pd.DataFrame({
            "id": ["r1", "r2"],
            "vessel_1": ["A", "X"],
            "vessel_2": ["B", "A"],
        })
        out = remove_row_vessel_double(df.copy(), ves, {})
        pd.testing.assert_frame_equal(out.reset_index(drop=True), df.reset_index(drop=True))


class TestDefineFuelCost(unittest.TestCase):
    def test_hfo_mgo_mdo(self):
        """
        fuel_cost_times_density = (density * 1e-6) * fuel_cost_per_ton
        """
        v = DummyVessel(fuel_type="HFO", density=980)
        self.assertAlmostEqual(define_fuel_cost(v, 600, 800, 1000), 980e-6 * 600)

        v.fuel_type = "MGO"
        self.assertAlmostEqual(define_fuel_cost(v, 600, 800, 1000), 980e-6 * 1000)

        v.fuel_type = "MDO"
        self.assertAlmostEqual(define_fuel_cost(v, 600, 800, 1000), 980e-6 * 800)


class TestTechRovCost(unittest.TestCase):

    @patch("oriom.utils.read_dataframe_value.compute_rov_cost")
    def test_tech_rov_cost_mixed_sources_and_shifts(self, mock_compute_rov):
        """
        - ROV cost comes from compute_rov_cost(row['id'], row['n_vessel_1'], rov_dict_cost)
        - days_tech = ceil((d_end - d_end_wait_start)/86400)
        - n_shift_tech = 2 if hours > duration_shift else 1
        - tech_cost: prefer column 'comments' dict via safe_get_tech_tot; else map from oper_dict_tech.
        """
        mock_compute_rov.side_effect = lambda op_id, n_v1, cost_dict: cost_dict.get(op_id, 0) * n_v1

        df = pd.DataFrame({
            "id": ["A", "B", "C", "D"],
            "n_vessel_1": [1, 2, 1, 3],
            "d_end_wait_start": [_dt(0), _dt(0), _dt(0), _dt(0)],
            "d_end": [_dt(10), _dt(5), _dt(30), _dt(8)],  # hours
            # Put tech_cost in comments for A and C; leave B and D to be filled via oper_dict_tech
            "comments": [
                "{'tech_cost': 100}",   # A
                "{}",                   # B -> None -> map
                "{'tech_cost': 50}",    # C
                None,                   # D -> None -> map
            ],
        })
        rov_dict_cost = {"A": 200, "B": 10, "C": 50, "D": 5}
        oper_dict_tech = {"B": 80, "D": 40}  # used only when comments has no tech_cost
        duration_shift = 12  # hours

        # Expected:
        # ROV: sum(cost * n_vessel_1) = A:200*1 + B:10*2 + C:50*1 + D:5*3 = 200 + 20 + 50 + 15 = 285
        # days_tech: ceil(hours/24) => A: ceil(10/24)=1 ; B: ceil(5/24)=1 ; C: ceil(30/24)=2 ; D: ceil(8/24)=1
        # n_shift_tech: hours>12 ? 2 : 1 => A:1 ; B:1 ; C:2 ; D:1
        # tech_cost per row:
        #   A: 100 (from comments)
        #   B: 80 (from oper_dict_tech)
        #   C: 50 (from comments)
        #   D: 40 (from oper_dict_tech)
        # Total tech = ceil( A:1*100*1 + B:1*80*1 + C:2*50*2 + D:1*40*1 ) = ceil(100 + 80 + 200 + 40) = 420
        tot_tech, tot_rov = tech_rov_cost(
            df=df.copy(),
            rov_dict_cost=rov_dict_cost,
            duration_shift=duration_shift,
            oper_dict_tech=oper_dict_tech,
        )
        self.assertEqual(tot_rov, 285)
        self.assertEqual(tot_tech, 420)


if __name__ == "__main__":
    unittest.main(verbosity=2)
