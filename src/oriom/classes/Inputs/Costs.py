import logging
import os
import pandas as pd
import math as mt
from ruamel.yaml import YAML
from oriom.utils.yaml_manager import inputs_to_yaml


class Cost():
    """Project inputs related with the Cost analysis. Project :class:`Inputs.Cost`
    can be defined either with a YAML file or one-by-one. If `file_inputs`
    parameter is given, the other parameters will not be considered.

    Note:
        merge:
            If this is True al functions in the "merging_fcn" are enabled. Also the attribute
            "time_between_merge" must be defined and corresponds to the number of days between two
            corrective maintenances that we are willing to wait in order to merge them and be performed
            as one offshore interventation.

    Attributes:
        fuel_cost_HFO (:obj:`dict`): Heavy Fuel Oil cost, in euros/ton.
            **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
        fuel_cost_MGO (:obj:`dict`): Marine Gas Oil cost, in euros/ton.
            **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
        fuel_cost_MDO (:obj:`dict`): Marine Diesel Oil cost, in euros/ton.
            **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
        electricity_selling_price (:obj:`dict`): Electricity selling price in euros/Mwh.
            **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
        port_cost_year (:obj:`dict`): Cost of a dedicated port terminal per year.
            **keys**: *value*: :obj:`float` ; *units*: :obj:`str`.
        merge (:obj:`dict`): Boolean, if True the log_dates will look for operation to merge.
            **keys**: *value*: :obj:`bool` ; *units*: : obj:``
        time_between_merge (:obj:`dict`): Number of days within which the operation can be merged. Its value is ``None`` if not defined.
        insurance_annual (:obj:`dict`): Cost of Insurance per year.
            **keys**: *value*: :obj:`float` ; *units*: : obj:``
        electricity_price (:obj:`dict`): Electricity selling price.
            **keys**: *value*: :obj:`float` ; *units*: : obj:``
        electricity_price pv (:obj:`dict`): Electricity selling price per pv tech.
            **keys**: *value*: :obj:`float` ; *units*: : obj:``
        electricity_price wt (:obj:`dict`): Electricity selling priceper wt tech.
            **keys**: *value*: :obj:`float` ; *units*: : obj:``
        electricity_price wec (:obj:`dict`): Electricity selling price per wec tech.
            **keys**: *value*: :obj:`float` ; *units*: : obj:``
        technicians_year (:obj:`dict`): Cost of Technicians per year.
            **keys**: *value*: :obj:`float` ; *units*: : obj:``
        file_inputs (:obj:`str`): Path for the file with all previous mandatory inputs.
            Its value is ``None`` if not defined.
        electricity_price_dict (:obj:`dict`): Electricity price per each tech

    Note:
        When the class is initialized :func:`_check_attributes` is run.

    Example:
        >>> args = {
        >>>         "fuel_cost_MDO": 700,
        >>>         "vessel_cost_year": 10000
        >>> }
        >>> inputs = Inputs.Cost(**args)
        >>> logging.info('The yearly cost of a dedicated vessel is %.3f %s.' % \
        >>>         (inputs.vessel_cost_year["value"], inputs.vessel_cost_year["units"]))
    """

    def __init__(self, **kwargs):
        """Initializes :class:`Inputs.Cost`.

        Args:
            **kwargs: Arbitrary keyword arguments.

        Keyword Args:
            electricity_selling_price (:obj:`float`): Electricity selling price in euros/Mwh.
            fuel_cost_HFO (:obj:`float`): Heavy Fuel Oil cost, in euros/ton.
            fuel_cost_MGO (:obj:`float`): Marine Gas Oil cost, in euros/ton.
            fuel_cost_MDO (:obj:`float`): Marine Diesel Oil cost, in euros/ton.
            port_cost_year (:obj:`float`,*optional*): Cost of a dedicated port terminal per year, in euros. Defaults to ``0.0``.
            merge (:obj:`dict`,*optional*): Boolean, if True the log_dates will look for operation to merge. Defaults to ``False``.
            time_between_merge (:obj:`int`,*optional*): Number of days within which the operation can be merged. Defaults to ``None``.
            insurance_annual (:obj:`float`,*optional*): Cost of Insurance per year, in euros. Defaults to ``0.0``.
            electricity_price (:obj:`dict`,*optional*): Dictionary Electricity selling price for each tech, in euros/MWh. Defaults to ``None``.
            technicians_year (:obj:`float`,*optional*): Cost of Technicians per year, in euros. Defaults to ``0.0``.
            file_inputs (:obj:`str`,*optional*): Path for the file with all previous mandatory inputs. Defaults to ``None``.

        Raises:
            NameError: units of :attr:`fuel_cost_hfo` not recognized.
            NameError: units of :attr:`fuel_cost_mgo` not recognized.
            NameError: units of :attr:`fuel_cost_mdo` not recognized.
        """
        self.inputs = {}

        # Default values
        self.inputs["vessel cost year"] = {"value" : 0.0, "units": 'euros'}
        self.inputs["port cost year"] = {"value": 0.0, "units": 'euros'}
        self.inputs["merge"] = {"value": False, "units": ""}
        self.inputs["time between merge"] = {"value": None, "units": 'days'}
        self.inputs["insurance annual"] = {"value": 0.0, "units": 'euros'}
        self.inputs["electricity price"] = {"value": None, "units": 'euros/mwh'}
        self.inputs["electricity price pv"] = {"value": None, "units": 'euros/mwh'}
        self.inputs["electricity price wec"] = {"value": None, "units": 'euros/mwh'}
        self.inputs["electricity price wt"] = {"value": None, "units": 'euros/mwh'}
        self.inputs["technicians year"] = {"value": 0.0, "units": 'euros'}

        file_path = kwargs.get('file_inputs', None)
        if file_path is not None:
            # Gets inputs from a yaml file
            f_yaml = open(os.path.join(file_path), 'r')
            yaml = YAML(typ='safe')
            inputs_yaml = yaml.load(f_yaml)
            f_yaml.close()

            # Verify inputs in inputs_yaml and organize them in dictionaries
            for key, values in inputs_yaml.items():
                name = key.lower()
                value = values['value']
                try:
                    if mt.isnan(float(value)) is True:
                        continue
                except ValueError:
                    pass

                units = str(values['units'])

                if 'fuel' in name:
                    if (
                            units.lower() == 'euros/ton' or
                            units.lower() == 'euro/ton' or
                            units.lower() == 'euros per ton' or
                            units.lower() == 'euro per ton'
                    ):
                        units = 'euros/ton'
                    else:
                        raise NameError('Units "%s" not recognized for fuel cost inputs.' % units)
                    if 'hfo' in name:
                        self.inputs["fuel cost hfo"] = {"value": float(value), "units": str(units)}
                    elif 'mgo' in name:
                        self.inputs["fuel cost mgo"] = {"value": float(value), "units": str(units)}
                    elif 'mdo' in name:
                        self.inputs["fuel cost mdo"] = {"value": float(value), "units": str(units)}
                    else:
                        logging.warning('Inputs.Cost: fuel type "%s" not recognized. Ignored.' % key)
                elif ('port' in name or 'terminal' in name) and ('annual' in name or 'year' in name):
                    if units.lower() != 'euros':
                        raise NameError('Units "%s" not recognized for a Dedicated Port Terminal annual cost input.' % units)
                    self.inputs["port cost year"] = {"value": float(value), "units": str(units)}
                elif 'time' in name and 'between' in name and 'merge' in name:
                    if pd.isna(value) is True:
                        self.inputs["time between merge"] = {"value": None, "units": str(units)}
                    else:
                        self.inputs["time between merge"] = {"value": int(value), "units": str(units)}
                elif 'merge' in name:
                    self.inputs["merge"] = {"value": bool(value), "units": None}
                elif 'insurance' in name and ('annual' in name or 'year' in name):
                    if units.lower() != 'euros':
                        raise NameError('Units "%s" not recognized for a Insurance annual cost input.' % units)
                    self.inputs["insurance annual"] = {"value": float(value), "units": str(units)}
                elif 'electricity' in name and 'price' in name:
                    if units.lower() != 'euros/mwh':
                        raise NameError('Units "%s" not recognized for the Electricity Selling Price input.' % units)
                    if name == 'electricity price':
                        self.inputs["electricity price"] = {"value": float(value), "units": str(units)}
                    elif 'pv' in name:
                        self.inputs["electricity price pv"] = {"value": float(value), "units": str(units)}
                    elif 'wec' in name:
                        self.inputs["electricity price wec"] = {"value": float(value), "units": str(units)}
                    elif 'wt' in name:
                        self.inputs["electricity price wt"] = {"value": float(value), "units": str(units)}
                    else:
                        raise NameError('Tech "%s" not recognized for the Electricity Selling Price input.' % name)
                elif 'technicians' in name and ('annual' in name or 'year' in name):
                    if units.lower() != 'euros':
                        raise NameError('Units "%s" not recognized for a Technicians annual cost input.' % units)
                    self.inputs["technicians year"] = {"value": float(value), "units": str(units)}
                else:
                    logging.warning('Inputs.Cost: input "%s" not recognized. Ignored.' % key)
            logging.info('Inputs.Cost: inputs read from a YAML file: "%s".' % file_path)

        # If a yaml file is not provided, gets inputs from **kwargs
        else:
            for key, value in kwargs.items():
                if key.lower() == 'fuel_cost_hfo':
                    self.inputs["fuel cost hfo"] = {
                            "value": float(value),
                            "units": 'euros/ton'
                    }
                elif key.lower() == 'fuel_cost_mgo':
                    self.inputs["fuel cost mgo"] = {
                            "value": float(value),
                            "units": 'euros/ton'
                    }
                elif key.lower() == 'fuel_cost_mdo':
                    self.inputs["fuel cost mdo"] = {
                            "value": float(value),
                            "units": 'euros/ton'
                    }
                elif key.lower() == 'port_cost_year':
                    self.inputs["port cost year"] = {
                            "value": float(value),
                            "units": 'euros'
                    }
                elif key.lower() == 'merge':
                    self.inputs["merge"] = {
                            "value": bool(value),
                            "units": None
                    }
                elif key.lower() == 'time_between_merge':
                    self.inputs["time between merge"] = {
                            "value": int(value),
                            "units": "day"
                    }
                elif key.lower() == 'insurance_annual':
                    self.inputs["insurance annual"] = {
                            "value": float(value),
                            "units": "euros"
                    }
                elif 'electricity_price' in key.lower():
                    if key.lower() == "electricity_price":
                        self.inputs["electricity price"] = {
                                "value": float(value),
                                "units": "euros/mwh"
                            }
                    elif 'pv' in key.lower():
                        self.inputs["electricity price pv"] = {
                                "value": float(value),
                                "units": "euros/mwh"
                            }
                    elif 'wec' in key.lower():
                        self.inputs["electricity price wec"] = {
                                "value": float(value),
                                "units": "euros/mwh"
                            }
                    elif 'wt' in key.lower():
                        self.inputs["electricity price wt"] = {
                                "value": float(value),
                                "units": "euros/mwh"
                            }
                elif key.lower() == 'technicians_year':
                    self.inputs["technicians year"] = {
                            "value": float(value),
                            "units": "euros"
                    }
                elif key.lower() == 'out_dir':
                    pass
                else:
                    logging.warning('Inputs.Cost: input "%s" not recognized. Ignored.' % key)
            logging.info('Inputs.Cost: inputs read from arguments')

        # Set values inside the inputs dict as direct attributes
        # from the Inputs class
        self.fuel_cost_hfo = self.inputs.get('fuel cost hfo')
        self.fuel_cost_mdo = self.inputs.get('fuel cost mdo')
        self.fuel_cost_mgo = self.inputs.get('fuel cost mgo')
        self.insurance_cost_year = self.inputs.get('insurance annual')
        self.port_cost_year = self.inputs.get('port cost year')
        self.merge = self.inputs.get("merge")
        self.time_between_merge = self.inputs.get("time between merge")
        self.electricity_price = self.inputs.get('electricity price')
        self.electricity_price_pv = self.inputs.get('electricity price pv')
        self.electricity_price_wec = self.inputs.get('electricity price wec')
        self.electricity_price_wt = self.inputs.get('electricity price wt')
        self.technicians_year = self.inputs.get('technicians year')

        if any([
            self.electricity_price_pv["value"] is not None,
            self.electricity_price_wt["value"] is not None,
            self.electricity_price_wec["value"] is not None
        ]):
            self.electricity_price_dict = {
                'pv': self.electricity_price_pv["value"],
                'wt': self.electricity_price_wt["value"],
                'wec': self.electricity_price_wec["value"]
            }
        else:
            if not self.electricity_price["value"]:
                self.electricity_price["value"] = 0
            self.electricity_price_dict = {
                'pv': self.electricity_price["value"],
                'wt': self.electricity_price["value"],
                'wec': self.electricity_price["value"]
            }


        self._check_attributes()

        # Save inputs as a YAML file
        out_dir = kwargs.get('out_dir')
        if out_dir is not None:
            inputs_to_yaml(self, out_dir, 'inputs_cost')


    def _check_attributes(self):
        """
        This method validates the attributes of the `Inputs.Cost` class to ensure they
        have valid values and fall within specified ranges.

        Raises errors if any attribute is outside the specified range.
        """
        if self.fuel_cost_hfo is not None and self.fuel_cost_hfo["value"] < 0:
            raise ValueError('"Fuel cost HFO" cannot be negative')
        if self.fuel_cost_mdo is not None and self.fuel_cost_mdo["value"] < 0:
            raise ValueError('"Fuel cost MDO" cannot be negative')
        if self.fuel_cost_mgo is not None and self.fuel_cost_mgo["value"] < 0:
            raise ValueError('"Fuel cost MGO" cannot be negative')
        if self.port_cost_year is not None and self.port_cost_year["value"] < 0:
            raise ValueError('"Dedicated port terminal annual cost" cannot be negative')
        if self.insurance_cost_year is not None and self.insurance_cost_year["value"] < 0:
            raise ValueError('"Insurance Cost per year" cannot be negative')
        if self.merge is True and self.time_between_merge is None:
            raise ValueError('If "Merge" is True the limit time between operaition must be defined')
        if self.technicians_year is not None and self.technicians_year["value"] < 0:
            raise ValueError('"Technicians Cost per year" cannot be negative')
        if self.electricity_price['value'] is not None and self.electricity_price["value"] < 0:
            raise ValueError('"Electricity Price" cannot be negative')
        if self.electricity_price_pv['value'] is not None and self.electricity_price_pv["value"] < 0:
            raise ValueError('"Electricity Price PV" cannot be negative')
        if self.electricity_price_wt['value'] is not None and self.electricity_price_wt["value"] < 0:
            raise ValueError('"Electricity Price WT" cannot be negative')
        if self.electricity_price_wec['value'] is not None and self.electricity_price_wec["value"] < 0:
            raise ValueError('"Electricity Price WEC" cannot be negative')
        if self.time_between_merge['value'] is not None and self.time_between_merge["value"] < 0:
            raise ValueError('"Time distance between operations to merge" cannot be negative')

        logging.debug('Inputs.Cost: attributes within ranges and valid.')


    def get_inputs(self):
        """Prints :class:`Inputs.Cost` to the command line."""
        for input, value in self.inputs.items():
            logging.info('%s - value: %s ; units: %s' % (input, value["value"], value["units"]))

