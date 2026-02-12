import pandas as pd
from datetime import timedelta

from logistic_tools.utils.read_dataframe_value import get_first_failure
from logistic_tools.utils.aux_functions import safe_copy_df

from logistic_tools.core.functions.logs_timeseries.logs_timeseries_func import create_mobilisation


def create_yearly_mobilisation_mother_vessel(
        log_events_merged: pd.DataFrame,
        mother_vessel_list: list,
    )->pd.DataFrame:

    """ 
    Create for each year of the log_events_merged file a mobilisation of a mother vessel from the first use
    
    NOTE This code is run as mother_vessel are defined as second vessels and second vessel do not generate a mobilisation
    Generate 1 mobilisation per year. To add externaly more mobilisation if more call are made

    Args:
        log_events_merged (pd.DataFrame): dataframe of all log_events_merged,
        mother_vessel_list (list): list of mother vessel.type defined,
        vessels (list): list of element of class ´Vessel´

    Return:
        pd.DataFrame: log_events_merged with added mobilisation of mother vessel
    """

    log_event_mother_vessel_mobi = pd.DataFrame(columns = log_events_merged.columns)

    # For each mother vessel
    for mother_vessel in mother_vessel_list:
        df_mother_vessel = log_events_merged[
                (log_events_merged['vessel_1'] == mother_vessel.id) |
                (log_events_merged['vessel_2'] == mother_vessel.id)
            ]
        
        if not df_mother_vessel.empty:
            # For each year
            for year in df_mother_vessel['d_trigger'].dt.year.unique():
                # Find first date that the vessel is used in each year
                df_mother_vessel_year = df_mother_vessel[df_mother_vessel['d_trigger'].dt.year == year]

                if not df_mother_vessel_year.empty:
                    first_year_date_row = df_mother_vessel_year.iloc[0]
                    count_failure = get_first_failure(first_year_date_row['comments']).split("_", 1)[1]
                
                    # Calculate the start of mobilisation
                    first_year_data_start = first_year_date_row['d_trigger'] - timedelta(hours = int(mother_vessel.mobilisation_time))

                    log_event_mother_vessel_mobi = create_mobilisation(
                            df = log_event_mother_vessel_mobi,
                            mobilisation_date = first_year_data_start,
                            end_mobi = first_year_date_row['d_trigger'],
                            event = 'mobilisation',
                            vessel = mother_vessel,
                            oper_list = first_year_date_row['id'],
                            count_fail = count_failure,
                            concat = True
                        )
                    

                else: 
                    continue
        else:
            continue
    
    log_events_merged = pd.concat([log_events_merged, log_event_mother_vessel_mobi], axis=0, ignore_index=False)

    log_events_merged = log_events_merged.sort_values(by='d_trigger').reset_index(drop=True)

    return log_events_merged
    

    
def reduce_redundant_mobilisations_inspection(
        log_events_merged: pd.DataFrame,
        vessels: list,
    )->pd.DataFrame:

    """ 
    Eliminate for each year of the log_events_merged file a mobilisation of a vessel used in inspection that is used 
    in another inspection of the same month

    Args:
        log_events_merged (pd.DataFrame): dataframe of all log_events_merged,
        vessels (list): list of element of class ´Vessel´

    Return:
        pd.DataFrame: log_events_merged with mobilisation reduced
    """

    # Create a deep copy of the main DataFrame for intermediate calculations
    log_events_merged_clean = safe_copy_df(log_events_merged, ['id', 'comments'])

    # Add a column with the YYYY-MM period extracted from the trigger date
    log_events_merged_clean['trigger_period'] = log_events_merged_clean['d_trigger'].dt.to_period('M')

    # Precompute columns for performance
    event_str = log_events_merged_clean['event'].astype(str)
    id_suffix = log_events_merged_clean['id'].astype(str).str.split('_', n=1).str[1]

    # Global set of indices to remove from the original DataFrame
    all_indices_to_remove = set()

    for vessel in vessels:
        # Avoid to procede if there is no mobilisation
        if vessel.mobilisation_time == 0:
            continue

        # Filter inspections for this vessel
        df_vessel = log_events_merged_clean[
            (log_events_merged_clean['event'] == 'inspection_site') &
            (log_events_merged_clean['vessel_1'] == vessel.id)
        ]

        if df_vessel.empty:
            continue

        # Group by period (month-year) and check for multiple inspections
        grouped = df_vessel.groupby('trigger_period')
        for period, group in grouped:
            # If only one inspection with this vessel proceed to next period
            if len(group) <= 1:
                continue

            # Get list of operation IDs for this period
            ids_to_reduce = group['id'].tolist()

            # Exclude the first operation (keep at least one mobilisation)
            ids_to_reduce_excl_first = ids_to_reduce[1:]

            # Build mask for mobilisation events whose suffix matches these IDs
            mask_remove = (
                event_str.str.contains('mobi', na=False) &
                id_suffix.isin(ids_to_reduce_excl_first)
            )

            all_indices_to_remove.update(log_events_merged_clean.index[mask_remove])

    # Drop all identified rows in a single call on the original DataFrame
    if all_indices_to_remove:
        log_events_merged.drop(index=all_indices_to_remove, inplace=True)
    
    return log_events_merged


if __name__ == '__main__':
    pass
