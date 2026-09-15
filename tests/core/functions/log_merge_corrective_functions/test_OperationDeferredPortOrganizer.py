# tests/core/functions/log_merge_corrective_functions/test_OperationDeferredPortOrganizer.py

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd

import oriom.core.functions.log_merge_corrective_functions.OperationDeferredPortOrganizer as deferred_port_module

from oriom.core.functions.log_merge_corrective_functions.OperationDeferredPortOrganizer import (
    OperationDeferredPortCreation,
)


class TestOperationDeferredPortCreation(unittest.TestCase):
    """Tests for OperationDeferredPortCreation with vessel quantity and mobilisation logic."""

    def setUp(self):
        """Prepare reusable deterministic test data."""
        self.base_time = pd.Timestamp("2025-01-10 00:00:00")
        self.period = pd.Period("2025-01", freq="M")

        self.op_ttp_id = 10
        self.op_add_port_id = 11
        self.op_tts_id = 20
        self.op_port_id = 100

        self.vessel_ttp_id = "V_TTP"
        self.vessel_add_id = "V_ADD"
        self.vessel_shared_id = "V_SHARED"
        self.vessel_support_id = "V_SUPPORT"

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
            "year_month",
        ]

        self.log_columns_without_year_month = [
            column for column in self.log_columns if column != "year_month"
        ]

        self.schedule = pd.DataFrame(
            {
                "datetime": pd.date_range(
                    self.base_time,
                    periods=300,
                    freq="h",
                ),
            }
        )

        self.find_element_class = MagicMock()
        self.find_element_class.find_operation_stats.return_value = {"dummy": True}

        self.patcher_safe_getattr = patch.object(
            deferred_port_module,
            "safe_getattr",
            side_effect=self._fake_safe_getattr,
        )
        self.patcher_approximate_hourly_data = patch.object(
            deferred_port_module,
            "approximate_hourly_data",
            side_effect=lambda dt: pd.Timestamp(dt).floor("h"),
        )
        self.patcher_overlap = patch.object(
            deferred_port_module.logs_preventive_aux,
            "date_ranges_overlap",
            side_effect=self._fake_date_ranges_overlap,
        )
        self.patcher_check_index = patch.object(
            deferred_port_module,
            "_check_index_row_validity",
            side_effect=self._fake_check_index_row_validity,
        )
        self.patcher_compute = patch.object(
            deferred_port_module,
            "compute_operation_datetimes",
            side_effect=self._fake_compute_operation_datetimes,
        )
        self.patcher_create_mobilisation = patch.object(
            deferred_port_module,
            "create_mobilisation",
            side_effect=self._fake_create_mobilisation,
        )

        self.mock_safe_getattr = self.patcher_safe_getattr.start()
        self.mock_approximate_hourly_data = self.patcher_approximate_hourly_data.start()
        self.mock_overlap = self.patcher_overlap.start()
        self.mock_check_index = self.patcher_check_index.start()
        self.mock_compute = self.patcher_compute.start()
        self.mock_create_mobilisation = self.patcher_create_mobilisation.start()

        self.addCleanup(self.patcher_safe_getattr.stop)
        self.addCleanup(self.patcher_approximate_hourly_data.stop)
        self.addCleanup(self.patcher_overlap.stop)
        self.addCleanup(self.patcher_check_index.stop)
        self.addCleanup(self.patcher_compute.stop)
        self.addCleanup(self.patcher_create_mobilisation.stop)

    # ------------------------------------------------------------------
    # Fake external functions
    # ------------------------------------------------------------------

    @staticmethod
    def _fake_safe_getattr(obj, attrs):
        """Return a nested attribute."""
        value = obj
        for attr in attrs:
            value = getattr(value, attr)
        return value

    @staticmethod
    def _fake_date_ranges_overlap(start_1, end_1, start_2, end_2):
        """Return True when two time intervals overlap."""
        return not (end_1 <= start_2 or end_2 <= start_1)

    @staticmethod
    def _fake_check_index_row_validity(idx_end_leadtime, last_valid_idx, r, oper_sched):
        """Return one schedule row when the requested index is valid."""
        if idx_end_leadtime > last_valid_idx:
            return pd.DataFrame()

        return oper_sched.iloc[[idx_end_leadtime]].copy()

    @staticmethod
    def _fake_compute_operation_datetimes(df_filtered_start_tow, oper_stat):
        """Build deterministic operation datetimes from the selected schedule row."""
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
        n_vessel,
    ):
        """Create a minimal mobilisation row compatible with the output schema."""
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
                    n_vessel,
                    None,
                    None,
                    f"mobi_{count_fail}",
                    False,
                    False,
                    False,
                ]
            ],
            columns=self.log_columns_without_year_month,
        )

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------

    @staticmethod
    def _make_vessel(vessel_id, n_vessels=4, mobilisation_time=4):
        """Create a minimal vessel object."""
        return SimpleNamespace(
            id=vessel_id,
            n_vessels=n_vessels,
            mobilisation_time=mobilisation_time,
        )

    def _make_operation(
        self,
        operation_id,
        vessel_1,
        vessel_2=None,
        recommissioning_time=0,
    ):
        """Create a minimal tow/additional operation object."""
        return SimpleNamespace(
            id=operation_id,
            vessel1_id=vessel_1.id if vessel_1 else None,
            vessel1=vessel_1,
            vessel2_id=vessel_2.id if vessel_2 else None,
            vessel2=vessel_2,
            recommissioning_time=recommissioning_time,
        )

    def _make_port_operation(self, add_op_tow_port=None):
        """Create a minimal port operation object."""
        operation_ids = [
            self.op_ttp_id,
            self.op_tts_id,
            self.op_port_id,
        ]

        if add_op_tow_port is not None:
            operation_ids.append(self.op_add_port_id)

        operation_ids = sorted(set(operation_ids))

        return SimpleNamespace(
            id=self.op_port_id,
            n_device_at_port=10,
            n_device_stored_at_port=0,
            ts_data=SimpleNamespace(
                oper_sched=self.schedule,
                last_valid_index=len(self.schedule) - 1,
            ),
            tow_data=SimpleNamespace(
                dict_tow_oper_sched={
                    operation_id: self.schedule for operation_id in operation_ids
                },
                dict_tow_oper_last_idx={
                    operation_id: len(self.schedule) - 1 for operation_id in operation_ids
                },
                dict_oper_stat={
                    operation_id: {"dummy": True} for operation_id in operation_ids
                },
                add_op_tow_port=add_op_tow_port,
                add_op_tow_site=None,
                tow_site_oper_sched=self.schedule,
                last_valid_idx_tow_site=len(self.schedule) - 1,
            ),
        )

    def _make_row(
        self,
        offset_minutes,
        event,
        operation_id,
        vessel_1,
        n_vessel_1,
        vessel_2,
        n_vessel_2,
        comments="failure_F1",
    ):
        """Build one deterministic log row."""
        trigger = self.base_time + pd.Timedelta(minutes=offset_minutes)

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
            vessel_1,
            n_vessel_1,
            vessel_2,
            n_vessel_2,
            comments,
            True,
            False,
            False,
            self.period,
        ]

    def _make_log_events(
        self,
        has_additional_operation,
        add_vessel_id,
        ttp_vessel_id,
        add_quantity,
        ttp_quantity,
        vessel_2_id=None,
        vessel_2_quantity=0,
    ):
        """Build one complete deferred campaign for a single failure."""
        rows = []

        if vessel_2_id is None:
            vessel_2_id = self.vessel_support_id

        if has_additional_operation:
            rows.append(
                self._make_row(
                    offset_minutes=0,
                    event="additional_before_tow_port",
                    operation_id=self.op_add_port_id,
                    vessel_1=add_vessel_id,
                    n_vessel_1=add_quantity,
                    vessel_2=vessel_2_id,
                    n_vessel_2=0,
                )
            )
            ttp_offset = 10
            port_offset = 20
            tts_offset = 30
        else:
            ttp_offset = 0
            port_offset = 10
            tts_offset = 20

        rows.extend(
            [
                self._make_row(
                    offset_minutes=ttp_offset,
                    event="tow_to_port",
                    operation_id=self.op_ttp_id,
                    vessel_1=ttp_vessel_id,
                    n_vessel_1=ttp_quantity,
                    vessel_2=vessel_2_id,
                    n_vessel_2=vessel_2_quantity,
                ),
                self._make_row(
                    offset_minutes=port_offset,
                    event="operation_at_port",
                    operation_id=self.op_port_id,
                    vessel_1=ttp_vessel_id,
                    n_vessel_1=0,
                    vessel_2=vessel_2_id,
                    n_vessel_2=0,
                ),
                self._make_row(
                    offset_minutes=tts_offset,
                    event="tow_to_site",
                    operation_id=self.op_tts_id,
                    vessel_1=ttp_vessel_id,
                    n_vessel_1=ttp_quantity,
                    vessel_2=vessel_2_id,
                    n_vessel_2=0,
                ),
            ]
        )

        return pd.DataFrame(rows, columns=self.log_columns)

    def _build_instance(
        self,
        has_additional_operation,
        add_vessel_id,
        ttp_vessel_id,
        add_quantity,
        ttp_quantity,
        vessel_2_id=None,
        vessel_2_quantity=0,
        vessel_availability=None,
    ):
        """Build a complete manager instance for one test case."""
        if vessel_availability is None:
            vessel_availability = {}

        if vessel_2_id is None:
            vessel_2_id = self.vessel_support_id

        vessel_ids = {
            self.vessel_ttp_id,
            self.vessel_add_id,
            self.vessel_shared_id,
            self.vessel_support_id,
            add_vessel_id,
            ttp_vessel_id,
            vessel_2_id,
        }
        vessel_ids.discard(None)

        vessels = {
            vessel_id: self._make_vessel(
                vessel_id=vessel_id,
                n_vessels=vessel_availability.get(vessel_id, 4),
                mobilisation_time=4,
            )
            for vessel_id in vessel_ids
        }

        add_op_object = None
        if has_additional_operation:
            add_op_object = SimpleNamespace(id=self.op_add_port_id)

        port_operation = self._make_port_operation(
            add_op_tow_port=add_op_object,
        )

        oper_dict_tow = {
            self.op_ttp_id: self._make_operation(
                operation_id=self.op_ttp_id,
                vessel_1=vessels[ttp_vessel_id],
                vessel_2=vessels[vessel_2_id],
            ),
            self.op_tts_id: self._make_operation(
                operation_id=self.op_tts_id,
                vessel_1=vessels[ttp_vessel_id],
                vessel_2=vessels[vessel_2_id],
            ),
        }

        if has_additional_operation:
            oper_dict_tow[self.op_add_port_id] = self._make_operation(
                operation_id=self.op_add_port_id,
                vessel_1=vessels[add_vessel_id],
                vessel_2=vessels[vessel_2_id],
            )

        log_events_tow_def = self._make_log_events(
            has_additional_operation=has_additional_operation,
            add_vessel_id=add_vessel_id,
            ttp_vessel_id=ttp_vessel_id,
            add_quantity=add_quantity,
            ttp_quantity=ttp_quantity,
            vessel_2_id=vessel_2_id,
            vessel_2_quantity=vessel_2_quantity,
        )

        self.find_element_class.find_failure_from_id.return_value = SimpleNamespace(
            id="F1",
            operation_triggered=self.op_port_id,
        )
        self.find_element_class.find_operation.return_value = port_operation

        manager = OperationDeferredPortCreation(
            log_events_tow_def=log_events_tow_def,
            oper_port_dict={
                self.op_port_id: port_operation,
            },
            oper_dict_tow=oper_dict_tow,
            find_element_class=self.find_element_class,
        )

        return manager

    def _run_case(
        self,
        has_additional_operation,
        add_vessel_id,
        ttp_vessel_id,
        add_quantity,
        ttp_quantity,
        vessel_2_id=None,
        vessel_2_quantity=0,
        vessel_availability=None,
    ):
        """Build a manager, execute the full deferred_port_manager flow and return both."""
        manager = self._build_instance(
            has_additional_operation=has_additional_operation,
            add_vessel_id=add_vessel_id,
            ttp_vessel_id=ttp_vessel_id,
            add_quantity=add_quantity,
            ttp_quantity=ttp_quantity,
            vessel_2_id=vessel_2_id,
            vessel_2_quantity=vessel_2_quantity,
            vessel_availability=vessel_availability,
        )

        result = manager.deferred_port_manager(
            time_fail_op_immediately=2.0,
        )

        return manager, result

    # ------------------------------------------------------------------
    # Assertion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _operation_events(result):
        """Return all non-mobilisation event names."""
        return result.loc[
            result["event"] != "mobilisation_merged",
            "event",
        ].tolist()

    @staticmethod
    def _mobilisation_summary(result):
        """Return mobilisation rows as tuples of vessel id, quantity and operation id."""
        mobilisation_rows = result[result["event"] == "mobilisation_merged"]

        return [
            (
                row["vessel_1"],
                int(row["n_vessel_1"]),
                row["id"],
            )
            for _, row in mobilisation_rows.iterrows()
        ]

    def _assert_tow_storage_slot(self, manager, vessel_id, slot_index, should_exist):
        """Assert whether a tow-at-port storage slot exists for device 1."""
        self.assertIn(vessel_id, manager.tow_at_port_date)
        self.assertIn(1, manager.tow_at_port_date[vessel_id])

        slot_value = manager.tow_at_port_date[vessel_id][1][slot_index]

        if should_exist:
            self.assertIsNotNone(slot_value)
        else:
            self.assertIsNone(slot_value)

    # ------------------------------------------------------------------
    # Main parameterised cases
    # ------------------------------------------------------------------

    def test_deferred_port_manager_mobilisation_cases(self):
        """Test full deferred_port_manager flow for add-operation and vessel-quantity combinations."""
        cases = [
            {
                "name": "no additional operation, two vessels used by towing",
                "has_additional_operation": False,
                "add_vessel_id": None,
                "ttp_vessel_id": self.vessel_ttp_id,
                "add_quantity": 0,
                "ttp_quantity": 2,
                "expected_events": [
                    "tow_to_port",
                    "operation_at_port",
                    "tow_to_site",
                ],
                "expected_mobilisations": [
                    (self.vessel_ttp_id, 2, self.op_ttp_id),
                ],
                "expected_mobilised": {
                    self.vessel_ttp_id: 2,
                    self.vessel_support_id: 0,
                },
                "expected_storage": [
                    (self.vessel_ttp_id, 0, True),
                    (self.vessel_ttp_id, 1, False),
                ],
            },
            {
                "name": "no additional operation, one vessel used by towing",
                "has_additional_operation": False,
                "add_vessel_id": None,
                "ttp_vessel_id": self.vessel_ttp_id,
                "add_quantity": 0,
                "ttp_quantity": 1,
                "expected_events": [
                    "tow_to_port",
                    "operation_at_port",
                    "tow_to_site",
                ],
                "expected_mobilisations": [
                    (self.vessel_ttp_id, 1, self.op_ttp_id),
                ],
                "expected_mobilised": {
                    self.vessel_ttp_id: 1,
                    self.vessel_support_id: 0,
                },
                "expected_storage": [
                    (self.vessel_ttp_id, 0, True),
                    (self.vessel_ttp_id, 1, False),
                ],
            },
            {
                "name": "additional operation with different vessel, all quantities equal to one",
                "has_additional_operation": True,
                "add_vessel_id": self.vessel_add_id,
                "ttp_vessel_id": self.vessel_ttp_id,
                "add_quantity": 1,
                "ttp_quantity": 1,
                "expected_events": [
                    "additional_before_tow_port",
                    "tow_to_port",
                    "operation_at_port",
                    "tow_to_site",
                ],
                "expected_mobilisations": [
                    (self.vessel_add_id, 1, self.op_add_port_id),
                    (self.vessel_ttp_id, 1, self.op_ttp_id),
                ],
                "expected_mobilised": {
                    self.vessel_add_id: 1,
                    self.vessel_ttp_id: 1,
                    self.vessel_support_id: 0,
                },
                "expected_storage": [
                    (self.vessel_add_id, 0, True),
                    (self.vessel_add_id, 1, False),
                    (self.vessel_ttp_id, 0, True),
                    (self.vessel_ttp_id, 1, False),
                ],
            },
            {
                "name": "additional operation with different vessel, add quantity one and TTP quantity two",
                "has_additional_operation": True,
                "add_vessel_id": self.vessel_add_id,
                "ttp_vessel_id": self.vessel_ttp_id,
                "add_quantity": 1,
                "ttp_quantity": 2,
                "expected_events": [
                    "additional_before_tow_port",
                    "tow_to_port",
                    "operation_at_port",
                    "tow_to_site",
                ],
                "expected_mobilisations": [
                    (self.vessel_add_id, 1, self.op_add_port_id),
                    (self.vessel_ttp_id, 2, self.op_ttp_id),
                ],
                "expected_mobilised": {
                    self.vessel_add_id: 1,
                    self.vessel_ttp_id: 2,
                    self.vessel_support_id: 0,
                },
                "expected_storage": [
                    (self.vessel_add_id, 0, True),
                    (self.vessel_add_id, 1, False),
                    (self.vessel_ttp_id, 0, True),
                    (self.vessel_ttp_id, 1, False),
                ],
            },
            {
                "name": "additional operation with different vessel, add quantity two and TTP quantity one",
                "has_additional_operation": True,
                "add_vessel_id": self.vessel_add_id,
                "ttp_vessel_id": self.vessel_ttp_id,
                "add_quantity": 2,
                "ttp_quantity": 1,
                "expected_events": [
                    "additional_before_tow_port",
                    "tow_to_port",
                    "operation_at_port",
                    "tow_to_site",
                ],
                "expected_mobilisations": [
                    (self.vessel_add_id, 2, self.op_add_port_id),
                    (self.vessel_ttp_id, 1, self.op_ttp_id),
                ],
                "expected_mobilised": {
                    self.vessel_add_id: 2,
                    self.vessel_ttp_id: 1,
                    self.vessel_support_id: 0,
                },
                "expected_storage": [
                    (self.vessel_add_id, 0, True),
                    (self.vessel_add_id, 1, False),
                    (self.vessel_ttp_id, 0, True),
                    (self.vessel_ttp_id, 1, False),
                ],
            },
            {
                "name": "additional operation with different vessel, add quantity two and TTP quantity two",
                "has_additional_operation": True,
                "add_vessel_id": self.vessel_add_id,
                "ttp_vessel_id": self.vessel_ttp_id,
                "add_quantity": 2,
                "ttp_quantity": 2,
                "expected_events": [
                    "additional_before_tow_port",
                    "tow_to_port",
                    "operation_at_port",
                    "tow_to_site",
                ],
                "expected_mobilisations": [
                    (self.vessel_add_id, 2, self.op_add_port_id),
                    (self.vessel_ttp_id, 2, self.op_ttp_id),
                ],
                "expected_mobilised": {
                    self.vessel_add_id: 2,
                    self.vessel_ttp_id: 2,
                    self.vessel_support_id: 0,
                },
                "expected_storage": [
                    (self.vessel_add_id, 0, True),
                    (self.vessel_add_id, 1, False),
                    (self.vessel_ttp_id, 0, True),
                    (self.vessel_ttp_id, 1, False),
                ],
            },
            {
                "name": "additional operation with same vessel, add quantity two and TTP quantity one",
                "has_additional_operation": True,
                "add_vessel_id": self.vessel_shared_id,
                "ttp_vessel_id": self.vessel_shared_id,
                "add_quantity": 2,
                "ttp_quantity": 1,
                "expected_events": [
                    "additional_before_tow_port",
                    "tow_to_port",
                    "operation_at_port",
                    "tow_to_site",
                ],
                "expected_mobilisations": [
                    (self.vessel_shared_id, 2, self.op_add_port_id),
                ],
                "expected_mobilised": {
                    self.vessel_shared_id: 2,
                    self.vessel_support_id: 0,
                },
                "expected_storage": [
                    (self.vessel_shared_id, 0, True),
                    (self.vessel_shared_id, 1, True),
                ],
            },
            {
                "name": "additional operation with same vessel, add quantity two and TTP quantity two",
                "has_additional_operation": True,
                "add_vessel_id": self.vessel_shared_id,
                "ttp_vessel_id": self.vessel_shared_id,
                "add_quantity": 2,
                "ttp_quantity": 2,
                "expected_events": [
                    "additional_before_tow_port",
                    "tow_to_port",
                    "operation_at_port",
                    "tow_to_site",
                ],
                "expected_mobilisations": [
                    (self.vessel_shared_id, 2, self.op_add_port_id),
                ],
                "expected_mobilised": {
                    self.vessel_shared_id: 2,
                    self.vessel_support_id: 0,
                },
                "expected_storage": [
                    (self.vessel_shared_id, 0, True),
                    (self.vessel_shared_id, 1, True),
                ],
            },
            {
                "name": "additional operation with same vessel, add quantity one and TTP quantity two",
                "has_additional_operation": True,
                "add_vessel_id": self.vessel_shared_id,
                "ttp_vessel_id": self.vessel_shared_id,
                "add_quantity": 1,
                "ttp_quantity": 2,
                "expected_events": [
                    "additional_before_tow_port",
                    "tow_to_port",
                    "operation_at_port",
                    "tow_to_site",
                ],
                "expected_mobilisations": [
                    (self.vessel_shared_id, 1, self.op_add_port_id),
                    (self.vessel_shared_id, 1, self.op_ttp_id),
                ],
                "expected_mobilised": {
                    self.vessel_shared_id: 2,
                    self.vessel_support_id: 0,
                },
                "expected_storage": [
                    (self.vessel_shared_id, 0, True),
                    (self.vessel_shared_id, 1, True),
                ],
            },
        ]

        for case in cases:
            with self.subTest(case=case["name"]):
                manager, result = self._run_case(
                    has_additional_operation=case["has_additional_operation"],
                    add_vessel_id=case["add_vessel_id"],
                    ttp_vessel_id=case["ttp_vessel_id"],
                    add_quantity=case["add_quantity"],
                    ttp_quantity=case["ttp_quantity"],
                )

                self.assertTrue(manager.operation_completed)
                self.assertEqual(
                    self._operation_events(result),
                    case["expected_events"],
                )
                self.assertEqual(
                    self._mobilisation_summary(result),
                    case["expected_mobilisations"],
                )

                for vessel_id, expected_count in case["expected_mobilised"].items():
                    self.assertEqual(
                        manager.vessels_mobilitated[vessel_id],
                        expected_count,
                    )

                for vessel_id, slot_index, should_exist in case["expected_storage"]:
                    self._assert_tow_storage_slot(
                        manager=manager,
                        vessel_id=vessel_id,
                        slot_index=slot_index,
                        should_exist=should_exist,
                    )

    def test_deferred_port_manager_creates_mobilisation_for_vessel_1_and_vessel_2(self):
        """The full flow should create mobilisation rows for vessel_1 and vessel_2 when both have positive quantity."""
        manager, result = self._run_case(
            has_additional_operation=False,
            add_vessel_id=None,
            ttp_vessel_id=self.vessel_ttp_id,
            add_quantity=0,
            ttp_quantity=1,
            vessel_2_id=self.vessel_support_id,
            vessel_2_quantity=2,
        )

        self.assertTrue(manager.operation_completed)

        self.assertEqual(
            self._mobilisation_summary(result),
            [
                (self.vessel_ttp_id, 1, self.op_ttp_id),
            ],
        )

        self.assertEqual(manager.vessels_mobilitated[self.vessel_ttp_id], 1)
        self.assertEqual(manager.vessels_mobilitated[self.vessel_support_id], 0)

    def test_deferred_port_manager_uses_available_vessel_quantity_across_multiple_devices(self):
        """The full flow should account for several available vessels and quantity used per towing operation."""
        vessel_availability = {
            self.vessel_ttp_id: 5,
            self.vessel_support_id: 4,
        }

        port_operation = self._make_port_operation(add_op_tow_port=None)

        vessel_ttp = self._make_vessel(
            vessel_id=self.vessel_ttp_id,
            n_vessels=5,
            mobilisation_time=4,
        )
        vessel_support = self._make_vessel(
            vessel_id=self.vessel_support_id,
            n_vessels=0,
            mobilisation_time=4,
        )

        oper_dict_tow = {
            self.op_ttp_id: self._make_operation(
                operation_id=self.op_ttp_id,
                vessel_1=vessel_ttp,
                vessel_2=vessel_support,
            ),
            self.op_tts_id: self._make_operation(
                operation_id=self.op_tts_id,
                vessel_1=vessel_ttp,
                vessel_2=vessel_support,
            ),
        }

        rows = []

        for failure_index, failure_name in enumerate(["F1", "F2"]):
            offset = failure_index * 60
            comments = f"failure_{failure_name}"

            rows.extend(
                [
                    self._make_row(
                        offset_minutes=offset,
                        event="tow_to_port",
                        operation_id=self.op_ttp_id,
                        vessel_1=self.vessel_ttp_id,
                        n_vessel_1=2,
                        vessel_2=self.vessel_support_id,
                        n_vessel_2=0,
                        comments=comments,
                    ),
                    self._make_row(
                        offset_minutes=offset + 10,
                        event="operation_at_port",
                        operation_id=self.op_port_id,
                        vessel_1=self.vessel_ttp_id,
                        n_vessel_1=0,
                        vessel_2=self.vessel_support_id,
                        n_vessel_2=0,
                        comments=comments,
                    ),
                    self._make_row(
                        offset_minutes=offset + 20,
                        event="tow_to_site",
                        operation_id=self.op_tts_id,
                        vessel_1=self.vessel_ttp_id,
                        n_vessel_1=2,
                        vessel_2=self.vessel_support_id,
                        n_vessel_2=0,
                        comments=comments,
                    ),
                ]
            )

        log_events_tow_def = pd.DataFrame(rows, columns=self.log_columns)

        self.find_element_class.find_failure_from_id.return_value = SimpleNamespace(
            id="F",
            operation_triggered=self.op_port_id,
        )
        self.find_element_class.find_operation.return_value = port_operation

        manager = OperationDeferredPortCreation(
            log_events_tow_def=log_events_tow_def,
            oper_port_dict={
                self.op_port_id: port_operation,
            },
            oper_dict_tow=oper_dict_tow,
            find_element_class=self.find_element_class,
        )

        self.assertEqual(manager.vessel_available[self.vessel_ttp_id], vessel_availability[self.vessel_ttp_id])

        result = manager.deferred_port_manager(
            time_fail_op_immediately=2.0,
        )

        self.assertTrue(manager.operation_completed)

        operation_events = self._operation_events(result)
        self.assertEqual(operation_events.count("tow_to_port"), 2)
        self.assertEqual(operation_events.count("operation_at_port"), 2)
        self.assertEqual(operation_events.count("tow_to_site"), 2)

        self.assertEqual(
            self._mobilisation_summary(result),
            [
                (self.vessel_ttp_id, 2, self.op_ttp_id),
                (self.vessel_ttp_id, 2, self.op_ttp_id),
            ],
        )

        self.assertEqual(manager.vessels_mobilitated[self.vessel_ttp_id], 4)
        self.assertLessEqual(
            manager.vessels_mobilitated[self.vessel_ttp_id],
            manager.vessel_available[self.vessel_ttp_id],
        )


    def test_overlap_shift_tow_keeps_dates_when_no_overlap_exists(self):
        """overlap_shift_tow should keep the proposed row dates when no vessel overlap exists."""
        manager = self._build_instance(
            has_additional_operation=False,
            add_vessel_id=None,
            ttp_vessel_id=self.vessel_ttp_id,
            add_quantity=0,
            ttp_quantity=1,
        )

        row = manager.log_events_tow_def.iloc[0]
        manager.period = self.period

        row_dates = {
            "date_end_wait_start": self.base_time + pd.Timedelta(hours=20),
            "date_end_dur_net_port": self.base_time + pd.Timedelta(hours=21),
            "date_end_transit_ts": self.base_time + pd.Timedelta(hours=22),
            "date_end_wait_site": self.base_time + pd.Timedelta(hours=23),
            "date_end_dur_net_site": self.base_time + pd.Timedelta(hours=24),
            "date_end_transit_tp": self.base_time + pd.Timedelta(hours=25),
            "date_end": self.base_time + pd.Timedelta(hours=26),
            "date_end_stat_chart": self.base_time + pd.Timedelta(hours=27),
        }

        existing_intervals = {
            "device_1": [
                (
                    self.base_time + pd.Timedelta(hours=5),
                    self.base_time + pd.Timedelta(hours=1),
                    1,
                )
            ]
        }

        result = manager.overlap_shift_tow(
            overlap_date=True,
            tow_at_site_date=existing_intervals,
            n_vess_row=4,
            oper_schedule=self.schedule,
            row_dates=row_dates,
            idx_oper_sched=20,
            last_valid_idx=len(self.schedule) - 1,
            row=row,
        )

        self.assertFalse(result.empty)
        self.assertEqual(
            result["d_end_wait_start"].iloc[0],
            self.base_time + pd.Timedelta(hours=20),
        )
        self.assertEqual(
            result["d_end"].iloc[0],
            self.base_time + pd.Timedelta(hours=26),
        )


    def test_overlap_shift_tow_reschedules_when_overlap_exceeds_vessel_capacity(self):
        """overlap_shift_tow should reschedule when overlapping vessel demand exceeds available vessels."""
        manager = self._build_instance(
            has_additional_operation=False,
            add_vessel_id=None,
            ttp_vessel_id=self.vessel_ttp_id,
            add_quantity=0,
            ttp_quantity=2,
            vessel_availability={
                self.vessel_ttp_id: 3,
            },
        )

        row = manager.log_events_tow_def.iloc[0]
        manager.period = self.period

        row_dates = {
            "date_end_wait_start": self.base_time + pd.Timedelta(hours=10),
            "date_end_dur_net_port": self.base_time + pd.Timedelta(hours=11),
            "date_end_transit_ts": self.base_time + pd.Timedelta(hours=12),
            "date_end_wait_site": self.base_time + pd.Timedelta(hours=13),
            "date_end_dur_net_site": self.base_time + pd.Timedelta(hours=14),
            "date_end_transit_tp": self.base_time + pd.Timedelta(hours=15),
            "date_end": self.base_time + pd.Timedelta(hours=16),
            "date_end_stat_chart": self.base_time + pd.Timedelta(hours=17),
        }

        existing_intervals = {
            "device_1": [
                (
                    self.base_time + pd.Timedelta(hours=18),
                    self.base_time + pd.Timedelta(hours=9),
                    2,
                )
            ]
        }

        result = manager.overlap_shift_tow(
            overlap_date=True,
            tow_at_site_date=existing_intervals,
            n_vess_row=3,
            oper_schedule=self.schedule,
            row_dates=row_dates,
            idx_oper_sched=10,
            last_valid_idx=len(self.schedule) - 1,
            row=row,
        )

        self.assertFalse(result.empty)

        self.assertGreater(
            result["d_end_wait_start"].iloc[0],
            self.base_time + pd.Timedelta(hours=10),
        )
        self.assertTrue(manager.operation_completed)


    def test_overlap_shift_tow_accepts_exact_vessel_capacity(self):
        """overlap_shift_tow should accept overlaps when total vessel use equals available capacity."""
        manager = self._build_instance(
            has_additional_operation=False,
            add_vessel_id=None,
            ttp_vessel_id=self.vessel_ttp_id,
            add_quantity=0,
            ttp_quantity=2,
            vessel_availability={
                self.vessel_ttp_id: 4,
            },
        )

        row = manager.log_events_tow_def.iloc[0]
        manager.period = self.period

        row_dates = {
            "date_end_wait_start": self.base_time + pd.Timedelta(hours=10),
            "date_end_dur_net_port": self.base_time + pd.Timedelta(hours=11),
            "date_end_transit_ts": self.base_time + pd.Timedelta(hours=12),
            "date_end_wait_site": self.base_time + pd.Timedelta(hours=13),
            "date_end_dur_net_site": self.base_time + pd.Timedelta(hours=14),
            "date_end_transit_tp": self.base_time + pd.Timedelta(hours=15),
            "date_end": self.base_time + pd.Timedelta(hours=16),
            "date_end_stat_chart": self.base_time + pd.Timedelta(hours=17),
        }

        existing_intervals = {
            "device_1": [
                (
                    self.base_time + pd.Timedelta(hours=18),
                    self.base_time + pd.Timedelta(hours=9),
                    2,
                )
            ]
        }

        result = manager.overlap_shift_tow(
            overlap_date=True,
            tow_at_site_date=existing_intervals,
            n_vess_row=4,
            oper_schedule=self.schedule,
            row_dates=row_dates,
            idx_oper_sched=10,
            last_valid_idx=len(self.schedule) - 1,
            row=row,
        )

        self.assertFalse(result.empty)
        self.assertEqual(
            result["d_end_wait_start"].iloc[0],
            self.base_time + pd.Timedelta(hours=10),
        )
        self.assertEqual(
            result["d_end"].iloc[0],
            self.base_time + pd.Timedelta(hours=16),
        )

    def test_overlap_shift_tow_returns_empty_when_reschedule_has_no_valid_index(self):
        """overlap_shift_tow should stop the operation when no valid reschedule row exists."""
        manager = self._build_instance(
            has_additional_operation=False,
            add_vessel_id=None,
            ttp_vessel_id=self.vessel_ttp_id,
            add_quantity=0,
            ttp_quantity=2,
            vessel_availability={
                self.vessel_ttp_id: 3,
            },
        )

        row = manager.log_events_tow_def.iloc[0]
        manager.period = self.period

        row_dates = {
            "date_end_wait_start": self.base_time + pd.Timedelta(hours=10),
            "date_end_dur_net_port": self.base_time + pd.Timedelta(hours=11),
            "date_end_transit_ts": self.base_time + pd.Timedelta(hours=12),
            "date_end_wait_site": self.base_time + pd.Timedelta(hours=13),
            "date_end_dur_net_site": self.base_time + pd.Timedelta(hours=14),
            "date_end_transit_tp": self.base_time + pd.Timedelta(hours=15),
            "date_end": self.base_time + pd.Timedelta(hours=16),
            "date_end_stat_chart": self.base_time + pd.Timedelta(hours=17),
        }

        existing_intervals = {
            "device_1": [
                (
                    self.base_time + pd.Timedelta(hours=18),
                    self.base_time + pd.Timedelta(hours=9),
                    2,
                )
            ]
        }

        with patch.object(
            deferred_port_module,
            "_check_index_row_validity",
            return_value=pd.DataFrame(),
        ):
            result = manager.overlap_shift_tow(
                overlap_date=True,
                tow_at_site_date=existing_intervals,
                n_vess_row=3,
                oper_schedule=self.schedule,
                row_dates=row_dates,
                idx_oper_sched=10,
                last_valid_idx=len(self.schedule) - 1,
                row=row,
            )

        self.assertTrue(result.empty)
        self.assertFalse(manager.operation_completed)
        
if __name__ == "__main__":
    unittest.main(verbosity=2)