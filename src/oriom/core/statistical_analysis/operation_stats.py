import pandas as pd
import numpy as np
import os
import logging
import math

"""
Based on the operation schedule of each operation it calculates the statistical analysis considering 
the main percentile (50 by default) and the other percentiles (typically 10,90).
"""

def operation_stats(
        df_operation_schedule: pd.DataFrame,
        percentile: int,
        out_dir: str=None
)-> pd.DataFrame:
    """
    Calculate statistical analysis for each operation based on the input file containing various durations and wait times. 
    The analysis is done based on the specified percentile and month.

    A statistical analysis is done for every operation based on the input file containing:
        - datetime
        - duration total
        - duration net_port if any
        - duration net site or duration net port_group/solo
        - wait start
        - wait port or wait port_group/solo
        - wait site if any
        - transit to site or transit to site_group/solo
        - transit to port or transit to port_group/solo
        - duration shutdown wtg
        - duration shutdown wec
        - duration shutdown pv

    Args:
        df_operation_schedule (:obj:`str`): File the TimeSeries for a given operation.
        percentile (:obj:`int`): Percentile choosen for the statistical analysis
            It comes from general inputs
        out_dir (:obj:`str`, *optional*): Folder directory to save the
            operation schedule. Defaults to ``None``.  
    Returns:
        :obj:`pd.DataFrame`: DataFrame with statistical analysis results for each operation.
    """

    # Check input file
    columns_mandatory = [
            'datetime',
            'dur_total',
            'wait_start',
            'dur_shutdown_wtg',
            'dur_shutdown_wec',
            'dur_shutdown_pv'
    ]
    
    missing_columns = [col for col in columns_mandatory if col not in df_operation_schedule.columns]

    if missing_columns:
        _e = f'Mandatory columns missing: {missing_columns}'
        logging.error(_e)
        raise NameError(_e)
    

    if all([
        'dur_net_site' not in df_operation_schedule,
        all(['dur_net_site_group' not in df_operation_schedule,
            'dur_net_site_solo' not in df_operation_schedule]) is True
    ]) is True:
        _e = 'Duration net site missing'
        logging.error(_e)
        raise NameError
    if all([
        'wait_port' not in df_operation_schedule,
        all(['wait_port_group' not in df_operation_schedule,
            'wait_port_solo' not in df_operation_schedule]) is True
    ]) is True:
        _e = 'Wait port missing'
        logging.error(_e)
        raise NameError
    if all([
        'transit_to_site' not in df_operation_schedule,
        all(['transit_to_site_group' not in df_operation_schedule,
            'transit_to_site_solo' not in df_operation_schedule]) is True
    ]) is True:
        _e = 'Transit to site missing'
        logging.error(_e)
        raise NameError
    if all([
        'transit_to_port' not in df_operation_schedule.columns,
        all(['transit_to_port_group' not in df_operation_schedule,
            'transit_to_port_solo' not in df_operation_schedule]) is True
    ]) is True:
        _e = 'Transit to port missing'
        logging.error(_e)
        raise NameError
    # Calculate the percentiles for each term
    month = list(range(1,13))

    columns = ['operation_id', 'percentile'] + month
    percentiles = pd.DataFrame(columns=columns)
    
    for m in month:
        list_duration = []
        df_op = pd.DataFrame()
        df_op = df_operation_schedule[df_operation_schedule['datetime'].dt.month == m]
        dur_total_p = np.nanpercentile(df_op['dur_total'], percentile, interpolation='nearest')
        if 'dur_net_site_group' in df_operation_schedule:
            list_names_duration = [
                'dur_total_p' ,
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
            if math.isnan(dur_total_p) is True:
                list_duration = [0] * 13
            else:
                duration_row = df_op[df_op['dur_total'] == dur_total_p]
                list_duration.append(dur_total_p)
                list_duration.append(duration_row['dur_net_site_group'].mean())
                list_duration.append(duration_row['dur_net_site_solo'].mean())
                list_duration.append(duration_row['transit_to_site_group'].mean())
                list_duration.append(duration_row['transit_to_site_solo'].mean())
                list_duration.append(duration_row['transit_to_port_group'].mean())
                list_duration.append(duration_row['transit_to_port_solo'].mean())
                list_duration.append(duration_row['wait_port_group'].mean())
                list_duration.append(duration_row['wait_port_solo'].mean())
                list_duration.append(duration_row['wait_start'].mean())
                list_duration.append(duration_row['dur_shutdown_wtg'].mean())
                list_duration.append(duration_row['dur_shutdown_wec'].mean())
                list_duration.append(duration_row['dur_shutdown_pv'].mean())
        elif 'dur_net_port' in df_operation_schedule:
            list_names_duration = [
                    'dur_total_p' ,
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
            if math.isnan(dur_total_p) is True:
                list_duration = [0] * 11
            else:
                duration_row = df_op[df_op['dur_total'] == dur_total_p]
                list_duration.append(dur_total_p)
                list_duration.append(duration_row['dur_net_port'].mean())
                list_duration.append(duration_row['dur_net_site'].mean())
                list_duration.append(duration_row['wait_start'].mean())
                list_duration.append(duration_row['wait_port'].mean())
                list_duration.append(duration_row['wait_site'].mean())
                list_duration.append(duration_row['transit_to_site'].mean())
                list_duration.append(duration_row['transit_to_port'].mean())
                list_duration.append(duration_row['dur_shutdown_wtg'].mean())
                list_duration.append(duration_row['dur_shutdown_wec'].mean())
                list_duration.append(duration_row['dur_shutdown_pv'].mean())
        else:
            list_names_duration = [
                    'dur_total_p' ,
                    'dur_net_site',
                    'wait_start',
                    'wait_port',
                    'transit_to_site',
                    'transit_to_port',
                    'dur_shutdown_wtg',
                    'dur_shutdown_wec',
                    'dur_shutdown_pv'
            ]
            if math.isnan(dur_total_p) is True:
                list_duration = [0] * 9
            else:
                duration_row = df_op[df_op['dur_total'] == dur_total_p]
                list_duration.append(dur_total_p)
                list_duration.append(duration_row['dur_net_site'].mean())
                list_duration.append(duration_row['wait_start'].mean())
                list_duration.append(duration_row['wait_port'].mean())
                list_duration.append(duration_row['transit_to_site'].mean())
                list_duration.append(duration_row['transit_to_port'].mean())
                list_duration.append(duration_row['dur_shutdown_wtg'].mean())
                list_duration.append(duration_row['dur_shutdown_wec'].mean())
                list_duration.append(duration_row['dur_shutdown_pv'].mean())
        
        percentiles['percentile'] = list_names_duration
        percentiles[m] = list_duration


    # Save statistics as a CSV
    if out_dir is not None:
        percentiles.to_csv(
                path_or_buf=out_dir,
                sep=','
        )
        logging.info('Statistics: saved as "%s".' % out_dir)

    return percentiles


if __name__ == '__main__':

    file_op = os.path.join(
            os.getcwd(),
            'tests',
            'test_files',
            'inputs',
            'operation_schedule.csv'
    )

    stats = operation_stats(file_op, 50, None)
