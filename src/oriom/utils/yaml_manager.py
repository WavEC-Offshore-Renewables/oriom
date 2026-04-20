import os
import logging
from ruamel.yaml import YAML

from oriom.utils.aux_functions import update_dict


def inputs_to_yaml(inputs_object, out_dir: str, out_name: str):
    """Saves ~Inputs.X as a YAML file.

    Args:
        out_dir (:obj:`str`): The path where the YAML file is saved.
        out_name (:obj:`str`): The name of the YAML file.

    """
    input_file_name = str(out_name) + '.yaml'
    f_inputs = open(os.path.join(out_dir, input_file_name), 'w')
    data = {}
    for input, value in inputs_object.inputs.items():
        if input != "metocean file tow location":
            data[input] = {"value": value["value"], "units": value["units"]}
        else:
            for input_n, value_n in value.items():
                data[f'{input} {input_n}'] = value_n

    yaml=YAML()
    yaml.indent(mapping=4)
    yaml.dump(data, f_inputs)
    f_inputs.close()
    logging.info('Inputs: inputs saved as "%s".' % input_file_name)


def update_yaml_each_attribute(
        file_dir: str,
        file_name: str,
        data: dict,
        operation_id: str = None
):
    """ Open a file yaml and add the attributes passed un the dictionary data """

    # Upload file YAML
    file_path = os.path.join(file_dir, file_name)
    with open(file_path, 'r') as f:
        yaml = YAML(typ='safe')
        attr_yaml = yaml.load(f)

    if attr_yaml is None:
        attr_yaml = {}
        raise ValueError(f'UPDATE YAML: The file {file_dir}/{file_name} is empty')

    attr_yaml.setdefault('working_shifts', {})

    # Update the file yaml for each key of the dict that is not olc
    if data:
        if operation_id and data.get('id_main') and data['id_main'] != operation_id:
            data['id_main'] = operation_id
        for k, v in data.items():
            if 'olc' not in k:
                if k == 'number_shifts_main':
                    k = 'days_main'
                elif k == 'number_shifts_last':
                    k = 'days_last'
                elif k == 'duration_shift_main':
                    k = 'duration_main'
                elif k == 'duration_shift_last':
                    k = 'duration_last'
                elif k == 'n_vessels_main':
                    k = 'n_vessel_main'
                elif k == 'n_vessels_last':
                    k = 'n_vessel_last'
                attr_yaml['working_shifts'][k] = v

    # Save the file YAML updated
    with open(file_path, 'w') as f:
        yaml = YAML()
        yaml.indent(mapping=4)
        yaml.dump(attr_yaml, f)


def update_yaml(
        file_dir: str,
        file_name: str,
        data: dict,
        data_key: str=None,
        recursive: bool=False,
        operation_id:str=None
):
    if data_key is not None and recursive is True:
        _w = 'If "recursive" is True, "data_key" is ignored.'
        logging.warning(_w)

    f = open(os.path.join(file_dir, file_name), 'r')
    yaml=YAML(typ='safe')
    attr_yaml = yaml.load(f)
    f.close()
    if operation_id and data.get('id_main') and data['id_main'] != operation_id:
        data['id_main'] = operation_id
    if recursive:
        new_yaml = update_dict(attr_yaml, data)
    else:
        new_yaml = attr_yaml
        new_yaml[data_key] = data

    f = open(os.path.join(file_dir, file_name), 'w')
    yaml=YAML()
    yaml.indent(mapping=4)
    #yaml.default_flow_style = None
    yaml.dump(new_yaml, f)
    f.close()


def load_shift_values_from_yaml(file_dir: str, file_name: str):
    """From a file yaml return a dictionary of some element selected"""
    op_working_shifts = {}

    # Upload file YAML
    file_path = os.path.join(file_dir, file_name)
    yaml = YAML(typ='safe')

    with open(file_path, 'r') as f:
        data = yaml.load(f)

    # Extract values with .get()
    op_working_shifts['days_main'] = data.get('days_main', None)
    op_working_shifts['duration_main'] = data.get('duration_main', None)
    op_working_shifts['days_last'] = data.get('days_last', None)
    op_working_shifts['duration_last'] = data.get('duration_last', None)
    op_working_shifts['n_vessel_main'] = data.get('n_vessel_main', None)
    op_working_shifts['n_vessel_last'] = data.get('n_vessel_last', None)
    op_working_shifts['n_dev_inspected_main_shift'] = data.get('n_dev_inspected_main_shift', None)
    op_working_shifts['n_dev_inspected_last_shift'] = data.get('n_dev_inspected_last_shift', None)
    op_working_shifts['n_crew_main'] = data.get('n_crew_main', None)
    op_working_shifts['n_crew_last'] = data.get('n_crew_last', None)

    return op_working_shifts


def load_similar_op_yaml(file_dir: str, file_name: str, operation_id: str = None) -> dict:
    """
    Recycling the values obtained from another operation, extrapolate from the similar operation the values
    regarding the shifts and return them in two dictionaries
    """

    data_working_shifts_key = [
        "days_main", "duration_main", "rov_main", "n_crew_main", "n_crew_last",
        "id_grouped", "days_grouped", "duration_grouped", "rov_grouped",
        "n_vessels_main", "n_vessels_last",
    ]

    # Upload the similar operation file YAML
    file_path = os.path.join(file_dir, file_name)
    yaml = YAML(typ='safe')

    with open(file_path, 'r') as f:
        data = yaml.load(f)

    section_data = data.get('working_shifts', {})

    # take only the values from the allowed_keys
    section_data['id_main'] = operation_id
    op_working_shifts = section_data

    data_working_shifts = {k: data.get(k) for k in data_working_shifts_key if k in data}

    return op_working_shifts, data_working_shifts

