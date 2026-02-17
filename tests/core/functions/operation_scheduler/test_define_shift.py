import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from oriom.core.functions.operation_scheduler.define_shift import output_working_shifts, merge_shift_deferred


class TestOutputWorkingShiftsGolden(unittest.TestCase):
    """Golden tests that mirror the examples you printed in __main__."""

    def test_output_working_shifts_1_minor_correction(self):
        out = output_working_shifts(
            N_devices=1,
            duration_shift=12,
            duration_inspection=6,
            rov=False,
            transit=0.5788,
            transit_between_devices=0.1,
            vessel_type='ctv',
            N_technicians_on_vessel=12,
            N_technicians_per_inspection=2,
            N_vessels=3
        )
        # Expected (from example)
        self.assertEqual(out["main_working_shift"]["number_shifts"], 0)
        self.assertAlmostEqual(out["main_working_shift"]["duration_shift"], 0.0, places=2)
        self.assertEqual(out["main_working_shift"]["number_inspections_per_shift"], 0)
        self.assertEqual(out["main_working_shift"]["number_vessels"], 0)

        self.assertEqual(out["last_working_shift"]["number_shifts"], 1)
        self.assertAlmostEqual(out["last_working_shift"]["duration_shift"], 7.16, places=2)
        self.assertEqual(out["last_working_shift"]["number_inspections_per_shift"], 1)
        self.assertEqual(out["last_working_shift"]["number_vessels"], 1)

    def test_output_working_shifts_2_simultaneous_no_last(self):
        out = output_working_shifts(
            N_devices=36,
            duration_shift=12,
            duration_inspection=4,
            rov=False,
            transit=0.5,
            transit_between_devices=0.1,
            vessel_type='ctv',
            N_technicians_on_vessel=12,
            N_technicians_per_inspection=2,
            N_vessels=3
        )
        self.assertEqual(out["main_working_shift"]["number_shifts"], 1)
        self.assertAlmostEqual(out["main_working_shift"]["duration_shift"], 10.1, places=2)
        self.assertEqual(out["main_working_shift"]["number_inspections_per_shift"], 12)
        self.assertEqual(out["main_working_shift"]["number_vessels"], 3)

        self.assertEqual(out["last_working_shift"]["number_shifts"], 0)
        self.assertAlmostEqual(out["last_working_shift"]["duration_shift"], 0.0, places=2)
        self.assertEqual(out["last_working_shift"]["number_inspections_per_shift"], 0)
        self.assertEqual(out["last_working_shift"]["number_vessels"], 0)

    def test_output_working_shifts_3_consecutive_no_last(self):
        out = output_working_shifts(
            N_devices=36,
            duration_shift=12,
            duration_inspection=4,
            rov=True,
            transit=0.5,
            transit_between_devices=0.1,
            vessel_type='ctv',
            N_technicians_on_vessel=12,
            N_technicians_per_inspection=2,
            N_vessels=3
        )
        self.assertEqual(out["main_working_shift"]["number_shifts"], 6)
        self.assertAlmostEqual(out["main_working_shift"]["duration_shift"], 9.1, places=2)
        self.assertEqual(out["main_working_shift"]["number_inspections_per_shift"], 2)
        self.assertEqual(out["main_working_shift"]["number_vessels"], 3)

        self.assertEqual(out["last_working_shift"]["number_shifts"], 0)
        self.assertAlmostEqual(out["last_working_shift"]["duration_shift"], 0.0, places=2)
        self.assertEqual(out["last_working_shift"]["number_inspections_per_shift"], 0)
        self.assertEqual(out["last_working_shift"]["number_vessels"], 0)

    def test_output_working_shifts_4_consecutive_with_last(self):
        out = output_working_shifts(
            N_devices=49,
            duration_shift=12,
            duration_inspection=4,
            rov=True,
            transit=0.5,
            transit_between_devices=0.1,
            vessel_type='ctv',
            N_technicians_on_vessel=12,
            N_technicians_per_inspection=2,
            N_vessels=3
        )
        self.assertEqual(out["main_working_shift"]["number_shifts"], 8)
        self.assertAlmostEqual(out["main_working_shift"]["duration_shift"], 9.1, places=2)
        self.assertEqual(out["main_working_shift"]["number_inspections_per_shift"], 2)
        self.assertEqual(out["main_working_shift"]["number_vessels"], 3)

        self.assertEqual(out["last_working_shift"]["number_shifts"], 1)
        self.assertAlmostEqual(out["last_working_shift"]["duration_shift"], 5.0, places=2)
        self.assertEqual(out["last_working_shift"]["number_inspections_per_shift"], 1)
        self.assertEqual(out["last_working_shift"]["number_vessels"], 1)

    def test_output_working_shifts_5_heavy_transit_last_only(self):
        out = output_working_shifts(
            N_devices=84,
            duration_shift=12,
            duration_inspection=1,
            rov=False,
            transit=2.31,
            transit_between_devices=0.01,
            vessel_type='ctv',
            N_technicians_on_vessel=12,
            N_technicians_per_inspection=2,
            N_vessels=3
        )
        self.assertEqual(out["main_working_shift"]["number_shifts"], 0)
        self.assertAlmostEqual(out["main_working_shift"]["duration_shift"], 0.0, places=2)
        self.assertEqual(out["main_working_shift"]["number_inspections_per_shift"], 0)
        self.assertEqual(out["main_working_shift"]["number_vessels"], 0)

        self.assertEqual(out["last_working_shift"]["number_shifts"], 1)
        self.assertAlmostEqual(out["last_working_shift"]["duration_shift"], 12.0, places=2)
        self.assertEqual(out["last_working_shift"]["number_inspections_per_shift"], 39)
        self.assertEqual(out["last_working_shift"]["number_vessels"], 3)

    def test_output_working_shifts_6_sv_last_only(self):
        out = output_working_shifts(
            N_devices=6,
            duration_shift=12,
            duration_inspection=5.3,
            rov=False,
            transit=2.31,
            transit_between_devices=0.01,
            vessel_type='sv',
            N_technicians_on_vessel=50,
            N_technicians_per_inspection=2,
            N_vessels=1
        )
        self.assertEqual(out["main_working_shift"]["number_shifts"], 6)
        self.assertAlmostEqual(out["main_working_shift"]["duration_shift"], 9.92, places=2)
        self.assertEqual(out["main_working_shift"]["number_inspections_per_shift"], 1)
        self.assertEqual(out["main_working_shift"]["number_vessels"], 1)

        self.assertEqual(out["last_working_shift"]["number_shifts"], 0)
        self.assertAlmostEqual(out["last_working_shift"]["duration_shift"], 0, places=2)
        self.assertEqual(out["last_working_shift"]["number_inspections_per_shift"], 0)
        self.assertEqual(out["last_working_shift"]["number_vessels"], 0)


class TestMergeShiftDeferredGolden(unittest.TestCase):
    """Golden tests for merge_shift_deferred. Caso 2 con expected esatto, gli altri con sanity checks."""

    def test_merge_shift_deferred_2_exact_expected(self):
        out = merge_shift_deferred(
            duration_shift=2,
            duration_inspection=6,
            transit_between_devices=0.1,
            operation_total_duration=7.16,
            n_vessel=3,
            n_oper=5,
            operation_concluded=0,
            end_wait_start_list_idx=[2288] * 5,
            day_start_idx=2288,
            N_technicians_on_vessel=12,
            N_technicians_per_inspection=2,
            vessel_type='ctv',
            rov=None,
            day_start_oper=pd.Timestamp("1990-04-06 08:00:00")
        )
        exp = (5, 2296, pd.Timestamp("1990-04-06 15:33:36"), 5, 10, 1)
        self.assertEqual(out, exp)

    def test_merge_shift_deferred_1_types_and_consistency(self):
        out = merge_shift_deferred(
            duration_shift=0,
            duration_inspection=2,
            transit_between_devices=0.015,
            operation_total_duration=6.62,
            n_vessel=3,
            n_oper=31,
            operation_concluded=0,
            end_wait_start_list_idx=[2168] * 31,
            day_start_idx=2168,
            N_technicians_on_vessel=12,
            N_technicians_per_inspection=2,
            vessel_type='ctv',
            rov=None,
            day_start_oper=pd.Timestamp("1990-04-01 08:00:00")
        )
        # Basic shape and types
        self.assertIsInstance(out, tuple)
        self.assertEqual(len(out), 6)
        op_concluded, day_start_idx, day_shift_end, total_dev, n_tech, n_vess_used = out
        self.assertIsInstance(op_concluded, int)
        self.assertIsInstance(day_start_idx, int)
        self.assertIsInstance(day_shift_end, pd.Timestamp)
        self.assertIsInstance(total_dev, int)
        self.assertIsInstance(n_tech, int)
        self.assertIsInstance(n_vess_used, int)
        # Minimal sanity
        self.assertGreaterEqual(op_concluded, 0)
        self.assertGreaterEqual(total_dev, 0)
        self.assertGreaterEqual(n_tech, 0)
        self.assertGreaterEqual(n_vess_used, 0)

    def test_merge_shift_deferred_3_sanity(self):
        out = merge_shift_deferred(
            duration_shift=6,
            duration_inspection=6,
            transit_between_devices=0.1,
            operation_total_duration=7.16,
            n_vessel=3,
            n_oper=18,
            operation_concluded=0,
            end_wait_start_list_idx=[37496] * 18,
            day_start_idx=37496,
            N_technicians_on_vessel=12,
            N_technicians_per_inspection=2,
            vessel_type='ctv',
            rov=None,
            day_start_oper=pd.Timestamp("1994-04-12 08:00:00")
        )
        self.assertIsInstance(out, tuple)
        self.assertEqual(len(out), 6)

    def test_merge_shift_deferred_4_sanity(self):
        out = merge_shift_deferred(
            duration_shift=12,
            duration_inspection=24,
            transit_between_devices=0.015,
            operation_total_duration=27.27,
            n_vessel=1,
            n_oper=2,
            operation_concluded=1,
            end_wait_start_list_idx=[133665] * 3,
            day_start_idx=133692,
            N_technicians_on_vessel=12,
            N_technicians_per_inspection=4,
            vessel_type='wv',
            rov=None,
            day_start_oper=pd.Timestamp("2005-04-02 12:00:00")
        )
        self.assertIsInstance(out, tuple)
        self.assertEqual(len(out), 6)


if __name__ == '__main__':
    unittest.main(verbosity=2)
