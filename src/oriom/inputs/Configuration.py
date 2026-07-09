import os
from datetime import datetime


class ConfigRun:
    """Runtime configuration with explicit constructor arguments.

    Attribute:
        STATISTICAL_CHART (bool): Flag to consider statistical time chart Pmax as end of contract ST
            Default to True.
        DIFF_DISTANCE (bool): Flag to consider different distance for port
            Default to False.
        DIFF_KM_DISTANCE (int): Distance of different port.
            Default to 30.
        KM_MOTHER_VESSEL (int): Distance of mother vessel anchor at site.
            Default to 5.
        VESSEL_DIST_REDUCED_LIST (list): List string for vessel.type that will use different km distance.
            Default to [].
        FUEL_TO_ADD (dict): key vessel id and value float of fuel cost to add on total lifetime.
            Default to {}.
        MOBILISATION_TO_ADD(dict): key vessel.id and value float of mobilisation cost to add on total lifetime.
            Default to {}.
        ENERGY_AVAILABILITY_CALCULATION (bool): Flag to consider energy calculation
            Default to True.
        ENERGY_STATISTICAL_CALCULATION (bool): Flag to consider statistical or timeseries energy calculation
            Default to False.
        PROJECT_NAME (str): Name of the project choose. Default to ''.
        BASEFILES_FROM_EXCEL (bool):  Flag to consider excel input file to read on sharepoint.
            Default to False.
        EXCEL_FILE_PATH (str): Path to the excel input file to read. Default to None.
        SOURCE_PATH_SHAREPOINT (str): Path to the excel input file to read in sharepoint folder. Default to None.
        FORM_NAME (str): Name of the excel input file to read. Default to None.,
        TIME_FAIL_OP_IMMEDIATELY(float): Reaction time of operation in consequence of failure.
            Default to 0.02.
        ST (bool): Boolean that will manage switching to ST O&M. Default to ``False``
        DIRS_OVERWRITE_PATH (str): Path were to find the overwrite file YAML. Default to ````
    """

    def __init__(
        self,
        # --- General ---
        STATISTICAL_CHART: bool = True,
        DIFF_DISTANCE: bool = False,
        DIFF_KM_DISTANCE: float = 30,
        KM_MOTHER_VESSEL: float = 5,
        VESSEL_DIST_REDUCED_LIST: list = [],
        FUEL_TO_ADD: dict = {},
        MOBILISATION_TO_ADD: dict = {},
        ENERGY_AVAILABILITY_CALCULATION: bool = True,
        ENERGY_STATISTICAL_CALCULATION: bool = True,
        SPECIAL_VARIABLE: dict = {},
        PROJECT_NAME: str = None,
        BASEFILES_FROM_EXCEL: bool = False,
        EXCEL_FILE_PATH: str = None,
        SOURCE_PATH_SHAREPOINT: str = None,
        FORM_NAME: str = None,
        TIME_FAIL_OP_IMMEDIATELY: float = 0.02,
        ST: bool = False,
        DIRS_OVERWRITE_PATH = ''
    ):

        # General
        self.STATISTICAL_CHART = STATISTICAL_CHART
        self.DIFF_DISTANCE = DIFF_DISTANCE
        self.DIFF_KM_DISTANCE = DIFF_KM_DISTANCE
        self.KM_MOTHER_VESSEL = KM_MOTHER_VESSEL
        self.VESSEL_DIST_REDUCED_LIST = VESSEL_DIST_REDUCED_LIST
        self.FUEL_TO_ADD = FUEL_TO_ADD
        self.MOBILISATION_TO_ADD = MOBILISATION_TO_ADD
        self.ENERGY_AVAILABILITY_CALCULATION = ENERGY_AVAILABILITY_CALCULATION
        self.ENERGY_STATISTICAL_CALCULATION = ENERGY_STATISTICAL_CALCULATION
        self.SPECIAL_VARIABLE = SPECIAL_VARIABLE
        self.ST = ST

        # Project
        self.PROJECT_NAME = PROJECT_NAME
        self.BASEFILES_FROM_EXCEL = BASEFILES_FROM_EXCEL
        self.EXCEL_FILE_PATH = EXCEL_FILE_PATH
        self.SOURCE_PATH_SHAREPOINT = SOURCE_PATH_SHAREPOINT
        self.FORM_NAME = FORM_NAME
        self.DIRS_OVERWRITE_PATH = DIRS_OVERWRITE_PATH

        # Simulation
        self.TIME_FAIL_OP_IMMEDIATELY = TIME_FAIL_OP_IMMEDIATELY

        self._check_attributes()

        self.OPERATION_FILES = [
            'attributes.yaml',
            'activities.csv',
            'workability.csv',
            'startability.csv',
            'operation_schedule.csv',
            'towing_inspection_log.csv'
        ]


    @staticmethod
    def _kv_lines(mapping):
        """Build formatted 'key: value' lines for logging."""
        # Keep deterministic order for readability
        lines = []
        for k in mapping:
            lines.append("  - {0}: {1}".format(k, mapping[k]))
        return "\n".join(lines)


    def log_parameters(self, logger, inputs_gen=None):
        """Log main configuration blocks and optionally previous timeseries."""
        general = {
            "STATISTICAL_CHART": self.STATISTICAL_CHART,
            "DIFF_DISTANCE": self.DIFF_DISTANCE,
            "DIFF_KM_DISTANCE": self.DIFF_KM_DISTANCE,
            "KM_MOTHER_VESSEL": self.KM_MOTHER_VESSEL,
            "VESSEL_DIST_REDUCED_LIST": self.VESSEL_DIST_REDUCED_LIST,
            "FUEL_TO_ADD": self.FUEL_TO_ADD,
            "MOBILISATION_TO_ADD": self.MOBILISATION_TO_ADD,
            "ENERGY_AVAILABILITY_CALCULATION": self.ENERGY_AVAILABILITY_CALCULATION,
        }
        project = {
            "PROJECT_NAME": self.PROJECT_NAME,
            "BASEFILES_FROM_EXCEL": self.BASEFILES_FROM_EXCEL,
            "EXCEL_FILE_PATH": self.EXCEL_FILE_PATH,
            "SOURCE_PATH_SHAREPOINT": self.SOURCE_PATH_SHAREPOINT,
            "FORM_NAME": self.FORM_NAME,
        }
        simulation = {
            "TIME_FAIL_OP_IMMEDIATELY": self.TIME_FAIL_OP_IMMEDIATELY,
        }

        logger.info("--------------------\tINPUTS - GENERAL\t--------------------")
        logger.info("Run parameters (general):\n%s", self._kv_lines(general))
        logger.info("Run parameters (project):\n%s", self._kv_lines(project))
        logger.info("Run parameters (simulation):\n%s", self._kv_lines(simulation))

        if inputs_gen is not None:
            try:
                prev_dir = inputs_gen.previous_run_dir["value"]
                if prev_dir:
                    logger.info("This run is using a previous timeseries: %s", prev_dir)
            except (AttributeError, KeyError, TypeError):
                # Silently ignore if inputs_gen does not expose the expected field
                pass

    def _check_attributes(self):
        """
        Validate that required attributes are defined.
        Raises ValueError if any attribute is missing or invalid.
        """
        required = [
            "STATISTICAL_CHART",
            "ENERGY_AVAILABILITY_CALCULATION",
            "PROJECT_NAME",
            "BASEFILES_FROM_EXCEL",
            "EXCEL_FILE_PATH",
            "FORM_NAME",
        ]

        missing = []
        for attr in required:
            if not hasattr(self, attr) or getattr(self, attr) is None:
                missing.append(attr)

        # Conditional requirement
        if getattr(self, "BASEFILES_FROM_EXCEL", False) is True:
            if not hasattr(self, "SOURCE_PATH_SHAREPOINT") or getattr(self, "SOURCE_PATH_SHAREPOINT") in (None, ""):
                missing.append("SOURCE_PATH_SHAREPOINT")

        if missing:
            raise ValueError("Config_Run: Missing value for" + ", ".join(missing))



class ProjectDirs:
    """Container for all project directories.
    
    Attributes:
        project_name (str): Name of the simulation undergoing
        tmp_dir (str): Path to the folder of the simulation undergoing
        base_dir (str): Path to the ``input`` folder of the simulation undergoing
        operation_dir (str): Path to the ``operations`` folder of the simulation undergoing
        graph_dir (str): Path to the ``graph`` folder of the simulation undergoing
        result_dir (str): Path to the ``results`` folder of the simulation undergoing
        result_dir_avg (str): Path to the ``results averaged`` folder of the simulation undergoing
        data_overwrite_user_path (str): Path to the ``user overwrite data`` folder of the simulation undergoing
        overwrite_files_path (dict): Dictionary with all the files selected by the users to overwrite
    """

    def __init__(
            self,
            project_name: str,
            time_prefix: datetime = '',
            data_overwrite_user_path: str = ''
        ):

        self.project_name = project_name
        self.tmp_dir = os.path.join(os.getcwd(), 'tmp')
        os.makedirs(self.tmp_dir, exist_ok=True)

        # timestamp to distinguish the runs
        self.run_dir = os.path.join(self.tmp_dir, project_name + str(time_prefix))

        # subdirectory
        self.operation_dir = os.path.join(self.run_dir, 'operation_dir')
        self.graph_dir = os.path.join(self.run_dir, 'graph_dir')
        self.result_dir = os.path.join(self.run_dir, 'result_dir')
        self.result_dir_avg = os.path.join(self.run_dir, 'result_dir_avg')
        self.base_dir = os.path.join(self.run_dir, 'base_files')
        self.data_overwrite_user_path = data_overwrite_user_path

        # creation of folders
        for d in [
            self.run_dir,
            self.operation_dir,
            self.graph_dir,
            self.result_dir,
            self.result_dir_avg,
            self.base_dir,
        ]:
            os.makedirs(d, exist_ok=True)

        if self.data_overwrite_user_path:
            self.overwrite_files_path = {
                'failure_path': os.path.join(self.data_overwrite_user_path, 'failures_user.yaml'),
                'operations_path': {
                    'operations_tow': os.path.join(self.data_overwrite_user_path, 'operations_corrective_tow_user.yaml'),
                    'operations_corr_major': os.path.join(self.data_overwrite_user_path, 'operations_corrective_major_user.yaml'),
                    'operations_minor': os.path.join(self.data_overwrite_user_path, 'operations_corrective_minor_user.yaml'),
                    'operations_inspect_site': os.path.join(self.data_overwrite_user_path, 'operations_inspect_site_user.yaml'),
                    'operations_inspect_port': os.path.join(self.data_overwrite_user_path, 'operations_inspect_port_user.yaml'),
                },
                'vessels_path': os.path.join(self.data_overwrite_user_path, 'vessels_user.yaml'),
            }

    def __repr__(self):
        return (
            f"ProjectDirs(project_name={self.project_name!r}, "
            f"run_dir={self.run_dir!r})"
        )


    @classmethod
    def create(
            cls,
            project_name: str = "My_project",
            time_prefix: datetime = '',
            data_overwrite_user_path: str = ''
        ) -> "ProjectDirs":

        """Create all the directories needed for saving results."""

        return cls(project_name, time_prefix, data_overwrite_user_path)