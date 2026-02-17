# tests/core/functions/KPI_final/test_kpi_extra.py

import unittest
from unittest.mock import patch
import pandas as pd
from datetime import datetime

from oriom.core.functions.kpi_final.kpi_extra import data_ctv_long_term_strategy


# ------------------------------------------------------------------
# Minimal test doubles
# ------------------------------------------------------------------

class DummyVessel:
    """Minimal vessel object with only attributes used by data_ctv_long_term_strategy."""

    def __init__(
        self,
        id_,
        charter=0.0,
        annual_contract=0.0,
        n_ves_annual_contract=0,
        monthly_contract_cost=0.0,
        n_ves_monthly_contract=0,
        months_contract=None,
    ):
        self.id = id_
        self.charter = charter
        self.annual_contract = annual_contract
        self.n_ves_annual_contract = n_ves_annual_contract
        self.monthly_contract_cost = monthly_contract_cost
        self.n_ves_monthly_contract = n_ves_monthly_contract
        self.months_contract = months_contract or []

    def copy(self):
        """Return a shallow copy (enough for the test)."""
        return DummyVessel(
            id_=self.id,
            charter=self.charter,
            annual_contract=self.annual_contract,
            n_ves_annual_contract=self.n_ves_annual_contract,
            monthly_contract_cost=self.monthly_contract_cost,
            n_ves_monthly_contract=self.n_ves_monthly_contract,
            months_contract=list(self.months_contract),
        )


class BaseVesselDayCounter:
    """Day-counter used when n_long_term_try == n_long_term (reuse actual simulation)."""

    def __init__(self, days_for_vessel):
        self._days_for_vessel = dict(days_for_vessel)

    def count_day_vessel(self, vessel_id):
        return self._days_for_vessel.get(vessel_id, 0)


class FakeVesselDayCounter:
    """
    Replacement for VesselDayCounter used inside data_ctv_long_term_strategy
    when n_long_term_try != n_long_term.

    It returns a deterministic number of short-term days depending on the
    current vessel contract (ves.n_ves_annual_contract), so we can assert
    the sensitivity branch is actually used.
    """

    created_instances = []

    def __init__(self, log_events_merged, vessels):
        # Store for inspection/debug if needed
        self.log_events_merged = log_events_merged
        self.vessels = vessels[0]
        FakeVesselDayCounter.created_instances.append(self)

    def allocate_vessels(self, **kwargs):
        # The function only needs a DataFrame to feed the next VesselDayCounter init.
        # Keep it simple and return a copy.
        return self.log_events_merged.copy()

    def count_day_vessel(self, vessel_id):
        # Make ST days depend on trial long-term contract (n_ves_annual_contract).
        # This lets us verify the branch changes the result across strategies.
        trial_contract = getattr(self.vessels, "n_ves_annual_contract", 0)
        return 10 + int(trial_contract)


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

class TestDataCtvLongTermStrategy(unittest.TestCase):

    def _make_log_events_merged(self):
        # Minimal input; function copies it and sets ST_contract column anyway.
        return pd.DataFrame(
            {
                "event": ["operation"],
                "ST_contract_1": [True],
                "ST_contract_2": [False],
                "d_end_stat_chart_orig": datetime(2012,6,1, 8),
                "n_vessel_1": 1,

            }
        )

    def test_strategy_keys_and_costs_small_n_long_term(self):
        """
        For n_ves_annual_contract = 2, len_simulation = range(0, 6) => keys 0..5.

        Verify:
        - output keys
        - short-term cost uses base day counter for k == n_long_term
        - sensitivity branch changes short-term days for k != n_long_term
        - long-term cost follows: n_lifetime * (annual_contract*k + LT_monthly)
        """
        vessel = DummyVessel(
            id_="CTV",
            charter=300,
            annual_contract=10000,
            n_ves_annual_contract=2,
            monthly_contract_cost=2000,
            n_ves_monthly_contract=1,
            months_contract=[6, 7, 8],
        )

        # Base day counter used when k == 2
        base_day_counter = BaseVesselDayCounter({"CTV": 12})  # 10 + 2 (consistent with Fake)
        log_events_merged = self._make_log_events_merged()
        n_lifetime = 3

        FakeVesselDayCounter.created_instances = []

        with patch(
            "oriom.core.functions.kpi_final.kpi_extra.VesselDayCounter",
            new=FakeVesselDayCounter,
        ):
            out = data_ctv_long_term_strategy(
                v=vessel,
                log_events_merged=log_events_merged,
                n_lifetime=n_lifetime,
            )

        # Expected strategy keys: 0..(2+3) => 0..5
        self.assertEqual(sorted(out.keys()), [0, 1, 2, 3, 4, 5])

        lt_monthly = 2000 * 1 * 3  # monthly_contract_cost * n_ves_monthly_contract * len(months_contract)
        # Long-term cost multiplies the whole bracket by n_lifetime (per implementation)
        # LT(k) = n_lifetime * (annual_contract*k + lt_monthly)

        for k, costs in out.items():
            expected_lt = n_lifetime * (10000 * k + lt_monthly)

            # Short-term days:
            # - For k == 2, function uses base_day_counter => 12 days
            # - For k != 2, function uses FakeVesselDayCounter => 10 + k days
            if k == 2:
                expected_st_days = 12
            else:
                expected_st_days = 10 + k

            expected_st = expected_st_days * 300

            self.assertEqual(costs["short_term_cost"], expected_st)
            self.assertEqual(costs["long_term_cost"], expected_lt)
            self.assertEqual(costs["tot_cost"], expected_st + expected_lt)

        # Optional sanity: ensure sensitivity branch instantiated VesselDayCounter at least once
        self.assertGreaterEqual(len(FakeVesselDayCounter.created_instances), 1)

    def test_strategy_uses_sliding_window_when_range_too_large(self):
        """
        If range(0, n_long_term+4) is longer than 8, implementation uses:
            range(n_long_term-5, n_long_term+4)

        Example: n_long_term = 10 => keys 5..13 (9 keys).
        """
        vessel = DummyVessel(
            id_="CTV",
            charter=100,
            annual_contract=1000,
            n_ves_annual_contract=10,
            monthly_contract_cost=0,
            n_ves_monthly_contract=0,
            months_contract=[],
        )

        base_day_counter = BaseVesselDayCounter({"CTV": 20})
        log_events_merged = self._make_log_events_merged()

        with patch(
            "oriom.core.functions.kpi_final.kpi_extra.VesselDayCounter",
            new=FakeVesselDayCounter,
        ):
            out = data_ctv_long_term_strategy(
                v=vessel,
                log_events_merged=log_events_merged,
                n_lifetime=1,
            )

        self.assertEqual(sorted(out.keys()), list(range(5, 14)))  # 5..13 inclusive


if __name__ == "__main__":
    unittest.main(verbosity=2)
