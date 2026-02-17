import os
import networkx as nx
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt


class Layout_Aux():
    """Auxiliary class with shared funciotns for Layout classes"""
    @staticmethod
    def add_substation_and_shore(G, n_strings, substation_node = 1, pv = False):
            """
            Add the shore and substation nodes, and the export cable between them.
            Args:
                G (networkx):
                n_strings (int): number of string
                substation_node (int): number of substation node
                pv (bool): Correction of y coordinates if pv tech. Default to ``False``
            """
            if pv:
                shore_y = -7
                sub_y = shore_y + 1
            else:
                shore_y = -3
                sub_y = shore_y + 2

            G.add_node(0)
            nx.set_node_attributes(G, {
                0: {
                    'name': 'SHORE',
                    'coords': ((n_strings - 1) / 2, shore_y),
                    'level': 'shore',
                    'power': 0
                }
            })
            # SUBSTATION
            G.add_node(substation_node)
            nx.set_node_attributes(G, {
                substation_node: {
                    'name': 'Sub',
                    'coords': ((n_strings - 1) / 2, sub_y),
                    'level': 'substation',
                    'power': 0
                }
            })
            # EXPORT CABLE
            G.add_edge(substation_node, 0)
            nx.set_edge_attributes(G, {
                (substation_node, 0): {
                    'name': 'export_cable',
                    'level': 'exp_cable',
                    'visible': True,
                    'p_limit': None
                }
            })
            return G


    @staticmethod
    def draw_layout(G, save_dir=None, show_plot=False, title=None, color = 'grey'):
        """Draw or save the layout graph."""
        pos = nx.get_node_attributes(G, "coords")
        names = nx.get_node_attributes(G, "name")
        edges_names = nx.get_edge_attributes(G, "name")

        plt.figure()
        nx.draw(G, pos=pos, font_size=7, node_size=100, node_color=color, with_labels=True, arrows=True, labels=names)
        nx.draw_networkx_edge_labels(G, pos=pos, edge_labels=edges_names, font_size = 4)
        pos = nx.get_node_attributes(G, "coords")
        for u, v, data in G.edges(data=True):
            if 'rad' in data:
                nx.draw_networkx_edges(G, pos, edgelist=[(u,v)], connectionstyle=f'arc3,rad={data["rad"]}')

        if save_dir is not None:
            plt.savefig(os.path.join(save_dir, f'{title}.jpg'))
        if show_plot:
            plt.show()
        plt.close()



    @staticmethod
    def interval_extract(n_devices, n_times):
        """
        Divide sequence of dvices in n_times (string)
        Example: [1,2,3,4,5,6], n_times=3 → [[1,2], [3,4], [5,6]]
        """
        n_devices = sorted(set(n_devices))

        output = []
        start = 0
        element_per_group = len(n_devices)//n_times if len(n_devices)//n_times != 0 else len(n_devices) % n_times
        n_times += 1 if len(n_devices) % n_times else n_times

        for i in range(n_times):
            end = start + element_per_group
            if end > len(n_devices):
                output.append(n_devices[start:])
            else:
                output.append(n_devices[start:end])
            start = end

        return [grp for grp in output if grp]
