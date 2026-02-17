import logging
import networkx as nx
from oriom.classes.Layouts.Layout_Auxiliary import Layout_Aux

COLOR = 'yellow'

class Layout_PV:
    """PV energy system layout generator with multiple topology options."""

    def __init__(self):
        self.count_nodes = 1
        self.count_nodes_sub = 0
        self.count_nodes_cb = 0
        self.count_nodes_tf = 0
        self.count_nodes_switcher = 0
        self.count_nodes_inv = 0

        self.spacing_sub = 13
        self.spacing_cb = 7
        self.spacing_tf = 7
        self.spacing_inv = 5
        self.spacing_str = 5

    # ---------------- Helper Functions ----------------
    def _set_node(self, G, node_id, name, coords=None, level=None, power=0):
        G.add_node(node_id)
        attr = {node_id: {'name': name, 'coords': coords, 'level': level, 'power': power}}
        nx.set_node_attributes(G, values=attr)

    def _set_edge(self, G, src, dst, name, level, visible=True, p_limit=None):
        G.add_edge(src, dst)
        attr = {(src, dst): {'name': name, 'level': level, 'visible': visible, 'p_limit': p_limit}}
        nx.set_edge_attributes(G, attr)

    # ---------------- Input Check ----------------
    def check_input_pv(self, n_panels: int, n_strings: int, n_inverters: int,
                       n_substations: int = None, n_mvtransformers: int = 1):
        """The islands of panels must be equal."""
        if n_panels % n_inverters != 0:
            _e = 'Layout: n_panels must be divisible by n_inverter'
            logging.error(_e)
            raise ValueError(_e)
        if (n_panels / n_inverters) % n_strings != 0:
            _e = 'Layout: n_panels/n_inverter must be divisible by n_strings'
            logging.error(_e)
            raise ValueError(_e)
        if n_substations:
            if (n_mvtransformers % n_substations != 0 or
                n_inverters % n_mvtransformers != 0 or
                n_panels % n_inverters != 0):
                _e = 'Layout: PV components must be divisible upstream component'
                logging.error(_e)
                raise ValueError(_e)

    # ---------------- Layout 1 ----------------
    def layout1_pv(
            self,
            n_panels: int,
            n_strings: int,
            n_inverters: int,
            tow_string_shutdown: bool,
            save_dir = None,
            show_plot = False
    ):
        """ 
        .. figure:: /_static/Layout_imgs/Solar_Layout_1.jpg
            :width: 800px
            :alt: esempio

            LAYOUT 1: Inverter = 2, Strings = 2,  n_panels = 36*4 

        Layout with 1 is composed by exp_cable, 1 Substation, Inverter with strings and modules

        """
        self.check_input_pv(n_panels,n_strings,n_inverters)

        G = nx.DiGraph()
        G.graph['tow_string_shutdown'] = tow_string_shutdown
        Layout_Aux.add_substation_and_shore(G, n_strings, substation_node = 1)

        n_panel_per_island = n_panels//n_inverters
        n_panel_per_string = n_panel_per_island//n_strings

        for i in range(1,n_inverters+1):
            self.count_nodes +=1
            s = i-(n_strings-1)/16
            p_per_string = n_panel_per_string
            h=4
            l=1
            self._set_node(G, self.count_nodes, f"Inv_{i}", coords = (i,0), level = 'inverter')
            self._set_edge(G, self.count_nodes, 1, "dyn_cable-sub", level = 'dyn_cable-sub')

            for p in range(1, n_panel_per_island+1):
                self.count_nodes += 1
                pan = "Pv_i%i" %i
                if p < p_per_string:
                    self._set_node(G, self.count_nodes, pan+f"_p{p}", coords = (s,h), level = 'device', power = 1)
                    p_1 = p+1
                    self._set_node(G, self.count_nodes+1, pan+f"_p{p_1}", coords = (s,h), level = 'device', power = 1)
                    self._set_edge(G, self.count_nodes+1, self.count_nodes, "opv-cable", level = 'array_cable')
                    h+=1.5
                else:
                    p_1 = p
                    attr_p1 = {self.count_nodes : {'name' : pan+ f"_p{p_1}", 'coords' : (s,h), 'level': 'device', 'power' : 1 }}
                    nx.set_node_attributes(G, values=attr_p1)
                    p_per_string = p_per_string+n_panel_per_string
                    s += 1/8
                    h = 4

                if p==l:
                    self._set_edge(G, self.count_nodes, self.count_nodes - l, "opv-cable", level = 'array_cable')
                    l+=n_panel_per_string

        Layout_Aux.draw_layout(G, save_dir, show_plot= show_plot, title="Solar_Layout_1", color = COLOR)

        return G
    
    
    # ---------------- Layout 2 ----------------
    def layout2_pv(
            self, n_panels: int, n_strings: int, n_inverters: int, n_mvtransformers: int,
            n_substations: int = 1, n_island_per_array_cable: int = 3, 
            tow_string_shutdown: bool = False, save_dir=None, show_plot=False):
        """

        .. figure:: /_static/Layout_imgs/Solar_Layout_2.jpg
            :width: 8000px
            :alt: esempio
            
            LAYOUT 2: n_substations = 6, n_island_per_array_cable = 3, Inverter = 12, Strings = 2, n_panels = 36*6 

        This layout create a complex pv farm layout with the resolution of the inverter level.
            The power node are the lowest node implemented (inverter) with the power of pv module connected. 
            Possibility to reduce resolution adjusting this code to string or PV level (high computational time)

        For this layout are presents:
          - 1 offshore substation 
          - N number (n_island_per_array_cable) of array island connected to it
          - n_substations represent the number of island

        SCHEME:
            - Shore - Exp_cable - Substation - Exp_cable_island - 
                Island_1 - Array_cable - Island_2 ... 
                    |  CB - dyn_cable_sub - Transf - cable_cb - Switch - cable_trans - invert -  

        Args:
            n_panels (: int): Total number of solar panels
            n_strings (: int): Number of string per each inverter
            n_inverters (: int): Total Number of inverter
            n_mvtransformers (: int): Number of Transformer
            n_substations (: int = 1): Total Number of solar Islands
            n_island_per_array_cable (int): Number of island that share the same array cable
                Default value to ´´1´´
            tow_string_shutdown (bool): Parameter that define if towing a device disconnect downstream component
                Default to False
            save_dir (: dir): Directory to save the graph
            show_plot (: bool): Boolean to decide if show the plot
        """

        self.check_input_pv(n_panels, n_strings, n_inverters, n_substations, n_mvtransformers)
        n_circuit_breakers = n_mvtransformers
        G = nx.DiGraph()
        G.graph['tow_string_shutdown'] = tow_string_shutdown
        Layout_Aux.add_substation_and_shore(G, n_strings, substation_node=1, pv=True)

        for sub in range(1, n_substations + 1):
            if (sub - 1) % n_island_per_array_cable == 0 or sub == 1:
                edge_island = 1
                level_edge = 'exp_cable_island'
                name_edge = 'export_cable_island'
            else:
                edge_island = self.count_nodes_sub
                level_edge = 'array_cable'
                name_edge = 'array_cable'

            x_sb = sub * self.spacing_sub
            self.count_nodes += 1
            self._set_node(G, self.count_nodes, f"Island_{sub}", coords=(x_sb, -5), level='island')
            self._set_edge(G, self.count_nodes, edge_island, name_edge, level_edge)
            self.count_nodes_sub = self.count_nodes

            circuit_braker_per_sub = n_circuit_breakers // n_substations
            for cb in range(1, circuit_braker_per_sub + 1):
                x_cb = x_sb + cb * self.spacing_cb
                self.count_nodes += 1
                self._set_node(G, self.count_nodes, f"CB_{cb}", coords=(x_cb, -4), level='circuit_braker')
                self._set_edge(G, self.count_nodes, self.count_nodes_sub, 'cable_cb-subst_connector', 'cable_cb')
                self.count_nodes_cb = self.count_nodes

                transformers_per_cb = n_mvtransformers // n_circuit_breakers
                for t in range(1, transformers_per_cb + 1):
                    x_tf = x_cb + (t - 1) * self.spacing_tf
                    self.count_nodes += 1
                    self._set_node(G, self.count_nodes, f"Transf_{cb}_{t}", coords=(x_tf, -3), level='mv_transformer')
                    self._set_edge(G, self.count_nodes, self.count_nodes_cb, 'cable_transf-cb', 'cable_transf')
                    self.count_nodes_tf = self.count_nodes

                    for t_sw in range(1, transformers_per_cb + 1):
                        x_sw = x_cb + (t_sw - 1) * self.spacing_tf
                        self.count_nodes += 1
                        self._set_node(G, self.count_nodes, f"Switcher_{cb}_{t_sw}", coords=(x_sw, -2), level='switcher')
                        self._set_edge(G, self.count_nodes, self.count_nodes_tf, 'cable_sw-trans', 'cable_switch')
                        self.count_nodes_switcher = self.count_nodes

                        inverter_per_tr = n_inverters // n_mvtransformers
                        n_panel_per_inv = n_panels // n_inverters
                        for i in range(1, inverter_per_tr + 1):
                            x_inv = x_tf + (i - 1) * self.spacing_inv
                            self.count_nodes += 1
                            self._set_node(G, self.count_nodes, f"Inv_{cb}_{t}_{i}", coords=(x_inv, -1),
                                           level='inverter', power=n_panel_per_inv)
                            self._set_edge(G, self.count_nodes, self.count_nodes_switcher, 'cable_in-sw', 'cable_inv')
                            self.count_nodes_inv = self.count_nodes

        Layout_Aux.draw_layout(G, save_dir, show_plot=show_plot, title="Solar_Layout_2", color = COLOR)
        return G


    # ---------------- Layout 3 ----------------
    def layout3_pv(self, n_strings: int, n_inverters: int, n_mvtransformers: int,
                   n_substations: int, tow_string_shutdown: bool, save_dir=None, show_plot=False):
        """
        UPSALLA layout implemented
        NOTE Layout not available
        """
        G = nx.DiGraph()
        G.graph['tow_string_shutdown'] = tow_string_shutdown
        if n_substations is None:
            n_substations = 1
        self._set_node(G, 0, 'SHORE', coords=(1, -3), level='', power=0)
        self.count_nodes = 0

        if n_inverters % n_mvtransformers != 0:
            logging.error('Layout: "n_inverters" must be divisible by "n_mvtransformers"')
            raise ValueError('Layout: "n_inverters" must be divisible by "n_mvtransformers"')
        n_inv_per_transf = n_inverters // n_mvtransformers

        if n_mvtransformers % n_substations != 0:
            logging.error('Layout: "nmv_transformers" must be divisible by "n_substations"')
            raise ValueError('Layout: "nmv_transformers" must be divisible by "n_substations"')
        n_mvtransformers = n_mvtransformers // n_substations

        for sub in range(1, n_substations + 1):
            self.count_nodes += 1
            self._set_node(G, self.count_nodes, 'Sub', coords=((n_substations + 1) / 2 - (sub - 1), -2),
                           level='substation')
            self._set_edge(G, self.count_nodes, 0, 'export_cable', 'exp_cable')
            count_hub = self.count_nodes
            j = 0
            for t in range(1, int(n_mvtransformers) + 1):
                self.count_nodes += 1
                h=0
                j+=1
                self._set_node(G, self.count_nodes, f"MV_transformer_{t}", coords = (j,-1), level='mv_transformer')
                self._set_edge(G, self.count_nodes, count_hub, 'dyn_cable-sub', 'dyn_cable-sub')
                node_transf = self.count_nodes
                s = (n_substations + 1) / 2 - (sub - 1) + (2 * (n_mvtransformers + 1) / 2 - 2 * (t - 2))

                for i in range(1, n_inv_per_transf + 1):
                    self.count_nodes += 1
                    m = s + (n_inv_per_transf+1/2-(i-1))
                    inv_i = f"Inverter_{t}_i{i}"
                    self._set_node(G, self.count_nodes, inv_i, coords=(m,h), level='inverter')
                    self._set_edge(G, self.count_nodes, node_transf, 'dyn_cable-sub', 'dyn_cable-sub')
                    node_inv = self.count_nodes
                    p= h +0.5
                    for st in range(1, n_strings+1):
                        self.count_nodes += 1
                        l = (s+n_strings)/2 - ((st-1))
                        array_inv = f"array_{i}_i{st}"
                        self._set_node(G, self.count_nodes, array_inv, coords=(l,p), level='device', power = 1)
                        self._set_edge(G, self.count_nodes, node_inv, 'opv-cable', 'array_cable')
                   
        Layout_Aux.draw_layout(G, save_dir, show_plot=show_plot, title="Solar_Layout_3", color = COLOR)
        return G

    # ---------------- Layout Selector ----------------
    def layout_pv(self, n_layout: int, n_panels: int, n_strings: int, n_inverters: int,
                  n_mvtransformers: int = 1, n_island_per_array_cable: int = 1, 
                  n_substations: int = 1,  tow_string_shutdown: bool = False,
                  save_dir: str = None, show_plot: bool = True):
        """
        Function to select and create the layout

        Args:
            n_layout (:obj:`int`): Type of layout.
            n_panels (:obj:`int`): Total number of panels.
            n_strings (:obj:`int`): Number of strings or number of strings per inverter.
            n_inverters (:obj:`int`): Number of inverters.
            n_substations (:obj:`int`): Number of substations. Defaults to `1`.
            n_mvtransformers (:obj:`int`): Number of transformers. Defaults to `1`.
            number_island_per_array_cable (:obj:`int`): Number of transformers. Defaults to `1`.
            save_dir (:obj:`str`, *optional*): Path dir to save graph representation. Defaults to `None`.
        Returns:
            :obj:`nx.DiGraph`: a graph representing the PV system.
        """
        if n_layout == 1:
            return self.layout1_pv(n_panels, n_strings, n_inverters, tow_string_shutdown, save_dir, show_plot)
        elif n_layout == 2:
            if n_substations > n_island_per_array_cable and n_substations % n_island_per_array_cable != 0:
                _e = "number of solar substation must be divisable per n_island_per_array_cable"
                logging.error(_e)
                raise ValueError(_e)
            return self.layout2_pv(n_panels, n_strings, n_inverters, n_mvtransformers,
                                   n_substations, n_island_per_array_cable, tow_string_shutdown, save_dir, show_plot)
        elif n_layout == 3:
            return self.layout3_pv(n_strings, n_inverters, n_mvtransformers, n_substations, tow_string_shutdown,
                                   save_dir, show_plot)
        else:
            _e = f'Layout selected :´{n_layout}´ for pv technology. The present scenario does not exist'
            logging.error(_e)
            raise ValueError(_e)
        

if '__main__' in __name__:
    lw = Layout_PV()
    G_pv = lw.layout_pv(
        n_layout = 1, 
        n_panels = 36*2,
        n_strings = 2,
        n_inverters= 2,
        n_mvtransformers = 2,
        n_island_per_array_cable = 3,
        n_substations = 6,
        tow_string_shutdown = False
    )