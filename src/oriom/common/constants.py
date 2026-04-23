""" Common fixed parameter for ORIOM """

# Failure list level available to select
FAILURE_LEVEL_LIST = [
    None, 'exp_cable', 'exp_cable_island', 'dyn_cable-sub',
    'array_cable', 'cable_cb', 'cable_transf', 'cable_switch',
    'cable_inv', 'string_cable', 'substation', 'mv_transformer',
    'circuit_braker', 'switcher', 'inverter', 'device', 'hub'
]

FAILURE_NODE_LEVEL_LIST = [
    'substation', 'mv_transformer', 'string', 'hub',
    'circuit_braker', 'switcher', 'inverter', 'device'
]

FAILURE_EDGE_LEVEL_LIST = [
    'exp_cable', 'exp_cable_island', 'dyn_cable-sub',
    'array_cable', 'cable_cb', 'cable_transf', 'cable_switch',
    'cable_inv', 'string_cable'
]

LIST_MONTHS_STR = [str(c) for c in range(1,13)]
LIST_MONTHS = [c for c in range(1,13)]

DICT_DAYS = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}