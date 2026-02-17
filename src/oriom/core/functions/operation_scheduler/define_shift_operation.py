 # Import packages
import pandas as pd
import numpy as np
import math as mt
from datetime import timedelta
from copy import deepcopy
from tqdm import tqdm
import logging

from oriom.utils.aux_functions import save_file_csv


def copy_row_wait_start(
    df_op_values: pd.DataFrame,
    ts: int,
    wait_start: float
) -> tuple[pd.DataFrame, int, bool]:
    
    """
    Copies operation values forward in time while 'wait_start' is active,
    filling future time steps with the same values from time `ts`,
    and decreasing the 'wait_start' counter each hour.

    If the index range goes beyond the DataFrame's index space, a warning is logged
    and the function returns early.

    Args:
        df_op_values (pd.DataFrame): DataFrame containing operational values indexed by time.
        ts (int): The current time index from which values will be copied.
        wait_start (float): Number of time steps to wait before starting the operation.

    Returns:
        tuple:
            - pd.DataFrame: Updated DataFrame with future values filled.
            - int: The last index written to (`wait_start_idx`) or `ts` if failed.
            - bool: True if update was successful, False otherwise.
    """

    try:
        # Compute target range to fill
        wait_start_idx = ts + int(wait_start)
        indices = np.arange(ts + 1, wait_start_idx + 1)

        # Ensure the DataFrame includes the required future indices
        if not np.all(np.isin(indices, df_op_values.index)):
            df_op_values = df_op_values.reindex(df_op_values.index.union(indices))

        # Select columns to copy (excluding first column)
        cols_to_copy = df_op_values.columns[1:]

        # Vectorized value copy
        values = df_op_values.loc[ts, cols_to_copy].values
        df_op_values.loc[indices, cols_to_copy] = np.tile(values, (len(indices), 1))

        # Decrease 'wait_start' for each hour ahead
        df_op_values.loc[indices, 'wait_start'] = wait_start - np.arange(1, len(indices) + 1)

        return df_op_values, wait_start_idx, wait_start, True

    except ValueError as e_:
        wait_start_idx = int(ts)
        logging.warning(
            f"Oper_schedule: No more 'wait_start' available after index {wait_start_idx}, error: {e_}"
        )
        return df_op_values, wait_start_idx, wait_start, False


def define_shift_operation_values(
        df_metocean: pd.DataFrame,
        operation,
        df_workability: pd.DataFrame,
        shift_data: dict,
        transit_duration: float,
        shutdown_wtg: float,
        shutdown_wec: float,
        shutdown_pv: float,
        duration_shift: float = 12,
        out_dir: str=None
) -> pd.DataFrame:
    """
    This function is to be used only in case of operations defined with the working shift function.

    Based on the number of shifts and its duration, :func:`define_shift_values`
    returns a timeseries dataframe with the operation total duration, waitings
    and transit times.

    IMPORTANT NOTE: all the values obtained are the sum of all shifts of work at the device.

    Args:
        df_metocean (:obj:`pandas.DataFrame`): metocean timeseries table.
            Rows as timesteps and colums as sea conditions.
        operation (:obj:`~OperationInspection` or :obj:`~CorrectiveMinor`): Operation.
        df_workability (:obj:`pd.DataFrame`): Workability of the inspection.
        shift_data (:obj:`dict`): Information about the shift with the
        following format:
            number_shifts_main (:obj:`int`): Number of shifts required for doing two operations in parallel.
            duration_shift_main (:obj:`float`): Duration of the shifts for doing the operations in parallel.
            number_shifts_last (:obj:`int`): Number of shifts required for the operation that lasts longer when done solo.
            duration_shift_last (:obj:`float`): Duration of the shift for the operation that lasts longer when done solo.
        transit_duration (:obj:`float`): Duration of the transit btween the port
            and the site.
        shutdown_wtg (:obj:`float`): For how long the WTGs are disconnected.
        shutdown_wec (:obj:`float`): For how long the WECs are disconnected.
        shutdown_pv (:obj:`float`): For how long the PVs are disconnected.
        out_dir (:obj:`str`, *optional*): Path for the out directory.
            Defaults to ``None``.

    Raises:
        ValueError: If this function is called for a set of :class:`Activity`.

    Returns:
        :obj:`pd.DataFrame`: Timeseries with the inspection total duration, waitinngs and transit times.
    """

    # Get information from shift_data
    shift_num_main = shift_data["number_shifts_main"]
    shift_duration_main = shift_data["duration_shift_main"]
    shift_num_last = shift_data["number_shifts_last"]
    shift_duration_last = shift_data["duration_shift_last"]

    if df_workability.shape[1] > 1:
        _e = 'Workability: This function only works with operations.'
        raise ValueError(_e)
    
    df_workability = deepcopy(df_workability)

    df_op_values = pd.DataFrame(
        np.nan,
        index=df_workability.index.tolist(),
        columns=[
            'dur_total',
            'dur_net_site',
            'wait_start',
            'wait_port',
            'transit_to_site',
            'transit_to_port',
            'dur_shutdown_wtg',
            'dur_shutdown_wec',
            'dur_shutdown_pv',
            'days_inspected'
        ]
    )

    df_op_values['days_inspected'] = df_op_values['days_inspected'].astype(object)
    masked_workability = df_workability.iloc[:, 0]

    # Check if all workability is True (common for port operations 24/7 of work)
    if masked_workability.all():
        dur_net_site = round(shift_num_main * (shift_duration_main - 2 * transit_duration) + shift_num_last * (shift_duration_last - 2 * transit_duration), 2)
        transit_duration = round(transit_duration * (shift_num_main+shift_num_last), 2)

        df_op_values.loc[:, 'dur_net_site'] = dur_net_site
        df_op_values.loc[:, 'transit_to_site'] = transit_duration
        df_op_values.loc[:, 'transit_to_port'] = transit_duration

        df_op_values.loc[:, 'wait_start'] = 0
        df_op_values.loc[:, 'wait_port'] = 0

        df_op_values['dur_total'] = df_op_values.iloc[:, 1:].sum(axis=1)

        df_op_values.loc[:, 'dur_shutdown_wtg'] = shutdown_wtg
        df_op_values.loc[:, 'dur_shutdown_wec'] = shutdown_wec
        df_op_values.loc[:, 'dur_shutdown_pv'] = shutdown_pv
        df_op_values['dur_total'] = df_op_values.iloc[:, 1:6].sum(axis=1)

        df_op_values['wait_start'] = df_op_values['wait_start'].astype(int)
        
        df_op_values.reset_index(inplace=True)
        df_op_values.rename(columns={"index": 'datetime'}, inplace=True)
        
        # Save schedule as a CSV
        if out_dir is not None:
            save_file_csv(df_to_save = df_op_values, save_dir = out_dir)
            logging.info('Schedule: saved as "%s".' % out_dir)

        return df_op_values

    # Filter the workabability based on the workability
    df_workability = df_workability.loc[df_workability.iloc[:, 0] == True]

    shift_duration_main_sec = timedelta(seconds=(shift_duration_main * 3600))
    shift_duration_last_sec = timedelta(seconds=(shift_duration_last * 3600))

    # Get a list of dates and time where shifts can take place
    hours_group_main = []
    dt_ini = df_workability.index[0]
    dt_prev = df_workability.index[0]
    for dt, _ in df_workability.iloc[1:,:].iterrows():
        dt_diff = dt - dt_prev

        hour_number = dt - dt_ini
        if dt_diff.total_seconds() > 3600:
            # End of consecutive hours
            if (dt_prev - dt_ini + timedelta(seconds=3600)) >= shift_duration_main_sec:
                hours_group_main.append(dt_ini)

            dt_ini = dt
        else:
            # Still on consecutive hours
            # Check if the mininum time for a shift was already fulfilled
            if hour_number >= shift_duration_main_sec:
                hours_group_main.append(dt_ini)
                # dt_ini = dt
                dt_ini += timedelta(seconds=3600)
        dt_prev = dt

    # Get a list of dates and time where the last shift can take place
    hours_group_last = []
    dt_ini = df_workability.index[0]
    dt_prev = df_workability.index[0]

    for dt, _ in df_workability.iloc[1:,:].iterrows():
        dt_diff = dt - dt_prev

        hour_number = dt - dt_ini
        if dt_diff.total_seconds() > 3600:
            # End of consecutive hours
            if (dt_prev - dt_ini + timedelta(seconds=3600)) >= shift_duration_last_sec:
                hours_group_last.append(dt_ini)

            dt_ini = dt
        else:
            # Still on consecutive hours
            # Check if the mininum time for a shift was already fulfilled
            if hour_number >= shift_duration_last_sec:
                hours_group_last.append(dt_ini)
                # dt_ini = dt
                dt_ini += timedelta(seconds=3600)
        dt_prev = dt

    # Define net durations
    dur_net_site = shift_num_main * (shift_duration_main - 2 * transit_duration) + shift_num_last * (shift_duration_last - 2 * transit_duration)
    transit_duration = transit_duration * (shift_num_main+shift_num_last)

    df_op_values.reset_index(inplace=True)
    df_op_values.rename(columns={"index": 'datetime'}, inplace=True)
    
    ds_hours_group_main = pd.Series(hours_group_main)
    ds_hours_group_last = pd.Series(hours_group_last)

    ts = df_op_values.index[0]  
    final_idx = df_op_values.index[-1]

    pbar = tqdm(
        range(final_idx),
        desc='Inspection "%s - %s"' % (operation.id, operation.name),
        leave=False
    )
    
    while ts < final_idx:
        days_inspected = []
        # Check when is the first oportunity to start the main shift
        ts_datetime = df_op_values.iloc[ts]['datetime']
        ts_unfeasible = False
        if ts_datetime in hours_group_main:
            wait_start = 0
            if shift_num_main:
                days_inspected.append(ts_datetime)
        else:
            # Drop all possible starting timesteps smaller than the current timestep (ts)
            ds_hours_group_main_greater = ds_hours_group_main[ds_hours_group_main >= ts_datetime]
            try:
                # Difference between the next possible timestep and the current
                wait_start = round(((ds_hours_group_main_greater.iloc[0] - ts_datetime).total_seconds() / 3600), 1)
                if shift_num_main:
                    days_inspected.append(ds_hours_group_main_greater.iloc[0])

                # Rounded to hours with 1 decimal digit
            except IndexError:
                # No more available possible times
                wait_start = np.nan
                df_op_values.loc[ts, 'dur_total'] = np.nan
                df_op_values.loc[ts, 'dur_shutdown_wtg'] = np.nan
                df_op_values.loc[ts, 'dur_shutdown_wec'] = np.nan
                df_op_values.loc[ts, 'dur_shutdown_pv'] = np.nan
                ts_unfeasible = True

        # Calculate the waiting at port (time between shifts) to complete all shifts
        wait_port = 0
        for shift in range(1, shift_num_main):
            next_ts = int(ts + wait_start + shift*shift_duration_main + wait_port)
            # Check when is the first oportunity to start the s_th shift
            next_ts_datetime = df_op_values.iloc[next_ts]['datetime']
            if next_ts_datetime in hours_group_main:
                days_inspected.append(next_ts_datetime)
                continue

            # Drop all possible starting timesteps smaller than the current timestep (next_ts)
            ds_hours_group_main_greater = ds_hours_group_main[ds_hours_group_main >= next_ts_datetime]
            try:
                # Difference between the next possible timestep and the current
                wait_port += (ds_hours_group_main_greater.iloc[0] - next_ts_datetime).total_seconds() / 3600
                days_inspected.append(ds_hours_group_main_greater.iloc[0])

            except IndexError:
                # No more available possible times
                wait_start = np.nan
                wait_port = np.nan
                ts_unfeasible = True
                break

        # And finally for the last shift
        if not ts_unfeasible and shift_num_last not in (0, None):
            if shift_num_main == 0:
                wait_start = 0
            curr_ts = int(ts + wait_start + shift_num_main*shift_duration_main + wait_port)
            # Check when is the first oportunity to start the last shift
            try:
                next_ts_datetime = df_op_values.iloc[curr_ts]['datetime']
                insp_last_day = next_ts_datetime
                if next_ts_datetime not in hours_group_last:
                    # Drop all possible starting timesteps smaller than the current timestep (curr_ts)
                    ds_hours_group_last_greater = ds_hours_group_last[ds_hours_group_last >= next_ts_datetime]
                    try:
                        # Difference between the next possible timestep and the current
                        time_wait = (ds_hours_group_last_greater.iloc[0] - next_ts_datetime).total_seconds() / 3600
                        # If main_shift present add to wait at port, else at wait at start
                        if shift_num_main > 0:
                            wait_port += time_wait
                        else:
                            wait_start = round(time_wait, 1)
                        insp_last_day = ds_hours_group_last_greater.iloc[0]
                    except IndexError:
                        # No more available possible times
                        wait_start = np.nan
                        wait_port = np.nan
                        ts_unfeasible = True
                        
                days_inspected.append(insp_last_day)

            except IndexError:
                # Timeseries ended
                wait_start = np.nan
                wait_port = np.nan
                ts_unfeasible = True

        if ts_unfeasible is False:
            dur_net_site = round(dur_net_site, 2)
            transit_duration = round(transit_duration, 2)
            wait_port = round(wait_port, 2)
            wait_start = round(wait_start, 2)

            df_op_values.loc[ts, 'dur_net_site'] = dur_net_site
            df_op_values.loc[ts, 'transit_to_site'] = transit_duration
            df_op_values.loc[ts, 'transit_to_port'] = transit_duration

            df_op_values.loc[ts, 'wait_start'] = wait_start
            df_op_values.loc[ts, 'wait_port'] = wait_port

            # If is port operation not 24/7 of work and has shutdown add also wait at port as shutdown
            df_op_values.loc[ts, 'dur_shutdown_wtg'] = shutdown_wtg
            df_op_values.loc[ts, 'dur_shutdown_wec'] = shutdown_wec
            df_op_values.loc[ts, 'dur_shutdown_pv'] = shutdown_pv
            df_op_values.at[ts, 'days_inspected'] = days_inspected

        else:
            df_op_values.loc[ts, 'dur_total'] = np.nan
            df_op_values.loc[ts, 'dur_shutdown_wtg'] = np.nan
            df_op_values.loc[ts, 'dur_shutdown_wec'] = np.nan
            df_op_values.loc[ts, 'dur_shutdown_pv'] = np.nan
            df_op_values.at[ts, 'days_inspected'] = np.nan

            ts = final_idx

        df_op_values, wait_start_idx, wait_start, success = copy_row_wait_start(df_op_values, ts=ts, wait_start=wait_start)

        if not success:
            break  
        
        if wait_start_idx > final_idx:
            wait_start_idx = final_idx
        
        pbar.update(wait_start+1) 
        # Update the next timestep to evaluate
        ts = wait_start_idx+1
    pbar.close()

    # Add wait_port time to shutdown for port inspections
    if getattr(operation, 'op_tow_port', None):
        for col_shut in ['dur_shutdown_wtg', 'dur_shutdown_wec', 'dur_shutdown_pv']:
            if (df_op_values[col_shut] > 0).any():
                df_op_values[col_shut] = df_op_values[col_shut] + df_op_values['wait_port']

    df_op_values['dur_total'] = df_op_values.iloc[:, 2:7].sum(axis=1, skipna=False)
    df_op_values['dur_total'] = df_op_values['dur_total'].round(1)

    if out_dir is not None:
        save_file_csv(df_to_save = df_op_values, save_dir = out_dir)
        logging.info('Schedule: saved as "%s".' % out_dir)

    return df_op_values



if __name__ == '__main__':
    pass