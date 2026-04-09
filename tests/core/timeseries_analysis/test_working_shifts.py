import unittest
import os
from oriom.classes.Operations.InspectionSite import InspectionSite
from oriom.classes.Vessel import Vessel

from oriom.classes.DefineOperationTechs import Define_operation

from oriom.core.timeseries_analysis.working_shifts import working_shifts


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

class TestWorkingShifts(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        operation_1 = InspectionSite(
                id_ = 'ofw_OP001',
                name = 'Inspectionsite_1',
                overnight_stay=False,
                periodicity=1,
                tech_per_device=4,
                tech_cost=200,
                dur_per_device=8,
                device_shutdown=False,
                level='device',
                vessel1_id='V005',
                vessel1_qt=5,
                intervened_wtg=20,
                rov_drone=None
        )
        Define_operation.define_vessels(
                operation=operation_1,
                file_vessels = file_vessels,
                file_fuel_density = file_fuel_density,
                file_fuel_cons = file_fuel_cons,
                file_load_factor = file_load_factor,
                vessels = vessels
        )

        operation_2 = InspectionSite(
                id_ = 'ofw_OP002',
                name = 'Inspectionsite_2',
                overnight_stay=False,
                periodicity=1,
                tech_per_device=4,
                tech_cost=200,
                dur_per_device=6,
                device_shutdown=False,
                level='device',
                vessel1_id='V005',
                vessel1_qt=5,
                intervened_wec=66,
                rov_drone=None,
                to_group_with=operation_1
        )
        Define_operation.define_vessels(
                operation=operation_2,
                file_vessels = file_vessels,
                file_fuel_density = file_fuel_density,
                file_fuel_cons = file_fuel_cons,
                file_load_factor = file_load_factor,
                vessels = vessels
        )
        operation_3 = InspectionSite(
                id_='ofw_OP003',
                name='Inspectionsite_3',
                overnight_stay=False,
                periodicity=1,
                tech_per_device=4,
                tech_cost=200,
                dur_per_device=11,
                device_shutdown=False,
                level='device',
                vessel1_id='V005',
                vessel1_qt=5,
                intervened_wtg=20,
                rov_drone=None
        )
        Define_operation.define_vessels(
                operation=operation_3,
                file_vessels = file_vessels,
                file_fuel_density = file_fuel_density,
                file_fuel_cons = file_fuel_cons,
                file_load_factor = file_load_factor,
                vessels = vessels
        )
        operation_4 = InspectionSite(
                id_ = 'ofw_OP004',
                name = 'Inspectionsite_4',
                overnight_stay=False,
                periodicity=1,
                tech_per_device=4,
                tech_cost=200,
                dur_per_device=5,
                device_shutdown=False,
                level='device',
                vessel1_id='V005',
                vessel1_qt=5,
                intervened_wtg=20,
                rov_drone='rov_1'
        )
        Define_operation.define_vessels(
                operation=operation_4,
                file_vessels = file_vessels,
                file_fuel_density = file_fuel_density,
                file_fuel_cons = file_fuel_cons,
                file_load_factor = file_load_factor,
                vessels = vessels
        )
        self.work_shifts_1,self.data_1 = working_shifts(
                operation=operation_1,
                duration_shift=12,
                transit=1,
                transit_between_devices=0.5,
                operation_to_group_with=operation_1.to_group_with
        )
        self.work_shifts_2,self.data_2 = working_shifts(
                operation=operation_2,
                duration_shift=12,
                transit=1,
                transit_between_devices=0.5,
                operation_to_group_with=operation_1
        )

        self.work_shifts_3,self.data_3 = working_shifts(
                operation=operation_3,
                duration_shift=12,
                transit=1,
                transit_between_devices=0.5,
                operation_to_group_with=operation_3.to_group_with
        )

        self.work_shifts_4,self.data_4 = working_shifts(
                operation=operation_4,
                duration_shift=12,
                transit=1,
                transit_between_devices=0.5,
                operation_to_group_with=operation_4.to_group_with
        )

    def test_case_1(self):

        self.assertEqual(self.work_shifts_1['number_shifts_main'], 1)
        self.assertEqual(self.work_shifts_1['number_shifts_last'], 1)
        self.assertEqual(self.work_shifts_1['duration_shift_main'], 11.0)
        self.assertEqual(self.work_shifts_1['duration_shift_last'], 11.0)

        self.assertEqual(self.data_1['id_main'],'ofw_op001')
        self.assertEqual(self.data_1['days_main'], 2)
        self.assertEqual(self.data_1['rov_main'],False)

    def test_case_2(self):
        self.assertEqual(self.work_shifts_2['number_shifts_main'], 3)
        self.assertEqual(self.work_shifts_2['number_shifts_last'], 4)
        self.assertEqual(self.work_shifts_2['duration_shift_main'], 11.0)
        self.assertEqual(self.work_shifts_2['duration_shift_last'], 9.0)

        self.assertEqual(self.data_2['id_main'],'ofw_op001')
        self.assertEqual(self.data_2['days_main'], 3)
        self.assertEqual(self.data_2['rov_main'],False)
        self.assertEqual(self.data_2['id_grouped'],'ofw_op002')
        self.assertEqual(self.data_2['days_grouped'], 7)
        self.assertEqual(self.data_2['rov_grouped'],False)

    def test_case_3(self):
        self.assertEqual(self.work_shifts_3['number_shifts_main'], 4)
        self.assertEqual(self.work_shifts_3['number_shifts_last'], 1)
        self.assertEqual(self.work_shifts_3['duration_shift_main'], 12.0)
        self.assertEqual(self.work_shifts_3['duration_shift_last'], 7.5)

        self.assertEqual(self.data_3['id_main'],'ofw_op003')
        self.assertEqual(self.data_3['days_main'], 5)
        self.assertEqual(self.data_3['rov_main'],False)

    def test_case_4(self):
        self.assertEqual(self.work_shifts_4['number_shifts_main'], 4)
        self.assertEqual(self.work_shifts_4['number_shifts_last'], 0)
        self.assertEqual(self.work_shifts_4['duration_shift_main'], 7.0)
        self.assertEqual(self.work_shifts_4['duration_shift_last'], 0)

        self.assertEqual(self.data_4['id_main'],'ofw_op004')
        self.assertEqual(self.data_4['days_main'], 4)
        self.assertEqual(self.data_4['rov_main'],True)


if __name__ == '__main__':
    unittest.main()