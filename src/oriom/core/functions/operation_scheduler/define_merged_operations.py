# Import packages
import pandas as pd
import numpy as np
import math as mt
from datetime import timedelta
from copy import deepcopy
from tqdm import tqdm
import logging


def define_merged_operations_values(
        ts_analyse: list,
        operation,
        df_workability_group: pd.DataFrame,
        df_workability_solo: pd.DataFrame,
        shift_data: dict,
        transit_duration: float,
        shutdown_wtg: float,
        shutdown_wec: float,
        shutdown_pv: float,
        double_shift: bool=False,
        out_dir: str=None
) -> pd.DataFrame:
    """
    This function is to be used only in case of grouped inspections for which two ``workability``
    are to be considered.

    Note:
        Based on the number of shifts and its duration, :func:`define_shift_values`
        returns a timeseries dataframe with the operation total duration, waitings
        and transit times.
        IMPORTANT NOTE: the shutdown durations are the sum of all net durations
        of work at the device.

    Args:
        ts_analyse (:obj:`list`): Timesteps of the metocean dataframe that are
            analysed.
        operations (:obj:`OperationInspectionSite` or :obj:`OperationInspectionPort`): Operation.
        df_workability_group (:obj:`pd.DataFrame`): `~Workability` when operations
            are done in parallel.
        df_workability_solo (:obj:`pd.DataFrame`): `~Workability` for the
            operation that last longer alone.
        shift_data (:obj:`dict`): Information about the shift with the
            following format:
        number_shifts_main (:obj:`int`):
            Number of shifts required for doing two operations in parallel.
        duration_shift_main (:obj:`float`):
            Duration of the shifts for doing the operations in parallel.
        number_shifts_last (:obj:`int`):
            Number of shifts required for the operation that lasts longer when done solo.
        duration_shift_last (:obj:`float`):
            Duration of the shift for the operation that lasts longer when done solo.
        transit_duration (:obj:`float`): Duration of the transit btween the port
            and the site.
        shutdown_wtg (:obj:`float`): For how long the WTGs are disconnected.
        shutdown_wec (:obj:`float`): For how long the WECs are disconnected.
        shutdown_pv (:obj:`float`): For how long the PVs are disconnected.
        double_shift (:obj:`bool`, *optional*): If the shifts are consecutive or
            not. Defaults to False.
        out_dir (:obj:`str`, *optional*): Path for the out directory.
            Defaults to None.

    Raises:
        ValueError: If this function is called for a set of :class:`Activity`s.

    Returns:
        :obj:`pd.DataFrame`: Timeseries with the inspection total duration, waitings and transit times.
    """
    # Get information from shift_data
    shift_num_group = shift_data["number_shifts_main"]
    shift_duration_group = shift_data["duration_shift_main"]
    shift_num_solo = shift_data["number_shifts_last"]
    shift_duration_solo = shift_data["duration_shift_last"]

    if df_workability_group.shape[1] > 1:
        _e = 'This function only works with operations.'
        raise ValueError('Scheduling: ' + _e)
    if df_workability_solo.shape[1] > 1:
        _e = 'This function only works with operations.'
        raise ValueError('Scheduling: ' + _e)

    # TODO: The double shift means that I can conduct a shift consecutively after the other, this not mean that it needs
    # to be done between the 8 and the 20 (light time). This should be changed in the future. Light OLC is already present
    # in the workability file.
    HOUR_MIN = 8
    HOUR_MAX = 20
    if double_shift:
        HOUR_MIN = -1
        HOUR_MAX = 25

    df_workability_group = deepcopy(df_workability_group)
    df_workability_solo = deepcopy(df_workability_solo)

    df_op_values = pd.DataFrame(
            np.nan,
            index=df_workability_group.index.tolist(),
            columns=[
                    'dur_total',
                    'dur_net_site_group',
                    'dur_net_site_solo',
                    'wait_start',
                    'wait_port_group',
                    'wait_port_solo',
                    'transit_to_site_group',
                    'transit_to_site_solo',
                    'transit_to_port_group',
                    'transit_to_port_solo',
                    'dur_shutdown_wtg',
                    'dur_shutdown_wec',
                    'dur_shutdown_pv'
            ]
    )

    # Filter the workabability based on the minimum and maximum hours
    df_workability_group = df_workability_group.loc[
            (df_workability_group.index.hour >= HOUR_MIN) & \
            (df_workability_group.index.hour < HOUR_MAX)
    ]
    df_workability_solo = df_workability_solo.loc[
            (df_workability_solo.index.hour >= HOUR_MIN) & \
            (df_workability_solo.index.hour < HOUR_MAX)
    ]

    # Check if all workabilities are always is True
    # (common for port operations and operations with high OLCs)
    all_true = [False, False]
    if df_workability_group.shape[0] == df_workability_group.loc[df_workability_group.iloc[:, 0] == True].shape[0]:
        all_true[0] = True
    if df_workability_solo.shape[0] == df_workability_solo.loc[df_workability_solo.iloc[:, 0] == True].shape[0]:
        all_true[1] = True

    # Filter workabilities based on the workability
    df_workability_group = df_workability_group.loc[df_workability_group.iloc[:, 0] == True]
    df_workability_solo = df_workability_solo.loc[df_workability_solo.iloc[:, 0] == True]

    # Duration of the shifts in seconds
    shift_duration_group_sec = timedelta(seconds=(shift_duration_group * 3600))
    shift_duration_solo_sec = timedelta(seconds=(shift_duration_solo * 3600))

    # Get a list of dates and time where operation shifts can take place
    startable_ts_group = []
    dt_ini = df_workability_group.index[0]
    dt_prev = df_workability_group.index[0]
    for dt, _ in df_workability_group.iloc[1:,:].iterrows():
        dt_diff = dt - dt_prev

        hour_number = dt - dt_ini
        if dt_diff.total_seconds() > 3600:
            # End of consecutive hours
            if (dt_prev - dt_ini + timedelta(seconds=3600)) >= shift_duration_group_sec:
                startable_ts_group.append(dt_ini)

            dt_ini = dt
        else:
            # Still on consecutive hours
            # Check if the mininum time for a shift was already fulfilled
            if hour_number >= shift_duration_group_sec:
                startable_ts_group.append(dt_ini)
                # dt_ini = dt
                dt_ini += timedelta(seconds=3600)
        dt_prev = dt

    # Get a list of dates and time where the last shift can take place
    startable_ts_solo = []
    dt_ini = df_workability_solo.index[0]
    dt_prev = df_workability_solo.index[0]
    for dt, _ in df_workability_solo.iloc[1:,:].iterrows():
        dt_diff = dt - dt_prev

        hour_number = dt - dt_ini
        if dt_diff.total_seconds() > 3600:
            # End of consecutive hours
            if (dt_prev - dt_ini + timedelta(seconds=3600)) >= shift_duration_solo_sec:
                startable_ts_solo.append(dt_ini)

            dt_ini = dt
        else:
            # Still on consecutive hours
            # Check if the mininum time for a shift was already fulfilled
            if hour_number >= shift_duration_solo_sec:
                startable_ts_solo.append(dt_ini)
                # dt_ini = dt
                dt_ini += timedelta(seconds=3600)
        dt_prev = dt

    # Define net durations
    dur_net_site_group = shift_num_group * (shift_duration_group - 2 * transit_duration)
    dur_net_site_solo = shift_num_solo * (shift_duration_solo - 2 * transit_duration)
    transit_duration_group = transit_duration * shift_num_group
    transit_duration_solo = transit_duration * shift_num_solo

    df_op_values.reset_index(inplace=True)
    df_op_values.rename(columns={"index": 'datetime'}, inplace=True)

    ds_startable_ts_group = pd.Series(startable_ts_group)
    ds_startable_ts_solo = pd.Series(startable_ts_solo)
    for ts in tqdm(
            ts_analyse,
            desc='Inspection "%s - %s"' % (operation.id, operation.name),
            leave=False
    ):
        ts_unfeasible = False
        # Calculate the waiting at port (time between shifts) to complete all shifts
        ts_group_operating = []
        waiting_group = 0
        for shift_group in range(0, shift_num_group):
            curr_ts = int(ts + shift_group*shift_duration_group + waiting_group)
            # Check when is the first oportunity to start the s_th shift_group
            curr_ts_datetime = df_op_values.iloc[curr_ts]['datetime']
            if curr_ts_datetime in startable_ts_group:
                ts_group_operating.extend([
                        curr_ts_datetime + ts_aux*timedelta(hours=1)
                        for ts_aux in range(0, mt.ceil(shift_duration_group))
                ])
                continue

            # It is not possible to start the grouped shift yet.
            # Check when will be the next possible timestep to start.
            # From the grouped shifts, drop all possible starting
            # timesteps smaller than the current timestep (curr_ts)
            ds_startable_ts_group_greater = ds_startable_ts_group[
                    ds_startable_ts_group >= curr_ts_datetime
            ]
            try:
                next_ts_group = ds_startable_ts_group_greater.iloc[0]
            except IndexError:
                # The grouped shift is not possble again
                wait_start = np.nan
                wait_port_group = np.nan
                wait_port_solo = np.nan
                ts_unfeasible = True
                break

            ts_group_operating.extend([
                    next_ts_group + ts_aux*timedelta(hours=1)
                    for ts_aux in range(0, mt.ceil(shift_duration_group))
            ])
            # Calculate waiting between curr_ts and next_ts_group
            waiting_group_dt = next_ts_group - df_op_values.iloc[curr_ts]['datetime']
            waiting_group += ((waiting_group_dt.days * 24) + (waiting_group_dt.seconds / 3600))
        del waiting_group
        # Shifts for grouped operations scheduled

        ts_solo_operating = []
        waiting_solo = 0
        shift_solo = 0
        while shift_solo < shift_num_solo:
            curr_ts = int(ts + shift_solo*shift_duration_solo + waiting_solo)
            # Check when is the first oportunity to start the s_th shift_solo
            curr_ts_datetime = df_op_values.iloc[curr_ts]['datetime']
            if curr_ts_datetime in startable_ts_solo:
                # Get timesteps where the solo operation will take place
                ts_solo_operating_aux = [
                        curr_ts_datetime + ts_aux*timedelta(hours=1)
                        for ts_aux in range(0, mt.ceil(shift_duration_solo))
                ]
                # If any of these time steps is part of the time steps
                # when grouped operation is taking place, skip this
                # otherwise, go to next shift
                if len([ts_aux for ts_aux in ts_solo_operating_aux if ts_aux in ts_group_operating]) == 0:
                    ts_solo_operating.extend(ts_solo_operating_aux)
                    shift_solo += 1
                    continue
                waiting_solo += 1

            # It is not possible to start the solo shift yet.
            # Check when will be the next possible timestep to start.
            # From the solo shifts, drop all possible starting
            # timesteps smaller than the current timestep (curr_ts)
            ds_startable_ts_solo_greater = ds_startable_ts_solo[
                    ds_startable_ts_solo >= curr_ts_datetime
            ]
            try:
                next_ts_solo = ds_startable_ts_solo_greater.iloc[0]
            except IndexError:
                # The solo shift is not possble again
                wait_start = np.nan
                wait_port_group = np.nan
                wait_port_solo = np.nan
                ts_unfeasible = True
                break

            ts_solo_operating_aux = [
                    next_ts_solo + ts_aux*timedelta(hours=1)
                    for ts_aux in range(0, mt.ceil(shift_duration_solo))
            ]
            # If any of these time steps is part of the time steps
            # when grouped operation is taking place, skip this
            # otherwise, go to next shift
            if len([ts_aux for ts_aux in ts_solo_operating_aux if ts_aux in ts_group_operating]) == 0:
                ts_solo_operating.extend(ts_solo_operating_aux)
                # Calculate waiting between curr_ts and next_ts_solo
                waiting_solo_dt = next_ts_solo - df_op_values.iloc[curr_ts]['datetime']
                waiting_solo += ((waiting_solo_dt.days * 24) + (waiting_solo_dt.seconds / 3600))
                shift_solo += 1
            else:
                waiting_solo += 1
        del waiting_solo
        # Shifts for solo operations scheduled
        if len(ts_solo_operating) == 0:
            # Add something meaningless (out of workability
            # dataframe) to avoid errors
            ts_solo_operating.extend([
                    df_op_values['datetime'].iloc[0] - timedelta(hours=1),
                    df_op_values['datetime'].iloc[-1] + timedelta(hours=1)
            ])

        if ts_unfeasible is False:
            # Create a timeseries where 2 represents the operations in paralle
            # and 1 represents the solo operation
            df_operations_rep = pd.DataFrame(
                    data=np.nan,
                    index=df_op_values['datetime'],
                    columns=['op_rep', 'wait', 'wait_sum']
            )
            df_operations_rep.index = pd.to_datetime(df_operations_rep.index)

            # Delete all timesteps that do not matter
            first_ts = df_op_values.iloc[ts]['datetime']
            # Get last ts
            last_ts = max(ts_group_operating[-1], ts_solo_operating[-1])
            df_operations_rep = df_operations_rep[
                    (df_operations_rep.index >= first_ts) &
                    (df_operations_rep.index <= last_ts)
            ]

            df_operations_rep['op_rep'][df_operations_rep.index.isin(ts_group_operating)] = 2
            df_operations_rep['op_rep'][df_operations_rep.index.isin(ts_solo_operating)] = 1
            df_operations_rep['op_rep'][~df_operations_rep.index.isin(ts_group_operating+ts_solo_operating)] = 0
            df_operations_rep['wait'][df_operations_rep.index.isin(ts_group_operating)] = 0
            df_operations_rep['wait'][df_operations_rep.index.isin(ts_solo_operating)] = 0
            df_operations_rep['wait'].fillna(value=1, inplace=True)
            df_operations_rep['wait_sum'][df_operations_rep.index.isin(ts_group_operating)] = 0
            df_operations_rep['wait_sum'][df_operations_rep.index.isin(ts_solo_operating)] = 0

            # Get waiting by reverted Dataframe and backfill nan value with incremented waiting
            df_operations_rep_rev = df_operations_rep['wait_sum'].iloc[::-1].notnull()
            df_operations_rep['wait_sum'] = df_operations_rep['wait_sum'].bfill() + \
                    df_operations_rep_rev.groupby(df_operations_rep_rev.cumsum()).cumcount()

            wait_start = float(df_operations_rep['wait_sum'].iloc[0])
            # Initialize waitings
            wait_port_group = df_operations_rep['wait'].sum(axis=0) - wait_start
            wait_port_solo = 0
            # Split the waitings depending on the operations
            if startable_ts_group[0] > startable_ts_solo[0]:
                # The first operation is a solo operation
                # Total waiting between the end of the first solo shift
                # and the begining of the first grouped shift
                partial_wait = df_operations_rep[
                        (df_operations_rep.index > ts_solo_operating[0]) &
                        (df_operations_rep.index < ts_group_operating[0])
                ]['wait'].sum(axis=0)
                wait_port_solo += partial_wait
                wait_port_group -= partial_wait

            if startable_ts_solo[-1] > startable_ts_group[-1]:
                # The last operation is a solo operation
                # Total waiting between the end of the last group shift
                # and the begining of the last solo shift
                partial_wait = df_operations_rep[
                        (df_operations_rep.index > ts_group_operating[-1]) &
                        (df_operations_rep.index < ts_solo_operating[-1])
                ]['wait'].sum(axis=0)
                wait_port_solo += partial_wait
                wait_port_group -= partial_wait

            dur_net_site_group = round(dur_net_site_group, 2)
            dur_net_site_solo = round(dur_net_site_solo, 2)
            transit_duration_group = round(transit_duration_group, 2)
            transit_duration_solo = round(transit_duration_solo, 2)
            wait_start = round(wait_start, 2)
            wait_port_group = round(wait_port_group, 2)
            wait_port_solo = round(wait_port_solo, 2)

            df_op_values.loc[ts, 'dur_net_site_group'] = dur_net_site_group
            df_op_values.loc[ts, 'dur_net_site_solo'] = dur_net_site_solo
            df_op_values.loc[ts, 'transit_to_site_group'] = transit_duration_group
            df_op_values.loc[ts, 'transit_to_site_solo'] = transit_duration_solo
            df_op_values.loc[ts, 'transit_to_port_group'] = transit_duration_group
            df_op_values.loc[ts, 'transit_to_port_solo'] = transit_duration_solo

            df_op_values.loc[ts, 'wait_start'] = wait_start
            df_op_values.loc[ts, 'wait_port_group'] = wait_port_group
            df_op_values.loc[ts, 'wait_port_solo'] = wait_port_solo

            df_op_values.loc[ts, 'dur_shutdown_wtg'] = shutdown_wtg
            df_op_values.loc[ts, 'dur_shutdown_wec'] = shutdown_wec
            df_op_values.loc[ts, 'dur_shutdown_pv'] = shutdown_pv

        else:
            df_op_values.loc[ts, 'dur_total'] = np.nan
            df_op_values.loc[ts, 'dur_shutdown_wtg'] = np.nan
            df_op_values.loc[ts, 'dur_shutdown_wec'] = np.nan
            df_op_values.loc[ts, 'dur_shutdown_pv'] = np.nan

    df_op_values['dur_total'] = df_op_values.iloc[:, 2:11].sum(axis=1, skipna=False)
    df_op_values['dur_total'] = df_op_values['dur_total'].round(1)

    df_op_values.set_index(keys='datetime', inplace=True, drop=True)

    # Save schedule as a CSV
    if out_dir is not None:
        df_op_values.to_csv(
                path_or_buf=out_dir,
                sep=','
        )
        logging.info('Schedule: saved as "%s".' % out_dir)

    return df_op_values