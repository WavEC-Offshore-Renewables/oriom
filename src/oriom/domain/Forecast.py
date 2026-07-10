import io
import logging
import os
import warnings
from datetime import datetime
import pandas as pd
import requests

from oriom.common import constants
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
        forecast_df (pd.DataFrame): Dataframe of the Ensemble Forecast data
        timeseries_file (str): Path of the Forecast file saved
    """

    def __init__(self, forecast_client: str, forecast_password: str, name_point: str, addr: str, save_dir:str):
        self.username = forecast_client
        self.password = forecast_password
        self.name_point = name_point
        self.addr = addr
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

        date_str = today.strftime("%Y%m%d")
        file_name = f"{date_str}.dat"
        name_file_save_list = ['previsao', 'listagem_ens']

        forecast_url_prevision = os.path.join(self.addr, f"previsao_{self.name_point}_{file_name}")
        forecast_url_ensamble = os.path.join(self.addr, f"listagem_ens_{self.name_point}_{file_name}")

        session = requests.Session()
        session.auth = (self.username, self.password)

        for forecast_url, IPMA_COL, IPMA_TRANSFORMATION_COL, PREVISION, name_file_save in zip(
            [forecast_url_prevision, forecast_url_ensamble],
            [constants.FORECAST_ARIA_COLUMNS, constants.ENSAMBLE_ARIA_COLUMNS],
            [constants.METOCEAN_FORECAST_COLUMNS_CONVERSION, constants.METOCEAN_ENSAMBLE_COLUMNS_CONVERSION],
            [True, False],
            name_file_save_list
        ):
            forecast_url = forecast_url.replace("\\", "/")
            df_metocean_file = pd.DataFrame()
            url_save_file = os.path.join(self.save_dir, f"{name_file_save + '_' + self.name_point + '_' + date_str}.csv")

            try:
                # File retrival
                response = session.get(forecast_url, timeout=30)
                response.raise_for_status()
                forecast_df = pd.read_csv(io.StringIO(response.text), delim_whitespace=True, header=None)

                # Dataframe construction
                forecast_df.columns = IPMA_COL
                df_metocean_file["datetime"] = pd.to_datetime(forecast_df[["year", "month", "day", "hour"]])
                for col_FORECAST, col_ORIOM in IPMA_TRANSFORMATION_COL.items():
                    df_metocean_file[col_ORIOM] = forecast_df[col_FORECAST]
                df_metocean_file.set_index("datetime", inplace=True)

                # Df save
                if PREVISION:
                    self.forecast_df = df_metocean_file
                    self.forecast_df['cs'] = 0
                    self.timeseries_file = url_save_file
                    save_file_csv(df_to_save = self.forecast_df, save_dir = self.timeseries_file, indexing = True)
                else:
                    self.ensamble_df = df_metocean_file
                    save_file_csv(df_to_save = self.forecast_df, save_dir = url_save_file, indexing = True)

                logging.info(f"Forecast data successfully saved to {url_save_file}")

            except requests.exceptions.RequestException as exc:
                logging.error("Failed to download forecast data for %s: %s", date_str,exc)

            except Exception as exc:
                logging.exception("Unexpected error while processing forecast data for %s: %s", date_str, exc)


if __name__ == "__main__":
    pass
    