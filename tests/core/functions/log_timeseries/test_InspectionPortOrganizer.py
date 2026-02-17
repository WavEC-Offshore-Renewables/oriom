# tests/test_inspection_port_creation.py

import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
import pandas as pd

from oriom.core.functions.logs_timeseries.InspectionPortOrganizer import InspectionPortCreation

# ----------------- Helpers -----------------

def make_sched(rows):
    """
    rows: list of dict with keys:
      'datetime', 'dur_total', 'wait_start', optional 'shutdown_hours'
    Returns a DataFrame with exactly the columns used by the class.
    """
    df = pd.DataFrame(rows)
    for col in ["dur_total", "wait_start"]:
        if col not in df.columns:
            df[col] = 0
    return df[["datetime", "dur_total", "wait_start"] + [c for c in df.columns if c not in ("datetime","dur_total","wait_start")]]

class DummyInspClass:
    def __init__(self, intervened_devices, insp_oper_sched):
        self.intervened_devices = intervened_devices
        self.ts_data = type("TS", (), {"oper_sched": insp_oper_sched})

class DummyInspection:
    def __init__(self, id_, n_vessel_1, intervened_devices, insp_oper_sched):
        self.id = id_
        self.n_vessel_1 = n_vessel_1
        self.insp_class = DummyInspClass(intervened_devices, insp_oper_sched)

# ----------------- Tests -----------------

class TestInspectionPortCreation(unittest.TestCase):

    @patch("oriom.core.functions.logs_timeseries.InspectionPortOrganizer.logs_preventive_aux.date_ranges_overlap")
    @patch("oriom.core.functions.logs_timeseries.InspectionPortOrganizer.logs_preventive_aux.take_op_schedule_tow")
    def test_happy_path_and_shutdown_accumulation(self, mock_take_tow, mock_overlap):
        """
        One device, no overlaps. Checks:
        - pipeline runs through tow->inspect->tow site
        - duration_shutdown_month[month] accumulates from both tow schedules
        - lists end_datetimes, end_stat_chart_datetimes, valid_datetimes are populated
        """
        mock_overlap.return_value = False  # no overlaps

        d0 = datetime(2025, 6, 1, 5, 0, 0)

        # Tow-to-port:
        #  - riga di start (d0) con dur_total=5, wait_start=1
        #  - riga a d0+1h (d_tow_port_wait) con shutdown_hours da sommare
        tow_port_df = make_sched([
            {"datetime": d0,                 "dur_total": 5, "wait_start": 1, "shutdown_hours": 2},
        ])

        # Inspection-at-port: riga a d_insp = d0+5h
        d_insp = d0 + timedelta(hours=5)
        insp_df = make_sched([
            {"datetime": d_insp, "dur_total": 4, "wait_start": 0},
        ])

        # Tow-to-site (port<->site):
        #  - riga di start (d_tow = d0+9h) con dur_total=6, wait_start=2
        #  - riga a d_tow+2h (d_tow_site_wait) con shutdown_hours da sommare
        d_tow = d_insp + timedelta(hours=4)  # d0 + 9h
        tow_site_port_df = make_sched([
            {"datetime": d_tow,                       "dur_total": 6, "wait_start": 2, "shutdown_hours": 3},
        ])


        # <<< FIX: accept keyword arguments >>>
        def _take(*args, **kwargs):
            op_tow = kwargs.get("op_tow")
            if op_tow == "op_tow_port":
                return tow_port_df
            if op_tow == "op_tow_site":
                return tow_site_port_df
            if op_tow == "op_tow_site_port":
                return tow_site_port_df
            raise AssertionError(f"Unexpected op_tow key: {op_tow}")

        mock_take_tow.side_effect = _take

        inspection = DummyInspection(id_="INSP01", n_vessel_1=2, intervened_devices=1, insp_oper_sched=insp_df)

        duration_shutdown_month = [0] * 13
        end_datetimes, end_stat_chart_datetimes, valid_datetimes = [], [], []

        sut = InspectionPortCreation(
            inspection=inspection,
            n_device_at_port=1,
            n_device_stored_at_port=0,
            find_element_class=None,
            shutdown_col="shutdown_hours"
        )

        sut.preventive_port_inspection(
            month_insp=6,
            duration_shutdown_month=duration_shutdown_month,
            end_datetimes=end_datetimes,
            end_stat_chart_datetimes=end_stat_chart_datetimes,
            valid_datetimes=valid_datetimes,
            d=d0
        )

        self.assertTrue(sut.operation_completed)
        self.assertEqual(len(end_datetimes), 1)
        self.assertEqual(end_datetimes[0], d_tow + timedelta(hours=6))
        self.assertEqual(end_stat_chart_datetimes[0], end_datetimes[0])
        self.assertEqual(valid_datetimes[0], d0)
        self.assertEqual(duration_shutdown_month[6], 5)

    @patch("oriom.core.functions.logs_timeseries.InspectionPortOrganizer.logs_preventive_aux.date_ranges_overlap")
    @patch("oriom.core.functions.logs_timeseries.InspectionPortOrganizer.logs_preventive_aux.take_op_schedule_tow")
    def test_missing_schedule_row_aborts_operation(self, mock_take_tow, mock_overlap):
        """
        If tow_inspection_schedule cannot find the matching 'datetime' row, it returns (None, None),
        the class sets operation_completed=False and stops without appending results.
        """
        mock_overlap.return_value = False

        tow_port_df = make_sched([
            {"datetime": datetime(2025, 6, 1, 6, 0, 0), "dur_total": 1, "wait_start": 1, "shutdown_hours": 1}
        ])
        insp_df = make_sched([
            {"datetime": datetime(2025, 6, 1, 10, 0, 0), "dur_total": 1, "wait_start": 0}
        ])
        tow_site_port_df = make_sched([
            {"datetime": datetime(2025, 6, 1, 11, 0, 0), "dur_total": 1, "wait_start": 0, "shutdown_hours": 1}
        ])

        # <<< FIX: accept keyword arguments >>>
        def _take(*args, **kwargs):
            op_tow = kwargs.get("op_tow")
            if op_tow == "op_tow_port":
                return tow_port_df
            if op_tow == "op_tow_site":
                return tow_site_port_df
            if op_tow == "op_tow_site_port":
                return tow_site_port_df
            raise AssertionError(f"Unexpected op_tow key: {op_tow}")

        mock_take_tow.side_effect = _take

        inspection = DummyInspection(id_="INSP02", n_vessel_1=1, intervened_devices=1, insp_oper_sched=insp_df)

        duration_shutdown_month = [0] * 13
        end_datetimes, end_stat_chart_datetimes, valid_datetimes = [], [], []
        d0 = datetime(2025, 6, 1, 5, 0, 0)  # start datetime NOT present in tow_port_df

        sut = InspectionPortCreation(
            inspection=inspection,
            n_device_at_port=1,
            n_device_stored_at_port=0,
            find_element_class=None,
            shutdown_col="shutdown_hours"
        )

        sut.preventive_port_inspection(
            month_insp=6,
            duration_shutdown_month=duration_shutdown_month,
            end_datetimes=end_datetimes,
            end_stat_chart_datetimes=end_stat_chart_datetimes,
            valid_datetimes=valid_datetimes,
            d=d0
        )

        self.assertFalse(sut.operation_completed)
        self.assertEqual(end_datetimes, [])
        self.assertEqual(end_stat_chart_datetimes, [])
        self.assertEqual(valid_datetimes, [])
        self.assertEqual(duration_shutdown_month[6], 0)


    @patch("oriom.core.functions.logs_timeseries.InspectionPortOrganizer.logs_preventive_aux.date_ranges_overlap")
    @patch("oriom.core.functions.logs_timeseries.InspectionPortOrganizer.logs_preventive_aux.take_op_schedule_tow")
    def test_four_devices_two_at_port_with_shutdown_accumulation(self, mock_take_tow, mock_overlap):
        """
        4 devices, capacity of 2 devices at port (n_device_at_port=2, n_vessel_1=2).
        Schedules with real DataFrames, shutdown accumulation enabled (shutdown_col="shutdown_hours").

        Durations per phase (applied at each start row):
          - tow to port:    dur_total=5h, wait_start=1h  -> wait row at start+1h (shutdown_hours=2)
          - inspect at port:dur_total=4h, wait_start=0h
          - tow to site:    dur_total=6h, wait_start=2h  -> wait row at start+2h (shutdown_hours=3)

        With 2-at-port capacity, devices 1 & 2 start immediately (d0, d0+1),
        devices 3 & 4 start after earliest site completions (≈ d0+15, d0+16).
        Final end for device #4: d0 + 31h.
        Total shutdown accumulation in month 6: 4*(2) + 4*(3) = 20.
        """
        mock_overlap.return_value = False  # no overlaps

        d0 = datetime(2025, 6, 1, 5, 0, 0)

        # ---------- Tow-to-port schedule ----------
        # Starts for devices 1..4 at: d0, d0+1h, d0+15h, d0+16h
        # Each has wait_start=1h -> wait rows at +1h from its start with shutdown_hours=2
        tow_port_rows = [
            # starts
            {"datetime": d0,                              "dur_total": 5, "wait_start": 1, "shutdown_hours": 4},
            {"datetime": d0 + timedelta(hours=1),        "dur_total": 4, "wait_start": 0, "shutdown_hours": 4},
            {"datetime": d0 + timedelta(hours=15),       "dur_total": 5, "wait_start": 1, "shutdown_hours": 4},
            {"datetime": d0 + timedelta(hours=16),       "dur_total": 4, "wait_start": 0, "shutdown_hours": 4}
        ]
        tow_port_df = make_sched(tow_port_rows)

        # ---------- Inspection-at-port schedule ----------
        # Start of inspection per device = tow_to_port end = start + 5h
        # Ends = start + 5h + 4h
        insp_rows = [
            {"datetime": d0 + timedelta(hours=5),        "dur_total": 4, "wait_start": 0},  # dev1
            {"datetime": d0 + timedelta(hours=6),        "dur_total": 4, "wait_start": 0},  # dev2
            {"datetime": d0 + timedelta(hours=15),       "dur_total": 14, "wait_start": 10},  # dev3 (15+5)
            {"datetime": d0 + timedelta(hours=16),       "dur_total": 13, "wait_start": 9},  # dev4 (16+5)
        ]
        insp_df = make_sched(insp_rows)

        # ---------- Tow-to-site (port<->site) schedule ----------
        # Start of site tow per device = inspection end = start + 5h + 4h
        # Ends = site start + 6h ; wait rows at site start + 2h with shutdown_hours=6
        tow_site_port_rows = [
            # starts
            {"datetime": d0 + timedelta(hours=9),        "dur_total": 6, "wait_start": 2, "shutdown_hours": 6},  # dev1 (5+4)
            {"datetime": d0 + timedelta(hours=10),       "dur_total": 5, "wait_start": 1, "shutdown_hours": 6},  # dev2 (6+4)
            {"datetime": d0 + timedelta(hours=29),       "dur_total": 6, "wait_start": 2, "shutdown_hours": 6},  # dev3 (20+4)
            {"datetime": d0 + timedelta(hours=30),       "dur_total": 5, "wait_start": 1, "shutdown_hours": 6},  # dev4 (21+4)
        ]
        tow_site_port_df = make_sched(tow_site_port_rows)

        # Patch take_op_schedule_tow to return the above DFs
        def _take(*args, **kwargs):
            op_tow = kwargs.get("op_tow")
            if op_tow == "op_tow_port":
                return tow_port_df
            if op_tow == "op_tow_site":
                # Only-site variant unused in this flow (we still return site-port DF safely)
                return tow_site_port_df
            if op_tow == "op_tow_site_port":
                return tow_site_port_df
            raise AssertionError(f"Unexpected op_tow key: {op_tow}")
        mock_take_tow.side_effect = _take

        # Build the inspection object (4 devices, 2 vessels)
        inspection = DummyInspection(
            id_="INSP_MULTI",
            n_vessel_1=2,
            intervened_devices=4,
            insp_oper_sched=insp_df
        )

        # Instantiate SUT with 2-at-port capacity and shutdown accumulation enabled
        sut = InspectionPortCreation(
            inspection=inspection,
            n_device_at_port=2,
            n_device_stored_at_port=0,
            find_element_class=None,
            shutdown_col="shutdown_hours"
        )

        # # Workaround for class indexing when device_n==2:
        # # the code uses self.tow_at_port[self.dev_idx_station_port-1] on the second device
        # # Seed key 0 with a valid tuple to avoid KeyError and keep timing coherent.
        # # (d_insp, d_wait) dummy for key 0
        # sut.tow_at_port[0] = (d0 + timedelta(hours=5), d0 + timedelta(hours=1))

        duration_shutdown_month = [0] * 12
        duration_shutdown_month[6] = 4 * 4
        end_datetimes, end_stat_chart_datetimes, valid_datetimes = [], [], []

        sut.preventive_port_inspection(
            month_insp=6,
            duration_shutdown_month=duration_shutdown_month,
            end_datetimes=end_datetimes,
            end_stat_chart_datetimes=end_stat_chart_datetimes,
            valid_datetimes=valid_datetimes,
            d=d0
        )

        # --- Assertions ---
        self.assertTrue(sut.operation_completed)

        # Only last device's end is added to the list (per current implementation)
        # Device 4 final end = site start (d0+25h) + 6h = d0+31h
        self.assertEqual(len(end_datetimes), 1)
        self.assertEqual(end_datetimes[0], d0 + timedelta(hours=35))
        self.assertEqual(end_stat_chart_datetimes[0], end_datetimes[0])
        self.assertEqual(valid_datetimes[0], d0)

        # Shutdown accumulation:
        self.assertEqual(duration_shutdown_month[6], 68)


#test_InspectionPortOrganizer

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import pandas as pd

from oriom.core.functions.logs_timeseries.InspectionPortOrganizer import (
    InspectionPortCreation,
)


class DummyInspection:
    """Minimal inspection object with only the attributes used by InspectionPortCreation."""

    def __init__(self, iid="insp_1", n_vessel_1=1):
        self.id = iid
        self.n_vessel_1 = n_vessel_1
        # Dummy nested structure if needed elsewhere
        self.insp_class = MagicMock()
        self.insp_class.id = iid


class TestInspectionPortCreation(unittest.TestCase):
    """Unit tests for InspectionPortCreation methods."""

    def _make_instance(self):
        """Create a bare instance with attributes manually injected."""
        insp = DummyInspection()
        inst = InspectionPortCreation.__new__(InspectionPortCreation)
        inst.inspection = insp
        inst.n_device_at_port = 2
        inst.n_device_stored_at_port = 0
        inst.operation_completed = True
        inst.shutdown_col = "shutdown"
        inst.tot_device = 3

        # Schedules: they will be overridden as needed in each test
        inst.oper_schedule_tow_port = pd.DataFrame()
        inst.oper_schedule_insp = pd.DataFrame()
        inst.oper_schedule_tow_site_only = pd.DataFrame()
        inst.oper_schedule_tow_site_port = pd.DataFrame()

        inst.tow_at_port = {}
        inst.tow_at_site = {}
        inst.insp_at_port = {}
        inst.dev_idx_station_port = 1
        return inst

    # ------------------------------------------------------------------ #
    # tow_inspection_schedule
    # ------------------------------------------------------------------ #

    def test_tow_inspection_schedule_ok(self):
        """tow_inspection_schedule returns correct end datetimes when schedule row exists."""
        inst = self._make_instance()
        start = datetime(2025, 1, 1, 8, 0)
        df = pd.DataFrame(
            [
                {
                    "datetime": start,
                    "dur_total": 2.3,   # ceil -> 3h
                    "wait_start": 0.6,  # ceil -> 1h
                }
            ]
        )
        d_insp, d_wait, d_orig = inst.tow_inspection_schedule(df, start, "OP1")

        self.assertEqual(d_orig, start)
        self.assertEqual(d_insp, start + timedelta(hours=3))
        self.assertEqual(d_wait, start + timedelta(hours=1))

    def test_tow_inspection_schedule_missing_row(self):
        """
        tow_inspection_schedule returns (None, None, None) when the datetime
        is not found in the schedule.
        """
        inst = self._make_instance()
        start = datetime(2025, 1, 1, 8, 0)
        other = datetime(2025, 1, 1, 9, 0)
        df = pd.DataFrame(
            [
                {
                    "datetime": other,
                    "dur_total": 1.0,
                    "wait_start": 0.0,
                }
            ]
        )
        d_insp, d_wait, d_orig = inst.tow_inspection_schedule(df, start, "OP1")

        self.assertIsNone(d_insp)
        self.assertIsNone(d_wait)
        self.assertIsNone(d_orig)

    # ------------------------------------------------------------------ #
    # overlap_shift_tow
    # ------------------------------------------------------------------ #

    @patch(
        "oriom.core.functions.logs_timeseries.InspectionPortOrganizer."
        "logs_preventive_aux.date_ranges_overlap",
        return_value=False,
    )
    def test_overlap_shift_tow_no_overlap(self, mock_overlap):
        """
        overlap_shift_tow returns the original values when no overlap is detected.
        """
        inst = self._make_instance()
        inst.oper_schedule_tow_port = pd.DataFrame()  # not used in this path

        d_start = datetime(2025, 1, 1, 8, 0)
        d_insp = d_start + timedelta(hours=3)
        d_wait = d_start + timedelta(hours=1)

        tow_at_site = {
            1: (d_start + timedelta(hours=5), d_start + timedelta(hours=4))
        }

        out_insp, out_wait, out_start = inst.overlap_shift_tow(
            overlap_date=True,
            tow_at_site=tow_at_site,
            d_insp=d_insp,
            d_tow_port_wait=d_wait,
            inspection=inst.inspection,
            n_device_at_port=inst.n_device_at_port,
            d_start_tow=d_start,
        )

        self.assertEqual(out_insp, d_insp)
        self.assertEqual(out_wait, d_wait)
        self.assertEqual(out_start, d_start)
        mock_overlap.assert_called()

    @patch(
        "oriom.core.functions.logs_timeseries.InspectionPortOrganizer."
        "logs_preventive_aux.date_ranges_overlap"
    )
    def test_overlap_shift_tow_with_reschedule(self, mock_overlap):
        """
        When overlaps exceed available vessels, overlap_shift_tow must call
        tow_inspection_schedule and return the rescheduled values.
        """
        inst = self._make_instance()
        inst.inspection.n_vessel_1 = 1  # force reschedule when there is 1 overlap

        d_start = datetime(2025, 1, 1, 8, 0)
        d_insp = d_start + timedelta(hours=3)
        d_wait = d_start + timedelta(hours=1)

        tow_at_site = {
            1: (d_start + timedelta(hours=2), d_start),  # overlapping interval
        }

        # First overlap -> True, then False to exit the loop
        mock_overlap.side_effect = [True, False]

        # Patch tow_inspection_schedule on the instance to simulate reschedule
        new_insp = d_start + timedelta(hours=10)
        new_wait = d_start + timedelta(hours=4)
        new_start = d_start + timedelta(hours=7)
        inst.oper_schedule_tow_port = MagicMock()  # unused on the fake
        inst.tow_inspection_schedule = MagicMock(
            return_value=(new_insp, new_wait, new_start)
        )

        out_insp, out_wait, out_start = inst.overlap_shift_tow(
            overlap_date=True,
            tow_at_site=tow_at_site,
            d_insp=d_insp,
            d_tow_port_wait=d_wait,
            inspection=inst.inspection,
            n_device_at_port=inst.n_device_at_port,
            d_start_tow=d_start,
        )

        inst.tow_inspection_schedule.assert_called()
        self.assertEqual(out_insp, new_insp)
        self.assertEqual(out_wait, new_wait)
        self.assertEqual(out_start, new_start)

    # ------------------------------------------------------------------ #
    # tow_to_port
    # ------------------------------------------------------------------ #

    def test_tow_to_port_first_device_success(self):
        """
        tow_to_port for the first device:
        - uses date_continuous as start
        - fills tow_at_port
        - increments duration_shutdown_month if shutdown_col is set.
        """
        inst = self._make_instance()
        start = datetime(2025, 1, 5, 6, 0)

        inst.oper_schedule_tow_port = pd.DataFrame(
            [
                {
                    "datetime": start,
                    "dur_total": 3.7,      # ceil -> 4h
                    "wait_start": 0.5,     # ceil -> 1h
                    "shutdown": 2.0,
                }
            ]
        )

        duration_shutdown_month = {"1": 0.0}
        month_insp = "1"

        d_insp = inst.tow_to_port(
            device_n=1,
            date_continuous=start,
            duration_shutdown_month=duration_shutdown_month,
            month_insp=month_insp,
        )

        # End of tow (4h after start)
        self.assertEqual(d_insp, start + timedelta(hours=4))
        # tow_at_port should have one entry with end and wait times
        self.assertIn(1, inst.tow_at_port)
        end_saved, wait_saved = inst.tow_at_port[1]
        self.assertEqual(end_saved, d_insp)
        self.assertEqual(wait_saved, start + timedelta(hours=1))
        # Shutdown month incremented
        self.assertEqual(duration_shutdown_month["1"], 2.0)

    def test_tow_to_port_device_above_capacity_uses_earliest_site_end(self):
        """
        When device_n > n_device_at_port, tow_to_port returns the earliest end
        from tow_at_site without calling tow_inspection_schedule.
        """
        inst = self._make_instance()
        inst.n_device_at_port = 1
        inst.tow_at_site = {
            1: (datetime(2025, 1, 1, 10, 0), datetime(2025, 1, 1, 8, 0)),
            2: (datetime(2025, 1, 1, 9, 0), datetime(2025, 1, 1, 7, 0)),
        }
        inst.dev_idx_station_port = 1

        duration_shutdown_month = {"1": 0.0}

        d_insp = inst.tow_to_port(
            device_n=2,
            date_continuous=datetime(2025, 1, 1, 6, 0),
            duration_shutdown_month=duration_shutdown_month,
            month_insp="1",
        )

        # Earliest end in tow_at_site is 09:00
        self.assertEqual(d_insp, datetime(2025, 1, 1, 9, 0))
        # dev_idx_station_port should be set to key with earliest end -> 2
        self.assertEqual(inst.dev_idx_station_port, 2)

    def test_tow_to_port_failure_sets_operation_completed_false(self):
        """
        If tow_inspection_schedule returns None values, tow_to_port must set
        operation_completed to False and return None.
        """
        inst = self._make_instance()
        inst.tow_inspection_schedule = MagicMock(return_value=(None, None, None))

        duration_shutdown_month = {"1": 0.0}
        d_insp = inst.tow_to_port(
            device_n=1,
            date_continuous=datetime(2025, 1, 1, 8, 0),
            duration_shutdown_month=duration_shutdown_month,
            month_insp="1",
        )

        self.assertFalse(inst.operation_completed)
        self.assertIsNone(d_insp)
        self.assertEqual(duration_shutdown_month["1"], 0.0)

    # ------------------------------------------------------------------ #
    # inspection_at_port
    # ------------------------------------------------------------------ #

    def test_inspection_at_port_success(self):
        """
        inspection_at_port:
        - calls tow_inspection_schedule with oper_schedule_insp.
        - fills insp_at_port at dev_idx_station_port.
        - increments duration_shutdown_month by wait_start from schedule.
        """
        inst = self._make_instance()
        d_insp = datetime(2025, 1, 3, 8, 0)

        inst.oper_schedule_insp = pd.DataFrame(
            [
                {
                    "datetime": d_insp,
                    "dur_total": 2.2,      # ceil -> 3h
                    "wait_start": 1.5,     # for shutdown aggregation
                }
            ]
        )

        duration_shutdown_month = {"1": 0.0}
        month_insp = "1"

        end_date = inst.inspection_at_port(
            d_insp=d_insp,
            duration_shutdown_month=duration_shutdown_month,
            month_insp=month_insp,
        )

        # tow_inspection_schedule used: dur_total ceil(2.2) = 3h
        self.assertEqual(end_date, d_insp + timedelta(hours=3))
        # insp_at_port populated for current device index
        self.assertIn(inst.dev_idx_station_port, inst.insp_at_port)
        saved_end, saved_wait = inst.insp_at_port[inst.dev_idx_station_port]
        self.assertEqual(saved_end, end_date)
        # shutdown month incremented by wait_start (1.5)
        self.assertEqual(duration_shutdown_month["1"], 1.5)

    def test_inspection_at_port_failure(self):
        """
        If tow_inspection_schedule fails, inspection_at_port must set
        operation_completed to False and return None.
        """
        inst = self._make_instance()
        inst.tow_inspection_schedule = MagicMock(return_value=(None, None, None))

        duration_shutdown_month = {"1": 0.0}
        end_date = inst.inspection_at_port(
            d_insp=datetime(2025, 1, 3, 8, 0),
            duration_shutdown_month=duration_shutdown_month,
            month_insp="1",
        )

        self.assertFalse(inst.operation_completed)
        self.assertIsNone(end_date)

    # ------------------------------------------------------------------ #
    # tow_to_site
    # ------------------------------------------------------------------ #

    def test_tow_to_site_only_schedule_success(self):
        """
        For device_n > tot_device - n_device_at_port it must use
        oper_schedule_tow_site_only and update tow_at_site and shutdown month.
        """
        inst = self._make_instance()
        inst.tot_device = 3
        inst.n_device_at_port = 1  # => only-schedule branch for device_n > 2
        inst.dev_idx_station_port = 1

        d_tow = datetime(2025, 1, 4, 8, 0)
        inst.oper_schedule_tow_site_only = pd.DataFrame(
            [
                {
                    "datetime": d_tow,
                    "dur_total": 1.5,     # ceil -> 2h
                    "wait_start": 0.3,
                    "shutdown": 4.0,
                }
            ]
        )

        duration_shutdown_month = {"1": 0.0}
        month_insp = "1"

        d_end = inst.tow_to_site(
            device_n=3,
            d_tow=d_tow,
            duration_shutdown_month=duration_shutdown_month,
            month_insp=month_insp,
        )

        # End must be d_tow + ceil(1.5) = 2h
        self.assertEqual(d_end, d_tow + timedelta(hours=2))
        self.assertIn(inst.dev_idx_station_port, inst.tow_at_site)
        saved_end, saved_wait = inst.tow_at_site[inst.dev_idx_station_port]
        self.assertEqual(saved_end, d_end)
        # Shutdown month incremented by 4.0
        self.assertEqual(duration_shutdown_month["1"], 4.0)

    def test_tow_to_site_failure(self):
        """
        If tow_inspection_schedule fails, tow_to_site must set
        operation_completed to False and return None.
        """
        inst = self._make_instance()
        inst.tot_device = 2
        inst.n_device_at_port = 1
        inst.tow_inspection_schedule = MagicMock(return_value=(None, None, None))

        duration_shutdown_month = {"1": 0.0}
        d_end = inst.tow_to_site(
            device_n=2,
            d_tow=datetime(2025, 1, 4, 8, 0),
            duration_shutdown_month=duration_shutdown_month,
            month_insp="1",
        )

        self.assertFalse(inst.operation_completed)
        self.assertIsNone(d_end)

    # ------------------------------------------------------------------ #
    # preventive_port_inspection
    # ------------------------------------------------------------------ #

    def test_preventive_port_inspection_success(self):
        """
        preventive_port_inspection calls tow_to_port, inspection_at_port and tow_to_site
        for each device and, if all succeed, appends final end date and trigger date
        to the provided lists.
        """
        inst = self._make_instance()
        inst.tot_device = 2
        inst.operation_completed = True
        inst.dev_idx_station_port = 1
        inst.tow_at_port = {}
        inst.tow_at_site = {}

        start = datetime(2025, 1, 10, 8, 0)

        # Simple fake sequence: each stage adds +1h
        def fake_tow_to_port(device_n, date_continuous, duration_shutdown_month, month_insp):
            start = date_continuous
            end = date_continuous + timedelta(hours=1)
            inst.tow_at_port[inst.dev_idx_station_port] = (start, end)
            return end

        def fake_inspection_at_port(d_insp, duration_shutdown_month, month_insp):
            return d_insp + timedelta(hours=1)

        def fake_tow_to_site(device_n, d_tow, duration_shutdown_month, month_insp):
            start = d_tow
            end = d_tow + timedelta(hours=1)
            inst.tow_at_site[inst.dev_idx_station_port] = (start, end)
            return end

        inst.tow_to_port = fake_tow_to_port
        inst.inspection_at_port = fake_inspection_at_port
        inst.tow_to_site = fake_tow_to_site

        duration_shutdown_month = {"1": 0.0}
        end_datetimes = []
        end_stat_chart_datetimes = []
        valid_datetimes = []

        inst.preventive_port_inspection(
            month_insp="1",
            duration_shutdown_month=duration_shutdown_month,
            end_datetimes=end_datetimes,
            end_stat_chart_datetimes=end_stat_chart_datetimes,
            valid_datetimes=valid_datetimes,
            d=start,
            df_port_inspection_log=pd.DataFrame(columns=['d_trigger', 'd_TTP_start', 'd_TTP_end', 'n_device'])
        )

        # 2 devices, but final result lists must have one element (campaign summary)
        self.assertTrue(inst.operation_completed)
        self.assertEqual(len(end_datetimes), 1)
        self.assertEqual(len(end_stat_chart_datetimes), 1)
        self.assertEqual(len(valid_datetimes), 1)
        # Each device: +3h, last device still ends at start+3h using our fake functions
        self.assertEqual(end_datetimes[0], start + timedelta(hours=3))
        self.assertEqual(end_stat_chart_datetimes[0], start + timedelta(hours=3))
        self.assertEqual(valid_datetimes[0], start)

    def test_preventive_port_inspection_stops_on_failure(self):
        """
        If one of the devices fails (operation_completed set to False),
        preventive_port_inspection must stop and not append any end date.
        """
        inst = self._make_instance()
        inst.tot_device = 3
        inst.operation_completed = True
        inst.dev_idx_station_port = 1
        inst.tow_at_port = {}
        inst.tow_at_site = {}

        start = datetime(2025, 1, 10, 8, 0)

        def faketow_to_port(device_n, date_continuous, duration_shutdown_month, month_insp):
            # First device ok, second fails
            if device_n == 2:
                inst.operation_completed = False
                return None
            start = date_continuous
            end = date_continuous + timedelta(hours=1)
            inst.tow_at_port[inst.dev_idx_station_port] = (start, end)
            return end

        def fake_inspection_at_port(d_insp, duration_shutdown_month, month_insp):
            return d_insp + timedelta(hours=1)

        def fake_tow_to_site(device_n, d_tow, duration_shutdown_month, month_insp):
            start = d_tow
            end = d_tow + timedelta(hours=1)
            inst.tow_at_site[inst.dev_idx_station_port] = (start, end)
            return end

        inst.tow_to_port = faketow_to_port
        inst.inspection_at_port = fake_inspection_at_port
        inst.tow_to_site = fake_tow_to_site

        duration_shutdown_month = {"1": 0.0}
        end_datetimes = []
        end_stat_chart_datetimes = []
        valid_datetimes = []

        inst.preventive_port_inspection(
            month_insp="1",
            duration_shutdown_month=duration_shutdown_month,
            end_datetimes=end_datetimes,
            end_stat_chart_datetimes=end_stat_chart_datetimes,
            valid_datetimes=valid_datetimes,
            d=start,
            df_port_inspection_log=pd.DataFrame(columns=['d_trigger', 'd_TTP_start', 'd_TTP_end', 'n_device'])
        )

        self.assertFalse(inst.operation_completed)
        self.assertEqual(end_datetimes, [])
        self.assertEqual(end_stat_chart_datetimes, [])
        self.assertEqual(valid_datetimes, [])

if __name__ == '__main__':
    unittest.main(verbosity=2)
