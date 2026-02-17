import ast
from datetime import timedelta
import pandas as pd

def get_first_failure(value)->str:
    """
    Analyze the value and return the first failure encountered in the value is:
        - a dictionary
        - a string representing a dictionary
        - a string
        
    Args: 
        value (dict|str): value to analyze
        
    Return:
        str: first failure encountered
    """
    
    # Case 1: value is a dict
    if isinstance(value, dict):
        failures = value.get('failures')
        if isinstance(failures, list) and failures:
            return failures[0]

    # Case 2: value is string representing a dict
    elif isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, dict):
                failures = parsed.get('failures')
                if isinstance(failures, list) and failures:
                    return failures[0]
        except (ValueError, SyntaxError):
            pass

        # Case 3: value is a simple string (only one failure)
        return value.strip() 
    
    raise ValueError(f"Unsupported type or empty value in failure evaluation: {value}, {type(value)}")


def compute_rov_cost(
    id_value, 
    n_vessels: int, 
    rov_dict_cost: dict
):
    """
    This function computes the ROV cost based on the id_value and number of vessels. 
    Takes the value in the col 'id' that represent the operation_id and returns the sum of the cost of the ROV for all the op conducted
    """

    if n_vessels is None:
        n_vessels = 1

    # Is a string and check what it contains (str or list)
    if isinstance(id_value, str):
        try:
            parsed = ast.literal_eval(id_value)
            if isinstance(parsed, list):
                # Contain list of tuples
                total = 0
                # For each item take the oper_id and add the cost of ROV an op uses it
                for item in parsed:
                    if isinstance(item, tuple) and len(item) == 2:
                        op_id = item[1]
                        rov_cost = rov_dict_cost.get(op_id, 0)
                        if rov_cost > 0:
                            total = rov_cost
                            break

                return total * n_vessels
            
            else:
                # Not a list, single oper
                return rov_dict_cost.get(id_value, 0) * n_vessels
            
        except (ValueError, SyntaxError):
            # Not a list, single oper
            return rov_dict_cost.get(id_value, 0) * n_vessels
        
    elif isinstance(id_value, list):
        # List already formatted
        total = 0
        for item in id_value:
            if isinstance(item, tuple) and len(item) == 2:
                op_id = item[1]
                total += rov_dict_cost.get(op_id, 0)
        return total * n_vessels
    
    else:
        return 0
    

def take_id_operation(
        id_value: str|list,
        index: int = None
) -> list:
    
    """
    Parses the 'id' field which can be either a string or a list of tuples.
    Returns a list of operation identifiers (as list of tuples).
    
    Args:
        id_value (str or list): The value from the 'id' column.
        index (int): Index of the row of log_event under analysys

    Returns:
        list: A list of tuples representing operation identifiers.
    """

    # already list of tuple
    if isinstance(id_value, list):
        return id_value  
    
    elif isinstance(id_value, str):
        try:
            parsed = ast.literal_eval(id_value)
            if isinstance(parsed, list):
                return parsed
            # wrap non-list in a tuple and list
            else:
                return [(index, parsed)]
        except (ValueError, SyntaxError):
            return [(index, id_value)]  # fallback for plain strings or invalid parsing
    
    else:
        return []
    

def approximate_hourly_data(data, round_up: bool = False):
    """Approximate a datetime to the nearest hour."""
    minutes = data.minute + data.second / 60  
    data = data.replace(minute=0, second=0, microsecond=0) + timedelta(hours=round(minutes / 60) if not round_up else (1 if minutes > 0 else 0))

    return data


def get_inspections_date(df)->list[list[pd.Timestamp]]:
    """
    Analyze the value and return a list of inspection dates encountered if value is:
        - a list
        - a string representing a list
        - a string
        
    Args: 
        df (pd.DataFrame): DataFrame containing inspection data
        
    Return:
        list[Sequence[pd.Timestamp]]: list of list for inspection dates
    """
    import re

    def parse_days_inspected(s):
        if pd.isna(s):
            return []
        # already a list / iterable of timestamps
        if isinstance(s, (list, tuple, pd.DatetimeIndex)):
            return pd.to_datetime(s)
        # string case (CSV)
        if isinstance(s, str):
            dates = re.findall(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", s)
            return pd.to_datetime(dates)
        raise ValueError(f"Unsupported type in days_inspected: {type(s)}")
    
    mask = df["days_inspected"].notna()
    df_valid = df.loc[mask].copy()
    if df_valid.empty:
        return []
    df_valid["days_inspected"] = df_valid["days_inspected"].apply(parse_days_inspected)
    all_days = df_valid["days_inspected"].tolist()

    return all_days

if __name__ == '__main__':
    pass
