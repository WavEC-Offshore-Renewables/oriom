import networkx as nx
import pandas as pd
import random
import logging

from logistic_tools.core.functions.layout_power.aux_layout_power_func import choose_loc
from logistic_tools.core.functions.layout_power.aux_layout_power_func import string_location

def manage_string_tow_operation(
    G: nx.DiGraph, 
    loc: int, 
    action: bool,
):
    """  Manage the disconnection/reconnection of the full string if a device is towed
    Args:
        G (:obj:`nx.DiGraph`): DiGraph. 
        loc (:obj:`int or tuple`): location of the failure
        action (:obj:`boolean`): define the action for the visibility of the node
    """
    for u, v in G.edges(loc):
        G[u][v]['visible'] = action


def shut(
    loc: int,
    shutdown: bool,
    G: nx.DiGraph,
    component_level_power: str,
    levels_component_no_power: set,
    tech: str,
    names_tech: str,
    n_pv_per_string: int = None,
    max_failure_module: int = None,
    device_shutted_string_level: dict = None,
    list_failed: set = (),
    string_inverter: set = (),
    event: str = ''
):  
    
    """
    It azzerate the power production of the nodes on which the power is implemented due to the shutting down of the component 
    if it lead to a shutdown. It also close the edges on wich the component is attached in the graph 
    
    For PV case
    device and string level are not implemented in G, so reduce power production for the loc of the inverter of 1 device or 
    n_pv_per_string. In PV the power of the component that fail is never putted to 0 as the restoration will be problematic
    after (difficult to establish at which power to restore). Anyway the closure of the edge in the graph will filter the
    power for that device failed.

    Modify the graph of the farm on which percentage calculation is made on
    Calculate the percentage of power available calculated on the lowest level component on which power is implemented
    (device for WEC and WGT and inverter for OPV)

    Args:
        loc (:obj:`int or tuple`): location of the failure
        shutdown (:obj:`boolean`): define if failure bringst to a shutdown
        G (:obj:`nx.DiGraph`): DiGraph.
        component_level_power (:obj:`str`): lower level of component with power implemented
        levels_component_no_power (:obj:`set`): level of node with level without power characteristic
        tech (:obj:`str`): name of tech analyzed
        names_tech (:obj:`str`): level of the component analyzed
        n_pv_per_strings (:obj:`int`, *optional*): number of modules each string
        max_failure_module (:obj:`int`, *optional*): number of failed module allowed each string
        device_shutted_string_level (:obj:`dict`, *optional*): Dictionary of string power layout
        list_failed (:obj:`set`, *optional*): set of already failed component. 
        string_inverter (:obj:`set`, *optional*): Set of string for the inverter
        event (:obj:`str`, *optional*): Type of event

    Returns:
        G graph and percentage farm available.
    """

    # Switching on or off the node in the graph
    if shutdown:
        if isinstance(loc, int): 
            livello = G.nodes[loc]['level'] 
            if tech == 'PV':
                #remove one PV from inverter
                if 'device' in names_tech:
                    G.nodes[loc]['power'] -= 1     
                    livello = 'device'
                #remove one string from inverter
                elif 'string' in names_tech:
                    G.nodes[loc]['power'] -= n_pv_per_string   
                    livello = 'string'
                #close a string if excess of failed PV module considering the failed one
                elif 'opv_fail_INV_V_min_exceded' in names_tech:
                    G.nodes[loc]['power'] -= (n_pv_per_string - max_failure_module)

            elif tech == 'wind' or tech == 'wave':
                G.nodes[loc]['power'] = 0

            # Disconnect the string if the component is not power defined (hub/connector/other)
            if livello in levels_component_no_power or event == 'tow':
                manage_string_tow_operation(G = G, loc = loc, action = False)
            # Disconnect if farm electr layout cannot sustain a tow without shutdown downstream string a is conducted a towing operation
            if event == 'tow' and getattr(G, 'graph', {}).get('tow_string_shutdown', False):
                manage_string_tow_operation(G = G, loc = loc, action = False)


        elif isinstance(loc, tuple):
            if tech == 'PV':
                #cable failure on tech not implemented, choose a random string and reduce the power
                if loc == ('x', 'x'):
                    # Reassign the location of the array cable to an inverter
                    level = component_level_power

                    list_nG = [n for n, attr in G.nodes(data='level') if attr == level]
                    if list_failed is None:
                        list_failed = set()

                    list_nG_not_failed = set(list_nG) - list_failed

                    if not list_nG_not_failed:
                        list_nG_not_failed = list_nG

                    loc = random.choice(list(list_nG_not_failed))

                    try: 
                        failed_strings = set(device_shutted_string_level[loc].keys())
                    except KeyError:
                        failed_strings = set()

                    k = string_location(failed_strings = failed_strings, string_inverter = string_inverter)
                    if loc not in device_shutted_string_level:
                        device_shutted_string_level[loc] = {}
                        pv_failed_in_string = 0
                    else:
                        pv_failed_in_string = device_shutted_string_level[loc].get(k, 0)
                    device_shutted_string_level[loc][k] = True

                    # Reduce the power of the inverter closing a string considering the already failed PV in that string
                    G.nodes[loc]['power'] -= (n_pv_per_string - pv_failed_in_string)
                else:
                    if G.edges[loc[0],loc[1]]['visible'] is True:
                        G.edges[loc[0],loc[1]]['visible'] = False
            elif tech == 'wind' or tech == 'wave':
                if G.edges[loc[0],loc[1]]['visible'] is True:
                    G.edges[loc[0],loc[1]]['visible'] = False
            else: pass

    # Manage case in which device already shut down but require a tow and farm electr layout lead to shutdown downstream string a is conducted a towing operation
    else:
        if event == 'tow' and getattr(G, 'graph', {}).get('tow_string_shutdown', False):
            manage_string_tow_operation(G = G, loc = loc, action = False)

    #Returning the percentage available
    n_list = []
    for node in G.nodes():
        if G.nodes[node]['level'] == component_level_power:  # Consider only power nodes as the power is on the lowest level component
            for path in nx.all_simple_paths(G, source=node, target=0):
                edges = list(zip(path[:-1], path[1:]))  # Convert the generator in a list
                if all(G[u][v].get('visible', False) for u, v in edges):  # Verify the visibility of arch
                    if node not in n_list:  # Avoid duplicate
                        n_list.append(node)
        else:
            pass

    power_node = [G.nodes[i]['power'] for i in n_list]
    power_farm = sum(power_node)

    return G, power_farm

def fix(
    loc,
    G: nx.DiGraph,
    component_level_power: str,
    levels_component_no_power: set,
    tech: str,
    names_tech: str,
    n_pv_per_string: int = None,
    event: str = ''
):
    """
    It restore the power production due to the fixing of the component failed
    For PV case device and string level are not implemented in G, so increase power production for the loc of the inverter
    Restore the graph of the farm on which percentage calculation is made on
    Calculate the percentage of power available calculated on the lowest level component on which power is implemented
    (device for WEC and WGT and inverter for OPV)

    Args:
        loc (:obj:`int or tuple`): location of the failure
        G (:obj:`nx.DiGraph`): DiGraph.
        component_level_power (:obj:`str`): level of component with power characteristic
        levels_component_no_power (:obj:`set`): level of node with level without power characteristic
        tech (:obj:`str`): name of tech analyzed
        names_tech (:obj:`str`): level of the component analyzed
        n_pv_per_string (:obj:`str`): number of pv modules per string 
        event (:obj:`str`, *optional*): Type of event

    Returns:
        G graph and percentage farm available.
    """

    if loc == ('x', 'x'):
        pass
    elif isinstance(loc, tuple) is True:
        if G.edges[loc[0],loc[1]]['visible'] is False:
            G.edges[loc[0],loc[1]]['visible'] = True
        else: pass
    elif isinstance(loc, int) is True:
        livello = G.nodes[loc]['level'] 
        
        if tech == 'PV':
            #restore one PV from string
            if 'device' in names_tech:
                G.nodes[loc]['power'] += 1              
                livello = 'device'
            #restore one string from inverter
            elif 'string' in names_tech:
                G.nodes[loc]['power'] += n_pv_per_string   
                livello = 'string'
        elif tech == 'wind' or tech == 'wave':
            if G.nodes[loc]['level'] == 'device':
                G.nodes[loc]['power'] = 1

        # Reconnect the string if the component is not power defined (hub/connector/other)
        if livello in levels_component_no_power or event == 'tow':
            manage_string_tow_operation(G = G, loc = loc, action = True)
        # Reconnect the string if the towing operation did shutdown the downstream string
        if event == 'tow' and getattr(G, 'graph', {}).get('tow_string_shutdown', False):
            manage_string_tow_operation(G = G, loc = loc, action = True)

    n_list = []
    for node in G.nodes():
        if G.nodes[node]['level'] == component_level_power:  # Consider only power nodes
            for path in nx.all_simple_paths(G, source=node, target=0):
                edges = list(zip(path[:-1], path[1:]))  # Convert the generator in a list
                if all(G[u][v].get('visible', False) for u, v in edges):  # Verify the visibility of arch
                    if node not in n_list:  # Avoid duplicate
                        n_list.append(node)
        else:
            pass

    power_node = [G.nodes[i]['power'] for i in n_list]
    power_farm = sum(power_node)
    return G, power_farm


def reassign_loc(
    row: pd.Series,
    df: pd.Series,
    find_element_class,
    G: nx.DiGraph,
    device_shutted: list,
    index:str,
    tech: str
):
    '''
    Reassign the location of a failure in case the component was already failed
    Update the failure and correlated operation in the df to update the new location

    Args:
        row (:obj:`pd.Series`): row of df dataframe
        df (:obj:`pd.DataFrame`): Dataframe of corrective shutdown
        find_element_class (Find_element_class): Initialized instance that provides fast access to operations, vessels and failures via internal dictionaries.
        G (:obj:`nx.DiGraph`): DiGraph.
        device_shutted (:obj:`list`): list of devices shutted
        indice (:obj:`str`): index of the failure analyzed
        tech (:obj:`str`): name of tech analyzed

    Returns:
        G graph and percentage farm available.
    '''
    id_ = row['id']
    id_fix_failure = 'oper_' + id_
    id_fail = id_.split('.')[0]
    failure = find_element_class.find_operation(id_fail)

    level = failure.level_failure   # obtain level of failure
    row['Loc'] = choose_loc(level, G, device_shutted, tech) # Reassign a location of the failure

    df.at[index, 'Loc'] = row['Loc']     # Modify the value in the dataframe for the failure

    # Find position for operation correlated in df 
    row_index = df.index[(df['Comments'] == id_fix_failure) & (df['Shut/Fix'] == 'fix')]
    if len(row_index) == 1:  
        row_index = row_index.item()  # Converte intex

    # Update the location in the correlated operation
    df.at[row_index, 'Loc'] = row['Loc']  

    return row['Loc']
