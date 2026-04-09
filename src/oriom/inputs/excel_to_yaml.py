import pandas as pd
import math as mt
import os
import platform
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq as CS
import logging


def excel_to_yaml(
        file_excel:str,
        out_dir:str,
        section: str=None
):

    # Define Excel file location
    FILE_EXCEL = file_excel
    # Denine excel sheets names
    INPUTS_SHEET_GENERAL = 'Gen_inputs'
    INPUTS_SHEET_TSERIES = 'TSA_inputs'
    INPUTS_SHEET_STATS = 'SA_inputs'
    INPUTS_SHEET_COST = 'C_inputs'
    WTG_SHEET = 'Gen_WTG'
    WEC_SHEET = 'Gen_WEC'
    PV_SHEET = 'Gen_PV'
    VESSELS_SHEET = 'Gen_Vessels'
    VESSELS_CONSUMPTION = 'Vessel_fuel'
    VESSELS_LOAD_FACTOR = 'Vessel_load_factor'
    VESSELS_FUEL_DENSITY = 'Vessel_fuel_density'
    ROV_SHEET = 'Gen_ROVs'
    OPERATIONS_INSPEC_SITE_SHEET = 'InspectionSite'
    OPERATIONS_INSPEC_PORT_SHEET = 'InspectionPort'
    OPERATIONS_CORR_MAJOR_SHEET = 'CorrectiveMajor'
    OPERATIONS_CORR_MINOR_SHEET = 'CorrectiveMinor'
    OPERATIONS_TOW_SHEET = 'OperationTow'
    ACTIVITIES_SHEET = 'Activities'
    FAILURES_SHEET = 'SA_Failures'
    SCENARIO_SHEET = 'SA_Scenarios'
    # Define outputs directory
    OUT_DIR = out_dir

    def inputs_general():
        inputs = {}
        # Default values
        inputs["consider double shifts"] = {"value" : False, "units": None}
        inputs["number_runs"] = {"value": 1, "units": None}

        # Gets inputs from an excel spreadsheet
        try:
            df_inputs = pd.read_excel(FILE_EXCEL, sheet_name=INPUTS_SHEET_GENERAL)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')
        df_inputs.columns = df_inputs.columns.str.lower()
        df_inputs.dropna(axis='rows', how='any', inplace=True)

        # Verify inputs in df_inputs and organize them in a dictionary
        for _, row in df_inputs.iterrows():
            name = row['input'].lower()
            value = row['value']
            try:
                if mt.isnan(float(value)) is True:
                    continue
            except ValueError:
                pass

            if 'use' in name and 'previous' in name and ('path' in name or 'dir' in name):
                inputs["previous run dir"] = {
                        "value": str(value),
                        "units": None
                }
            elif ('previous' in name and ('tseries' in name or ('time' in name and 'series' in name))):
                inputs["consider tseries"] = {
                        "value": bool(value),
                        "units": None
                }
            elif ('number' in name and 'runs' in name):
                inputs["number_runs"] = {
                        "value": int(value),
                        "units": None
                }
            elif ('overwrite' in name and 'previous' in name):
                inputs["overwrite"] = {
                        "value": bool(value),
                        "units": None
                }
            elif ('double' in name and 'shift' in name):
                inputs["consider double shifts"] = {
                        "value": bool(value),
                        "units": None
                }
            elif ('log' in name and 'file' in name):
                inputs["logevents file"] = {
                        "value": str(value),
                        "units": None
                }
            elif ('fail' in name and 'file' in name):
                inputs["failureevent file"] = {
                        "value": str(value),
                        "units": None
                }
            else:
                _w = 'ExcelToYAML.Inputs.General: input "%s" not recognized. Ignored.' % row['input']
                logging.warning(_w)
        _i = 'ExcelToYAML: inputs read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_inputs = os.path.join(OUT_DIR, 'inputs_gen.yaml')
        f_inputs = open(f_inputs, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        yaml.dump(inputs, f_inputs)
        f_inputs.close()

    def inputs_tseries():
        inputs = {}
        # Default values
        inputs["surface roughness"] = {"value" : 0.0002, "units": 'metres'}
        inputs["metocean ws height"] = {"value": 10.0, "units" : 'metres'}
        inputs["max wait"] = {"value": 8.0, "units": 'hours'}
        inputs["montecarlo percentage"] = {"value": 0.3, "units": None}
        inputs["shift duration"] = {"value": 12, "units": 'hours'}
        inputs["failure scenario"] = {"value": 0, "units": None}
        inputs["metocean file location tow"] = {}

        # Gets inputs from an excel spreadsheet
        try:
            df_inputs = pd.read_excel(FILE_EXCEL, sheet_name=INPUTS_SHEET_TSERIES)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')
        df_inputs.columns = df_inputs.columns.str.lower()
        df_inputs.dropna(axis='rows', how='any', inplace=True)

        # Verify inputs in df_inputs and organize them in a dictionary
        for _, row in df_inputs.iterrows():
            name = row['input'].lower()
            value = row['value']
            units = str(row['units'])
            if 'site' in name and 'latitude' in name:
                if 'degree' not in units.lower():
                    raise NameError('Units "%s" not recognized for Site Latitude input.' % units)
                inputs["site latitude"] = {"value": float(value), "units": str(units)}

            elif 'site' in name and 'longitude' in name:
                if 'degree' not in units.lower():
                    raise NameError('Units "%s" not recognized for Site Longitude input.' % units)
                inputs["site longitude"] = {"value": float(value), "units": str(units)}

            elif 'metocean' in name and 'file' in name and 'tow' not in name:
                value = str(value)
                if platform.system().lower() != 'windows':
                     value = value.replace('\\', '/')
                inputs["metocean file location"] = {"value": value, "units": None}

            elif 'metocean' in name and 'file' in name and 'tow' in name and 'number' in name:
                inputs[f"metocean tow file number"] = {"value": int(value), "units": None}

            elif 'metocean' in name and 'file' in name and 'tow' in name and 'number' not in name:
                value = str(value)
                i = name[-1]
                if platform.system().lower() != 'windows':
                    value = value.replace('\\', '/')
                inputs[f"metocean file location tow{i}"] = {"value": value, "units": None}

            elif 'metocean' in name and any(word in name for word in ['windspeed', 'wind speed', 'ws']) and 'height' in name:
                inputs["metocean ws height"] = {"value": float(value), "units": str(units)}

            elif 'surface' in name and 'roughness' in name:
                inputs["surface roughness"] = {"value": float(value), "units": str(units)}

            elif 'distance' in name and 'port' in name:
                if units.lower() == 'km' or 'kilometer' in units.lower() or 'kilometre' in units.lower():
                    units = 'km'
                elif units.lower() == 'm':
                    value = value / 1000
                    units = 'km'
                else:
                    raise NameError('Units "%s" not recognized for Distance to Port input.' % units)
                inputs["distance to port"] = {"value": float(value), "units": str(units)}

            elif 'time' in name and 'between' in name and 'devices' in name and 'pv' in name:
                if 'hour' in units.lower():
                    units = 'hours'
                elif 'minute' in units.lower():
                    value = value / 60
                    units = 'hours'
                else:
                    raise NameError('Units "%s" not recognized for Transit Time Between Devices pv input.' % units)
                inputs["time between devices pv"] = {"value": float(value), "units": str(units)}

            elif 'time' in name and 'between' in name and 'devices' in name and 'wt' in name:
                if 'hour' in units.lower():
                    units = 'hours'
                elif 'minute' in units.lower():
                    value = value / 60
                    units = 'hours'
                else:
                    raise NameError('Units "%s" not recognized for Transit Time Between Devices input.' % units)
                inputs["time between devices wt"] = {"value": float(value), "units": str(units)}

            elif 'time' in name and 'between' in name and 'devices' in name and 'wec' in name:
                if 'hour' in units.lower():
                    units = 'hours'
                elif 'minute' in units.lower():
                    value = value / 60
                    units = 'hours'
                else:
                    raise NameError('Units "%s" not recognized for Transit Time Between Devices input.' % units)
                inputs["time between devices wec"] = {"value": float(value), "units": str(units)}

            elif 'max' in name and 'wow' in name and 'between' in name and 'activities' in name:
                if 'hour' not in units.lower():
                    raise NameError('Units "%s" not recognized for Max WoW between activities input.' % units)
                inputs["max wait"] = {"value": int(value), "units": str(units)}

            elif 'timeseries' in name and 'analysed' in name and 'percent' in name:
                inputs["montecarlo percentage"] = {"value": float(value), "units": None}

            elif 'failure' in name and 'scenario' in name:
                inputs["failure scenario"] = {"value": int(value), "units": None}

            elif 'length' in name and 'export' in name:
                inputs["length export cable"] = {"value": float(value), "units": str(units)}

            elif 'shift' in name and 'duration' in name:
                inputs["shift duration"] = {"value": int(value), "units": str(units)}

            elif 'double' in name and 'shifts' in name:
                inputs["double shifts"] = {"value": (value), "units": str(units)}

            elif 'merge' in name and 'vessel' in name:
                values_list = [v.strip().lower() for v in str(value).split(',')]
                inputs["merge vessel"] = {"value": values_list, "units": str(units)}

            else:
                _w = 'ExcelToYAML.Inputs.TimeSeries: input "%s" not recognized. Ignored.' % row['input']
                logging.warning(_w)
        _i = 'ExcelToYAML.Inputs.TimeSeries: inputs read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)
        if not inputs[f"metocean file location tow"]:
            inputs.pop("metocean file location tow", None)
        f_inputs = os.path.join(OUT_DIR, 'inputs_tseries.yaml')
        f_inputs = open(f_inputs, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        yaml.dump(inputs, f_inputs)
        f_inputs.close()

    def inputs_stats():
        inputs = {}
        # Default values
        inputs["percentile main"] = {"value": 50, "units" : None}
        inputs["percentiles"] = {"value": [], "units" : None}
        inputs["period infant mortality"] = {"value": 0, "units" : 'years'}
        inputs["period wear out"] = {"value": 0, "units" : 'years'}
        inputs["failure ratio"]  = {"value": 0, "units" : None}
        inputs["failure ratio sensitivity"]  = {"value": 1, "units" : None}
        inputs["percentage shutdown"] = {"value" : None, "units" : "%"}

        # Gets inputs from an excel spreadsheet
        try:
            df_inputs = pd.read_excel(FILE_EXCEL, sheet_name=INPUTS_SHEET_STATS)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')
        df_inputs.columns = df_inputs.columns.str.lower()

        # Drop useless rows
        df_inputs = df_inputs[~pd.isnull(df_inputs['input'])]
        df_inputs.dropna(axis='columns', how='all', inplace=True)
        # Verify inputs in df_inputs and organize them in a dictionary
        for _, row in df_inputs.iterrows():
            name = row['input'].lower()
            value = row['value']
            units = str(row['units'])
            if 'project' in name and 'lifetime' in name:
                if units.lower() != 'years':
                    raise NameError('Units "%s" not recognized for Project Lifetime input.' % units)
                inputs["lifetime"] = {"value": int(value), "units": str(units)}

            elif 'start' in name and 'year' in name and 'project' in name:
                inputs['start year'] = {"value": int(value), "units": None}
            elif 'start' in name and 'month' in name and 'project' in name:
                inputs['start month'] = {"value": int(value), "units": None}

            elif 'day ' in name and 'scheduling' in name and 'operation' in name:
                inputs['last day operation'] = {"value": int(value), "units": None}

            elif 'percentile' in name and 'main' in name:
                inputs['percentile main'] = {"value": int(value), "units": None}
                inputs['percentiles']["value"].append(int(value))
                inputs['percentiles']["value"].sort()
            elif 'percentile' in name and '1' in name:
                inputs['percentiles']["value"].append(int(value))
                inputs['percentiles']["value"].sort()
            elif 'percentile' in name and '2' in name:
                inputs['percentiles']["value"].append(int(value))
                inputs['percentiles']["value"].sort()

            elif 'infant' in name and 'mortality' in name:
                if units.lower() != 'years':
                    raise NameError('Units "%s" not recognized for Period of Infant Mortality input.' % units)
                if pd.isna(value) or value == 0:
                    inputs['period infant mortality'] = {"value": 0, "units": units}
                else:
                    inputs['period infant mortality'] = {"value": int(value), "units": units}
            elif 'wear' in name and 'out' in name:
                if units.lower() != 'years':
                    raise NameError('Units "%s" not recognized for Period of Wear Out input.' % units)
                if pd.isna(value) or value == 0:
                    inputs['period wear out'] = {"value": 0, "units": units}
                else:
                    inputs['period wear out'] = {"value": int(value), "units": units}
            elif 'fail' in name and 'ratio' in name and not 'sensitivity' in name:
                if pd.isna(value) or value == 0:
                    inputs['failure ratio'] = {"value": 0, "units": None}
                else:
                    inputs['failure ratio'] = {"value": float(value), "units": None}
            elif 'fail' in name and 'ratio' in name and 'sensitivity' in name:
                if pd.isna(value) or value == 0:
                    inputs['failure ratio sensitivity'] = {"value": 1, "units": None}
                else:
                    inputs['failure ratio sensitivity'] = {"value": float(value), "units": None}
            elif 'percentage' in name and 'shutdown' in name:
                if pd.isna(value) is True:
                    inputs['percentage shutdown'] = {'value' : None, 'units' : '%'}
                else:
                    inputs['percentage shutdown'] = {'value' : int(value), 'units' : '%'}
            else:
                _w = 'ExcelToYAML.Inputs.Stats: input "%s" not recognized. Ignored.' % row['input']
                logging.warning(_w)
        _i = 'ExcelToYAML.Inputs.Stats: inputs read from an Excel file: "%s".' % file_excel
        logging.info(_i)

        f_inputs = os.path.join(OUT_DIR, 'inputs_stats.yaml')
        f_inputs = open(f_inputs, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        yaml.dump(inputs, f_inputs)
        f_inputs.close()

    def inputs_costs():
        inputs = {}
        # Default values
        inputs["vessel cost year"] = {"value" : 0.0, "units": 'euros'}
        inputs["port cost day"] = {"value": 0.0, "units": 'euros'}
        inputs["merge"] = {"value": False, "units": ""}
        inputs["time between merge"] = {"value": None, "units": 'days'}

        # Gets inputs from an excel spreadsheet
        try:
            df_inputs = pd.read_excel(FILE_EXCEL, sheet_name=INPUTS_SHEET_COST)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')
        df_inputs.columns = df_inputs.columns.str.lower()
        df_inputs.dropna(axis='rows', how='any', inplace=True)

        # Verify inputs in df_inputs and organize them in a dictionary
        for _, row in df_inputs.iterrows():
            name = row['input'].lower()
            value = row['value']
            units = str(row['units'])
            if 'fuel' in name:
                if (
                        units.lower() == 'euros/ton' or
                        units.lower() == 'euro/ton' or
                        units.lower() == 'euros per ton' or
                        units.lower() == 'euro per ton'
                ):
                    units = 'euros/ton'
                else:
                    raise NameError('Units "%s" not recognized for fuel cost inputs.' % units)

                if 'hfo' in name:
                    inputs["fuel cost hfo"] = {"value": float(value), "units": str(units)}
                elif 'mgo' in name:
                    inputs["fuel cost mgo"] = {"value": float(value), "units": str(units)}
                elif 'mdo' in name:
                    inputs["fuel cost mdo"] = {"value": float(value), "units": str(units)}
                else:
                    logging.warning('Inputs.Cost: fuel type "%s" not recognized. Ignored.' % row['input'])

            elif 'vessel' in name and 'year' in name:
                if units.lower() != 'euros':
                    raise NameError('Units "%s" not recognized for Dedicated Vessel cost input.' % units)
                inputs["vessel cost year"] = {"value": float(value), "units": str(units)}

            elif ('port' in name or 'terminal' in name) and ('day' in name or 'daily' in name):
                if units.lower() != 'euros':
                    raise NameError('Units "%s" not recognized for Port Terminal Daily cost input.' % units)
                inputs["port cost day"] = {"value": float(value), "units": str(units)}
            elif ('port' in name or 'terminal' in name) and ('annual' in name or 'year' in name):
                if units.lower() != 'euros':
                    raise NameError('Units "%s" not recognized for Dedicated Port Terminal annual cost input.' % units)
                inputs["port cost annual"] = {"value": float(value), "units": str(units)}
            elif ('try' in name) and ('merge' in name) and ('operations' in name):
                inputs["merge"] = {"value": bool(value), "units": None}
            elif ('time' in name) and ('operations' in name) and ('merge' in name):
                if pd.isna(value) is True:
                    inputs["time between merge"] = {"value": None, "units": str(units)}
                else:
                    inputs["time between merge"] = {"value": int(value), "units": str(units)}
            elif 'insurance' in name and ('annual' in name or 'year' in name):
                if units.lower() != 'euros':
                    raise NameError('Units "%s" not recognized for a Insurance annual cost input.' % units)
                inputs["insurance annual"] = {"value": float(value), "units": str(units)}
            elif 'electricity' in name and 'price' in name:
                if units.lower() != 'euros/mwh':
                    raise NameError('Units "%s" not recognized for the Electricity Selling Price input.' % units)
                if all(tech not in name for tech in ['wt', 'pv', 'wec']):
                    inputs["electricity price"] = {"value": float(value), "units": str(units)}
                elif 'pv' in name:
                    inputs["electricity price pv"] = {"value": float(value), "units": str(units)}
                elif 'wt' in name:
                    inputs["electricity price wt"] = {"value": float(value), "units": str(units)}
                elif 'wec' in name:
                    inputs["electricity price wec"] = {"value": float(value), "units": str(units)}
                else:
                    raise NameError('tech "%s" not recognized for the Electricity Selling Price input.' % name)
            elif 'technicians' in name and ('annual' in name or 'year' in name):
                if units.lower() != 'euros':
                    raise NameError('Units "%s" not recognized for a Technicians annual cost input.' % units)
                inputs["technicians year"] = {"value": float(value), "units": str(units)}
            else:
                logging.warning('Inputs.Cost: input "%s" not recognized. Ignored.' % row['input'])
        logging.info('Inputs.Cost: inputs read from an Excel file: "%s".' % file_excel)

        f_inputs = os.path.join(OUT_DIR, 'inputs_costs.yaml')
        f_inputs = open(f_inputs, 'w')
        yaml = YAML()
        yaml.indent(mapping=4)
        yaml.dump(inputs, f_inputs)
        f_inputs.close()

    def general_wtg():
        wtg = {}

        # Gets WTG from an excel spreadsheet
        try:
            df_wtg = pd.read_excel(FILE_EXCEL, sheet_name=WTG_SHEET)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')
        df_wtg.columns = df_wtg.columns.str.lower()
        df_wtg.dropna(axis='rows', how='any', inplace=True)

        # Verify WTG in df_wtg and organize them in a dictionary
        for _, row in df_wtg.iterrows():
            name = row['input'].lower()
            value = row['value']
            units = str(row['units']).lower()
            if 'devices' in name:
                wtg["devices"] = {"value": int(value), "units": None}

            elif 'rated' in name and 'power' in name:
                if 'mw' in units and 'device' in units:
                    value = round(value, 3)
                elif 'kw' in units and 'device' in units:
                    value = round(value / 1000, 3)
                elif 'w' in units and 'device' in units:
                    value = round(value / 1000000, 3)
                else:
                    _e = 'Units of "rated power" not recognized. '
                    _e += 'Please use "MW/device", "kW/device" or "W/device".'
                    logging.error('ExcelToYAML.WindTurbineGenerator: ' + _e)
                    raise NameError(_e)
                wtg["rated power"] = {"value": float(value), "units": 'MW'}

            elif 'cut-in' in name:
                if 'm/s' in units:
                    value = round(value, 3)
                elif 'km/h' in units:
                    value = round(value * 0.2778, 3)
                elif 'kn' in units and 'device' in units:
                    value = round(value * 0.5144, 3)
                else:
                    _e = 'Units of "cut-in" not recognized. '
                    _e += 'Please use "m/s", "km/h" or "knots".'
                    logging.error('ExcelToYAML.WindTurbineGenerator: ' + _e)
                    raise NameError(_e)
                wtg["cut-in"] = {"value": float(value), "units": 'm/s'}

            elif 'cut-off' in name:
                if 'm/s' in units:
                    value = round(value, 3)
                elif 'km/h' in units:
                    value = round(value * 0.2778, 3)
                elif 'kn' in units and 'device' in units:
                    value = round(value * 0.5144, 3)
                else:
                    _e = 'Units of "cut-off" not recognized. '
                    _e += 'Please use "m/s", "km/h" or "knots".'
                    logging.error('ExcelToYAML.WindTurbineGenerator: ' + _e)
                    raise NameError(_e)
                wtg["cut-off"] = {"value": float(value), "units": 'm/s'}

            elif 'hub' in name and 'height' in name:
                if 'cm' in units:
                    value = round(value / 100, 3)
                elif 'm' in units:
                    value = round(value, 3)
                else:
                    _e = 'Units of "hub height" not recognized. '
                    _e += 'Please use "m" or "cm".'
                    logging.error('ExcelToYAML.WindTurbineGenerator: ' + _e)
                    raise NameError(_e)
                wtg["hub height"] = {"value": float(value), "units": 'm'}

            elif 'curve' in name and 'file' in name:
                value = str(value)
                if platform.system().lower() != 'windows':
                     value = value.replace('\\', '/')
                wtg["power curve file"] = {"value": value, "units": None}

            elif 'moorings' in name:
                value = int(value)
                wtg["moorings per wtg"] = {"value": value, "units": None}

            elif 'strings' in name and not 'connector' in name:
                value = int(value)
                wtg["number of strings"] = {"value": value, "units": None}

            elif 'strings' in name and 'connector' in name:
                value = int(value)
                wtg["n strings to connector"] = {"value": value, "units": None}
            
            elif 'substations' in name:
                value = int(value)
                wtg["number of substations"] = {"value": value, "units": None}

            elif 'export' in name and 'cable' in name:
                value = int(value)
                wtg["number export cables"] = {"value": value, "units": None}

            elif "number" in name and "device" in name and "port" in name and "stored" not in name:
                value = int(value)
                wtg[name] = {"value": value, "units": None}

            elif "number" in name and "device" in name and "port" in name and "stored" in name:
                value = int(value)
                wtg[name] = {"value": value, "units": None}

            elif 'layout' in name:
                value = int(value)
                wtg["layout type"] = {"value": value, "units": None}

            elif 'tow' in name and 'string' in name:
                value = bool(value)
                wtg["tow string shutdown"] = {"value": value, "units": None}

            else:
                _w = 'ExcelToYAML.WindTurbineGenerator: input "%s" not recognized. Ignored.' % row['input']
                logging.warning(_w)
        _i = 'ExcelToYAML: WTG read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_wtg = os.path.join(OUT_DIR, 'wtg.yaml')
        f_wtg = open(f_wtg, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        yaml.dump(wtg, f_wtg)
        f_wtg.close()

    def general_wec():
        wec = {}

        # Gets WEC from an excel spreadsheet
        try:
            df_wec = pd.read_excel(FILE_EXCEL, sheet_name=WEC_SHEET)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')
        df_wec.columns = df_wec.columns.str.lower()
        df_wec.dropna(axis='rows', how='any', inplace=True)

        # Verify WEC in df_wec and organize them in a dictionary
        for _, row in df_wec.iterrows():
            name = row['input'].lower()
            value = row['value']
            units = str(row['units']).lower()
            if 'devices' in name:
                wec["devices"] = {"value": int(value), "units": None}

            elif 'rated' in name and 'power' in name:
                if 'mw' in units and 'device' in units:
                    value = round(value, 3)
                elif 'kw' in units and 'device' in units:
                    value = round(value / 1000, 3)
                elif 'w' in units and 'device' in units:
                    value = round(value / 1000000, 3)
                else:
                    _e = 'Units of "rated power" not recognized. '
                    _e += 'Please use "MW/device", "kW/device" or "W/device".'
                    logging.error('ExcelToYAML.WaveEnergyConverter: ' + _e)
                    raise NameError(_e)
                wec["rated power"] = {"value": float(value), "units": 'MW'}

            elif 'matrix' in name and 'file' in name:
                value = str(value)
                if platform.system().lower() != 'windows':
                     value = value.replace('\\', '/')
                wec["power matrix file"] = {"value": value, "units": None}

            elif 'strings' in name:
                value = int(value)
                wec["number of strings"] = {"value": value, "units": None}

            elif 'substations' in name:
                value = int(value)
                wec["number of substations"] = {"value": value, "units": None}

            elif 'export' in name and 'cable' in name:
                value = int(value)
                wec["number export cables"] = {"value": value, "units": None}

            elif "number" in name and "device" in name and "port" in name and "stored" not in name:
                value = int(value)
                wec[name] = {"value": value, "units": None}

            elif "number" in name and "device" in name and "port" in name and "stored" in name:
                value = int(value)
                wec[name] = {"value": value, "units": None}

            elif 'layout' in name:
                value = int(value)
                wec["layout type"] = {"value": value, "units": None}

            elif 'tow' in name and 'string' in name:
                value = bool(value)
                wec["tow string shutdown"] = {"value": value, "units": None}

            else:
                _w = 'ExcelToYAML.WaveEnergyConverter: input "%s" not recognized. Ignored.' % row['input']
                logging.warning(_w)
        _i = 'ExcelToYAML: WEC read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_wec = os.path.join(OUT_DIR, 'wec.yaml')
        f_wec = open(f_wec, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        yaml.dump(wec, f_wec)
        f_wec.close()

    def general_pv():
        pv = {}

        # Gets PV from an excel spreadsheet
        try:
            df_pv = pd.read_excel(FILE_EXCEL, sheet_name=PV_SHEET)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')
        df_pv.columns = df_pv.columns.str.lower()
        df_pv.dropna(axis='rows', how='any', inplace=True)

        # Verify PV in df_pv and organize them in a dictionary
        for _, row in df_pv.iterrows():
            name = row['input'].lower()
            value = row['value']
            units = str(row['units']).lower()
            if 'devices' in name and 'power' not in name:
                pv["devices"] = {"value": int(value), "units": None}

            elif 'device' in name and 'power' in name:
                if 'kw' in units and 'device' in units:
                    value = round(value, 3)
                elif 'w' in units and 'device' in units:
                    value = round(value / 1000, 3)
                else:
                    _e = 'Units of "rated power" not recognized. '
                    _e += 'Please use "kW/device" or "W/device".'
                    logging.error('ExcelToYAML.PVProduction: ' + _e)
                    raise NameError(_e)
                pv["rated power"] = {"value": float(value), "units": 'kW'}

            elif 'curve' in name and 'file' in name:
                value = str(value)
                if platform.system().lower() != 'windows':
                     value = value.replace('\\', '/')
                pv["power curve file"] = {"value": value, "units": None}

            elif 'strings' in name:
                value = int(value)
                pv["number of strings"] = {"value": value, "units": None}

            elif 'inverters' in name:
                value = int(value)
                pv["number of inverters"] = {"value": value, "units": None}

            elif 'transformers' in name:
                value = int(value)
                pv["number of mv transformers"] = {"value": value, "units": None}

            elif 'substations' in name:
                value = int(value)
                pv["number of substations"] = {"value": value, "units": None}

            elif 'export' in name and 'cable' in name:
                value = int(value)
                pv["number export cables"] = {"value": value, "units": None}

            elif 'island' in name and 'array' in name:
                value = int(value)
                pv["number island per array"] = {"value": value, "units": None}

            elif "number" in name and "device" in name and "port" in name and "stored" not in name:
                value = int(value)
                pv[name] = {"value": value, "units": None}

            elif "number" in name and "device" in name and "port" in name and "stored" in name:
                value = int(value)
                pv[name] = {"value": value, "units": None}

            elif 'degradation' in name:
                value = round(value, 2)
                pv["degradation"] = {"value": float(value), "units": None}

            elif 'layout' in name:
                value = int(value)
                pv["layout type"] = {"value": value, "units": None}

            elif 'max failure module' in name:
                value = int(value)
                pv["max failure module"] = {"value": value, "units": None}

            elif 'tow' in name and 'string' in name:
                value = bool(value)
                pv["tow string shutdown"] = {"value": value, "units": None}

            else:
                _w = 'ExcelToYAML.PVProduction: input "%s" not recognized. Ignored.' % row['input']
                logging.warning(_w)
        _i = 'ExcelToYAML: PV read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_pv = os.path.join(OUT_DIR, 'pv.yaml')
        f_pv = open(f_pv, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        yaml.dump(pv, f_pv)
        f_pv.close()

    def vessels(units_row: bool=True):
        vessels = []

        # Gets Vessels from an excel spreadsheet
        try:
            df_vessels = pd.read_excel(FILE_EXCEL, sheet_name=VESSELS_SHEET)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')

        #df_vessels.dropna(axis=1, how='all', inplace=True)
        df_vessels = df_vessels[df_vessels['id'].notna()]
        df_vessels.fillna('NA', inplace=True)
        df_vessels.columns = df_vessels.columns.str.lower()
        columns_mandatory = ['id', 'type', 'speed_transit', 'crew_capacity','overnight']
        if any([column not in df_vessels.columns for column in columns_mandatory]) is True:
            _e = '"id", "type", "speed_transit", "crew_capacity", "overnight" are mandatory columns'
            logging.error('Vessel: ' + _e)
            raise NameError(_e)

        # Verify vessels in df_vessels and organize them in a dictionary
        for idx, row in df_vessels.iterrows():
            if units_row is True and idx == 0:
                # Skip first row
                continue
            vessels.append({
                    "id": row['id'],
                    "type": row['type'],
                    "list_name": row['list_name'],
                    "number_vessels": row['number_vessels'],
                    "speed_transit": row['speed_transit'],
                    "speed_towing": row['speed_towing'],
                    "daily_charter": row['daily_charter'],
                    "mother_vessel": row['mother_vessel'],
                    "annual_contract": row['annual_contract'],
                    "n_ves_annual_contract": row['n_ves_annual_contract'],
                    "months_contract": row['months_contract'],
                    "monthly_contract_cost": row['monthly_contract_cost'],
                    "n_ves_monthly_contract": row['n_ves_monthly_contract'],
                    "mobilisation_time": row['mobilisation_time'],
                    "mobilisation_cost": row['mobilisation_cost'],
                    "crew_capacity": row['crew_capacity'],
                    "overnight": row['overnight'],
                    "num_berths": row['num_berths'],
                    "power": row['power'],
                    "fuel_type": row['fuel_type'],
                    "fuel_cons_transit": row['fuel_cons_transit'],
                    "fuel_cons_maneuver": row['fuel_cons_maneuver'],
                    "fuel_cons_standby": row['fuel_cons_standby'],
                    "notes": row['notes']
            })

        # Drop nan values
        for idx, vessel in enumerate(vessels):
            vessels[idx] = {
                    k: vessel[k]
                    for k in vessel
                    if vessel[k] != 'NA'
            }

        _i = 'ExcelToYAML: Vessels read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_vessels = os.path.join(OUT_DIR, 'vessels.yaml')
        f_vessels = open(f_vessels, 'w')
        yaml = YAML()
        yaml.indent(mapping=4)
        vessels = CS(vessels)
        for v in range(1, len(vessels)):
            vessels.yaml_set_comment_before_after_key(v, before='\n')
        yaml.dump(vessels, f_vessels)
        f_vessels.close()

    def vessels_fuel(units_row: bool=True):
        fuels = []

        # Gets Fuels data from an excel spreadsheet
        try:
            df_fuels = pd.read_excel(FILE_EXCEL, sheet_name=VESSELS_CONSUMPTION)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')

        df_fuels.dropna(axis=1, how='all', inplace=True)
        df_fuels.columns = df_fuels.columns.str.lower()

        # Verify fuel in df_fuels and organize them in a dictionary
        for idx, row in df_fuels.iterrows():
            if units_row is True and idx == 0:
                # Skip first row
                continue
            fuels.append({
                    "vessel": row['vessel'],
                    "fuel type": row['fuel type'],
                    "rated power": row['rated power'],
                    "sfoc": row['sfoc']
            })

        _i = 'ExcelToYAML: Fuels read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_fuels = os.path.join(OUT_DIR, 'vessels_fuels.yaml')
        f_fuels = open(f_fuels, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        fuels = CS(fuels)
        for f in range(1, len(fuels)):
            fuels.yaml_set_comment_before_after_key(f, before='\n')
        yaml.dump(fuels, f_fuels)
        f_fuels.close()

    def vessels_loads():
        loads = []

        # Gets Load Factors data from an excel spreadsheet
        try:
            df_loads = pd.read_excel(FILE_EXCEL, sheet_name=VESSELS_LOAD_FACTOR)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')

        df_loads.dropna(axis=1, how='all', inplace=True)
        df_loads.columns = df_loads.columns.str.lower()

        # Verify load factors in df_loads and organize them in a dictionary
        for _, row in df_loads.iterrows():
            loads.append({
                    "operation": row['operation'],
                    "load_factor": row['load_factor']
            })

        _i = 'ExcelToYAML: Load factors read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_loads = os.path.join(OUT_DIR, 'vessels_loads.yaml')
        f_loads = open(f_loads, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        loads = CS(loads)
        for l in range(1, len(loads)):
            loads.yaml_set_comment_before_after_key(l, before='\n')
        yaml.dump(loads, f_loads)
        f_loads.close()

    def vessels_densities():
        densities = []

        # Gets Fuel densities data from an excel spreadsheet
        try:
            df_densities = pd.read_excel(FILE_EXCEL, sheet_name=VESSELS_FUEL_DENSITY)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')

        df_densities.dropna(axis=1, how='all', inplace=True)
        df_densities.columns = df_densities.columns.str.lower()

        # Verify fuel densities in df_densities and organize them in a dictionary
        for _, row in df_densities.iterrows():
            densities.append({
                    "fuel": row['fuel'],
                    "density": row['density']
            })

        _i = 'ExcelToYAML: Fuel densities read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_densities = os.path.join(OUT_DIR, 'vessels_densities.yaml')
        f_densities = open(f_densities, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        densities = CS(densities)
        for l in range(1, len(densities)):
            densities.yaml_set_comment_before_after_key(l, before='\n')
        yaml.dump(densities, f_densities)
        f_densities.close()

    def rovs_drones(units_row: bool=True):
        rovs_drones = []

        # Gets ROVs and Drones from an excel spreadsheet
        try:
            df_rovs_drones = pd.read_excel(FILE_EXCEL, sheet_name=ROV_SHEET)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')

        df_rovs_drones.dropna(axis=1, how='all', inplace=True)
        df_rovs_drones = df_rovs_drones[df_rovs_drones['id'].notna()]
        df_rovs_drones.fillna('NA', inplace=True)
        df_rovs_drones.columns = df_rovs_drones.columns.str.lower()
        columns_mandatory = ['id', 'rov name', 'type', 'daily_charter']
        if any([column not in df_rovs_drones.columns for column in columns_mandatory]) is True:
            _e = '"id", "rov name", "type" and "daily_charter" are mandatory columns'
            logging.error('RovDrone: ' + _e)
            raise NameError(_e)

        # Verify ROVs and Drone in df_rovs_drones and organize them in a dictionary
        for idx, row in df_rovs_drones.iterrows():
            if units_row is True and idx == 0:
                # Skip first row
                continue
            rovs_drones.append({
                    "id": row["id"],
                    "name": row["rov name"],
                    "type": row["type"],
                    "daily_charter": row["daily_charter"],
                    "weight": row["weight"],
                    "dimensions": row["dimensions"],
                    "useful_capacity": row["useful_capacity"],
                    "speed_transit": row["speed_transit"],
                    "battery_capacity": row["battery_capacity"],
                    "recharging_duration": row["recharging_duration"],
                    "max_distance": row["max_distance"],
                    "avg_autonomy": row["avg_autonomy"],
                    "on_site": row["on_site"],
                    "support_vessel": row["support_vessel"],
                    "nr_technicians": row["nr_technicians"],
                    "ws_max": row["ws_max"],
                    "hs_max": row["hs_max"],
                    "daylight": row["daylight"],
                    "precipitation_max": row["precipitation_max"]
            })

        # Drop nan values
        for idx, rov_drone in enumerate(rovs_drones):
            rovs_drones[idx] = {
                    k: rov_drone[k]
                    for k in rov_drone
                    if rov_drone[k] != 'NA'
            }

        _i = 'ExcelToYAML: ROVs and Drones read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_rovs_drones = os.path.join(OUT_DIR, 'rovs.yaml')
        f_rovs_drones = open(f_rovs_drones, 'w')
        yaml = YAML()
        yaml.indent(mapping=4)
        rovs_drones = CS(rovs_drones)
        for v in range(1, len(rovs_drones)):
            rovs_drones.yaml_set_comment_before_after_key(v, before='\n')
        yaml.dump(rovs_drones, f_rovs_drones)
        f_rovs_drones.close()

    def inspections_site(units_row: bool=True):
        operations = []

        # Gets Operations from an excel spreadsheet
        try:
            df_operations = pd.read_excel(FILE_EXCEL, sheet_name=OPERATIONS_INSPEC_SITE_SHEET)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')

        df_operations.dropna(axis=1, how='all', inplace=True)
        df_operations = df_operations[df_operations['id'].notna()]
        df_operations.fillna('NA', inplace=True)
        df_operations.columns = df_operations.columns.str.lower()
        columns_mandatory = [
                'id',
                'name',
                'overnight_stay',
                'periodicity',
                'technicians_per_device',
                'technician_cost',
                'dur_per_device',
                'device_shutdown',
                'level'
        ]
        if any([column not in df_operations.columns for column in columns_mandatory]) is True:
            _e = '"id", "name", "overnight_stay", "periodicity",'
            _e += ' "technicians_per_device", "technicians_cost", "dur_per_device",'
            _e += ' "device_shutdown" and "level" are mandatory columns.'
            logging.error(_e)
            raise NameError(_e)

        # Verify operations in df_operations and organize them in a dictionary
        for idx, row in df_operations.iterrows():
            if units_row is True and idx == 0:
                # Skip first row
                continue
            operations.append({
                    "id": row['id'],
                    "name": row['name'],
                    "overnight_stay": row['overnight_stay'],
                    "periodicity": row['periodicity'],
                    "tech_per_device": row['technicians_per_device'],
                    "tech_cost": row['technician_cost'],
                    "dur_per_device": row['dur_per_device'],
                    "device_shutdown": row['device_shutdown'],
                    "level": row['level'],
                    "months": row['preferred_months'],
                    "day_start": row['day_start'],
                    "intervened_wtg": row['wtg_intervened'],
                    "intervened_wec": row['wec_intervened'],
                    "intervened_pv": row['pv_intervened'],
                    "wave_height": row['hs'],
                    "wave_period": row['tp'],
                    "wind_speed": row['ws'],
                    "wind_speed_hub": row['ws_hub'],
                    "current_speed": row['cs'],
                    "light": row['light'],
                    "vessel1_id": row['vessel1_id'],
                    "vessel1_qt": row['vessel1_qt'],
                    "vessel2_id": row['vessel2_id'],
                    "vessel2_qt": row['vessel2_qt'],
                    "rov_drone": row['rov_drone'],
                    "parts_cost": row['parts_cost'],
                    "other_costs": row['other_costs'],
                    "to_be_grouped": row['to_be_grouped'],
                    "to_group_with": row['to_group_with'],
                    "double_shift": row['double_shift']
            })

        # Drop nan values
        for idx, operation in enumerate(operations):
            operations[idx] = {
                    k: operation[k]
                    for k in operation
                    if operation[k] != 'NA'
            }

        _i = 'ExcelToYAML: Inspections at Site read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_operations = os.path.join(OUT_DIR, 'operations_inspections_site.yaml')
        f_operations = open(f_operations, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        operations = CS(operations)
        for v in range(1, len(operations)):
            operations.yaml_set_comment_before_after_key(v, before='\n')
        yaml.dump(operations, f_operations)
        f_operations.close()

    def inspections_port(units_row: bool=True):
        operations = []

        # Gets Operations from an excel spreadsheet
        try:
            df_operations = pd.read_excel(FILE_EXCEL, sheet_name=OPERATIONS_INSPEC_PORT_SHEET)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')

        df_operations.dropna(axis=1, how='all', inplace=True)
        df_operations = df_operations[df_operations['id'].notna()]
        df_operations.fillna('NA', inplace=True)
        df_operations.columns = df_operations.columns.str.lower()
        columns_mandatory = [
                'id',
                'name',
                'periodicity',
                'technicians_per_device',
                'technician_cost',
                'dur_per_device'
        ]
        if any([column not in df_operations.columns for column in columns_mandatory]) is True:
            _e = '"id", "name", "periodicity", "technicians_per_device",'
            _e += ' "technicians_cost" and "dur_per_device"'
            _e += ' are mandatory columns.'
            logging.error(_e)
            raise NameError(_e)

        # Verify operations in df_operations and organize them in a dictionary
        for idx, row in df_operations.iterrows():
            if units_row is True and idx == 0:
                # Skip first row
                continue
            operations.append({
                    "id": row['id'],
                    "name": row['name'],
                    "periodicity": row['periodicity'],
                    "tech_per_device": row['technicians_per_device'],
                    "tech_cost": row['technician_cost'],
                    "dur_per_device": row['dur_per_device'],
                    "months": row['preferred_months'],
                    "day_start": row['day_start'],
                    "intervened_devices": row['devices_intervened'],
                    "wind_speed": row['ws'],
                    "light": row['light'],
                    "level": row['level'],
                    "parts_cost": row['parts_cost'],
                    "other_costs": row['other_costs'],
                    "double_shift": row['double_shift']
            })

        # Drop nan values
        for idx, operation in enumerate(operations):
            operations[idx] = {
                    k: operation[k]
                    for k in operation
                    if operation[k] != 'NA'
            }

        _i = 'ExcelToYAML: Inspections at Port read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_operations = os.path.join(OUT_DIR, 'operations_inspections_port.yaml')
        f_operations = open(f_operations, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        operations = CS(operations)
        for v in range(1, len(operations)):
            operations.yaml_set_comment_before_after_key(v, before='\n')
        yaml.dump(operations, f_operations)
        f_operations.close()

    def corrective_minor(units_row: bool=True):
        operations = []

        # Gets Operations from an excel spreadsheet
        try:
            df_operations = pd.read_excel(FILE_EXCEL, sheet_name=OPERATIONS_CORR_MINOR_SHEET)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')

        df_operations.dropna(axis=1, how='all', inplace=True)
        df_operations = df_operations[df_operations['id'].notna()]
        df_operations.fillna('NA', inplace=True)
        df_operations.columns = df_operations.columns.str.lower()
        columns_mandatory = [
                'id',
                'name',
                'duration_net',
                'device_shutdown',
                'vessel1_id',
                'technicians',
                'technician_cost',
                'level'
        ]
        if any([column not in df_operations.columns for column in columns_mandatory]) is True:
            _e = '"id", "name", "duration_net", "device_shutdown", "vessel1_id", "technicians",'
            _e += ' "technician_cost" and "level" are mandatory columns.'
            logging.error(_e)
            raise NameError(_e)

        # Verify operations in df_operations and organize them in a dictionary
        for idx, row in df_operations.iterrows():
            if units_row is True and idx == 0:
                # Skip first row
                continue

            tech_wtg = False
            tech_wec = False
            tech_pv = False
            if row["wtg"] != 'NA':
                tech_wtg = True
            if row["wec"] != 'NA':
                tech_wec = True
            if row["pv"] != 'NA':
                tech_pv = True

            operations.append({
                    "id": row['id'],
                    "name": row['name'],
                    "tech_wtg": tech_wtg,
                    "tech_wec": tech_wec,
                    "tech_pv": tech_pv,
                    "duration_net": row['duration_net'],
                    "device_shutdown": row['device_shutdown'],
                    "wave_height": row['hs'],
                    "wave_period": row['tp'],
                    "wind_speed": row['ws'],
                    "wind_speed_hub": row['ws_hub'],
                    "current_speed": row['cs'],
                    "light": row['light'],
                    "vessel1_id": row['vessel1_id'],
                    "vessel1_qt": row['vessel1_qt'],
                    "vessel2_id": row['vessel2_id'],
                    "vessel2_qt": row['vessel2_qt'],
                    "rov_drone": row['rov_drone'],
                    "tech_required": row['technicians'],
                    "tech_cost": row['technician_cost'],
                    "other_costs": row['other_costs'],
                    "level": row["level"],
                    "double_shift": row['double_shift']
            })

        # Drop nan values
        for idx, operation in enumerate(operations):
            operations[idx] = {
                    k: operation[k]
                    for k in operation
                    if operation[k] != 'NA'
            }

        _i = 'ExcelToYAML: Corrective Minor read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_operations = os.path.join(OUT_DIR, 'operations_corrective_minor.yaml')
        f_operations = open(f_operations, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        operations = CS(operations)
        for v in range(1, len(operations)):
            operations.yaml_set_comment_before_after_key(v, before='\n')
        yaml.dump(operations, f_operations)
        f_operations.close()

    def corrective_major(units_row: bool=True):
        operations = []

        # Gets Operations from an excel spreadsheet
        try:
            df_operations = pd.read_excel(FILE_EXCEL, sheet_name=OPERATIONS_CORR_MAJOR_SHEET)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')

        df_operations.dropna(axis=1, how='all', inplace=True)
        df_operations = df_operations[df_operations['id'].notna()]
        df_operations.fillna('NA', inplace=True)
        df_operations.columns = df_operations.columns.str.lower()
        columns_mandatory = [
                'id',
                'name',
                'tow_to_port',
                'technicians_required',
                'technician_cost'
        ]
        if any([column not in df_operations.columns for column in columns_mandatory]) is True:
            _e = '"id", "name", "tow_to_port", "technicians_required", '
            _e += '"technicians_cost" are mandatory columns.'
            logging.error(_e)
            raise NameError(_e)

        # Verify operations in df_operations and organize them in a dictionary
        for idx, row in df_operations.iterrows():
            if units_row is True and idx == 0:
                # Skip first row
                continue

            operations.append({
                    "id": row['id'],
                    "name": row['name'],
                    "tow_to_port": row['tow_to_port'],
                    "tech_required": row['technicians_required'],
                    "tech_cost": row['technician_cost'],
                    "vessel1_id": row['vessel1_id'],
                    "vessel1_qt": row['vessel1_qt'],
                    "vessel2_id": row['vessel2_id'],
                    "vessel2_qt": row['vessel2_qt'],
                    "rov_drone": row['rov_drone'],
                    "other_costs": row['other_costs']
            })

        # Drop nan values
        for idx, operation in enumerate(operations):
            operations[idx] = {
                    k: operation[k]
                    for k in operation
                    if operation[k] != 'NA'
            }

        _i = 'ExcelToYAML: Corrective Major read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_operations = os.path.join(OUT_DIR, 'operations_corrective_major.yaml')
        f_operations = open(f_operations, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        operations = CS(operations)
        for v in range(1, len(operations)):
            operations.yaml_set_comment_before_after_key(v, before='\n')
        yaml.dump(operations, f_operations)
        f_operations.close()

    def towing_operations(units_row: bool=True):
        operations = []

        # Gets Operations from an excel spreadsheet
        try:
            df_operations = pd.read_excel(FILE_EXCEL, sheet_name=OPERATIONS_TOW_SHEET)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')

        df_operations.dropna(axis=1, how='all', inplace=True)
        df_operations = df_operations[df_operations['id'].notna()]
        df_operations.fillna('NA', inplace=True)
        df_operations.columns = df_operations.columns.str.lower()
        columns_mandatory = [
                'id',
                'name',
                'technicians_required',
                'technician_cost'
        ]
        if any([column not in df_operations.columns for column in columns_mandatory]) is True:
            _e = '"id", "name", "tow_to_port", "technicians_required", '
            _e += '"technicians_cost" are mandatory columns.'
            logging.error(_e)
            raise NameError(_e)

        # Verify operations in df_operations and organize them in a dictionary
        for idx, row in df_operations.iterrows():
            if units_row is True and idx == 0:
                # Skip first row
                continue

            operations.append({
                    "id": row['id'],
                    "name": row['name'],
                    "tech_required": row['technicians_required'],
                    "tech_cost": row['technician_cost'],
                    "vessel1_id": row['vessel1_id'],
                    "vessel2_id": row['vessel2_id'],
                    "vessel1_qt": row['vessel1_qt'],
                    "vessel2_qt": row['vessel2_qt'],
                    "addition_op_tow": row['additional_previous_op_tow'],
                    "string_disconnection": row['string_disconnection'],
                    "recommissioning_time": row['recommissioning_time'],
                    "other_costs": row['other_costs']
            })

        # Drop nan values
        for idx, operation in enumerate(operations):
            operations[idx] = {
                    k: operation[k]
                    for k in operation
                    if operation[k] != 'NA'
            }

        _i = 'ExcelToYAML: Towing Operations read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_operations = os.path.join(OUT_DIR, 'operations_tow.yaml')
        f_operations = open(f_operations, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        operations = CS(operations)
        for v in range(1, len(operations)):
            operations.yaml_set_comment_before_after_key(v, before='\n')
        yaml.dump(operations, f_operations)
        f_operations.close()

    def operation_activities(units_row: bool=True):
        activities = []

        # Gets Activities from an excel spreadsheet
        try:
            df_activities = pd.read_excel(FILE_EXCEL, sheet_name=ACTIVITIES_SHEET)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')

        df_activities.dropna(axis=1, how='all', inplace=True)
        df_activities = df_activities[df_activities['id'].notna()]
        df_activities.fillna('NA', inplace=True)
        df_activities.columns = df_activities.columns.str.lower()
        columns_mandatory = [
                'id',
                'op',
                'name',
                'location',
                'duration'
        ]
        if any([column not in df_activities.columns for column in columns_mandatory]) is True:
            _e = '"id", "op", "name", "location" and "duration" '
            _e += 'are mandatory columns.'
            logging.error(_e)
            raise NameError(_e)

        # Verify activities in df_activities and organize them in a dictionary
        for idx, row in df_activities.iterrows():
            if units_row is True and idx == 0:
                # Skip first row
                continue
            activities.append({
                    "id": row['id'],
                    "op": row['op'],
                    "name": row['name'],
                    "location": row['location'],
                    "wtg_shutdown_dur": row['wtg_shutdown_dur'],
                    "wec_shutdown_dur": row['wec_shutdown_dur'],
                    "pv_shutdown_dur": row['pv_shutdown_dur'],
                    "duration": row['duration'],
                    "hs": row['hs'],
                    "tp": row['tp'],
                    "ws": row['ws'],
                    "ws_hub": row['ws_hub'],
                    "cs": row['cs'],
                    "light": row['light']
            })

        # Drop nan values
        for idx, activity in enumerate(activities):
            activities[idx] = {
                    k: activity[k]
                    for k in activity
                    if activity[k] != 'NA'
            }

        dict_ops = {}
        # dict_ops initialization
        for activity in activities:
            dict_ops[activity["op"]] = []
        # Add activities to operations
        for activity in activities:
            op_id = activity["op"]
            del activity["op"]
            dict_ops[op_id].append(activity)

        _i = 'ExcelToYAML: Activities read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_activities = os.path.join(OUT_DIR, 'operations_activities.yaml')
        f_activities = open(f_activities, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        yaml.dump(dict_ops, f_activities)
        f_activities.close()

    def failures(units_row: bool=True):
        failures = []

        # Gets Failures from an excel spreadsheet
        try:
            df_failures = pd.read_excel(FILE_EXCEL, sheet_name=FAILURES_SHEET)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')

        df_failures.dropna(axis=1, how='all', inplace=True)
        df_failures = df_failures[df_failures['id'].notna()]
        df_failures.fillna('NA', inplace=True)
        df_failures.columns = df_failures.columns.str.lower()
        columns_mandatory = [
                'id',
                'name',
                'number_of_element_farm',
                'probability_failure',
                'maintenance_strategy',
                'level_failure'
        ]
        if any([column not in df_failures.columns for column in columns_mandatory]) is True:
            _e = '"id", "name", "number_of_element_farm", "probability_failure"'
            _e += ', "maintenance_strategy" and "level_failure" are mandatory '
            _e += 'columns.'
            logging.error(_e)
            raise NameError(_e)

        # Verify failures in df_failures and organize them in a dictionary
        for idx, row in df_failures.iterrows():
            if units_row is True and idx == 0:
                # Skip first row
                continue
            failures.append({
                    "id": row['id'],
                    "name": row['name'],
                    "number_of_element_farm": row['number_of_element_farm'],
                    "probability_failure": row['probability_failure'],
                    "maintenance_strategy": row['maintenance_strategy'],
                    "level_failure": row['level_failure'],
                    "op_trigger": row['op_trigger'],
                    "preferred_month": row['preferred_month'],
                    "avoid_month_correction": row['avoid_month_correction'],
                    "lead_time": row['lead_time'],
                    "bath_tub": row['bath_tub'],
                    "fail_variation": row['fail_variation'],
                    "potential_shutdown": row['potential_shutdown'],
                    "perc_shutdown": row['perc_shutdown'],
                    "parts_cost": row['parts_cost'],
            })

        # Drop nan values
        for idx, failure in enumerate(failures):
            failures[idx] = {
                    k: failure[k]
                    for k in failure
                    if failure[k] != 'NA'
            }

        _i = 'ExcelToYAML: Failures read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_failures = os.path.join(OUT_DIR, 'failures.yaml')
        f_failures = open(f_failures, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        failures = CS(failures)
        for v in range(1, len(failures)):
            failures.yaml_set_comment_before_after_key(v, before='\n')
        yaml.dump(failures, f_failures)
        f_failures.close()

    def failure_scenarios(units_row: bool=True):
        scenarios = []

        # Gets Scenarios from an excel spreadsheet
        try:
            df_scenarios = pd.read_excel(FILE_EXCEL, sheet_name=SCENARIO_SHEET)
        except PermissionError:
            logging.error('Could not open the Excel file. Make sure the file is not opened.')
            raise PermissionError('Could not open the Excel file. Make sure the file is not opened.')

        df_scenarios.dropna(axis=1, how='all', inplace=True)
        df_scenarios = df_scenarios[df_scenarios['scenarios'].notna()]
        df_scenarios.fillna('NA', inplace=True)
        df_scenarios.columns = df_scenarios.columns.str.lower()
        columns_mandatory = [
                'scenarios',
                'january',
                'february',
                'march',
                'april',
                'may',
                'june',
                'july',
                'august',
                'september',
                'october',
                'november',
                'december'
        ]
        if any([column not in df_scenarios.columns for column in columns_mandatory]) is True:
            _e = '"scenarios", "january", "february", "march", "april", '
            _e += '"may", "june", "july", "august", "september", '
            _e += '"october", "november" and "december".'
            logging.error(_e)
            raise NameError(_e)

        # Verify scenarios in df_scenarios and organize them in a dictionary
        for idx, row in df_scenarios.iterrows():
            if units_row is True and idx == 0:
                # Skip first row
                continue
            scenarios.append({
                    "scenarios": row['scenarios'],
                    "january": row['january'],
                    "february": row['february'],
                    "march": row['march'],
                    "april": row['april'],
                    "may": row['may'],
                    "june": row['june'],
                    "july": row['july'],
                    "august": row['august'],
                    "september": row['september'],
                    "october": row['october'],
                    "november": row['november'],
                    "december": row['december']
            })

        _i = 'ExcelToYAML: Scenarios read from an Excel file: "%s".' % FILE_EXCEL
        logging.info(_i)

        f_scenarios = os.path.join(OUT_DIR, 'scenarios.yaml')
        f_scenarios = open(f_scenarios, 'w')
        yaml=YAML()
        yaml.indent(mapping=4)
        scenarios = CS(scenarios)
        for v in range(1, len(scenarios)):
            scenarios.yaml_set_comment_before_after_key(v, before='\n')
        yaml.dump(scenarios, f_scenarios)
        f_scenarios.close()


    # Call functions
    try:
        inputs_general()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % INPUTS_SHEET_GENERAL
        if str(_e) != _expected:
            raise
    try:
        inputs_tseries()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % INPUTS_SHEET_TSERIES
        if str(_e) != _expected:
            raise
    try:
        inputs_stats()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % INPUTS_SHEET_STATS
        if str(_e) != _expected:
            raise
    try:
        inputs_costs()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % INPUTS_SHEET_COST
        if str(_e) != _expected:
            raise
    try:
        general_wtg()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % WTG_SHEET
        if str(_e) != _expected:
            raise
    try:
        general_wec()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % WEC_SHEET
        if str(_e) != _expected:
            raise
    try:
        general_pv()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % PV_SHEET
        if str(_e) != _expected:
            raise
    try:
        vessels()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % VESSELS_SHEET
        if str(_e) != _expected:
            raise
    try:
        vessels_fuel(units_row=False)
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % VESSELS_CONSUMPTION
        if str(_e) != _expected:
            raise
    try:
        vessels_loads()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % VESSELS_LOAD_FACTOR
        if str(_e) != _expected:
            raise
    try:
        vessels_densities()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % VESSELS_FUEL_DENSITY
        if str(_e) != _expected:
            raise
    try:
        rovs_drones()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % ROV_SHEET
        if str(_e) != _expected:
            raise
    try:
        inspections_site()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % OPERATIONS_INSPEC_SITE_SHEET
        if str(_e) != _expected:
            raise
    try:
        inspections_port()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % OPERATIONS_INSPEC_PORT_SHEET
        if str(_e) != _expected:
            raise
    try:
        corrective_minor()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % OPERATIONS_CORR_MINOR_SHEET
        if str(_e) != _expected:
            raise
    try:
        corrective_major()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % OPERATIONS_CORR_MAJOR_SHEET
        if str(_e) != _expected:
            raise
    try:
        towing_operations()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % OPERATIONS_TOW_SHEET
        if str(_e) != _expected:
            raise
    try:
        operation_activities()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % ACTIVITIES_SHEET
        if str(_e) != _expected:
            raise
    try:
        failures()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % FAILURES_SHEET
        if str(_e) != _expected:
            raise
    try:
        failure_scenarios()
    except ValueError as _e:
        _expected = 'Worksheet named \'%s\' not found' % SCENARIO_SHEET
        if str(_e) != _expected:
            raise


if __name__ == '__main__':
    file_excel_inputs = os.path.join(os.getcwd(), 'tests', 'test_files', 'excel_to_yaml', 'inputs.xlsx')
    file_excel_wtg = os.path.join(os.getcwd(), 'tests', 'test_files', 'excel_to_yaml', 'wtg.xlsx')
    file_excel_wec = os.path.join(os.getcwd(), 'tests', 'test_files', 'excel_to_yaml', 'wec.xlsx')
    file_excel_pv = os.path.join(os.getcwd(), 'tests', 'test_files', 'excel_to_yaml', 'pv.xlsx')
    file_excel_vessels = os.path.join(os.getcwd(), 'tests', 'test_files', 'excel_to_yaml', 'vessels.xlsx')
    file_excel_rovs = os.path.join(os.getcwd(), 'tests', 'test_files', 'excel_to_yaml', 'rovs.xlsx')
    file_excel_operations = os.path.join(os.getcwd(), 'tests', 'test_files', 'excel_to_yaml', 'operations.xlsx')
    file_excel_activities = os.path.join(os.getcwd(), 'tests', 'test_files', 'excel_to_yaml', 'activities.xlsx')
    file_excel_failures = os.path.join(os.getcwd(), 'tests', 'test_files', 'excel_to_yaml', 'failures.xlsx')

    run_dir = os.path.join(os.getcwd(), 'tmp')
    if not os.path.exists(run_dir):
        os.mkdir(run_dir)
    run_dir = os.path.join(os.getcwd(), 'tmp', 'test_yaml')
    if not os.path.exists(run_dir):
        os.mkdir(run_dir)
    run_dir = os.path.join(os.getcwd(), 'tmp', 'test_yaml', 'base_files')
    if not os.path.exists(run_dir):
        os.mkdir(run_dir)
    excel_to_yaml(file_excel_inputs, run_dir)
    excel_to_yaml(file_excel_wtg, run_dir)
    excel_to_yaml(file_excel_wec, run_dir)
    excel_to_yaml(file_excel_pv, run_dir)
    excel_to_yaml(file_excel_vessels, run_dir)
    excel_to_yaml(file_excel_rovs, run_dir)
    excel_to_yaml(file_excel_operations, run_dir)
    excel_to_yaml(file_excel_activities, run_dir)
    excel_to_yaml(file_excel_failures, run_dir)
