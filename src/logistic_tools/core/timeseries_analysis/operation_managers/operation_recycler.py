import os
import logging
import pandas as pd

try:
    from logistic_tools.core.functions.private import check_files
except ImportError:
    check_files = None


def recycle_other_oper_scheduler(
        minor_oper_dict: dict,
        hash_to_key: dict,
        operation, 
        attribute_list:list
) -> str:
    """
    Checks whether an operation that has the same attributes to another already exists in the dictionary.
    If so, returns the existing operation ID.
    Otherwise, adds the operation to the dictionary using its ID as the key.

    Args:
        minor_oper_dict (dict): Dictionary with key operation.id and values the attribute_list of the operation.
        hash_to_key (dict): Dictionary to a fast
        operation (Class: `CorrectiveMinor`): Operation of the class `CorrectiveMinor`.
        attribute_list (list): list of attribute to evaluate
    Returns:
        operation_id (str): the ID of the matched or newly inserted operation
    """
    op_values = tuple(getattr(operation, attr, None) for attr in attribute_list)

    if op_values in hash_to_key:
        # An equivalent operation already exists, return its group ID
        return hash_to_key[op_values]
    else:
        # Register a new group using operation.id as key
        minor_oper_dict[operation.id] = list(op_values)
        hash_to_key[op_values] = operation.id
        return operation.id
    

def recycle_major_other_oper_scheduler(
        operations: object,
        actual_oper: object,
        df_startability: pd.DataFrame,
        counter_op: int,
        operation_dir: str
):
    """
    Checks whether an operation has the same startability file to any another already existing operation.
    If so, save the oper_schedule of the similar operation

    Args:
        operations (object): List of objective of the class `OperationMajor` or `OperationTow`
        actual_oper (dict): Actual operation analyzed of the class `OperationMajor` or `OperationTow`
        df_startability (pd.DataFrame): startability dataframe of actual_oper
        counter_op (int): Counter of operation index.
        operation_dir (dir): directory of operations
    Returns:
        bool
    """
    for oper in operations[:counter_op]:
        start = getattr(oper.ts_data, "startability", None)
        if start is not None and not start.empty:
            if df_startability.equals(start):
                if compare_operations(actual_oper,oper) and check_files:
                    file_exist = check_files.reuse_file_exist(
                            op_dir = os.path.join(operation_dir, actual_oper.id), 
                            file_name_schedule = 'operation_schedule.csv', 
                            operation = actual_oper, 
                            similar_inspection_id = oper.id,
                            op_dir_other = os.path.join(operation_dir, oper.id)
                    )
                    if file_exist:
                        return True
    return False


def compare_operations(op1, op2):
    """
    Compare two operations activities: return True if all values
    duration, location, wtg_shutdown_dur, vessels of each activity are equals.
    """
    if len(op1.activities) != len(op2.activities):
        return False
    if op1.vessel1_id != op2.vessel1_id:
        return False
    for a1, a2 in zip(op1.activities, op2.activities):
        if (a1.duration != a2.duration or
            a1.location != a2.location or
            a1.wtg_shutdown_dur != a2.wtg_shutdown_dur):
            return False

    return True