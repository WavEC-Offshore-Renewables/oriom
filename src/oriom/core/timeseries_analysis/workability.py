# Import packages
import os
import pandas as pd
import numpy as np
import logging
from copy import deepcopy

from oriom.utils.aux_functions import save_file_csv


def workability(
        df_metocean: pd.DataFrame,
        activities: list=None,
        operation=None,
        out_dir: str=None
) -> pd.DataFrame:
    """Evaluates the workability per timestep of all :attr:`activities` of an
        operation or an operation alone.

    Note:
        There are two types of operations, one defined with activities (CorrectiveMajor and OperationTow)
        and one not defined with activities. The workability works for both but if activities
        are defined than the operations should not be defined.

    Args:
        df_metocean (:obj:`pandas.DataFrame`): metocean timeseries table.
            Rows as timesteps and colums as sea conditions.
        activities (:obj:`list`, *optional*): list of objects where each object
            is an :class:`~oriom.classes.Activity.Activity`.
        operation (:obj:`class`,*optional*): operation with
            Operation Limit Criteria defined as attributs.
        out_dir (:obj:`str`, *optional*): output directory folder path.
            Defaults to ``None``.

    Raises:
        KeyError: If there is an activity (in :attr:`activities`) with Hs limit
            criteria and there is no Hs information on the :attr:`df_metocean`.
        KeyError: If there is an activity (in :attr:`activities`) with Tp limit
            criteria and there is no Tp information on the :attr:`df_metocean`.
        KeyError: If there is an activity (in :attr:`activities`) with Ws limit
            criteria and there is no Ws information on the :attr:`df_metocean`.
        KeyError: If there is an activity (in :attr:`activities`) with Ws at hub
            height limit criteria and there is no Ws at hub height information on
            the :attr:`df_metocean`.
        KeyError: If there is an activity (in :attr:`activities`) with Cs limit
            criteria and there is no Cs information on the :attr:`df_metocean`.
        KeyError: If there is an activity (in :attr:`activities`) with day light
            requirements and there is no day light information on the
            :attr:`df_metocean`.
        AssertionError: If one of the :attr:`activities` never has a workable
            timestep.
    Raises:
        ValueError: if both ``activities`` and ``operations`` are defined.
        KeyError: if metocean file does not have hs
        KeyError: if metocean file does not have tp
        KeyError: if metocean file does not have ws
        KeyError: if metocean file does not have ws_hub
        KeyError: if metocean file does not have cs
        KeyError: if metocean file does not have light
    Returns:
        :class:`pandas.DataFrame`: Boolean table with timesteps as rows and activity IDs as
        columns.
            :obj:`index`: timestamps of type :class:`pandas.DatetimeIndex`.

            :obj:`columns`:
                :obj:`<activities[0].id>`: :obj:`bool`, dtype: object

                :obj:`<activities[1].id>`: :obj:`bool`, dtype: object

                (...)

                :obj:`<activities[len(activities)-1].id>`: :obj:`bool`,
                dtype: object
    """
    if activities is not None and operation is not None:
        _e = 'you cannot define both "activities" and "operation" arguments'
        raise ValueError('Workability: ' + _e)

    # Check compability between timeseries and activities/operation
    if activities is not None:
        all_hs = [True if act.hs is not None else False for act in activities]
        all_tp = [True if act.tp is not None else False for act in activities]
        all_ws = [True if act.ws is not None else False for act in activities]
        all_ws_hub = [True if act.ws_hub is not None else False for act in activities]
        all_cs = [True if act.cs is not None else False for act in activities]
        all_light = [True if act.light is not None else False for act in activities]
    elif operation is not None:
        all_hs = [False]
        all_tp = [False]
        all_ws = [False]
        all_ws_hub = [False]
        all_cs = [False]
        all_light = [False]
        if hasattr(operation, 'hs') is True and operation.hs is not None:
            all_hs = [True]
        if hasattr(operation, 'tp') is True and operation.tp is not None:
            all_tp = [True]
        if hasattr(operation, 'ws') is True and operation.ws is not None:
            all_ws = [True]
        if hasattr(operation, 'ws_hub') is True and operation.ws_hub is not None:
            all_ws_hub = [True]
        if hasattr(operation, 'cs') is True and operation.cs is not None:
            all_cs = [True]
        if hasattr(operation, 'light') is True and operation.light is not None:
            all_light = [True]

    if any(all_hs) is True and 'hs' not in df_metocean.columns:
        _e = 'Metocean timeseries should have information regarding Wave Height (hs)'
        logging.error('Workability: ' + _e)
        raise KeyError(_e)
    if any(all_tp) is True and 'tp' not in df_metocean.columns:
        _e = 'Metocean timeseries should have information regarding Wave Period (tp)'
        logging.error('Workability: ' + _e)
        raise KeyError(_e)
    if any(all_ws) is True and 'ws' not in df_metocean.columns:
        _e = 'Metocean timeseries should have information regarding Wind Speed (ws)'
        logging.error('Workability: ' + _e)
        raise KeyError(_e)
    if any(all_ws_hub) is True and 'ws_hub' not in df_metocean.columns:
        _e = 'Metocean timeseries should have information regarding Wind Speed at hub height (ws_hub)'
        logging.error('Workability: ' + _e)
        raise KeyError(_e)
    if any(all_cs) is True and 'cs' not in df_metocean.columns:
        _e = 'Metocean timeseries should have information regarding Current Speed (cs)'
        logging.error('Workability: ' + _e)
        raise KeyError(_e)
    if any(all_light) is True and 'light' not in df_metocean.columns:
        _e = 'Metocean timeseries should have information regarding day light (light)'
        logging.error('Workability: ' + _e)
        raise KeyError(_e)

    # Initialize a pandas DataFrame df_workability with ones (activities always
    # "workable")
    if activities is not None:
        columns_names = [act.id for act in activities]
    elif operation is not None:
        columns_names = [operation.id]
    df_workability = pd.DataFrame(
            True,
            index=deepcopy(df_metocean.index),
            columns=columns_names
    )

    if activities is not None:
        for activity in activities:
            hs = np.inf
            tp = np.inf
            ws = np.inf
            ws_hub = np.inf
            cs = np.inf
            light = False

            olc_exists = False
            try:
                hs = float(activity.hs)
                olc_exists = True
            except TypeError:
                pass
            try:
                tp = float(activity.tp)
                olc_exists = True
            except TypeError:
                pass
            try:
                ws = float(activity.ws)
                olc_exists = True
            except TypeError:
                pass
            try:
                ws_hub = float(activity.ws_hub)
                olc_exists = True
            except TypeError:
                pass
            try:
                cs = float(activity.cs)
                olc_exists = True
            except TypeError:
                pass
            try:
                light = bool(activity.light)
                olc_exists = True
            except TypeError:
                pass

            # If there is any weather restriction
            if olc_exists is True:
                # The workability for these OLCs was not define yet
                # For the given metocean data, check when this activity CANNOT be
                # performed
                c_hs = df_metocean['hs'] > hs      # Condition Hs
                c_tp = df_metocean['tp'] > tp      # Condition Tp
                c_ws = df_metocean['ws'] > ws      # Condition Ws
                c_ws_hub = df_metocean['ws_hub'] > ws_hub   # Condition Ws_hub
                c_cs = df_metocean['cs'] > cs      # Condition Cs
                c_light = df_metocean['light'] < light   # Condition light

                condition = c_hs | c_tp | c_ws | c_ws_hub | c_cs | c_light

                ds_act_work = df_workability[activity.id]
                ds_act_work[condition] = False
                df_workability[activity.id] = ds_act_work

                if ds_act_work.sum() == 0:
                    _e = 'Activity %s does not have workability' % activity.id
                    logging.error('Workability: ' + _e)
                    raise AssertionError(_e)
            del hs, tp, ws, ws_hub, cs, light

    elif operation is not None:
        hs = np.inf
        tp = np.inf
        ws = np.inf
        ws_hub = np.inf
        cs = np.inf
        light = False

        olc_exists = False
        try:
            hs = float(operation.hs)
            olc_exists = True
        except TypeError:
            pass
        except AttributeError:
            pass
        try:
            tp = float(operation.tp)
            olc_exists = True
        except TypeError:
            pass
        except AttributeError:
            pass
        try:
            ws = float(operation.ws)
            olc_exists = True
        except TypeError:
            pass
        try:
            ws_hub = float(operation.ws_hub)
            olc_exists = True
        except TypeError:
            pass
        except AttributeError:
            pass
        try:
            cs = float(operation.cs)
            olc_exists = True
        except TypeError:
            pass
        except AttributeError:
            pass
        try:
            light = bool(operation.light)
            olc_exists = True
        except TypeError:
            pass

        # If there is any weather restriction
        if olc_exists is True:
            # The workability for these OLCs was not define yet
            # For the given metocean data, check when this operation CANNOT be
            # performed
            c_hs = df_metocean['hs'] > hs      # Condition Hs
            c_tp = df_metocean['tp'] > tp      # Condition Tp
            c_ws = df_metocean['ws'] > ws      # Condition Ws
            c_ws_hub = df_metocean['ws_hub'] > ws_hub   # Condition Ws
            c_cs = df_metocean['cs'] > cs      # Condition Cs
            c_light = df_metocean['light'] < light   # Condition light

            condition = c_hs | c_tp | c_ws | c_ws_hub | c_cs | c_light

            ds_op_work = df_workability[operation.id]
            ds_op_work[condition] = False
            df_workability[operation.id] = ds_op_work

            if ds_op_work.sum() == 0:
                _e = 'Operation %s does not have workability' % operation.id
                logging.error('Workability: ' + _e)
                raise AssertionError(_e)
        del hs, tp, ws, ws_hub, cs, light

    df_workability.index.name = 'datetime'

    # Save workability as a CSV
    if out_dir is not None:
        save_file_csv(df_workability, out_dir, 'workability.csv', indexing = True)
        logging.info('Workability: saved as "%s".' % os.path.join(out_dir, 'workability.csv'))

    return df_workability


def workability_tow(
        df_metocean: pd.DataFrame,
        metocean_tow: dict,
        metocean_distance_lag: dict,
        operation: object,
        op_dir: str = None
)->pd.DataFrame:
    """
    Evaluate the workability file considering various metocean point location

    Args:

        df_metocean (:obj:`pandas.DataFrame`): metocean timeseries table of site location.
            Rows as timesteps and colums as sea conditions.
        metocean_tow (dict): Dictionary with key of int and values Metocean object of point location
        metocean_distance_lag (dict): Dictionary with key of int and values distance point to site in hours of transit along tow
        operation (:obj:`class`): operation of OperationTow class with
            Operation Limit Criteria defined as attributs.
        out_dir (:obj:`str`, *optional*): output directory folder path.
            Defaults to ``None``.
    """

    def and_series_on_ref(df_works:dict, dict_durations:dict, act_name:str, site:bool) ->pd.Series:
        """
        Function to evaluate the df_workability of all the df_metocean data for an activity
        In check if index are complient with site metocean, it join the values of the various df_metocean with AND logic

        Args:
            df_works (dict): Dictionary of workability for the various location
            dict_durations (dict): Dictionary of durations to the various location
            act_name (str): Name of the activity under analysis
            site (bool): Boolean to identify if TTP or TTS

        Return:
            (pd.Series) Series related to act_name with values True only if all are True, else False if df compliant
                else return series related of site metocean data

        Raise:
            Warnign if index or column not not complient with site metocean data

        Example:
            df0	    df1	    df2	    result_series
            True	True	True	True
            True	False	True	False
            True	True	NaN	    False
            True	True	True	True
        """

        ref_series = df_works[0][act_name]
        ref_index = ref_series.index
        result_series = pd.Series(True, index=ref_index)

        for i, df in df_works.items():
            # df column check
            if act_name not in df:
                logging.warning(
                    f"Column '{act_name}' missing in metocean data point {i}. "
                    "Considered site metocean data only."
                )
                return ref_series.copy()
            # df index check
            if not ref_index.isin(df.index).all():
                logging.warning(
                    f"metocean data point {i} has different index"
                    "Considered site metocean data only."
                )
                return ref_series.copy()

            # shift the series considering the duration to reach the new location considered
            if i > 0:
                lag_index = dict_durations[i]
                # For the location closest to the site consider new metocean at half the trip
                if i == 1:
                    lag_index /=2

                lag_index = int(np.ceil(lag_index))
                # Take a negative lag if TTP, so the index is shifted above
                if site:
                    lag_index = -abs(lag_index)
                # cut df if longer than site metocean data, shift the index by its lag of the transit
                s = (
                    df[act_name]
                    .loc[ref_index]
                    .shift(lag_index)
                )
            else:
                # cut df if longer than site metocean data
                s = df[act_name].loc[ref_index]
            # Concatenate all boolean with AND of the metocean with the total series
            result_series &= s.fillna(False).astype(bool)

        return result_series

    df_works = {}

    # Point workability (0 -> site, x -> point, -1 -> port)
    for i in range(0, len(metocean_tow)+1):
        df_works[i] = workability(
            activities=operation.activities,
            df_metocean=df_metocean if i == 0 else metocean_tow[i].df_timeseries,
            out_dir=op_dir
        )

    site = False
    # Overlap a unique workability depending by the activity
    df_workability = df_works[0].copy()
    for i, op_act in enumerate(operation.activities):
        if op_act.location == "site":
            df_workability[op_act.id] = df_works[0][op_act.id]
            site = True
        elif op_act.location == "port":
            df_workability[op_act.id] = df_works[-1][op_act.id]
        elif op_act.towing:
            df_workability[op_act.id] = and_series_on_ref(
                df_works = df_works,
                dict_durations = metocean_distance_lag,
                act_name = op_act.id,
                site = site
            )
    return df_workability

def workability_tow_distance_lag(
    metocean_tow_distance: dict,
    operation: object
):
    """ Evaluates the duration of transit during towing opeartion between the points of the metocean"""

    dict_distance_duration = {}
    vessel_1 = getattr(operation, 'vessel1', None)
    total_distance = 0
    for i, distance in metocean_tow_distance.items():
        # calculate half of the distance to be covered to evaluate next point 
        dict_distance_duration[i] = (((total_distance + distance/2) * 1000) / vessel_1.speed_tow) / 3600
        total_distance += distance

    return dict_distance_duration


if __name__ == '__main__':
    file_metocean = os.path.join(os.getcwd(), 'tests', 'test_files', 'metocean', 'metocean_dummy.csv')
    file_activities = os.path.join(os.getcwd(), 'tests', 'test_files', 'op_activities_dummy.csv')

    from oriom.classes import Metocean
    metocean = Metocean(
            file_=file_metocean,
            latitude=41.615065,
            longitude=-9.348514
    )
    metocean.interpolate()
    metocean.get_daylight_timesteps()       # TODO: Load a file with light instead of calling this

    from oriom.classes import Activity
    activities = Activity.get_activities_from_csv(file_activities)

    temp_dir = os.path.join(os.getcwd(), 'tmp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    workability(
            activities=activities,
            df_metocean=metocean.df_timeseries,
            out_dir=temp_dir
    )
