# tests/domain/forecasts/test_forecast_manager.py

import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, sentinel

import pandas as pd
import requests

import oriom.domain.Forecasts.Forecast_manager as forecast_manager_module


# ------------------------------------------------------------------
# Test doubles
# ------------------------------------------------------------------

class DummyForecast:
    """Minimal Forecast test double."""

    def __init__(self, type_forecast):
        self.type_forecast = type_forecast
        self.username = "test_user"
        self.password = "test_password"
        self.addr = "https://forecast.test/api"
        self.forecast_data = {
            "NAME_FILE_SAVE": ["forecast", "ensemble"],
            "NAME_FILE": ["main.dat", "ensemble.dat"],
            "DF_COLUMNS": [
                ["year", "month", "day", "hour", "hs", "tp"],
                ["year", "month", "day", "hour", "hs", "tp"],
            ],
            "FORECAST_COLUMNS_CONVERSION": [
                {"hs": "Hs", "tp": "Tp"},
                {"hs": "Hs", "tp": "Tp"},
            ],
        }


class DummyResponse:
    """Minimal HTTP response test double."""

    def __init__(self, text, raise_error=None):
        self.text = text
        self.raise_error = raise_error

    def raise_for_status(self):
        if self.raise_error:
            raise self.raise_error


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

class TestForecastManagerInit(unittest.TestCase):
    """Tests for Forecast_manager.__init__."""

    @patch.object(forecast_manager_module.Forecast_manager, "retrieve_forecast_data")
    @patch.object(forecast_manager_module, "Forecast", DummyForecast)
    def test_init_sets_attributes_and_retrieves_forecast_data(self, mock_retrieve_forecast_data):
        """The constructor should initialise attributes and trigger forecast retrieval."""
        forecast_user_data = {
            "type_forecast": "ipma",
            "name_point": "previsao_AB_",
        }

        manager = forecast_manager_module.Forecast_manager(
            forecast_user_data=forecast_user_data,
            save_dir="fake/save/dir",
        )

        self.assertEqual(manager.type_forecast, "ipma")
        self.assertEqual(manager.name_point, "previsao_AB_")
        self.assertEqual(manager.save_dir, "fake/save/dir")
        self.assertTrue(manager.forecast_df.empty)
        self.assertTrue(manager.ensamble_df.empty)
        self.assertEqual(manager.timeseries_file, "")

        mock_retrieve_forecast_data.assert_called_once()

        retrieved_date = mock_retrieve_forecast_data.call_args.args[0]
        self.assertEqual(retrieved_date, date.today())


class TestRetrieveForecastData(unittest.TestCase):
    """Tests for Forecast_manager.retrieve_forecast_data."""

    def create_manager_without_init(self):
        """Create a Forecast_manager instance without running __init__."""
        manager = forecast_manager_module.Forecast_manager.__new__(
            forecast_manager_module.Forecast_manager
        )
        manager.type_forecast = "ipma"
        manager.forecast = DummyForecast(type_forecast="ipma")
        manager.name_point = "previsao_AB_"
        manager.save_dir = "fake/save/dir"
        manager.forecast_df = pd.DataFrame()
        manager.ensamble_df = pd.DataFrame()
        manager.timeseries_file = ""
        return manager

    @patch.object(forecast_manager_module, "save_file_csv")
    @patch.object(forecast_manager_module.requests, "Session")
    def test_retrieve_forecast_data_downloads_parses_interpolates_and_saves(
        self,
        mock_session_class,
        mock_save_file_csv,
    ):
        """
        retrieve_forecast_data should:
        - create an authenticated session
        - download forecast and ensemble files
        - convert forecast columns into ORIOM columns
        - interpolate missing hourly timestamps
        - save the forecast dataframe
        """
        manager = self.create_manager_without_init()

        main_forecast_text = (
            "2026 7 10 0 1.0 8.0\n"
            "2026 7 10 2 3.0 10.0\n"
        )

        ensemble_forecast_text = (
            "2026 7 10 0 2.0 9.0\n"
            "2026 7 10 1 4.0 11.0\n"
        )

        mock_session = MagicMock()
        mock_session.get.side_effect = [
            DummyResponse(main_forecast_text),
            DummyResponse(ensemble_forecast_text),
        ]
        mock_session_class.return_value = mock_session

        manager.retrieve_forecast_data(today=date(2026, 7, 10))

        self.assertEqual(mock_session.auth, ("test_user", "test_password"))

        self.assertEqual(mock_session.get.call_count, 2)
        self.assertEqual(
            mock_session.get.call_args_list[0].args[0],
            "https://forecast.test/api/forecast_previsao_AB__main.dat",
        )
        self.assertEqual(
            mock_session.get.call_args_list[1].args[0],
            "https://forecast.test/api/ensemble_previsao_AB__ensemble.dat",
        )

        expected_index = pd.to_datetime(
            [
                "2026-07-10 00:00:00",
                "2026-07-10 01:00:00",
                "2026-07-10 02:00:00",
            ]
        )

        self.assertEqual(manager.forecast_df.index.tolist(), expected_index.tolist())
        self.assertEqual(manager.forecast_df["Hs"].tolist(), [1.0, 2.0, 3.0])
        self.assertEqual(manager.forecast_df["Tp"].tolist(), [8.0, 9.0, 10.0])
        self.assertEqual(manager.forecast_df["cs"].tolist(), [0, 0, 0])

        ensemble_index = pd.to_datetime(
            [
                "2026-07-10 00:00:00",
                "2026-07-10 01:00:00",
            ]
        )

        self.assertEqual(manager.ensamble_df.index.tolist(), ensemble_index.tolist())
        self.assertEqual(manager.ensamble_df["Hs"].tolist(), [2.0, 4.0])
        self.assertEqual(manager.ensamble_df["Tp"].tolist(), [9.0, 11.0])

        self.assertEqual(
            manager.timeseries_file,
            "fake/save/dir/forecast_previsao_AB__main.dat.csv",
        )

        self.assertEqual(mock_save_file_csv.call_count, 2)

        mock_save_file_csv.assert_any_call(
            df_to_save=manager.forecast_df,
            save_dir="fake/save/dir/forecast_previsao_AB__main.dat.csv",
            indexing=True,
        )

        mock_save_file_csv.assert_any_call(
            df_to_save=manager.forecast_df,
            save_dir="fake/save/dir/ensemble_previsao_AB__ensemble.dat.csv",
            indexing=True,
        )

    @patch.object(forecast_manager_module, "save_file_csv")
    @patch.object(forecast_manager_module.requests, "Session")
    def test_retrieve_forecast_data_logs_request_errors_without_raising(
        self,
        mock_session_class,
        mock_save_file_csv,
    ):
        """Request errors should be logged and should not be raised."""
        manager = self.create_manager_without_init()

        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.RequestException("download failed")
        mock_session_class.return_value = mock_session

        with self.assertRaises(FileExistsError):
            manager.retrieve_forecast_data(today=date(2026, 7, 10))

        mock_save_file_csv.assert_not_called()

    @patch.object(forecast_manager_module, "save_file_csv")
    @patch.object(forecast_manager_module.requests, "Session")
    def test_retrieve_forecast_data_logs_unexpected_processing_errors_without_raising(
        self,
        mock_session_class,
        mock_save_file_csv,
    ):
        """Unexpected processing errors should be logged and should not be raised."""
        manager = self.create_manager_without_init()

        invalid_forecast_text = (
            "2026 7 10 0 1.0\n"
        )

        mock_session = MagicMock()
        mock_session.get.side_effect = [
            DummyResponse(invalid_forecast_text),
            DummyResponse(invalid_forecast_text),
        ]
        mock_session_class.return_value = mock_session

        with self.assertRaises(FileExistsError):
            manager.retrieve_forecast_data(today=date(2026, 7, 10))

        mock_save_file_csv.assert_not_called()

    @patch.object(forecast_manager_module, "save_file_csv")
    @patch.object(forecast_manager_module.requests, "Session")
    def test_retrieve_forecast_data_warns_when_forecast_is_longer_than_three_days(
        self,
        mock_session_class,
        mock_save_file_csv,
    ):
        """A warning should be logged when the main forecast contains more than three days."""
        manager = self.create_manager_without_init()

        rows = []
        forecast_index = pd.date_range(
            start="2026-07-10 00:00:00",
            periods=74,
            freq="1h",
        )

        for timestamp in forecast_index:
            rows.append(
                f"{timestamp.year} {timestamp.month} {timestamp.day} {timestamp.hour} 1.0 8.0"
            )

        long_forecast_text = "\n".join(rows)

        ensemble_forecast_text = (
            "2026 7 10 0 2.0 9.0\n"
            "2026 7 10 1 3.0 10.0\n"
        )

        mock_session = MagicMock()
        mock_session.get.side_effect = [
            DummyResponse(long_forecast_text),
            DummyResponse(ensemble_forecast_text),
        ]
        mock_session_class.return_value = mock_session

        manager.retrieve_forecast_data(today=date(2026, 7, 10))

        self.assertEqual(len(manager.forecast_df), 74)
        self.assertEqual(mock_save_file_csv.call_count, 2)


class TestInterpolateHourlyForecast(unittest.TestCase):
    """Tests for Forecast_manager.interpolate_hourly_forecast."""

    def create_manager_without_init(self):
        """Create a Forecast_manager instance without running __init__."""
        return forecast_manager_module.Forecast_manager.__new__(
            forecast_manager_module.Forecast_manager
        )

    def test_interpolate_hourly_forecast_returns_unchanged_dataframe_when_index_is_hourly(self):
        """Hourly forecast data should be returned unchanged."""
        manager = self.create_manager_without_init()

        index = pd.to_datetime(
            [
                "2026-07-10 00:00:00",
                "2026-07-10 01:00:00",
                "2026-07-10 02:00:00",
            ]
        )

        input_df = pd.DataFrame(
            {
                "Hs": [1.0, 2.0, 3.0],
                "Tp": [8.0, 9.0, 10.0],
            },
            index=index,
        )

        result = manager.interpolate_hourly_forecast(input_df)

        pd.testing.assert_frame_equal(result, input_df)

    def test_interpolate_hourly_forecast_adds_missing_timestamps_and_interpolates(self):
        """Missing hourly timestamps should be inserted and linearly interpolated."""
        manager = self.create_manager_without_init()

        index = pd.to_datetime(
            [
                "2026-07-10 00:00:00",
                "2026-07-10 02:00:00",
            ]
        )

        input_df = pd.DataFrame(
            {
                "Hs": [1.0, 3.0],
                "Tp": [8.0, 10.0],
            },
            index=index,
        )

        result = manager.interpolate_hourly_forecast(input_df)

        expected_index = pd.to_datetime(
            [
                "2026-07-10 00:00:00",
                "2026-07-10 01:00:00",
                "2026-07-10 02:00:00",
            ]
        )

        expected_df = pd.DataFrame(
            {
                "Hs": [1.0, 2.0, 3.0],
                "Tp": [8.0, 9.0, 10.0],
            },
            index=expected_index,
        )

        pd.testing.assert_frame_equal(result, expected_df, check_freq=False)

if __name__ == "__main__":
    unittest.main(verbosity=2)