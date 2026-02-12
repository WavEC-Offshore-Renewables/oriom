#test_InspectionSiteOrganizer

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

import pandas as pd

from logistic_tools.core.functions.logs_timeseries.InspectionSiteOrganizer import (
    InspectionSiteCreation,
)


class DummyInspClass:
    """Minimal insp_class container."""

    def __init__(self, vessel2_id=None, oper_sched=None):
        self.vessel2_id = vessel2_id
        self.ts_data = MagicMock()
        self.ts_data.oper_sched = oper_sched


class DummyInspection:
    """Minimal inspection object with only the attributes used by InspectionSiteCreation."""

    def __init__(self, iid="insp_1", vessel2_id=None, oper_sched=None):
        self.id = iid
        self.insp_class = DummyInspClass(vessel2_id=vessel2_id, oper_sched=oper_sched)


class TestInspectionSiteCreation(unittest.TestCase):
    """Unit tests for InspectionSiteCreation."""

    @patch(
        "logistic_tools.core.functions.logs_timeseries.InspectionSiteOrganizer."
        "logs_timeseries_func.inspection_statistic_duration"
    )
    def test_preventive_site_inspection_simple(self, mock_stat_dur):
        """Basic case: single inspection at site, no mother vessel campaign."""
        start = datetime(2025, 1, 1, 8, 0)
        oper_sched = pd.DataFrame(
            [
                {
                    "datetime": start,
                    "dur_total": 5.0,
                }
            ]
        )
        insp = DummyInspection(iid="insp_site", vessel2_id=None, oper_sched=oper_sched)
        creation = InspectionSiteCreation(insp)

        mock_stat_dur.return_value = 7.0

        mother_campaign = {}
        end_datetimes = []
        end_stat_chart_datetimes = []
        valid_datetimes = []

        find_element_class = MagicMock()
        find_element_class.find_operation_stats_pmax.return_value = MagicMock()

        creation.preventive_site_inspection(
            mother_vessel_inspection_campaign=mother_campaign,
            find_element_class=find_element_class,
            end_datetimes=end_datetimes,
            end_stat_chart_datetimes=end_stat_chart_datetimes,
            valid_datetimes=valid_datetimes,
            d=start,
        )

        # Check flags and lists
        self.assertTrue(creation.operation_completed)
        self.assertFalse(creation.inspection_campaign_flag)
        self.assertEqual(len(end_datetimes), 1)
        self.assertEqual(len(end_stat_chart_datetimes), 1)
        self.assertEqual(len(valid_datetimes), 1)

        # End of device = start + dur_total
        self.assertEqual(end_datetimes[0], start + timedelta(hours=5.0))
        # Statistical end = start + returned percentile duration
        self.assertEqual(end_stat_chart_datetimes[0], start + timedelta(hours=7.0))
        self.assertEqual(valid_datetimes[0], start)

        # Mother campaign dict not modified
        self.assertEqual(mother_campaign, {})

    @patch(
        "logistic_tools.core.functions.logs_timeseries.InspectionSiteOrganizer."
        "logs_timeseries_func.inspection_statistic_duration",
        return_value=4.0,
    )
    def test_preventive_site_inspection_campaign_first_time(self, mock_stat_dur):
        """
        Campaign case: vessel_2 is a mother vessel and no previous entry exists
        for the given (year, month, day). Must use the original 'd' and then
        store d_end_device in the campaign dict.
        """
        start = datetime(2025, 6, 10, 9, 0)
        oper_sched = pd.DataFrame(
            [
                {
                    "datetime": start,
                    "dur_total": 3.0,
                }
            ]
        )
        insp = DummyInspection(iid="insp_campaign", vessel2_id="MOTH1", oper_sched=oper_sched)
        creation = InspectionSiteCreation(insp)

        mother_campaign = {"MOTH1": {2025: {}}}
        end_datetimes = []
        end_stat_chart_datetimes = []
        valid_datetimes = []

        find_element_class = MagicMock()
        find_element_class.find_operation_stats_pmax.return_value = MagicMock()

        creation.preventive_site_inspection(
            mother_vessel_inspection_campaign=mother_campaign,
            find_element_class=find_element_class,
            end_datetimes=end_datetimes,
            end_stat_chart_datetimes=end_stat_chart_datetimes,
            valid_datetimes=valid_datetimes,
            d=start,
        )

        self.assertTrue(creation.operation_completed)
        self.assertTrue(creation.inspection_campaign_flag)

        # Lists must contain one entry
        self.assertEqual(len(end_datetimes), 1)
        self.assertEqual(len(end_stat_chart_datetimes), 1)
        self.assertEqual(len(valid_datetimes), 1)

        d_end_device = start + timedelta(hours=3.0)
        d_stat = start + timedelta(hours=4.0)

        self.assertEqual(end_datetimes[0], d_end_device)
        self.assertEqual(end_stat_chart_datetimes[0], d_stat)
        self.assertEqual(valid_datetimes[0], start)

        # Campaign dict must store the end date for this (month, day)
        self.assertIn((6, 10), mother_campaign["MOTH1"][2025])
        self.assertEqual(mother_campaign["MOTH1"][2025][(6, 10)], d_end_device)

    @patch(
        "logistic_tools.core.functions.logs_timeseries.InspectionSiteOrganizer."
        "approximate_hourly_data"
    )
    @patch(
        "logistic_tools.core.functions.logs_timeseries.InspectionSiteOrganizer."
        "logs_timeseries_func.inspection_statistic_duration",
        return_value=2.0,
    )
    def test_preventive_site_inspection_campaign_reuses_previous_date(
        self, mock_stat_dur, mock_approx
    ):
        """
        If an entry already exists in the campaign dict for the given (year, month, day),
        the code must use that datetime (after approximate_hourly_data) as new start 'd'.
        """
        # Original input date (will be overridden)
        d_input = datetime(2025, 6, 10, 9, 0)
        # Previously stored end-of-campaign date
        previous_end = datetime(2025, 6, 11, 10, 0)
        # approximate_hourly_data will be used to adjust this
        adjusted_start = previous_end + timedelta(hours=1)
        mock_approx.return_value = adjusted_start

        oper_sched = pd.DataFrame(
            [
                {
                    "datetime": adjusted_start,
                    "dur_total": 1.5,
                }
            ]
        )
        insp = DummyInspection(iid="insp_campaign2", vessel2_id="MOTH1", oper_sched=oper_sched)
        creation = InspectionSiteCreation(insp)

        mother_campaign = {"MOTH1": {2025: {(6, 10): previous_end}}}

        end_datetimes = []
        end_stat_chart_datetimes = []
        valid_datetimes = []

        find_element_class = MagicMock()
        find_element_class.find_operation_stats_pmax.return_value = MagicMock()

        creation.preventive_site_inspection(
            mother_vessel_inspection_campaign=mother_campaign,
            find_element_class=find_element_class,
            end_datetimes=end_datetimes,
            end_stat_chart_datetimes=end_stat_chart_datetimes,
            valid_datetimes=valid_datetimes,
            d=d_input,
        )

        self.assertTrue(creation.operation_completed)
        self.assertTrue(creation.inspection_campaign_flag)

        # approximate_hourly_data must be called with the previously stored date
        mock_approx.assert_called_once_with(data=previous_end, round_up=True)

        # Start used in the schedule is the adjusted_start
        self.assertEqual(len(valid_datetimes), 1)
        self.assertEqual(valid_datetimes[0], adjusted_start)

        # dur_total = 1.5 -> d_end_device = adjusted_start + 1.5h
        d_end_device = adjusted_start + timedelta(hours=1.5)
        d_stat = adjusted_start + timedelta(hours=2.0)

        self.assertEqual(end_datetimes[0], d_end_device)
        self.assertEqual(end_stat_chart_datetimes[0], d_stat)

        # Campaign dict must be updated with new end date
        self.assertEqual(mother_campaign["MOTH1"][2025][(6, 10)], d_end_device)

    def test_preventive_site_inspection_missing_schedule_row(self):
        """
        If the schedule row for the given datetime does not exist, the method must
        set operation_completed False and not append anything to the lists.
        """
        start = datetime(2025, 3, 1, 8, 0)
        other = datetime(2025, 3, 1, 9, 0)
        oper_sched = pd.DataFrame(
            [
                {
                    "datetime": other,
                    "dur_total": 2.0,
                }
            ]
        )
        insp = DummyInspection(iid="insp_missing", vessel2_id=None, oper_sched=oper_sched)
        creation = InspectionSiteCreation(insp)

        mother_campaign = {}
        end_datetimes = []
        end_stat_chart_datetimes = []
        valid_datetimes = []

        find_element_class = MagicMock()

        # No patch of inspection_statistic_duration is needed: code will fail before
        creation.preventive_site_inspection(
            mother_vessel_inspection_campaign=mother_campaign,
            find_element_class=find_element_class,
            end_datetimes=end_datetimes,
            end_stat_chart_datetimes=end_stat_chart_datetimes,
            valid_datetimes=valid_datetimes,
            d=start,
        )

        self.assertFalse(creation.operation_completed)
        self.assertEqual(end_datetimes, [])
        self.assertEqual(end_stat_chart_datetimes, [])
        self.assertEqual(valid_datetimes, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
