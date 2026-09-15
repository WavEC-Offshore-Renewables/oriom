import io
import logging
import os
import pandas as pd
import requests

from oriom.common import constants_forecast
from oriom.utils.aux_functions import save_file_csv


class Forecast:
    """
    Class to handle forecast data retrieval and processing.

    Attributes:
        forecast_tipe (str): Forecast to be used
        forecast_data (dict): Forecast column and files data
    """

    def __init__(self, type_forecast: str):
        self.type_forecast = type_forecast
        self.forecast_access()
        self.forecast_finder()


    def forecast_access(self):
        """
        Find the forecast access data to be used.

        Raise:
            ValueError: If type of data not found
        """
        
        self.username = os.getenv(f"{self.type_forecast}_USERNAME")
        self.password = os.getenv(f"{self.type_forecast}_PASSWORD")
        self.addr = os.getenv(f"{self.type_forecast}_URL")
        if any(value is None for value in [
            self.username,
            self.password,
            self.addr,
        ]):
            e_ = f"Forecast: Missing environment variable for forecast type '{self.type_forecast}'"
            logging.error(e_)
            raise ValueError(e_)


    def forecast_finder(self):
        """
        Find the forecast data to be used.

        Raise:
            ValueError: If type of data not found
        """

        try:
            self.forecast_data = getattr(constants_forecast, self.type_forecast)
        except AttributeError:
            e_ = f"Forecast: Forecast type '{self.type_forecast}' does not exist ""in constants_forecast."
            logging.error(e_)
            raise ValueError(e_)