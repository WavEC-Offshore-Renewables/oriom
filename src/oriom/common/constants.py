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