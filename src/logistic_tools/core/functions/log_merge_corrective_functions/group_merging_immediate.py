import pandas as pd
from collections import defaultdict

from logistic_tools.utils.aux_functions import save_file_csv


def mergeble_operation(oper_dict, result_dir_r, OLC_LIST):
    """
    Evaluate and create a rank of operations diveded by the vessel, the OLC and the duration of the operations
    The operations are grouped by: 
        - Same vessel
            - OLC feasible (if op1 have OLC on Hs and op2 on Ws they are not mergeble)
                - Duration of the operation

    The operations merged are ranked by less restrictive to most restrictive (Higher rank means more restrictive operation)

    Args:
        oper_dict (:obj:`dict`): A dictionary containing operation details.
        result_dir_r (:obj:`str`): The directory where the result file will be saved.
        OLC_LIST (:obj:`list`): A list of OLC keys to be considered for ranking.
    Returns:
        grouped_operations (:obj:`dict`): A dictionary containing the grouped and ranked operations.
            
    """
    
    def reorganize_operations(grouped_operations):
        reorganized_data = defaultdict(lambda: defaultdict(dict))

        for vessel, groups in grouped_operations.items():
            for group_id, operations in groups.items():
                group_name = f"Group {group_id}"  
                for rank, (op_name, details) in enumerate(operations, start=1):
                    reorganized_data[vessel][group_name][op_name] = {
                        "Rank": rank,
                        "duration": details["duration"],
                        "OLC": [details.get(olc, 'N/A') for olc in ['hs', 'cs', 'ws', 'ws_hub', 'tp', 'light']]
                    }

        return dict(reorganized_data)
    
    # NOTE: a class can be implemented for the ranks and the functions
    def save_rank(data):
        rows = []
        for vessel, groups in data.items():
            for group, operations in groups.items():
                for op_name, op_data in operations.items():
                    row = {
                        "Vessel": vessel,
                        "Group": group,
                        "Operation": op_name,
                        "Rank": op_data["Rank"],
                        "Duration": op_data["duration"],
                        "OLC": ', '.join(map(str, op_data["OLC"])) 
                    }
                    rows.append(row)

        # Creare un DataFrame
        df = pd.DataFrame(rows)
        save_file_csv(df, result_dir_r, 'rank_merge_operation.csv')


    def rank_operations(
        op, 
        details,
        oper_dict,
        oper_list
    ):
            
        """
        This function create a dictionary that will group operation that can be conducted together ranking them by the Vessels, OLC and durations.
        Higher rank will mean more restrictive operation, OLC are considered before than duration of the operation

        Args:
            op (:obj:`str`): The key from the dictionary, representing the operation name.
            details (:obj:`dict`): The value associated with the key, containing the operation details (Vessel, OLC, duration, rov).
            oper_dict (:obj:`dict`): The dictionary above cited
            oper_list (:obj:`list`): A list of all operation prsent

        Returns:
            No returns, it create a dictionary.
        """

        def is_olc_equal(op1, op2):
            """ Return True if op1 has all OLC equal to op2 """
            return all(op1.get(olc) == op2.get(olc) for olc in OLC_LIST)

        def is_olc_higher(op1, op2):
            """ Return True if op1 has all OLC higher than op2 """
            return any(op1.get(olc) > op2.get(olc) for olc in OLC_LIST) and not all(op1.get(olc) == op2.get(olc) for olc in OLC_LIST)

        def is_olc_mixed(op1, op2):
            """ Return True if op1 has at least an OLC higher and another lower than op2 """
            higher = any(op1.get(olc) > op2.get(olc) for olc in OLC_LIST if op1.get(olc))
            lower = any(op1.get(olc) < op2.get(olc) for olc in OLC_LIST if op1.get(olc))
            return higher and lower

        def duration(op1, op2):
            """ Returns True if op1 has lower duration di op2 """
            return op1.get('duration') < op2.get('duration')
        
        
        def insert_operation(j,op,details):
            """Insert operation in group and remove it from the list"""

            if op in oper_list:
                oper_list.remove(op)
            grouped_operations[vessel1][group_id].insert(j, (op, details)) 
        
        def create_new_group(op,details):
            """Create new group insert the operation and remove it from the list"""

            try:
                oper_list.remove(op)
            except ValueError:
                pass
            grouped_operations[vessel1][i].append((op, details))
            

        dur_pos = 0
        vessel1 = details['vess_1']
        if vessel1 is not None:
            if not grouped_operations[vessel1]:  # Se non ci sono gruppi, creane uno
                i = 1  
                grouped_operations[vessel1][i] = []  # Inizializza la lista
                create_new_group(op,details)  # Aggiunge l'operazione
            else:
                i = 1
                group_found = False
                alredy_group = False

                for group_id in list(grouped_operations[vessel1].keys()):
                    this_group = False
                    rank_equal_found = False

                    if any(op == existing_op[0] for existing_op in grouped_operations[vessel1][group_id]):
                        alredy_group = True
                        continue

                    j = 0
                    for o, o_details in grouped_operations[vessel1][group_id]:  # Estrarre chiave e dettagli
                        j += 1
                        if op == o:
                            continue

                        other_group = is_olc_mixed(oper_dict[op], o_details)
                        if other_group:
                            break
                        
                        group_found = True
                        this_group = True
                        higher_rank = is_olc_higher(oper_dict[op], o_details)
                        if higher_rank:
                            if not rank_equal_found:
                                insert_operation(j-1, op, details)  
                            break

                        equal_rank = is_olc_equal(oper_dict[op], o_details)
                        if equal_rank:
                            lower_dur = duration(oper_dict[op], o_details)
                            if lower_dur:
                                insert_operation(j-1, op, details)
                                rank_equal_found = False
                                break

                            rank_equal_found = True
                            dur_pos = j
                    if this_group:
                        if rank_equal_found:
                            insert_operation(dur_pos, op, details)
                            continue

                        if j == len(grouped_operations[vessel1][group_id]):
                            insert_operation(j, op, details)
                    i += 1

                if alredy_group:
                    group_found = True
                if not group_found:
                    create_new_group(op,details)
                if op in oper_list:
                    create_new_group(op,details)


    # Create dictionary for ranked opeations
    grouped_operations = defaultdict(lambda: defaultdict(list))
    oper_list = list(oper_dict.keys())

    # Create a rank for the possible mergeble operations. Run it twice in order to create a rank that does not defend by the order of the operation analyzed
    for k in range(2):
        for op, details in oper_dict.items():
            rank_operations(op, details, oper_dict, oper_list)

    # Reorganize ranked operations data
    grouped_operations = reorganize_operations(grouped_operations)
    save_rank(grouped_operations)

    return grouped_operations


if __name__ == '__main__':

    # Temporary code for manual testing
    sample_operations = {
        "OpA": {"vess_1": "Alpha", "duration": 5, "hs": 1, "cs": 2, "ws": 1, "ws_hub": 1, "tp": 2, "light": 1},
        "OpB": {"vess_1": "Alpha", "duration": 4, "hs": 1, "cs": 2, "ws": 1, "ws_hub": 1, "tp": 2, "light": 1},
    }
    result = mergeble_operation(sample_operations, "./tmp/", ['hs', 'cs', 'ws', 'ws_hub', 'tp', 'light'])
