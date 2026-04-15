# test_OperationDeferredPortOrganizer.py

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd

from oriom.core.functions.log_merge_corrective_functions.OperationDeferredPortOrganizer import (
    OperationDeferredPortCreation,
)


class TestOperationDeferredPortCreation(unittest.TestCase):

    def setUp(self):
        """
        Prepare a minimal but realistic environment for the class under test.
        """

        self.base_time = pd.Timestamp("2025-01-10 00:00:00")

        self.log_columns = [
            "d_trigger",
            "d_end_leadtime",
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
            "shutdown",
            "ST_contract_1",
            "ST_contract_2",
        ]

        self.schedule = pd.DataFrame(
            {
                "datetime": pd.date_range(self.base_time, periods=200, freq="h"),
            }
        )

        self.vessel = SimpleNamespace(
            id="V1",
            n_vessels=1,
            mobilisation_time=4,
        )

        self.add_op_tow_port = None
        self.add_op_tow_site = None
        
        self.oper_port_dict = {100: SimpleNamespace(
            id=100,
            n_device_at_port=1,
            n_device_stored_at_port=0,
            ts_data=SimpleNamespace(
                oper_sched=self.schedule,
                last_valid_index=len(self.schedule) - 1,
            ),
            tow_data=SimpleNamespace(
                dict_tow_oper_sched={
                    10: self.schedule,
                    11: self.schedule,
                    20: self.schedule,
                    21: self.schedule,
                    22: self.schedule,
                    100: self.schedule,
                },
                dict_tow_oper_last_idx={
                    10: len(self.schedule) - 1,
                    11: len(self.schedule) - 1,
                    20: len(self.schedule) - 1,
                    21: len(self.schedule) - 1,
                    22: len(self.schedule) - 1,
                    100: len(self.schedule) - 1,
                },
                dict_oper_stat={
                    10: {"dummy": True},
                    11: {"dummy": True},
                    20: {"dummy": True},
                    21: {"dummy": True},
                    22: {"dummy": True},
                    100: {"dummy": True},
                },
                add_op_tow_port=self.add_op_tow_port,
                add_op_tow_site=self.add_op_tow_site,
                tow_site_oper_sched=self.schedule,
                last_valid_idx_tow_site=len(self.schedule) - 1,
            ),
        )}

        self.oper_dict_tow = {
            10: SimpleNamespace(id=10, vessel1_id="V1", vessel1=self.vessel, recommissioning_time=0),
            11: SimpleNamespace(id=11, vessel1_id="V1", vessel1=self.vessel, recommissioning_time=0),
            20: SimpleNamespace(id=20, vessel1_id="V1", vessel1=self.vessel, recommissioning_time=0),
            21: SimpleNamespace(id=21, vessel1_id="V1", vessel1=self.vessel, recommissioning_time=6),
            22: SimpleNamespace(id=22, vessel1_id="V1", vessel1=self.vessel, recommissioning_time=0),
        }

        self.find_element_class = MagicMock()
        self.find_element_class.find_operation_stats.return_value = {"dummy": True}

        self.period = pd.Period("2025-01", freq="M")

        self.patcher_safe_getattr = patch(
            "oriom.core.functions.log_merge_corrective_functions.OperationDeferredPortOrganizer.safe_getattr",
            side_effect=lambda obj, attrs: getattr(getattr(obj, attrs[0]), attrs[1]),
        )
        self.patcher_approximate_hourly_data = patch(
            "oriom.core.functions.log_merge_corrective_functions.OperationDeferredPortOrganizer.approximate_hourly_data",
            side_effect=lambda dt: pd.Timestamp(dt).floor("h"),
        )
        self.patcher_overlap = patch(
            "oriom.core.functions.log_merge_corrective_functions.OperationDeferredPortOrganizer.logs_preventive_aux.date_ranges_overlap",
            side_effect=lambda start_1, end_1, start_2, end_2: not (end_1 <= start_2 or end_2 <= start_1),
        )
        self.patcher_check_index = patch(
            "oriom.core.functions.log_merge_corrective_functions.OperationDeferredPortOrganizer._check_index_row_validity",
            side_effect=self._fake_check_index_row_validity,
        )
        self.patcher_compute = patch(
            "oriom.core.functions.log_merge_corrective_functions.OperationDeferredPortOrganizer.compute_operation_datetimes",
            side_effect=self._fake_compute_operation_datetimes,
        )
        self.patcher_create_mobilisation = patch(
            "oriom.core.functions.log_merge_corrective_functions.OperationDeferredPortOrganizer.create_mobilisation",
            side_effect=self._fake_create_mobilisation,
        )

        self.patcher_safe_getattr.start()
        self.patcher_approximate_hourly_data.start()
        self.patcher_overlap.start()
        self.patcher_check_index.start()
        self.patcher_compute.start()
        self.patcher_create_mobilisation.start()

        self.addCleanup(self.patcher_safe_getattr.stop)
        self.addCleanup(self.patcher_approximate_hourly_data.stop)
        self.addCleanup(self.patcher_overlap.stop)
        self.addCleanup(self.patcher_check_index.stop)
        self.addCleanup(self.patcher_compute.stop)
        self.addCleanup(self.patcher_create_mobilisation.stop)

    def _build_row(
        self,
        trigger_offset_minutes,
        event,
        operation_id,
        comments="failure_1",
    ):
        """
        Build one log row using deterministic timestamps.
        """

        trigger = self.base_time + pd.Timedelta(minutes=trigger_offset_minutes)

        return [
            trigger,
            trigger + pd.Timedelta(hours=1),
            trigger + pd.Timedelta(hours=2),
            trigger + pd.Timedelta(hours=3),
            trigger + pd.Timedelta(hours=4),
            trigger + pd.Timedelta(hours=5),
            trigger + pd.Timedelta(hours=6),
            trigger + pd.Timedelta(hours=7),
            trigger + pd.Timedelta(hours=8),
            trigger + pd.Timedelta(hours=9),
            event,
            operation_id,
            "V1",
            1,
            None,
            None,
            comments,
            True,
            False,
            False,
        ]

    def _build_log_events_three_rows(self):
        """
        Build a campaign with three rows:
        tow_to_port -> operation_at_port -> tow_to_site
        """

        df = pd.DataFrame(
            [
                self._build_row(0, "tow_to_port", 10),
                self._build_row(10, "operation_at_port", 100),
                self._build_row(20, "tow_to_site", 20),
            ],
            columns=self.log_columns,
        )
        df["year_month"] = df["d_trigger"].dt.to_period("M")
        return df

    def _build_log_events_five_rows(self):
        """
        Build a campaign with five rows:
        additional_before_tow_port -> tow_to_port -> operation_at_port
        -> tow_to_site -> additional_after_tow_site
        """

        df = pd.DataFrame(
            [
                self._build_row(0, "additional_before_tow_port", 11),
                self._build_row(10, "tow_to_port", 10),
                self._build_row(20, "operation_at_port", 100),
                self._build_row(30, "tow_to_site", 20),
                self._build_row(40, "additional_after_tow_site", 21),
            ],
            columns=self.log_columns,
        )
        df["year_month"] = df["d_trigger"].dt.to_period("M")
        return df

    def _fake_check_index_row_validity(self, idx_end_leadtime, last_valid_idx, r, oper_sched):
        """
        Return one valid schedule row when the index is valid, otherwise an empty DataFrame.
        """

        if idx_end_leadtime > last_valid_idx:
            return pd.DataFrame()

        return oper_sched.iloc[[idx_end_leadtime]].copy()

    def _fake_compute_operation_datetimes(self, df_filtered_start_tow, oper_stat):
        """
        Build deterministic operation datetimes from the selected schedule row.
        """

        start = pd.Timestamp(df_filtered_start_tow["datetime"].iloc[0])

        return {
            "date_end_wait_start": start + pd.Timedelta(hours=1),
            "date_end_dur_net_port": start + pd.Timedelta(hours=2),
            "date_end_transit_ts": start + pd.Timedelta(hours=3),
            "date_end_wait_site": start + pd.Timedelta(hours=4),
            "date_end_dur_net_site": start + pd.Timedelta(hours=5),
            "date_end_transit_tp": start + pd.Timedelta(hours=6),
            "date_end": start + pd.Timedelta(hours=7),
            "date_end_stat_chart": start + pd.Timedelta(hours=8),
        }

    def _fake_create_mobilisation(
        self,
        df,
        mobilisation_date,
        end_mobi,
        event,
        vessel,
        oper_list,
        count_fail,
        concat,
        n_vessel
    ):
        """
        Create a minimal mobilisation row compatible with the class output schema.
        """

        return pd.DataFrame(
            [
                [
                    mobilisation_date,
                    mobilisation_date,
                    end_mobi,
                    end_mobi,
                    end_mobi,
                    end_mobi,
                    end_mobi,
                    end_mobi,
                    end_mobi,
                    end_mobi,
                    event,
                    oper_list[0],
                    vessel.id,
                    1,
                    None,
                    None,
                    f"mobi_{count_fail}",
                    False,
                    False,
                    False,
                ]
            ],
            columns=self.log_columns,
        )

    def _build_instance(self, log_events_tow_def):
        """
        Create a fresh class instance for each test branch.
        """

        return OperationDeferredPortCreation(
            log_events_tow_def=log_events_tow_def.copy(),
            oper_port_dict=self.oper_port_dict,
            oper_dict_tow=self.oper_dict_tow,
            find_element_class=self.find_element_class,
        )

    def test_init_builds_internal_state(self):
        """
        Ensure initialization populates schedules, vessel availability and dictionaries.
        """

        log_events_tow_def = self._build_log_events_three_rows()
        manager = self._build_instance(log_events_tow_def)

        self.assertEqual(manager.n_device_at_port, 1)
        self.assertEqual(manager.vessel_available["V1"], 1)
        self.assertIn(100, manager.dict_oper_sched)
        self.assertIn(11, manager.dict_oper_sched)
        self.assertIn(22, manager.dict_oper_sched)
        self.assertTrue(manager.operation_completed)

    def test_reset_data_period_reinitializes_runtime_dictionaries(self):
        """
        Ensure period-specific state is reset correctly.
        """

        log_events_tow_def = self._build_log_events_three_rows()
        manager = self._build_instance(log_events_tow_def)

        manager.dev_idx_station_port = 99
        manager.tow_at_port_date["V1"][1] = ("x", "y")
        manager.tow_at_site_date["V1"][1] = ("x", "y")
        manager.oper_at_port_date[1] = ("x", "y")

        manager.reset_data_period()

        self.assertEqual(manager.dev_idx_station_port, 0)
        self.assertEqual(manager.tow_at_port_date, {"V1": {}})
        self.assertEqual(manager.tow_at_site_date, {"V1": {}})
        self.assertEqual(manager.oper_at_port_date, {})

    def test_write_event_row_appends_dataframe(self):
        """
        Ensure a new event row is appended to the internal log.
        """

        log_events_tow_def = self._build_log_events_three_rows()
        manager = self._build_instance(log_events_tow_def)
        row_to_write = log_events_tow_def.iloc[[0]]

        manager.write_event_row(row_to_write)

        self.assertEqual(len(manager.df_port_oper_def_log), 1)
        self.assertEqual(manager.df_port_oper_def_log.iloc[0]["id"], 10)

    def test_overlap_shift_tow_returns_row_without_recomputation_when_no_overlap(self):
        """
        Ensure overlap_shift_tow returns a new row directly when there is no overlap.
        """

        log_events_tow_def = self._build_log_events_three_rows()
        manager = self._build_instance(log_events_tow_def)
        row = log_events_tow_def.iloc[0]
        row_dates = self._fake_compute_operation_datetimes(
            pd.DataFrame({"datetime": [self.base_time + pd.Timedelta(hours=10)]}),
            {},
        )

        result = manager.overlap_shift_tow(
            overlap_date=True,
            tow_at_site_date={"dev_1": (self.base_time, self.base_time + pd.Timedelta(minutes=30))},
            n_vess_row=2,
            oper_schedule=self.schedule,
            row_dates=row_dates,
            idx_oper_sched=0,
            last_valid_idx=len(self.schedule) - 1,
            row=row,
            period=self.period,
        )

        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty)
        self.assertEqual(result.iloc[0]["event"], "tow_to_port")

    def test_overlap_shift_tow_returns_empty_when_schedule_cannot_be_found(self):
        """
        Ensure overlap_shift_tow returns an empty DataFrame when no valid schedule exists.
        """

        log_events_tow_def = self._build_log_events_three_rows()
        manager = self._build_instance(log_events_tow_def)
        row = log_events_tow_def.iloc[0]
        row_dates = self._fake_compute_operation_datetimes(
            pd.DataFrame({"datetime": [self.base_time + pd.Timedelta(hours=5)]}),
            {},
        )

        with patch(
            "oriom.core.functions.log_merge_corrective_functions.OperationDeferredPortOrganizer._check_index_row_validity",
            return_value=pd.DataFrame(),
        ):
            result = manager.overlap_shift_tow(
                overlap_date=True,
                tow_at_site_date={
                    "dev_1": (
                        self.base_time + pd.Timedelta(hours=20),
                        self.base_time + pd.Timedelta(hours=5),
                    )
                },
                n_vess_row=1,
                oper_schedule=self.schedule,
                row_dates=row_dates,
                idx_oper_sched=0,
                last_valid_idx=len(self.schedule) - 1,
                row=row,
                period=self.period,
            )

        self.assertTrue(result.empty)
        self.assertFalse(manager.operation_completed)

    def test_tow_to_port_first_device_uses_original_row(self):
        """
        Ensure the first device uses the original event row without rescheduling.
        """

        log_events_tow_def = self._build_log_events_three_rows()
        manager = self._build_instance(log_events_tow_def)
        row = log_events_tow_def.iloc[0]

        result, write_event = manager.tow_to_port(row=row, device_n=1, period=self.period)

        self.assertTrue(write_event)
        self.assertEqual(result.iloc[0]["id"], 10)
        self.assertIn(1, manager.tow_at_port_date["V1"])

    def test_tow_to_port_reschedules_for_second_device(self):
        """
        Ensure the tow-to-port event is rescheduled when vessel capacity is exceeded.
        """

        log_events_tow_def = self._build_log_events_three_rows()
        manager = self._build_instance(log_events_tow_def)
        row = log_events_tow_def.iloc[0]
        manager.tow_at_port_date[1] = {'V1':
            (
                self.base_time + pd.Timedelta(hours=20),
                self.base_time + pd.Timedelta(hours=10),
            )
        }
        manager.n_device_at_port = 2
        manager.dev_idx_station_port = 2
        result, write_event = manager.tow_to_port(
            row=row,
            device_n=2,
            period=self.period,
            date_start_op=self.base_time + pd.Timedelta(hours=10),
        )

        self.assertTrue(write_event)
        self.assertFalse(result.empty)
        self.assertEqual(result.iloc[0]["id"], 10)
        self.assertIn(2, manager.tow_at_port_date["V1"])

    def test_tow_to_port_returns_empty_when_reschedule_fails(self):
        """
        Ensure tow_to_port returns an empty DataFrame when schedule lookup fails.
        """

        log_events_tow_def = self._build_log_events_three_rows()
        manager = self._build_instance(log_events_tow_def)
        row = log_events_tow_def.iloc[0]

        with patch(
            "oriom.core.functions.log_merge_corrective_functions.OperationDeferredPortOrganizer._check_index_row_validity",
            return_value=pd.DataFrame(),
        ):
            result = manager.tow_to_port(
                row=row,
                device_n=2,
                period=self.period,
                date_start_op=self.base_time + pd.Timedelta(hours=10),
            )

        self.assertTrue(result.empty)
        self.assertFalse(manager.operation_completed)

    def test_operation_at_port_first_device_uses_original_row(self):
        """
        Ensure the first port operation reuses the original row.
        """

        log_events_tow_def = self._build_log_events_three_rows()
        manager = self._build_instance(log_events_tow_def)
        row = log_events_tow_def.iloc[1]

        result = manager.operation_at_port(
            row=row,
            device_n=1,
            date_start_op=self.base_time,
            period=self.period,
        )

        self.assertFalse(result.empty)
        self.assertEqual(result.iloc[0]["id"], 100)
        self.assertIn(1, manager.oper_at_port_date)

    def test_operation_at_port_second_device_is_rescheduled(self):
        """
        Ensure subsequent port operations are rescheduled from the provided start date.
        """

        log_events_tow_def = self._build_log_events_three_rows()
        manager = self._build_instance(log_events_tow_def)
        row = log_events_tow_def.iloc[1]

        result = manager.operation_at_port(
            row=row,
            device_n=2,
            date_start_op=self.base_time + pd.Timedelta(hours=11),
            period=self.period,
        )

        self.assertFalse(result.empty)
        self.assertEqual(result.iloc[0]["event"], "operation_at_port")

    def test_tow_to_site_second_device_with_tts_branch(self):
        """
        Ensure tow_to_site uses the dedicated tow-site schedule when tts is True.
        """

        log_events_tow_def = self._build_log_events_three_rows()
        manager = self._build_instance(log_events_tow_def)
        manager.n_device_at_port = 2
        manager.oper_port = manager.oper_port_dict[100]
        manager.dev_idx_station_port = 2
        row = log_events_tow_def.iloc[2]
        manager.tow_at_site_date["V1"][1] = (
            self.base_time + pd.Timedelta(hours=50),
            self.base_time + pd.Timedelta(hours=40),
        )

        result = manager.tow_to_site(
            row=row,
            device_n=2,
            tts=True,
            date_start_op=self.base_time + pd.Timedelta(hours=12),
            period=self.period,
        )

        self.assertFalse(result.empty)
        self.assertEqual(result.iloc[0]["id"], 20)
        self.assertIn(2, manager.tow_at_site_date["V1"])

    def test_create_mobi_returns_mobilisation_row(self):
        """
        Ensure create_mobi builds a valid mobilisation row.
        """

        log_events_tow_def = self._build_log_events_three_rows()
        manager = self._build_instance(log_events_tow_def)
        manager.df_port_oper_def_log = log_events_tow_def.iloc[[0]].copy()
        row = log_events_tow_def.iloc[0]

        result = manager.create_mobi(
            row=row,
            time_fail_op_immediately=2.0,
            vessel=self.vessel,
            n_vess=1
        )

        self.assertFalse(result.empty)
        self.assertEqual(result.iloc[0]["event"], "mobilisation_merged")
        self.assertEqual(result.iloc[0]["vessel_1"], "V1")

    def test_add_recommission_updates_event_and_site_tracking(self):
        """
        Ensure add_recommission updates timestamps and tracking dictionaries.
        """

        log_events_tow_def = self._build_log_events_five_rows()
        manager = self._build_instance(log_events_tow_def)
        row = log_events_tow_def.iloc[4]
        row_dates_tow_recom = log_events_tow_def.iloc[[4]].copy()
        manager.dev_idx_station_port = 1
        manager.tow_at_site_date["V1"][1] = (
            row_dates_tow_recom["d_end"].iloc[0],
            row_dates_tow_recom["d_end_wait_start"].iloc[0],
        )
        manager.oper_port = manager.oper_port_dict[100]
        manager.oper_port.tow_data.add_op_tow_port = SimpleNamespace(
            id=11,
            ts_data=SimpleNamespace(
                oper_sched=self.schedule,
                last_valid_index=len(self.schedule) - 1,
            ),
        )
        manager.oper_port.tow_data.add_op_tow_site = SimpleNamespace(
            id=22,
            ts_data=SimpleNamespace(
                oper_sched=self.schedule,
                last_valid_index=len(self.schedule) - 1,
            ),
        )

        result = manager.add_recommission(
            row_dates_tow_recom=row_dates_tow_recom,
            row=row,
            recommission=6,
        )

        self.assertEqual(result.iloc[0]["event"], "recommissioning")
        self.assertIsNone(result.iloc[0]["vessel_1"])
        self.assertEqual(
            manager.tow_at_site_date["V1"][1][0],
            result.iloc[0]["d_end"],
        )

    def test_deferred_port_manager_full_flow_with_three_rows(self):
        """
        Ensure the main manager handles the basic three-row flow correctly.
        """

        log_events_tow_def = self._build_log_events_three_rows()
        manager = self._build_instance(log_events_tow_def)
        self.find_element_class.find_operation.return_value = self.oper_port_dict[100]
        result = manager.deferred_port_manager(time_fail_op_immediately=2.0)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty)
        self.assertIn("mobilisation_merged", result["event"].values)
        self.assertIn("tow_to_port", result["event"].values)
        self.assertIn("operation_at_port", result["event"].values)
        self.assertIn("tow_to_site", result["event"].values)
        self.assertNotIn("recommissioning", result["event"].values)

    def test_deferred_port_manager_full_flow_with_five_rows(self):
        """
        Ensure the main manager handles the five-row flow with additional operations.
        """

        log_events_tow_def = self._build_log_events_five_rows()
        manager = self._build_instance(log_events_tow_def)
        self.find_element_class.find_operation.return_value = self.oper_port_dict[100]
        result = manager.deferred_port_manager(time_fail_op_immediately=2.0)

        self.assertIsInstance(result, pd.DataFrame)
        self.assertFalse(result.empty)
        self.assertIn("mobilisation_merged", result["event"].values)
        self.assertIn("additional_before_tow_port", result["event"].values)
        self.assertIn("tow_to_port", result["event"].values)
        self.assertIn("operation_at_port", result["event"].values)
        self.assertIn("tow_to_site", result["event"].values)
        self.assertIn("additional_after_tow_site", result["event"].values)
        self.assertIn("recommissioning", result["event"].values)

    def test_deferred_port_manager_logs_error_when_operation_is_not_completed(self):
        """
        Ensure an error is logged when a deferred campaign cannot be completed.
        """

        log_events_tow_def = self._build_log_events_three_rows()
        manager = self._build_instance(log_events_tow_def)
        manager.oper_port = manager.oper_port_dict[100]
        manager.oper_port.tow_data.add_op_tow_port = False
        self.find_element_class.find_operation.return_value = self.oper_port_dict[100]
        with patch.object(
            manager,
            "tow_to_port",
            side_effect=lambda *args, **kwargs: self._mark_incomplete_and_return_empty(manager),
        ), patch(
            "oriom.core.functions.log_merge_corrective_functions.OperationDeferredPortOrganizer.logging.error"
        ) as mock_logging_error:
            result = manager.deferred_port_manager(time_fail_op_immediately=2.0)

        self.assertTrue(result.empty)
        mock_logging_error.assert_called_once()

    @staticmethod
    def _mark_incomplete_and_return_empty(manager):
        """
        Helper used to simulate a failed scheduling flow.
        """

        manager.operation_completed = False
        return pd.DataFrame(), True


if __name__ == "__main__":
    unittest.main()