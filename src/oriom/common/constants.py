""" Common fixed parameter for ORIOM """

FAILURE_NODE_LEVEL_LIST = [
    'shore', 'substation', 'mv_transformer', 'string', 'hub',
    'circuit_braker', 'switcher', 'inverter', 'device'
]

FAILURE_EDGE_LEVEL_LIST = [
    'exp_cable', 'exp_cable_island', 'dyn_cable-sub',
    'array_cable', 'cable_cb', 'cable_transf', 'cable_switch',
    'cable_inv', 'string_cable'
]

FAILURE_LEVEL_LIST = [None] + FAILURE_NODE_LEVEL_LIST + FAILURE_EDGE_LEVEL_LIST

LIST_MONTHS_STR = [str(c) for c in range(1,13)]
LIST_MONTHS = [c for c in range(1,13)]

DICT_DAYS = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}

REUSE_FIELDS_MAJOR_TO_COMPARE = [
    "location", "wtg_shutdown_dur", "wec_shutdown_dur", "pv_shutdown_dur", 
    "duration", "hs", "tp", "ws", "ws_hub", "cs", "light"
]

ATTRIBUTE_LIST_REUSE_INSPECTION = [
    'dur_per_device', 'hs', 'tp', 'ws', 'ws_hub', 'cs', 'light', 'vessel1_id', 'rov_drone',
    'technicians_per_device', 'vessel2_id', 'device_shutdown', 'intervened_wtg', 'intervened_wec',
    'intervened_pv','rov', 'overnight', 'double_shift'
]

ATTRIBUTE_LIST_REUSE_MINOR = [
    'duration_net', 'hs', 'tp', 'ws', 'ws_hub', 'cs', 'light', 
    'vessel1_id', 'vessel2_id', 'shutdown', 'technology', 'rov'
]
power_conversion = {'_w': 1 / 1000, '_kw': 1.0, '_mw': 1000}

UNIT_CONVERSION = {
    'wind_speed': {
        '_m/s': 1.0,
        '_km/h': 1000 / 3600,
        '_knots': 0.514444,
        '_kn': 0.514444,
    },
    'p_wind': power_conversion,
    'p_wave': power_conversion
}

TECH_TYPES = ['wtg', 'wec', 'pv']

FORMATS_DATETIME = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%y %H:%M:%S",
    "%d-%m-%y %H:%M:%S",
    "%d-%m-%y %H:%M",
    "%d-%m-%Y %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%m/%d/%Y %H:%M"
]

METOCEAN_COLUMNS = ['datetime', 'hs', 'tp', 'te', 'ws', 'ws_hub', 'cs', 'si', 'light']