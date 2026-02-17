#Import packages
import pandas as pd
from copy import deepcopy


def get_meaningful_timesteps(
        timeseries: pd.DataFrame,
        timesteps: list,
) -> list:
    """
    Extract meaningful timesteps from a given timeseries based on specified timesteps and conditions.

    Args:
        timeseries (:obj:`pd.DataFrame`): The input timeseries data
        timesteps (:obj:`list`): List of timesteps to consider
        
    Returns:
        :obj:`list`: List of meaningful timesteps
    """

    df_timeseries = deepcopy(timeseries)
    df_timeseries.reset_index(inplace=True)
    df_timeseries_timesteps = df_timeseries[df_timeseries.index.isin(timesteps)]

    df_timeseries_timesteps.reset_index(inplace=True)
    df_timeseries_timesteps.set_index('datetime', inplace=True)
    df_timeseries_timesteps.index = pd.to_datetime(df_timeseries_timesteps.index)

    timesteps_meaningful = df_timeseries_timesteps['index'].to_list()

    return timesteps_meaningful