# oriom/layout/manager.py
import logging
from typing import Optional
from networkx import DiGraph

from oriom.classes.Layouts.Layouts_Wind import Layout_Wind
from oriom.classes.Layouts.Layouts_Wave import Layout_Wave
from oriom.classes.Layouts.Layouts_PV import Layout_PV


class LayoutManager:
    @staticmethod
    def build_layouts(power_farm, wtg, wec, pv, graph_dir = None) -> dict[str, Optional[DiGraph]]:
        G_wind = G_wave = G_pv = None

        if getattr(power_farm, "wtg_number_devices", 0) and wtg.number_devices > 0:
            G_wind = Layout_Wind().layout_wind(
                n_layout=wtg.wtg_layout,
                n_turbines=wtg.number_devices,
                n_strings=wtg.number_strings,
                n_substations=wtg.number_substations,
                n_exports=wtg.number_exportcables,
                tow_string_shutdown = getattr(wtg, "tow_string_shutdown", True),
                save_dir=graph_dir, 
                show_plot=False
            )
            logging.info("Layout: Wind farm layout defined")

        if getattr(power_farm, "wec_number_devices", 0) and wec.number_devices > 0:
            G_wave = Layout_Wave().layout_wave(
                n_layout=wec.wec_layout,
                n_wec=wec.number_devices,
                n_strings=wec.number_strings,
                n_substations=getattr(wec, "number_substations", 1),
                n_exports=getattr(wec, "number_exportcables", 1),
                tow_string_shutdown = getattr(wec, "tow_string_shutdown", False),
                save_dir=graph_dir, 
                show_plot=False
            )
            logging.info("Layout: Wave farm layout defined")

        if power_farm.pv_number_devices is not None:
            G_pv = Layout_PV().layout_pv(
                n_layout=pv.pv_layout,
                n_panels=pv.number_devices,
                n_strings=pv.number_strings,
                n_inverters=pv.number_inverters,
                n_substations=pv.number_substations,
                n_mvtransformers=pv.number_mv_transformers,
                n_island_per_array_cable = pv.number_island_per_array_cable,
                tow_string_shutdown = getattr(pv, "tow_string_shutdown", False),
                save_dir=graph_dir, 
                show_plot=False,
            )
            logging.info("Layout: PV farm layout defined")

        return {"G_wind": G_wind, "G_wave": G_wave, "G_pv": G_pv}
   