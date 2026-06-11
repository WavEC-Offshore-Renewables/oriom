# Import packages
import os
import pandas as pd
import logging
from ruamel.yaml import YAML


class Scenario():
    """Scenario class.

    Note:
        The scenario defines per month a probability. A higher probability leads to a higher likelihood
        of failure events happening. These probabilities are used as weights when randomly deciding when the
        failure events are occurring.

    Attributes:
        scenario(:obj:`str`): The scenario to be represented.
            Six scenarios available:

                - Scenario 0: Every month has the same percentages of occurence of failures;
                - Scenario 1: Worst case scenario: 60 % of the failure events occurs between November and February, 40 % occurs in the rest of the year;
                - Scenario 2: Best case scenario: 60% of the failure events occurs between May and August, 40% in the rest of the year;
                - Scenario 3: Based on the report from Evolve Consortium, the percentages are obtained based on proportions of the wind speed peaks;
                - Scenario 4: Scenario to be tested;
                - Scenario 5:Scenario to be tested
        probability(:obj:`dict`): The probability of failure per month.
            **keys**: *months*: :obj:`float`
    """
    def __init__(
            self,
            scenario: str,
            jan: float,
            feb: float,
            mar: float,
            apr: float,
            may: float,
            jun: float,
            jul: float,
            aug: float,
            sep: float,
            oct: float,
            nov: float,
            dec: float
    ):
        """Initializes :class:'Scenario' class.

        Args:
            scenario(:obj:`int`): The scenario to be represented.
            jan (:obj:`float`): Probability of failure for January.
            feb (:obj:`float`): Probability of failure for February.
            mar (:obj:`float`): Probability of failure for March.
            apr (:obj:`float`): Probability of failure for April.
            mai (:obj:`float`): Probability of failure for Mai.
            jun (:obj:`float`): Probability of failure for June.
            jul (:obj:`float`): Probability of failure for July.
            aug (:obj:`float`): Probability of failure for August.
            sep (:obj:`float`): Probability of failure for September.
            oct (:obj:`float`): Probability of failure for October.
            nov (:obj:`float`): Probability of failure for November.
            dec (:obj:`float`): Probability of failure for December.
        """
        self.scenario = int(scenario)
        self.probability = {
                "jan": float(jan),
                "feb": float(feb),
                "mar": float(mar),
                "apr": float(apr),
                "may": float(may),
                "jun": float(jun),
                "jul": float(jul),
                "aug": float(aug),
                "sep": float(sep),
                "oct": float(oct),
                "nov": float(nov),
                "dec": float(dec)
        }
        self.percentage_month = [
                float(jan),
                float(feb),
                float(mar),
                float(apr),
                float(may),
                float(jun),
                float(jul),
                float(aug),
                float(sep),
                float(oct),
                float(nov),
                float(dec)
        ]
        self._check_inputs()

    def _check_inputs(self):
        """
        This method validates the attributes of the `Scenario` class to ensure they
        have valid values and fall within specified ranges.

        Raises errors if any attribute is outside the specified range.
        """
        percentage_month = 0
        for month, prob in self.probability.items():
            if prob < 0:
                logging.error('Percentage of %s cannot be negative' % month)
                raise ValueError('Percentage of %s cannot be negative' % month)
            percentage_month += prob

        if round(sum(self.percentage_month),6) != 1:
            logging.error('The sum of the percentages must be equal to 1')
            raise ValueError('The sum of the percentages must be equal to 1')

    def get_scenarios_from_yaml(file_path: str)-> dict:
        """Returns a dict of :class:`Scenario` based on a YAML file.

       Args:
           file_path (:obj:`str`): YAML file path with scenarios.

        Raises:
            KeyError: if some of the mandatory keys of YAML are
                not provided.

        Returns:
           :obj:`dict`: :obj:`dict` of :class:`Scenario`.
        """
        # Gets scenarios from a YAML file
        f_yaml = open(os.path.join(file_path), 'r')
        yaml = YAML(typ='safe')
        scenarios_yaml = yaml.load(f_yaml)
        f_yaml.close()
        # All scenarios keys to lower case
        scenarios_yaml = [
                {key.lower(): val for key, val in scenario.items()}
                for scenario in scenarios_yaml
        ]

        keys_mandatory = [
                'scenarios',
                'january',
                'february',
                'march',
                'april',
                'may',
                'june',
                'july',
                'august',
                'september',
                'october',
                'november',
                'december'
        ]

        scenarios_dict = {}
        for scenario in scenarios_yaml:
            if any([
                    key not in scenario.keys()
                    for key in keys_mandatory
            ]) is True:
                _e = '"scenarios", "january", "february", "march", "april", '
                _e += '"may", "june", "july", "august", "september", '
                _e += '"october", "november" and "december" are mandatory '
                _e += 'keys.'
                logging.error('Scenario: ' + _e)
                raise KeyError(_e)
            scenarios_dict[scenario["scenarios"]] = (Scenario(
                    scenario=scenario["scenarios"],
                    jan=scenario["january"],
                    feb=scenario["february"],
                    mar=scenario["march"],
                    apr=scenario["april"],
                    may=scenario["may"],
                    jun=scenario["june"],
                    jul=scenario["july"],
                    aug=scenario["august"],
                    sep=scenario["september"],
                    oct=scenario["october"],
                    nov=scenario["november"],
                    dec=scenario["december"]
            ))

        logging.info('Scenario: scenarios read from file: "%s".' % file_path)
        return scenarios_dict


    def create_equal_scenarios()-> dict:
        """Returns a dict of :class:`Scenario` based with equal probabilities.

        Returns:
           :obj:`dict`: :obj:`dict` of :class:`Scenario`.
        """
        scenarios_dict = {}
        for scenario in range(1):

            scenarios_dict[scenario] = (Scenario(
                    scenario=0,
                    jan=1/12,
                    feb=1/12,
                    mar=1/12,
                    apr=1/12,
                    may=1/12,
                    jun=1/12,
                    jul=1/12,
                    aug=1/12,
                    sep=1/12,
                    oct=1/12,
                    nov=1/12,
                    dec=1/12
            ))

        return scenarios_dict

if __name__ == '__main__':

    file_path = os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'scenarios.yaml')
    scenarios = Scenario.get_scenarios_from_yaml(file_path)
