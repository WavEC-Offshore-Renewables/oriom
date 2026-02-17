import pandas as pd
from itertools import repeat
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta
import logging
import numpy as np

DICT_DAYS = {1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}

def failures_event(
        s: int,
        scenarios: list,
        failures: list,
        N_LIFETIME: int,
        START_YEAR: int,
        START_MONTH: int,
        infant_mortality: int,
        wear_out: int,
        fail_ratio: float,
        fixed_seed: bool,
        dates_failures_OLD:  pd.DataFrame = None
) -> pd.DataFrame:
    """Create a table with failures throughtout the months for the lifetime.

    Note:
        The failure generation considers:
            - if the FR*N_device*years > 1: a fixed total value of events for each type of failures 
            - if the FR*N_device*years < 1: a poisson distribution of total value of events for each type of failures 
        Then takes all failure rates and randomly picks dates of occurrence within the lifetime of the project.
        If a non-uniform scenario is chosen, failures will most likely happen more in months with a higher probability.
        Also there is the option to simulate a bath tub along the project lifetime. Based on the ``fail_ratio`` (ratio between 
        likelihood of failure during the infant mortality (or wear out) and the constant failure rate in the bath tub distribution),
        failure are more concentrated in the initial year (as many as the ``infant_mortality``) and lasts years (as many as ``wear_out``).

    Args:
        s (:obj:`int`): Choose between the 6 (s: [0,5]) available scenarios
        scenarios (:obj:`list`): List obtained from the class, percentages of probability
            for each month
        failures (:obj:`list`): List obtained from the class, failure rate for each component
        N_LIFETIME (:obj:`int`): Lifetime of the project
        START_YEAR (:obj:`int`): Starting year of the project
        START_MONTH (:obj:`int`): starting month of the project
        infant_mortality (:obj:`int`): Number of years at the start of the project with a higher probability of having failures
        wear_out (:obj:`int`): Number of years of the end of the project with a higher probability of having failures
        fail_ratio (:obj:`float`): Probability of failure during infant mortality and wear out with reference with normal life
        fixed_seed (:obj:`bool`): Fixed seed True or False for repeatibility
        dates_failures_OLD (:obj: `pd.DataFrame`): Failure dataframe imported from previous failure file if present
            Defaults to ``pd.DataFrame.empty``.
    Returns:
        :obj:`pd.DataFrame`: a dataframe containing the dates of failure occurrences.

    """
    # NOTE: seed list as the lenght of the failures
    n_months = list(range(1, + 12*N_LIFETIME+1))                # 20 year-> 240 months
    n_project_years = [str(c) for c in range(1,N_LIFETIME+1)]   # year=1...20
    n_project_yearsxmonths = [
            r for i in n_project_years
            for r in repeat(i,12)
    ]
    n_year = [c for c in range(START_YEAR, START_YEAR+N_LIFETIME+2)]        # Real starting year
    n_yearsxmonths = [
            r for i in n_year
            for r in repeat(i,12)
    ]
    n_yearsxmonths = n_yearsxmonths[
            START_MONTH-1 : len(n_months)-1+START_MONTH
    ]
    year = list(range(1,13))*N_LIFETIME
    year = [str(c) for c in year[:]]
    year = year[START_MONTH-1 :] + year[: START_MONTH-1]

    # Import percentages based on the chosen scenario
    scenario__prob = scenarios[s].percentage_month * N_LIFETIME
    scenario__probability = scenario__prob[START_MONTH-1 :]
    scenario__probability += scenario__prob[: START_MONTH-1]

    columns = ['N_months','Year','Project_year','Months',"Percentages"]
    dict_failures = {failure.id: {
            'fail_rate': (
                round(failure.fail_rate * N_LIFETIME * failure.n_element)
                if failure.fail_rate * N_LIFETIME * failure.n_element >= 1
                else np.random.poisson(failure.fail_rate * N_LIFETIME * failure.n_element)
            ),
            'bath_tub': failure.bath_tub
        }
        for failure in failures
        }
    
    failures_id = list(dict_failures.keys())
    columns= columns + failures_id
    df_failures_per_scenario= pd.DataFrame(columns=columns)
    df_failures_per_scenario['N_months'] = n_months
    df_failures_per_scenario['Year'] = n_yearsxmonths
    df_failures_per_scenario['Project_year']= n_project_yearsxmonths
    df_failures_per_scenario['Months'] = year
    df_failures_per_scenario['Percentages'] = scenario__probability
    df_failures_per_scenario.set_index('N_months', inplace=True)
    df_failures_per_scenario = df_failures_per_scenario.fillna(0)

    # If bath-tub considered
    df_failures_per_scenario_bath_tub = df_failures_per_scenario.copy()
    base_probability = 1/(N_LIFETIME)
    infant_mortality_probability = base_probability * fail_ratio
    wear_out_probability = base_probability * fail_ratio
    base_probability = (1-infant_mortality_probability*infant_mortality-wear_out_probability*wear_out)/(N_LIFETIME-wear_out-infant_mortality)

    if infant_mortality != 0 and wear_out == 0:
        infant_months = list(range(1,infant_mortality * 12 + 1))
        df_failures_per_scenario_bath_tub.loc[infant_months,'Percentages'] += infant_mortality_probability
        df_failures_per_scenario_bath_tub.loc[infant_months[-1] + 1:,'Percentages'] += base_probability

    elif infant_mortality == 0 and wear_out != 0:
        wear_out_m = list(range(0, wear_out *12))
        wear_out_months = []
        for i in wear_out_m:
             wear_out_months.append(n_months[-1] - i)
        df_failures_per_scenario_bath_tub.loc[wear_out_months,'Percentages'] += wear_out_probability
        df_failures_per_scenario_bath_tub.loc[:wear_out_months[-1] - 1,'Percentages'] += base_probability

    elif infant_mortality != 0 and wear_out !=0:
        infant_months = list(range(1,infant_mortality * 12 + 1))
        df_failures_per_scenario_bath_tub.loc[infant_months,'Percentages'] += infant_mortality_probability
        wear_out_m = list(range(0, wear_out *12))
        wear_out_months = []
        for i in wear_out_m:
             wear_out_months.append(n_months[-1] - i)
        df_failures_per_scenario_bath_tub.loc[wear_out_months,'Percentages'] += wear_out_probability
        df_failures_per_scenario_bath_tub.loc[infant_months[-1] +1 : wear_out_months[-1] - 1 ,'Percentages'] += base_probability


    i=0
    for id_ in failures_id:
        f = dict_failures[id_]['fail_rate']

        i+=1
        for n in range(f):
            if dict_failures[id_]['bath_tub'] is True:
                if fixed_seed is True:
                    random.seed(n)
                weights = df_failures_per_scenario_bath_tub['Percentages'].clip(lower=0)
                idx = random.choices(
                    df_failures_per_scenario_bath_tub.index,
                    weights = weights
                )
            else:
                if fixed_seed is True:
                    random.seed(n)
                weights = df_failures_per_scenario['Percentages'].clip(lower=0)
                idx = random.choices(
                    df_failures_per_scenario.index,
                    weights = weights
                )
            df_failures_per_scenario.loc[idx, id_] += 1

    # Create a dictionary with the characteristic of each failrue
    dict_failures_variables = {
            failure.id : [
                    failure.maintenance_strategy,
                    failure.operation_triggered,
                    failure.preferred_month
            ]
            for failure in failures
    }

    # Define the dates in which the failures occur

    date_start = datetime(START_YEAR, START_MONTH, 1, 0, 0, 0)
    date_end = date_start + relativedelta(years=N_LIFETIME+1)
    time_range = pd.date_range(date_start, date_end, freq='H')

    list_dates = []
    list_ids = []
    list_maintenance_strategy = []
    list_operation_triggered = []
    list_preferred_month = []

    # If a previous failure_file is used
    if dates_failures_OLD is not None and not dates_failures_OLD.empty:
        try:
            dates_failures_OLD['datetime'] = pd.to_datetime(
                dates_failures_OLD['datetime'],
                format="%Y-%m-%d %H:%M:%S"
            )
            dates_failures_OLD = dates_failures_OLD.sort_values(by='datetime')
        except Exception as e_:
            logging.error(f'Errors in using previous file: {e_}')
            raise FileNotFoundError(f'Errors in using previous file: {e_}')

        # --- Controlli logici
        ids_old = dates_failures_OLD['id'].unique()
        missing_failure = [f for f in ids_old if f not in dict_failures_variables]

        if missing_failure:
            msg = (f"Warning: fail_ids '{missing_failure}' from OLD_failure_file "
                f"not found in dict_failures_variables")
            logging.error(msg)
            raise KeyError(msg)

        dates_failures = dates_failures_OLD
            
    else:
        list_dates = []
        list_ids = []
        list_maintenance_strategy = []
        list_operation_triggered = []
        list_preferred_month = []
        l = 0
        for id_ in dict_failures_variables.keys():
            df_new = df_failures_per_scenario
            df_new= df_new.drop(df_new[df_new[id_] == 0].index)

            for _, row in df_new.iterrows():
                l+=1
                if fixed_seed is True:
                    random.seed(l)
                n = row[id_]
                month = row['Months']
                month = int(month)
                year = row['Year']
                year = int(year)
                time_window = time_range[time_range.year == year]
                time_window = time_window[time_window.month == month]

                day = range(1, DICT_DAYS[int(month)]+1)
                time_window = time_window[time_window.day.isin(day)]

                dates = random.choices(time_window, k = n)

                for d in dates:
                    list_dates.append(d)
                    list_ids.append(id_)
                    list_maintenance_strategy.append(dict_failures_variables[id_][0])
                    list_operation_triggered.append(dict_failures_variables[id_][1])
                    list_preferred_month.append(dict_failures_variables[id_][2])
    
        dates_failures = pd.DataFrame(columns=[
                'datetime',
                'id',
                'maintenance_strategy',
                'operation_triggered',
                'preferred_month'
        ])

        dates_failures['datetime'] = list_dates
        dates_failures['id'] = list_ids
        dates_failures['maintenance_strategy'] = list_maintenance_strategy
        dates_failures['operation_triggered'] = list_operation_triggered
        dates_failures['preferred_month'] = list_preferred_month
        dates_failures = dates_failures.sort_values(by ='datetime').reset_index(drop=True)
    

    return dates_failures


if __name__ == '__main__':
    pass