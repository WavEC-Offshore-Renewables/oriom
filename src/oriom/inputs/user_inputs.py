import os
import logging
from ruamel.yaml import YAML

from oriom.domain.Forecast import Forecast


ATTR_TO_LOWER = [
    'id', 'level', 'level_failure', 'operation_triggered', 'maintenance_strategy', 
    'type', 'fuel_type', 'vessel1_id', 'vessel2_id', 'rov_drone', 'to_group_with', 'name'
]


class user_input_overwrite():
    """ Class to evaluate the user specific data and modify the preexistent data
    Methods:
        run(): Main entry point to process data and return the dictionaries
        read_user_data(): Read user specific data and store them
        overwrite_user_data(): Overwrite user specific data
        ST_switcher(): Switch to ST use mode
    """
    def __init__(self):
        self.failure_dict_value = {}
        self.failure_list_obj = []
        self.oper_dict_value = {}
        self.oper_dict_obj = {}
        self.vessels_dict_value = {}
        self.vessels_list_obj = []
        pass


    @classmethod
    def run_overwrite(
        cls,
        inputs: object,
        dirs: object,
        failures: list,
        operations: dict,
        vessels: list,
        files_paths: dict,
        ST: bool
    ):
        """ Factory method to execute logic and return values ​​directly. 
        Args:
            inputs (object): Inputs object from ``Inputs`` class
            dirs (object): Directories object from ``Dirs`` class
            failures (list): List of failure objects of class ``Failure``
            operations (dict): Dictionary of operation lists
            vessels (list): List of Vessel objects
            files_paths (dict): Dictionaries of file path to use for overwriting
            ST (bool): Boolean that will manage switching to ST O&M
        """
        # Create instance
        instance = cls()
        
        # Use instance logic and read USER DATA
        instance.failure_dict_value = instance.read_user_data(file_path=files_paths.get('failure_path'))
        for operation_type in operations.keys():
            files_paths_op = files_paths.get('operations_path')
            instance.oper_dict_value[operation_type] = instance.read_user_data(file_path=files_paths_op.get(operation_type, ''))
        instance.vessels_dict_value = instance.read_user_data(file_path=files_paths.get('vessels_path'))

        # OVERWRITE WITH USER DATA
        instance.overwrite_user_data(original_data = failures, data_overwrite = instance.failure_dict_value)
        instance.overwrite_user_data(original_data = vessels, data_overwrite = instance.vessels_dict_value)
        for operation_type in operations.keys():
            instance.overwrite_user_data(
                original_data = operations[operation_type],
                data_overwrite = instance.oper_dict_value[operation_type],
            )
        
        # Evaluate ST O&M mode
        if ST:
            failures, operations = instance.ST_switcher(inputs = inputs, dirs = dirs, failures = failures, operations = operations)

        # Returns value modified
        return (
            failures,
            operations,
            vessels
        )


    def read_user_data(self, file_path):
        """
        Read the YAML file containing user modifications.
        Returns
            dict: Dictionary indexed by object ID, where each value is the corresponding YAML entry with:
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data_yaml = YAML(typ="safe").load(f) or []
        except FileNotFoundError:
            return {}

        data_dict = {}

        for item in data_yaml:
            # Convert all keys to lowercase
            item = {key.lower(): value for key, value in item.items()}

            # Convert selected string attributes to lowercase
            for attr in ATTR_TO_LOWER:
                value = item.get(attr)
                if isinstance(value, str):
                    item[attr] = value.lower()

            # Store using the object ID as key
            data_dict[item["id"]] = item

        return data_dict


    def data_finder(self, original_data, key_data):
        """ Find the object to overwrite by its ID"""

        data_modify = None
        for dat in original_data:
            if dat.id == key_data:
                data_modify = dat

        if not data_modify:
            e_ = f'Data to overwrite {key_data} not found in {original_data} objects list'
            logging.error(e_)
            raise KeyError(e_)
        
        return data_modify


    def overwrite_user_data(self, original_data: dict, data_overwrite: dict):
        """ Overwrite all the original data that are defined by the USER """
        # Iterate on data to overwrite by the ID of the object
        if data_overwrite:
            for key_data, data_overw in data_overwrite.items():
                # Find the object by its ID
                original_data_modify = self.data_finder(original_data = original_data, key_data = key_data.lower())
                # For each data to overwrite check if attribute exist and overwrite the value
                for data_key_write, data_write in data_overw.items():
                    if getattr(original_data_modify, data_key_write, None) != None:
                        if getattr(original_data_modify, data_key_write, None) != data_write:
                            info_ = f'Attribute modified for ´´{original_data_modify}´´: ´´{data_key_write}´´'
                            info_ += f'from ´´{getattr(original_data_modify, data_key_write, None)}´´ ->  ``{data_write}´´'
                            logging.info(info_)
                            setattr(original_data_modify, data_key_write, data_write)
                    else:
                        e_ = f'Attribute to overwrite ´´{data_key_write}´´ not found in ´´{original_data_modify}´´ objects for {key_data}´´'
                        logging.error(e_)
                        raise KeyError(e_)

    
    def ST_switcher(self, inputs: object, dirs: object, failures: list, operations: dict):
        """ Modify data to switch into Short Term O&M """
        failures = self.ST_data_object_overwrite(object_data_list = failures, dict_value = self.failure_dict_value)
        
        logging.info('-------------------------')
        logging.info('Switched to ST O&M mode')
        logging.info('-------------------------')

        logging.info(f"Failures analysed: {[fail.id for fail in failures]}")
        
        for operation_type in operations.keys():
            operations[operation_type] = self.ST_data_object_overwrite(
                object_data_list = operations[operation_type],
                dict_value = self.oper_dict_value.get(operation_type, {})
            )
            logging.info(f"{operation_type} analysed: {[op.id for op in operations[operation_type]]}")


        # Withdrawn Forecast Data and substitue it with timeseries file
        IPMA_forecast = Forecast(
            forecast_client=os.getenv("IPMA_USERNAME"),
            forecast_password=os.getenv("IPMA_PASSWORD"),
            name_point='AB',
            addr=r'https://api.ipma.pt/ARIA2/points/forecast',
            save_dir = dirs.run_dir
        )
        inputs.tseries.file_metocean["value"] = IPMA_forecast.timeseries_file

        return failures, operations


    def ST_data_object_overwrite(self, object_data_list: list, dict_value: dict) -> list:
        """Returns a list of objects based on a the objects to filter within the one defined in dict_value by the user."""
        data_filtered = []
        for key in dict_value.keys():
            for element in object_data_list:
                if element.id == key:
                    data_filtered.append(element)
                    break

        return data_filtered


if __name__ == '__main__':

    from oriom.domain.Operations.CorrectiveMajor import CorrectiveMajor
    from oriom.domain.Operations.OperationTow import OperationTow
    from oriom.domain.Failure import Failure
    from oriom.domain.Operations.InspectionSite import InspectionSite

    class DUMMY_2():
        def __init__(self):
            self.file_metocean = {'value': 'prova'}
        def __str__(self):
            return 'DUMMY'

    class DUMMY():
        def __init__(self, id = 'ID_001'):
            self.tseries = DUMMY_2()
            self.run_dir = r'C:\Users\RiccardoMeda\Project\oriom\tmp\user'
            self.id = id
            self.ST = False

        def __str__(self):
            return 'DUMMY'


    path_modifier_user = r'C:\Users\RiccardoMeda\Project\oriom\tmp\user'


    failures = Failure.get_failures_from_yaml(file_path = os.path.join(path_modifier_user, 'failures.yaml'))

    operations = {}
    operations['operations_tow'] = OperationTow.get_operations_from_yaml(file_path = os.path.join(path_modifier_user, 'operations_tow.yaml'))
    # Define Inspection Campaings at site
    operations['operations_inspect_site'] = InspectionSite.get_inspections_from_yaml(file_path = os.path.join(path_modifier_user, 'operations_inspections_site.yaml'))
    # Define Major Corrective Operations
    operations['operations_corr_major'] = CorrectiveMajor.get_operations_from_yaml(
        file_path = os.path.join(path_modifier_user, 'operations_corrective_major.yaml'),
        towing_operations = operations['operations_tow']
    )


    failures, operations, vessels = user_input_overwrite.run_overwrite(
        inputs=DUMMY(), 
        dirs=DUMMY(), 
        failures=failures, 
        operations=operations,
        vessels = [DUMMY(), DUMMY()],
        files_paths={
            'failure_path': os.path.join(path_modifier_user, 'failures_user.yaml'),
            'operations_path': {
                'operations_corr_major': os.path.join(path_modifier_user, 'operations_corrective_major_user.yaml'),
                'operations_tow': os.path.join(path_modifier_user, 'operations_tow_user.yaml'),
                'operations_inspect_site': os.path.join(path_modifier_user, 'xx.yaml'),
            },
            'vessels_path': os.path.join(path_modifier_user, 'vessels_user.yaml'),
        },
        ST = DUMMY()
    )
