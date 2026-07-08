import unittest
from oriom.domain.Layouts.Layouts_Managers import LayoutManager


class TestLayoutManager(unittest.TestCase):

    def test_layout_manager_all(self):
        class Dummy:
            pass

        power_farm = Dummy()
        power_farm.wtg_number_devices = 5
        power_farm.wec_number_devices = 3
        power_farm.pv_number_devices = 10

        wtg = Dummy()
        wtg.number_devices = 5
        wtg.number_strings = 1
        wtg.n_string_to_connector = 1
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

        self.assertIsNotNone(result["G_wind"])
        self.assertIsNotNone(result["G_wave"])
        self.assertIsNotNone(result["G_pv"])


if __name__ == "__main__":
    unittest.main(verbosity=2)