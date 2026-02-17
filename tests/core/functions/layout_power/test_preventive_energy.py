# tests/test_preventive_energy.py

import unittest
from unittest.mock import patch
from datetime import datetime

import pandas as pd
import networkx as nx

from oriom.core.functions.layout_power import preventive_energy


COLS = [
    "Date",
    "Event",
    "id",
    "Name",
    "En_loss_kWh",
    "Time_shutdown",
]


class DummyInspClass:
    def __init__(self, level, name="Inspection", double_shift=False):
        self.level = level
        self.name = name
        self.double_shift = double_shift
        # Per il ramo timeseries servirebbe ts_data.oper_sched,
        # ma nei test statistici non è necessario (lo aggiungeremo solo per il test timeseries).


class DummyInspectionStat:
    def __init__(self, insp_id, level, shutdown_dict, name="Inspection", double_shift=False):
        self.id = insp_id
        self.insp_class = DummyInspClass(level=level, name=name, double_shift=double_shift)
        # Usato da preventive_rows nel ramo statistico
        self.shutdown_dict = shutdown_dict


class DummyFindElement:
    """
    Sostituisce Find_element_class: mantiene un mapping id -> DummyInspectionStat
    e solleva ValueError se l'ispezione non è trovata.
    """
    def __init__(self, stats_list):
        self._stats_by_id = {s.id: s for s in stats_list}

    def find_operation_stats(self, insp_id):
        if insp_id not in self._stats_by_id:
            raise ValueError("Inspection not found")
        return self._stats_by_id[insp_id]


class TestPreventiveEnergyNoDevices(unittest.TestCase):
    """
    Se nessun n_device_* è fornito, tutti gli output devono essere DataFrame vuoti.
    """

    @patch(
        "oriom.core.functions.layout_power.preventive_energy.log_event_convert_stringtime",
        side_effect=lambda df: df,
    )
    def test_returns_empty_dataframes_when_no_devices(self, _mock_convert):
        log_events = pd.DataFrame(
            {
                "event": ["inspection_site"],
                "id": ["ofw_insp_001"],
                "d_trigger": [datetime(2025, 6, 1, 10, 0, 0)],
                "d_end": [datetime(2025, 6, 1, 12, 0, 0)],
            }
        )

        dummy_finder = DummyFindElement([])

        df_wind, df_wave, df_pv = preventive_energy.preventive_energy(
            log_events=log_events,
            inspections_site_stat=[],
            inspections_port_stat=[],
            start_year=2025,
            find_element_class=dummy_finder,
        )

        self.assertTrue(df_wind.empty)
        self.assertTrue(df_wave.empty)
        self.assertTrue(df_pv.empty)


class TestPreventiveEnergyWind(unittest.TestCase):
    """
    Test per il ramo WIND dentro preventive_energy (uso statistico).
    """

    def setUp(self):
        # Single wind inspection in June 2025
        self.log_events = pd.DataFrame(
            {
                "event": ["inspection_site"],
                "id": ["ofw_insp_001"],
                "d_trigger": [datetime(2025, 6, 1, 10, 0, 0)],
                "d_end": [datetime(2025, 6, 1, 12, 0, 0)],
            }
        )

        # Dummy inspection stat con shutdown hours per mese 6
        self.inspections_site_stat = [
            DummyInspectionStat(
                insp_id="ofw_insp_001",
                level="device",
                shutdown_dict={"6": 2.5},
                name="WTG Site Inspection",
                double_shift=False,
            )
        ]
        self.inspections_port_stat = []

        # Graph semplice: shore node + un device node
        self.G_wind = nx.DiGraph()
        self.G_wind.add_node(0, level="SHORE", power=0.0)
        self.G_wind.add_node(1, level="device", power=10.0)
        self.G_wind.add_edge(1, 0, visible=True)

        # Monthly power (valore fittizio)
        self.power_wind = {6: 1000.0}

        self.find_element_class = DummyFindElement(
            self.inspections_site_stat + self.inspections_port_stat
        )

    @patch(
        "oriom.core.functions.layout_power.preventive_energy.log_event_convert_stringtime",
        side_effect=lambda df: df,
    )
    @patch(
        "oriom.core.functions.layout_power.preventive_energy.aux_layout_power_func.statistical_power_preventive_evaluation"
    )
    def test_wind_branch_builds_one_row_with_energy_and_shutdown(
        self,
        mock_stat_eval,
        _mock_convert,
    ):
        """
        Ramo WIND (STATISTIC_ENERGY=True):
        - una riga di ispezione in log_events
        - preventive_rows deve creare esattamente una riga in df_wind
        - En_loss_kWh viene dal mock di statistical_power_preventive_evaluation
        - Time_shutdown viene dal dizionario di shutdown (dopo cast a int delle chiavi)
        """
        mock_stat_eval.return_value = 42.0

        df_wind, df_wave, df_pv = preventive_energy.preventive_energy(
            log_events=self.log_events.copy(),
            inspections_site_stat=self.inspections_site_stat,
            inspections_port_stat=self.inspections_port_stat,
            start_year=2025,
            find_element_class=self.find_element_class,
            n_device_wtg=10,
            n_device_wec=None,
            n_device_pv=None,
            G_wind=self.G_wind,
            G_wave=None,
            G_pv=None,
            power_wind=self.power_wind,
            power_wave=None,
            power_pv=None,
            degradation_rate=None,
            STATISTIC_ENERGY=True,  # forziamo il ramo statistico
        )

        # Solo il ramo wind deve essere popolato
        self.assertFalse(df_wind.empty)
        self.assertTrue(df_wave.empty)
        self.assertTrue(df_pv.empty)

        self.assertEqual(len(df_wind), 1)
        row = df_wind.iloc[0]

        self.assertEqual(row["Event"], "inspection_site")
        self.assertEqual(row["id"], "ofw_insp_001")
        self.assertEqual(row["Name"], "WTG Site Inspection")
        self.assertEqual(row["En_loss_kWh"], 42.0)
        # Shutdown hours da shutdown_dict["6"] -> chiave convertita a int 6
        self.assertEqual(row["Time_shutdown"], 2.5)

        # statistical_power_preventive_evaluation deve essere chiamata una sola volta
        self.assertEqual(mock_stat_eval.call_count, 1)


class TestPreventiveEnergyWindTimeseries(unittest.TestCase):
    """
    Test per il ramo WIND con approccio timeseries (STATISTIC_ENERGY=False).
    """

    def setUp(self):
        # Una sola ispezione wind
        self.log_events = pd.DataFrame(
            {
                "event": ["inspection_site"],
                "id": ["ofw_insp_ts_001"],
                "d_trigger": [datetime(2025, 6, 2, 10, 0, 0)],
                "d_end": [datetime(2025, 6, 2, 12, 0, 0)],
            }
        )

        # InspectionStat con livello "device"
        self.insp_stat = DummyInspectionStat(
            insp_id="ofw_insp_ts_001",
            level="device",
            shutdown_dict={"6": 1.0},  # non usato nel ramo timeseries ma innocuo
            name="WTG TS Inspection",
            double_shift=False,
        )
        # Aggiungiamo ts_data.oper_sched per evitare AttributeError
        ts_data = type("TSData", (), {"oper_sched": "DUMMY_SCHED"})()
        self.insp_stat.insp_class.ts_data = ts_data

        self.inspections_site_stat = [self.insp_stat]
        self.inspections_port_stat = []

        # Graph con livello device
        self.G_wind = nx.DiGraph()
        self.G_wind.add_node(0, level="SHORE", power=0.0)
        self.G_wind.add_node(1, level="device", power=10.0)
        self.G_wind.add_edge(1, 0, visible=True)

        self.power_wind = {6: 1000.0}  # non usato nel timeseries

        self.find_element_class = DummyFindElement(
            self.inspections_site_stat + self.inspections_port_stat
        )

    @patch(
        "oriom.core.functions.layout_power.preventive_energy.log_event_convert_stringtime",
        side_effect=lambda df: df,
    )
    @patch(
        "oriom.core.functions.layout_power.preventive_energy.aux_layout_power_func.timeseries_power_preventive_evaluation"
    )
    @patch(
        "oriom.core.functions.layout_power.preventive_energy.aux_layout_power_func.take_date_inspection_oper_scheduler"
    )
    def test_wind_timeseries_branch_uses_timeseries_results(
        self,
        mock_take_dates,
        mock_ts_eval,
        _mock_convert,
    ):
        """
        Ramo WIND timeseries:
        - STATISTIC_ENERGY=False e prefix_list=['ofw','oce'] => else branch
        - take_date_inspection_oper_scheduler e timeseries_power_preventive_evaluation sono mockati
        - la riga finale deve riportare i valori di energy_list[0] e shutdown_hour_list[0].
        """
        # Mock: le date di ispezione non sono rilevanti, basta restituire qualcosa
        mock_take_dates.return_value = [["dummy_date"]]

        # timeseries_power_preventive_evaluation restituisce una lista con un elemento
        mock_ts_eval.return_value = ([100.0], [5.0])

        df_wind, df_wave, df_pv = preventive_energy.preventive_energy(
            log_events=self.log_events.copy(),
            inspections_site_stat=self.inspections_site_stat,
            inspections_port_stat=self.inspections_port_stat,
            start_year=2025,
            find_element_class=self.find_element_class,
            n_device_wtg=10,
            n_device_wec=None,
            n_device_pv=None,
            G_wind=self.G_wind,
            G_wave=None,
            G_pv=None,
            power_wind=self.power_wind,
            power_wave=None,
            power_pv=None,
            degradation_rate=None,
            STATISTIC_ENERGY=False,  # forziamo ramo timeseries
        )

        # Solo df_wind deve essere popolato
        self.assertFalse(df_wind.empty)
        self.assertTrue(df_wave.empty)
        self.assertTrue(df_pv.empty)

        self.assertEqual(len(df_wind), 1)
        row = df_wind.iloc[0]

        self.assertEqual(row["Event"], "inspection_site")
        self.assertEqual(row["id"], "ofw_insp_ts_001")
        self.assertEqual(row["Name"], "WTG TS Inspection")
        # Valori derivati dal mock timeseries_power_preventive_evaluation
        self.assertEqual(row["En_loss_kWh"], 100.0)
        self.assertEqual(row["Time_shutdown"], 5.0)

        # Verifica che le funzioni timeseries siano state chiamate una sola volta
        self.assertEqual(mock_take_dates.call_count, 1)
        self.assertEqual(mock_ts_eval.call_count, 1)


class TestPreventiveEnergyWave(unittest.TestCase):
    """
    Test per il ramo WAVE dentro preventive_energy (uso statistico).
    """

    def setUp(self):
        # Single wave inspection
        self.log_events = pd.DataFrame(
            {
                "event": ["inspection_port"],
                "id": ["owc_insp_001"],
                "d_trigger": [datetime(2025, 1, 10, 8, 0, 0)],
                "d_end": [datetime(2025, 1, 10, 12, 0, 0)],
            }
        )

        self.inspections_site_stat = []
        self.inspections_port_stat = [
            DummyInspectionStat(
                insp_id="owc_insp_001",
                level="device",
                shutdown_dict={"1": 4.0},
                name="WEC Port Inspection",
                double_shift=False,
            )
        ]

        self.G_wave = nx.DiGraph()
        self.G_wave.add_node(0, level="SHORE", power=0.0)
        self.G_wave.add_node(1, level="device", power=5.0)
        self.G_wave.add_edge(1, 0, visible=True)

        self.power_wave = {1: 500.0}

        self.find_element_class = DummyFindElement(
            self.inspections_site_stat + self.inspections_port_stat
        )

    @patch(
        "oriom.core.functions.layout_power.preventive_energy.log_event_convert_stringtime",
        side_effect=lambda df: df,
    )
    @patch(
        "oriom.core.functions.layout_power.preventive_energy.aux_layout_power_func.statistical_power_preventive_evaluation"
    )
    def test_wave_branch_builds_one_row(
        self,
        mock_stat_eval,
        _mock_convert,
    ):
        """
        Ramo WAVE (STATISTIC_ENERGY=True):
        - una riga di ispezione
        - deve generare una riga in df_wave con energia e shutdown
        """
        mock_stat_eval.return_value = 10.0

        df_wind, df_wave, df_pv = preventive_energy.preventive_energy(
            log_events=self.log_events.copy(),
            inspections_site_stat=self.inspections_site_stat,
            inspections_port_stat=self.inspections_port_stat,
            start_year=2025,
            find_element_class=self.find_element_class,
            n_device_wtg=None,
            n_device_wec=5,
            n_device_pv=None,
            G_wind=None,
            G_wave=self.G_wave,
            G_pv=None,
            power_wind=None,
            power_wave=self.power_wave,
            power_pv=None,
            degradation_rate=None,
            STATISTIC_ENERGY=True,  # ramo statistico
        )

        self.assertTrue(df_wind.empty)
        self.assertFalse(df_wave.empty)
        self.assertTrue(df_pv.empty)

        self.assertEqual(len(df_wave), 1)
        row = df_wave.iloc[0]
        self.assertEqual(row["Event"], "inspection_port")
        self.assertEqual(row["id"], "owc_insp_001")
        self.assertEqual(row["Name"], "WEC Port Inspection")
        self.assertEqual(row["En_loss_kWh"], 10.0)
        self.assertEqual(row["Time_shutdown"], 4.0)

        self.assertEqual(mock_stat_eval.call_count, 1)


class TestPreventiveEnergyPV(unittest.TestCase):
    """
    Test per il ramo PV dentro preventive_energy.
    Il ramo PV entra sempre nel blocco statistico perché 'opv' è in prefix_list.
    """

    def setUp(self):
        # Single PV inspection
        self.log_events = pd.DataFrame(
            {
                "event": ["inspection_site"],
                "id": ["opv_insp_001"],
                "d_trigger": [datetime(2025, 6, 1, 9, 0, 0)],
                "d_end": [datetime(2025, 6, 1, 11, 0, 0)],
            }
        )

        self.inspections_site_stat = [
            DummyInspectionStat(
                insp_id="opv_insp_001",
                level="inverter",
                shutdown_dict={"6": 3.0},
                name="PV Site Inspection",
                double_shift=True,
            )
        ]
        self.inspections_port_stat = []

        self.G_pv = nx.DiGraph()
        self.G_pv.add_node(0, level="SHORE", power=0.0)
        self.G_pv.add_node(1, level="inverter", power=20.0)
        self.G_pv.add_edge(1, 0, visible=True)

        # Simple PV power profile: month -> hour -> power
        self.power_pv = {6: {h: 50.0 for h in range(24)}}
        self.n_device_pv = 20
        self.start_year = 2020
        self.degradation_rate = 5.0

        self.find_element_class = DummyFindElement(
            self.inspections_site_stat + self.inspections_port_stat
        )

    @patch(
        "oriom.core.functions.layout_power.preventive_energy.log_event_convert_stringtime",
        side_effect=lambda df: df,
    )
    @patch(
        "oriom.core.functions.layout_power.preventive_energy.aux_layout_power_func.statistical_power_preventive_evaluation"
    )
    def test_pv_branch_calls_statistical_power_eval_with_degradation(
        self,
        mock_stat_eval,
        _mock_convert,
    ):
        """
        PV branch:
        - deve chiamare statistical_power_preventive_evaluation con degradation_rate e start_year
        - deve produrre una riga in df_pv con energia e ore di shutdown.
        """
        mock_stat_eval.return_value = 123.0

        df_wind, df_wave, df_pv = preventive_energy.preventive_energy(
            log_events=self.log_events.copy(),
            inspections_site_stat=self.inspections_site_stat,
            inspections_port_stat=self.inspections_port_stat,
            start_year=self.start_year,
            find_element_class=self.find_element_class,
            n_device_wtg=None,
            n_device_wec=None,
            n_device_pv=self.n_device_pv,
            G_wind=None,
            G_wave=None,
            G_pv=self.G_pv,
            power_wind=None,
            power_wave=None,
            power_pv=self.power_pv,
            degradation_rate=self.degradation_rate,
            STATISTIC_ENERGY=False,  # 'opv' forza comunque il ramo statistico
        )

        self.assertTrue(df_wind.empty)
        self.assertTrue(df_wave.empty)
        self.assertFalse(df_pv.empty)

        self.assertEqual(len(df_pv), 1)
        row = df_pv.iloc[0]
        self.assertEqual(row["Event"], "inspection_site")
        self.assertEqual(row["id"], "opv_insp_001")
        self.assertEqual(row["Name"], "PV Site Inspection")
        self.assertEqual(row["En_loss_kWh"], 123.0)
        self.assertEqual(row["Time_shutdown"], 3.0)

        # statistical_power_preventive_evaluation deve essere chiamata una sola volta
        self.assertEqual(mock_stat_eval.call_count, 1)

        args, kwargs = mock_stat_eval.call_args
        # dict_power deve essere lo stesso oggetto passato
        self.assertIs(kwargs["dict_power"], self.power_pv)
        # n_device_tot
        self.assertEqual(kwargs["n_device_tot"], self.n_device_pv)
        # degradation_rate e start_year passati correttamente
        self.assertEqual(kwargs["degradation_rate"], self.degradation_rate)
        self.assertEqual(kwargs["start_year"], self.start_year)


class TestPreventiveEnergyMissingInspection(unittest.TestCase):
    """
    Se un id di ispezione appare in log_events ma non nelle liste inspections_*,
    preventive_energy deve sollevare ValueError ("Inspection not found") tramite DummyFindElement.
    """

    @patch(
        "oriom.core.functions.layout_power.preventive_energy.log_event_convert_stringtime",
        side_effect=lambda df: df,
    )
    def test_missing_inspection_definition_raises_value_error(self, _mock_convert):
        # Una ispezione "ofw_insp_999" non presente in inspections_site_stat/port_stat
        log_events = pd.DataFrame(
            {
                "event": ["inspection_site"],
                "id": ["ofw_insp_999"],
                "d_trigger": [datetime(2025, 6, 1, 10, 0, 0)],
                "d_end": [datetime(2025, 6, 1, 12, 0, 0)],
            }
        )

        inspections_site_stat = []
        inspections_port_stat = []

        # Graph semplice per wind
        G_wind = nx.DiGraph()
        G_wind.add_node(0, level="SHORE", power=0.0)
        G_wind.add_node(1, level="device", power=10.0)
        G_wind.add_edge(1, 0, visible=True)

        power_wind = {6: 1000.0}

        # DummyFindElement senza ispezioni definite → solleva ValueError
        find_element_class = DummyFindElement([])

        with self.assertRaises(ValueError):
            preventive_energy.preventive_energy(
                log_events=log_events,
                inspections_site_stat=inspections_site_stat,
                inspections_port_stat=inspections_port_stat,
                start_year=2025,
                find_element_class=find_element_class,
                n_device_wtg=10,
                n_device_wec=None,
                n_device_pv=None,
                G_wind=G_wind,
                G_wave=None,
                G_pv=None,
                power_wind=power_wind,
                power_wave=None,
                power_pv=None,
                degradation_rate=None,
                STATISTIC_ENERGY=True,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
