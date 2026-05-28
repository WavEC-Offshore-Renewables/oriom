# test_excel_to_yaml.py

import os
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from ruamel.yaml import YAML

import oriom.inputs.excel_to_yaml as excel_to_yaml_module


class TestExcelToYaml(unittest.TestCase):
    @patch("oriom.inputs.excel_to_yaml.pd.read_excel")
    def test_excel_to_yaml_creates_inputs_gen_yaml_from_gen_inputs_sheet(
        self, mock_read_excel
    ):
        """
        excel_to_yaml must read the 'Gen_inputs' sheet and create the file
        inputs_gen.yaml with the expected fields.
        """

        # Fake DataFrame for the Gen_inputs sheet
        df_gen = pd.DataFrame(
            {
                "input": [
                    "use previous run dir",
                    "previous tseries",
                    "number of runs",
                    "overwrite previous",
                    "double shifts",
                    "logevents file",
                    "failureevent file",
                    "unknown parameter",
                ],
                "value": [
                    r"C:\tmp\prev",
                    1,
                    5,
                    0,
                    1,
                    r"C:\logs",
                    r"C:\fails",
                    999,  # this should only generate a warning and be ignored
                ],
                "units": [""] * 8,
            }
        )

        def fake_read_excel(*args, **kwargs):
            sheet = kwargs.get("sheet_name")
            if sheet == "Gen_inputs":
                return df_gen
            # Simulates pandas behavior when the sheet does not exist
            raise ValueError(f"Worksheet named '{sheet}' not found")

        mock_read_excel.side_effect = fake_read_excel

        yaml_safe = YAML(typ="safe")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Call the function under test
            excel_to_yaml_module.excel_to_yaml(
                file_excel="dummy.xlsx",  # the path is ignored by the mock
                out_dir=tmpdir,
            )

            # Verify that the file has been created
            yaml_path = os.path.join(tmpdir, "inputs_gen.yaml")
            self.assertTrue(
                os.path.exists(yaml_path),
                "inputs_gen.yaml was not created in the output folder",
            )

            # Load the YAML content and verify fields
            with open(yaml_path, "r") as f:
                data = yaml_safe.load(f)

            # Expected dictionary after processing the Gen_inputs sheet
            expected = {
                # default set in inputs_general, then updated by the "double shifts" row
                "consider double shifts": {"value": True, "units": None},
                # default set to 1, then overwritten by "number of runs"
                "number_runs": {"value": 5, "units": None},
                "previous run dir": {
                    "value": r"C:\tmp\prev",
                    "units": None,
                },
                "consider tseries": {"value": True, "units": None},
                "overwrite": {"value": False, "units": None},
                "logevents file": {"value": r"C:\logs", "units": None},
                "failureevent file": {"value": r"C:\fails", "units": None},
            }

            self.assertEqual(
                data,
                expected,
                "The content of inputs_gen.yaml does not match the expected result",
            )

    # ------------------------------------------------------------------
    # Extended Test: cover all sheet and file YAML
    # ------------------------------------------------------------------
    @patch("oriom.inputs.excel_to_yaml.platform.system", return_value="Linux")
    @patch("oriom.inputs.excel_to_yaml.pd.read_excel")
    def test_excel_to_yaml_creates_all_yaml_files_from_multiple_sheets(
        self, mock_read_excel, mock_platform_system
    ):
        """
        excel_to_yaml must read multiple sheets and generate the corresponding YAML
        files with correctly converted values and units.
        Questo test aumenta il coverage su inputs_tseries, inputs_stats, inputs_costs,
        general_wtg/wec/pv, vessels, fuels, loads, densities, rovs, inspections, corrective,
        towing, activities, failures, scenarios.
        """

        # -------------------------
        # 1) Build all fake dataframes
        # -------------------------
        # Gen_inputs
        df_gen = pd.DataFrame(
            {
                "input": [
                    "previous run dir",
                    "previous tseries",
                    "number of runs",
                    "overwrite previous",
                    "double shifts",
                    "logevents file",
                    "failureevent file",
                ],
                "value": [
                    r"/tmp/prev",
                    1,
                    3,
                    0,
                    1,
                    r"/tmp/logs",
                    r"/tmp/fails",
                ],
                "units": [""] * 7,
            }
        )

        # TSA_inputs
        df_tsa = pd.DataFrame(
            {
                "input": [
                    "Site latitude",
                    "Site longitude",
                    "Metocean file",
                    "Metocean windspeed height",
                    "Surface roughness",
                    "Distance to port",
                    "Time between devices pv",
                    "Time between devices wt",
                    "Time between devices wec",
                    "Max WoW between activities",
                    "Timeseries analysed percent",
                    "Length export cable",
                    "Shift duration",
                    "Double shifts",
                    "Merge vessel",
                    "Unknown TSA row",
                ],
                "value": [
                    45.0,
                    -10.0,
                    r"C:\meto\file.nc",
                    20.0,
                    0.0005,
                    10000.0,      # in meters, converted in in km
                    30.0,         # 30 min -> 0.5 h
                    60.0,         # 60 min -> 1 h
                    120.0,        # 120 min -> 2 h
                    8.0,
                    0.5,
                    50.0,
                    12,
                    1,
                    "CTV1, ATV2",
                    999,
                ],
                "units": [
                    "degrees",
                    "degrees",
                    "",
                    "m",
                    "m",
                    "m",
                    "minutes",
                    "minutes",
                    "minutes",
                    "hours",
                    "%",
                    "km",
                    "hours",
                    "",
                    "",
                    "",
                ],
            }
        )

        # SA_inputs
        df_stats = pd.DataFrame(
            {
                "input": [
                    "Project lifetime",
                    "Start year project",
                    "Start month project",
                    "Day scheduling operation",
                    "Percentile main",
                    "Percentile 1",
                    "Percentile 2",
                    "Infant mortality period",
                    "Wear out period",
                    "Failure ratio",
                    "Failure ratio sensitivity",
                    "Percentage shutdown",
                    "Unknown stats",
                ],
                "value": [
                    25,
                    2025,
                    2,
                    365,
                    50,
                    25,
                    75,
                    0,
                    2,
                    0.1,
                    2.0,
                    10,
                    999,
                ],
                "units": [
                    "years",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "years",
                    "years",
                    "",
                    "",
                    "%",
                    "",
                ],
            }
        )

        # C_inputs
        df_costs = pd.DataFrame(
            {
                "input": [
                    "Fuel cost HFO",
                    "Fuel cost MGO",
                    "Fuel cost MDO",
                    "Vessel cost year",
                    "Port terminal daily cost",
                    "Port terminal annual cost",
                    "Try merge operations",
                    "Time operations merge",
                    "Insurance annual cost",
                    "Electricity selling price",
                    "Electricity selling price wt",
                    "Electricity selling price pv",
                    "Electricity selling price wec",
                    "Technicians annual cost",
                    "Unknown cost",
                ],
                "value": [
                    100.0,
                    200.0,
                    300.0,
                    1000.0,
                    500.0,
                    10000.0,
                    1,
                    5,
                    4000.0,
                    50.0,
                    55.0,
                    60.0,
                    65.0,
                    7000.0,
                    999,
                ],
                "units": [
                    "euros/ton",
                    "euros per ton",
                    "euro per ton",
                    "euros",
                    "euros",
                    "euros",
                    "",
                    "days",
                    "euros",
                    "euros/MWh",
                    "euros/MWh",
                    "euros/MWh",
                    "euros/MWh",
                    "euros",
                    "",
                ],
            }
        )

        # Gen_WTG
        df_wtg = pd.DataFrame(
            {
                "input": [
                    "Number of devices",
                    "Rated power",
                    "Cut-in speed",
                    "Cut-off speed",
                    "Hub height",
                    "Power curve file",
                    "Moorings per wtg",
                    "Number of strings",
                    "Number of substations",
                    "Number export cables",
                    "Number devices in port",
                    "Number devices in port stored",
                    "Layout type",
                    "Unknown WTG",
                ],
                "value": [
                    10,
                    3.0,
                    4.0,
                    25.0,
                    10000.0,
                    r"C:\curve\wtg.csv",
                    3,
                    4,
                    1,
                    2,
                    2,
                    10,
                    10,
                    999,
                ],
                "units": [
                    "",
                    "MW/device",
                    "m/s",
                    "km/h",
                    "cm",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ],
            }
        )

        # Gen_WEC
        df_wec = pd.DataFrame(
            {
                "input": [
                    "Number of devices",
                    "Rated power",
                    "Power matrix file",
                    "Number of strings",
                    "Number of substations",
                    "Number export cables",
                    "Number devices in port",
                    "Number devices in port stored",
                    "Layout type",
                    "Unknown WEC",
                ],
                "value": [
                    5,
                    1.5,
                    r"C:\matrix\wec.csv",
                    2,
                    1,
                    1,
                    5,
                    5,
                    2,
                    999,
                ],
                "units": [
                    "",
                    "MW/device",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ],
            }
        )

        # Gen_PV
        df_pv = pd.DataFrame(
            {
                "input": [
                    "Number devices",
                    "Device power",
                    "Power curve file",
                    "Number of strings",
                    "Number of inverters",
                    "Number of transformers",
                    "Number of substations",
                    "Number export cables",
                    "Number island array",
                    "Number device in port",
                    "Number device in port stored",
                    "Degradation",
                    "Layout type",
                    "Max failure module",
                    "Unknown PV",
                ],
                "value": [
                    10,
                    500.0,
                    r"C:\curve\pv.csv",
                    10,
                    5,
                    2,
                    1,
                    2,
                    3,
                    1,
                    1,
                    0.5,
                    1,
                    10,
                    999,
                ],
                "units": [
                    "",
                    "kW/device",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ],
            }
        )

        # Vessels
        df_vessels = pd.DataFrame(
            {
                "id": ["UNIT", "CTV1"],
                "type": ["UNIT", "CTV"],
                "list_name": ["UNIT", "list_ctv"],
                "number_vessels": ["UNIT", 2],
                "speed_transit": ["UNIT", 20.0],
                "speed_towing": ["UNIT", 5.0],
                "daily_charter": ["UNIT", 10000.0],
                "mother_vessel": ["UNIT", "no"],
                "annual_contract": ["UNIT", "NA"],
                "n_ves_annual_contract": ["UNIT", "NA"],
                "months_contract": ["UNIT", "NA"],
                "monthly_contract_cost": ["UNIT", "NA"],
                "n_ves_monthly_contract": ["UNIT", "NA"],
                "mobilisation_time": ["UNIT", 24.0],
                "mobilisation_cost": ["UNIT", 50000.0],
                "crew_capacity": ["UNIT", 12],
                "overnight": ["UNIT", "no"],
                "num_berths": ["UNIT", "NA"],
                "power": ["UNIT", "NA"],
                "fuel_type": ["UNIT", "MGO"],
                "fuel_cons_transit": ["UNIT", 1.0],
                "fuel_cons_maneuver": ["UNIT", 0.5],
                "fuel_cons_standby": ["UNIT", 0.2],
                "notes": ["UNIT", "NA"],
            }
        )

        # Vessel_fuel
        df_vessels_fuel = pd.DataFrame(
            {
                "vessel": ["UNIT", "CTV1"],
                "fuel type": ["UNIT", "MGO"],
                "rated power": ["UNIT", 1000.0],
                "sfoc": ["UNIT", 200.0],
            }
        )

        # Vessel_load_factor
        df_vessels_loads = pd.DataFrame(
            {
                "operation": ["UNIT", "op1"],
                "load_factor": ["UNIT", 0.8],
            }
        )

        # Vessel_fuel_density
        df_vessels_density = pd.DataFrame(
            {
                "fuel": ["UNIT", "MGO"],
                "density": ["UNIT", 0.85],
            }
        )

        # Gen_ROVs
        df_rovs = pd.DataFrame(
            {
                "id": ["UNIT", "ROV1"],
                "rov name": ["UNIT", "RovAlpha"],
                "type": ["UNIT", "ROV"],
                "daily_charter": ["UNIT", 5000.0],
                "weight": ["UNIT", "NA"],
                "dimensions": ["UNIT", "NA"],
                "useful_capacity": ["UNIT", "NA"],
                "speed_transit": ["UNIT", "NA"],
                "battery_capacity": ["UNIT", "NA"],
                "recharging_duration": ["UNIT", "NA"],
                "max_distance": ["UNIT", "NA"],
                "avg_autonomy": ["UNIT", "NA"],
                "on_site": ["UNIT", "NA"],
                "support_vessel": ["UNIT", "NA"],
                "nr_technicians": ["UNIT", 2],
                "ws_max": ["UNIT", "NA"],
                "hs_max": ["UNIT", "NA"],
                "daylight": ["UNIT", "NA"],
                "precipitation_max": ["UNIT", "NA"],
            }
        )

        # InspectionSite
        df_inspec_site = pd.DataFrame(
            {
                "id": ["UNIT", "INS1"],
                "name": ["UNIT", "Inspection Site 1"],
                "overnight_stay": ["UNIT", "no"],
                "periodicity": ["UNIT", 12],
                "technicians_per_device": ["UNIT", 2],
                "technician_cost": ["UNIT", 300.0],
                "dur_per_device": ["UNIT", 8.0],
                "device_shutdown": ["UNIT", "yes"],
                "level": ["UNIT", 1],
                "preferred_months": ["UNIT", "1,2"],
                "day_start": ["UNIT", 1],
                "wtg_intervened": ["UNIT", "yes"],
                "wec_intervened": ["UNIT", "NA"],
                "pv_intervened": ["UNIT", "NA"],
                "hs": ["UNIT", 2.0],
                "tp": ["UNIT", 8.0],
                "ws": ["UNIT", 15.0],
                "ws_hub": ["UNIT", 20.0],
                "cs": ["UNIT", 1.0],
                "light": ["UNIT", "day"],
                "vessel1_id": ["UNIT", "CTV1"],
                "vessel1_qt": ["UNIT", 1],
                "vessel2_id": ["UNIT", "NA"],
                "vessel2_qt": ["UNIT", "NA"],
                "rov_drone": ["UNIT", "NA"],
                "parts_cost": ["UNIT", 0.0],
                "other_costs": ["UNIT", 0.0],
                "to_be_grouped": ["UNIT", "no"],
                "to_group_with": ["UNIT", "NA"],
                "double_shift": ["UNIT", 0],
            }
        )

        # InspectionPort
        df_inspec_port = pd.DataFrame(
            {
                "id": ["UNIT", "INP1"],
                "name": ["UNIT", "Inspection Port 1"],
                "periodicity": ["UNIT", 12],
                "technicians_per_device": ["UNIT", 1],
                "technician_cost": ["UNIT", 200.0],
                "dur_per_device": ["UNIT", 4.0],
                "preferred_months": ["UNIT", "3,4"],
                "day_start": ["UNIT", 1],
                "devices_intervened": ["UNIT", "all"],
                "ws": ["UNIT", 20.0],
                "light": ["UNIT", "day"],
                "level": ["UNIT", 1],
                "parts_cost": ["UNIT", 0.0],
                "other_costs": ["UNIT", 0.0],
                "double_shift": ["UNIT", 0],
            }
        )

        # CorrectiveMinor
        df_corr_minor = pd.DataFrame(
            {
                "id": ["UNIT", "CM1"],
                "name": ["UNIT", "Corrective minor 1"],
                "duration_net": ["UNIT", 8.0],
                "device_shutdown": ["UNIT", "yes"],
                "vessel1_id": ["UNIT", "CTV1"],
                "vessel1_qt": ["UNIT", 1],
                "technicians": ["UNIT", 2],
                "technician_cost": ["UNIT", 300.0],
                "level": ["UNIT", 1],
                "wtg": ["UNIT", "yes"],
                "wec": ["UNIT", "NA"],
                "pv": ["UNIT", "NA"],
                "hs": ["UNIT", 2.0],
                "tp": ["UNIT", 8.0],
                "ws": ["UNIT", 15.0],
                "ws_hub": ["UNIT", 20.0],
                "cs": ["UNIT", 1.0],
                "light": ["UNIT", "day"],
                "vessel2_id": ["UNIT", "NA"],
                "vessel2_qt": ["UNIT", "NA"],
                "rov_drone": ["UNIT", "NA"],
                "other_costs": ["UNIT", 0.0],
                "double_shift": ["UNIT", 0],
            }
        )

        # CorrectiveMajor
        df_corr_major = pd.DataFrame(
            {
                "id": ["UNIT", "CMA1"],
                "name": ["UNIT", "Corrective major 1"],
                "tow_to_port": ["UNIT", "yes"],
                "technicians_required": ["UNIT", 3],
                "technician_cost": ["UNIT", 400.0],
                "vessel1_id": ["UNIT", "CTV1"],
                "vessel1_qt": ["UNIT", 1],
                "vessel2_id": ["UNIT", "NA"],
                "vessel2_qt": ["UNIT", "NA"],
                "rov_drone": ["UNIT", "NA"],
                "other_costs": ["UNIT", 0.0],
            }
        )

        # OperationTow
        df_tow = pd.DataFrame(
            {
                "id": ["UNIT", "TOW1"],
                "name": ["UNIT", "Tow op 1"],
                "technicians_required": ["UNIT", 2],
                "technician_cost": ["UNIT", 250.0],
                "vessel1_id": ["UNIT", "CTV1"],
                "vessel2_id": ["UNIT", "NA"],
                "vessel1_qt": ["UNIT", 1],
                "vessel2_qt": ["UNIT", "NA"],
                "other_costs": ["UNIT", 0.0],
                "additional_previous_op_tow": ["UNIT", "NA"],
                "string_disconnection": ["UNIT", False],
                "recommissioning_time": ["UNIT", "NA"],
            }
        )

        # Activities
        df_activities = pd.DataFrame(
            {
                "id": ["UNIT", "ACT1"],
                "op": ["UNIT", "OP1"],
                "name": ["UNIT", "Activity 1"],
                "location": ["UNIT", "site"],
                "wtg_shutdown_dur": ["UNIT", 1.0],
                "wec_shutdown_dur": ["UNIT", 0.0],
                "pv_shutdown_dur": ["UNIT", 0.0],
                "duration": ["UNIT", 4.0],
                "hs": ["UNIT", 2.0],
                "tp": ["UNIT", 8.0],
                "ws": ["UNIT", 15.0],
                "ws_hub": ["UNIT", 20.0],
                "cs": ["UNIT", 1.0],
                "light": ["UNIT", "day"],
            }
        )

        # Failures
        df_failures = pd.DataFrame(
            {
                "id": ["UNIT", "F1"],
                "name": ["UNIT", "Failure 1"],
                "number_of_element_farm": ["UNIT", 10],
                "probability_failure": ["UNIT", 0.01],
                "maintenance_strategy": ["UNIT", "CM1"],
                "level_failure": ["UNIT", 1],
                "op_trigger": ["UNIT", "OP1"],
                "preferred_month": ["UNIT", 1],
                "preferred_day": ["UNIT", 1],
                "avoid_month_correction": ["UNIT", '1,2'],
                "lead_time": ["UNIT", 30],
                "bath_tub": ["UNIT", "no"],
                "fail_variation": ["UNIT", 0.1],
                "potential_shutdown": ["UNIT", "yes"],
                "perc_shutdown": ["UNIT", 25],
                "parts_cost": ["UNIT", 0.0],
            }
        )

        # SA_Scenarios
        df_scenarios = pd.DataFrame(
            {
                "scenarios": ["UNIT", "S1"],
                "january": ["UNIT", 1.0],
                "february": ["UNIT", 1.0],
                "march": ["UNIT", 1.0],
                "april": ["UNIT", 1.0],
                "may": ["UNIT", 1.0],
                "june": ["UNIT", 1.0],
                "july": ["UNIT", 1.0],
                "august": ["UNIT", 1.0],
                "september": ["UNIT", 1.0],
                "october": ["UNIT", 1.0],
                "november": ["UNIT", 1.0],
                "december": ["UNIT", 1.0],
            }
        )

        # -------------------------
        # 2) Fake read_excel returns DF corrected for every sheet
        # -------------------------
        sheets = {
            "Gen_inputs": df_gen,
            "TSA_inputs": df_tsa,
            "SA_inputs": df_stats,
            "C_inputs": df_costs,
            "Gen_WTG": df_wtg,
            "Gen_WEC": df_wec,
            "Gen_PV": df_pv,
            "Gen_Vessels": df_vessels,
            "Vessel_fuel": df_vessels_fuel,
            "Vessel_load_factor": df_vessels_loads,
            "Vessel_fuel_density": df_vessels_density,
            "Gen_ROVs": df_rovs,
            "InspectionSite": df_inspec_site,
            "InspectionPort": df_inspec_port,
            "CorrectiveMinor": df_corr_minor,
            "CorrectiveMajor": df_corr_major,
            "OperationTow": df_tow,
            "Activities": df_activities,
            "SA_Failures": df_failures,
            "SA_Scenarios": df_scenarios,
        }

        def fake_read_excel(*args, **kwargs):
            sheet = kwargs.get("sheet_name")
            if sheet in sheets:
                return sheets[sheet]
            raise ValueError(f"Worksheet named '{sheet}' not found")

        mock_read_excel.side_effect = fake_read_excel

        yaml_safe = YAML(typ="safe")

        # -------------------------
        # 3) Esecution and verifications
        # -------------------------
        with tempfile.TemporaryDirectory() as tmpdir:
            excel_to_yaml_module.excel_to_yaml(
                file_excel="dummy.xlsx",
                out_dir=tmpdir,
            )

            expected_files = [
                "inputs_gen.yaml",
                "inputs_tseries.yaml",
                "inputs_stats.yaml",
                "inputs_costs.yaml",
                "wtg.yaml",
                "wec.yaml",
                "pv.yaml",
                "vessels.yaml",
                "vessels_fuels.yaml",
                "vessels_loads.yaml",
                "vessels_densities.yaml",
                "rovs.yaml",
                "operations_inspections_site.yaml",
                "operations_inspections_port.yaml",
                "operations_corrective_minor.yaml",
                "operations_corrective_major.yaml",
                "operations_tow.yaml",
                "operations_activities.yaml",
                "failures.yaml",
                "scenarios.yaml",
            ]

            for fname in expected_files:
                self.assertTrue(
                    os.path.exists(os.path.join(tmpdir, fname)),
                    f"{fname} was not created in the output folder",
                )

            # --- inputs_tseries.yaml ---
            with open(os.path.join(tmpdir, "inputs_tseries.yaml"), "r") as f:
                tseries = yaml_safe.load(f)

            self.assertAlmostEqual(
                tseries["distance to port"]["value"], 10.0
            )  # 10000 m -> 10 km
            self.assertEqual(tseries["distance to port"]["units"], "km")
            self.assertAlmostEqual(
                tseries["time between devices pv"]["value"], 0.5
            )  # 30 min -> 0.5 h
            self.assertEqual(tseries["time between devices pv"]["units"], "hours")
            self.assertEqual(
                tseries["merge vessel"]["value"], ["ctv1", "atv2"]
            )  # lower-case and split

            # --- inputs_stats.yaml ---
            with open(os.path.join(tmpdir, "inputs_stats.yaml"), "r") as f:
                stats = yaml_safe.load(f)

            self.assertEqual(stats["lifetime"]["value"], 25)
            self.assertEqual(stats["lifetime"]["units"], "years")
            self.assertEqual(stats["start year"]["value"], 2025)
            self.assertEqual(stats["start month"]["value"], 2)
            # percentiles ordered
            self.assertEqual(stats["percentiles"]["value"], [25, 50, 75])

            # --- inputs_costs.yaml ---
            with open(os.path.join(tmpdir, "inputs_costs.yaml"), "r") as f:
                costs = yaml_safe.load(f)

            self.assertAlmostEqual(costs["fuel cost hfo"]["value"], 100.0)
            self.assertEqual(costs["fuel cost hfo"]["units"], "euros/ton")
            self.assertAlmostEqual(costs["fuel cost mgo"]["value"], 200.0)
            self.assertEqual(costs["vessel cost year"]["units"], "euros")
            self.assertTrue(costs["merge"]["value"])
            self.assertEqual(costs["time between merge"]["value"], 5)
            self.assertEqual(costs["electricity price wt"]["value"], 55.0)
            self.assertEqual(costs["technicians year"]["value"], 7000.0)

            # --- wtg.yaml ---
            with open(os.path.join(tmpdir, "wtg.yaml"), "r") as f:
                wtg = yaml_safe.load(f)

            self.assertEqual(wtg["devices"]["value"], 10)
            # rated power rest in MW
            self.assertAlmostEqual(wtg["rated power"]["value"], 3.0)
            self.assertEqual(wtg["rated power"]["units"], "MW")
            # cut-off in km/h -> m/s (25 * 0.2778)
            self.assertAlmostEqual(wtg["cut-off"]["value"], round(25.0 * 0.2778, 3))
            self.assertEqual(wtg["hub height"]["value"], 100.0)  # 10000 cm -> 100 m
            self.assertEqual(
                wtg["power curve file"]["value"], "C:/curve/wtg.csv"
            )

            # --- wec.yaml ---
            with open(os.path.join(tmpdir, "wec.yaml"), "r") as f:
                wec = yaml_safe.load(f)

            self.assertEqual(wec["devices"]["value"], 5)
            self.assertAlmostEqual(wec["rated power"]["value"], 1.5)
            self.assertEqual(wec["rated power"]["units"], "MW")
            self.assertEqual(wec["number of strings"]["value"], 2)

            # --- pv.yaml ---
            with open(os.path.join(tmpdir, "pv.yaml"), "r") as f:
                pv = yaml_safe.load(f)

            self.assertEqual(pv["devices"]["value"], 10)
            self.assertAlmostEqual(pv["rated power"]["value"], 500.0)
            self.assertEqual(pv["rated power"]["units"], "kW")
            self.assertEqual(pv["degradation"]["value"], 0.5)
            self.assertEqual(pv["max failure module"]["value"], 10)

            # --- vessels.yaml ---
            with open(os.path.join(tmpdir, "vessels.yaml"), "r") as f:
                vessels = yaml_safe.load(f)

            self.assertEqual(len(vessels), 1)  # skip row UNIT
            self.assertEqual(vessels[0]["id"], "CTV1")
            # "NA" rimossi
            self.assertNotIn("notes", vessels[0])

            # --- failures.yaml ---
            with open(os.path.join(tmpdir, "failures.yaml"), "r") as f:
                failures = yaml_safe.load(f)

            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0]["id"], "F1")
            self.assertEqual(failures[0]["maintenance_strategy"], "CM1")

            # --- scenarios.yaml ---
            with open(os.path.join(tmpdir, "scenarios.yaml"), "r") as f:
                scenarios = yaml_safe.load(f)

            self.assertEqual(len(scenarios), 1)
            self.assertEqual(scenarios[0]["scenarios"], "S1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
