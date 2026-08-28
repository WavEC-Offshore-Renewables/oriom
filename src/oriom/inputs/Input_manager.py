import os
import shutil
import logging
from oriom.inputs.excel_to_yaml import excel_to_yaml
from oriom.inputs import msoffice365_sharepoint


# Central mapping: logical keys -> filenames
FILE_MAP = {
    "inputs_gen_file": "inputs_gen.yaml",
    "inputs_tseries_file": "inputs_tseries.yaml",
    "inputs_stats_file": "inputs_stats.yaml",
    "inputs_costs_file": "inputs_costs.yaml",
    "wtg_file": "wtg.yaml",
    "wec_file": "wec.yaml",
    "pv_file": "pv.yaml",
    "vessels_file": "vessels.yaml",
    "vessels_fuel_cons_file": "vessels_fuels.yaml",
    "vessels_load_factor_file": "vessels_loads.yaml",
    "vessels_fuel_density_file": "vessels_densities.yaml",
    "rovs_drones_file": "rovs.yaml",
    "operations_insp_site_file": "operations_inspections_site.yaml",
    "operations_insp_port_file": "operations_inspections_port.yaml",
    "operations_corr_minor_file": "operations_corrective_minor.yaml",
    "operations_corr_major_file": "operations_corrective_major.yaml",
    "operations_tow_file": "operations_tow.yaml",
    "operations_activities_file": "operations_activities.yaml",
    "failures_file": "failures.yaml",
    "scenarios_file": "scenarios.yaml",
}


class Input_Files:
    """Container for all input file paths under a base directory."""

    def __init__(self, base_dir):
        self.base_dir = base_dir
        # Dynamically create attributes from FILE_MAP
        for key, fname in FILE_MAP.items():
            setattr(self, key, os.path.join(self.base_dir, fname))

    def __getitem__(self, key):
        """Allow dict-like access: files['inputs_gen']"""
        if key not in FILE_MAP:
            raise KeyError("Unknown file key: %s" % key)
        return getattr(self, key)

    def as_dict(self):
        """Return all paths as a {key: str} dictionary"""
        return dict((k, getattr(self, k)) for k in FILE_MAP.keys())

    def keys(self):
        return FILE_MAP.keys()

    def values(self):
        return (getattr(self, k) for k in FILE_MAP.keys())

    def items(self):
        return ((k, getattr(self, k)) for k in FILE_MAP.keys())

    def validate(self, must_exist=True):
        """
        Validate existence of files. If must_exist=True, raise if any missing.
        Returns the list of missing paths (empty if none).
        """
        missing = [getattr(self, k) for k in FILE_MAP.keys() if not os.path.exists(getattr(self, k))]
        if must_exist and missing:
            raise FileNotFoundError("Missing required input files:\n" + "\n".join(missing))
        return missing



# -----------
# Standalone
# -----------


def extract_input_from_excel(
    dirs: object,
    base_file_excel: bool,
    sharepoint_file_path: str,
    excel_file_path: str,
    form_name: str
):

    """
    Evaluate from which path input data is taken

    Args:
        dirs (ProjectDirs): class of ProjectDirs on which are stored all the simulation path
        base_file_excel (bool): Boolean that indicate if the input file must be taken from the sharepoint
        sharepoint_file_path (string): Path of input file in the sharepoint
        excel_file_path (string): Path of input file in the local memory
        form_name (string): Name of the simulation choosen
    """

    if base_file_excel is True:
        # Download Excel for from SharePoint
        msoffice365_sharepoint.download_file(
                source_path = sharepoint_file_path,
                dest_dir = dirs.tmp_dir,
                filename = form_name,
                dotenv_path = os.path.join(os.getcwd(), '.env')
        )
        # Call Excel-to-YAML functions
        excel_to_yaml(
                file_excel = os.path.join(os.getcwd(), 'tmp', form_name),
                out_dir = dirs.base_dir
        )
        shutil.copy2(os.path.join(excel_file_path, form_name), os.path.join(dirs.run_dir, form_name))
        logging.info(f"Input Manager: {form_name} downloaded from SharePoint and saved into current directory")

    elif base_file_excel is False and excel_file_path is not None:
        excel_to_yaml(
                file_excel=os.path.join(excel_file_path, form_name),
                out_dir = dirs.base_dir
        )
        shutil.copy2(os.path.join(excel_file_path, form_name), os.path.join(dirs.run_dir, form_name))
        logging.info(f"Input Manager: Input file {form_name} copied from local path and saved into current directory")

    elif base_file_excel is False and excel_file_path is None:
        for file_name in os.listdir(os.path.join(os.getcwd(),'tests','test_files','inputs')):
            # construct full file path
            source = os.path.join(os.getcwd(),'tests','test_files','inputs',file_name)
            destination = os.path.join(dirs.base_dir,file_name)
            # copy only files
            if source.endswith(('.yaml', '.yml')):
                shutil.copy(source, destination)

    


def handle_overwrite_previous(inputs_gen, dirs):
    """
    Handle overwrite of previous run if requested by inputs_gen.
    If previous run is requested overwrite the simulation directory with old simulation dir

    Args:
        inputs_gen (class: Inputs.General): class of general inputs
        dirs (class: ProjectDirs): class of simulation directory
    """
    try:
        if inputs_gen.overwrite_previous["value"]:
            for filename in os.listdir(dirs.run_dir):
                if filename == 'operation_dir':
                    continue
                source_path = os.path.join(dirs.run_dir, filename)
                destination_path = os.path.join(inputs_gen.previous_run_dir["value"], filename)

                if os.path.exists(destination_path):
                    if os.path.isfile(destination_path):
                        os.remove(destination_path)
                    elif os.path.isdir(destination_path):
                        shutil.rmtree(destination_path)

                shutil.move(source_path, destination_path)

            # Remove old log if exists
            try:
                os.remove(os.path.join(inputs_gen.previous_run_dir["value"], 'logging.log'))
            except FileNotFoundError:
                pass

            # Cleanup run_dir and update dirs paths
            shutil.rmtree(dirs.run_dir)
            dirs.run_dir = inputs_gen.previous_run_dir["value"]
            dirs.graph_dir = os.path.join(dirs.run_dir, 'graph_dir')
            dirs.operation_dir = os.path.join(dirs.run_dir, 'operation_dir')
            dirs.result_dir = os.path.join(dirs.run_dir, 'result_dir')
            dirs.base_dir = os.path.join(dirs.run_dir, 'base_files')

    except TypeError:
        pass
