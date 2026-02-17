class Results:
    """ Class container to contain all the results from the simulations"""

    def __init__(self):
        self.dfs_tot_cost_list = []
        self.dfs_tot_yearly_cost_list = []
        self.dfs_ctv_list = []
        self.dfs_log_events = []
        self.dfs_log_events_merged = []
        self.kpi_om_type_cost_list = []

        self.dfs_energy_yearly_dict = {
            "Availability_year_wind": [],
            "Availability_year_wave": [],
            "Availability_year_pv": []
        }

        self.dfs_energy_yearly_month_dict = {
            "Availability_month_wind": [],
            "Availability_month_wave": [],
            "Availability_month_pv": []
        }