# tests/aux_operation.py
import os
import unittest
import types
import networkx as nx
from copy import deepcopy

from oriom.utils import aux_operation
from oriom.core.builders.DefineOperationTechs import Define_operation
from oriom.classes.Operations.CorrectiveMajor import CorrectiveMajor
from oriom.classes.Operations.CorrectiveMinor import CorrectiveMinor
from oriom.classes.Operations.OperationTow import OperationTow
from oriom.classes.Vessel import Vessel

# ---------------------------
# Helpers / fakes for tests
# ---------------------------

class FakeFailure:
    """Simple helper class to mimic a Failure object."""
    def __init__(self, operation_triggered, maintenance_strategy, preferred_month=None):
        self.operation_triggered = operation_triggered
        self.maintenance_strategy = maintenance_strategy
        self.preferred_month = preferred_month


class FakeTechObj:
    """Simple helper class to mimic wtg/wec/pv objects in define_device_at_port."""
    def __init__(self, n_device_at_port, n_device_stored_at_port):
        self.n_device_at_port = n_device_at_port
        self.n_device_stored_at_port = n_device_stored_at_port

class FakeTowOp:
    """Simple helper class to mimic an OperationTow object."""
    def __init__(self, _id, name, tow_to_port = False):
        self.id = _id
        self.name = name
        self.tow_to_port = tow_to_port

class FakeOpTOW:
    """Simple helper class to mimic an OperationTow object."""
    def __init__(self,_id, name):
        self.id = _id
        self.name = name
        self.op_tow_site = None
        self.op_tow_port = None
        self.op_tow_site_port = None
        
def make_graph_with_levels(node_lvls=(), edge_lvls=()):
    G = nx.DiGraph()
    # Put a couple of nodes/edges with given level tags
    G.add_node(0, name="SHORE", level="shore")
    for i, lv in enumerate(node_lvls, start=1):
        G.add_node(i, level=lv)
    # Add edges and label their level
    last = 0
    for i, lv in enumerate(edge_lvls, start=1):
        G.add_edge(last, i)
        nx.set_edge_attributes(G, {(last, i): {"level": lv}})
        last = i
    return G


# ---------------------------
# aux_operation.level_component_check
# ---------------------------
class TestLevelComponentCheck(unittest.TestCase):
    def setUp(self):
        # Graphs keyed as in tech_map: {'G_wind': 'ofw', 'G_pv': 'opv', 'G_wave': 'owc'}
        self.Gs = {
            "G_wind": make_graph_with_levels(node_lvls=("substation", "device"), edge_lvls=("exp_cable", "array_cable")),
            "G_pv":   make_graph_with_levels(node_lvls=("inverter", "device"), edge_lvls=("array_cable",)),
            "G_wave": make_graph_with_levels(node_lvls=("device",), edge_lvls=("array_cable",)),
        }

    def test_valid_levels_for_specific_tech(self):
        # Objects with 'level' present in corresponding tech graphs
        ops = []
        # 'ofw' -> wind
        a = types.SimpleNamespace(id="ofw_001", level="device")
        # 'opv' -> pv
        b = types.SimpleNamespace(id="opv_007", level="inverter")
        # 'owc' -> wave
        c = types.SimpleNamespace(id="owc_055", level="array_cable")  # allowed because edges carry levels
        ops.extend([a, b, c])

        # Should not raise
        aux_operation.level_component_check(self.Gs, ops, failure=False)

    def test_valid_levels_for_oce_any(self):
        # 'oce' -> check against union of all graphs
        d = types.SimpleNamespace(id="oce_999", level="substation")
        aux_operation.level_component_check(self.Gs, [d], failure=False)  # present in G_wind node levels

    def test_missing_level_raises_keyerror(self):
        # 'opv' with level not present in PV graph -> KeyError
        bad = types.SimpleNamespace(id="opv_010", level="nonexistent_level")
        with self.assertRaises(KeyError):
            aux_operation.level_component_check(self.Gs, [bad], failure=False)

    def test_failure_mode_uses_level_failure(self):
        # In failure=True, code reads 'level_failure'
        ok = types.SimpleNamespace(id="ofw_100", level_failure="device")
        aux_operation.level_component_check(self.Gs, [ok], failure=True)  # should pass

        bad = types.SimpleNamespace(id="owc_200", level_failure="not_there")
        with self.assertRaises(KeyError):
            aux_operation.level_component_check(self.Gs, [bad], failure=True)


    def test_operation_check_identities(self):
        # Create operations with unique ids
        ops = [
            types.SimpleNamespace(id="ofw_001"),
            types.SimpleNamespace(id="opv_002"),
            types.SimpleNamespace(id="owc_003"),
        ]
        # Should not raise
        aux_operation.operation_check_identities(ops)

        # Add a duplicate id
        ops.append(types.SimpleNamespace(id="ofw_001"))  # duplicate

        with self.assertRaises(ValueError) as context:
            aux_operation.operation_check_identities(ops)

        self.assertIn("Duplicate operation id found", str(context.exception))

class TestOperation(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        file_vessels=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels.yaml')
        file_vessels_fuels=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_fuels.yaml')
        file_vessels_loads=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_loads.yaml')
        file_vessels_densities=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_densities.yaml')

        self.op_corr = CorrectiveMajor(
                id_='ofw_OP103',
                name='Corrective_dummy',
                tow_to_port=False,
                tech_required=3,
                tech_cost=300,
                other_costs=19000
        )
        self.op_tow_port = OperationTow(
                id_='ofw_removal_tow',
                name='WTG removal',
                tech_required=3,
                tech_cost=300,
                vessel1_id='V001',
                other_costs=19000
        )
        self.op_tow_site = OperationTow(
                id_='ofw_deploy_tow',
                name='WTG redeploy',
                tech_required=3,
                tech_cost=300,
                vessel1_id='V001',
                other_costs=1000
        )

        vessels_obj = Vessel.get_vessels_from_yaml(
                file_path = file_vessels,
                file_fuel_density = file_vessels_densities,
                file_fuel_cons = file_vessels_fuels,
                file_load_factor = file_vessels_loads
        )

        self.vessels = {ves.id: ves for ves in vessels_obj}

    def test_define_months_operations_specific_failures(self):
        """
        define_months_operations must restrict months to the preferred months of
        failures whose maintenance_strategy contains 'specific'.
        """
        op = CorrectiveMinor(
            id_="ofw051",
            name="Corrective",
            duration_net=2.0,
            device_shutdown=True,
            level="device",
            tech_required=1,
            vessel1_id="CTV1",
        )

        f_specific_1 = FakeFailure(
            operation_triggered="ofw051",
            maintenance_strategy="specific-month",
            preferred_month=3,
        )
        f_specific_2 = FakeFailure(
            operation_triggered="ofw051",
            maintenance_strategy="specific-window",
            preferred_month=5,
        )
        f_other = FakeFailure(
            operation_triggered="ofw051",
            maintenance_strategy="immediate",
            preferred_month=None,
        )

        op.failures = [f_specific_1, f_specific_2, f_other]

        # Before redefinition, all months or defaults are present
        self.assertEqual(op.months, list(range(1, 13)))

        op.define_months_operations()

        self.assertEqual(op.months, [3, 5])


    def test_get_failures_assigns_matching_failures(self):
        """aux_operation.get_failures must allocate failures whose operation_triggered matches operation id."""
        op = CorrectiveMinor(
            id_="ofw050",
            name="Corrective",
            duration_net=2.0,
            device_shutdown=True,
            level="device",
            tech_required=1,
            vessel1_id="CTV1",
        )

        f1 = FakeFailure(operation_triggered="ofw050", maintenance_strategy="immediate")
        f2 = FakeFailure(operation_triggered="ofw999", maintenance_strategy="immediate")

        aux_operation.get_failures(operation=op, failures_list=[f1, f2])

        self.assertIsNotNone(op.failures)
        self.assertEqual(len(op.failures), 1)
        self.assertIs(op.failures[0], f1)



    def test_define_activities(self):
        op_corr = deepcopy(self.op_corr)
        self.assertIsNone(op_corr.activities)

        op_corr.id = 'ofw_op103'
        aux_operation.define_activities(
            operation=op_corr,
                file_activities=os.path.join(
                        os.getcwd(),
                        'tests',
                        'test_files',
                        'inputs',
                        'operations_activities.yaml'
                ),
                distance_to_site=10,
                transit_between_devices = 0.1,
                tow_op = False
        )

        op_tow = deepcopy(self.op_tow_port)
        op_tow.vessel1_id = 'v001'
        Define_operation.define_vessels(
                operation=op_tow,
                file_vessels=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels.yaml'),
                file_fuel_cons=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_fuels.yaml'),
                file_load_factor=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_loads.yaml'),
                file_fuel_density=os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'vessels_densities.yaml'),
                vessels = self.vessels
        )

        aux_operation.define_activities(
                operation=op_tow,
                file_activities=os.path.join(
                        os.getcwd(),
                        'tests',
                        'test_files',
                        'inputs',
                        'operations_activities.yaml'
                ),
                distance_to_site=10,
                transit_between_devices=0.1,
                tow_op = True
        )


    # ------------------------------------------------------------------ #
    # define_device_at_port
    # ------------------------------------------------------------------ #
    def test_define_device_at_port_sets_values_for_ofw(self):
        """define_device_at_port must pick values from the correct technology object."""
        op = FakeTowOp(_id="ofw200", name='opertow_1', tow_to_port=True)
        wtg = FakeTechObj(n_device_at_port=3, n_device_stored_at_port=2)
        wec = FakeTechObj(n_device_at_port=99, n_device_stored_at_port=99)
        pv = FakeTechObj(n_device_at_port=99, n_device_stored_at_port=99)

        aux_operation.define_device_at_port(op, wtg, wec, pv, False)
        self.assertEqual(op.n_device_at_port, 3)
        self.assertEqual(op.n_device_stored_at_port, 2)

    def test_define_device_at_port_defaults_for_none_or_zero(self):
        """None/zero values must be defaulted to 1 and 0."""
        op = FakeTowOp(_id="ofw201", name='opertow_2')
        wtg = FakeTechObj(n_device_at_port=None, n_device_stored_at_port=None)
        wec = FakeTechObj(n_device_at_port=0, n_device_stored_at_port=None)
        pv = FakeTechObj(n_device_at_port=0, n_device_stored_at_port=None)

        aux_operation.define_device_at_port(op, wtg, wec, pv, True)
        self.assertEqual(op.n_device_at_port, 1)
        self.assertEqual(op.n_device_stored_at_port, 0)

    def test_define_device_at_port_negative_values_raise(self):
        """Negative values for device counts must raise ValueError."""
        op = FakeTowOp(_id="ofw202", name='opertow_3')
        wtg = FakeTechObj(n_device_at_port=-1, n_device_stored_at_port=0)
        wec = FakeTechObj(0, 0)
        pv = FakeTechObj(0, 0)

        with self.assertRaises(ValueError):
            aux_operation.define_device_at_port(op, wtg, wec, pv, True)

    def test_define_device_at_port_invalid_prefix_raises_keyerror(self):
        """Invalid prefix must cause KeyError in define_device_at_port."""
        op = FakeTowOp(_id="ofw203", name='opertow_4')
        # Hack id after creation to bypass __init__ prefix check
        op.id = "xxx999"
        wtg = FakeTechObj(1, 0)
        wec = FakeTechObj(1, 0)
        pv = FakeTechObj(1, 0)

        with self.assertRaises(KeyError):
            aux_operation.define_device_at_port(op, wtg, wec, pv, True)
            
    # ------------------------------------------------------------------ #
    # define_tow_operations behaviour
    # ------------------------------------------------------------------ #

    def test_define_tow_operations(self):
        """If a tow operation name has neither 'remov' nor 'deplo', TypeError must be raised."""
        op = FakeOpTOW(_id = 'ofw_001', name = 'oper_port')
        op_deplo = FakeOpTOW(_id = 'ofw_002', name = 'deplo')
        op_remove = FakeOpTOW(_id = 'ofw_003', name = 'remove')
        op_deplo_remove = FakeOpTOW(_id = 'ofw_003', name = 'deplo_remove')

        aux_operation.define_tow_operations(op, [op_deplo, op_remove, op_deplo_remove], op_type='op_2')

    def test_define_tow_operations_missing(self):
        """If a tow operation name has neither 'remov' nor 'deplo', TypeError must be raised."""
        op = FakeOpTOW(_id = 'ofw_001', name = 'oper_port')
        op_remove = FakeOpTOW(_id = 'ofw_003', name = 'remove')
        op_deplo_remove = FakeOpTOW(_id = 'ofw_003', name = 'deplo_remove')
        with self.assertRaises(NameError):
            aux_operation.define_tow_operations(op, [op_remove, op_deplo_remove], op_type='op_2')

    def test_define_tow_operations_unrecognized_name_raises_type_error(self):
        """If a tow operation name has neither 'remov' nor 'deplo', TypeError must be raised."""
        op = FakeOpTOW(_id = 'ofw_001', name = 'oper_port_2')
        bad_ops = FakeOpTOW(_id = 'ofw_unknown ', name = 'ofw_just_towing')
        with self.assertRaises(TypeError):
            aux_operation.define_tow_operations(op, [bad_ops], op_type='op_2')

    def test_define_tow_operations_unrecognized_prefix(self):
        """If a tow operation name has neither 'remov' nor 'deplo', TypeError must be raised."""
        op_bad = FakeOpTOW(_id = 'xxx_001', name = 'oper_port_2')
        op_deplo = FakeOpTOW(_id = 'ofw_002', name = 'deplo')
        with self.assertRaises(TypeError):
            aux_operation.define_tow_operations(op_bad, [op_deplo], op_type='op_2')

if __name__ == "__main__":
    unittest.main(verbosity=2)