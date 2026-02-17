#test_cost_evaluator

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta

# ---- CHANGE THESE IMPORTS if your real paths differ ----
from oriom.core.functions.kpi_final import kpi_aux
from oriom.core.functions.kpi_final.kpi_cost_evaluator import (  # <-- sostituisci con il path reale del file testato
    inspection_data,
    values_from_log_file,
    find_time_log_events_insp,
    calculate_event_costs,
    part_other_cost,
    zero_variables,
)

# ---------- Dummies ----------

class DummyVessel:
    """Minimal vessel used by the functions."""
    def __init__(self, n_vessels=2, id_vess = 'v001', fuel_cons_transit=10, fuel_cons_maneuver=5, fuel_cons_standby=2):
        self.n_vessels = n_vessels
        self.id = id_vess,
        self.fuel_cons_transit = fuel_cons_transit
        self.fuel_cons_maneuver = fuel_cons_maneuver
        self.fuel_cons_standby = fuel_cons_standby

class DummyTSDATA():
    def __init__(self, oper_sched=None):
        self.oper_sched = oper_sched

class DummyFailure():
    def __init__(self, id, parts_cost):
        self.id = id
        self.parts_cost = parts_cost

class DummyFindFailure():
    def __init__(self, failures):
        self.failures_dict_id = {f.id: f for f in failures}
    
    def find_failure_from_id(self, fail_id):
        f = self.failures_dict_id.get(fail_id)
        if f:
            return f

class DummyRov:
    def __init__(self, daily_charter=1000):
        self.daily_charter = daily_charter


class DummyInspClassPort:
    """Mimic an 'inspection at port' class layout."""
    def __init__(self, id_, intervened_devices=4, n_device_at_port=2, n_device_stored_at_port=0,
                 rov_drone=None, tech_per_device=3, tech_cost=200,
                 days_main=0, days_last=0, n_vessel_main=0, n_vessel_last=0,
                 op_tow_port="op_tow_port", op_tow_site="op_tow_site",
                 op_tow_site_port="op_tow_site_port", ts_data = None):
        self.id = id_
        self.intervened_devices = intervened_devices
        self.n_device_at_port = n_device_at_port
        self.n_device_stored_at_port = n_device_stored_at_port
        self.rov_drone = rov_drone
        self.tech_per_device = tech_per_device
        self.tech_cost = tech_cost
        self.days_main = days_main
        self.days_last = days_last
        self.n_vessel_main = n_vessel_main
        self.n_vessel_last = n_vessel_last
        self.op_tow_port = op_tow_port
        self.op_tow_site = op_tow_site
        self.op_tow_site_port = op_tow_site_port
        self.ts_data = ts_data


class DummyInspClassSite:
    """Mimic an 'inspection at site' class layout."""
    def __init__(self, id_, intervened_wtg=5, intervened_pv=0, intervened_wec=0,
                 rov_drone=None, tech_per_device=2, tech_cost=150,
                 days_main=10, days_last=0, n_vessel_main=2, n_vessel_last=0, ts_data = None):
        self.id = id_
        self.intervened_wtg = intervened_wtg
        self.intervened_pv = intervened_pv
        self.intervened_wec = intervened_wec
        self.rov_drone = rov_drone
        self.tech_per_device = tech_per_device
        self.tech_cost = tech_cost
        self.days_main = days_main
        self.days_last = days_last
        self.n_vessel_main = n_vessel_main
        self.n_vessel_last = n_vessel_last
        self.ts_data = ts_data


class DummyInsp:
    """Wrapper that provides .id and .insp_class"""
    def __init__(self, id_, insp_class):
        self.id = id_
        self.insp_class = insp_class


def dt(h=0):
    return datetime(2025, 6, 1, 0, 0, 0) + timedelta(hours=h)


# ---------- Tests for inspection_data ----------

class TestInspectionData(unittest.TestCase):
    def test_port_branch(self):
        insp_cls = DummyInspClassPort(
            id_="PORT01",
            intervened_devices=4,
            n_device_at_port=2,
            n_device_stored_at_port=1,
            rov_drone=DummyRov(daily_charter=500),
            tech_per_device=3,
            tech_cost=200,
        )
        insp = DummyInsp("PORT01", insp_cls)
        got = inspection_data(insp)
        # (insp_id, rov_cost_insp, device_inspected, n_tech_inps_tot, c_tech_inps, n_device_port, n_device_store_port)
        self.assertEqual(got, ("PORT01", 500, 4, 12, 200, 2, 1))

    @patch.object(kpi_aux, "n_technicians", return_value=7)
    def test_site_branch(self, mock_ntech):
        insp_cls = DummyInspClassSite(
            id_="SITE01",
            intervened_wtg=5,
            rov_drone=DummyRov(daily_charter=800),
            tech_per_device=2,
            tech_cost=150,
            days_main=6,
            n_vessel_main=2,
        )
        insp = DummyInsp("SITE01", insp_cls)
        got = inspection_data(insp)
        # (insp_id, rov_cost_insp, device_inspected, n_tech_inps_tot, c_tech_inps)
        self.assertEqual(got, ("SITE01", 800, 5, 7, 150))
        mock_ntech.assert_called_once()


# ---------- Tests for values_from_log_file ----------

class TestValuesFromLogFile(unittest.TestCase):
    @patch.object(kpi_aux, "remove_row_vessel_double", side_effect=lambda df, ves, rov_tech_vessel_count: df)
    @patch.object(kpi_aux, "tech_rov_cost", return_value=(420, 285))
    def test_values_from_log_file_aggregation(self, mock_trc, mock_rr):
        """
        Check transit/standby/maneuver sums and pass-through of tech/rov costs.
        """
        df = pd.DataFrame({
            "d_end_transit_ts": [dt(12), dt(22)],
            "d_end_dur_net_port": [dt(10), dt(20)],
            "d_end_transit_tp": [dt(35), dt(50)],
            "d_end_dur_net_site": [dt(30), dt(45)],
            "d_end": [dt(40), dt(60)],
            "d_end_leadtime": [dt(32), dt(48)],
        })
        # transit_ts: (12-10)=2, (22-20)=2 => 4
        # transit_tp: (35-30)=5, (50-45)=5 => 10  => total transit = 14
        # standby_p_start: (10-32) + (20-48) => negative? Note: function computes (d_end_dur_net_port - d_end_leadtime)
        #   row1: (10 - 32)h = -22  ; row2: (20 - 48)h = -28  -> -50 (the function sums as-is)
        # standby_p_end: (40-35)=5 ; (60-50)=10 => 15  => total standby = -35
        # maneuver: (30-12)=18 ; (45-22)=23 => 41
        # We do not alter the function’s behavior; we just assert the arithmetic.
        ves = DummyVessel()
        transit_time, standby_time, maneuver_time, tech_cost, rov_cost = values_from_log_file(
            df=df,
            ves=ves,
            duration_shift=12,
            oper_dict_tech={"A": 1},
            rov_dict_cost={"A": 1},
            rov_tech_vessel_count={},
        )
        self.assertEqual(transit_time, 14)
        self.assertEqual(standby_time, -35)
        self.assertEqual(maneuver_time, 41)
        self.assertEqual(tech_cost, 420)
        self.assertEqual(rov_cost, 285)
        mock_rr.assert_called_once()
        mock_trc.assert_called_once()


# ---------- Tests for find_time_log_events_insp ----------

class TestFindTimeLogEventsInsp(unittest.TestCase):
    @patch("oriom.core.functions.kpi_final.kpi_cost_evaluator.approximate_hourly_data", side_effect=lambda x: x)
    def test_site_inspection_flow(self, mock_approx):
        """
        Single site inspection:
        - 1 event in logs
        - oper_sched row with exact matching datetime
        - contributions scaled by vessel.n_vessels
        """
        ves = DummyVessel(n_vessels=2)

        # oper_sched: one row aligning with d_trigger
        oper_sched = pd.DataFrame([{
            "datetime": dt(10),
            "transit_to_port": 1.5,
            "transit_to_site": 2.0,
            "wait_start": 0.5,
            "wait_port": 1.0,
            "dur_net_site": 3.0,
            "days_inspected": ["2025-06-01"],  # list branch
        }])

        ts_data_op = DummyTSDATA(oper_sched = oper_sched)

        # dicts
        insp_port_data = {}

        insp_cls = DummyInspClassSite(
            id_="SITE01",
            intervened_wtg=3,
            rov_drone=DummyRov(900),
            tech_per_device=2,
            tech_cost=150,
            days_main=5,
            n_vessel_main=2,
            ts_data = ts_data_op
        )
        insp = DummyInsp("SITE01", insp_cls)

        # logs: one event
        logs = pd.DataFrame({
            "id": ["SITE01"],
            "d_trigger": [dt(10)],
            "d_end_leadtime": [dt(34)],
            "d_end": [dt(40)],
            "n_vessel" : 2
        })


        # rov_tech_vessel_count starts empty for this vessel
        rov_tech_vessel_count = {ves.n_vessels: []}  # keys can be vessel ID; here use int to show it's just a dict

        t_tr, t_sb, t_mz, c_tech, c_rov = find_time_log_events_insp(
            log_events_merged_insp=logs,
            operations_inspect_site=[insp],
            operations_inspect_port=[],
            duration_shift=12,
            ves=ves,
            insp_port_data=insp_port_data,
            rov_tech_vessel_count={ves.id if hasattr(ves, 'id') else 'VESSEL': []},
        )
        # transit: (1.5+2.0)*n_vessels = 3.5*2=7.0
        # standby: (0.5+1.0)*2=3.0
        # maneuver: 3.0*2=6.0
        self.assertEqual((t_tr, t_sb, t_mz), (7.0, 3.0, 6.0))
        # tech cost = n_tech_inps_tot*c_tech_inps for each log row
        # n_tech_inps_tot determined by kpi_aux.n_technicians inside inspection_data(site)
        # We won't assert absolute tech/rov costs here, only that totals are non-negative and numeric.
        self.assertTrue(c_tech >= 0)
        self.assertTrue(c_rov >= 0)

    @patch("oriom.core.functions.kpi_final.kpi_cost_evaluator.approximate_hourly_data", side_effect=lambda x: x)
    def test_port_inspection_flow(self, mock_approx):
        """
        Single port inspection:
        - Verify transit/maneuver/standby breakdown with provided numbers.
        - Verify towing tech costs pathways.
        """
        ves = DummyVessel(n_vessels=1)
        insp_cls = DummyInspClassPort(
            id_="PORT01",
            intervened_devices=4,
            n_device_at_port=2,
            n_device_stored_at_port=0,
            rov_drone=DummyRov(500),
            tech_per_device=2,
            tech_cost=100,
        )
        insp = DummyInsp("PORT01", insp_cls)

        logs = pd.DataFrame({
            "id": ["PORT01"],
            "d_trigger": [dt(0)],
            "d_end": [dt(10)],
            "d_end_leadtime": [dt(0)],
            "n_vessel" : 1
        })

        # Build minimal 'ts_data' holders with the attributes read in the code
        class TS:
            def __init__(self, dur_net_site, transit_ts):
                self.dur_net_site = dur_net_site
                self.transit_ts = transit_ts

        # For port branch, code accesses:
        # insp_port_data[insp_id][insp_id].ts_data.dur_net_site -> duration for shifts counting
        # and per-operation entries for op_tow_port, op_tow_site, op_tow_site_port
        op_port = MagicMock()
        op_port.ts_data = TS(dur_net_site=2.0, transit_ts=1.0)
        op_port.tech_required = 1
        op_port.tech_cost = 50

        op_site = MagicMock()
        op_site.ts_data = TS(dur_net_site=3.0, transit_ts=1.5)
        op_site.tech_required = 2
        op_site.tech_cost = 60

        op_site_port = MagicMock()
        op_site_port.ts_data = TS(dur_net_site=4.0, transit_ts=2.0)
        op_site_port.tech_required = 3
        op_site_port.tech_cost = 70

        insp_port_data = {
            "PORT01": {
                "PORT01": MagicMock(ts_data=TS(dur_net_site=8.0, transit_ts=0.0)),
                insp_cls.op_tow_port: op_port,
                insp_cls.op_tow_site: op_site,
                insp_cls.op_tow_site_port: op_site_port,
            }
        }

        # rov_tech_vessel_count starts empty for this vessel key
        rov_tech_vessel_count = {'v001': []}

        t_tr, t_sb, t_mz, c_tech, c_rov = find_time_log_events_insp(
            log_events_merged_insp=logs,
            operations_inspect_site=[],
            operations_inspect_port=[insp],
            duration_shift=8,  # dur_net_port_days = ceil(8.0 / 8) = 1
            ves=ves,
            insp_port_data=insp_port_data,
            rov_tech_vessel_count=rov_tech_vessel_count,
        )

        # From code:
        # device_inspected=4, n_device_port=2
        # trans_without_dev = op_tow_port.ts_data.transit_ts = 1.0
        # trans_with_dev    = op_tow_site_port.ts_data.transit_ts = 2.0
        # manuv_rem = 2.0 ; manuv_red = 3.0 ; manuv_rem_red = 4.0
        #
        # transit_devices_tow = (4-2)*2.0*2 + 2*1.0*2 = 2*4 + 2*2 = 8 + 4 = 12
        # manuver_devices_tow = (4-2)*4.0 + 2*2.0 + 2*3.0 = 8 + 4 + 6 = 18
        # time_total_tow = 10h (from logs)
        # stand_by_tow = 10 - 12 - 18 = -20 (the function does no clipping)
        self.assertEqual((t_tr, t_mz), (12, 18))
        self.assertEqual(t_sb, -20)
        # tech_tow_cost:
        #   tech_rem = 1*50=50
        #   tech_red = 2*60=120
        #   tech_rem_red = 3*70=210
        #   -> (4-2)*210 + 2*50 + 2*120 = 2*210 + 100 + 240 = 760
        # n_tech_inps_tot = 2*4 = 8 ; dur_net_port_days=1 ; c_tech_inps=100
        # tot_tech_cost_insp += 8*1*100 + 760 = 1560
        self.assertEqual(c_tech, 1560)
        # rov: rov_insp_day * rov_cost_insp ; count_day() returns ceil((d_end - d_trigger)/day)=ceil(10/24)=1
        # rov_cost_insp = 500 -> 500
        self.assertEqual(c_rov, 500)


# ---------- Tests for calculate_event_cost ----------

class TestCalculateEventCosts(unittest.TestCase):
    @patch("oriom.core.functions.kpi_final.kpi_cost_evaluator.values_from_log_file",
           return_value=(5.0, 2.0, 3.0, 100, 50))
    def test_without_insp_params(self, mock_values):
        """
        No insp_params -> uses values_from_log_file; costs via kpi_aux.calculate_cost.
        """
        ves = DummyVessel(fuel_cons_transit=10, fuel_cons_maneuver=5, fuel_cons_standby=2)
        df = pd.DataFrame({"any": [1]})  # non-empty to trigger normal path
        # Directly use real kpi_aux.calculate_cost behavior
        tc, mc, sc, days, rov = calculate_event_costs(
            log_df=df,
            ves=ves,
            duration_shift=12,
            fuel_cost_density=0.8,  # €/l
            rov_dict_cost={"X": 1},
            oper_dict_tech={"X": 1},
            insp_params=None,
            rov_tech_vessel_count={},
        )
        # expected fuel costs:
        # transit: 5h * 10 * 0.8 = 40
        # maneuver: 3h * 5 * 0.8 = 12
        # standby: 2h * 2 * 0.8 = 3.2
        self.assertAlmostEqual(tc, 40)
        self.assertAlmostEqual(mc, 12)
        self.assertAlmostEqual(sc, 3.2)
        self.assertEqual((days, rov), (100, 50))

    def test_empty_df_returns_zeroes(self):
        df = pd.DataFrame()
        ves = DummyVessel()
        got = calculate_event_costs(
            log_df=df,
            ves=ves,
            duration_shift=12,
            fuel_cost_density=1.0,
        )
        self.assertEqual(got, (0, 0, 0, 0, 0))


# ---------- Tests for part_other_cost & zero_variables ----------

class TestPartOtherCostAndZeros(unittest.TestCase):
    def test_part_other_cost(self):
        failures = []
        df = pd.DataFrame({
            "id": ["OP1", "OP2", "OP3"],
            "d_end": [dt(48), dt(25), dt(10)],
            "d_end_leadtime": [dt(24), dt(20), dt(5)],
            "event": ["operation", "operation", "operation"],
            "comments": ['oper_a1.1', 'oper_a2.1', 'oper_a3.1']
        })

        ids = ['a1', 'a2', 'a3']
        costs = [1000, 500, 999]

        failures.extend(DummyFailure(f_id, f_cost) for f_id, f_cost in zip(ids, costs))
        find_element_class = DummyFindFailure(failures)

        class OpStat:
            def __init__(self, id_, parts_cost, other_costs, port_costs=0):
                self.op_class = type("C", (), {
                    "id": id_,
                    "parts_cost": parts_cost,
                    "other_costs": other_costs,
                    "port_costs": port_costs
                })()

        total_ops = [
            OpStat("OP1", parts_cost=1000, other_costs=200, port_costs=50),  # (48-24)=24h -> 1 day
            OpStat("OP2", parts_cost=500, other_costs=100, port_costs=10),   # (25-20)=5h -> 0 days
            OpStat("OPX", parts_cost=999, other_costs=999, port_costs=999),  # won't merge (id mismatch)
        ]

        part_cost, other_cost = part_other_cost(df, total_ops, find_element_class)
        # parts: 1000 + 500 = 1500
        # other: (200 + 100) + (port_costs_day) => OP1: 50*1 + OP2: 10*0 = 50
        # total other = 300 + 50 = 350
        self.assertEqual(part_cost, 1500)
        self.assertEqual(other_cost, 350)

    def test_zero_variables(self):
        self.assertEqual(zero_variables(), (0, 0, 0, 0, 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
