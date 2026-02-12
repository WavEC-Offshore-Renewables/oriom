# tests/aux_operation.py
import os
import unittest
import types
import networkx as nx
from copy import deepcopy

from logistic_tools.utils.aux_operation import level_component_check, operation_check_identities, define_activities
from logistic_tools.classes.DefineOperationTechs import Define_operation
from logistic_tools.classes.Operations.CorrectiveMajor import CorrectiveMajor
from logistic_tools.classes.Operations.OperationTow import OperationTow
from logistic_tools.classes.Vessel import Vessel

# ---------------------------
# Helpers / fakes for tests
# ---------------------------

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
# level_component_check
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
        level_component_check(self.Gs, ops, failure=False)

    def test_valid_levels_for_oce_any(self):
        # 'oce' -> check against union of all graphs
        d = types.SimpleNamespace(id="oce_999", level="substation")
        level_component_check(self.Gs, [d], failure=False)  # present in G_wind node levels

    def test_missing_level_raises_keyerror(self):
        # 'opv' with level not present in PV graph -> KeyError
        bad = types.SimpleNamespace(id="opv_010", level="nonexistent_level")
        with self.assertRaises(KeyError):
            level_component_check(self.Gs, [bad], failure=False)

    def test_failure_mode_uses_level_failure(self):
        # In failure=True, code reads 'level_failure'
        ok = types.SimpleNamespace(id="ofw_100", level_failure="device")
        level_component_check(self.Gs, [ok], failure=True)  # should pass

        bad = types.SimpleNamespace(id="owc_200", level_failure="not_there")
        with self.assertRaises(KeyError):
            level_component_check(self.Gs, [bad], failure=True)


    def test_operation_check_identities(self):
        # Create operations with unique ids
        ops = [
            types.SimpleNamespace(id="ofw_001"),
            types.SimpleNamespace(id="opv_002"),
            types.SimpleNamespace(id="owc_003"),
        ]
        # Should not raise
        operation_check_identities(ops)

        # Add a duplicate id
        ops.append(types.SimpleNamespace(id="ofw_001"))  # duplicate

        with self.assertRaises(ValueError) as context:
            operation_check_identities(ops)
        
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


    def test_define_activities(self):
        op_corr = deepcopy(self.op_corr)
        self.assertIsNone(op_corr.activities)

        op_corr.id = 'ofw_op103'
        define_activities(
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

        define_activities(
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


if __name__ == "__main__":
    unittest.main(verbosity=2)