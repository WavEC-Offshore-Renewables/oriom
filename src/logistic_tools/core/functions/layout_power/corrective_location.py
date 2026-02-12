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


def logs_corrective_locations(
    r: pd.Series,
    op_corr_excluding_tow: list,
    shut_attribute: str,
    find_element_class,
    dict_locations: dict,
) -> tuple[list, dict]:
    """
    Generate time-ordered abstract corrective events WITHOUT deciding location.
    Location and shutdown effects must be handled later during simulation.

    Args:
        r (:obj:`pd.Series`): Row of the Log_event (failure, operation, inspection_port, inspection_site).
        op_corr_excluding_tow (:obj:`list`): list of string representig object.id :class:`OperationsMinor`+`OperationsMajor`.
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
            "loc": None,              # decided later
        })

        # store failure → future operations will reference this
        dict_locations[r['id']] = None

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
                "loc": None,
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
                "loc": None,
            })

    # ---------- OPERATION (excluding tow) ----------
    elif r['event'] == 'operation' and r['id'] in op_corr_excluding_tow:
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
        events.append({
            "date": r['d_end_transit_tp'],
            "event": "operation",
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