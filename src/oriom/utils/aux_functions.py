import os
from ruamel.yaml import YAML
import collections.abc
import logging
import pandas as pd
import shutil
from copy import deepcopy

from oriom.common.constants import FORMATS_DATETIME

def update_dict(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = update_dict(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def save_file_csv(
    df_to_save: pd.DataFrame,
    save_dir: str,
    filename: str = None,
    indexing: bool = False
):

    """
    Function to save csv

    Args:
        df_to_save (pd.DataFrame): dataframe to save in csv
        save_dir (str): address to save file
        filename (str *optional): name of the file to save if not present in the save_dir. Default to False
        indexing (bool *optional): flag to decide if the index must be saved or not. Default to False
    """

    if filename:
        path_file = os.path.join(os.getcwd(),save_dir,filename)
    else:
        path_file = os.path.join(os.getcwd(),save_dir)

    df_to_save.to_csv(
        path_or_buf=path_file,
        index=indexing,
        sep=','
    )


def safe_getattr(obj, attr_chain: list, value_not_found = None):
    """ Take deep attribute in objects, Iterate for attribute the gatattr with always value_not_found as exception"""
    for attr in attr_chain:
        obj = getattr(obj, attr, value_not_found)
        if obj is None or value_not_found:
            break
    return obj


def convert_stringtime(
    df: pd.DataFrame,
    dt_column: str='datetime'
) -> pd.DataFrame:

    """
    Convert column in datetime. It tries different format till it find one
    Args:
        df (:obj:`pd.DataFrame`): The dataframe to convert
        dt_column (:obj:`str`): The column to convert in datetime format
    Returns:
        df (:obj:`pd.DataFrame`): The dataframe with the column converted in datetime format

    Raises:
        ValueError: If the column is not in datetime format and no format is found
    """

    if pd.api.types.is_datetime64_any_dtype(df[dt_column]):
        return df

    # Mask value to convert (exclude 'reuse_vessel')
    if dt_column == 'd_end_stat_chart':
        mask_convert = df[dt_column] != 'reuse_vessel'



    i=0
    for fmt in FORMATS_DATETIME:
        i+=1
        try:
            if dt_column == 'd_end_stat_chart':
                df.loc[mask_convert, dt_column] = pd.to_datetime(df.loc[mask_convert, dt_column], format=fmt)
            else:
                df[dt_column] = pd.to_datetime(df[dt_column], format=fmt)
            return df
        except ValueError as _e:
            if i == len(FORMATS_DATETIME):
                logging.error(f'LogDates: {_e} for {df}')
                raise ValueError(f'LogDates: {_e} for {df}')
            continue
    return df


def log_event_convert_stringtime(
    df_log_event_: pd.DataFrame
) -> pd.DataFrame:

    """
    Convert the string time to datetime format for the log events
    Args:
        df_log_event_ (:obj:`pd.DataFrame`): The dataframe of the log events
    """
    # Convert string time to datetime format for the log events
    for i in df_log_event_.columns:
        if 'd_' in i:
            try:
                df_log_event_ = convert_stringtime(df_log_event_, i)
            except: continue
        else: continue

    return df_log_event_


def take_attribute(op_id, find_element_class):
    """
    Auxiliary function to take the parameters of the operation
    Args:
        op_id (:obj:`str`): The id of the operation to take the parameters
        operation_log_file (:obj:`list`): The list of class that contains the operation to analyse
        time_between_devices (:obj:`dict`): The dictionary that contains the time between devices for various technologies
        find_element_class (Find_element_class): Initialized instance that provides fast access to operations,
            vessels and failures via internal dictionaries.

    """
    # General data
    oper_stat = find_element_class.find_operation_stats(op_id)
    oper = oper_stat.op_class
    tech_cost = getattr(oper, "tech_cost", 0)

    # Vessel data
    ves_2 = None
    vessel_2 = None
    if oper.vessel2_id:
        vessel_2 = oper.vessel2.id
        ves_2 = oper.vessel2_qt

    # Ts data
    oper_sched = oper.ts_data.oper_sched

    index_wait_to_start_col = oper_sched.columns.get_loc('wait_start')
    index_wait_port_col = oper_sched.columns.get_loc('wait_port')

    return (
        oper_stat, oper, tech_cost,
        vessel_2, ves_2, oper_sched,
        index_wait_to_start_col, index_wait_port_col
        )


def create_run_folder_operation(
        operation,
        operation_dir: str,
        inputs_gen,
        operation_files: list
):
    """ Function used to create the operations folders and copy previous result if exists"""

    op_dir = os.path.join(operation_dir, operation.id)
    if not os.path.exists(op_dir):
        os.makedirs(op_dir)

    if (
            inputs_gen.consider_tseries is not None and
            inputs_gen.consider_tseries["value"] is True
    ):
        # Copy results from a previous run, if possible
        src_dir = os.path.join(inputs_gen.previous_run_dir["value"], 'operation_dir', operation.id)
        if not os.path.exists(src_dir):
            # This operation was not considered in the previous run.
            # Nothing to copy.
            return
        dst_dir = os.path.join(operation_dir, operation.id)
        for file_name in os.listdir(src_dir):
            if file_name in operation_files:
                source = os.path.join(src_dir, file_name)
                destination = os.path.join(dst_dir, file_name)
                try:
                    shutil.copy(source, destination)
                    #logging.info('Operation: "%s" copied from "%s".' % src_dir)
                except shutil.SameFileError:
                    pass
                except FileNotFoundError:
                    pass


def safe_copy_df(
        df_orig: pd.DataFrame,
        deep_cols: list
)-> pd.DataFrame:

    """
    Creates a shallow copy of the DataFrame, and applies deepcopy only to selected columns
    (e.g., those containing lists, dicts, or other mutable objects).

    Args:
        df_orig (pd.DataFrame): The original DataFrame to copy.
        deep_cols (List[str]): List of column names to deepcopy.

    Returns:
        pd.DataFrame: A new DataFrame with selected columns deeply copied.
    """
    df_orig = df_orig.copy()
    df_copy = df_orig.copy()
    for deep_col in deep_cols:
        df_copy[deep_col] = df_orig[deep_col].apply(deepcopy)

    return df_copy