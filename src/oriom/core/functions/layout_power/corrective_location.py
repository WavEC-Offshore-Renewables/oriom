import pandas as pd
import networkx as nx
import logging

COLS = ['Date', 'Event', 'id', 'Comments', 'Name', 'Loc', 'Shutdown', 'Shut/Fix']

RENAME_COL = {
    'event': 'Event',
    'comments': 'Comments',
    'name': 'Name',
    'loc': 'Loc',
    'shutdown': 'Shutdown',
    'shut/fix': 'Shut/Fix'
}


def choose_spec_loc_string(G, start_node):
    """ 
    Find the first node to start_node after the node with level attribute == ``substation`` 
        with the shortest path from ``substation``. Used to deenergize a string.
    
    Args:
        G (:obj:nx.DiGraph): Graph of tech farm.
        start_node (int): Position of the node to evaluate
    """
    # Shorterst path to the HUB
    percorso = nx.shortest_path(G, source=start_node, target=0)
    # Find first node with level != power_level
    previous_node = None
    level_node = None
    for nodo in percorso:
        if previous_node == None:
            previous_node = nodo
        if G.nodes[nodo].get("level") == 'substation':
            level_node = previous_node
            break
        previous_node = nodo

    if level_node:
        edges = list(G.edges(level_node))
        return edges[0]
    else:
        raise AttributeError(f'substation not found for node {start_node}')
    
    
def condition_shut_fix_evaluation(op_corr_tow: dict, fail_op: list, op_add_tow: dict, r: str, specific_tow: str):
    """ Evaluate the condition to decide if the shutdown or fix event should be added to the energy events."""
    # if no tow operation is connected to the failure
    has_corr = any(f.id in op_corr_tow.keys() for f in fail_op)
    # if any tow operation is connected to the failure and is specific_tow op
    has_remove = any(specific_tow in f.name.lower() for f in fail_op)
    # If string disconnection
    add_flag = op_add_tow.get(r, {}).get('string', False)

    enter_condition = (
        not has_corr
        or add_flag
        or has_remove
    )
    return enter_condition

def logs_corrective_locations(
    r: pd.Series,
    op_corr_excluding_tow: list,
    shut_attribute: str,
    find_element_class,
    dict_locations: dict,
    op_corr_tow: dict,
    op_add_tow: dict
) -> tuple[list, dict]:
    """
    Generate time-ordered abstract corrective events WITHOUT deciding location.
    Location and shutdown effects must be handled later during simulation.

    Args:
        r (:obj:`pd.Series`): Row of the Log_event (failure, operation, inspection_port, inspection_site).
        op_corr_excluding_tow (list): list of string representig object.id :class:`OperationsMinor`+`OperationsMajor`.
        op_corr_tow (dict): dict of string representig object.id :class:`OperationsTow`.
        op_add_tow (dict): dict of string representig object.id : string_disconnection that are additions to other operations.
        find_element_class (Find_element_class): Initialized instance that provides fast access to operations,
            vessels and failures via internal dictionaries.
        dict_locations (dict): Dictionary with key the failure id and value the location assigned.
    """

    events = []

    # ---------- FAILURE ----------
    if r['event'] == 'failure':
        id_ = r['id'].split('.')[0]
        failure = find_element_class.find_failure_from_id(id_)
        level = failure.level_failure
        shut = r.get('shutdown', False)

        events.append({
            "date": r['Date'],
            "event": "failure",
            "id": r['id'],
            "comments": r['comments'],
            "name": failure.name,
            "failure_id": r['id'],
            "level": level,
            "shutdown": shut,
            "shut_fix": "shut",
            "loc": None,              # decided later on
        })

        # store failure → future operations will reference this
        dict_locations[r['id']] = None

        # Introduce Hybrid management for failure finding
        if 'hybrid' in failure.name:
            events.append({
                "date": r['Date'],
                "event": "failure",
                "id": 'hybrid_' + r['id'],
                "comments": r['comments'],
                "name": 'hybrid '+ failure.name,
                "failure_id": 'hybrid_'+ r['id'],
                "level": level,
                "shutdown": shut,
                "shut_fix": "shut",
                "loc": None,
            })
            events.append({
                "date": r['Date'] + pd.Timedelta(days=2),
                "event": "operation",
                "id": 'ofw_op009',
                "comments": 'oper_' + r['comments'],
                "name": 'hybrid failure finding',
                "failure_id": 'hybrid_'+ r['id'],
                "level": level,
                "shutdown": True,
                "shut_fix":  "fix",
                "loc": None,
            })

            # store failure → future operations will reference this
            dict_locations['hybrid_' + r['id']] = None

    # ---------- TOW ----------
    elif r['event'] == 'tow':
        fail = r['comments'][4:]
        if fail not in dict_locations:
            raise ValueError(
                f"E availability: Corrective tow operation without failure: {r['id']}, {r['comments']}"
            )

        if 'removal' in r['id']:
            events.append({
                "date": r['d_end_transit_ts'],
                "event": "tow",
                "id": r['id'],
                "comments": r['comments'],
                "name": r['id'],
                "failure_id": fail,
                "shutdown": True,
                "shut_fix": "shut",
                "loc": None,            # decided later on
            })

        elif 'redeploy' in r['id']:
            events.append({
                "date": r['d_end_dur_net_site'],
                "event": "tow",
                "id": r['id'],
                "comments": r['comments'],
                "name": r['id'],
                "failure_id": fail,
                "shutdown": False,
                "shut_fix": "fix",
                "loc": None,            # decided later on
            })

    # ---------- OPERATION (excluding tow) ----------
    elif r['event'] == 'operation' and r['id'] in op_corr_excluding_tow or r['event'] == 'recommissioning':
        if not isinstance(r['comments'], str):
            raise TypeError(f"Invalid comments type: {r['comments']}")

        fail = r['comments'][5:]
        if fail not in dict_locations:
            raise ValueError(
                f"E availability: Corrective operation without failure: {r['id']}, {r['comments']}"
            )

        operation = find_element_class.find_operation_stats(r['id'])
        shut_fix = 'shut' if getattr(operation.op_class, 'tow_to_port', False) else 'fix'
        shutdown_hours = getattr(operation, shut_attribute)
        month = r['d_end_transit_ts'].month

        fail_op = operation.op_class.failures or []

        # Shut operations
        shut_case = condition_shut_fix_evaluation(op_corr_tow, fail_op, op_add_tow, r['id'], 'remov')
        if shut_case:
            if r['event'] != 'recommissioning':
                # optional shutdown before repair
                if shutdown_hours.get(str(month), 0) != 0:
                    events.append({
                        "date": r['d_end_transit_ts'],
                        "event": "operation",
                        "id": r['id'],
                        "comments": r['comments'],
                        "name": operation.op_class.name,
                        "failure_id": fail,
                        "shutdown": True,
                        "shut_fix": "shut",
                        "loc": None,
                    })
        
        # fix or final state
        fix_case = condition_shut_fix_evaluation(op_corr_tow, fail_op, op_add_tow, r['id'], 'deplo')
        if fix_case:
            events.append({
                "date": r['d_end_dur_net_site'],
                "event": "operation" if r['event'] != 'recommissioning' else 'recommissioning',
                "id": r['id'],
                "comments": r['comments'],
                "name": operation.op_class.name,
                "failure_id": fail,
                "shutdown": True,
                "shut_fix": shut_fix,
                "loc": None,
            })

    return events, dict_locations

if __name__ == '__main__':
    pass