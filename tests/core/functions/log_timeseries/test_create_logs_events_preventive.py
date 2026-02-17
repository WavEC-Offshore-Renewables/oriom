#test_create_logs_events_preventive

import unittest
from unittest.mock import patch
from datetime import datetime, timedelta

import pandas as pd

from oriom.core.functions.logs_timeseries.create_logs_events_preventive import (
    create_logs_preventive,
)


class DummyStats:
    """Minimal stats object holding start year, month and lifetime."""

    def __init__(self, start_year=2020, start_month=1, lifetime=2):
        self.start_year = {"value": start_year}
        self.start_month = {"value": start_month}
        self.lifetime = {"value": lifetime}


class DummyInputs:
    """Minimal Inputs object exposing a .stats attribute."""

    def __init__(self, stats: DummyStats):
        self.stats = stats


class DummyVessel:
    """Minimal Vessel object used in inspections and mother_vessels_list."""

    def __init__(self, vid: str, mobilisation_time: float = 0.0):
        self.id = vid
        self.mobilisation_time = mobilisation_time


class DummyInspClass:
    """Minimal inspection 'class' object that includes id and vessel1."""

    def __init__(self, iid: str, vessel1: DummyVessel):
        self.id = iid
        self.vessel1 = vessel1


class DummyInspection:
    """
    Minimal inspection wrapper used by create_logs_preventive.

    For site inspections:
        - insp.vessel1 is accessed
        - insp.insp_class is accessed
    For port inspections:
        - insp.insp_class.vessel1 is accessed
        - insp.vessel1 is used in mobilisation
    """

    def __init__(self, iid: str, vessel: DummyVessel):
        self.id = iid
        self.vessel1 = vessel
        self.insp_class = DummyInspClass(iid, vessel)


class TestCreateLogsPreventive(unittest.TestCase):
    """Tests for create_logs_preventive."""

    def setUp(self):
        # Minimal set of columns required to run the function
        self.COLS = ["d_trigger", "d_end", "event", "id", "vessel_1"]
        stats = DummyStats(start_year=2020, start_month=1, lifetime=1)
        self.inputs = DummyInputs(stats=stats)

    def test_no_inspections_returns_empty_dataframe(self):
        """If there are no site or port inspections, the result must be an empty DataFrame."""

        result = create_logs_preventive(
            COLS=self.COLS,
            inputs=self.inputs,
            inspections_port_stat=[],
            inspections_site_stat=[],
            find_element_class=None,
            percentile=0.9,
            mother_vessels_list=[],
        )

        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)
        self.assertListEqual(list(result.columns), self.COLS)

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_preventive."
        "logs_timeseries_func.create_mobilisation"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_preventive."
        "define_dates_inspection.define_dates"
    )
    def test_site_inspection_with_mobilisation_creates_inspection_and_mob_rows(
        self, mock_define_dates, mock_create_mob
    ):
        """
        For a site inspection with vessel.mobilisation_time != 0:
        - define_dates_inspection.define_dates is called once
        - one mobilisation row is created per inspection row
        - resulting DataFrame has inspection rows + mobilisation rows.
        """

        vessel = DummyVessel("CTV-1", mobilisation_time=24.0)
        inspection = DummyInspection("S1", vessel)

        # Simulate define_dates_inspection returning one inspection row
        d_trigger = datetime(2020, 1, 10, 8, 0, 0)
        df_site = pd.DataFrame(
            [[d_trigger, d_trigger + timedelta(hours=1), "inspection_site", "S1", vessel.id]],
            columns=self.COLS,
        )
        mock_define_dates.return_value = df_site

        # Simulate create_mobilisation returning a single mobilisation row
        mob_row = pd.DataFrame(
            [[d_trigger, d_trigger + timedelta(days=1), "mobilisation", "mob_S1", vessel.id]],
            columns=self.COLS,
        )
        mock_create_mob.return_value = mob_row

        result = create_logs_preventive(
            COLS=self.COLS,
            inputs=self.inputs,
            inspections_port_stat=[],
            inspections_site_stat=[inspection],
            find_element_class=None,
            percentile=0.9,
            mother_vessels_list=[vessel],
        )

        # define_dates must be called once for the single site inspection
        mock_define_dates.assert_called_once()
        # create_mobilisation called once for the single row in df_site
        self.assertEqual(mock_create_mob.call_count, 1)

        # Result must contain inspection rows + mobilisation rows = 2
        self.assertEqual(len(result), 2)

        # Check that both inspection and mobilisation events are present
        events = set(result["event"].tolist())
        self.assertIn("inspection_site", events)
        self.assertIn("mobilisation", events)

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_preventive."
        "logs_timeseries_func.create_mobilisation"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_preventive."
        "define_dates_inspection.define_dates"
    )
    def test_site_inspection_without_mobilisation_does_not_call_create_mobilisation(
        self, mock_define_dates, mock_create_mob
    ):
        """
        If site inspection vessel has mobilisation_time == 0,
        mobilisation rows must not be created and create_mobilisation must not be called.
        """

        vessel = DummyVessel("CTV-2", mobilisation_time=0.0)
        inspection = DummyInspection("S2", vessel)

        d_trigger = datetime(2020, 1, 15, 9, 0, 0)
        df_site = pd.DataFrame(
            [[d_trigger, d_trigger + timedelta(hours=2), "inspection_site", "S2", vessel.id]],
            columns=self.COLS,
        )
        mock_define_dates.return_value = df_site

        result = create_logs_preventive(
            COLS=self.COLS,
            inputs=self.inputs,
            inspections_port_stat=[],
            inspections_site_stat=[inspection],
            find_element_class=None,
            percentile=0.9,
            mother_vessels_list=[vessel],
        )

        # One call to define_dates
        mock_define_dates.assert_called_once()
        # No call to create_mobilisation
        mock_create_mob.assert_not_called()

        # Result must contain only the inspection row
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["event"], "inspection_site")

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_preventive."
        "logs_timeseries_func.create_mobilisation"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_preventive."
        "define_dates_inspection.define_dates"
    )
    def test_port_inspection_sets_vessel_1_from_insp_class_and_adds_mobilisation(
        self, mock_define_dates, mock_create_mob
    ):
        """
        For port inspections:
        - vessel_1 in df_row_dates must be overwritten with insp.insp_class.vessel1.id
        - mobilisation rows are created when insp.insp_class.vessel1.mobilisation_time != 0.
        """

        vessel = DummyVessel("PORT-VES", mobilisation_time=12.0)
        inspection = DummyInspection("P1", vessel)

        d_trigger = datetime(2020, 2, 5, 7, 0, 0)
        # define_dates does not need to set vessel_1 correctly, function will override it.
        df_port = pd.DataFrame(
            [[d_trigger, d_trigger + timedelta(hours=3), "inspection_port", "P1", "WRONG"]],
            columns=self.COLS,
        )
        mock_define_dates.return_value = df_port

        mob_row = pd.DataFrame(
            [[d_trigger, d_trigger + timedelta(days=1), "mobilisation", "mob_P1", vessel.id]],
            columns=self.COLS,
        )
        mock_create_mob.return_value = mob_row

        result = create_logs_preventive(
            COLS=self.COLS,
            inputs=self.inputs,
            inspections_port_stat=[inspection],
            inspections_site_stat=[],
            find_element_class=None,
            percentile=0.9,
            mother_vessels_list=[vessel],
        )

        # One call to define_dates
        mock_define_dates.assert_called_once()
        # One call to create_mobilisation
        self.assertEqual(mock_create_mob.call_count, 1)

        # There should be 1 inspection row + 1 mobilisation row
        self.assertEqual(len(result), 2)

        # Filter inspection_port rows and verify vessel_1 has been overwritten correctly
        insp_rows = result[result["event"] == "inspection_port"]
        self.assertEqual(len(insp_rows), 1)
        self.assertEqual(insp_rows.iloc[0]["vessel_1"], vessel.id)

        # Mobilisation row should be present as well
        mob_rows = result[result["event"] == "mobilisation"]
        self.assertEqual(len(mob_rows), 1)

    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_preventive."
        "logs_timeseries_func.create_mobilisation"
    )
    @patch(
        "oriom.core.functions.logs_timeseries.create_logs_events_preventive."
        "define_dates_inspection.define_dates"
    )
    def test_port_inspection_without_mobilisation_time_skips_mobilisation(
        self, mock_define_dates, mock_create_mob
    ):
        """
        If insp.insp_class.vessel1.mobilisation_time == 0, no mobilisation rows should be added
        for port inspections.
        """

        vessel = DummyVessel("PORT-VES-2", mobilisation_time=0.0)
        inspection = DummyInspection("P2", vessel)

        d_trigger = datetime(2020, 3, 1, 10, 0, 0)
        df_port = pd.DataFrame(
            [[d_trigger, d_trigger + timedelta(hours=1), "inspection_port", "P2", "WRONG"]],
            columns=self.COLS,
        )
        mock_define_dates.return_value = df_port

        result = create_logs_preventive(
            COLS=self.COLS,
            inputs=self.inputs,
            inspections_port_stat=[inspection],
            inspections_site_stat=[],
            find_element_class=None,
            percentile=0.9,
            mother_vessels_list=[vessel],
        )

        mock_define_dates.assert_called_once()
        mock_create_mob.assert_not_called()

        # Only inspection_port row should be present
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["event"], "inspection_port")
        self.assertEqual(result.iloc[0]["vessel_1"], vessel.id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
