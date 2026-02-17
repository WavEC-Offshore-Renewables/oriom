#test_group_merging_immediate

import unittest
import os
from unittest.mock import patch
from oriom.core.functions.log_merge_corrective_functions.group_merging_immediate import mergeble_operation
from pprint import pprint

class TestMergebleOperation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result_dir_r = os.path.join(os.getcwd(), 'tmp')
        cls.OLC_LIST = ['hs', 'cs', 'ws', 'ws_hub', 'tp', 'light']

    @patch('oriom.core.functions.log_merge_corrective_functions.group_merging_immediate.save_file_csv')
    def test_case_1_basic_structure(self, mock_save_file_csv):
        # Original simple case (Op1, Op2 in same group with different durations)
        oper_dict = {
            "Op1": {"vess_1": "Vessel1", "duration": 5, "hs": 1, "cs": 1, "ws": 1, "ws_hub": 1, "tp": 1, "light": 1},
            "Op2": {"vess_1": "Vessel1", "duration": 3, "hs": 1, "cs": 1, "ws": 1, "ws_hub": 1, "tp": 1, "light": 1},
            "Op3": {"vess_1": "Vessel2", "duration": 7, "hs": 2, "cs": 2, "ws": 2, "ws_hub": 2, "tp": 2, "light": 2}
        }
        result = mergeble_operation(oper_dict, self.result_dir_r, self.OLC_LIST)

        self.assertEqual(result["Vessel1"]["Group 1"]["Op2"]["Rank"], 1)
        self.assertEqual(result["Vessel1"]["Group 1"]["Op1"]["Rank"], 2)
        self.assertEqual(result["Vessel2"]["Group 1"]["Op3"]["Rank"], 1)
        

        mock_save_file_csv.assert_called_once()

    @patch('oriom.core.functions.log_merge_corrective_functions.group_merging_immediate.save_file_csv')
    def test_case_2_custom_grouping(self, mock_save_file_csv):
        # New set with different OLC values to create separate groups
        oper_dict = {
            "OpA": {"vess_1": "Vessel1", "duration": 4, "hs": 2, "cs": 3, "ws": 2, "ws_hub": 1, "tp": 1, "light": 1},
            "OpB": {"vess_1": "Vessel1", "duration": 5, "hs": 3, "cs": 4, "ws": 2, "ws_hub": 1, "tp": 1, "light": 1},
            "OpC": {"vess_1": "Vessel1", "duration": 1, "hs": 2, "cs": 3, "ws": 2, "ws_hub": 1, "tp": 1, "light": 1}
        }
        result = mergeble_operation(oper_dict, self.result_dir_r, self.OLC_LIST)
        #pprint('\n\n')
        #pprint('result 2')
        #pprint(result)
        # OpA OpB and OpC same OLC → same group, OpC shorter → rank 1
        group = result["Vessel1"]["Group 1"]
        self.assertEqual(group["OpC"]["Rank"], 2)
        self.assertEqual(group["OpA"]["Rank"], 3)
        self.assertEqual(group["OpB"]["Rank"], 1)
        mock_save_file_csv.assert_called_once()

    @patch('oriom.core.functions.log_merge_corrective_functions.group_merging_immediate.save_file_csv')
    def test_case_3_large_example(self, mock_save_file_csv):
        # Complex case with 25 operations from user
        oper_dict = {
            'Op1': {'vess_1': 'VesselA', 'duration': 10, 'hs': 3, 'cs': 2, 'ws': 5, 'ws_hub': 6, 'tp': 4, 'light': 2},
            'Op2': {'vess_1': 'VesselA', 'duration': 8, 'hs': 2, 'cs': 1, 'ws': 4, 'ws_hub': 5, 'tp': 3, 'light': 1},
            'Op3': {'vess_1': 'VesselA', 'duration': 6, 'hs': 2, 'cs': 1, 'ws': 4, 'ws_hub': 5, 'tp': 3, 'light': 1},
            'Op4': {'vess_1': 'VesselB', 'duration': 12, 'hs': 4, 'cs': 3, 'ws': 100, 'ws_hub': 7, 'tp': 5, 'light': 3},
            'Op5': {'vess_1': 'VesselA', 'duration': 4, 'hs': 5, 'cs': 2, 'ws': 4, 'ws_hub': 9, 'tp': 5, 'light': 3},
            'Op6': {'vess_1': 'VesselA', 'duration': 6, 'hs': 3, 'cs': 2, 'ws': 100, 'ws_hub': 6, 'tp': 4, 'light': 2},
            'Op7': {'vess_1': 'VesselA', 'duration': 12, 'hs': 4, 'cs': 2, 'ws': 2, 'ws_hub': 2, 'tp': 2, 'light': 8},
            'Op8': {'vess_1': 'VesselA', 'duration': 12, 'hs': 8, 'cs': 8, 'ws': 8, 'ws_hub': 8, 'tp': 8, 'light': 8},
            'Op9': {'vess_1': 'VesselA', 'duration': 1, 'hs': 1, 'cs': 100, 'ws': 1, 'ws_hub': 1, 'tp': 1, 'light': 1},
            'Op10': {'vess_1': 'VesselC', 'duration': 5, 'hs': 3, 'cs': 2, 'ws': 5, 'ws_hub': 6, 'tp': 4, 'light': 2},
            'Op11': {'vess_1': 'VesselC', 'duration': 9, 'hs': 2, 'cs': 1, 'ws': 4, 'ws_hub': 5, 'tp': 3, 'light': 1},
            'Op12': {'vess_1': 'VesselB', 'duration': 7, 'hs': 4, 'cs': 3, 'ws': 6, 'ws_hub': 100, 'tp': 5, 'light': 3},
            'Op13': {'vess_1': 'VesselA', 'duration': 15, 'hs': 5, 'cs': 2, 'ws': 4, 'ws_hub': 9, 'tp': 5, 'light': 3},
            'Op14': {'vess_1': 'VesselB', 'duration': 6, 'hs': 6, 'cs': 5, 'ws': 7, 'ws_hub': 9, 'tp': 6, 'light': 4},
            'Op15': {'vess_1': 'VesselA', 'duration': 11, 'hs': 2, 'cs': 1, 'ws': 4, 'ws_hub': 5, 'tp': 3, 'light': 1},
            'Op16': {'vess_1': 'VesselC', 'duration': 14, 'hs': 3, 'cs': 2, 'ws': 5, 'ws_hub': 6, 'tp': 4, 'light': 2},
            'Op17': {'vess_1': 'VesselA', 'duration': 3, 'hs': 1, 'cs': 1, 'ws': 1, 'ws_hub': 1, 'tp': 1, 'light': 1},
            'Op18': {'vess_1': 'VesselB', 'duration': 8, 'hs': 4, 'cs': 3, 'ws': 6, 'ws_hub': 7, 'tp': 5, 'light': 3},
            'Op19': {'vess_1': 'VesselC', 'duration': 10, 'hs': 8, 'cs': 8, 'ws': 8, 'ws_hub': 8, 'tp': 8, 'light': 8},
            'Op20': {'vess_1': 'VesselC', 'duration': 10, 'hs': 8, 'cs': 8, 'ws': 8, 'ws_hub': 8, 'tp': 8, 'light': 8},
            'Op21': {'vess_1': 'VesselA', 'duration': 2, 'hs': 6, 'cs': 4, 'ws': 5, 'ws_hub': 7, 'tp': 6, 'light': 3},
            'Op22': {'vess_1': 'VesselA', 'duration': 2, 'hs': 6, 'cs': 4, 'ws': 5, 'ws_hub': 7, 'tp': 6, 'light': 3},
            'Op23': {'vess_1': 'VesselA', 'duration': 2, 'hs': 6, 'cs': 4, 'ws': 2, 'ws_hub': 7, 'tp': 6, 'light': 3},
            'Op24': {'vess_1': 'VesselA', 'duration': 4, 'hs': 6, 'cs': 4, 'ws': 5, 'ws_hub': 7, 'tp': 6, 'light': 3},
            'Op25': {'vess_1': 'VesselA', 'duration': 4, 'hs': 6, 'cs': 4, 'ws': 5, 'ws_hub': 7, 'tp': 6, 'light': 3}
        }

        result = mergeble_operation(oper_dict, self.result_dir_r, self.OLC_LIST)

        # Spot check: ensure one known group exists and operations appear
        # VesselA - Group 1
        self.assertIn('Op6', result['VesselA']['Group 1'])
        self.assertEqual(result['VesselA']['Group 1']['Op6']['Rank'], 1)
        self.assertIn('Op1', result['VesselA']['Group 1'])
        self.assertEqual(result['VesselA']['Group 1']['Op1']['Rank'], 2)
        self.assertIn('Op3', result['VesselA']['Group 1'])
        self.assertEqual(result['VesselA']['Group 1']['Op3']['Rank'], 3)
        self.assertIn('Op2', result['VesselA']['Group 1'])
        self.assertEqual(result['VesselA']['Group 1']['Op2']['Rank'], 4)
        self.assertIn('Op15', result['VesselA']['Group 1'])
        self.assertEqual(result['VesselA']['Group 1']['Op15']['Rank'], 5)
        self.assertIn('Op17', result['VesselA']['Group 1'])
        self.assertEqual(result['VesselA']['Group 1']['Op17']['Rank'], 6)

        # VesselA - Group 2
        self.assertIn('Op5', result['VesselA']['Group 2'])
        self.assertEqual(result['VesselA']['Group 2']['Op5']['Rank'], 1)
        self.assertIn('Op13', result['VesselA']['Group 2'])
        self.assertEqual(result['VesselA']['Group 2']['Op13']['Rank'], 2)
        self.assertIn('Op3', result['VesselA']['Group 2'])
        self.assertEqual(result['VesselA']['Group 2']['Op3']['Rank'], 3)
        self.assertIn('Op2', result['VesselA']['Group 2'])
        self.assertEqual(result['VesselA']['Group 2']['Op2']['Rank'], 4)
        self.assertIn('Op15', result['VesselA']['Group 2'])
        self.assertEqual(result['VesselA']['Group 2']['Op15']['Rank'], 5)
        self.assertIn('Op17', result['VesselA']['Group 2'])
        self.assertEqual(result['VesselA']['Group 2']['Op17']['Rank'], 6)

        # VesselA - Group 3
        self.assertIn('Op8', result['VesselA']['Group 3'])
        self.assertEqual(result['VesselA']['Group 3']['Op8']['Rank'], 1)
        self.assertIn('Op7', result['VesselA']['Group 3'])
        self.assertEqual(result['VesselA']['Group 3']['Op7']['Rank'], 2)
        self.assertIn('Op15', result['VesselA']['Group 3'])
        self.assertEqual(result['VesselA']['Group 3']['Op15']['Rank'], 3)
        self.assertIn('Op17', result['VesselA']['Group 3'])
        self.assertEqual(result['VesselA']['Group 3']['Op17']['Rank'], 4)

        # VesselA - Group 4
        self.assertIn('Op9', result['VesselA']['Group 4'])
        self.assertEqual(result['VesselA']['Group 4']['Op9']['Rank'], 1)
        self.assertIn('Op17', result['VesselA']['Group 4'])
        self.assertEqual(result['VesselA']['Group 4']['Op17']['Rank'], 2)

        # VesselA - Group 5
        self.assertIn('Op8', result['VesselA']['Group 5'])
        self.assertEqual(result['VesselA']['Group 5']['Op8']['Rank'], 1)
        self.assertIn('Op21', result['VesselA']['Group 5'])
        self.assertEqual(result['VesselA']['Group 5']['Op21']['Rank'], 2)
        self.assertIn('Op22', result['VesselA']['Group 5'])
        self.assertEqual(result['VesselA']['Group 5']['Op22']['Rank'], 3)
        self.assertIn('Op24', result['VesselA']['Group 5'])
        self.assertEqual(result['VesselA']['Group 5']['Op24']['Rank'], 4)
        self.assertIn('Op25', result['VesselA']['Group 5'])
        self.assertEqual(result['VesselA']['Group 5']['Op25']['Rank'], 5)
        self.assertIn('Op23', result['VesselA']['Group 5'])
        self.assertEqual(result['VesselA']['Group 5']['Op23']['Rank'], 6)
        self.assertIn('Op1', result['VesselA']['Group 5'])
        self.assertEqual(result['VesselA']['Group 5']['Op1']['Rank'], 7)
        self.assertIn('Op17', result['VesselA']['Group 5'])
        self.assertEqual(result['VesselA']['Group 5']['Op17']['Rank'], 8)

        # VesselB - Group 1
        self.assertIn('Op4', result['VesselB']['Group 1'])
        self.assertEqual(result['VesselB']['Group 1']['Op4']['Rank'], 1)
        self.assertIn('Op18', result['VesselB']['Group 1'])
        self.assertEqual(result['VesselB']['Group 1']['Op18']['Rank'], 2)

        # VesselB - Group 2
        self.assertIn('Op12', result['VesselB']['Group 2'])
        self.assertEqual(result['VesselB']['Group 2']['Op12']['Rank'], 1)
        self.assertIn('Op18', result['VesselB']['Group 2'])
        self.assertEqual(result['VesselB']['Group 2']['Op18']['Rank'], 2)

        # VesselB - Group 3
        self.assertIn('Op14', result['VesselB']['Group 3'])
        self.assertEqual(result['VesselB']['Group 3']['Op14']['Rank'], 1)
        self.assertIn('Op18', result['VesselB']['Group 3'])
        self.assertEqual(result['VesselB']['Group 3']['Op18']['Rank'], 2)

        # VesselC - Group 1
        self.assertIn('Op19', result['VesselC']['Group 1'])
        self.assertEqual(result['VesselC']['Group 1']['Op19']['Rank'], 1)
        self.assertIn('Op20', result['VesselC']['Group 1'])
        self.assertEqual(result['VesselC']['Group 1']['Op20']['Rank'], 2)
        self.assertIn('Op10', result['VesselC']['Group 1'])
        self.assertEqual(result['VesselC']['Group 1']['Op10']['Rank'], 3)
        self.assertIn('Op16', result['VesselC']['Group 1'])
        self.assertEqual(result['VesselC']['Group 1']['Op16']['Rank'], 4)
        self.assertIn('Op11', result['VesselC']['Group 1'])
        self.assertEqual(result['VesselC']['Group 1']['Op11']['Rank'], 5)

        #pprint('\n\n')
        #pprint('result 3')
        # #pprint(result)

        # Ensure rankings are set
        for vessel in result:
            for group in result[vessel]:
                for op_data in result[vessel][group].values():
                    self.assertIn("Rank", op_data)
                    self.assertIn("OLC", op_data)

        mock_save_file_csv.assert_called_once()


class TestMergebleOperationBasicGrouping(unittest.TestCase):
    """
    Tests for basic grouping and ranking logic in mergeble_operation.
    """

    @patch(
        "oriom.core.functions.log_merge_corrective_functions.group_merging_immediate.save_file_csv"
    )
    def test_same_vessel_same_olc_ranked_by_duration(self, mock_save):
        """
        Two operations with the same vessel and identical OLC limits:
        - they must end up in the same group
        - shorter duration must get Rank=1 (higher in the list)
        """
        oper_dict = {
            "OpA": {
                "vess_1": "V1",
                "duration": 5,
                "hs": 1,
                "cs": 2,
                "ws": 1,
                "ws_hub": 1,
                "tp": 2,
                "light": 1,
            },
            "OpB": {
                "vess_1": "V1",
                "duration": 3,  # shorter → should be Rank 1
                "hs": 1,
                "cs": 2,
                "ws": 1,
                "ws_hub": 1,
                "tp": 2,
                "light": 1,
            },
        }

        grouped = mergeble_operation(
            oper_dict,
            result_dir_r="/tmp",
            OLC_LIST=["hs", "cs", "ws", "ws_hub", "tp", "light"],
        )

        # Only one vessel and one group expected
        self.assertIn("V1", grouped)
        self.assertEqual(len(grouped["V1"]), 1)
        group_name = list(grouped["V1"].keys())[0]

        ops = grouped["V1"][group_name]
        self.assertEqual(set(ops.keys()), {"OpA", "OpB"})

        # Shorter duration must have Rank 1
        self.assertEqual(ops["OpB"]["Rank"], 1)
        self.assertEqual(ops["OpA"]["Rank"], 2)

        # Duration must be correctly stored
        self.assertEqual(ops["OpA"]["duration"], 5)
        self.assertEqual(ops["OpB"]["duration"], 3)

        # save_file_csv must be called once
        mock_save.assert_called_once()

    @patch(
        "oriom.core.functions.log_merge_corrective_functions.group_merging_immediate.save_file_csv"
    )
    def test_same_vessel_different_olc_more_restrictive_first(self, mock_save):
        """
        Two operations with same vessel and same duration but different OLC limits:
        - the more restrictive (higher OLC values) must get Rank=1.
        """
        oper_dict = {
            "SoftOp": {
                "vess_1": "V1",
                "duration": 4,
                "hs": 1,
                "cs": 1,
                "ws": 1,
                "ws_hub": 1,
                "tp": 1,
                "light": 1,
            },
            "HardOp": {
                "vess_1": "V1",
                "duration": 4,
                "hs": 2,  # stricter Hs
                "cs": 1,
                "ws": 1,
                "ws_hub": 1,
                "tp": 1,
                "light": 1,
            },
        }

        grouped = mergeble_operation(
            oper_dict,
            result_dir_r="/tmp",
            OLC_LIST=["hs", "cs", "ws", "ws_hub", "tp", "light"],
        )

        self.assertIn("V1", grouped)
        self.assertEqual(len(grouped["V1"]), 1)
        group_name = list(grouped["V1"].keys())[0]

        ops = grouped["V1"][group_name]
        self.assertEqual(set(ops.keys()), {"SoftOp", "HardOp"})

        # More restrictive (HardOp) must rank before SoftOp
        self.assertEqual(ops["HardOp"]["Rank"], 1)
        self.assertEqual(ops["SoftOp"]["Rank"], 2)

        mock_save.assert_called_once()

    @patch(
        "oriom.core.functions.log_merge_corrective_functions.group_merging_immediate.save_file_csv"
    )
    def test_mixed_olc_creates_separate_groups(self, mock_save):
        """
        Mixed OLC case:
        - one operation has higher values for some OLC and lower for others,
          compared to the first one.
        - They must NOT be in the same group (is_olc_mixed → True).
        """
        oper_dict = {
            "OpX": {
                "vess_1": "V1",
                "duration": 4,
                "hs": 1,
                "cs": 3,
                "ws": 2,
                "ws_hub": 1,
                "tp": 2,
                "light": 1,
            },
            "OpY": {
                "vess_1": "V1",
                "duration": 4,
                "hs": 2,  # higher than OpX
                "cs": 1,  # lower than OpX
                "ws": 2,
                "ws_hub": 1,
                "tp": 2,
                "light": 1,
            },
        }

        grouped = mergeble_operation(
            oper_dict,
            result_dir_r="/tmp",
            OLC_LIST=["hs", "cs", "ws", "ws_hub", "tp", "light"],
        )

        self.assertIn("V1", grouped)
        # Mixed OLC → operations must end up in separate groups
        self.assertEqual(len(grouped["V1"]), 2)

        all_ops = set()
        for grp in grouped["V1"].values():
            all_ops.update(grp.keys())

        self.assertEqual(all_ops, {"OpX", "OpY"})
        mock_save.assert_called_once()

    @patch(
        "oriom.core.functions.log_merge_corrective_functions.group_merging_immediate.save_file_csv"
    )
    def test_different_vessels_are_separated(self, mock_save):
        """
        Operations belonging to different vessels must never be grouped together.
        """
        oper_dict = {
            "OpA": {
                "vess_1": "V1",
                "duration": 5,
                "hs": 1,
                "cs": 1,
                "ws": 1,
                "ws_hub": 1,
                "tp": 1,
                "light": 1,
            },
            "OpB": {
                "vess_1": "V2",
                "duration": 6,
                "hs": 1,
                "cs": 1,
                "ws": 1,
                "ws_hub": 1,
                "tp": 1,
                "light": 1,
            },
        }

        grouped = mergeble_operation(
            oper_dict,
            result_dir_r="/tmp",
            OLC_LIST=["hs", "cs", "ws", "ws_hub", "tp", "light"],
        )

        # Two different vessels
        self.assertIn("V1", grouped)
        self.assertIn("V2", grouped)
        self.assertEqual(len(grouped["V1"]), 1)
        self.assertEqual(len(grouped["V2"]), 1)

        # Each vessel must only contain its own operation
        group_v1 = list(grouped["V1"].values())[0]
        group_v2 = list(grouped["V2"].values())[0]
        self.assertEqual(set(group_v1.keys()), {"OpA"})
        self.assertEqual(set(group_v2.keys()), {"OpB"})

        mock_save.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)

