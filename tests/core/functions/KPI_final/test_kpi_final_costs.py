# test_kpi_final_costs.py

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import timedelta
from types import SimpleNamespace

from oriom.core.functions.kpi_final.kpi_final_costs import kpi_final_total_cost


# ------------------------------------------------------------------
# Dummy domain objects
# ------------------------------------------------------------------

class DummyVessel:
    def __init__(self, id_, type_="other", n_ves_annual_contract=0):
        self.id = id_
        self.type = type_
        self.n_ves_annual_contract = n_ves_annual_contract


class DummyInputs:
    class _S:
        def __init__(self, start_year, lifetime):
            self.start_year = {"value": start_year}
            self.lifetime = {"value": lifetime}

    def __init__(self, start_year, lifetime):
        self.stats = self._S(start_year, lifetime)


class DummyDayCounter:
    """Deepcopy-safe day counter used as return value of patched VesselDayCounter."""
    def __init__(self, vessels_calendar: pd.DataFrame):
        self.vessels_calendar = vessels_calendar

    def allocate_vessels(self, *args, **kwargs):
        return None


# ------------------------------------------------------------------
# Test case
# ------------------------------------------------------------------

class TestKpiFinalTotalCost(unittest.TestCase):

    # ---------------- helpers ----------------

    def _make_logs(self, start="2025-01-01 00:00:00", n=2):
        cols = [
            "event", "d_end", "vessel_1", "d_end_leadtime", "d_trigger",
            "d_end_transit_ts", "d_end_dur_net_port", "d_end_transit_tp",
            "d_end_dur_net_site", "id", "comments", "vessel_2",
            "n_vessel_1", "n_vessel_1_effective", "n_vessel_2", "ST_contract_1", "ST_contract_2"
        ]

        dt_cols = [
            "d_end", "d_end_leadtime", "d_trigger", "d_end_transit_ts",
            "d_end_dur_net_port", "d_end_transit_tp", "d_end_dur_net_site"
        ]

        if n == 0:
            df = pd.DataFrame(columns=cols)
            # IMPORTANT: keep datetime dtype even if empty (needed by .dt.year later)
            for c in dt_cols:
                df[c] = pd.to_datetime(df[c])
            return df.copy(), df.copy()

        d0 = pd.to_datetime(start)
        rows = []
        for i in range(n):
            d_end = d0 + timedelta(days=i)
            rows.append({
                "event": "operation",
                "d_end": d_end,
                "vessel_1": "V1",
                "d_end_leadtime": d_end - timedelta(hours=8),
                "d_trigger": d_end - timedelta(hours=10),
                "d_end_transit_ts": d_end - timedelta(hours=6),
                "d_end_dur_net_port": d_end - timedelta(hours=7),
                "d_end_transit_tp": d_end - timedelta(hours=1),
                "d_end_dur_net_site": d_end - timedelta(hours=5),
                "id": f"OP{i+1}",
                "comments": "{}",
                "vessel_2": None,
                "n_vessel_1": 1,
                "n_vessel_1_effective": 1,
                "n_vessel_2": 0,
                "ST_contract_1": False,
                "ST_contract_2": False
            })

        df = pd.DataFrame(rows)
        return df, df.copy()

    def _mock_vessel_day_counter(self, start="2025-01-01", end="2026-12-31"):
        idx = pd.date_range(start, end, freq="D")
        cal = pd.DataFrame({"V1": 0}, index=idx)
        # use SimpleNamespace to make deepcopy simple and predictable
        return SimpleNamespace(vessels_calendar=cal)

    def _mk_kpi(self, vessel_ids, direct_cost=100, days=2):
        return pd.DataFrame({
            "vessel_id": list(vessel_ids),
            "lifetime_direct_costs": [direct_cost] * len(vessel_ids),
            "n_chart_days": [days] * len(vessel_ids),
            "tot_other_costs": [0] * len(vessel_ids),
            "av_other_costs": [0] * len(vessel_ids),
        })

    def _calendar_df(self, start="2025-01-01", end="2026-12-31"):
        idx = pd.date_range(start, end, freq="D")
        return pd.DataFrame({"V1": 0}, index=idx)

    # ------------------------------------------------------------------
    # TEST 1 — baseline (fixed annual costs row)
    # ------------------------------------------------------------------

    @patch("oriom.core.functions.kpi_final.kpi_final_costs.VesselDayCounter")
    @patch("oriom.core.functions.kpi_final.kpi_final_costs.create_lifetime_cost", side_effect=lambda df: df)
    @patch("oriom.core.functions.kpi_final.kpi_final_costs.kpi_cost_vessel_internal")
    @patch("oriom.core.functions.kpi_final.kpi_final_costs.aux_functions.log_event_convert_stringtime", side_effect=lambda df: df)
    def test_no_mother_no_ctv(
        self,
        mock_log_convert,
        mock_kpi_cost,
        mock_create_lifetime_cost,
        mock_vdc_cls,
    ):
        log_events, log_events_merged = self._make_logs()

        vessels = [DummyVessel("V1"), DummyVessel("V2")]
        inputs = DummyInputs(2025, 2)

        # VesselDayCounter instance created inside kpi_final_total_cost
        mock_vdc_cls.return_value = DummyDayCounter(self._calendar_df())

        kpi_life = self._mk_kpi(["V1", "V2"], direct_cost=100, days=2)
        kpi_year_2025 = self._mk_kpi(["V1", "V2"], direct_cost=100, days=2)
        kpi_fuel = pd.DataFrame()

        # Called twice: (1) lifetime, (2) for year 2025 (since 2026 has no events)
        mock_kpi_cost.side_effect = [
            (kpi_life, pd.DataFrame(), pd.DataFrame()),
            (kpi_year_2025, pd.DataFrame(), pd.DataFrame()),
            (kpi_fuel, pd.DataFrame(), pd.DataFrame()),
        ]

        kpi_total, kpi_yearly, *_ = kpi_final_total_cost(
            log_events,
            log_events_merged,
            vessels,
            inputs,
            self._mock_vessel_day_counter(),   # vessel_day_counter (arg)
            MagicMock(),                       # find_element_class (unused here)
            [], [], [], [],                    # stats lists
            0, 0, 0,                           # fuel costs
            12,                                # duration_shift
            2,                                 # n_lifetime
            1000, 2000, 3000,                  # port, insurance, technician
            mother_vessels=[]
        )

        self.assertIn(("vessel_id", ""), kpi_yearly.columns)
        fixed = kpi_yearly[kpi_yearly[("vessel_id", "")] == "fixed_annual_cost"].iloc[0]
        self.assertEqual(fixed[(2025, "direct_costs")], 6000)

    # ------------------------------------------------------------------
    # TEST 2 — empty year (no events => yearly direct_costs = 0)
    # ------------------------------------------------------------------

    @patch("oriom.core.functions.kpi_final.kpi_final_costs.VesselDayCounter")
    @patch("oriom.core.functions.kpi_final.kpi_final_costs.create_lifetime_cost", side_effect=lambda df: df)
    @patch("oriom.core.functions.kpi_final.kpi_final_costs.kpi_cost_vessel_internal")
    @patch("oriom.core.functions.kpi_final.kpi_final_costs.aux_functions.log_event_convert_stringtime", side_effect=lambda df: df)
    def test_empty_year_zero_costs(
        self,
        mock_log_convert,
        mock_kpi_cost,
        mock_create_lifetime_cost,
        mock_vdc_cls,
    ):
        log_events, log_events_merged = self._make_logs(n=0)

        vessels = [DummyVessel("V1")]
        inputs = DummyInputs(2025, 1)

        mock_vdc_cls.return_value = DummyDayCounter(self._calendar_df())

        # Lifetime call happens even if year is empty; mock it.
        kpi_life = self._mk_kpi(["V1"], direct_cost=0, days=0)
        mock_kpi_cost.return_value = (kpi_life, pd.DataFrame(), pd.DataFrame())

        _, kpi_yearly, *_ = kpi_final_total_cost(
            log_events,
            log_events_merged,
            vessels,
            inputs,
            self._mock_vessel_day_counter(start="2025-01-01", end="2025-12-31"),
            MagicMock(),
            [], [], [], [],
            0, 0, 0,
            12, 1,
            0, 0, 0,
            mother_vessels=[]
        )

        row = kpi_yearly[kpi_yearly[("vessel_id", "")] == "V1"].iloc[0]
        self.assertEqual(row[(2025, "direct_costs")], 0)

    # ------------------------------------------------------------------
    # TEST 3 — total row (sum lifetime_direct_costs)
    # ------------------------------------------------------------------

    @patch("oriom.core.functions.kpi_final.kpi_final_costs.VesselDayCounter")
    @patch("oriom.core.functions.kpi_final.kpi_final_costs.create_lifetime_cost", side_effect=lambda df: df)
    @patch("oriom.core.functions.kpi_final.kpi_final_costs.kpi_cost_vessel_internal")
    @patch("oriom.core.functions.kpi_final.kpi_final_costs.aux_functions.log_event_convert_stringtime", side_effect=lambda df: df)
    def test_total_row(
        self,
        mock_log_convert,
        mock_kpi_cost,
        mock_create_lifetime_cost,
        mock_vdc_cls,
    ):
        log_events, log_events_merged = self._make_logs()

        vessels = [DummyVessel("V1"), DummyVessel("V2")]
        inputs = DummyInputs(2025, 1)

        mock_vdc_cls.return_value = DummyDayCounter(self._calendar_df(start="2025-01-01", end="2025-12-31"))

        kpi_life = self._mk_kpi(["V1", "V2"], direct_cost=0, days=2)
        # Set lifetime costs for total-row check
        kpi_life.loc[kpi_life["vessel_id"] == "V1", "lifetime_direct_costs"] = 100
        kpi_life.loc[kpi_life["vessel_id"] == "V2", "lifetime_direct_costs"] = 200

        # yearly call also needs n_chart_days
        kpi_year_2025 = kpi_life.copy()
        kpi_fuel = pd.DataFrame()

        mock_kpi_cost.side_effect = [
            (kpi_life, pd.DataFrame(), pd.DataFrame()),
            (kpi_year_2025, pd.DataFrame(), pd.DataFrame()),
            (kpi_fuel, pd.DataFrame(), pd.DataFrame()),
        ]

        kpi_total, *_ = kpi_final_total_cost(
            log_events,
            log_events_merged,
            vessels,
            inputs,
            self._mock_vessel_day_counter(start="2025-01-01", end="2025-12-31"),
            MagicMock(),
            [], [], [], [],
            0, 0, 0,
            12, 1,
            0, 0, 0,
            mother_vessels=[]
        )

        total = kpi_total[kpi_total["vessel_id"] == "total"].iloc[0]
        self.assertEqual(total["lifetime_direct_costs"], 300)


if __name__ == "__main__":
    unittest.main(verbosity=2)
