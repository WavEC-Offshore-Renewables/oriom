import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd

import logistic_tools.core.functions.logs_timeseries.define_dates_inspection as define_dates


class DummyInspClass:
    def __init__(
        self,
        n_device_at_port=0,
        n_device_stored_at_port=0,
        duration_main=0,
        days_main=0,
        days_last=0,
        op_tow_port=False,
        vessel1_id="V1",
        vessel2_id=None,
        n_vessel_main=1,
        n_vessel_last=1,
        insp_port_dir=None,
    ):
        self.n_device_at_port = n_device_at_port
        self.n_device_stored_at_port = n_device_stored_at_port
        self.duration_main = duration_main
        self.days_main = days_main
        self.days_last = days_last
        self.op_tow_port = op_tow_port
        self.vessel1_id = vessel1_id
        self.vessel2_id = vessel2_id
        self.n_vessel_main = n_vessel_main
        self.n_vessel_last = n_vessel_last
        self.insp_port_dir = insp_port_dir


class DummyInspection:
    def __init__(
        self,
        insp_id,
        insp_class: DummyInspClass,
        n_vessel_1=1,
        shutdown_dict=None,
    ):
        self.id = insp_id
        self.insp_class = insp_class
        self.n_vessel_1 = n_vessel_1
        # shutdown_dict is updated at the end of define_dates for port inspections
        self.shutdown_dict = shutdown_dict if shutdown_dict is not None else {}


class TestDefineDatesBasic(unittest.TestCase):
    def setUp(self):
        # Minimal set of columns that will be used for the resulting dataframe
        self.COLS = [
            "d_trigger",
            "d_end_wait_start",
            "d_end_dur_net_port",
            "d_end_transit_ts",
            "d_end_wait_site",
            "d_end_dur_net_site",
            "d_end_transit_tp",
            "d_end",
            "d_end_stat_chart",
            "event",
            "id",
            "vessel_1",
            "n_vessel_1",
            "vessel_2",
            "n_vessel_2",
            "comments",
        ]

    @patch(
        "logistic_tools.core.functions.logs_timeseries.define_dates_inspection.aux_functions.safe_getattr"
    )
    def test_returns_empty_when_no_days(self, m_safe_getattr):
        """
        If max(days_main, days_last) == 0 the function must return an empty
        inspection dataframe.
        """
        insp_class = DummyInspClass(days_main=0, days_last=0)
        inspection = DummyInspection("ofw_insp_001", insp_class)

        # safe_getattr should return the actual attributes from insp_class
        def _safe(obj, attrs, default=None):
            cur = obj
            for a in attrs:
                cur = getattr(cur, a, default)
            return cur

        m_safe_getattr.side_effect = _safe

        df = define_dates.define_dates(
            COLS=self.COLS,
            inspection=inspection,
            event="inspection_site",
            start_year=2025,
            start_month=1,
            n_lifetime=1,
            percentile=90,
            find_element_class=MagicMock(),
        )

        self.assertTrue(df.empty)


class TestDefineDatesPortInspection(unittest.TestCase):
    def setUp(self):
        self.COLS = [
            "d_trigger",
            "d_end_wait_start",
            "d_end_dur_net_port",
            "d_end_transit_ts",
            "d_end_wait_site",
            "d_end_dur_net_site",
            "d_end_transit_tp",
            "d_end",
            "d_end_stat_chart",
            "event",
            "id",
            "vessel_1",
            "n_vessel_1",
            "vessel_2",
            "n_vessel_2",
            "comments",
        ]

    @patch(
        "logistic_tools.core.functions.logs_timeseries.define_dates_inspection.aux_functions.save_file_csv"
    )
    @patch(
        "logistic_tools.core.functions.logs_timeseries.define_dates_inspection.aux_functions.log_event_convert_stringtime",
        side_effect=lambda df: df,
    )
    @patch(
        "logistic_tools.core.functions.logs_timeseries.define_dates_inspection.logs_timeseries_func.create_stat_chart_inspection_port",
        side_effect=lambda df, p: df,
    )
    @patch(
        "logistic_tools.core.functions.logs_timeseries.define_dates_inspection.logs_preventive_aux.start_date_inspection"
    )
    @patch(
        "logistic_tools.core.functions.logs_timeseries.define_dates_inspection.InspectionPortCreation"
    )
    @patch(
        "logistic_tools.core.functions.logs_timeseries.define_dates_inspection.aux_functions.safe_getattr"
    )
    def test_port_inspection_updates_shutdown_dict_and_towing_log(
        self,
        m_safe_getattr,
        m_port_creation,
        m_start_dates,
        _m_create_chart,
        _m_log_convert,
        m_save_csv,
    ):
        """
        Port inspection branch:
        - uses InspectionPortCreation.preventive_port_inspection
        - on last iteration sets inspection.insp_class.towing_log
        - calls save_file_csv for towing_log
        - updates inspection.shutdown_dict when shutdown_col is not None
        """
        # Two inspection dates in June
        d1 = datetime(2025, 6, 1, 8, 0, 0)
        d2 = datetime(2025, 6, 15, 8, 0, 0)
        m_start_dates.return_value = [d1, d2]

        # Dummy inspection with port inspection enabled, 3 vessels but max 2 at port
        insp_class = DummyInspClass(
            n_device_at_port=2,
            n_device_stored_at_port=0,
            duration_main=8,
            days_main=1,
            days_last=0,
            op_tow_port=True,
            vessel1_id="V_MAIN",
            vessel2_id="V_AUX",
            insp_port_dir="/tmp",
        )
        inspection = DummyInspection(
            "ofw_insp_001", insp_class, n_vessel_1=3, shutdown_dict={"6": 1.0}
        )

        # safe_getattr: just follow attribute chain
        def _safe(obj, attrs, default=None):
            cur = obj
            for a in attrs:
                cur = getattr(cur, a, default)
            return cur

        m_safe_getattr.side_effect = _safe

        # Mock InspectionPortCreation instance
        dummy_port_instance = MagicMock()
        # Mark operation as completed so loop continues through all dates
        dummy_port_instance.operation_completed = True

        def _preventive_port_inspection(
            month_insp,
            duration_shutdown_month,
            end_datetimes,
            end_stat_chart_datetimes,
            valid_datetimes,
            d,
            df_port_inspection_log,
        ):
            # Simulate that towing/inspection takes 4 hours in that month
            duration_shutdown_month[month_insp] += 4.0
            # Simulate logging one interval per datetime
            valid_datetimes.append(d)
            end_dt = d + timedelta(hours=4)
            end_datetimes.append(end_dt)
            end_stat_chart_datetimes.append(end_dt)
            # Append a dummy row to towing log
            new_row = pd.DataFrame(
                [[d, d, end_dt, 1]],
                columns=["d_trigger", "d_TTP_start", "d_TTP_end", "n_device"],
            )
            return pd.concat([df_port_inspection_log, new_row], ignore_index=True)

        dummy_port_instance.preventive_port_inspection.side_effect = (
            _preventive_port_inspection
        )
        m_port_creation.return_value = dummy_port_instance

        df = define_dates.define_dates(
            COLS=self.COLS,
            inspection=inspection,
            event="inspection_port",
            start_year=2025,
            start_month=6,
            n_lifetime=1,
            percentile=90,
            find_element_class=MagicMock(),
        )

        # We expect two valid dates (one per datetime returned by start_date_inspection)
        self.assertEqual(len(df), 2)
        self.assertListEqual(df["d_trigger"].tolist(), [d1, d2])
        self.assertEqual(df["event"].iloc[0], "inspection_port")
        self.assertEqual(df["id"].iloc[0], inspection.id)
        # vessel1_id and vessel2_id propagated
        self.assertEqual(df["vessel_1"].iloc[0], "V_MAIN")
        self.assertEqual(df["vessel_2"].iloc[0], "V_AUX")
        # n_vessel_1 limited by n_device_at_port -> min(3, 2) = 2
        self.assertEqual(df["n_vessel_1"].iloc[0], 2)
        # Since vessel2_id is not None, n_vessel_2 must be 1
        self.assertEqual(df["n_vessel_2"].iloc[0], 1)

        # Towing log should be set on insp_class
        self.assertTrue(hasattr(inspection.insp_class, "towing_log"))
        self.assertIsInstance(inspection.insp_class.towing_log, pd.DataFrame)
        self.assertEqual(len(inspection.insp_class.towing_log), 2)

        # save_file_csv must be called once with the towing log
        self.assertEqual(m_save_csv.call_count, 1)

        # Check shutdown_dict update:
        # We added 4h in June for each of 2 inspections -> total 8
        # The function divides by the number of occurrences in that month (2) -> 4
        # Then adds to existing shutdown_dict["6"] = 1.0 -> expected 5.0
        self.assertIn("6", inspection.shutdown_dict)
        self.assertAlmostEqual(inspection.shutdown_dict["6"], 5.0, places=7)


class TestDefineDatesSiteInspection(unittest.TestCase):
    def setUp(self):
        self.COLS = [
            "d_trigger",
            "d_end_wait_start",
            "d_end_dur_net_port",
            "d_end_transit_ts",
            "d_end_wait_site",
            "d_end_dur_net_site",
            "d_end_transit_tp",
            "d_end",
            "d_end_stat_chart",
            "event",
            "id",
            "vessel_1",
            "n_vessel_1",
            "vessel_2",
            "n_vessel_2",
            "comments",
        ]

    @patch(
        "logistic_tools.core.functions.logs_timeseries.define_dates_inspection.logs_timeseries_func.create_stat_chart_inspection_port",
        side_effect=lambda df, p: df,
    )
    @patch(
        "logistic_tools.core.functions.logs_timeseries.define_dates_inspection.logs_preventive_aux.start_date_inspection"
    )
    @patch(
        "logistic_tools.core.functions.logs_timeseries.define_dates_inspection.InspectionSiteCreation"
    )
    @patch(
        "logistic_tools.core.functions.logs_timeseries.define_dates_inspection.aux_functions.safe_getattr"
    )
    def test_site_inspection_basic(
        self,
        m_safe_getattr,
        m_site_creation,
        m_start_dates,
        _m_create_chart,
    ):
        """
        Site inspection branch:
        - op_tow_port is False
        - uses InspectionSiteCreation.preventive_site_inspection
        - sets comment to 'event' or 'event_campaign' when inspection_campaign_flag is True
        """
        d1 = datetime(2025, 3, 1, 8, 0, 0)
        d2 = datetime(2025, 4, 1, 8, 0, 0)
        m_start_dates.return_value = [d1, d2]

        # days_main > 0 => n_vessel_main used
        insp_class = DummyInspClass(
            days_main=2,
            days_last=0,
            op_tow_port=False,
            vessel1_id="SITE_V1",
            vessel2_id=None,
            n_vessel_main=4,
            n_vessel_last=2,
        )
        inspection = DummyInspection("owc_insp_123", insp_class, n_vessel_1=99)

        # safe_getattr: simple chained getattr
        def _safe(obj, attrs, default=None):
            cur = obj
            for a in attrs:
                cur = getattr(cur, a, default)
            return cur

        m_safe_getattr.side_effect = _safe

        # Mock InspectionSiteCreation instance
        dummy_site_instance = MagicMock()
        dummy_site_instance.operation_completed = True
        dummy_site_instance.inspection_campaign_flag = True  # to test "_campaign" comment

        def _preventive_site_inspection(
            mother_vessel_inspection_campaign,
            find_element_class,
            end_datetimes,
            end_stat_chart_datetimes,
            valid_datetimes,
            d,
        ):
            end_dt = d + timedelta(hours=6)
            valid_datetimes.append(d)
            end_datetimes.append(end_dt)
            end_stat_chart_datetimes.append(end_dt)

        dummy_site_instance.preventive_site_inspection.side_effect = (
            _preventive_site_inspection
        )
        m_site_creation.return_value = dummy_site_instance

        df = define_dates.define_dates(
            COLS=self.COLS,
            inspection=inspection,
            event="inspection_site",
            start_year=2025,
            start_month=1,
            n_lifetime=1,
            percentile=95,
            find_element_class=MagicMock(),
            mother_vessel_inspection_campaign={},
        )

        # Two dates from start_date_inspection
        self.assertEqual(len(df), 2)
        self.assertListEqual(df["d_trigger"].tolist(), [d1, d2])
        # Comments should be suffixed with '_campaign' because flag is True
        self.assertTrue(df["comments"].str.startswith("inspection_site_campaign").all())
        # n_vessel_1 comes from insp_class.n_vessel_main (4), not from inspection.n_vessel_1
        self.assertEqual(df["n_vessel_1"].iloc[0], 4)
        # vessel_2 is None -> n_vessel_2 should be None
        self.assertIsNone(df["vessel_2"].iloc[0])
        self.assertTrue(df["n_vessel_2"].isna().all())

    @patch(
        "logistic_tools.core.functions.logs_timeseries.define_dates_inspection.logs_timeseries_func.create_stat_chart_inspection_port",
        side_effect=lambda df, p: df,
    )
    @patch(
        "logistic_tools.core.functions.logs_timeseries.define_dates_inspection.logs_preventive_aux.start_date_inspection"
    )
    @patch(
        "logistic_tools.core.functions.logs_timeseries.define_dates_inspection.InspectionSiteCreation"
    )
    @patch(
        "logistic_tools.core.functions.logs_timeseries.define_dates_inspection.aux_functions.safe_getattr"
    )
    def test_site_inspection_uses_n_vessel_last_when_days_main_zero(
        self,
        m_safe_getattr,
        m_site_creation,
        m_start_dates,
        _m_create_chart,
    ):
        """
        When days_main == 0, n_vessel_last must be used to fill n_vessel_1.
        """
        d1 = datetime(2025, 5, 1, 8, 0, 0)
        m_start_dates.return_value = [d1]

        insp_class = DummyInspClass(
            days_main=0,
            days_last=1,
            op_tow_port=False,
            vessel1_id="SITE_V1",
            vessel2_id=None,
            n_vessel_main=3,
            n_vessel_last=7,
        )
        inspection = DummyInspection("opv_insp_456", insp_class, n_vessel_1=99)

        def _safe(obj, attrs, default=None):
            cur = obj
            for a in attrs:
                cur = getattr(cur, a, default)
            return cur

        m_safe_getattr.side_effect = _safe

        dummy_site_instance = MagicMock()
        dummy_site_instance.operation_completed = True
        dummy_site_instance.inspection_campaign_flag = False

        def _preventive_site_inspection(
            mother_vessel_inspection_campaign,
            find_element_class,
            end_datetimes,
            end_stat_chart_datetimes,
            valid_datetimes,
            d,
        ):
            end_dt = d + timedelta(hours=4)
            valid_datetimes.append(d)
            end_datetimes.append(end_dt)
            end_stat_chart_datetimes.append(end_dt)

        dummy_site_instance.preventive_site_inspection.side_effect = (
            _preventive_site_inspection
        )
        m_site_creation.return_value = dummy_site_instance

        df = define_dates.define_dates(
            COLS=self.COLS,
            inspection=inspection,
            event="inspection_site",
            start_year=2025,
            start_month=5,
            n_lifetime=1,
            percentile=90,
            find_element_class=MagicMock(),
            mother_vessel_inspection_campaign={},
        )

        self.assertEqual(len(df), 1)
        # n_vessel_1 should be taken from n_vessel_last
        self.assertEqual(df["n_vessel_1"].iloc[0], 7)
        # Comments should equal the event (no campaign)
        self.assertEqual(df["comments"].iloc[0], "inspection_site")


if __name__ == "__main__":
    unittest.main(verbosity=2)
