#test_kpi_vessel_total

import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pandas as pd
import numpy as np

from logistic_tools.core.functions.kpi_final import kpi_vessel_total


class DummyVesselDayCounter:
    """
    Simple stub for the vessel_day_count argument.
    days is the number of charter days that will be returned.
    """

    def __init__(self, days):
        self._days = days

    def count_day_vessel(self, ves_id):
        return self._days


class TestKpiCostVesselInternalNoEvents(unittest.TestCase):
    """
    Basic test: no events, one vessel, everything should be zero.
    """

    @patch("logistic_tools.core.functions.kpi_final.kpi_vessel_total.safe_copy_df",
           side_effect=lambda df, cols: df.copy())
    @patch("logistic_tools.core.functions.kpi_final.kpi_vessel_total.calculate_event_costs")
    @patch("logistic_tools.core.functions.kpi_final.kpi_vessel_total.part_other_cost")
    @patch("logistic_tools.core.functions.kpi_final.kpi_vessel_total.kpi_aux.filter_df_events_per_vessel",
           side_effect=lambda df, ves_id, *args, **kwargs: df)
    @patch("logistic_tools.core.functions.kpi_final.kpi_vessel_total.kpi_aux.define_fuel_cost",
           return_value=0.0)
    @patch("logistic_tools.core.functions.kpi_final.kpi_vessel_total.VesselDayCounter")
    def test_single_vessel_no_events_zero_costs(
        self,
        mock_vdc_cls,
        mock_define_fuel_cost,
        mock_filter_df,
        mock_part_other_cost,
        mock_calc_event_costs,
        _mock_safe_copy,
    ):
        # All logs empty
        empty = pd.DataFrame()
        log_events_op_orig = empty.copy()
        log_events_op_merged_orig = empty.copy()
        log_events_op_def_merged_orig = empty.copy()
        log_events_op_merged_oper_orig = empty.copy()
        log_events_insp_merged_orig = empty.copy()
        log_events_mobi_merged_orig = empty.copy()
        log_events_tow_orig = empty.copy()
        log_events_op_port_orig = empty.copy()

        # calculate_event_costs always returns zeros
        mock_calc_event_costs.return_value = (0.0, 0.0, 0.0, 0.0, 0.0)
        # part_other_cost returns zeros
        mock_part_other_cost.return_value = (0.0, 0.0)

        # VesselDayCounter created for inspections -> 0 days
        mock_vdc_instance = MagicMock()
        mock_vdc_instance.count_day_vessel.return_value = 0
        mock_vdc_cls.return_value = mock_vdc_instance

        # vessel_day_count passed as argument: 0 charter days
        vessel_day_count = DummyVesselDayCounter(days=0)
        vessel_day_count_ST = DummyVesselDayCounter(days=0)

        # Single vessel with minimal attributes
        vessel = SimpleNamespace(
            id="V1",
            type="CTV",
            charter=0.0,
            annual_contract=0.0,
            n_ves_annual_contract=0,
            monthly_contract_cost=0.0,
            n_ves_monthly_contract=0,
            months_contract=[],
            mobilisation_cost=0.0,
        )

        kpi_om, kpi_om_type_cost = kpi_vessel_total.kpi_cost_vessel_internal(
            log_events_op_orig=log_events_op_orig,
            log_events_op_merged_orig=log_events_op_merged_orig,
            log_events_op_def_merged_orig=log_events_op_def_merged_orig,
            log_events_op_merged_oper_orig=log_events_op_merged_oper_orig,
            log_events_insp_merged_orig=log_events_insp_merged_orig,
            log_events_mobi_merged_orig=log_events_mobi_merged_orig,
            log_events_tow_orig=log_events_tow_orig,
            log_events_op_port_orig=log_events_op_port_orig,
            vessel_day_count=vessel_day_count,
            vessel_day_count_ST=vessel_day_count_ST,
            tech_per_oper_dict={},
            rov_cost_dict={},
            insp_port_data={},
            vessels=[vessel],
            duration_shift=12.0,
            total_operations=[],
            operations_tow_stat=[],
            inspections_site_stat=[],
            inspections_port_stat=[],
            fuel_cost_hfo=0.0,
            fuel_cost_mgo=0.0,
            fuel_cost_mdo=0.0,
            find_element_class = {}
        )

        # One row only, for the single vessel
        self.assertEqual(len(kpi_om), 1)
        row = kpi_om.iloc[0]

        # Charter days = 0
        self.assertEqual(row["n_chart_days"], 0)

        # All cost columns should be zero
        cost_cols = [
            "av_vessel_costs",
            "tot_vessel_costs",
            "av_mobilization_costs",
            "tot_mobilization_costs",
            "av_technicians_costs",
            "tot_technicians_costs",
            "av_part_costs",
            "tot_part_costs",
            "av_rov_costs",
            "tot_rov_costs",
            "av_other_costs",
            "tot_other_costs",
            "average_direct_costs",
            "lifetime_direct_costs",
        ]
        for c in cost_cols:
            self.assertEqual(row[c], 0.0)

        # kpi_om_type_cost has corrective and preventive both equal to 0
        self.assertEqual(set(kpi_om_type_cost["description"]), {"corrective", "preventive"})
        self.assertTrue((kpi_om_type_cost["values"] == 0.0).all())


class TestKpiCostVesselInternalWithEvents(unittest.TestCase):
    """
    Non-trivial test: one vessel, some costs and port operations,
    checking aggregation, averages, and op vs insp cost split.
    """

    @patch("logistic_tools.core.functions.kpi_final.kpi_vessel_total.safe_copy_df",
           side_effect=lambda df, cols: df.copy())
    @patch("logistic_tools.core.functions.kpi_final.kpi_vessel_total.calculate_event_costs")
    @patch("logistic_tools.core.functions.kpi_final.kpi_vessel_total.part_other_cost")
    @patch("logistic_tools.core.functions.kpi_final.kpi_vessel_total.kpi_aux.tech_rov_cost")
    @patch("logistic_tools.core.functions.kpi_final.kpi_vessel_total.kpi_aux.filter_df_events_per_vessel",
           side_effect=lambda df, ves_id, *args, **kwargs: df)
    @patch("logistic_tools.core.functions.kpi_final.kpi_vessel_total.kpi_aux.define_fuel_cost",
           return_value=1.0)
    @patch("logistic_tools.core.functions.kpi_final.kpi_vessel_total.VesselDayCounter")
    def test_single_vessel_with_costs_and_port_operations(
        self,
        mock_vdc_cls,
        _mock_define_fuel_cost,
        _mock_filter_df,
        mock_tech_rov_cost,
        mock_part_other_cost,
        mock_calc_event_costs,
        _mock_safe_copy,
    ):
        """
        We configure:
        - charter_days = 10
        - inspection vessel days = 4
        - mocked event costs:
          * merged corrective: (1, 10, 100, 1, 1000)
          * deferred merged:   (2, 20, 200, 2, 2000)
          * not-merged ops:    (3, 30, 300, 3, 3000)
          * tow ops:           (4, 40, 400, 4, 4000)
          * inspections:       (5, 50, 500, 5, 5000)

        This allows us to compute expected totals and op_cost / insp_cost.
        """

        # Create small non-empty logs so that branches are exercised
        log_events_op_orig = pd.DataFrame({"id": ["op.1"], "comments": ["c1"]})
        log_events_op_merged_orig = pd.DataFrame({"id": ["opm.1"], "comments": ["c2"]})
        log_events_op_def_merged_orig = pd.DataFrame({"id": ["opd.1"], "comments": ["c3"]})
        log_events_op_merged_oper_orig = pd.DataFrame({"id": ["opo.1"], "comments": ["c4"]})
        log_events_insp_merged_orig = pd.DataFrame({"id": ["insp.1"], "comments": ["i1"]})
        log_events_mobi_merged_orig = pd.DataFrame({"id": ["mob.1"], "comments": ["m1"], "n_vessel_1": [3]})
        log_events_tow_orig = pd.DataFrame({"id": ["tow.1"], "comments": ["t1"]})
        log_events_op_port_orig = pd.DataFrame({"id": ["port.1"], "comments": ["p1"]})

        # Side-effect for calculate_event_costs: different result per call
        # Call order in code: merged, def_merged, merged_oper, tow, inspections
        calc_returns = [
            (1.0, 10.0, 100.0, 1.0, 1000.0),   # merged
            (2.0, 20.0, 200.0, 2.0, 2000.0),   # deferred merged
            (3.0, 30.0, 300.0, 3.0, 3000.0),   # not merged ops
            (4.0, 40.0, 400.0, 4.0, 4000.0),   # tow
            (5.0, 50.0, 500.0, 5.0, 5000.0),   # inspections
        ]

        def calc_side_effect(*args, **kwargs):
            return calc_returns.pop(0)

        mock_calc_event_costs.side_effect = calc_side_effect

        # part_other_cost:
        # - first call: for operation logs
        # - second call: for port operations
        def part_other_side_effect(df, total_operations, find_element_class):
            if "op." in df.get("id", [""])[0]:
                return 100.0, 200.0  # (part_cost, other_cost) for vessel ops
            else:
                return 50.0, 60.0    # for port ops

        mock_part_other_cost.side_effect = part_other_side_effect

        # tech_rov_cost for port operations
        mock_tech_rov_cost.return_value = (50.0, 500.0)  # (tech_cost_port, rov_cost_port)

        # VesselDayCounter used inside function for inspections -> 4 days for vessel
        mock_vdc_instance = MagicMock()
        mock_vdc_instance.count_day_vessel.return_value = 4
        mock_vdc_cls.return_value = mock_vdc_instance

        # vessel_day_count argument: 10 charter days
        vessel_day_count = DummyVesselDayCounter(days=10)
        vessel_day_count_ST = DummyVesselDayCounter(days=8)

        # Single vessel with costs
        vessel = SimpleNamespace(
            id="V1",
            type="CTV",
            charter=100.0,              # €/day
            annual_contract=0.0,
            n_ves_annual_contract=0,
            monthly_contract_cost=0.0,
            n_ves_monthly_contract=0,
            months_contract=[],
            mobilisation_cost=10000.0,  # €/mobilisation day
        )

        kpi_om, kpi_om_type_cost = kpi_vessel_total.kpi_cost_vessel_internal(
            log_events_op_orig=log_events_op_orig,
            log_events_op_merged_orig=log_events_op_merged_orig,
            log_events_op_def_merged_orig=log_events_op_def_merged_orig,
            log_events_op_merged_oper_orig=log_events_op_merged_oper_orig,
            log_events_insp_merged_orig=log_events_insp_merged_orig,
            log_events_mobi_merged_orig=log_events_mobi_merged_orig,
            log_events_tow_orig=log_events_tow_orig,
            log_events_op_port_orig=log_events_op_port_orig,
            vessel_day_count=vessel_day_count,
            vessel_day_count_ST=vessel_day_count_ST,
            tech_per_oper_dict={"dummy": 1},
            rov_cost_dict={"dummy": 1},
            insp_port_data={},
            vessels=[vessel],
            duration_shift=12.0,
            total_operations=[],
            operations_tow_stat=[],
            inspections_site_stat=[],
            inspections_port_stat=[],
            fuel_cost_hfo=0.0,
            fuel_cost_mgo=0.0,
            fuel_cost_mdo=0.0,
            find_element_class = {}
        )

        # We expect two rows: vessel + 'oper_port'
        self.assertEqual(len(kpi_om), 2)

        # --- Check vessel row ---
        vessel_row = kpi_om[kpi_om["vessel_id"] == "V1"].iloc[0]

        # Charter days should be 10
        self.assertEqual(vessel_row["n_chart_days"], 10)

        # Transit / maneuver / standby totals and vessel_cost:
        # transit_cost = 1 + 2 + 3 + 5 + 4 = 15
        # maneuver_cost = 10 + 20 + 30 + 50 + 40 = 150
        # standby_cost = 100 + 200 + 300 + 500 + 400 = 1500
        # ST_charter_cost = 8 * 100 = 8000

        expected_vessel_cost_total = 800 + 15 + 150 + 1500  # = 2465
        self.assertAlmostEqual(vessel_row["tot_vessel_costs"], expected_vessel_cost_total, places=6)
        self.assertAlmostEqual(vessel_row["av_vessel_costs"], expected_vessel_cost_total / 10.0, places=6)

        # Tech costs:
        # tech_cost = 1+2+3+5+4 = 15
        self.assertAlmostEqual(vessel_row["tot_technicians_costs"], 15.0, places=6)
        self.assertAlmostEqual(vessel_row["av_technicians_costs"], 1.5, places=6)

        # Part / other costs from part_other_cost for operations
        self.assertAlmostEqual(vessel_row["tot_part_costs"], 100.0, places=6)
        self.assertAlmostEqual(vessel_row["av_part_costs"], 10.0, places=6)
        self.assertAlmostEqual(vessel_row["tot_other_costs"], 200.0, places=6)
        self.assertAlmostEqual(vessel_row["av_other_costs"], 20.0, places=6)

        # ROV cost:
        # rov_cost = 1000+2000+3000+5000+4000 = 15000
        self.assertAlmostEqual(vessel_row["tot_rov_costs"], 15000.0, places=6)
        self.assertAlmostEqual(vessel_row["av_rov_costs"], 1500.0, places=6)

        # Mobilisation: n_vessel_1 sum = 3
        self.assertAlmostEqual(vessel_row["av_mobilization_costs"], 10000.0, places=6)
        self.assertAlmostEqual(vessel_row["tot_mobilization_costs"], 30000.0, places=6)

        # Check lifetime and average direct costs
        avg_direct_expected = (
            vessel_row["av_vessel_costs"]
            + vessel_row["av_part_costs"]
            + vessel_row["av_technicians_costs"]
            + vessel_row["av_technicians_costs"]
            + vessel_row["av_other_costs"]
            + vessel_row["av_rov_costs"]
        )
        lifetime_direct_expected = (
            vessel_row["tot_vessel_costs"]
            + vessel_row["tot_part_costs"]
            + vessel_row["tot_technicians_costs"]
            + vessel_row["tot_mobilization_costs"]
            + vessel_row["tot_other_costs"]
            + vessel_row["tot_rov_costs"]
        )
        self.assertAlmostEqual(vessel_row["average_direct_costs"], avg_direct_expected, places=6)
        self.assertAlmostEqual(vessel_row["lifetime_direct_costs"], lifetime_direct_expected, places=6)

        # --- Check port operations row ---
        port_row = kpi_om[kpi_om["vessel_id"] == "oper_port"].iloc[0]

        # One operation at port
        self.assertEqual(port_row["n_chart_days"], 1)
        # Tech/ROV/part/other from mocks
        self.assertAlmostEqual(port_row["tot_technicians_costs"], 50.0, places=6)
        self.assertAlmostEqual(port_row["tot_rov_costs"], 500.0, places=6)
        self.assertAlmostEqual(port_row["tot_part_costs"], 50.0, places=6)
        self.assertAlmostEqual(port_row["tot_other_costs"], 60.0, places=6)
        # Averages equal to totals (1 operation)
        self.assertAlmostEqual(port_row["av_technicians_costs"], 50.0, places=6)
        self.assertAlmostEqual(port_row["av_rov_costs"], 500.0, places=6)
        self.assertAlmostEqual(port_row["av_part_costs"], 50.0, places=6)
        self.assertAlmostEqual(port_row["av_other_costs"], 60.0, places=6)

        # --- Check global op vs insp costs ---
        # From the specification above, the internal accumulation should give:
        # op_cost = 11720, insp_cost = 5960
        corr_val = float(kpi_om_type_cost[kpi_om_type_cost["description"] == "corrective"]["values"].iloc[0])
        prev_val = float(kpi_om_type_cost[kpi_om_type_cost["description"] == "preventive"]["values"].iloc[0])

        self.assertAlmostEqual(corr_val, 11720.0, places=6)
        self.assertAlmostEqual(prev_val, 5960.0, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
