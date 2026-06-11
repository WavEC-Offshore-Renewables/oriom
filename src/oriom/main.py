"""Main script to run ``oriom`` package."""
# import libraries
import os
import logging
import warnings
from copy import deepcopy
import time
from datetime import datetime

# Import oriom package
from oriom.inputs.Configuration import ConfigRun, ProjectDirs
from oriom.inputs.Input_manager import Input_Files, extract_input_from_excel, handle_overwrite_previous

from oriom.utils import aux_functions
from oriom.utils import aux_operation

from oriom.classes.Inputs import Inputs
from oriom.classes.Metocean import Metocean
from oriom.classes.RovDrone import RovDrone
from oriom.classes.Operations.InspectionSite import InspectionSite
from oriom.classes.Operations.InspectionPort import InspectionPort
from oriom.classes.Operations.CorrectiveMajor import CorrectiveMajor
from oriom.classes.Operations.CorrectiveMinor import CorrectiveMinor
from oriom.classes.Operations.OperationTow import OperationTow
from oriom.classes.OperationsStat.CorrectiveStat import CorrectiveStat
from oriom.classes.OperationsStat.InspectionPortStat import InspectionPortStat
from oriom.classes.OperationsStat.InspectionSiteStat import InspectionSiteStat
from oriom.classes.OperationsStat.OperationTowStat import OperationsTowStat
from oriom.classes.DefineOperationTechs import Define_operation
from oriom.classes.Failure import Failure
from oriom.classes.Results import Results
from oriom.classes.Scenario import Scenario
from oriom.classes.Power import PVPower as PVPower
from oriom.classes.FindElementClass import Find_Element
from oriom.classes.Technologies import TechnologyBuilder

from oriom.classes.Layouts.Layouts_Managers import LayoutManager
from oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager import inspect_site_manager
from oriom.core.timeseries_analysis.operation_managers.operations_tow_manager import operation_tow_manager
from oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager import operation_inspect_port_manager
from oriom.core.timeseries_analysis.operation_managers.operations_major_manager import operation_major_manager
from oriom.core.timeseries_analysis.operation_managers.operations_minor_manager import opeartion_minor_manager
from oriom.core.timeseries_analysis.montecarlo import f_montecarlo

from oriom.core.statistical_analysis.statisticals_duration_manager import statistical_duration_manager
from oriom.core.statistical_analysis.power_stats import average_pwind
from oriom.core.statistical_analysis.power_stats import average_pwave
from oriom.core.statistical_analysis.final_run_statistics import return_statistics_runs
from oriom.core.results_block_manager import results_block
from oriom import test

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
DEFAULT_CONFIG  = ConfigRun(
    STATISTICAL_CHART=True,
    DIFF_DISTANCE=False,
    DIFF_KM_DISTANCE=5,
    KM_MOTHER_VESSEL=5,
    VESSEL_DIST_REDUCED_LIST=["ctv","sv"],
    FUEL_TO_ADD = {},
    MOBILISATION_TO_ADD={},
    ENERGY_AVAILABILITY_CALCULATION=True,
    ENERGY_STATISTICAL_CALCULATION=False,
    PROJECT_NAME="SeaPotential_MEGAWAVE_deferred",
    BASEFILES_FROM_EXCEL=False,
    EXCEL_FILE_PATH=r"C:\Users\rmeda\WavEC Offshore Renewables\Equipa WavEC - T8.1\CaseStudies\Case study\Sensitivities\SEAPOTENTIAL",
    SOURCE_PATH_SHAREPOINT="",
    FORM_NAME="ORIOM_SeaPotential_MEGAWAVE_deferred.xlsx",
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


    logging.info('--------------------\tINPUTS - TECHNOLOGIES - POWER PRODUCTION\t--------------------')
    farm_technologies = TechnologyBuilder.build_technologies(
        run_dir=dirs.run_dir,
        wtg_file=files.wtg_file,
        wec_file=files.wec_file,
        pv_file=files.pv_file,
    )

    logging.info('--------------------\tINPUTS\t--------------------')
    inputs = Inputs(
        general = inputs_gen,
        stats = Inputs.Statistical(file_inputs = files.inputs_stats_file, out_dir = dirs.run_dir),
        cost = Inputs.Cost(file_inputs = files.inputs_costs_file, out_dir = dirs.run_dir),
        tseries = Inputs.TimeSeries.from_run_dir(run_dir = dirs.run_dir, file_inputs = files.inputs_tseries_file),
    )

    logging.info('--------------------\tINPUTS - METOCEAN\t--------------------')
    # Build or reuse Metocean in one call
    metocean = Metocean.from_run_dir(
        run_dir=dirs.run_dir,
        tseries_inputs=inputs.tseries,
        power_farm=farm_technologies.power,
        wtg=farm_technologies.wtg,
        z0=inputs.tseries.surface_roughness["value"],
        stat_inputs=inputs.stats
    )

    # Build Metocean tow in one call
    metocean_tow = Metocean.from_run_dir(
        run_dir=dirs.run_dir,
        tseries_inputs=inputs.tseries,
        stat_inputs=inputs.stats,
        tow_metocean = True
    )

    # Attach power columns and get power-only view
    metocean = Metocean.attach_power_columns(metocean, farm_technologies.power, out_dir=dirs.run_dir)


    logging.info('--------------------\tLAYOUT\t--------------------')
    G_layouts = LayoutManager.build_layouts(
        power_farm=farm_technologies.power,
        wtg=farm_technologies.wtg,
        wec=farm_technologies.wec,
        pv=farm_technologies.pv,
        graph_dir=dirs.graph_dir,
    )

    logging.info('--------------------\FAILURES\t--------------------')
    # Define failure events
    failures = Failure.get_failures_from_yaml(
            file_path = files.failures_file
    )
    # Variate failure rate for sensitivity analysis
    for failure in failures:
        if getattr(failure, "fail_variation", False):
            failure.fail_rate *= inputs.stats.failure_ratio_sensitivity["value"]

    logging.info('--------------------\tINPUTS - OPERATIONS\t--------------------')
    vessels = {}

    # Define ROVs and Drones
    rovs_drones = RovDrone.get_rovdrones_from_yaml(files.rovs_drones_file)

    # Define Towing Operations
    operations_tow = OperationTow.get_operations_from_yaml(
        file_path = files.operations_tow_file
    )

    # Define Inspection Campaings at site
    operations_inspect_site = InspectionSite.get_inspections_from_yaml(
        file_path = files.operations_insp_site_file
    )

    # Define Inspection Campaings at port
    operations_inspect_port = InspectionPort.get_inspections_from_yaml(
        file_path = files.operations_insp_port_file,
        towing_operations = operations_tow
    )

    # Define Major Corrective Operations
    operations_corr_major = CorrectiveMajor.get_operations_from_yaml(
        file_path = files.operations_corr_major_file,
        towing_operations = operations_tow
    )

    # Define Minor Corrective Operations
    operations_corr_minor = CorrectiveMinor.get_operations_from_yaml(
        file_path = files.operations_corr_minor_file
    )

    total_operations = operations_tow + operations_inspect_site + operations_inspect_port + operations_corr_major + operations_corr_minor

    for operation in (operations_corr_major + operations_corr_minor):
        # Define deferred months of operation if presents
        operation.define_months_operations()
        # Define failure class in Operation attributes
        aux_operation.get_failures(operation, failures)

    # Create and prepare a run folder for each operation
    for operation in total_operations:
        aux_functions.create_run_folder_operation(
            operation = operation,
            operation_dir = dirs.operation_dir,
            inputs_gen = inputs.general,
            operation_files = Config.OPERATION_FILES
        )

        # Populate Operations with vessels
        if getattr(operation, 'vessel1_id', None):
            Define_operation.define_vessels(
                operation = operation,
                file_vessels = files.vessels_file,
                file_fuel_cons = files.vessels_fuel_cons_file,
                file_load_factor = files.vessels_load_factor_file,
                file_fuel_density = files.vessels_fuel_density_file,
                vessels = vessels
            )

        # Populate Operations with ROV
        if getattr(operation, 'rov_drone', None):
            Define_operation.define_rovs(
                operation=operation,
                rovs_drones=rovs_drones,
            )

    # Populate Operations with device at port storage and simultaneus operations
    for operations_list, inspection in zip(
        (operations_inspect_port, operations_corr_major),
        (True, False)
    ):
        for operation in operations_list:
            aux_operation.define_device_at_port(
                oper=operation,
                wtg=farm_technologies.wtg,
                wec=farm_technologies.wec,
                pv=farm_technologies.pv,
                inspection=inspection
            )

    # Populate the inspection level if not defined previously
    for operation in (operations_inspect_port + operations_inspect_site):
        operation.define_level(G_layouts = G_layouts)

    # Check minor operation durations
    for operation in operations_corr_minor:
        if operation.duration_net >= inputs.tseries.shift_duration["value"]:
            raise ValueError("OperMinor: Duration too long, define the operation as a major", operation.id)

    for operation in operations_tow:
        if getattr(operation, "addition_op_tow", None):
            operation.define_previous_op_tow(operations_corr_major)

    # Populate Major Corrective ant Tow Operations Operations with activities
    for operation in (operations_corr_major + operations_tow):
        op_dir = os.path.join(dirs.operation_dir, operation.id)
        # Check if there is already an activities file
        if check_files and check_files.check_file_exists(path=op_dir, file_name='activities.csv'):
            aux_operation.recycle_activities(
                operation = operation,
                dir=op_dir,
                file_name='activities',
                tow_op = operation in operations_tow
            )
        else:
            time_between_devices = inputs.tseries.find_time_between_devices(operation_obj_id = operation.id)

            aux_operation.define_activities(
                operation = operation,
                file_activities = files.operations_activities_file,
                distance_to_site = inputs.tseries.distance["value"],
                transit_between_devices = time_between_devices,
                tow_op = operation in operations_tow
            )
            operation.activities[0].save_activities_as_csv(operation, os.path.join(op_dir, 'activities.csv'))

    # Check if all the levels defined are associated to a component in the graph
    for operation_type in [operations_inspect_port, operations_inspect_site]:
        aux_operation.level_component_check(Gs = G_layouts, operations = operation_type)

    # Create list of vessels and mother_vessels
    vessels = list(vessels.values())
    mother_vessels = [v for v in vessels if v.mother_vessel]

    # Save operation attributes as YAML files
    for operation in total_operations:
        op_dir = os.path.join(dirs.operation_dir, operation.id)
        # Check if there is already an attributes file
        if check_files and check_files.check_file_exists(path=op_dir, file_name='attributes.yaml'):
            continue
        operation.to_yaml(op_dir)

    aux_operation.operation_check_identities(total_operations)

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

    # Check if all the levels defined are associated to a component in the graph
    aux_operation.level_component_check(Gs = G_layouts, operations = failures, failure = True)

    # Define scenario for failure event
    inputs.tseries.scenario = Scenario.get_scenarios_from_yaml(
            file_path = files.scenarios_file
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

    operation_tow_manager(
        operation_dir = dirs.operation_dir,
        df_metocean = metocean.df_timeseries,
        max_wait = inputs.tseries.max_wait["value"],
        operations_tow = operations_tow,
        timesteps = timesteps,
        Config = Config,
        inputs_tseries = inputs.tseries,
        metocean_tow = metocean_tow
    )

    inspect_site_manager(
        operation_dir = dirs.operation_dir,
        df_metocean = metocean.df_timeseries,
        operations_inspect_site = operations_inspect_site,
        inputs_tseries = inputs.tseries,
        Config = Config
    )

    operation_inspect_port_manager(
        operation_dir = dirs.operation_dir,
        df_metocean = metocean.df_timeseries,
        duration_shift = inputs.tseries.shift_duration["value"],
        operations_inspect_port = operations_inspect_port
    )

    operation_major_manager(
        operation_dir = dirs.operation_dir,
        df_metocean = metocean.df_timeseries,
        operations_corr_major = operations_corr_major,
        inputs_tseries = inputs.tseries,
        Config = Config,
        timesteps = timesteps
    )

    opeartion_minor_manager(
        operation_dir = dirs.operation_dir,
        df_metocean = metocean.df_timeseries,
        operations_corr_minor = operations_corr_minor,
        inputs_tseries = inputs.tseries,
        Config = Config
    )


    ### --- OPERATION STATISTICAL ANALYSES --- ###
    logging.info('---------------------------------------------------------------')
    logging.info('--------------------\tSTATISTICAL ANALYSIS\t----------------')
    logging.info('---------------------------------------------------------------')

    statistical_duration_manager(
        operation_dir = dirs.operation_dir,
        total_operations = total_operations,
        inputs_stats = inputs.stats
    )

    # Fill the operations_stats with the maximum value of percentile
    logging.info('--------------------\tOperations statistics\t----------------')
    percentiles = {"pmax": inputs.stats.percentile_max["value"], "pmain": inputs.stats.percentile_main["value"]}

    operations_tow_stats = {}
    for key, perc in percentiles.items():
        operations_tow_stats[key] = OperationsTowStat.get_towing_statistics(
            operations=operations_tow,
            PERCENTILE=perc,
            run_dir=dirs.operation_dir,
        )

    operations_corrective_stats = {}
    for key, perc in percentiles.items():
        operations_corrective_stats[key] = CorrectiveStat.get_corrective_statistics(
            operations = operations_corr_major+operations_corr_minor,
            operations_tow_stat = operations_tow_stats[key],
            PERCENTILE = perc,
            run_dir = dirs.operation_dir,
        )

    inspections_site_stats = {}
    for key, perc in percentiles.items():
        inspections_site_stats[key] = InspectionSiteStat.get_inspection_statistics(
            insepctions_site=operations_inspect_site,
            PERCENTILE=perc,
            run_dir=dirs.operation_dir,
        )

    inspections_port_stats = {}
    for key, perc in percentiles.items():
        inspections_port_stats[key] = InspectionPortStat.get_inspection_statistics(
            insepctions_port = operations_inspect_port,
            PERCENTILE = perc,
            run_dir = dirs.operation_dir,
            n_port_inspections = {
                prefix: getattr(tech, 'n_device_at_port', 0) for prefix, tech in zip(["ofw", "owc", "opv"], [farm_technologies.wtg, farm_technologies.wec, farm_technologies.pv])
            },
            operations_tow_stat = operations_tow_stats[key],
            shift = inputs.tseries.shift_duration["value"]
        )

    find_element = Find_Element.create(
        operations = operations_tow + operations_inspect_site + operations_inspect_port + operations_corr_major + operations_corr_minor,
        operations_stats = operations_tow_stats['pmain'] + inspections_site_stats['pmain'] + inspections_port_stats['pmain'] + operations_corrective_stats['pmain'],
        operations_stats_pmax = operations_tow_stats['pmax'] + inspections_site_stats['pmax'] + inspections_port_stats['pmax'] + operations_corrective_stats['pmax'],
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
            operations_tow_stats = operations_tow_stats,
            inspections_port_stats = inspections_port_stats,
            inspections_site_stats = inspections_site_stats,
            operations_corrective_stats = operations_corrective_stats,
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
        operations_total = total_operations,
        save_dir = dirs.result_dir_avg
    )

    logging.info('--------------------\tEND OF THE SIMULATION\t--------------------')

    return dirs


if __name__ == "__main__":
    run()