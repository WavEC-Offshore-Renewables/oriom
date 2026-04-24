#test_logs_preventive_aux

import unittest
from unittest.mock import MagicMock

from datetime import datetime

import pandas as pd

from oriom.core.functions.logs_timeseries import logs_preventive_aux


class DummyInspClass:
    """Minimal insp_class for start_date_inspection tests."""

    def __init__(self, months, periodicity, day_start=1):
        self.months = months
        self.periodicity = periodicity
        self.day_start = day_start


class DummyInspection:
    """Minimal inspection object with insp_class and dur_total_dict."""

    def __init__(self, iid, months, periodicity, day_start, dur_total_dict):
        self.id = iid
        self.insp_class = DummyInspClass(
            months=months,
            periodicity=periodicity,
            day_start=day_start,
        )
        # Keys must be strings for dur_total_dict
        self.dur_total_dict = {str(k): v for k, v in dur_total_dict.items()}


class TestTakeOpScheduleTow(unittest.TestCase):
    def test_take_op_schedule_tow_returns_schedule(self):
        """take_op_schedule_tow should return the oper_sched of the towing operation."""
        df_sched = pd.DataFrame({"datetime": [datetime(2025, 1, 1, 8, 0)], "dur_total": [5.0]})

        tow_stat = MagicMock()
        tow_stat.op_class.ts_data.oper_sched = df_sched

        insp = MagicMock()
        insp.insp_class.op_tow_port = "tow_op_01"

        find_element_class = MagicMock()
        find_element_class.find_operation_stats.return_value = tow_stat

        result = logs_preventive_aux.take_op_schedule_tow(
            inspection=insp,
            find_element_class=find_element_class,
            op_tow="op_tow_port",
        )

        find_element_class.find_operation_stats.assert_called_once_with("tow_op_01")
        self.assertIs(result, df_sched)


class TestCreateSublists(unittest.TestCase):
    def test_create_sublists_even_split(self):
        """create_sublists should split evenly when length is divisible by n."""
        numbers = [1, 2, 3, 4]
        sublists = logs_preventive_aux.create_sublists(numbers, 2)
        self.assertEqual(len(sublists), 2)
        self.assertEqual(sublists[0], [1, 2])
        self.assertEqual(sublists[1], [3, 4])

    def test_create_sublists_uneven_split(self):
        """create_sublists should distribute remainder elements to the first sublists."""
        numbers = [1, 2, 3, 4, 5]
        sublists = logs_preventive_aux.create_sublists(numbers, 3)
        lengths = [len(sl) for sl in sublists]
        self.assertEqual(lengths, [2, 2, 1])
        self.assertEqual(sum(len(sl) for sl in sublists), len(numbers))
        self.assertEqual(sorted(sum(sublists, [])), numbers)

    def test_create_sublists_more_groups_than_elements(self):
        """create_sublists should create empty sublists when n > len(numbers)."""
        numbers = [1, 2, 3]
        sublists = logs_preventive_aux.create_sublists(numbers, 5)
        self.assertEqual(len(sublists), 5)
        self.assertEqual(sorted(sum(sublists, [])), numbers)
        # First len(numbers) sublists will contain the elements, the rest will be empty
        self.assertEqual([len(sl) for sl in sublists[:3]], [1, 1, 1])
        self.assertEqual([len(sl) for sl in sublists[3:]], [0, 0])


class TestReciprocal(unittest.TestCase):
    def test_reciprocal_basic(self):
        """reciprocal should return 1.0 / n."""
        self.assertEqual(logs_preventive_aux.reciprocal(2), 0.5)
        self.assertAlmostEqual(logs_preventive_aux.reciprocal(4), 0.25)

    def test_reciprocal_float(self):
        """reciprocal should work with floats as well."""
        self.assertAlmostEqual(logs_preventive_aux.reciprocal(0.5), 2.0)


class TestDateRangesOverlap(unittest.TestCase):
    def test_overlap_true(self):
        """date_ranges_overlap returns True for overlapping ranges."""
        s1 = datetime(2025, 1, 1, 8)
        e1 = datetime(2025, 1, 1, 12)
        s2 = datetime(2025, 1, 1, 10)
        e2 = datetime(2025, 1, 1, 14)
        self.assertTrue(logs_preventive_aux.date_ranges_overlap(s1, e1, s2, e2))

    def test_overlap_contained(self):
        """date_ranges_overlap returns True when one range is fully contained in the other."""
        s1 = datetime(2025, 1, 1, 8)
        e1 = datetime(2025, 1, 1, 18)
        s2 = datetime(2025, 1, 1, 9)
        e2 = datetime(2025, 1, 1, 10)
        self.assertTrue(logs_preventive_aux.date_ranges_overlap(s1, e1, s2, e2))

    def test_overlap_false_disjoint(self):
        """date_ranges_overlap returns False for clearly disjoint ranges."""
        s1 = datetime(2025, 1, 1, 8)
        e1 = datetime(2025, 1, 1, 9)
        s2 = datetime(2025, 1, 1, 10)
        e2 = datetime(2025, 1, 1, 11)
        self.assertFalse(logs_preventive_aux.date_ranges_overlap(s1, e1, s2, e2))

    def test_overlap_false_touching_at_boundary(self):
        """date_ranges_overlap returns False when start1 == end2 as per implementation."""
        s1 = datetime(2025, 1, 1, 10)
        e1 = datetime(2025, 1, 1, 12)
        s2 = datetime(2025, 1, 1, 8)
        e2 = s1  # equal to start1
        self.assertFalse(logs_preventive_aux.date_ranges_overlap(s1, e1, s2, e2))


class TestStartDateInspectionPeriodicGE1(unittest.TestCase):
    def test_periodic_ge1_months_none(self):
        """
        If months is None and periodicity >= 1, it should:
        - expand months to 1..12
        - choose the month with minimal dur_total
        - produce one date per year within lifetime at 08:00.
        """
        dur_dict = {m: 10.0 for m in range(1, 13)}
        dur_dict[5] = 1.0  # Unique minimum at May

        inspection = DummyInspection(
            iid="insp_ge1_none",
            months=None,
            periodicity=1,
            day_start=10,
            dur_total_dict=dur_dict,
        )

        datetimes = logs_preventive_aux.start_date_inspection(
            inspection=inspection,
            start_year=2020,
            start_month=1,
            n_lifetime=3,
        )

        self.assertEqual(len(datetimes), 3)
        for year, dt in zip([2020, 2021, 2022], datetimes):
            self.assertEqual(dt, datetime(year, 5, 10, 8, 0, 0))

        # months must have been expanded to full year
        self.assertEqual(inspection.insp_class.months, list(range(1, 13)))

    def test_periodic_ge1_single_month(self):
        """
        If months is a single int and periodicity >= 1, dates should fall on that month/day at 08:00.
        """
        dur_dict = {3: 2.0, 7: 1.0}  # Only month=7 used
        inspection = DummyInspection(
            iid="insp_ge1_single",
            months=7,
            periodicity=1,
            day_start=15,
            dur_total_dict=dur_dict,
        )

        datetimes = logs_preventive_aux.start_date_inspection(
            inspection=inspection,
            start_year=2020,
            start_month=1,
            n_lifetime=2,
        )

        self.assertEqual(len(datetimes), 2)
        self.assertEqual(datetimes[0], datetime(2020, 7, 15, 8, 0, 0))
        self.assertEqual(datetimes[1], datetime(2021, 7, 15, 8, 0, 0))

    def test_periodic_ge1_months_list(self):
        """
        If months is a list and periodicity >= 1, should pick the month with minimum dur_total
        among the selected months.
        """
        dur_dict = {3: 5.0, 9: 2.0, 12: 7.0}
        inspection = DummyInspection(
            iid="insp_ge1_list",
            months=[3, 9, 12],
            periodicity=2,   # every 2 years
            day_start=5,
            dur_total_dict=dur_dict,
        )

        datetimes = logs_preventive_aux.start_date_inspection(
            inspection=inspection,
            start_year=2020,
            start_month=1,
            n_lifetime=5,
        )
        # Minimum dur_total is at month 9
        expected_years = [2022, 2024]
        self.assertEqual(len(datetimes), len(expected_years))
        for year, dt in zip(expected_years, datetimes):
            self.assertEqual(dt, datetime(year, 9, 5, 8, 0, 0))


class TestStartDateInspectionPeriodicLT1(unittest.TestCase):
    def test_periodic_lt1_valid(self):
        """
        For periodicity < 1, the function should:
        - derive n_times = 1 / periodicity
        - split months into n sublists
        - for each sublist choose the month with minimum dur_total
        - generate dates at 06:00 for each year & chosen month.
        """
        dur_dict = {
            3: 5.0,   # group 1
            9: 2.0,   # group 1 -> minimum
            6: 3.0,   # group 2 -> minimum
            12: 4.0,  # group 2
        }
        inspection = DummyInspection(
            iid="insp_lt1_valid",
            months=[3, 9, 6, 12],
            periodicity=0.5,   # twice per year
            day_start=20,
            dur_total_dict=dur_dict,
        )

        datetimes = logs_preventive_aux.start_date_inspection(
            inspection=inspection,
            start_year=2020,
            start_month=1,
            n_lifetime=3,
        )

        # n_times = 2, list_year = [2020, 2021, 2022] => 6 dates
        self.assertEqual(len(datetimes), 6)

        # Because create_sublists([3,9,6,12],2) -> [[3,9],[6,12]],
        # first group month 9, second group month 6.
        first_three = datetimes[:3]
        last_three = datetimes[3:]

        for year, dt in zip([2020, 2021, 2022], first_three):
            self.assertEqual(dt, datetime(year, 9, 20, 6, 0, 0))

        for year, dt in zip([2020, 2021, 2022], last_three):
            self.assertEqual(dt, datetime(year, 6, 20, 6, 0, 0))

    def test_periodic_lt1_raises_if_not_enough_months(self):
        """
        If periodicity < 1 and len(months) < n_times, a ValueError must be raised.
        """
        dur_dict = {3: 1.0}
        inspection = DummyInspection(
            iid="insp_lt1_error",
            months=[3],
            periodicity=0.25,  # 4 times per year
            day_start=1,
            dur_total_dict=dur_dict,
        )

        with self.assertRaises(ValueError):
            logs_preventive_aux.start_date_inspection(
                inspection=inspection,
                start_year=2020,
                start_month=1,
                n_lifetime=3,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
