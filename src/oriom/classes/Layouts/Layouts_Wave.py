import logging
import os
import networkx as nx
import matplotlib.pyplot as plt

from oriom.classes.Layouts.Layout_Auxiliary import Layout_Aux

COLOR = 'skyblue'

class Layout_Wave():
    """Wave energy system layout generator with multiple topology options."""

    # -------------------- UTILITIES -------------------- #
    def check_input_wave(self, n_wec: int, n_strings: int):
        """Ensure that n_wec is divisible by n_strings."""
        if (n_wec % n_strings) != 0:
            logging.error('Layout: n_wec must be divisible by n_strings')
            raise ValueError('Layout: n_wec must be divisible by n_strings')


    # ---------------------------------------------------------------------
    # Layout 1
    # ---------------------------------------------------------------------
    def layout1_wave(self, n_wec: int, n_strings: int, substation_node: int, tow_string_shutdown: bool,
                     save_dir=None, show_plot=False):
        """
        .. figure:: /_static/Layout_imgs/Wave_Layout_1.jpg
            :width: 8000px
            :alt: esempio

            LAYOUT 1: SIMPLE LAYOUT, n_substations = 1, n_strings=2, n_wec=6

        Layout 1: One substation, one export cable to shore, uniform strings.
        """
        self.check_input_wave(n_wec, n_strings)
        G = nx.DiGraph()
        G.graph['tow_string_shutdown'] = tow_string_shutdown
        Layout_Aux.add_substation_and_shore(G, n_strings, substation_node)

        if n_wec == 1:
            node = substation_node + 1
            G.add_node(node)
            nx.set_node_attributes(G, {node: {
                'name': "WEC_1", 'coords': ((n_strings - 1) / 2, 0),
                'level': 'device', 'power': 1
            }})
            G.add_edge(node, substation_node)
            nx.set_edge_attributes(G, {(node, substation_node): {
                'name': 'array_cable', 'level': 'array_cable',
                'visible': True, 'p_limit': None
            }})
        else:
            wec = list(range(1, n_wec + 1))
            wec_per_string = Layout_Aux.interval_extract(wec, n_strings)
            node_counter = substation_node
            for s, string_wec in enumerate(wec_per_string):
                h = 2
                for i, t in enumerate(string_wec):
                    node_counter += 1
                    G.add_node(node_counter)
                    nx.set_node_attributes(G, {node_counter: {
                        'name': f"WEC_{t}", 'coords': (s, h),
                        'level': 'device', 'power': 1
                    }})
                    if i == 0:
                        G.add_edge(node_counter, substation_node)
                    else:
                        G.add_edge(node_counter, node_counter - 1)
                    nx.set_edge_attributes(G, {(list(G.edges())[-1]): {
                        'name': 'array_cable', 'level': 'array_cable',
                        'visible': True, 'p_limit': None
                    }})
                    h += 3

        Layout_Aux.draw_layout(G, save_dir, show_plot, title="Wave_Layout_1", color = COLOR)
        return G

    # ---------------------------------------------------------------------
    # Layout 2
    # ---------------------------------------------------------------------
    def layout2_wave(
            self,
            n_wec: int,
            n_strings: int,
            n_substations: int,
            tow_string_shutdown: bool,
            save_dir=None,
            show_plot=False
    ):
        '''

        .. figure:: /_static/Layout_imgs/Wave_Layout_2.jpg
            :width: 8000px
            :alt: esempio

            LAYOUT 2: DOUBLE FARM REDUNDANT LAYOUT, n_substations=2, n_strings=2, n_wec=8

        This layout allows to create two identical independent farms, each
        with on substation and an export cable. The substations are alsoo connected
        to allow redundancy.
        '''
        if n_wec % n_substations !=0:
            _e = 'N_wec and N_substations must be divisible'
            logging.error('Layout: '+_e)
            raise ValueError(_e)

        n_wecs = int(n_wec/n_substations)
        shore_node = 0
        sub_nodes = []
        Gs = {}
        positions = {}

        conn_offset = 1  # counter

        # Independent farm creations
        for s in range(n_substations):
            sub_node = conn_offset
            sub_nodes.append(sub_node)
            G = self.layout1_wave(
                n_wec=n_wecs,
                n_strings=n_strings,
                substation_node=sub_node,
                tow_string_shutdown = tow_string_shutdown,
                show_plot = False
            )
            Gs[f"G_{s}"] = G
            conn_offset += n_wecs + 1

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

        ## connect substations
        pos = nx.get_node_attributes(G_composed, "coords")
        positions = {}

        x_shift = 0
        for g in Gs.keys():
            for node in Gs[g].nodes:
                if node == shore_node:
                    positions[node] = (pos[node][0] - (n_strings+1)/2, pos[node][1])
                else:
                    positions[node] = (pos[node][0] - x_shift, pos[node][1])
            x_shift += n_strings+1

        names = nx.get_node_attributes(G_composed, "name")
        edges_names = nx.get_edge_attributes(G_composed, "name")
        nx.draw(G_composed, pos=positions, with_labels=True, node_color='lightblue', node_size=100, alpha=0.8, labels=names)
        nx.draw_networkx_edge_labels(G_composed, pos=positions, edge_labels=edges_names, font_size=5)

        if save_dir is not None:
            plt.savefig(os.path.join(save_dir, 'Wave_Layout_2.jpg'))
        else:
            plt.show()
        plt.close()

        return G_composed


    # ---------------------------------------------------------------------
    # Layout 3
    # ---------------------------------------------------------------------
    def layout3_wave(
            self,
            n_wec: int,
            n_strings: int,
            n_exports: int,
            tow_string_shutdown: bool,
            save_dir=None,
            show_plot=False
    ):
        '''

        .. figure:: /_static/Layout_imgs/Wave_Layout_3.jpg
            :width: 8000px
            :alt: esempio

            *LAYOUT 3*: REDUNDANT EXPORT CABLE LAYOUT, n_export_cables=2, n_strings=2, n_wec=6

        This layout is considering one substation to which all the strings
        are connected and multiple export cable to shore to allow for redundancy
        '''
        G = self.layout1_wave(n_wec=n_wec,n_strings=n_strings,substation_node=n_exports, tow_string_shutdown=tow_string_shutdown)

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

        Layout_Aux.draw_layout(G, save_dir, show_plot, title="Wave_Layout_3", color = COLOR)

        return G



    # ---------------------------------------------------------------------
    # Layout 4
    # ---------------------------------------------------------------------
    def layout4_wave(
            self,
            n_wec: int,
            n_strings: int,
            substation_node: int,
            n_string_to_connector: int = 6,
            tow_string_shutdown: bool = False,
            save_dir=None,
            show_plot=False
    ):

        """
        .. figure:: /_static/Layout_imgs/Wave_Layout_4.jpg
            :width: 8000px
            :alt: esempio

            LAYOUT 4: CORPOWER LAYOUT, n_export_cables=1, substation_node=1, n_string_to_connector=6 (Default), n_strings=12, n_wec=150

        CORPOWER layout
        Strings are connected to the same 66 kV feeder cable that bring power to offshore substation
        Vaious power size are implementable
        Args:
            n_string_to_connector (int): Number of string that connect in the same point to the feeder.
                Default value to ´´6´´ as layout CORPOWER
        """

        G = nx.DiGraph()
        G.graph['tow_string_shutdown'] = tow_string_shutdown
        Layout_Aux.add_substation_and_shore(G, n_strings, substation_node)

        list_wec= list(range(1,n_wec+1))
        wec_per_string =  []
        i=0
        order = [12 if i % 2 == 0 else 13 for i in range(n_strings)]
        for o in order:
            string_i = list_wec[i:o+i]
            wec_per_string.append(string_i)
            i+=o

        if sum(order) != n_wec:
            _e = 'Layout: n_wec must be equal to CORPOWER layout strings'
            logging.error(_e)
            raise ValueError(_e)

        h = 4
        l = 2

        count_nodes = substation_node
        connector_node = substation_node
        for s in range(n_strings):
            offset = 1.5 if s % 2 == 0 else 0
            if s == 0 or s % n_string_to_connector == 0:
                count_nodes +=1
                G.add_node(count_nodes)
                att_w = {count_nodes:{
                        'name' : "Connector_node",
                        'coords' : (s+(n_string_to_connector/2)-0.5,1),
                        'level' : 'hub',
                        'power' : 0
                }}
                nx.set_node_attributes(G, values=att_w)

                G.add_edge(count_nodes, connector_node)
                attr_es = {(count_nodes, connector_node):{
                        'name' : "feeder_cable",
                        'level' : 'exp_cable_island',
                        'visible': True,
                        'p_limit': None
                }}
                nx.set_edge_attributes(G, attr_es)

                connector_node = count_nodes

            for t in wec_per_string[s][:]:
                if t < wec_per_string[s][-1]:
                    count_nodes +=1
                    G.add_node(count_nodes)
                    att_w = {count_nodes:{
                            'name' : "WEC_%i" %t,
                            'coords' : (s,h+offset),
                            'level' : 'device',
                            'power' : 1
                    }}
                    nx.set_node_attributes(G, values=att_w)
                    t_1 = t+1
                    G.add_node(count_nodes+1)
                    att_w1 = {count_nodes+1:{
                            'name' : "WEC_%i" %t_1,
                            'coords' : (s,h+offset),
                            'level' : 'device',
                            'power' : 1
                    }}
                    G.add_edge(count_nodes+1,count_nodes)
                    attr_ef = {(count_nodes+1,count_nodes):{
                            'name' : "array_cable",
                            'level' : 'array_cable',
                            'visible': True,
                            'p_limit': None
                    }}
                    nx.set_edge_attributes(G, attr_ef)
                    nx.set_node_attributes(G,values=att_w1)
                    h+=3
                    if t == wec_per_string[s][0]:
                        G.add_edge(count_nodes, connector_node)
                        attr_es = {(count_nodes, connector_node):{
                                'name' : "array_cable",
                                'level' : 'array_cable',
                                'visible': True,
                                'p_limit': None
                        }}
                        nx.set_edge_attributes(G, attr_es)
                else:
                    att_w1 = {count_nodes+1:{
                            'name' : "WEC_%i" %t_1,
                            'coords' : (s,h+offset),
                            'level' : 'device',
                            'power' : 1
                    }}
                    nx.set_node_attributes(G,values=att_w1)
                    count_nodes+=1
            h=4
            l += len(wec_per_string[s])

        Layout_Aux.draw_layout(G, save_dir, show_plot, title="Wave_Layout_4", color = COLOR)
        return G


    # ---------------------------------------------------------------------
    # Layout 5
    # ---------------------------------------------------------------------
    def layout5_wave(
            self,
            n_wec: int,
            n_strings: int,
            substation_node: int,
            n_string_to_connector: int = 1,
            tow_string_shutdown: bool = False,
            save_dir=None,
            show_plot=False
    ):

        """
        Layout with 1 Substation, 1 Array Cable, 1 Connector and n_wec connected to the same connector
        2 mode of use:
            1) The n_wec can be considered as module of the wec, the wec itself might be the connector
            2) Otherwise more devices connected by umbilicals to Connector that goes to Substation
        """

        G = nx.DiGraph()
        G.graph['tow_string_shutdown'] = tow_string_shutdown

        # DEFINING SHORE
        G.add_node(0)
        attr_s = {0: {
                'name' : 'SHORE',
                'coords' : (-4,-1),
                'level' : '',
                'power' : 0
        }}
        nx.set_node_attributes(G, values=attr_s)

        # DEFINING SUBSTATION
        G.add_node(substation_node)
        attr_h = {substation_node: {
                'name' : 'Sub',
                'coords' : (-2,-1),
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

        wecs = list(range(1, n_wec + 1))
        wec_per_string = Layout_Aux.interval_extract(wecs, n_strings)

        h = 1
        l = 1

        count_nodes = substation_node
        connector_node = substation_node
        for s in range(n_strings):
            if s == 0:
                count_nodes +=1
                G.add_node(count_nodes)
                att_w = {count_nodes:{
                        'name' : "Connector_node",
                        'coords' : (s+(n_string_to_connector/2)-0.5,-1),
                        'level' : 'hub',
                        'power' : 0
                }}
                nx.set_node_attributes(G, values=att_w)

                G.add_edge(count_nodes, connector_node)
                attr_es = {(count_nodes, connector_node):{
                        'name' : "feeder_cable",
                        'level' : 'exp_cable_island',
                        'visible': True,
                        'p_limit': None
                }}
                nx.set_edge_attributes(G, attr_es)

                connector_node = count_nodes

            for t in wec_per_string[s]:
                count_nodes +=1
                G.add_node(count_nodes)
                att_w = {count_nodes:{
                        'name' : "WEC_%i" %t,
                        'coords' : (s,h),
                        'level' : 'device',
                        'power' : 1
                }}
                nx.set_node_attributes(G, values=att_w)

                G.add_edge(count_nodes, connector_node)
                attr_es = {(count_nodes, connector_node):{
                        'name' : "array_cable",
                        'level' : 'array_cable',
                        'visible': True,
                        'p_limit': None
                }}
                nx.set_edge_attributes(G, attr_es)

            h=1
            l += 1

        Layout_Aux.draw_layout(G, save_dir, show_plot, title="Wave_Layout_5", color = COLOR)
        return G

    # ---------------------------------------------------------------------
    # Dispatcher
    # ---------------------------------------------------------------------
    def layout_wave(
                self, n_layout: int, n_wec: int, n_strings: int,
                n_substations: int = 1, n_exports: int = 1, n_string_to_connector = 6,
                tow_string_shutdown: bool = False, save_dir: str = None, show_plot: bool = True
        ):
        """Select and build the desired wind farm layout."""
        if n_layout == 1:
            G = self.layout1_wave(n_wec=n_wec, n_strings=n_strings, substation_node=1, tow_string_shutdown = tow_string_shutdown, save_dir = save_dir, show_plot = show_plot)
        elif n_layout == 2:
            G = self.layout2_wave(n_wec=n_wec, n_strings=n_strings,n_substations=n_substations, tow_string_shutdown = tow_string_shutdown, save_dir = save_dir, show_plot = show_plot)
        elif n_layout == 3:
            G = self.layout3_wave(n_wec=n_wec,n_strings=n_strings,n_exports=n_exports, tow_string_shutdown = tow_string_shutdown, save_dir = save_dir, show_plot = show_plot)
        elif n_layout == 4:
            G = self.layout4_wave(n_wec=n_wec, n_strings=n_strings, substation_node=1, n_string_to_connector = n_string_to_connector, tow_string_shutdown = tow_string_shutdown, save_dir = save_dir, show_plot = show_plot)
        elif n_layout == 5:
            G = self.layout5_wave(n_wec=n_wec, n_strings=n_wec, substation_node=1, n_string_to_connector = n_string_to_connector, tow_string_shutdown = tow_string_shutdown, save_dir = save_dir, show_plot = show_plot)
        else:
            _e = f'Layout selected :´{n_layout}´ for wave technology. The present scenario does not exists'
            logging.error(_e)
            raise ValueError (_e)
        return G


if '__main__' in __name__:
    lw = Layout_Wave()
    G = lw.layout_wave(
        n_layout = 4,
        n_wec = 6,
        n_strings = 3,
        n_string_to_connector = 3,
        n_substations = 2,
        n_exports = 1,
        tow_string_shutdown = False
    )

