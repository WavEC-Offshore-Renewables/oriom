import io
import logging
import os
import warnings
from datetime import datetime
import pandas as pd
import requests

from oriom.common.constants import FORECAST_ARIA_COLUMNS, METOCEAN_FORECAST_COLUMNS_CONVERSION
from oriom.utils.aux_functions import save_file_csv


class Forecast:
    """
    Class to handle forecast data retrieval and processing.

    Attributes:
        username (str): Username of the account for forecast API
        password (str): Passkey of the account for forecast API
        name_point (str): Name of the point location to retrive
        addr (str): URL of the forecast API
        save_dir (str): Path of the folder on which store the forecast data
        forecast_df (pd.DataFrame): Dataframe of the Forecast data
        timeseries_file (str): Path of the Forecast file saved
    """

    def __init__(self, forecast_client: str, forecast_password: str, name_point: str, addr: str, save_dir:str):
        self.username = forecast_client
        self.password = forecast_password
        self.name_point = name_point
        self.addr = addr
        self.save_dir = save_dir
        self.forecast_df = pd.DataFrame()
        self.timeseries_file = r''
        
        self.retrieve_forecast_data(datetime.now().date())


    def retrieve_forecast_data(self, today: datetime) -> pd.DataFrame:
        """
        Download forecast data for a given date, save it locally,
        and return it as a pandas DataFrame.

        Args:
            today (datetime): Forecast date of the actual day.
        """

        date_str = today.strftime("%Y%m%d")
        file_name = f"{date_str}.dat"

        forecast_url = os.path.join(self.addr, f"previsao_AB_{file_name}")
        forecast_url = forecast_url.replace("\\", "/")

        session = requests.Session()
        session.auth = (self.username, self.password)

        try:
            response = session.get(forecast_url, timeout=30)
            response.raise_for_status()

            forecast_df = pd.read_csv(io.StringIO(response.text), delim_whitespace=True, header=None)
            forecast_df.columns = FORECAST_ARIA_COLUMNS

            self.forecast_df["datetime"] = pd.to_datetime(forecast_df[["year", "month", "day", "hour"]])
            for col_FORECAST, col_ORIOM in METOCEAN_FORECAST_COLUMNS_CONVERSION.items():
                self.forecast_df[col_ORIOM] = forecast_df[col_FORECAST]
            self.forecast_df['cs'] = 0
            
            self.forecast_df.set_index("datetime", inplace=True)

            self.timeseries_file = os.path.join(self.save_dir, f"{self.name_point+date_str}.csv")

            save_file_csv(df_to_save = self.forecast_df, save_dir = self.timeseries_file, indexing = True)

            logging.info(f"Forecast data successfully saved to {self.save_dir + self.name_point +'.csv'}")

        except requests.exceptions.RequestException as exc:
            logging.error("Failed to download forecast data for %s: %s", date_str,exc)

        except Exception as exc:
            logging.exception("Unexpected error while processing forecast data for %s: %s", date_str, exc)


if __name__ == "__main__":
    pass
    