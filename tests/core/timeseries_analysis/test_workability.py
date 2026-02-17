import unittest
import os
from copy import deepcopy
from datetime import datetime
from unittest.mock import patch
import itertools

import pandas as pd
import numpy as np

from oriom.classes.Metocean import Metocean
from oriom.classes.Activity import Activity

from oriom.core.timeseries_analysis.workability import workability, workability_tow


class TestWorkability(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        class DummyStatInputs:
            start_year = {"value": 2018}
            lifetime = {"value": 1}

        file_metocean = os.path.join(
            os.getcwd(),
            "tests",
            "test_files",
            "metocean",
            "metocean_dummy_hourly.csv",
        )
        file_activities = os.path.join(
            os.getcwd(),
            "tests",
            "test_files",
            "op_activities_dummy.csv",
        )
        self.metocean = Metocean(
            file_=file_metocean,
            latitude=41.615065,
            longitude=-9.348514,
            stat_inputs = DummyStatInputs
        )
        self.activities = Activity.get_activities_from_csv(file_activities)

    def test_main(self):
        metocean = deepcopy(self.metocean)
        metocean.get_daylight_timesteps()
        df_workability = workability(
            activities=self.activities,
            df_metocean=metocean.df_timeseries,
        )
        self.assertTrue(df_workability.iloc[2:20, 0].all())
        self.assertTrue(df_workability.iloc[:-3, 1].all())
        self.assertTrue(df_workability.iloc[20:31, 2].all())
        # 20 and 31 instead of 19 and -7 because at timestep 19 there is no daylight

        self.assertFalse(df_workability.iloc[0:2, 0].any())
        self.assertFalse(df_workability.iloc[:20, 2].any())
        # 20 instead of 19 because at timestep 19 ther is no daylight

    def test_save(self):
        metocean = deepcopy(self.metocean)
        metocean.get_daylight_timesteps()
        tmp_dir = os.path.join(os.getcwd(), "tmp", "test")
        if not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir)
        workability(
            activities=self.activities,
            df_metocean=metocean.df_timeseries,
            out_dir=tmp_dir,
        )
        open(os.path.join(os.getcwd(), "tmp", "test", "workability.csv"), "r")
        os.remove(os.path.join(os.getcwd(), "tmp", "test", "workability.csv"))

    def test_errors(self):
        # Incompatibility between metocean timeseries and activities OLCs
        metocean = deepcopy(self.metocean)
        metocean_aux = deepcopy(metocean)
        del metocean_aux.df_timeseries["hs"]
        self.assertRaises(
            KeyError, workability, metocean_aux.df_timeseries, self.activities, None
        )
        metocean_aux = deepcopy(metocean)
        del metocean_aux.df_timeseries["tp"]
        self.assertRaises(
            KeyError, workability, metocean_aux.df_timeseries, self.activities, None
        )
        metocean_aux = deepcopy(metocean)
        del metocean_aux.df_timeseries["ws"]
        self.assertRaises(
            KeyError, workability, metocean_aux.df_timeseries, self.activities, None
        )
        metocean_aux = deepcopy(metocean)
        del metocean_aux.df_timeseries["cs"]
        self.assertRaises(
            KeyError, workability, metocean_aux.df_timeseries, self.activities, None
        )

        # Zero timesteps with workability
        activtiy = Activity(
            id_="dummy",
            name="dummy",
            duration=1,
            location="site",
            wave_height=0.001,
        )
        self.assertRaises(
            AssertionError, workability, metocean.df_timeseries, [activtiy], None
        )


    def test_errors_missing_ws_hub_and_light(self):
        """
        Verify that the lack of ws_hub and light in df_metocean
            with activities that use them generates KeyError.
        """

        class DummyActivity:
            def __init__(self, id_, ws_hub=None, light=None):
                self.id = id_
                self.hs = None
                self.tp = None
                self.ws = None
                self.ws_hub = ws_hub
                self.cs = None
                self.light = light

        # df with all columns except ws_hub
        df = pd.DataFrame(
            {
                "hs": [0.5],
                "tp": [5.0],
                "ws": [10.0],
                "cs": [0.5],
                "light": [True],
            },
            index=pd.date_range("2025-01-01", periods=1, freq="H"),
        )
        acts = [DummyActivity("A", ws_hub=15.0, light=None)]
        with self.assertRaises(KeyError):
            workability(df_metocean=df, activities=acts)

        # df without light
        df2 = pd.DataFrame(
            {
                "hs": [0.5],
                "tp": [5.0],
                "ws": [10.0],
                "ws_hub": [12.0],
                "cs": [0.5],
            },
            index=pd.date_range("2025-01-01", periods=1, freq="H"),
        )
        acts2 = [DummyActivity("B", ws_hub=None, light=True)]
        with self.assertRaises(KeyError):
            workability(df_metocean=df2, activities=acts2)

    def test_activities_and_operation_together_raise_value_error(self):
        """
        If both activities and operations are defined, it must raise ValueError.
        """

        class DummyActivity:
            def __init__(self, id_):
                self.id = id_
                self.hs = None
                self.tp = None
                self.ws = None
                self.ws_hub = None
                self.cs = None
                self.light = None

        class DummyOperation:
            def __init__(self, id_):
                self.id = id_
                self.hs = None
                self.tp = None
                self.ws = None
                self.ws_hub = None
                self.cs = None
                self.light = None

        df = pd.DataFrame(
            {
                "hs": [0.5],
                "tp": [5.0],
                "ws": [10.0],
                "ws_hub": [12.0],
                "cs": [0.5],
                "light": [True],
            },
            index=pd.date_range("2025-01-01", periods=1, freq="H"),
        )
        acts = [DummyActivity("A")]
        op = DummyOperation("OP1")

        with self.assertRaises(ValueError):
            workability(df_metocean=df, activities=acts, operation=op)

    def test_operation_path_with_constraints(self):
        """
        Operation branch test: If the operation has OLC,
            timesteps that violate the bounds must evaluate to False.
        """

        class DummyOperation:
            def __init__(self, id_):
                self.id = id_
                # limiti: hs <= 1.0, tp <= 10, ws <= 30, ws_hub <= 30, cs <= 2, light=True
                self.hs = 1.0
                self.tp = 10.0
                self.ws = 30.0
                self.ws_hub = 30.0
                self.cs = 2.0
                self.light = True

        idx = pd.date_range("2025-01-01", periods=4, freq="H")
        df = pd.DataFrame(
            {
                "hs": [0.5, 0.1, 2.0, 3.0],      # last 2 overgoes the limit
                "tp": [5.0, 5.0, 5.0, 5.0],
                "ws": [10.0, 10.0, 10.0, 10.0],
                "ws_hub": [10.0, 10.0, 10.0, 10.0],
                "cs": [0.5, 0.5, 0.5, 0.5],
                "light": [True, True, True, False],  # last timestep withuout light
            },
            index=idx,
        )

        op = DummyOperation("OP1")
        df_work = workability(df_metocean=df, operation=op)

        self.assertEqual(list(df_work.columns), ["OP1"])
        self.assertEqual(df_work.index.name, "datetime")
        # first two True, last two False
        expected = [True, True, False, False]
        self.assertListEqual(df_work["OP1"].tolist(), expected)


# ---------------- TEST for workability_tow (include and_series_on_ref) ----------------


class DummyTowActivity:
    def __init__(self, id_, location="site", towing=False):
        self.id = id_
        self.location = location
        self.towing = towing
        # the other attributes are not needed because in these tests workability is mocked


class DummyTowOperation:
    def __init__(self, activities):
        self.activities = activities


class DummyMetoceanPoint:
    def __init__(self, df):
        self.df_timeseries = df


class TestWorkabilityTow(unittest.TestCase):
    def _make_base_operation_and_metocean(self):
        """
        Construct a DummyTowOperation with:
        - activity 'act_site' (location='site')
        - activity 'act_tow' (towing=True)
        and a dictionary metocean_tow with 2 points (1 and 2).
        """
        act_site = DummyTowActivity(id_="act_site", location="site", towing=False)
        act_tow = DummyTowActivity(id_="act_tow", location="tow", towing=True)
        operation = DummyTowOperation(activities=[act_site, act_tow])

        # df_metocean of site (not actually used when workability is mocked)
        idx = pd.date_range("2025-01-01", periods=4, freq="H")
        df_site = pd.DataFrame({"dummy": [0, 1, 2, 3]}, index=idx)

        # metocean_tow with 2 points
        metocean_tow = {
            1: DummyMetoceanPoint(df_site.copy()),
            2: DummyMetoceanPoint(df_site.copy()),
        }
        return operation, df_site, metocean_tow

    @patch("oriom.core.timeseries_analysis.workability.workability")
    def test_towing_and_series_basic(self, mock_workability):
        """
        Base case towing:
        - workability is mocked and returns df_works[0], df_works[1], df_works[2]
        - and_series_on_ref must AND the various points for 'act_tow'.
        """
        operation, df_site, metocean_tow = self._make_base_operation_and_metocean()

        idx = df_site.index
        df0 = pd.DataFrame(
            {
                "act_site": [True, True, True, True],
                "act_tow": [True, True, True, True],
            },
            index=idx,
        )
        df1 = pd.DataFrame(
            {
                "act_site": [True, True, True, True],
                "act_tow": [True, False, True, True],
            },
            index=idx,
        )
        df2 = pd.DataFrame(
            {
                "act_site": [True, True, True, True],
                "act_tow": [True, True, np.nan, True],
            },
            index=idx,
        )

        df_map = {0: df0, 1: df1, 2: df2}
        counter = itertools.count(0)

        def fake_workability(*args, **kwargs):
            i = next(counter)
            return df_map[i]

        mock_workability.side_effect = fake_workability

        df_work = workability_tow(
            df_metocean=df_site,
            metocean_tow=metocean_tow,
            operation=operation,
            op_dir=None,
        )

        # act_site taken from site
        pd.testing.assert_series_equal(df_work["act_site"], df0["act_site"])

        # act_tow must be AND of df0, df1, df2 (NaN -> False)
        expected_tow = pd.Series(
            [True, False, False, True],
            index=idx,
            name="act_tow",
        )
        pd.testing.assert_series_equal(df_work["act_tow"], expected_tow)

    @patch("oriom.core.timeseries_analysis.workability.workability")
    @patch("oriom.core.timeseries_analysis.workability.logging.warning")

    def test_towing_missing_column_falls_back_to_site_series(self, m_log_warning, mock_workability):
        """
        If a df_works[i] does not have the act_tow column, and_series_on_ref should
        log a warning and simply return the site series.
        """
        operation, df_site, metocean_tow = self._make_base_operation_and_metocean()
        idx = df_site.index

        df0 = pd.DataFrame(
            {
                "act_site": [True, True, True, True],
                "act_tow": [True, True, True, True],
            },
            index=idx,
        )
        df1 = pd.DataFrame(
            {
                "act_site": [False, False, False, False],
                # column act_tow missing
            },
            index=idx,
        )

        df_map = {0: df0, 1: df1, 2: df1}
        counter = itertools.count(0)

        def fake_workability(*args, **kwargs):
            i = next(counter)
            return df_map[i]

        mock_workability.side_effect = fake_workability

        df_work = workability_tow(
            df_metocean=df_site,
            metocean_tow=metocean_tow,
            operation=operation,
            op_dir=None,
        )

        # act_tow must be equal to site (fallback)
        m_log_warning.assert_called_once()
        pd.testing.assert_series_equal(df_work["act_tow"], df0["act_tow"])
        self.assertIn("missing in metocean data point", m_log_warning.call_args[0][0])

    @patch("oriom.core.timeseries_analysis.workability.workability")
    @patch("oriom.core.timeseries_analysis.workability.logging.warning")
    def test_towing_index_mismatch_falls_back_to_site_series(self, m_log_warning, mock_workability):
        """
        If a df_works[i] has an incompatible index, and_series_on_ref should
        log a warning and return the site series.
        """
        operation, df_site, metocean_tow = self._make_base_operation_and_metocean()
        idx = df_site.index

        df0 = pd.DataFrame(
            {
                "act_site": [True, True, True, True],
                "act_tow": [True, True, True, True],
            },
            index=idx,
        )
        # different index (shifted by 1 day) -> is_in not compatible
        df_bad = pd.DataFrame(
            {
                "act_site": [True, True, True, True],
                "act_tow": [False, False, False, False],
            },
            index=idx + pd.Timedelta(days=1),
        )

        df_map = {0: df0, 1: df_bad, 2: df_bad}
        counter = itertools.count(0)

        def fake_workability(*args, **kwargs):
            i = next(counter)
            return df_map[i]

        mock_workability.side_effect = fake_workability


        df_work = workability_tow(
            df_metocean=df_site,
            metocean_tow=metocean_tow,
            operation=operation,
            op_dir=None,
        )

        m_log_warning.assert_called_once()
        pd.testing.assert_series_equal(df_work["act_tow"], df0["act_tow"])
        self.assertIn("has different index", m_log_warning.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
