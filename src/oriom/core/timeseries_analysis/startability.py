# Import packages
import os
import pandas as pd
import numpy as np
import math as mt
from copy import deepcopy
import logging

from oriom.utils.aux_functions import save_file_csv

def startability(
        activities: list,
        df_workability: pd.DataFrame,
        out_dir: str=None
) -> pd.DataFrame:
    """Evaluates the startability of all :attr:`activities` per timestep.

    This is called only for those operations defined by activities.

    Args:
        activities (:obj:`list`): List of objects where each object is an
            :class:`~oriom.classes.Activity.Activity`.
        df_workability (:obj:`pandas.DataFrame`): Boolean table with timesteps
            as rows and activity IDs as columns.
        out_dir (:obj:`str`, *optional*): Output directory folder path.
            Defaults to ``None``.

    Raises:
        KeyError: If :attr:`df_workability` index name is not ``datetime``.

    Returns:
        :class:`pandas.DataFrame`: Boolean table with timesteps as rows and
        activity IDs as columns.
            :obj:`index`: timestamps of type :class:`pandas.DatetimeIndex`.

            :obj:`columns`:
                :obj:`<activities[0].id>`: :obj:`bool`, dtype: object

                :obj:`<activities[1].id>`: :obj:`bool`, dtype: object

                (...)

                :obj:`<activities[len(activities)-1].id>`: :obj:`bool`,
                dtype: object
    """
    # Check df_workability index name
    if df_workability.index.name != 'datetime':
        _e = 'Workability DataFrame should have "datetime" as index name'
        logging.error('Startability: ' + _e)
        raise KeyError(_e)
    # Define a list of dict "database" to improve df_startability calculations
    list_start_db = []

    df_index = deepcopy(df_workability.index)
    df_workability.reset_index(inplace=True, drop=True)
    # Initialize a pandas DataFrame df_startability with False
    df_startability = pd.DataFrame(
            False,
            index=df_workability.index.tolist(),
            columns=df_workability.columns.tolist()
    )

    for activity in activities:
        act_id = activity.id

        hs = np.inf
        tp = np.inf
        ws = np.inf
        cs = np.inf
        light = False
        duration = 0

        try:
            hs = float(activity.hs)
        except TypeError:
            pass
        try:
            tp = float(activity.tp)
        except TypeError:
            pass
        try:
            ws = float(activity.ws)
        except TypeError:
            pass
        try:
            cs = float(activity.cs)
        except TypeError:
            pass
        try:
            light = bool(activity.light)
        except TypeError:
            pass
        duration = float(activity.duration)
        # How many timesteps are covered by this activity duration
        act_duration_ts = int(mt.ceil(duration))

        # Boolean pandas Series representing the workability for this activity
        workability_ones = df_workability[act_id] == True

        # First, search in the database if the startability for this OLCs and
        # duration was already defined
        startability_exists = False
        for db_elem in list_start_db:
            if (db_elem['hs'] == hs and
                db_elem['tp'] == tp and
                db_elem['ws'] == ws and
                db_elem['cs'] == cs and
                db_elem['light'] == light and
                db_elem['duration'] == act_duration_ts):
                startability_exists = True
                break

        if startability_exists is True:
            # Load startability from database
            list_startability = db_elem['startability']
            ds_startability = pd.Series(list_startability, name=activity.id)
            df_startability[activity.id] = ds_startability
            del db_elem
        else:
            # Check if there is any restriction in workability
            if workability_ones.all():
                # If there is no restrictions, startability is always 1
                # Startability = 1
                df_startability[act_id] = True

                if ((hs == np.inf or hs == np.nan) and
                    (tp == np.inf or tp == np.nan) and
                    (ws == np.inf or ws == np.nan) and
                    (cs == np.inf or cs == np.nan) and
                    light is False):
                    # If there are no OLC, then all startabilities = 1
                    pass
                else:
                    if act_duration_ts > 1:
                        df_startability[act_id].iloc[-(act_duration_ts - 1):] = np.nan
                    # Nan because it is not known if the activity can start or not, and,
                    # for that reason, it doesn't have statitical meaning
                    df_startability[act_id] = df_startability[act_id].astype(bool)
            else:
                # For some timesteps, the workability of the activity is 0
                # Check when workability changes from 0->1 or from 1->0
                df_work_diff = df_workability[act_id].astype(int).diff()
                # Save indexes where:
                # - workability changes from 0->1
                work_start_index = df_work_diff[df_work_diff == 1].index.tolist()
                # - workability changes from 1->0
                work_end_index = df_work_diff[df_work_diff == -1].index.tolist()

                if len(work_start_index) != 0:
                    # Workability has at least one transition from 0->1
                    if len(work_end_index) != 0:
                        # Workability has at least one transition from 0->1 and 1->0
                        if work_start_index[0] > work_end_index[0]:
                            # Workability starts with 1s
                            index2 = work_end_index[0] - mt.ceil(activity.duration)
                            if index2 > 0:
                                df_startability.loc[0:index2, act_id] = True
                            del index2
                            # This entry of the list was already considered
                            work_end_index.pop(0)             # Delete it
                        else:
                            # Workability starts with 0s
                            pass

                        for index in work_start_index:
                            # Number of workability timesteps
                            try:
                                index2 = work_end_index[0]
                                work_end_index.pop(0)
                            except IndexError:
                                index2 = df_startability.shape[0]

                            work_time_steps = index2 - index
                            if work_time_steps >= activity.duration:
                                # activity may start
                                # for how many times steps may it start?
                                start_time_steps = work_time_steps - mt.floor(activity.duration)
                                if mt.floor(activity.duration) == activity.duration:
                                    start_time_steps += 1
                                index2 = index + start_time_steps - 1
                                df_startability.loc[index:index2, act_id] = True
                            else:
                                # activity cannot start: workability < duration
                                pass
                    else:
                        # Workability has only one transition from 0->1
                        # Fill all rows with 1
                        df_startability.loc[work_start_index[0]:, act_id] = True

                else:
                    # Workability has no transition 0->1, so the only transition must be
                    # from 1->0. The activity can always start until workability is 0
                    # less the duration of the activity
                    last_time_step = work_end_index[0] - act_duration_ts + 1
                    df_startability[act_id].iloc[0:last_time_step] = True

            if act_duration_ts > 1:
                # ### This should only occur for workabilities = True
                df_startability[act_id].iloc[-(act_duration_ts - 1):] = np.nan
            # Nan because it is not known if the activity can start or not, and,
            # for that reason, it doesn't have statitical meaning

            # Convert startability to boolean type
            ds_not_null = df_startability[act_id].notnull()
            df_startability[act_id][ds_not_null] = df_startability[act_id].astype(bool)

        del hs, tp, ws, cs, duration
    del list_start_db

    df_startability.index = df_index

    # Save startability as a CSV
    if out_dir is not None:
        save_file_csv(df_workability, out_dir, 'startability.csv', indexing = True)
        logging.info('Startability: saved as "%s".' % os.path.join(out_dir, 'startability.csv'))

    return df_startability


if __name__ == '__main__':
    file_workability = os.path.join(os.getcwd(), 'tests', 'test_files', 'workability_dummy.csv')
    file_activities = os.path.join(os.getcwd(), 'tests', 'test_files', 'op_activities_dummy.csv')

    df_workability = pd.read_csv(file_workability, sep=',')
    df_workability['datetime'] = pd.to_datetime(df_workability['datetime'])
    df_workability.set_index('datetime', inplace=True)

    from oriom.classes import Activity
    activities = Activity.get_activities_from_csv(file_activities)

    temp_dir = os.path.join(os.getcwd(), 'tmp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    startability(
            activities=activities,
            df_workability=df_workability,
            out_dir=temp_dir
    )
