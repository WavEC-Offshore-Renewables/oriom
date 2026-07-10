import io
import logging
import os
from datetime import datetime
import pandas as pd
import requests
from dotenv import load_dotenv

from oriom.utils.aux_functions import save_file_csv
from oriom.domain.Forecasts.Forecast import Forecast

load_dotenv()

class Forecast_manager:
    """
    Class to handle forecast data retrieval and processing.

    Attributes:
        type_forecast (str): Type of forecast selected
        username (str): Username of the account for forecast API
        password (str): Passkey of the account for forecast API
        addr (str): URL of the forecast API
        save_dir (str): Path of the folder on which store the forecast data
        forecast_df (pd.DataFrame): Dataframe of the Forecast data
        forecast_df (pd.DataFrame): Dataframe of the Ensemble Forecast data
        timeseries_file (str): Path of the Forecast file saved
        forecast_user_data (dict): Dict of Forecast User data containing Type of forecast selected and point selected

    """

    def __init__(self, forecast_user_data: dict, save_dir:str):
        self.type_forecast = forecast_user_data['type_forecast']
        self.forecast = Forecast(type_forecast = self.type_forecast)
        self.name_point = forecast_user_data['name_point']

        self.save_dir = save_dir
        self.forecast_df = pd.DataFrame()
        self.ensamble_df = pd.DataFrame()
        self.timeseries_file = r''
        
        self.retrieve_forecast_data(datetime.now().date())
    

    def retrieve_forecast_data(self, today: datetime) -> pd.DataFrame:
        """
        Download forecast data and ensamble for a given date, modify columns, save it locally,
        and return it as a pandas DataFrame.

        Args:
            today (datetime): Forecast date of the actual day.
        """

        session = requests.Session()
        session.auth = (self.forecast.username, self.forecast.password)

        for i in range(0, len(self.forecast.forecast_data['NAME_FILE_SAVE'])):
            file_forecast_name = f"{self.forecast.forecast_data['NAME_FILE_SAVE'][i]}_{self.name_point}_{self.forecast.forecast_data['NAME_FILE'][i]}"
            forecast_url = os.path.join(self.forecast.addr, file_forecast_name).replace("\\", "/")
            url_save_file = os.path.join(self.save_dir, f"{file_forecast_name}.csv").replace("\\", "/")

            df_metocean_file = pd.DataFrame()

            # File retrival
            try:
                response = session.get(forecast_url, timeout=30)
                response.raise_for_status()
                forecast_df = pd.read_csv(io.StringIO(response.text), delim_whitespace=True, header=None)

                # Dataframe construction
                forecast_df.columns = self.forecast.forecast_data['DF_COLUMNS'][i]
                df_metocean_file["datetime"] = pd.to_datetime(forecast_df[["year", "month", "day", "hour"]])
                for col_FORECAST, col_ORIOM in self.forecast.forecast_data['FORECAST_COLUMNS_CONVERSION'][i].items():
                    df_metocean_file[col_ORIOM] = forecast_df[col_FORECAST]
                df_metocean_file.set_index("datetime", inplace=True)
                df_metocean_file = self.interpolate_hourly_forecast(df_metocean_file = df_metocean_file)

                # Df save
                if i == 0:
                    self.forecast_df = df_metocean_file
                    self.forecast_df['cs'] = 0
                    self.timeseries_file = url_save_file
                    if len(self.forecast_df) > 24*3:
                        logging.warning('Forecast: The forecast retrrived consider more then 3 days forecast. Accuracy of such metocean data are weak')
                else:
                    self.ensamble_df = df_metocean_file

                save_file_csv(df_to_save = self.forecast_df, save_dir = url_save_file, indexing = True)

                logging.info(f"Forecast data successfully saved to {url_save_file}")

            except requests.exceptions.RequestException as exc:
                e_ = "Failed to download forecast data for %s: %s. ST O&M not considered", self.forecast.forecast_data['NAME_FILE'][i], exc
                logging.error(e_)
                raise FileExistsError(e_)
            except Exception as exc:
                e_ ="Unexpected error while processing forecast data for %s: %s. ST O&M not considered", self.forecast.forecast_data['NAME_FILE'][i], exc
                logging.exception(e_)
                raise FileExistsError(e_)

    def interpolate_hourly_forecast(self, df_metocean_file: pd.DataFrame):
        """
        Ensure the forecast has an hourly timestep. Missing timestamps are inserted and interpolated.

        Args:
            df_metocean_file (pd.DataFrame): Forecast dataframe with columns
        """

        forecast_df = df_metocean_file.copy()

        # Expected hourly index
        expected_index = pd.date_range(start=forecast_df.index.min(), end=forecast_df.index.max(), freq="1h")

        missing_dates = expected_index.difference(forecast_df.index)

        if len(missing_dates) > 0:

            first_missing = missing_dates[0]
            days_from_start = (first_missing - forecast_df.index.min()).total_seconds() / 86400
            logging.warning(f"Forecast timestep is not hourly. Interpolated missing timestamps Starting from {days_from_start:.2f} days after first timestamp.")

            forecast_df = forecast_df.reindex(expected_index)
            # Interpolate numeric columns
            forecast_df = forecast_df.interpolate(method="linear")

        return forecast_df
    
if __name__ == "__main__":
    pass
    