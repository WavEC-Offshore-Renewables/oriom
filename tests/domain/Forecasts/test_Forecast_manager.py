# tests/domain/forecasts/test_forecast_manager.py

import unittest
from unittest.mock import MagicMock, patch

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
            "NAME_FILE": pd.Timestamp("2026-07-10"),
            "DF_COLUMNS": [
                ["year", "month", "day", "hour", "hs", "tp"],
                ["year", "month", "day", "hour", "hs", "tp"],
            ],
            "FORECAST_COLUMNS_CONVERSION": [
                {"hs": "Hs", "tp": "Tp"},
                {"hs": "Hs", "tp": "Tp"},
            ],
        }


class DummyForecastWithoutColumnConversion:
    """Minimal Forecast test double without predefined forecast column conversion."""

    def __init__(self, type_forecast):
        self.type_forecast = type_forecast
        self.username = "test_user"
        self.password = "test_password"
        self.addr = "https://forecast.test/api"
        self.forecast_data = {
            "NAME_FILE_SAVE": ["forecast", "ensemble"],
            "NAME_FILE": pd.Timestamp("2026-07-10"),
            "DF_COLUMNS": [
                ["year", "month", "day", "hour", "Hs", "Tp"],
                ["year", "month", "day", "hour", "Hs", "Tp"],
            ],
            "FORECAST_COLUMNS_CONVERSION": [
                {},
                {},
            ],
        }


class DummyResponse:
    """Minimal HTTP response test double."""

    def __init__(self, text, raise_error=None):
        self.text = text
        self.raise_error = raise_error

    def raise_for_status(self):
        """Raise the configured HTTP error, if any."""
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

        mock_retrieve_forecast_data.assert_called_once_with()


class TestRetrieveForecastData(unittest.TestCase):
    """Tests for Forecast_manager.retrieve_forecast_data."""

    def create_manager_without_init(self, forecast_class=DummyForecast):
        """Create a Forecast_manager instance without running __init__."""
        manager = forecast_manager_module.Forecast_manager.__new__(
            forecast_manager_module.Forecast_manager
        )
        manager.type_forecast = "ipma"
        manager.forecast = forecast_class(type_forecast="ipma")
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
        - save forecast and ensemble dataframes
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

        manager.retrieve_forecast_data()

        self.assertEqual(mock_session.auth, ("test_user", "test_password"))

        self.assertEqual(mock_session.get.call_count, 2)
        self.assertEqual(
            mock_session.get.call_args_list[0].args[0],
            "https://forecast.test/api/forecast_previsao_AB__20260710.dat",
        )
        self.assertEqual(
            mock_session.get.call_args_list[1].args[0],
            "https://forecast.test/api/ensemble_previsao_AB__10072026.dat",
        )

        expected_forecast_index = pd.date_range(
            start="2026-07-10 00:00:00",
            end="2026-07-10 02:00:00",
            freq="1h",
        )

        self.assertEqual(manager.forecast_df.index.tolist(), expected_forecast_index.tolist())
        self.assertEqual(manager.forecast_df["Hs"].tolist(), [1.0, 2.0, 3.0])
        self.assertEqual(manager.forecast_df["Tp"].tolist(), [8.0, 9.0, 10.0])
        self.assertEqual(manager.forecast_df["cs"].tolist(), [0, 0, 0])

        expected_ensemble_index = pd.date_range(
            start="2026-07-10 00:00:00",
            end="2026-07-10 01:00:00",
            freq="1h",
        )

        self.assertEqual(manager.ensamble_df.index.tolist(), expected_ensemble_index.tolist())
        self.assertEqual(manager.ensamble_df["Hs"].tolist(), [2.0, 4.0])
        self.assertEqual(manager.ensamble_df["Tp"].tolist(), [9.0, 11.0])

        self.assertEqual(
            manager.timeseries_file,
            "fake/save/dir/forecast_previsao_AB__20260710.dat.csv",
        )

        self.assertEqual(mock_save_file_csv.call_count, 2)

        first_save_call = mock_save_file_csv.call_args_list[0]
        second_save_call = mock_save_file_csv.call_args_list[1]

        self.assertEqual(
            first_save_call.kwargs["save_dir"],
            "fake/save/dir/forecast_previsao_AB__20260710.dat.csv",
        )
        self.assertFalse(first_save_call.kwargs["indexing"])

        expected_saved_forecast_df = manager.forecast_df.rename_axis("datetime").reset_index()
        pd.testing.assert_frame_equal(
            first_save_call.kwargs["df_to_save"],
            expected_saved_forecast_df,
        )

        self.assertEqual(
            second_save_call.kwargs["save_dir"],
            "fake/save/dir/ensemble_previsao_AB__10072026.dat.csv",
        )
        self.assertFalse(second_save_call.kwargs["indexing"])

        expected_saved_ensemble_df = manager.ensamble_df.rename_axis("datetime").reset_index()
        pd.testing.assert_frame_equal(
            second_save_call.kwargs["df_to_save"],
            expected_saved_ensemble_df,
        )

    @patch.object(forecast_manager_module, "save_file_csv")
    @patch.object(forecast_manager_module.requests, "Session")
    def test_retrieve_forecast_data_uses_previous_day_when_current_day_is_unavailable(
        self,
        mock_session_class,
        mock_save_file_csv,
    ):
        """retrieve_forecast_data should retry with the previous day when the current day is unavailable."""
        manager = self.create_manager_without_init()

        main_forecast_text = (
            "2026 7 9 0 1.0 8.0\n"
            "2026 7 9 1 2.0 9.0\n"
        )

        ensemble_forecast_text = (
            "2026 7 10 0 2.0 9.0\n"
            "2026 7 10 1 4.0 11.0\n"
        )

        mock_session = MagicMock()
        mock_session.get.side_effect = [
            DummyResponse(
                "",
                raise_error=requests.exceptions.HTTPError("current forecast not ready"),
            ),
            DummyResponse(main_forecast_text),
            DummyResponse(ensemble_forecast_text),
        ]
        mock_session_class.return_value = mock_session

        manager.retrieve_forecast_data()

        self.assertEqual(mock_session.get.call_count, 3)

        self.assertEqual(
            mock_session.get.call_args_list[0].args[0],
            "https://forecast.test/api/forecast_previsao_AB__20260710.dat",
        )
        self.assertEqual(
            mock_session.get.call_args_list[1].args[0],
            "https://forecast.test/api/forecast_previsao_AB__20260709.dat",
        )
        self.assertEqual(
            mock_session.get.call_args_list[2].args[0],
            "https://forecast.test/api/ensemble_previsao_AB__10072026.dat",
        )

        self.assertEqual(
            manager.timeseries_file,
            "fake/save/dir/forecast_previsao_AB__20260709.dat.csv",
        )

        self.assertEqual(mock_save_file_csv.call_count, 2)

    @patch.object(forecast_manager_module, "save_file_csv")
    @patch.object(forecast_manager_module.requests, "Session")
    def test_retrieve_forecast_data_raises_runtime_error_after_two_request_failures(
        self,
        mock_session_class,
        mock_save_file_csv,
    ):
        """Request errors should raise RuntimeError after both current-day and previous-day attempts fail."""
        manager = self.create_manager_without_init()

        mock_session = MagicMock()
        mock_session.get.side_effect = requests.exceptions.RequestException("download failed")
        mock_session_class.return_value = mock_session

        with self.assertRaises(RuntimeError) as context:
            manager.retrieve_forecast_data()

        self.assertIn("Failed to download forecast data", str(context.exception))
        self.assertEqual(mock_session.get.call_count, 2)
        mock_save_file_csv.assert_not_called()


    @patch.object(forecast_manager_module, "save_file_csv")
    @patch.object(forecast_manager_module.pd, "read_csv")
    @patch.object(forecast_manager_module.requests, "Session")
    def test_retrieve_forecast_data_raises_runtime_error_after_two_processing_failures(
        self,
        mock_session_class,
        mock_read_csv,
        mock_save_file_csv,
    ):
        """Unexpected processing errors should raise RuntimeError after both attempts fail."""
        manager = self.create_manager_without_init()

        mock_session = MagicMock()
        mock_session.get.side_effect = [
            DummyResponse("invalid content"),
            DummyResponse("invalid content"),
        ]
        mock_session_class.return_value = mock_session

        mock_read_csv.side_effect = ValueError("parse failed")

        with self.assertRaises(RuntimeError) as context:
            manager.retrieve_forecast_data()

        self.assertIn("Unexpected error while processing forecast data", str(context.exception))
        self.assertEqual(mock_session.get.call_count, 2)
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

        manager.retrieve_forecast_data()

        self.assertEqual(len(manager.forecast_df), 74)
        self.assertEqual(mock_save_file_csv.call_count, 2)


    @patch.object(forecast_manager_module, "save_file_csv")
    @patch.object(forecast_manager_module.requests, "Session")
    def test_retrieve_forecast_data_adds_cs_when_missing_from_main_forecast(
        self,
        mock_session_class,
        mock_save_file_csv,
    ):
        """The main forecast dataframe should receive a cs column when it is missing."""
        manager = self.create_manager_without_init()

        main_forecast_text = (
            "2026 7 10 0 1.0 8.0\n"
            "2026 7 10 1 3.0 10.0\n"
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

        manager.retrieve_forecast_data()

        self.assertIn("cs", manager.forecast_df.columns)
        self.assertEqual(manager.forecast_df["cs"].tolist(), [0, 0])
        self.assertEqual(mock_save_file_csv.call_count, 2)

    @patch.object(forecast_manager_module, "save_file_csv")
    @patch.object(forecast_manager_module.requests, "Session")
    def test_retrieve_forecast_data_uses_same_columns_when_conversion_is_empty(
        self,
        mock_session_class,
        mock_save_file_csv,
    ):
        """If forecast column conversion is empty, the manager should keep the original forecast columns."""
        manager = self.create_manager_without_init(
            forecast_class=DummyForecastWithoutColumnConversion,
        )

        main_forecast_text = (
            "2026 7 10 0 1.0 8.0\n"
            "2026 7 10 1 3.0 10.0\n"
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

        manager.retrieve_forecast_data()

        for column in ["year", "month", "day", "hour", "Hs", "Tp", "cs"]:
            self.assertIn(column, manager.forecast_df.columns)

        self.assertEqual(manager.forecast_df["Hs"].tolist(), [1.0, 3.0])
        self.assertEqual(manager.forecast_df["Tp"].tolist(), [8.0, 10.0])
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

        expected_index = pd.date_range(
            start="2026-07-10 00:00:00",
            end="2026-07-10 02:00:00",
            freq="1h",
        )

        expected_df = pd.DataFrame(
            {
                "Hs": [1.0, 2.0, 3.0],
                "Tp": [8.0, 9.0, 10.0],
            },
            index=expected_index,
        )

        pd.testing.assert_frame_equal(result, expected_df)

if __name__ == "__main__":
    unittest.main(verbosity=2)