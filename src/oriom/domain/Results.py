class Results:
    """ Class container to contain all the results from the simulations"""

    def __init__(self):
        self.dfs_failures = {}
        self.operation_vessel_percentiles_dict = {}
        self.dfs_energy_yearly_dict, self.dfs_energy_yearly_month_dict = {}, {}
        self.dfs_energy_data = []
        self.dfs_tot_cost_list = []
        self.dfs_tot_yearly_cost_list = []
        self.dfs_ctv_list = []
        self.dfs_log_events = []
        self.dfs_log_events_merged = []
        self.kpi_om_type_cost_list = []
        self.dfs_vessel_fuel_usage = []

        for tech in ["wind", "wave", "pv"]:
            self.dfs_energy_yearly_dict[f"Availability_year_{tech}"] = []
            self.dfs_energy_yearly_month_dict[f"Availability_month_{tech}"] = []
