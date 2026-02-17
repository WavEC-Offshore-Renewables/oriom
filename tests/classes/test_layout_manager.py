# tests/test_layout_aux.py
import unittest

from oriom.classes.Layouts.Layouts_Managers import LayoutManager


def test_layout_manager_all():
    class Dummy:
        pass

    power_farm = Dummy()
    power_farm.wtg_number_devices = 5
    power_farm.wec_number_devices = 3
    power_farm.pv_number_devices = 10

    wtg = Dummy()
    wtg.number_devices = 5
    wtg.number_strings = 1
    wtg.number_substations = 1
    wtg.number_exportcables = 1
    wtg.wtg_layout = 1

    wec = Dummy()
    wec.number_devices = 3
    wec.number_strings = 1
    wec.number_substations = 1
    wec.number_exportcables = 1
    wec.wec_layout = 1

    pv = Dummy()
    pv.number_devices = 10
    pv.number_strings = 1
    pv.number_inverters = 1
    pv.number_substations = 1
    pv.number_mv_transformers = 1
    pv.number_island_per_array_cable = 1
    pv.pv_layout = 1

    result = LayoutManager.build_layouts(power_farm, wtg, wec, pv)

    assert result["G_wind"] is not None
    assert result["G_wave"] is not None
    assert result["G_pv"] is not None


if __name__ == "__main__":
    unittest.main(verbosity=2)

