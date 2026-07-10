# tests/domain/forecasts/test_forecast.py

import importlib
import os
import unittest
from unittest.mock import patch, sentinel


forecast_module = importlib.import_module("oriom.domain.Forecasts.Forecast")


class TestForecast(unittest.TestCase):
    """Tests for the Forecast class."""

    def test_init_sets_access_data_and_forecast_data(self):
        """
        Forecast initialisation should:
        - read credentials from environment variables
        - read the forecast URL from environment variables
        - load the selected forecast data from constants_forecast
        """
        forecast_type = "TEST_FORECAST"

        env_values = {
            "TEST_FORECAST_USERNAME": "test_user",
            "TEST_FORECAST_PASSWORD": "test_password",
            "TEST_FORECAST_URL": "https://forecast.test/api",
        }

        with patch.dict(os.environ, env_values, clear=False), patch.object(
            forecast_module.constants_forecast,
            forecast_type,
            sentinel.forecast_data,
            create=True,
        ):
            forecast = forecast_module.Forecast(type_forecast=forecast_type)

        self.assertEqual(forecast.type_forecast, forecast_type)
        self.assertEqual(forecast.username, "test_user")
        self.assertEqual(forecast.password, "test_password")
        self.assertEqual(forecast.addr, "https://forecast.test/api")
        self.assertEqual(forecast.forecast_data, sentinel.forecast_data)

    def test_forecast_access_sets_username_password_and_addr(self):
        """forecast_access should read username, password and URL from environment variables."""
        forecast_type = "ACCESS_TEST"

        env_values = {
            "ACCESS_TEST_USERNAME": "access_user",
            "ACCESS_TEST_PASSWORD": "access_password",
            "ACCESS_TEST_URL": "https://access.test/api",
        }

        forecast = forecast_module.Forecast.__new__(forecast_module.Forecast)
        forecast.type_forecast = forecast_type

        with patch.dict(os.environ, env_values, clear=False):
            forecast.forecast_access()

        self.assertEqual(forecast.username, "access_user")
        self.assertEqual(forecast.password, "access_password")
        self.assertEqual(forecast.addr, "https://access.test/api")

    def test_forecast_access_raises_value_error_when_username_is_missing(self):
        """forecast_access should raise ValueError when the username environment variable is missing."""
        forecast_type = "MISSING_USERNAME_TEST"

        env_values = {
            "MISSING_USERNAME_TEST_PASSWORD": "test_password",
            "MISSING_USERNAME_TEST_URL": "https://forecast.test/api",
        }

        forecast = forecast_module.Forecast.__new__(forecast_module.Forecast)
        forecast.type_forecast = forecast_type

        with patch.dict(os.environ, env_values, clear=True):
            with self.assertRaises(ValueError) as context:
                forecast.forecast_access()

        self.assertIn(
            "Forecast: Missing environment variable for forecast type 'MISSING_USERNAME_TEST'",
            str(context.exception),
        )

    def test_forecast_access_raises_value_error_when_password_is_missing(self):
        """forecast_access should raise ValueError when the password environment variable is missing."""
        forecast_type = "MISSING_PASSWORD_TEST"

        env_values = {
            "MISSING_PASSWORD_TEST_USERNAME": "test_user",
            "MISSING_PASSWORD_TEST_URL": "https://forecast.test/api",
        }

        forecast = forecast_module.Forecast.__new__(forecast_module.Forecast)
        forecast.type_forecast = forecast_type

        with patch.dict(os.environ, env_values, clear=True):
            with self.assertRaises(ValueError) as context:
                forecast.forecast_access()

        self.assertIn(
            "Forecast: Missing environment variable for forecast type 'MISSING_PASSWORD_TEST'",
            str(context.exception),
        )

    def test_forecast_access_raises_value_error_when_url_is_missing(self):
        """forecast_access should raise ValueError when the URL environment variable is missing."""
        forecast_type = "MISSING_URL_TEST"

        env_values = {
            "MISSING_URL_TEST_USERNAME": "test_user",
            "MISSING_URL_TEST_PASSWORD": "test_password",
        }

        forecast = forecast_module.Forecast.__new__(forecast_module.Forecast)
        forecast.type_forecast = forecast_type

        with patch.dict(os.environ, env_values, clear=True):
            with self.assertRaises(ValueError) as context:
                forecast.forecast_access()

        self.assertIn(
            "Forecast: Missing environment variable for forecast type 'MISSING_URL_TEST'",
            str(context.exception),
        )

    def test_forecast_access_logs_error_when_environment_variable_is_missing(self):
        """forecast_access should log an error when one or more required environment variables are missing."""
        forecast_type = "LOG_MISSING_ENV_TEST"

        forecast = forecast_module.Forecast.__new__(forecast_module.Forecast)
        forecast.type_forecast = forecast_type

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                forecast.forecast_access()


    def test_forecast_finder_sets_forecast_data(self):
        """forecast_finder should load the forecast configuration from constants_forecast."""
        forecast_type = "FINDER_TEST"

        forecast = forecast_module.Forecast.__new__(forecast_module.Forecast)
        forecast.type_forecast = forecast_type

        with patch.object(
            forecast_module.constants_forecast,
            forecast_type,
            sentinel.finder_forecast_data,
            create=True,
        ):
            forecast.forecast_finder()

        self.assertEqual(forecast.forecast_data, sentinel.finder_forecast_data)

    def test_forecast_finder_raises_value_error_when_forecast_type_does_not_exist(self):
        """forecast_finder should raise ValueError when the forecast type is not defined in constants_forecast."""
        forecast_type = "UNKNOWN_FORECAST_TYPE"

        forecast = forecast_module.Forecast.__new__(forecast_module.Forecast)
        forecast.type_forecast = forecast_type

        if hasattr(forecast_module.constants_forecast, forecast_type):
            delattr(forecast_module.constants_forecast, forecast_type)

        with self.assertRaises(ValueError) as context:
            forecast.forecast_finder()

        self.assertIn(
            "Forecast: Forecast type 'UNKNOWN_FORECAST_TYPE' does not exist",
            str(context.exception),
        )

    def test_forecast_finder_logs_error_when_forecast_type_does_not_exist(self):
        """forecast_finder should log an error when the forecast type is not defined."""
        forecast_type = "UNKNOWN_LOG_FORECAST_TYPE"

        forecast = forecast_module.Forecast.__new__(forecast_module.Forecast)
        forecast.type_forecast = forecast_type

        if hasattr(forecast_module.constants_forecast, forecast_type):
            delattr(forecast_module.constants_forecast, forecast_type)

        with self.assertRaises(ValueError):
            forecast.forecast_finder()


if __name__ == "__main__":
    unittest.main(verbosity=2)