import pandas as pd
import copy

from logistic_tools.core.functions.vessels_manager.VesselDayCount import VesselDayCounter


def data_ctv_long_term_strategy(
        v: object, 
        log_events_merged: pd.DataFrame,
        n_lifetime: int
    ):
    
    """
    This function return a dictionary where show the total costs (short term + long term) of the ctv vessel in case
    different number of long term vessel are charted. 

    Args:
        v (object): object of class `~logistic_tools.classes.Vessel.Vessel`
        log_events_merged (:obj:`pd.DataFrame`): Dataframe of log_events_merged
        n_lifetime (:obj:`int`): Lifetime of the project in years.

    Returns:
        dict
    """

    ctv_strategy_cost = {}
    n_long_term = v.n_ves_annual_contract
    len_simulation = range(0,n_long_term+4)
    if len(len_simulation) > 8:
        len_simulation = range(n_long_term-5,n_long_term+4)

    log_events_merged_reset = log_events_merged.copy()

    # reset values as original
    log_events_merged_reset['ST_contract_1'] = False
    log_events_merged_reset['ST_contract_2'] = False
    log_events_merged_reset['d_end_stat_chart'] = log_events_merged_reset['d_end_stat_chart_orig']
    log_events_merged_reset['n_vessel_1_effective'] = log_events_merged_reset['n_vessel_1']
    

    for n_long_term_try in len_simulation:
        ctv_strategy_cost[n_long_term_try] = {}
        # Copy and reset the ST_contract
        log_events_m = log_events_merged_reset.copy()

        # Evaluate ST vessel with new contract stipulated
        # copy vessel and modify n_contract
        ves = copy.deepcopy(v)
        ves.n_ves_annual_contract = n_long_term_try

        # Create a new log_events_merged with different ST
        vessel_day_count_sensitivity = VesselDayCounter(log_events_merged = log_events_m, vessels=[ves])
        log_m = vessel_day_count_sensitivity.allocate_vessels(log_events_merged = log_events_m, ST = True)

        # Filter only for ST
        log_m = log_m[log_m["ST_contract_1"] | log_m["ST_contract_2"]].copy()

        # Recreate the vessel calendar only with ST contracts
        vessel_day_count_sensitivity_ST = VesselDayCounter(log_events_merged = log_m, vessels=[ves])
        _ = vessel_day_count_sensitivity_ST.allocate_vessels(log_events_merged = log_events_merged, contract_evaluation = False)
        vessel_day_count_count = vessel_day_count_sensitivity_ST

        # Filter daily_vessel for the relevant vessel
        short_term_days_chart = vessel_day_count_count.count_day_vessel(ves.id)
            
        ST_ctv_cost = short_term_days_chart * ves.charter
        LT_monthly_charter_cost = getattr(ves, 'monthly_contract_cost', 0)*getattr(ves, 'n_ves_monthly_contract', 0)*len(getattr(ves, 'months_contract', []))
        LT_ctv_cost = n_lifetime * (ves.annual_contract * n_long_term_try + LT_monthly_charter_cost)

        ctv_strategy_cost[n_long_term_try]['short_term_cost'] = ST_ctv_cost
        ctv_strategy_cost[n_long_term_try]['long_term_cost'] = LT_ctv_cost
        ctv_strategy_cost[n_long_term_try]['tot_cost'] = ST_ctv_cost + LT_ctv_cost

    return ctv_strategy_cost



if __name__ == '__main__':
    pass
    