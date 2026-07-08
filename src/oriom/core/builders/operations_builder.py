import sys
import os

sys.path.append(r"C:\Users\RiccardoMeda\Project\oriom\src")

from oriom.core.statistical_analysis.aux_statistical import find_percentiles

from oriom.utils import aux_functions
from oriom.utils import aux_operation

from oriom.domain.Vessels.RovDrone import RovDrone
from oriom.domain.Operations.InspectionSite import InspectionSite
from oriom.domain.Operations.InspectionPort import InspectionPort
from oriom.domain.Operations.CorrectiveMajor import CorrectiveMajor
from oriom.domain.Operations.CorrectiveMinor import CorrectiveMinor
from oriom.domain.Operations.OperationTow import OperationTow
from oriom.domain.OperationsStat.CorrectiveStat import CorrectiveStat
from oriom.domain.OperationsStat.InspectionPortStat import InspectionPortStat
from oriom.domain.OperationsStat.InspectionSiteStat import InspectionSiteStat
from oriom.domain.OperationsStat.OperationTowStat import OperationsTowStat
from oriom.domain.FindElementClass import Find_Element

from oriom.core.builders.DefineOperationTechs import Define_operation
from oriom.core.timeseries_analysis.operation_managers.operations_inspection_site_manager import inspect_site_manager
from oriom.core.timeseries_analysis.operation_managers.operations_tow_manager import operation_tow_manager
from oriom.core.timeseries_analysis.operation_managers.operations_inspection_port_manager import operation_inspect_port_manager
from oriom.core.timeseries_analysis.operation_managers.operations_major_manager import operation_major_manager
from oriom.core.timeseries_analysis.operation_managers.operations_minor_manager import opeartion_minor_manager


try:
    from oriom.core.functions.private import check_files
except ImportError:
    check_files = None

def aux_operation_builder(
        Config: object,
        inputs: object,
        files: object,
        dirs: object,
        failures: list,
        farm_technologies: object,
        G_layouts: dict
):
    """
    Create objects, populate for each operation the attributes and create a run folder with the activities and attributes files

    Args:
        Config (object): Configuration object from ``Config`` class
        inputs (object): Inputs object from ``Inputs`` class
        files (object): Files object from ``Files`` class
        dirs (object): Directories object from ``Dirs`` class
        failures (list): List of failure objects
        farm_technologies (object): Farm technologies object from ``FarmTechnologies`` class
        G_layouts (dict): Dictionary of graph layouts

    Returns: dict: Dictionary with the following keys
        - rovs_drones: List of ROV and Drone objects
        - vessels: List of Vessel objects
        - operations_tow: List of Towing Operation objects
        - operations_corr_major: List of Major Corrective Operation objects
        - operations_corr_minor: List of Minor Corrective Operation objects
        - operations_inspect_port: List of Inspection at Port Operation objects
        - operations_inspect_site: List of Inspection at Site Operation objects
        - total_operations: List of all Operation objects
    """

    vessels = {}

    # Define ROVs and Drones
    rovs_drones = RovDrone.get_rovdrones_from_yaml(files.rovs_drones_file)
    # Define Towing Operations
    operations_tow = OperationTow.get_operations_from_yaml(file_path = files.operations_tow_file)
    # Define Inspection Campaings at site
    operations_inspect_site = InspectionSite.get_inspections_from_yaml(file_path = files.operations_insp_site_file)
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
    operations_corr_minor = CorrectiveMinor.get_operations_from_yaml(file_path = files.operations_corr_minor_file)
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


    # Save operation attributes as YAML files
    for operation in total_operations:
        op_dir = os.path.join(dirs.operation_dir, operation.id)
        # Check if there is already an attributes file
        if check_files and check_files.check_file_exists(path=op_dir, file_name='attributes.yaml'):
            continue
        operation.to_yaml(op_dir)

    aux_operation.operation_check_identities(total_operations)

    return {
        'rovs_drones': rovs_drones,
        'vessels': vessels,
        'operations_tow': operations_tow,
        'operations_corr_major': operations_corr_major,
        'operations_corr_minor': operations_corr_minor,
        'operations_inspect_port': operations_inspect_port,
        'operations_inspect_site': operations_inspect_site,
        'total_operations': total_operations
    }


def aux_operation_stats_builder(
        inputs: object,
        dirs: object,
        farm_technologies: object,
        operations: dict,
        vessels: list,
        failures: list
):
    """
    Create statistical analysis for each operation and return a dictionary with the results

    Args:
        inputs (object): Inputs object from ``Inputs`` class
        dirs (object): Directories object from ``Dirs`` class
        farm_technologies (object): Farm technologies object from ``FarmTechnologies`` class
        operations (dict): Dictionary of operation lists
        vessels (list): List of Vessel objects
        failures (list): List of failure objects

    Returns: dict: Dictionary with the following keys
        - operations_tow_stats: Dictionary with the statistical analysis for Towing Operations
        - operations_corrective_stats: Dictionary with the statistical analysis for Corrective Operations
        - inspections_site_stats: Dictionary with the statistical analysis for Inspection at Site Operations
        - inspections_port_stats: Dictionary with the statistical analysis for Inspection at Port Operations
    """

    percentiles = find_percentiles(inputs_stats=inputs.stats)

    operations_tow_stats = {}
    for key, perc in percentiles.items():
        operations_tow_stats[key] = OperationsTowStat.get_towing_statistics(
            operations=operations['operations_tow'],
            PERCENTILE=perc,
            run_dir=dirs.operation_dir,
        )

    operations_corrective_stats = {}
    for key, perc in percentiles.items():
        operations_corrective_stats[key] = CorrectiveStat.get_corrective_statistics(
            operations = operations['operations_corr_major']+operations['operations_corr_minor'],
            operations_tow_stat = operations_tow_stats[key],
            PERCENTILE = perc,
            run_dir = dirs.operation_dir,
        )

    inspections_site_stats = {}
    for key, perc in percentiles.items():
        inspections_site_stats[key] = InspectionSiteStat.get_inspection_statistics(
            insepctions_site=operations['operations_inspect_site'],
            PERCENTILE=perc,
            run_dir=dirs.operation_dir,
        )

    inspections_port_stats = {}
    for key, perc in percentiles.items():
        inspections_port_stats[key] = InspectionPortStat.get_inspection_statistics(
            insepctions_port = operations['operations_inspect_port'],
            PERCENTILE = perc,
            run_dir = dirs.operation_dir,
            n_port_inspections = {
                prefix: getattr(tech, 'n_device_at_port', 0) for prefix, tech in zip(["ofw", "owc", "opv"], [farm_technologies.wtg, farm_technologies.wec, farm_technologies.pv])
            },
            operations_tow_stat = operations_tow_stats[key],
            shift = inputs.tseries.shift_duration["value"]
        )

    
    find_element = Find_Element.create(
        operations = operations['total_operations'],
        operations_stats = operations_tow_stats['pmain'] + inspections_site_stats['pmain'] + inspections_port_stats['pmain'] + operations_corrective_stats['pmain'],
        operations_stats_pmax = operations_tow_stats['pmax'] + inspections_site_stats['pmax'] + inspections_port_stats['pmax'] + operations_corrective_stats['pmax'],
        vessels = vessels,
        failures = failures
    )


    return {
        'inspections_port_stats': inspections_port_stats,
        'inspections_site_stats': inspections_site_stats,
        'operations_corrective_stats': operations_corrective_stats,
        'operations_tow_stats': operations_tow_stats
    }, find_element


def operation_timeseries_builder(
        inputs: object,
        dirs: object,
        operations: dict,
        metocean: object,
        metocean_port: object,
        metocean_tow: object,
        metocean_tow_distance: object,
        timesteps: list,
        Config: object
):
    """
    Create timeseries analysis for each operation and save the results in the operation run folder. 
    The function calls the operation managers for each operation type.

    Args:
        inputs (object): Inputs object from ``Inputs`` class
        dirs (object): Directories object from ``Dirs`` class
        operations (dict): Dictionary of operation lists
        metocean (object): Metocean object from ``Metocean`` class
        metocean_port (object): Metocean object from ``Metocean`` class for port operations
        metocean_tow (object): Metocean object from ``Metocean`` class for towing operations
        metocean_tow_distance (object): Metocean object from ``Metocean`` class for towing operations with distance
        timesteps (list): List of timesteps for the simulation
        Config (object): Configuration object from ``Config`` class
    """
    
    operation_tow_manager(
        operation_dir = dirs.operation_dir,
        df_metocean = metocean.df_timeseries,
        max_wait = inputs.tseries.max_wait["value"],
        operations_tow = operations['operations_tow'],
        timesteps = timesteps,
        Config = Config,
        inputs_tseries = inputs.tseries,
        metocean_tow = metocean_tow,
        metocean_tow_distance = metocean_tow_distance
    )

    inspect_site_manager(
        operation_dir = dirs.operation_dir,
        df_metocean = metocean.df_timeseries,
        operations_inspect_site = operations['operations_inspect_site'],
        inputs_tseries = inputs.tseries,
        Config = Config
    )

    operation_inspect_port_manager(
        operation_dir = dirs.operation_dir,
        df_metocean = metocean_port.df_timeseries,
        duration_shift = inputs.tseries.shift_duration["value"],
        operations_inspect_port = operations['operations_inspect_port']
    )

    operation_major_manager(
        operation_dir = dirs.operation_dir,
        df_metocean = metocean.df_timeseries,
        df_metocean_port = metocean_port.df_timeseries,
        operations_corr_major = operations['operations_corr_major'],
        inputs_tseries = inputs.tseries,
        Config = Config,
        timesteps = timesteps
    )

    opeartion_minor_manager(
        operation_dir = dirs.operation_dir,
        df_metocean = metocean.df_timeseries,
        operations_corr_minor = operations['operations_corr_minor'],
        inputs_tseries = inputs.tseries,
        Config = Config
    )