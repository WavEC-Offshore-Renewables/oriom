# tests/core/functions/operation_scheduler/test_shift_functions.py
import unittest
from datetime import datetime, timedelta

from logistic_tools.core.functions.operation_scheduler.shift_functions import (
    operation_consecutive,
    operation_consecutive_simultaneously,
    last_oper,
    results_data,
)


class TestOperationConsecutive(unittest.TestCase):
    def test_case_1_merge_ok_within_leadtime(self):
        # Expected by manual reasoning: (10.1, 2)
        hours, n_dev = operation_consecutive(
            duration_shift=12,
            duration_inspection=4,
            transit_between_devices=0.1,
            hours=6,
            n_oper=4,
            operation_concluded=2,
            end_wait_start_list_idx=[18, 18, 19, 20],
            day_start_idx=18,
        )
        self.assertAlmostEqual(hours, 10.1, places=6)
        self.assertEqual(n_dev, 2)

    def test_case_2_exceed_shift_duration(self):
        # Expected: (7, 1)
        hours, n_dev = operation_consecutive(
            duration_shift=12,
            duration_inspection=5,
            transit_between_devices=0.1,
            hours=7,
            n_oper=4,
            operation_concluded=2,
            end_wait_start_list_idx=[18, 18, 19, 20],
            day_start_idx=1,
        )
        self.assertAlmostEqual(hours, 7.0, places=6)
        self.assertEqual(n_dev, 1)

    def test_case_3_exceed_n_oper(self):
        # Expected: (6, 1)
        hours, n_dev = operation_consecutive(
            duration_shift=12,
            duration_inspection=4,
            transit_between_devices=0.1,
            hours=6,
            n_oper=4,
            operation_concluded=3,
            end_wait_start_list_idx=[18, 18, 19, 20],
            day_start_idx=18,
        )
        self.assertAlmostEqual(hours, 6.0, places=6)
        self.assertEqual(n_dev, 1)

    def test_case_4_exceed_leadtime(self):
        # Expected: (6, 1)
        hours, n_dev = operation_consecutive(
            duration_shift=12,
            duration_inspection=4,
            transit_between_devices=0.1,
            hours=6,
            n_oper=4,
            operation_concluded=2,
            end_wait_start_list_idx=[18, 18, 19, 20],
            day_start_idx=1,
        )
        self.assertAlmostEqual(hours, 6.0, places=6)
        self.assertEqual(n_dev, 1)


class TestOperationConsecutiveSimultaneously(unittest.TestCase):
    def test_case_1_merging_exceeds_shift_duration(self):
        # Correct result is (10.699999999999998, 8, 4)
        hours, n_dev, max_crew = operation_consecutive_simultaneously(
            duration_shift=12,
            duration_inspection=4,
            crew=4,
            transit_between_devices=0.1,
            hours=6,
            n_oper=12,
            operation_concluded=0,
            end_wait_start_list_idx=[18, 18, 18, 18, 18, 18, 18, 18, 19, 20, 20, 20],
            day_start_idx=18,
        )
        self.assertAlmostEqual(hours, 10.7, places=6)
        self.assertEqual(n_dev, 8)
        self.assertEqual(max_crew, 4)

    def test_case_2_merging_exceeds_crew_number(self):
        # Correct result is (6.1, 2, 2)
        hours, n_dev, max_crew = operation_consecutive_simultaneously(
            duration_shift=12,
            duration_inspection=4,
            crew=2,
            transit_between_devices=0.1,
            hours=6,
            n_oper=4,
            operation_concluded=2,
            end_wait_start_list_idx=[18, 18, 19, 20],
            day_start_idx=18,
        )
        self.assertAlmostEqual(hours, 6.1, places=6)
        self.assertEqual(n_dev, 2)
        self.assertEqual(max_crew, 2)

    def test_case_3_merging_exceeds_leadtime_list(self):
        # Correct result is (6.1, 2, 2)
        hours, n_dev, max_crew = operation_consecutive_simultaneously(
            duration_shift=12,
            duration_inspection=4,
            crew=4,
            transit_between_devices=0.1,
            hours=6,
            n_oper=4,
            operation_concluded=0,
            end_wait_start_list_idx=[1, 4, 19, 20],
            day_start_idx=1,
        )
        self.assertAlmostEqual(hours, 6.1, places=6)
        self.assertEqual(n_dev, 2)
        self.assertEqual(max_crew, 2)

    def test_case_4_merging_exceeds_n_device(self):
        # Correct result is (6.0, 1, 1)
        hours, n_dev, max_crew = operation_consecutive_simultaneously(
            duration_shift=12,
            duration_inspection=4,
            crew=4,
            transit_between_devices=0.1,
            hours=6,
            n_oper=4,
            operation_concluded=3,
            end_wait_start_list_idx=[18, 18, 19, 20],
            day_start_idx=18,
        )
        self.assertAlmostEqual(hours, 6.0, places=6)
        self.assertEqual(n_dev, 1)
        self.assertEqual(max_crew, 1)

    def test_case_5_small_shift_many_crews(self):
        # Correct result is (0.4, 5, 5)
        hours, n_dev, max_crew = operation_consecutive_simultaneously(
            duration_shift=2,
            duration_inspection=6,
            crew=6,
            transit_between_devices=0.1,
            hours=0,
            n_oper=5,
            operation_concluded=0,
            end_wait_start_list_idx=[2288] * 5,
            day_start_idx=2288,
        )
        self.assertAlmostEqual(hours, 0.4, places=6)
        self.assertEqual(n_dev, 5)
        self.assertEqual(max_crew, 5)

    def test_case_6_simultaneous_op_only(self):
        # Correct result is (0.4, 5, 5)
        hours, n_dev, max_crew = operation_consecutive_simultaneously(
            duration_shift=6,
            duration_inspection=6,
            crew=6,
            transit_between_devices=0.1,
            hours=0,
            n_oper=18,
            operation_concluded=0,
            end_wait_start_list_idx=[28834] * 18,
            day_start_idx=28834,
        )
        self.assertAlmostEqual(hours, 0.5, places=6)
        self.assertEqual(n_dev, 6)
        self.assertEqual(max_crew, 6)


class TestLastOper(unittest.TestCase):
    def test_case_1_n_shifts_capped_by_vessels(self):
        # Expected: (last_shift=0, dev_left=0, left_hours=0, n_shifts=3, last_max_crew=0)
        out = last_oper(
            n_shifts=12,
            n_vessel=3,
            dev_left=6,
            duration_inspection=4,
            operation_total_duration=6,
            transit_between_devices=0.1,
        )
        self.assertEqual(out, (0, 0, 0, 3, 0))

    def test_case_2_last_shift_exists(self):
        # Expected: (1, 2, 10.1, 2, 1)
        out = last_oper(
            n_shifts=2,
            n_vessel=3,
            dev_left=2,
            duration_inspection=4,
            operation_total_duration=6,
            transit_between_devices=0.1,
        )
        self.assertEqual(out, (1, 2, 10.1, 2, 1))

    def test_case_X_no_n_shifts_argument(self):
        # Expected: (1, 1, 5, None, 1)
        out = last_oper(
            n_vessel=3,
            dev_left=1,
            duration_inspection=4,
            operation_total_duration=5,
            transit_between_devices=0.1,
        )
        self.assertEqual(out, (1, 1, 5.0, None, 1))

    def test_case_3_no_dev_left(self):
        # Expected: (0, 0, 0, 2, 0)
        out = last_oper(
            n_shifts=2,
            n_vessel=3,
            dev_left=0,
            duration_inspection=4,
            operation_total_duration=6,
            transit_between_devices=0.1,
        )
        self.assertEqual(out, (0, 0, 0, 2, 0))

    def test_case_4_simultaneous_last_shift_under_crew(self):
        # Expected: (1, 3, 6.2, 2, 3)
        out = last_oper(
            n_shifts=2,
            n_vessel=3,
            dev_left=3,
            duration_inspection=4,
            operation_total_duration=6,
            transit_between_devices=0.1,
            max_crew=4,
        )
        self.assertEqual(out, (1, 3, 6.2, 2, 3))

    def test_case_5_simultaneous_last_shift_over_crew(self):
        # Expected: (1, 8, 10.7, 2, 4)
        out = last_oper(
            n_shifts=2,
            n_vessel=3,
            dev_left=8,
            duration_inspection=4,
            operation_total_duration=6,
            transit_between_devices=0.1,
            max_crew=4,
        )
        self.assertEqual(out, (1, 8, 10.7, 2, 4))


class TestResultsData(unittest.TestCase):
    def test_results_simple_consecutive(self):
        # Sanity check for results_data with consecutive (max_crew=None)
        res = results_data(
            n_device_shift=2,       # per shift
            dev_left=1,             # last shift devices
            n_shifts=2,             # two main shifts
            last_shift=1,           # plus a last shift
            operation_concluded=0,
            N_technicians_per_inspection=2,
            hours=9.0,
            left_hours=5.0,
            day_start_idx=100,
            day_start_oper=datetime(2020, 1, 1, 8, 0, 0),
            operation_total_duration=6.0,
            max_crew=None,          # consecutive => technicians = n_vessels * tech_per_insp
            last_max_crew=1,
        )
        # Unpack results
        op_conc, day_idx, day_end, total_dev, n_tech, n_vess = res

        # total_device_this_shift = 2*2 + 1 = 5
        self.assertEqual(total_dev, 5)
        self.assertEqual(op_conc, 5)

        # n_vessel_used = n_shifts + last_shift = 3
        self.assertEqual(n_vess, 3)

        # technicians = N_technicians_per_inspection * n_vessel_used = 2*3 = 6 (no simult)
        self.assertEqual(n_tech, 6)

        # hours_worked = max(hours, left_hours) = 9
        # day_start_idx += ceil(9 + 6) = 100 + 15 = 115
        self.assertEqual(day_idx, 115)

        # day_end = 8:00 + (9 + 6)h = 23:00
        self.assertEqual(day_end, datetime(2020, 1, 1, 23, 0, 0))

    def test_results_simultaneous(self):
        # With simultaneity (max_crew given), technicians calc changes
        res = results_data(
            n_device_shift=3,
            dev_left=2,
            n_shifts=2,
            last_shift=1,
            operation_concluded=4,
            N_technicians_per_inspection=3,
            hours=8.0,
            left_hours=10.0,  # dominates
            day_start_idx=200,
            day_start_oper=datetime(2021, 6, 1, 7, 0, 0),
            operation_total_duration=5.0,
            max_crew=4,
            last_max_crew=2,
        )
        op_conc, day_idx, day_end, total_dev, n_tech, n_vess = res

        # total_dev = 3*2 + 2 = 8 ; op_conc from 4 -> 12
        self.assertEqual(total_dev, 8)
        self.assertEqual(op_conc, 12)

        # n_vessel_used = 2 + 1 = 3
        self.assertEqual(n_vess, 3)

        # technicians = tech_per_insp * (max_crew*n_shifts + last_max_crew*last_shift)
        # = 3 * (4*2 + 2*1) = 3 * 10 = 30
        self.assertEqual(n_tech, 30)

        # hours_worked = max(8,10) = 10 ; idx += ceil(10+5)=15 -> 200+15=215
        self.assertEqual(day_idx, 215)
        # day_end = 7:00 + 15h = 22:00
        self.assertEqual(day_end, datetime(2021, 6, 1, 22, 0, 0))


if __name__ == '__main__':
    unittest.main(verbosity=2)
