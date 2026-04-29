import pandas as pd
from datetime import timedelta

from oriom.core.functions.logs_timeseries import logs_timeseries_func
from oriom.core.functions.logs_timeseries import define_dates_inspection


def create_logs_preventive(
    COLS: list,
    inputs: object,
    inspections_port_stat: list,
    inspections_site_stat: list,
    find_element_class: object,
    percentile: float,
    mother_vessels_list: list,
)->pd.DataFrame:

    """
    Manage the creation of the log of preventive inspections

    Args:
        COLS (list): List of columns of the log dataframe
        inputs (object): Object from class `Inputs` that contains all the inputs of the simulation
        inspections_port_stat (list): List of object :class:`Inspection
        inspections_site_stat (list): List of object :class:`Inspection
        find_element_class (object): Object from class :class:`FindElementClass`
        percentile (float): Percentile of the weather window to consider for the operations
        mother_vessels_list (list): List of object :class:`Vessel` that are mother vessels
    Returns:
        log_preventive (pd.DataFrame): Dataframe with the log of all the preventive
    """

    # extract inputs
    start_year = inputs.stats.start_year["value"]
    start_month = inputs.stats.start_month["value"]
    n_lifetime = inputs.stats.lifetime["value"]
    log_preventive = pd.DataFrame(columns=COLS)

    # dict for mother_vessel_campaign
    mother_vessel_inspection_campaign = {}
    for ves in mother_vessels_list:
        mother_vessel_inspection_campaign[ves.id] = {k:{} for k in range(start_year, start_year + n_lifetime)}

    # Create logs preventive inspections at site
    for insp in inspections_site_stat:
        df_row_dates = define_dates_inspection.define_dates(
            COLS = COLS,
            inspection = insp,
            event = 'inspection_site',
            start_year = start_year,
            start_month = start_month,
            n_lifetime = n_lifetime,
            percentile = percentile,
            find_element_class = find_element_class,
            mother_vessel_inspection_campaign = mother_vessel_inspection_campaign
        )

        if not df_row_dates.empty:
            log_preventive = pd.concat([df_row_dates,log_preventive], axis=0, ignore_index=True)
            # Create mobilisation
            if insp.vessel1.mobilisation_time !=0:
                rows_to_add = []
                for _, row in df_row_dates.iterrows():
                    row_mob_prev = logs_timeseries_func.create_mobilisation(
                        df = log_preventive,
                        mobilisation_date = row['d_trigger'],
                        end_mobi = row['d_trigger'] + timedelta(days = 1),
                        event = 'mobilisation',
                        vessel = insp.vessel1,
                        oper_list = [insp.insp_class.id],
                        count_fail = insp.id,
                        concat = False,
                        n_vessel=insp.insp_class.vessel1_qt
                    )
                    rows_to_add.append(row_mob_prev)

                log_preventive = pd.concat([log_preventive] + rows_to_add, axis=0, ignore_index=True)

    # Create logs preventive inspections at port
    for insp in inspections_port_stat:
        df_row_dates = define_dates_inspection.define_dates(
            COLS = COLS,
            inspection = insp,
            event = 'inspection_port',
            start_year = start_year,
            start_month = start_month,
            n_lifetime = n_lifetime,
            percentile = percentile,
            find_element_class = find_element_class,
            mother_vessel_inspection_campaign = mother_vessel_inspection_campaign
        )
        if not df_row_dates.empty:

            df_row_dates['vessel_1'] = insp.insp_class.vessel1.id
            log_preventive = pd.concat([log_preventive,df_row_dates])

            # Create mobilisation
            if insp.insp_class.vessel1.mobilisation_time !=0:
                rows_to_add = []
                for _, row in df_row_dates.iterrows():
                    row_mob_prev = logs_timeseries_func.create_mobilisation(
                        df = log_preventive,
                        mobilisation_date = row['d_trigger'],
                        end_mobi = row['d_trigger'] + timedelta(days=1),
                        event = 'mobilisation',
                        vessel = insp.vessel1,
                        oper_list = [insp.insp_class.id],
                        count_fail = insp.id,
                        concat = False,
                        n_vessel=row['n_vessel_1']
                    )
                    rows_to_add.append(row_mob_prev)

                log_preventive = pd.concat([log_preventive] + rows_to_add, axis=0, ignore_index=True)

    return log_preventive


if __name__ == '__main__':
    pass