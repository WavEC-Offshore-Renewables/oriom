"""Main script to run ``oriom`` package."""
# import libraries
import os
import logging
import warnings
from copy import deepcopy
import time
from datetime import datetime
import sys

# Import oriom package
from oriom.inputs.Configuration import ConfigRun, ProjectDirs
from oriom.inputs.Input_manager import Input_Files, extract_input_from_excel, handle_overwrite_previous

from oriom.utils import aux_functions
from oriom.utils import aux_operation

from oriom.domain.Inputs.Inputs import Inputs
from oriom.domain.Metocean import Metocean
from oriom.domain.OperationsStat.CorrectiveStat import CorrectiveStat
from oriom.domain.OperationsStat.InspectionPortStat import InspectionPortStat
from oriom.domain.OperationsStat.InspectionSiteStat import InspectionSiteStat
from oriom.domain.OperationsStat.OperationTowStat import OperationsTowStat
from oriom.domain.Failure import Failure
from oriom.domain.Results import Results
from oriom.domain.Techs.Power import PVPower as PVPower
from oriom.domain.FindElementClass import Find_Element
from oriom.domain.Techs.Technologies import TechnologyBuilder
from oriom.domain.Layouts.Layouts_Managers import LayoutManager
from oriom.core.timeseries_analysis.montecarlo import f_montecarlo
from oriom.core.builders.operation_builder import aux_operation_builder, aux_operation_stats_builder, operation_timeseries_builder
from oriom.core.statistical_analysis.statisticals_duration_manager import statistical_duration_manager
from oriom.core.statistical_analysis.power_stats import average_pwind, average_pwave
from oriom.core.statistical_analysis.final_run_statistics import return_statistics_runs
from oriom.core.results_block_manager import results_block
from oriom import test

ST_main = True

print()
test.test()
time.sleep(1)
print()


try:
    from oriom.core.functions.private import check_files
except ImportError:
    check_files = None
    e_ = 'The user is not authorized to use private function. "Check_files", '
    e_ += '"KPI_Insight" and "VesselMobilisationScheduler" module are not available'
    logging.warning(e_)

warnings.simplefilter('ignore')
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

### ---------- INPUTS ---------- ###
### Parameters hard coded to define ###
DEFAULT_CONFIG = ConfigRun(
    STATISTICAL_CHART=True,
    DIFF_DISTANCE=False,
    DIFF_KM_DISTANCE=5,
    KM_MOTHER_VESSEL=5,
    VESSEL_DIST_REDUCED_LIST=["ctv","sv"],
    FUEL_TO_ADD = {},
    MOBILISATION_TO_ADD={},
    ENERGY_AVAILABILITY_CALCULATION=True,
    ENERGY_STATISTICAL_CALCULATION=False,
    PROJECT_NAME="test_oriom",
    BASEFILES_FROM_EXCEL=False,
    EXCEL_FILE_PATH=r"C:\Users\RiccardoMeda\Project\oriom\tests\test_files\test_end_to_end",
    SOURCE_PATH_SHAREPOINT="",
    FORM_NAME="form_test.xlsx",
    TIME_FAIL_OP_IMMEDIATELY=0.02,
)


### ------------------------------------------------------------------ ###
### ------------------------------ CODE ------------------------------ ###
### ------------------------------------------------------------------ ###

def run(config: ConfigRun | None = None):
    """Run a full simulation and return the created ProjectDirs."""

    Config = config or DEFAULT_CONFIG

    time_prefix = datetime.now().strftime("_[%Y%m%d_%H%M%S]")

    # Temporary directory
    dirs = ProjectDirs.create(project_name = Config.PROJECT_NAME, time_prefix = time_prefix)

    ### ---------- CONVERT EXCEL FORM TO YAML BASE FILES ---------- ###
    extract_input_from_excel(
        dirs = dirs,
        base_file_excel = Config.BASEFILES_FROM_EXCEL,
        sharepoint_file_path = Config.SOURCE_PATH_SHAREPOINT,
        excel_file_path = Config.EXCEL_FILE_PATH,
        form_name = Config.FORM_NAME
    )

    # Define General inputs
    inputs_gen_file = os.path.join(dirs.base_dir, 'inputs_gen.yaml')
    inputs_gen = Inputs.General(
        file_inputs=inputs_gen_file,
        out_dir=dirs.run_dir
    )

    handle_overwrite_previous(inputs_gen, dirs)

    # Configure logging
    for handler in logging.root.handlers[:]:
                    logging.root.removeHandler(handler)
    logging.basicConfig(
            filename=os.path.join(dirs.run_dir, 'logging.log'),
            encoding='utf-8',
            format='%(asctime)s %(levelname)-8s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            level=logging.INFO
    )

    # Log configuration parameters
    Config.log_parameters(
        logger=logging,
        inputs_gen=inputs_gen
    )

    if Config.BASEFILES_FROM_EXCEL is False and Config.EXCEL_FILE_PATH is None:
        logging.warning('This run is using the test files')

    logging.info('This run is ran times: ' + str(inputs_gen.number_runs["value"]))

    ### ---------- INPUTS ---------- ###
    files = Input_Files(dirs.base_dir)

    logging.info('--------------------\tINPUTS\t--------------------')
    inputs = Inputs(
        general = inputs_gen,
        stats = Inputs.Statistical(file_inputs = files.inputs_stats_file, out_dir = dirs.run_dir),
        cost = Inputs.Cost(file_inputs = files.inputs_costs_file, out_dir = dirs.run_dir),
        tseries = Inputs.TimeSeries.from_run_dir(
            run_dir = dirs.run_dir,
            file_inputs = files.inputs_tseries_file,
            scenarios_file = files.scenarios_file
        ),
    )

    logging.info('--------------------\tINPUTS - TECHNOLOGIES - POWER PRODUCTION\t--------------------')
    farm_technologies = TechnologyBuilder.build_technologies(
        run_dir=dirs.run_dir,
        wtg_file=files.wtg_file,
        wec_file=files.wec_file,
        pv_file=files.pv_file,
        file_electrical_loss = inputs.tseries.file_wake_loss['value'],
        file_wake_loss = inputs.tseries.file_wake_loss['value']
    )

    logging.info('--------------------\tLAYOUT\t--------------------')
    G_layouts = LayoutManager.build_layouts(
        power_farm=farm_technologies.power,
        wtg=farm_technologies.wtg,
        wec=farm_technologies.wec,
        pv=farm_technologies.pv,
        graph_dir=dirs.graph_dir,
    )

    logging.info('--------------------\tFARM\t--------------------')
    #TODO oriom OOP
    """     
    farm = Farm(
        inputs = inputs,
        farm_tech = farm_technologies,
        layouts = G_layouts
    )

    port = Port(
        id_= 'port_id',
        name = 'My_Port',
        location = {'lat': inputs.tseries.site_lat["value"], 'lon': inputs.tseries.site_lon["value"]}
    )

    storage = Storage(
        id_ = 'storage_id',
        max_space = 5
    )
    
    """

    logging.info('--------------------\tINPUTS - METOCEAN\t--------------------')
    # Build or reuse Metocean in one call
    metocean, _ = Metocean.from_run_dir(
        run_dir=dirs.run_dir,
        tseries_inputs=inputs.tseries,
        power_farm=farm_technologies.power,
        wtg=farm_technologies.wtg,
        z0=inputs.tseries.surface_roughness["value"],
        stat_inputs=inputs.stats,
    )
    
    metocean_port, _ = Metocean.from_run_dir(
        run_dir=dirs.run_dir,
        tseries_inputs=inputs.tseries,
        stat_inputs=inputs.stats,
        port_metocean = True,
        site_metocean = metocean
    )

    # Build Metocean tow in one call
    metocean_tow, metocean_tow_distance = Metocean.from_run_dir(
        run_dir=dirs.run_dir,
        tseries_inputs=inputs.tseries,
        stat_inputs=inputs.stats,
        tow_metocean = True
    )

    # Attach power columns and get power-only view
    metocean = Metocean.attach_power_columns(metocean = metocean, power_farm = farm_technologies.power, out_dir=dirs.run_dir)


    logging.info('--------------------\FAILURES\t--------------------')
    # Define failure events
    failures = Failure.get_failures_from_yaml(
            file_path = files.failures_file
    )
    # Variate failure rate for sensitivity analysis
    for failure in failures:
        if getattr(failure, "fail_variation", False):
            failure.fail_rate *= inputs.stats.failure_ratio_sensitivity["value"]
            logging.info(f'Failure {failure.id_} FR have been multiplied by {inputs.stats.failure_ratio_sensitivity["value"]}')

    # Check if all the levels defined are associated to a component in the graph
    aux_operation.level_component_check(Gs = G_layouts, operations = failures, failure = True)

    logging.info('--------------------\tINPUTS - OPERATIONS\t--------------------')
    operations = aux_operation_builder(
        Config = Config,
        inputs = inputs,
        files = files,
        dirs = dirs,
        failures = failures,
        farm_technologies = farm_technologies,
        G_layouts = G_layouts
    )

    # Create list of vessels and mother_vessels
    vessels = list(operations['vessels'].values())
    mother_vessels = [v for v in vessels if v.mother_vessel]


    logging.info('--------------------\tDERIVED INPUTS\t--------------------')
    # Statistical analysis of the power fro wtg and wec
    dict_power_wind = average_pwind(
            timeseries_with_power=deepcopy(metocean.df_timeseries),
            out_dir=os.path.join(os.getcwd(), dirs.run_dir)
    )

    dict_power_wave = average_pwave(
            timeseries_with_power=deepcopy(metocean.df_timeseries),
            out_dir=os.path.join(os.getcwd(), dirs.run_dir)
    )



    # Generate random timesteps to be analysed
    timesteps, _ = f_montecarlo(
            data_panda=metocean.df_timeseries,
            ts_percent_dec=inputs.tseries.montecarlo_percent["value"]
    )


    ### --- OPERATION ANALYSES PER TIMESTEP --- ###
    logging.info('---------------------------------------------------------------')
    logging.info('--------------------\tTIMESERIES ANALYSIS\t--------------------')
    logging.info('---------------------------------------------------------------')

    operation_timeseries_builder(
        inputs = inputs,
        dirs = dirs,
        operations = operations,
        metocean = metocean,
        metocean_port = metocean_port,
        metocean_tow = metocean_tow,
        metocean_tow_distance = metocean_tow_distance,
        timesteps = timesteps,
        Config = Config,
    )


    ### --- OPERATION STATISTICAL ANALYSES --- ###
    logging.info('---------------------------------------------------------------')
    logging.info('--------------------\tSTATISTICAL ANALYSIS\t----------------')
    logging.info('---------------------------------------------------------------')
    operations_stats, find_element = aux_operation_stats_builder(
        inputs = inputs,
        dirs = dirs,
        farm_technologies = farm_technologies,
        operations = operations,
        vessels = vessels,
        failures = failures
    )


    logging.info('---------------------------------------------------------------')
    logging.info('--------------------\tRESULT BLOCK\t----------------')
    logging.info('---------------------------------------------------------------')

    results_container = Results()
    for r in range(inputs.general.number_runs["value"]):
        logging.info('Simulating run number: %d \n This process might take a while', r)
        result_dir_r = os.path.join(dirs.result_dir,f"{'result_'}{r}")
        logging.info('Creating folder results: ' + f"{'result_'}{r}")
        os.makedirs(result_dir_r)

        start = time.time()

        results_block(
            result_dir_r = result_dir_r,
            r = r,
            inputs = inputs,
            Config = Config,
            find_element = find_element,
            farm_technologies = farm_technologies,
            results_dict = results_container,
            failures = failures,
            operations_tow_stats = operations_stats['operations_tow_stats'],
            inspections_port_stats = operations_stats['inspections_port_stats'],
            inspections_site_stats = operations_stats['inspections_site_stats'],
            operations_corrective_stats = operations_stats['operations_corrective_stats'],
            vessels = vessels,
            mother_vessels = mother_vessels,
            G_layouts = G_layouts,
            dict_power_wind = dict_power_wind,
            dict_power_wave = dict_power_wave,
            metocean_timeseries = metocean.df_timeseries
        )

        end = time.time()
        logging.info(f"\n\n Time of one simulation): {end - start:.0f} sec")


    logging.info('----------------------------------------------------')
    logging.info('----------------------------------------------------')
    logging.info('--------------------\tAveraging Results\t----------------')

    if not os.path.exists(dirs.result_dir_avg):
        os.makedirs(dirs.result_dir_avg)

    return_statistics_runs(
        n_lifetime = inputs.stats.lifetime["value"],
        find_element_class = find_element,
        results_dict = results_container,
        fuel_add = Config.FUEL_TO_ADD,
        mobilisation_add = Config.MOBILISATION_TO_ADD,
        electricity_cost_dict = inputs.cost.electricity_price_dict,
        n_runs = inputs.general.number_runs["value"],
        vessels = vessels,
        operations_total = operations['total_operations'],
        save_dir = dirs.result_dir_avg
    )

    logging.info('--------------------\tEND OF THE SIMULATION\t--------------------')

    if ST_main:
        from oriom.export.st_package import export_st_package
        export_st_package(
            package_dir=r"C:\Users\RiccardoMeda\temp",
            Config=Config,
            operations_stats = operations_stats,
            overwrite = True
        )

    return dirs

if __name__ == "__main__":
    run()