import networkx as nx
import logging
import os
import matplotlib.pyplot as plt

from oriom.domain.Layouts.Layout_Auxiliary import Layout_Aux


class Layout_Wind():
    """Class to generate various offshore wind farm electrical layouts."""

    def check_input_wind(self, n_turbines: int, n_strings: int):
        """Ensure number of turbines is divisible by number of strings."""
        if n_turbines % n_strings != 0:
            msg = f"Layout: n_turbines ({n_turbines}) must be divisible by n_strings ({n_strings})"
            logging.error(msg)
            raise ValueError(msg)


    # ---------------------------------------------------------------------
    # Layout 1
    # ---------------------------------------------------------------------
    def layout1_wind(self, n_turbines: int, n_strings: int, substation_node: int, tow_string_shutdown: bool,
                     save_dir=None, show_plot=False):
        """
        .. figure:: /_static/Layout_imgs/Wind_Layout_1.jpg
            :width: 8000px
            :alt: example

            LAYOUT 1: SIMPLE LAYOUT, n_strings=2, n_turbines=6
            
            Levels: 
                onshore substation = 'shore';
                export cable = 'exp_cable';
                offshore substation = 'substation'; 
                array cable = 'array_cable';
                interarray_cable = 'dyn_cable-sub';
                wtg = 'device';

        Layout 1: One substation, one export cable to shore, uniform strings.
        """
        self.check_input_wind(n_turbines, n_strings)
        G = nx.DiGraph()
        G.graph['tow_string_shutdown'] = tow_string_shutdown
        Layout_Aux.add_substation_and_shore(G, n_strings, substation_node)

        if n_turbines == 1:
            node = substation_node + 1
            G.add_node(node)
            nx.set_node_attributes(G, {node: {
                'name': "Wtg_1", 'coords': ((n_strings - 1) / 2, 0),
                'level': 'device', 'power': 1
            }})
            G.add_edge(node, substation_node)
            nx.set_edge_attributes(G, {(node, substation_node): {
                'name': 'array_cable', 'level': 'array_cable',
                'visible': True, 'p_limit': None
            }})
        else:
            turbines = list(range(1, n_turbines + 1))
            turbines_per_string = Layout_Aux.interval_extract(turbines, n_strings)
            node_counter = substation_node

            for s, string_turbines in enumerate(turbines_per_string):
                h = 2
                for i, t in enumerate(string_turbines):
                    if t == string_turbines[0]:
                        cable_name = 'array_cable'
                        cable_level = 'array_cable'
                    else:
                        cable_name = 'inter_array_cable'
                        cable_level = 'dyn_cable-sub'
                    node_counter += 1
                    G.add_node(node_counter)
                    nx.set_node_attributes(G, {node_counter: {
                        'name': f"Wtg_{t}", 'coords': (s, h),
                        'level': 'device' if t != string_turbines[-1] else 'last_string_device',
                        'power': 1
                    }})
                    if i == 0:
                        G.add_edge(node_counter, substation_node)
                    else:
                        G.add_edge(node_counter, node_counter - 1)
                    nx.set_edge_attributes(G, {(list(G.edges())[-1]): {
                        'name': cable_name, 'level': cable_level,
                        'visible': True, 'p_limit': None
                    }})
                    h += 3
        Layout_Aux.draw_layout(G, save_dir, show_plot, title="Wind_Layout_1")
        return G

    # ---------------------------------------------------------------------
    # Layout 2
    # ---------------------------------------------------------------------
    def layout2_wind(self, n_turbines: int, n_strings: int, n_substations: int, tow_string_shutdown: bool,
                 save_dir=None, show_plot=False):
        """
        .. figure:: /_static/Layout_imgs/Wind_Layout_2.jpg
            :width: 8000px
            :alt: example

            LAYOUT 2: DOUBLE FARM REDUNDANT LAYOUT, n_substations=2, n_strings=2, n_turbines=8
            
            Levels: 
                onshore substation = 'shore';
                export cable = 'exp_cable';
                redundant export cable = 'redundant_cable';
                offshore substation = 'substation'; 
                array cable = 'array_cable';
                interarray_cable = 'dyn_cable-sub';
                wtg = 'device';

        Layout 2: Multiple independent farms, each with one substation and one export cable.
            All substations connect to a single shore node. Redundancy cable between substations.
        """
        if n_turbines % n_substations != 0:
            raise ValueError(f"Layout: {n_turbines=} not divisible by {n_substations=}")

        n_wtgs = n_turbines // n_substations
        sub_nodes = []
        Gs = {}

        conn_offset = 1  # counter

        # Independent farm creations
        for s in range(n_substations):
            sub_node = conn_offset
            sub_nodes.append(sub_node)
            G_sub = self.layout1_wind(
                n_turbines=n_wtgs,
                n_strings=n_strings,
                substation_node=sub_node,
                tow_string_shutdown = tow_string_shutdown,
                show_plot=False
            )
            Gs[f"G_{s}"] = G_sub
            conn_offset += n_wtgs+1

        # Composition of the farms
        G_composed = nx.compose_all(Gs.values())

        # Redundant connections between substations
        for s in range(len(sub_nodes) - 1):
            G_composed.add_edge(sub_nodes[s], sub_nodes[s + 1])
            G_composed.add_edge(sub_nodes[s + 1], sub_nodes[s])
            nx.set_edge_attributes(G_composed, {
                (sub_nodes[s], sub_nodes[s + 1]): {'name': 'redundant_cable', 'level': 'redundant_cable', 'visible': False, 'p_limit': None},
                (sub_nodes[s + 1], sub_nodes[s]): {'name': 'redundant_cable', 'level': 'redundant_cable', 'visible': False, 'p_limit': None}
            })

        # Shifting coordinates for the graph visualization
        pos = nx.get_node_attributes(G_composed, "coords")
        positions = {}
        x_shift = 0
        for g in Gs.keys():
            for node in Gs[g].nodes:
                if node == 0:
                    positions[node] = (pos[node][0] - (n_strings+1)/2, pos[node][1])
                else:
                    positions[node] = (pos[node][0] - x_shift, pos[node][1])
            x_shift += n_strings + 1

        names = nx.get_node_attributes(G_composed, "name")
        edges_names = nx.get_edge_attributes(G_composed, "name")
        nx.draw(G_composed, pos=positions, with_labels=True, node_color='lightblue', node_size=100, alpha=0.8, labels=names)
        nx.draw_networkx_edge_labels(G_composed, pos=positions, edge_labels=edges_names, font_size=5)

        if save_dir is not None:
            plt.savefig(os.path.join(save_dir, 'Wind_Layout_2.jpg'))
        if show_plot:
            plt.show()
        plt.close()


        return G_composed

    # ---------------------------------------------------------------------
    # Layout 3
    # ---------------------------------------------------------------------
    def layout3_wind(self, n_turbines: int, n_strings: int, n_exports: int, tow_string_shutdown: bool, save_dir=None, show_plot=False):
        """
        .. figure:: /_static/Layout_imgs/Wind_Layout_3.jpg
            :width: 8000px
            :alt: example

            LAYOUT 3: REDUNDANT EXPORT CABLE LAYOUT, n_exports=3,, n_strings=2, n_turbines=6,
            
            Levels: 
                onshore substation = 'shore';
                export cable = 'exp_cable';
                redundant export cable = 'exp_cable';
                offshore substation = 'substation';
                array cable = 'array_cable';
                interarray_cable = 'dyn_cable-sub';
                wtg = 'device';

        Layout 3: Layout 1 with multiple export cables to shore for redundancy.
        """
        G = self.layout1_wind(n_turbines=n_turbines, n_strings=n_strings, substation_node=n_exports, tow_string_shutdown = tow_string_shutdown, show_plot=False)

        max_node = max(G.nodes)
        # Creation ficticial node for redundancy export cable
        for i in range(n_exports - 1):
            max_node += 1
            dummy_node = max_node
            G.add_node(dummy_node)
            nx.set_node_attributes(G, {dummy_node: {
                'name': f'Dummy_{i+1}',
                'coords': ((n_strings+i*0.5) / 2, -1-i*0.5),
                'level': 'dummy',
                'power': 0
            }})

            # Dummy connection to dummy substation
            G.add_edge(n_exports, dummy_node)
            nx.set_edge_attributes(G, {(n_exports, dummy_node): {
                'name': f'exp_cable_dummy{i}',
                'level': 'exp_cable_dummy',
                'visible': True,
                'p_limit': None
            }})

            #Connection dummy substation to shore (real connection)
            G.add_edge(dummy_node, 0)
            nx.set_edge_attributes(G, {(dummy_node, 0): {
                'name': f'export_cable_{i}',
                'level': 'exp_cable',
                'visible': True,
                'p_limit': None
            }})

        Layout_Aux.draw_layout(G, save_dir, show_plot, title="Wind_Layout_3")
        return G

    # ---------------------------------------------------------------------
    # Layout 4
    # ---------------------------------------------------------------------
    def layout4_wind(self, n_turbines: int, n_strings: int,
                     substation_node: int, string_list: list, tow_string_shutdown: bool,
                     save_dir=None, show_plot=False):
        """
        .. figure:: /_static/Layout_imgs/Wind_Layout_4.jpg
            :width: 8000px
            :alt: example

            LAYOUT 4: CUSTOM STRINGS, string_list = [5, 8, 5, 8, 6, 8], n_strings=6, n_turbines=40
            
            Levels: 
                onshore substation = 'shore';
                export cable = 'exp_cable';
                offshore substation = 'substation';
                array cable = 'array_cable';
                interarray_cable = 'dyn_cable-sub';
                wtg = 'device';

        Layout 4: Custom non-uniform string configuration.
        """
        def split_by_string(n_turbs, sizes, n_strings):
            if len(sizes) != n_strings:
                raise ValueError(f"Layout: {len(sizes)=} must equal {n_strings=}")
            if sum(sizes) != len(n_turbs):
                raise ValueError("Layout: total turbines must match sum of string sizes")
            groups, index = [], 0
            for size in sizes:
                groups.append(n_turbs[index:index + size])
                index += size
            return groups

        G = nx.DiGraph()
        G.graph['tow_string_shutdown'] = tow_string_shutdown

        Layout_Aux.add_substation_and_shore(G, n_strings)
        list_turbines = list(range(1, n_turbines + 1))
        turbines_per_string = split_by_string(list_turbines, string_list, n_strings)
        node_counter = substation_node

        for s, string_turbines in enumerate(turbines_per_string):
            h = 2
            for i, t in enumerate(string_turbines):
                if t == string_turbines[0]:
                    cable_name = 'array_cable'
                    cable_level = 'array_cable'
                else:
                    cable_name = 'inter_array_cable'
                    cable_level = 'dyn_cable-sub'
                node_counter += 1
                G.add_node(node_counter)
                nx.set_node_attributes(G, {node_counter: {
                    'name': f"Wtg_{t}", 'coords': (s, h),
                    'level': 'device' if t != string_turbines[-1] else 'last_string_device',
                    'power': 1
                }})
                if i == 0:
                    G.add_edge(node_counter, substation_node)
                else:
                    G.add_edge(node_counter, node_counter - 1)
                nx.set_edge_attributes(G, {(list(G.edges())[-1]): {
                    'name': cable_name, 'level': cable_level,
                    'visible': True, 'p_limit': None
                }})
                h += 3

        Layout_Aux.draw_layout(G, save_dir, show_plot, title="Wind_Layout_4")
        return G

    # ---------------------------------------------------------------------
    # Layout 5
    # ---------------------------------------------------------------------
    def layout5_wind(
            self,
            n_turbines: int,
            n_strings: int,
            substation_node: int,
            n_string_to_connector: int = 6,
            tow_string_shutdown: bool = False,
            save_dir=None,
            show_plot=False
    ):

        """
        .. figure:: /_static/Layout_imgs/Wind_Layout_5.jpg
            :width: 8000px
            :alt: example

            LAYOUT 5, FISHBONE: n_export_cables=1, substation_node=1, n_string_to_connector(hub)=2, n_strings=4, n_turbines=12
            
            Levels: 
                onshore substation = 'shore';
                export cable = 'exp_cable';
                offshore substation = 'substation';
                feeder cable = 'exp_cable_island' (offshore substation to main connector node);
                Fishbone main connector = 'hub';
                array cable = 'array_cable' (cable between connectors);
                Fishbone connector = 'circuit_braker';
                interarray cable = 'dyn_cable-sub' (cable between WTG and connectors);
                wtg = 'device';

        FISHBONE layout
        Strings are connected to the same 66 kV feeder cable that bring power to offshore substation

        Hard code to modify n_string_to_connector

        Args:
            n_string_to_connector (int): Number of string that are connect to the same connector (hub).
                Default value to ´´6´´
        """

        G = nx.DiGraph()
        G.graph['tow_string_shutdown'] = tow_string_shutdown
        Layout_Aux.add_substation_and_shore(G, n_strings, substation_node)

        turbines = list(range(1, n_turbines + 1))
        turb_per_string = Layout_Aux.interval_extract(turbines, n_strings)

        h = 4

        count_nodes = substation_node
        connector_node = substation_node
        list_connector = list(range(0, n_strings, n_string_to_connector))
        for s in range(n_strings):
            if s in list_connector:
                count_nodes +=1
                G.add_node(count_nodes)
                att_w = {count_nodes:{
                        'name' : "Connector_node",
                        'coords' : (s+(n_string_to_connector/2)-0.5,1),
                        'level' : 'hub',
                        'power' : 0
                }}
                nx.set_node_attributes(G, values=att_w)

                G.add_edge(count_nodes, substation_node)
                attr_es = {(count_nodes, substation_node):{
                        'name' : "feeder_cable",
                        'level' : 'exp_cable_island',
                        'visible': True,
                        'p_limit': None
                }}
                nx.set_edge_attributes(G, attr_es)

                connector_node = count_nodes

            for t in turb_per_string[s][:]:
                offset = (-0.25, 0.25) if t % 2 == 0 else (0.25, 0.25)
                count_nodes +=1
                # Connector
                G.add_node(count_nodes)
                att_w = {count_nodes:{
                        'name' : "Conn_%i" %t,
                        'coords' : (s,h),
                        'level' : 'circuit_braker',
                        'power' : 0
                }}
                if t == turb_per_string[s][0]:
                    G.add_edge(count_nodes, connector_node)
                    attr_es = {(count_nodes, connector_node):{
                            'name' : "array_cable",
                            'level' : 'array_cable',
                            'visible': True,
                            'p_limit': None
                    }}
                nx.set_edge_attributes(G, attr_es)
                nx.set_node_attributes(G, values=att_w)

                # Turbine
                t_1 = t+1
                G.add_node(count_nodes+1)
                att_w1 = {count_nodes+1:{
                        'name' : "WTG_%i" %t,
                        'coords' : (s+offset[0],h+offset[1]),
                        'level' : 'device',
                        'power' : 1
                }}
                G.add_edge(count_nodes+1,count_nodes)
                attr_ef = {(count_nodes+1,count_nodes):{
                        'name' : "inter_array_cable",
                        'level' : 'dyn_cable-sub',
                        'visible': True,
                        'p_limit': None
                }}
                nx.set_edge_attributes(G, attr_ef)
                nx.set_node_attributes(G,values=att_w1)
                h+=2
                if t < turb_per_string[s][-1]:
                    # Connector + 1
                    t_1 = t+1
                    G.add_node(count_nodes+2)
                    att_w2 = {count_nodes+2:{
                            'name' : "Conn_%i" %t_1,
                            'coords' : (s,h),
                            'level' : 'circuit_braker',
                            'power' : 0
                    }}
                    G.add_edge(count_nodes+2,count_nodes)
                    attr_ef2 = {(count_nodes+2,count_nodes):{
                            'name' : "array_cable",
                            'level' : 'array_cable',
                            'visible': True,
                            'p_limit': None
                    }}

                    nx.set_edge_attributes(G, attr_ef2)
                    nx.set_node_attributes(G,values=att_w2)
                    h+=3
                count_nodes+=1
            h=4

        Layout_Aux.draw_layout(G, save_dir, show_plot, title="Wind_Layout_5")
        return G


    # ---------------------------------------------------------------------
    # Layout 6
    # ---------------------------------------------------------------------
    def layout6_wind(
            self,
            n_turbines: int,
            n_strings: int,
            substation_node: int,
            n_string_to_connector: int = 1,
            tow_string_shutdown: bool = False,
            save_dir=None,
            show_plot=False
    ):

        """
        .. figure:: /_static/Layout_imgs/Wind_Layout_6.jpg
            :width: 800px
            :alt: example

            LAYOUT 6 STAR LAYOUT: n_export_cables=1, substation_node=1, n_string_to_connector(hub)=5, n_turbines=15
            
            Levels: 
                onshore substation = 'shore';
                export cable = 'exp_cable';
                offshore substation = 'substation';
                array cable/feeder cable = 'array_cable' (offshore substation to main connector node);
                Star connector = 'hub';
                interarray cable = 'dyn_cable-sub' (cable between WTG and connectors);
                wtg = 'device';

        Layout with 1 Substation, 1 Array Cable, hubs and string of 1 turbine connected to  connector

        Args:
            n_string_to_connector (int): Number of string that are connect to the same connector (hub).
                Default value to ´´1´´
            n_strings (int): Number of strings in the layout. Is equal to n_turbines
        """

        G = nx.DiGraph()
        G.graph['tow_string_shutdown'] = tow_string_shutdown

        # DEFINING SHORE
        G.add_node(0)
        attr_s = {0: {
                'name' : 'SHORE',
                'coords' : (n_turbines/2-0.5,-2),
                'level' : 'shore',
                'power' : 0
        }}
        nx.set_node_attributes(G, values=attr_s)

        # DEFINING SUBSTATION
        G.add_node(substation_node)
        attr_h = {substation_node: {
                'name' : 'Sub',
                'coords' : (n_turbines/2-0.5,-1),
                'level' : 'substation',
                'power' : 0
        }}
        nx.set_node_attributes(G, values=attr_h)

        # CONNECTING HUB TO SHORE
        G.add_edge(substation_node,0)
        attr_exp = {(substation_node,0) : {
                'name' : 'export_cable',
                'level' : 'exp_cable',
                'visible': True,
                'p_limit': None,
        }}
        nx.set_edge_attributes(G, attr_exp)

        turbs = list(range(1, n_turbines + 1))
        turbs_per_string = Layout_Aux.interval_extract(turbs, n_strings)

        list_connector = list(range(0, n_strings, n_string_to_connector))

        h = 1
        l = 1

        count_nodes = substation_node
        connector_node = substation_node

        for s in range(n_strings):
            if s in list_connector:
                count_nodes +=1
                G.add_node(count_nodes)
                att_w = {count_nodes:{
                        'name' : "Connector_node",
                        'coords' : (s+(n_string_to_connector/2)-0.5,0),
                        'level' : 'hub',
                        'power' : 0
                }}
                nx.set_node_attributes(G, values=att_w)

                G.add_edge(count_nodes, substation_node)
                attr_es = {(count_nodes, substation_node):{
                        'name' : "feeder_cable",
                        'level' : 'exp_cable_island',
                        'visible': True,
                        'p_limit': None
                }}
                nx.set_edge_attributes(G, attr_es)

                connector_node = count_nodes

            for t in turbs_per_string[s]:
                count_nodes +=1
                G.add_node(count_nodes)
                att_w = {count_nodes:{
                        'name' : "WTG_%i" %t,
                        'coords' : (s,h),
                        'level' : 'device',
                        'power' : 1
                }}
                nx.set_node_attributes(G, values=att_w)

                G.add_edge(count_nodes, connector_node)
                attr_es = {(count_nodes, connector_node):{
                        'name' : "inter_array_cable",
                        'level' : 'dyn_cable-sub',
                        'visible': True,
                        'p_limit': None
                }}
                nx.set_edge_attributes(G, attr_es)

            h=1
            l += 1

        Layout_Aux.draw_layout(G = G, save_dir = save_dir, show_plot = show_plot, title="Wind_Layout_6")
        return G

    # ---------------------------------------------------------------------
    # Layout 7
    # ---------------------------------------------------------------------
    def layout7_wind(self, n_turbines: int, n_strings: int, substation_node: int, tow_string_shutdown: bool,
                     save_dir=None, show_plot=False):
        """
        .. figure:: /_static/Layout_imgs/Wind_Layout_7.jpg
            :width: 8000px
            :alt: example

            LAYOUT 7: SIMPLE LAYOUT with RING array cables, n_strings=2, n_turbines=6

            
            Levels: 
                onshore substation = 'shore';
                export cable = 'exp_cable';
                offshore substation = 'substation'; 
                array cable = 'array_cable';
                interarray_cable = 'dyn_cable-sub';
                wtg = 'device';

        Layout 7: One substation, one export cable to shore, Ring array cable uniform strings.
        """
        self.check_input_wind(n_turbines, n_strings)
        G = nx.DiGraph()
        G.graph['tow_string_shutdown'] = tow_string_shutdown
        Layout_Aux.add_substation_and_shore(G, n_strings, substation_node)

        if n_turbines == 1:
            node = substation_node + 1
            G.add_node(node)
            nx.set_node_attributes(G, {node: {
                'name': "Wtg_1", 'coords': ((n_strings - 1) / 2, 0),
                'level': 'device', 'power': 1
            }})
            G.add_edge(node, substation_node)
            nx.set_edge_attributes(G, {(node, substation_node): {
                'name': 'array_cable', 'level': 'array_cable',
                'visible': True, 'p_limit': None
            }})
        else:
            turbines = list(range(1, n_turbines + 1))
            turbines_per_string = Layout_Aux.interval_extract(turbines, n_strings)
            node_counter = substation_node

            for s, string_turbines in enumerate(turbines_per_string):
                h = 2
                for i, t in enumerate(string_turbines):
                    if t == string_turbines[0]:
                        cable_name = 'array_cable'
                        cable_level = 'array_cable'
                    else:
                        cable_name = 'inter_array_cable'
                        cable_level = 'dyn_cable-sub'
                    node_counter += 1
                    G.add_node(node_counter)
                    nx.set_node_attributes(G, {node_counter: {
                        'name': f"Wtg_{t}", 'coords': (s, h),
                        'level': 'device', 'power': 1
                    }})
                    if i == 0:
                        G.add_edge(node_counter, substation_node)
                    else:
                        G.add_edge(node_counter, node_counter - 1)
                    nx.set_edge_attributes(G, {(list(G.edges())[-1]): {
                        'name': cable_name, 'level': cable_level,
                        'visible': True, 'p_limit': None
                    }})
                    # RING ARRAY creation
                    if t == string_turbines[-1]:
                        G.add_edge(node_counter, substation_node)
                        nx.set_edge_attributes(G, {(list(G.edges())[-1]): {
                            'name': 'array_cable', 'level': 'array_cable',
                            'visible': True, 'p_limit': None
                        }})

                    h += 3
        Layout_Aux.draw_layout(G, save_dir, show_plot, title="Wind_Layout_7")
        return G
    # ---------------------------------------------------------------------
    # Dispatcher
    # ---------------------------------------------------------------------
    def layout_wind(
                self, n_layout: int, n_turbines: int, n_strings: int,
                n_substations: int = 1, n_exports: int = 1, n_string_to_connector = 6,
                tow_string_shutdown: bool = True, save_dir: str = None, show_plot: bool = True
        ):
        """Select and build the desired wind farm layout."""
        if n_layout == 1:
            return self.layout1_wind(n_turbines, n_strings, substation_node = 1, tow_string_shutdown = tow_string_shutdown, save_dir = save_dir, show_plot = show_plot)
        elif n_layout == 2:
            return self.layout2_wind(n_turbines, n_strings, n_substations, tow_string_shutdown, save_dir, show_plot)
        elif n_layout == 3:
            return self.layout3_wind(n_turbines, n_strings, n_exports, tow_string_shutdown, save_dir, show_plot)
        elif n_layout == 4:
            if n_turbines == 73:
                string_list = [8, 8, 8, 8, 9, 8, 8, 8, 8]
            elif n_turbines == 40:
                string_list = [5, 8, 5, 8, 6, 8]
            else:
                if n_turbines % n_strings != 0:
                    raise ValueError("Layout 4: n_turbines must be divisible by n_strings or modify string_list manually")
                string_list = [n_turbines // n_strings] * n_strings
            return self.layout4_wind(n_turbines, n_strings, 1, string_list, tow_string_shutdown, save_dir, show_plot)
        elif n_layout == 5:
            if n_turbines % n_strings != 0 or n_strings % n_string_to_connector:
                raise ValueError("Layout 5: n_turbines must be divisible by n_strings or n_string_to_connector manually")
            return self.layout5_wind(n_turbines=n_turbines, n_strings=n_strings, substation_node=1, n_string_to_connector = n_string_to_connector, tow_string_shutdown = tow_string_shutdown, save_dir = save_dir, show_plot = show_plot)
        elif n_layout == 6:
            if n_turbines % n_string_to_connector:
                raise ValueError("Layout 6: n_turbines must be divisible by n_string_to_connector manually")
            return self.layout6_wind(n_turbines=n_turbines, n_strings=n_turbines, substation_node=1, n_string_to_connector = n_string_to_connector, tow_string_shutdown = tow_string_shutdown, save_dir = save_dir, show_plot = show_plot)
        if n_layout == 7:
            return self.layout7_wind(n_turbines, n_strings, substation_node = 1, tow_string_shutdown = tow_string_shutdown, save_dir = save_dir, show_plot = show_plot)
        else:
            _e = f'Layout selected :´{n_layout}´ for wind technology. The present scenario does not exists'
            logging.error(_e)
            raise ValueError (_e)



# ---------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------
if __name__ == "__main__":

    lw = Layout_Wind()
    G = lw.layout_wind(
        n_layout=7,
        n_turbines=6,
        n_strings=2,
        n_substations=1,
        n_exports=1,
        n_string_to_connector = 1,
        tow_string_shutdown = True,
        save_dir = None,
        show_plot=True
    )