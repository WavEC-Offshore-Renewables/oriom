import unittest
import os
from copy import deepcopy
from datetime import datetime
from datetime import timedelta

from oriom.classes.Operations.InspectionSite import InspectionSite
from oriom.classes.Operations.InspectionPort import InspectionPort
from oriom.classes.Operations.CorrectiveMajor import CorrectiveMajor
from oriom.classes.Operations.OperationTow import OperationTow
from oriom.classes.OperationsStat.InspectionSiteStat import InspectionSiteStat
from oriom.classes.OperationsStat.InspectionPortStat import InspectionPortStat
from oriom.classes.OperationsStat.CorrectiveStat import CorrectiveStat
from oriom.classes.OperationsStat.OperationTowStat import OperationsTowStat
from oriom.classes.Vessel import Vessel
from oriom.core.builders.DefineOperationTechs import Define_operation


file_vessels=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels.yaml')
file_fuel_cons=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_fuels.yaml')
file_load_factor=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_loads.yaml')
file_fuel_density=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_densities.yaml')

vessels_obj = Vessel.get_vessels_from_yaml(
        file_path = file_vessels,
        file_fuel_density = file_fuel_density,
        file_fuel_cons = file_fuel_cons,
        file_load_factor = file_load_factor
)

vessels = {ves.id: ves for ves in vessels_obj}


class TestOperationStat(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        file_inspection_site=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'operations_inspections_site.yaml')
        file_inspection_port=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'operations_inspections_port.yaml')
        file_correctivemajor=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'operations_corrective_major.yaml')
        file_operationtow=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'operations_tow.yaml')

        operations_tow = OperationTow.get_operations_from_yaml(file_operationtow)
        self.run_dir = os.path.join(os.getcwd(), 'tests', 'test_files', 'statistical_analysis')
        self.operations_tow_stat = []

        for op in operations_tow:
            Define_operation.define_vessels(
                    operation=op,
                    file_vessels = file_vessels,
                    file_fuel_density = file_fuel_density,
                    file_fuel_cons = file_fuel_cons,
                    file_load_factor = file_load_factor,
                    vessels = vessels
            )
            try:
                self.operations_tow_stat.append(
                    OperationsTowStat(
                        op,
                        50,
                        self.run_dir
                    )
                )
            except: FileNotFoundError
        self.operations_inspect_site = InspectionSite.get_inspections_from_yaml(
                file_path=file_inspection_site
        )
        self.operations_inspect_port = InspectionPort.get_inspections_from_yaml(
                file_path=file_inspection_port,
                towing_operations=operations_tow
        )
        self.operations_corr_major = CorrectiveMajor.get_operations_from_yaml(
                file_path=file_correctivemajor,
                towing_operations=operations_tow
        )

    def test_inspectionsitestat(self):
        for inspection in self.operations_inspect_site:
            if inspection.id=='owc_cpo_a1':
                inspection_stat_site = InspectionSiteStat(
                    inspection=inspection,
                    PERCENTILE=50,
                    run_dir=self.run_dir,
                )
            else: break

        self.assertEqual(inspection_stat_site.id, 'owc_cpo_a1')
        self.assertIsInstance(inspection_stat_site.dur_total_dict,dict)
        list_months = [str(c) for c in range(1,13)]
        self.assertEqual(list(inspection_stat_site.dur_total_dict.keys()),list_months)
        self.assertEqual(inspection_stat_site.insp_class.months, [4,5,10,11])

    def test_inspectionportstat(self):
        for inspection in self.operations_inspect_port:
            if inspection.id=='owc_cpo_a3':
                inspection_stat_port = InspectionPortStat(
                    inspection=inspection,
                    PERCENTILE=50,
                    run_dir=self.run_dir,
                    n_port_inspections={"ofw": 2, "owc":2, "opv": 2},
                    operations_tow_stat=self.operations_tow_stat,
                    shift=24
                )
            else: break
        self.assertEqual(inspection_stat_port.id, 'owc_cpo_a3')
        self.assertIsInstance(inspection_stat_port.dur_total_dict,dict)

    def test_correctivestatsite(self):
        for op in self.operations_corr_major:
            if op.id == 'owc_op101':
                break
        op_corr = op
        Define_operation.define_vessels(
                operation=op_corr,
                file_vessels = file_vessels,
                file_fuel_density = file_fuel_density,
                file_fuel_cons = file_fuel_cons,
                file_load_factor = file_load_factor,
                vessels = vessels
        )
        operation_corr_site = CorrectiveStat(
            operation=op_corr,
            PERCENTILE=50,
            run_dir=self.run_dir,
            operations_tow_stat=self.operations_tow_stat
        )
        self.assertIsInstance(operation_corr_site.dur_net_site_dict,dict)
        list_months = [str(c) for c in range(1,13)]
        self.assertEqual(list(operation_corr_site.wait_start_dict.keys()),list_months)
        self.assertEqual(operation_corr_site.tow_to_port_dict,None)

    def test_correctivestatport(self):
        for op_corr in self.operations_corr_major:
            if op_corr.id == 'ofw_op103':
                operation_corr_port = CorrectiveStat(
                    operation=op_corr,
                    PERCENTILE=50,
                    run_dir=self.run_dir,
                    operations_tow_stat=self.operations_tow_stat
                )

        self.assertEqual(operation_corr_port.tow_to_site_dict['6'], 19.39 )
        self.assertEqual(operation_corr_port.tow_to_port_dict['1'], 195.83)
        self.assertEqual(operation_corr_port.vessel1.id, 'v001')


if __name__ == '__main__':

    unittest.main()