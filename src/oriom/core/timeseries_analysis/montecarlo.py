import pandas as pd
import numpy as np
import warnings
import numpy as np
import random
from copy import deepcopy


def f_montecarlo(data_panda: pd.DataFrame, ts_percent_dec: float) -> tuple:
    """Select randomly the timestemp to analyse selecting a fixed % for each months.

    Args:
        data_panda (pd.DataFrame): Table with metocean data.

            :obj:`index`: timestamps of type :class:`pandas.DatetimeIndex`.

            :obj:`columns`: *irrelevant*.

        ts_percent_dec (float): Total percentage (decimal) of timesteps to analyse of each month.

    Returns:
        :obj:`(list, dict)`: The first element is a list of indexes of hindcast
        timeseries to consider in the analysis as operation starts. The
        second element is a dictionay where each key is a month of the year
        (from 1 to 12) and each month contains a dictionary with data
        related to that month.

    Example:
        >>> df = pd.read_csv(
        >>>         os.path.join(
        >>>                 os.getcwd(),
        >>>                 'tests',
        >>>                 'test_files',
        >>>                 'metocean',
        >>>                 'metocean_dummy.csv')
        >>> )
        >>> df.set_index('datetime', inplace=True)
        >>> df.index = pd.to_datetime(df.index)
        >>> df
                                   hs        tp    ws cs
        datetime
        2018-01-01 00:00:00  5.306843  13.678154   0   0
        2018-01-01 03:00:00  5.351300  13.731167   0   0
        2018-01-01 06:00:00  5.287027  13.781198   0   0
        2018-01-01 09:00:00  5.183515  13.806049   0   0
        2018-01-01 12:00:00  5.163932  13.797152   0   0
        ...                       ...        ...  ..  ..
        2018-12-31 09:00:00  0.731762  11.038247   0   0
        2018-12-31 12:00:00  0.692632  12.898156   0   0
        2018-12-31 15:00:00  0.737242  13.321549   0   0
        2018-12-31 18:00:00  0.820476  13.247357   0   0
        2018-12-31 21:00:00  0.973393  16.841156   0   0
        >>> montecarlo = f_montecarlo(df, 0.3)
        >>> montecarlo
        (
            [8, 9, 10, 13, ... 2915, 2916, 2917, 2919],
            {
                1: {
                    "data":                datetime        ws         hs  tp  cs
                            0   2018-01-01 00:00:00  5.306843  13.678154   0   0
                            1   2018-01-01 03:00:00  5.351300  13.731167   0   0
                            2   2018-01-01 06:00:00  5.287027  13.781198   0   0
                            ..                  ...       ...        ...  ..  ..
                            246 2018-01-31 18:00:00  1.686003  10.862346   0   0
                            247 2018-01-31 21:00:00  1.408824  10.707803   0   0
                            [248 rows x 5 columns],
                    "original_ids": [0, 1, 2, 3, ... 245, 246, 247],
                    "n_ids_orig_m": 248,
                    "n_ts_reduced_m": 75,
                    "ids_list_red_m": [50, 246, 235, 185, ... 62, 68, 156]
                },
                2: {...},
                3: {...},
                4: {...},
                5: {...},
                6: {...},
                7: {...},
                8: {...},
                9: {...},
                10: {...},
                11: {...},
                12: {
                    "data":                 datetime        ws         hs  tp  cs
                            2672 2018-12-01 00:00:00  2.706241  10.670498   0   0
                            2673 2018-12-01 03:00:00  2.622541  10.731612   0   0
                            2674 2018-12-01 06:00:00  2.572355  10.799954   0   0
                            2675 2018-12-01 09:00:00  2.491952  10.865313   0   0
                            ..                  ...       ...        ...  ..  ..
                            2918 2018-12-31 18:00:00  0.820476  13.247357   0   0
                            2919 2018-12-31 21:00:00  0.973393  16.841156   0   0
                            [248 rows x 5 columns],
                    "original_ids": [2672, 2673, 2674, 2675, ... 2917, 2918, 2919],
                    "n_ids_orig_m": 248,
                    "n_ts_reduced_m": 75,
                    "ids_list_red_m": [2821, 2747, 2888, 2749, ... 2829, 2718, 2903]
                }
            }
        )
    """
    data_panda_aux = deepcopy(data_panda)
    data_panda_aux.reset_index(inplace=True)
    months = [timestep.month for timestep in data_panda_aux['datetime']]
    months = pd.DataFrame(months)
    months = months.iloc[:, 0].unique().tolist()

    data = {
            1: "",
            2: "",
            3: "",
            4: "",
            5: "",
            6: "",
            7: "",
            8: "",
            9: "",
            10: "",
            11: "",
            12: ""
    }
    ids_list_reduced = list()     # empty list of total timestep ids

    for m in months:
        data_m = data_panda_aux.loc[data_panda_aux['datetime'].dt.month==m]     # unnecessary
        ids_orig = list(data_m.index)                                           # list of ids from original timeseries in month m
        n_ids_orig_m = len(ids_orig)                                            # number of ids in original timeseries for month m
        n_ts_reduced_m = int( np.ceil( ts_percent_dec * n_ids_orig_m ) )        # reduced number of ids based on percentage
        if (ts_percent_dec * n_ids_orig_m) < 1 or n_ts_reduced_m == 0:
            warnings.warn('Extremely low percentage results in less than a simulation per month. One simulation value will be used instead')
            n_ts_reduced_m = 1

        # Random selection of timesteps
        ids_list_red_m = random.sample(ids_orig, n_ts_reduced_m)
        data[m] = {
                "data": data_m,
                "original_ids": ids_orig,
                "n_ids_orig_m": n_ids_orig_m,
                "n_ts_reduced_m": n_ts_reduced_m,
                "ids_list_red_m": ids_list_red_m
        }

        ids_list_reduced += ids_list_red_m
    ids_list_reduced.sort()

    return ids_list_reduced, data


if __name__ == '__main__':

    import os
    df = pd.read_csv(
            os.path.join(
                    os.getcwd(),
                    'tests',
                    'test_files',
                    'metocean',
                    'metocean_1year.csv')
    )
    df.set_index('datetime', inplace=True)
    df.index = pd.to_datetime(df.index)
    montecarlo = f_montecarlo(df, 0.3)
