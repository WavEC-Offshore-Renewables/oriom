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

    def __init__(self, type_forecast: str, name_point: str, save_dir: str):
        self.type_forecast = type_forecast
        self.name_point = name_point
        self.save_dir = save_dir
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
        
            
        
    def IPMA_forecast_retrive(self, forecast_date: str, save_name: str, date_format = '%Y%m%d'):
        """ 
        Retrive data from forecast. 
        Try 2 attempts considering actual and previous date in case odiern forecast not ready

        Raise:
            RuntimeError: if any exceptions occurs
        """
        session = requests.Session()
        session.auth = (self.username, self.password)
        
        forecast_found = False
        # Iterate for exact day or previous day if forecast did not exit yet
        for day_offset in range(150):
            date_trial = (forecast_date-pd.Timedelta(days=day_offset)).strftime(date_format)
                
            file_forecast_name = f"{save_name}_{self.name_point}_{date_trial}.dat"
            forecast_url = os.path.join(self.addr, file_forecast_name).replace("\\", "/")
            url_save_file = os.path.join(self.save_dir, f"{file_forecast_name}.csv").replace("\\", "/")

            # File retrival
            try:
                response = session.get(forecast_url, timeout=30)
                response.raise_for_status()
                forecast_df = pd.read_csv(io.StringIO(response.text), delim_whitespace=True, header=None)
                forecast_found = True
                break
            except requests.exceptions.RequestException as exc:
                if day_offset == 150:
                    e_ = f"Failed to download forecast data for "f"{forecast_date}: {exc}\n{forecast_url}"
                    logging.error(e_)
                    raise RuntimeError(e_)
            except Exception as exc:
                if day_offset == 150:
                    e_ = f"Unexpected error while processing forecast data for {forecast_date}: {exc}. ST O&M not considered"
                    logging.exception(e_)
                    raise RuntimeError(e_)
        if not forecast_found:
            raise RuntimeError(f"Failed to download forecast data for {forecast_date-pd.Timedelta(days=day_offset)}")
        return forecast_df, url_save_file