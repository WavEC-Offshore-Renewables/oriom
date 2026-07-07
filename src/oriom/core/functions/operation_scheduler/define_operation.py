 # Import packages
import pandas as pd
import numpy as np
import math as mt
from datetime import timedelta
from copy import deepcopy
from tqdm import tqdm
import logging

from oriom.utils.aux_functions import save_file_csv


def define_operation_values(
        ts_analyse: list,
        operation,
        df_startability: pd.DataFrame,
        MAX_WAIT: float = 24.0,
        out_dir: str = None
) -> pd.DataFrame:
    """
    This function is to be used only in case of operations defined by activities.

    For a timeseries (df_startability) this function schedule a given operation and, for each timestep,
    calculates what are the operation durations and waitings. Major and TOW operations are definded by
    activities. To schedule such operations are firtly analyzed the most restrictive activities
    and from it is check if the other activities can be conducted in a range of MAX_WAIT hours.
    To reduce computational time, if the operation in such timestep has waiting hours to start,
    the function jump directly at the timestep after the operation has been scheduled. Then,
    evaluate the next time step. This is done for all the timesteps till no more operation can
    be scheduled (end of timeseries analysis)

    For a set of timesteps (:attr:`ts_analyse`) of a timeseries, this
    function schedules a given operation and, for each timestep, calculates
    what are the operation durations and waitings.
    Args:
        ts_analyse (:obj:`list`): Set of timesteps of the timeseries to be
            analysed.
        operation: Operation to be analysed. it can be of type:
            :class:`oriom.classes.OperationInspection`,
            :class:`oriom.classes.OperationCorrective` or
            :class:`oriom.classes.OperationTow`.
        df_startability (:obj:`pandas.DataFrame`): Startability of the
            operation activities.
        MAX_WAIT (:obj:`float`, *optional*): Maximum waiting time between
            activities. Defaults to ``24.0``.
        out_dir (:obj:`str`, *optional*): Folder directory to save the
            operation schedule. Defaults to ``None``.

    Raises:
        InterruptedError: If the operation can never be scheduled.

    Returns:
        :class:`pandas.DataFrame`: The operation schedule for a given
        timeseries.
            :obj:`index`: timestamps of type :class:`pandas.DatetimeIndex`.
            :obj:`columns`:
                :obj:`dur_total`: total duration of the operation.
                :obj:`dur_net`: duration of the operation without
                wating to start time.
                :obj:`wait_start`: waiting on weather time to start
                the first activity.
                :obj:`wait_site`: waiting on weather time between
                activities.

    Example:
        Dummy operation considerign an intervation on a Wave Energy Converter
        device. The dummy operation is composed of 7
        :class:`~oriom.classes.Activity.Activity`.
        >>> df_startability
                             A01_0  A02_0  A03_0  A04_0  A03_1  A05_0  A06_0
        datetime

        >>> 2018-02-17 12:00:00  False   True  False   True  False   True  False
        >>> 2018-02-17 13:00:00  False   True  False   True  False   True  False
        >>> 2018-02-17 14:00:00   True   True  False   True  False   True  False
        >>> 2018-02-17 15:00:00   True   True  False   True  False   True  False
        >>> 2018-02-17 16:00:00   True   True  False   True  False   True  False
        >>> 2018-02-17 17:00:00   True   True  False   True  False   True   True
        >>> 2018-02-17 18:00:00   True   True  False   True  False   True   True
        >>> 2018-02-17 19:00:00   True   True  False   True  False   True   True
        >>> 2018-02-17 20:00:00   True   True  False   True  False   True   True
        >>> 2018-02-17 21:00:00   True   True  False   True  False   True   True
        >>> 2018-02-17 22:00:00   True   True  False   True  False   True   True
        >>> 2018-02-17 23:00:00   True   True  False   True  False   True   True
        >>> 2018-02-18 00:00:00   True   True  False   True  False   True   True
        ...                    ...    ...    ...    ...    ...    ...    ...
        >>> 2018-02-19 08:00:00  False   True   True   True   True   True   True
        >>> 2018-02-19 09:00:00  False   True   True   True   True   True   True
        >>> 2018-02-19 10:00:00    NaN   True  False   True  False   True   True
        >>> 2018-02-19 11:00:00    NaN    NaN  False   True  False   True   True
        >>> 2018-02-19 12:00:00    NaN    NaN    NaN   True    NaN    NaN    NaN
        >>> define_operation_values(
        >>>         ts_analyse=ts_sample,
        >>>         operation=operation,
        >>>         df_startability=df_startability
        >>> )
                             dur_total   dur_net_port   dur_net_site    wait_start  wait_port   wait_site   transit_to_site transit_to_port
        >>> 2018-02-17 12:00:00       27.5            2.0            7.5          14.0                    0.0               2.0             2.0
        >>> 2018-02-17 13:00:00       26.5            2.0            7.5          13.0                    0.0               2.0             2.0
        >>> 2018-02-17 14:00:00       25.5            2.0            7.5          12.0                    0.0               2.0             2.0
        >>> 2018-02-17 15:00:00       24.5            2.0            7.5          11.0                    0.0               2.0             2.0
        >>> 2018-02-17 16:00:00       23.5            2.0            7.5          10.0                    0.0               2.0             2.0
        >>> 2018-02-17 17:00:00       22.5            2.0            7.5           9.0                    0.0               2.0             2.0
        >>> 2018-02-17 18:00:00       21.5            2.0            7.5           8.0                    0.0               2.0             2.0
        >>> 2018-02-17 19:00:00       20.5            2.0            7.5           7.0                    0.0               2.0             2.0
        >>> 2018-02-17 20:00:00       19.5            2.0            7.5           6.0                    0.0               2.0             2.0
        >>> 2018-02-17 21:00:00       18.5            2.0            7.5           5.0                    0.0               2.0             2.0
        >>> 2018-02-17 22:00:00       17.5            2.0            7.5           4.0                    0.0               2.0             2.0
        >>> 2018-02-17 23:00:00       16.5            2.0            7.5           3.0                    0.0               2.0             2.0
        >>> 2018-02-18 00:00:00       15.5            2.0            7.5           2.0                    0.0               2.0             2.0
        ...                        ...            ...            ...           ...                    ...               ...             ...
        >>> 2018-02-19 08:00:00        NaN            NaN            NaN           NaN                    NaN               NaN             NaN
        >>> 2018-02-19 09:00:00        NaN            NaN            NaN           NaN                    NaN               NaN             NaN
        >>> 2018-02-19 10:00:00        NaN            NaN            NaN           NaN                    NaN               NaN             NaN
        >>> 2018-02-19 11:00:00        NaN            NaN            NaN           NaN                    NaN               NaN             NaN
        >>> 2018-02-19 12:00:00        NaN            NaN            NaN           NaN                    NaN               NaN             NaN
    """

    def operation_variables(
            metocean_ts: int,
            activities: list,
            df_startability: pd.DataFrame,
            act_most_restrict_idx: int,
            prev_duration: float,
            MAX_WAIT: float
    ) -> dict:
        """For all timestep of the timeseries, this function tries to
        schedule the operation respecting each activity startability and
        the maximum time allowed between activities. If for the given
        timestep the operation cannot occur, it returns the timestep.
        If the operation can occur, it returns the duration and waitings
        for that operation.

        Args:
            metocean_ts (:obj:`int`): Timestep to be evaluated.
            activities (:obj:`list`): List of ~Activity of the operation.
            df_startability (:obj:`pandas.DataFrame`): Startability of the
                operation activities.
            act_most_restrict_idx (:obj:`int`): Index of the first most
                restrictive activity.
            prev_duration (:obj:`float`): Operation duration between
                :attr:`metocean_ts` and :attr:`act_most_restrict_idx`.
            MAX_WAIT (:obj:`float`): Maximum waiting on weather between two
                activities.

        Returns:
            dict: dictionary containing all figures related with this
                :attr:`metocean_ts`.

        Keyword Returns:
            metocean_ts (:obj:`int`): timestep of the metocean table to be
                analysed.
            ts_acts_start (:obj:`list`): list of timesteps where each activity
                from :attr:`activities` is starting, considering
                :attr:`metocean_ts`.
            op_dur (:obj:`float`): total duration of the operation.
            duration (:obj:`float`): duration of the operation without wating
                to start time.
            waitings (:obj:`dict`):
                to_start (:obj:`float`): Waiting on weather time to start the
                    first activity.
                site (:obj:`float`): Waiting on weather time between activities.
        """

        # Initialize time steps for the activities to start and to end
        ts_acts_start = [None] * len(activities)    # Example: [0, 48, ..., 104] or [0, 49, ..., 105]

        # Check what is the first timestep where this acvitivity can start.
        # We must consider previous acts net duration.
        act_low_first_ts = int(metocean_ts + prev_duration)
        act_low_startability = df_startability.iloc[act_low_first_ts:, act_most_restrict_idx].dropna()
        if act_low_startability.sum() == 0:
            # This activity cannot start anymore
            return metocean_ts

        # It means that it is possible to start this activity.
        # All possible timesteps:
        act_low_ts_all = act_low_startability[act_low_startability == True].index

        prev_solution_found = False
        next_solution_found = False

        for act_low_ts in act_low_ts_all:
            ts_acts_start[act_most_restrict_idx] = act_low_ts

            # Initialize current time step
            # Timestep where the most restrictive activity starts
            ts_curr = act_low_ts
            # Initialize current time
            # When the most restrictive activity start
            time_curr = act_low_ts + round((prev_duration % 1), 3)

            # Check if previous activities can start before this one:
            prev_act_idx = act_most_restrict_idx - 1
            if prev_act_idx == -1:
                # Most restrictive activity is the first one
                prev_solution_found = True
            while prev_act_idx > -1:
                act_dur = activities[prev_act_idx].duration

                # Update current time
                time_curr = time_curr - act_dur
                # Update current time step
                ts_curr = int(time_curr)

                ts_max = ts_curr

                ts_min = max(int(time_curr - MAX_WAIT), metocean_ts)
                act_startability = df_startability.iloc[ts_min:(ts_max+1), prev_act_idx].dropna()

                if act_startability.sum() == 0 or (time_curr - MAX_WAIT) < 0:
                    # This activity cannot start anymore.
                    # Get out from this while loop and
                    # test most restrictive activity next possible timstep.
                    break

                # This activity can occur in this interval
                if prev_act_idx == 0:
                    prev_solution_found = True
                # When?
                act_ts_all = act_startability[act_startability == True].index
                ts_acts_start[prev_act_idx] = act_ts_all[-1]
                time_curr = ts_acts_start[prev_act_idx]
                prev_act_idx -= 1

            if prev_solution_found is False:
                continue

            # Initialize current time
            # When the most restrictive activity ends
            time_curr = act_low_ts + round((prev_duration % 1), 3) + activities[act_most_restrict_idx].duration
            # Timestep where the most restrictive activity starts
            ts_curr = int(time_curr)

            # Check if next activities can start after this one:
            next_act_idx = act_most_restrict_idx + 1
            if next_act_idx == len(activities):
                # Most restrictive activity is the last one
                next_solution_found = True
            while next_act_idx < len(activities):
                act_dur = activities[next_act_idx].duration

                ts_min = ts_curr
                ts_max = min(int(time_curr + MAX_WAIT), df_startability.shape[0] - 1)

                act_startability = df_startability.iloc[ts_min:(ts_max+1), next_act_idx].dropna()

                if act_startability.sum() == 0 or (time_curr + MAX_WAIT) >= df_startability.shape[0]:
                    # This activity cannot start anymore.
                    # Get out from this while loop and
                    # test most restrictive activity next possible timestep.
                    break

                # This activity can occur in this interval
                if next_act_idx == len(activities) - 1:
                    next_solution_found = True
                # When?
                act_ts_all = act_startability[act_startability == True].index
                ts_acts_start[next_act_idx] = act_ts_all[0]

                # Update current time
                time_curr = ts_acts_start[next_act_idx] + act_dur
                # Update current time step
                ts_curr = int(time_curr)
                next_act_idx += 1

            if next_solution_found:
                # There is a solution for this timestep "metocean_ts"
                # Initialize durations
                durations = {
                        "port": 0.0,
                        "site": 0.0,
                        "transit_to_site": 0.0,
                        "transit_to_port": 0.0,
                        "shutdown_wtg": 0.0,
                        "shutdown_wec": 0.0,
                        "shutdown_pv": 0.0
                }
                # Initialize waiting times
                waitings = {
                        "to_start": ts_acts_start[0] - metocean_ts,
                        "port": 0.0,
                        "site": 0.0
                }
                time_curr = ts_acts_start[0]
                towing_to_site = False
                for act_idx, activity in enumerate(activities):
                    act_dur = round(activity.duration, 2)
                    act_loc = activity.location.lower()
                    if act_idx != 0:
                        act_prev_loc = activities[act_idx - 1].location.lower()
                        wait_time = ts_acts_start[act_idx] - time_curr
                        wait_time = max(round(wait_time, 2), 0)
                        act_prev_shutdown_wtg = activities[act_idx - 1].wtg_shutdown_dur * activities[act_idx - 1].duration
                        act_prev_shutdown_wec = activities[act_idx - 1].wec_shutdown_dur * activities[act_idx - 1].duration
                        act_prev_shutdown_pv = activities[act_idx - 1].pv_shutdown_dur * activities[act_idx - 1].duration
                    else:
                        act_prev_loc = act_loc
                        wait_time = 0
                        act_prev_shutdown_wtg = activity.wtg_shutdown_dur * act_dur
                        act_prev_shutdown_wec = activity.wec_shutdown_dur * act_dur
                        act_prev_shutdown_pv = activity.pv_shutdown_dur * act_dur

                    # Update durations
                    if act_loc == 'transit':
                        if act_prev_loc == 'site':
                            durations["transit_to_port"] += act_dur
                        else:
                            durations["transit_to_site"] += act_dur
                            if 'tow' in activity.name.lower():
                                towing_to_site = True
                    elif act_loc == 'port':
                        durations["port"] += act_dur
                    elif act_loc == 'site':
                        durations["site"] += act_dur
                    else:
                        _e = 'Activity location "%s" not recognized!' % act_loc
                        logging.error('Scheduling: ' + _e)
                        raise AssertionError(_e)
                    durations["shutdown_wtg"] += activity.wtg_shutdown_dur * activity.duration
                    durations["shutdown_wec"] += activity.wec_shutdown_dur * activity.duration
                    durations["shutdown_pv"] += activity.pv_shutdown_dur * activity.duration

                    # Update waitings
                    if wait_time > 0:
                        if act_prev_loc == 'port':
                            waitings["port"] += wait_time
                        elif act_prev_loc == 'site':
                            waitings["site"] += wait_time
                        elif act_prev_loc == 'transit' and act_loc == 'port':
                            waitings["port"] += wait_time
                        elif act_prev_loc == 'transit' and act_loc == 'site':
                            waitings["site"] += wait_time
                        elif act_prev_loc == 'transit' and act_loc == 'transit':
                            waitings["port"] += wait_time
                        else:
                            _e = 'Activity location "%s" not recognized!' % act_prev_loc
                            logging.error('Scheduling: ' + _e)
                            raise AssertionError(_e)

                        if act_prev_shutdown_wtg > 0 and activity.wtg_shutdown_dur > 0:
                            durations["shutdown_wtg"] += wait_time
                        if act_prev_shutdown_wec > 0 and activity.wec_shutdown_dur > 0:
                            durations["shutdown_wec"] += wait_time
                        if act_prev_shutdown_pv > 0 and activity.pv_shutdown_dur > 0:
                            durations["shutdown_pv"] += wait_time

                    # Update current time
                    time_curr += act_dur + wait_time
                    time_curr = round(time_curr, 2)

                op_dur = waitings["to_start"] + time_curr - ts_acts_start[0]
                op_dur = round(op_dur, 2)

                return {
                        "metocean_ts": metocean_ts,
                        "ts_acts_start": ts_acts_start,
                        "op_dur": op_dur,
                        "durations": durations,
                        "waitings": waitings,
                        "towing_shut": towing_to_site
                }
            else:
                # reset previous solution if the next_solution_found is not satisfied
                prev_solution_found = False

        return metocean_ts

    if len(operation.activities) <= 3:
        MAX_WAIT = 0
    logging.info(f'Operation_scheduler: For {operation.id} the maximum waiting on weather between activities is {MAX_WAIT} hours')

    df_index = deepcopy(df_startability.index)
    df_index = pd.DataFrame(df_index.tolist(), columns=['datetime'])
    df_index = df_index['datetime'].tolist()

    df_startability.reset_index(inplace=True, drop=True)

    duration_net = sum([act.duration for act in operation.activities])

    # Get most restricitve activity index () - the activity with least probability to start (lowest startability)
    act_starts_num = df_startability.sum(axis=0).to_list()
    act_low_idx = act_starts_num.index(min(act_starts_num))
    # Get net duration of the activities before the most restricitve activity
    acts_net_duration = sum([act.duration for act in operation.activities[:act_low_idx]])
    # For every timestep to be analysed, get when each activity of the operation would start, the operation total duration,
    # the other durations and the waiting times between

    final_idx = df_startability.index[-1]
    timestep = df_startability.index[0]

    list_st_dur_wt = []
    progress_bar = tqdm(total=final_idx, desc='Looping through Major Corrective Operation "%s - %s"' % (operation.id, operation.name), leave=False)
    for _ in range(final_idx):
        result_op_var = operation_variables(
            metocean_ts = timestep,
            activities = operation.activities,
            df_startability = df_startability,
            act_most_restrict_idx = act_low_idx,
            prev_duration = acts_net_duration,
            MAX_WAIT = MAX_WAIT
        )

        try:
            # Verify if the result is a dictionary otherwise break the loop (no more available shifts)
            if isinstance(result_op_var, dict):
                list_st_dur_wt.append(result_op_var)
                first_entry = list_st_dur_wt[-1]
                wow = int(first_entry['waitings']['to_start'])

                # Precompute base values
                base_ts = first_entry["metocean_ts"]
                base_wait = first_entry["waitings"]["to_start"]
                base_port = first_entry["waitings"]["port"]
                base_site = first_entry["waitings"]["site"]
                if first_entry["towing_shut"]:
                    max_key_shutdown = max(first_entry['durations'], key=first_entry['durations'].get)
                    base_shutdown = first_entry['durations'][max_key_shutdown]

                    # Deepcopy to avoid mutating original
                    base = deepcopy(first_entry)
                    del base["metocean_ts"]
                    del base["waitings"]
                    del base['durations'][max_key_shutdown]

                    base_durations = base['durations']  # all others except max_key_shutdown
                    base_other = {k: v for k, v in base.items() if k != "durations"}

                    new_entries = []
                    for i in range(1, wow + 1):
                        new_entry = {
                            "metocean_ts": base_ts + i,
                            "durations": {
                                **base_durations,
                                max_key_shutdown: base_shutdown - i
                            },
                            "waitings": {
                                "to_start": base_wait - i,
                                "port": base_port,
                                "site": base_site,
                            },
                            **base_other
                        }
                        new_entries.append(new_entry)

                # Create a shallow copy for shared structure (except mutable parts)
                else:
                    base = deepcopy(first_entry)
                    del base["metocean_ts"]
                    del base["waitings"]

                    # Precompute new entries efficiently
                    new_entries = [{
                        "metocean_ts": base_ts + i,
                        "waitings": {
                            "to_start": base_wait - i,
                            "port": base_port,
                            "site": base_site,
                        }, **base} for i in range(1, wow + 1)]

                list_st_dur_wt.extend(new_entries)

                timestep += int(wow+1)

                # Check that we do not exceed the final index
                if timestep >= final_idx:
                    break
                progress_bar.update(wow+1)
            else:
                raise TypeError('result_op_var is not a dict: %s %s' % type(result_op_var), result_op_var)
        except TypeError as e_:
            break
    progress_bar.close()

    # operation_variables() returns an integer if the operation cannot occur and
    # a tuple if it can.
    # Store both values. If the operation cannot start in a certain timestep, the
    # wait to start time must be accessed
    list_op_impossible = [
            elem
            for elem in list_st_dur_wt
            if type(elem) != dict
    ]
    list_st_dur_wt = [
            elem
            for elem in list_st_dur_wt
            if type(elem) == dict
    ]
    if len(list_st_dur_wt) == 0:
        _e = f'The operation {operation.id} can never occur. OLCs may be to resctric.'
        raise InterruptedError('Scheduling: ' + _e)

    else:
        list_op_start_idx = [elem["metocean_ts"] for elem in list_st_dur_wt]
        # list_op_start = [elem["ts_acts_start"][0] for elem in list_st_dur_wt]
        list_op_dur = [elem["op_dur"] for elem in list_st_dur_wt]
        list_durations = [elem["durations"] for elem in list_st_dur_wt]
        list_waitings = [elem["waitings"] for elem in list_st_dur_wt]

    # Define a Operation values DataFrame
    # Dur_site should be duration_net instead

    df_op_values = pd.DataFrame(
            np.nan,
            index=df_startability.index.tolist(),
            columns=[
                    'dur_total',
                    'dur_net_port',
                    'dur_net_site',
                    'wait_start',
                    'wait_port',
                    'wait_site',
                    'transit_to_site',
                    'transit_to_port',
                    'dur_shutdown_wtg',
                    'dur_shutdown_wec',
                    'dur_shutdown_pv'
            ]
    )

    df_durations = pd.DataFrame(list_durations)
    df_waitings = pd.DataFrame(list_waitings)

    # Operation values DataFrame filtered for possible timesteps
    df_op_values_f = df_op_values[df_op_values.index.isin(list_op_start_idx)]
    df_op_values_f.loc[:, 'dur_net_port'] = df_durations['port'].tolist()
    df_op_values_f.loc[:, 'dur_net_site'] = df_durations['site'].tolist()
    df_op_values_f.loc[:, 'transit_to_site'] = df_durations['transit_to_site'].tolist()
    df_op_values_f.loc[:, 'transit_to_port'] = df_durations['transit_to_port'].tolist()
    df_op_values_f.loc[:, 'dur_shutdown_wtg'] = df_durations['shutdown_wtg'].tolist()
    df_op_values_f.loc[:, 'dur_shutdown_wec'] = df_durations['shutdown_wec'].tolist()
    df_op_values_f.loc[:, 'dur_shutdown_pv'] = df_durations['shutdown_pv'].tolist()
    df_op_values_f.loc[:, 'wait_start'] = df_waitings['to_start'].tolist()
    df_op_values_f.loc[:, 'wait_port'] = df_waitings['port'].tolist()
    df_op_values_f.loc[:, 'wait_site'] = df_waitings['site'].tolist()
    df_op_values_f['dur_total'] = df_op_values_f.iloc[:, 1:8].sum(axis=1, skipna=False)
    df_op_values_f['dur_total'] = df_op_values_f['dur_total'].round(1)

    df_op_values.update(df_op_values_f)

    # Operation values DataFrame filtered for impossible timesteps
    df_op_values_f = df_op_values[df_op_values.index.isin(list_op_impossible)]
    df_op_values_f.iloc[:,:] = np.nan
    df_op_values.update(df_op_values_f)

    # Iterate over columns and replace 0 with nan if the operation net_duration is > remaining TS
    last_valid_index = df_startability.shape[0] - duration_net
    df_op_values.loc[df_op_values.index > last_valid_index, :] = np.nan

    df_op_values.index = df_index
    df_op_values.reset_index(inplace=True)
    df_op_values.rename(columns={df_op_values.columns[0]: 'datetime'}, inplace=True)

    # Save schedule as a CSV
    if out_dir is not None:
        save_file_csv(df_to_save = df_op_values, save_dir = out_dir)
        logging.info('Schedule: saved as "%s".' % out_dir)

    return df_op_values



if __name__ == '__main__':
    pass