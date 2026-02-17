# tests/test_stat_chart_inspection_campaign_end_to_end.py
import unittest
from unittest.mock import patch
import pandas as pd
import numpy as np
import pandas.testing as pdt
from datetime import datetime, timedelta
from types import SimpleNamespace

from oriom.core.functions.vessels_manager.VesselChartInspCampaign import Stat_chart_inspection_campaign



# --------- Dummies to mimic production structures ---------

class DummyMotherVessel:
    def __init__(self, mother_vessel: bool):
        self.mother_vessel = mother_vessel

class DummyInspectionCore:
    def __init__(self, id_: str, months, day_start: int, vessel2):
        self.id = id_
        self.months = months              # int or list[int]
        self.day_start = day_start
        self.vessel2 = vessel2            # has .mother_vessel

class DummyInspectionStat:
    def __init__(self, insp_class: DummyInspectionCore):
        self.insp_class = insp_class

class DummyVessel:
    def __init__(self, id_):
        self.id = id_


# --------- Build inspections ONLY from the provided table ---------

def build_inspections_from_provided_table():
    """
    Using exactly the table you provided.
    Rules:
      - mother_vessel = True iff vessel2 == "V004 - SOV"
      - day_start default = 1 if missing (opv_a5 has day_start=2)
      - months can be "3,7" -> [3,7] or a single number string -> int
    """
    rows = [
        ("opv_a1",       "4",   None,              "",           ""),
        ("opv_a5",       "3",   2,                 "V004 - SOV", "V004"),
        ("opv_a2",       "4",   None,              "V004 - SOV", "V004"),
        ("opv_a4",       "4",   None,              "V004 - SOV", "V004"),
        ("opv_a6",       "9",   None,              "V004 - SOV", "V004"),
        ("ofw_wf_a1",    "6",   None,              "V004 - SOV", "V004"),
        ("ofw_wf_a2",    "6",   None,              "V004 - SOV", "V004"),
        ("ofw_wf_a3",    "5",   None,              "",           ""),
        ("ofw_wf_a7",    "6",   None,              "V004 - SOV", "V004"),
        ("ofw_wf_a8",    "6",   None,              "V004 - SOV", "V004"),
        ("ofw_wf_a9",    "6",   None,              "V004 - SOV", "V004"),
        ("ofw_wf_a6",    "6",   None,              "V004 - SOV", "V004"),
        ("owc_cpo_a1",        "3,7", None,              "V004 - SOV", "V004"),
        ("owc_cpo_a2",        "3",   None,              "V004 - SOV", "V004"),
        ("owc_cpo_a3",   "3",   None,              "V004 - SOV", "V004"),
        ("owc_exp_1",    "7",   None,              "",           ""),
        ("owc_cpo_a4",   "3",   None,              "V004 - SOV", "V004"),


    ]
    out = []
    for id_, months_str, day_start, vessel2, _v2id in rows:
        mv = DummyMotherVessel(mother_vessel=(vessel2 == "V004 - SOV")) if vessel2 else None
        if "," in months_str:
            months = [int(x.strip()) for x in months_str.split(",") if x.strip()]
        else:
            months = int(months_str)
        day = day_start if day_start is not None else 1
        insp = DummyInspectionCore(id_=id_, months=months, day_start=day, vessel2=mv)
        out.append(DummyInspectionStat(insp))
    return out


# --------- Build the provided DataFrame (d_end_stat_chart initially NaN) ---------

def build_provided_df():
    rows = [
        # d_trigger, d_end, d_end_stat_chart, event, id, vessel_1, n_vessel_1, vessel_2, n_vessel_2, comments, shutdown
        ("01-03-90 8:00",  "16-02-91 9:30",   None, "inspection_site", "opv_a5",     "v100", 4, "v004", 1, "inspection_site_campaign", True),
        ("01-04-90 8:00",  "13-04-90 17:12",  None, "inspection_site", "opv_a2",     "v100", 2, "v004", 1, "inspection_site_campaign", False),
        ("01-04-90 20:00", "13-04-90 17:12",  None, "inspection_site", "opv_a4",     "v100", 4, "v004", 1, "inspection_site_campaign", False),
        ("08-05-90 17:00", "21-07-90 16:48",  None, "inspection_site", "owc_cpo_a1", "v100", 4, "v004", 1, "inspection_site_campaign", False),
        ("01-06-90 8:00",  "20-06-90 15:06",  None, "inspection_site", "ofw_wf_a1",  "v001", 2, "v004", 1, "inspection_site_campaign", False),
        ("06-06-90 14:00", "20-06-90 15:06",  None, "inspection_site", "ofw_wf_a2",  "v001", 2, "v004", 1, "inspection_site_campaign", True),
        ("07-06-90 23:00", "20-06-90 15:06",  None, "inspection_site", "ofw_wf_a7",  "v001", 2, "v004", 1, "inspection_site_campaign", True),
        ("08-06-90 22:00", "20-06-90 15:06",  None, "inspection_site", "ofw_wf_a8",  "v001", 2, "v004", 1, "inspection_site_campaign", True),
        ("09-06-90 23:00", "20-06-90 15:06",  None, "inspection_site", "ofw_wf_a9",  "v001", 2, "v004", 1, "inspection_site_campaign", True),
        ("11-06-90 15:00", "20-06-90 15:06",  None, "inspection_site", "ofw_wf_a6",  "v001", 2, "v004", 1, "inspection_site_campaign", True),
        ("01-07-90 8:00",  "26-09-90 23:36",  None, "inspection_site", "owc_cpo_a1", "v100", 4, "v004", 1, "inspection_site_campaign", False),
        ("21-07-90 17:00", "16-02-91 9:30",   None, "inspection_site", "owc_cpo_a2", "v100", 4, "v004", 1, "inspection_site_campaign", True),
        ("03-08-90 13:00", "16-02-91 9:30",   None, "inspection_site", "owc_cpo_a3", "v100", 4, "v004", 1, "inspection_site_campaign", True),
        ("14-08-90 14:00", "16-02-91 9:30",   None, "inspection_site", "owc_cpo_a4", "v100", 4, "v004", 1, "inspection_site_campaign", False),
        ("01-09-90 8:00",  "19-09-90 16:30",  None, "inspection_site", "opv_a6",     "v100", 4, "v004", 1, "inspection_site_campaign", False),
        ("01-03-91 8:00",  "16-02-92 9:30",   None, "inspection_site", "opv_a5",     "v100", 4, "v004", 1, "inspection_site_campaign", True),
        ("01-04-91 8:00",  "13-04-91 17:12",  None, "inspection_site", "opv_a2",     "v100", 2, "v004", 1, "inspection_site_campaign", False),
        ("04-04-91 19:00", "13-04-91 17:12",  None, "inspection_site", "opv_a4",     "v100", 4, "v004", 1, "inspection_site_campaign", False),
        ("08-05-91 17:00", "19-07-91 16:48",  None, "inspection_site", "owc_cpo_a1", "v100", 4, "v004", 1, "inspection_site_campaign", False),
        ("01-06-91 8:00",  "20-06-91 15:06",  None, "inspection_site", "ofw_wf_a1",  "v001", 2, "v004", 1, "inspection_site_campaign", False),
        ("06-06-91 14:00", "20-06-91 15:06",  None, "inspection_site", "ofw_wf_a2",  "v001", 2, "v004", 1, "inspection_site_campaign", True),
        ("07-06-91 23:00", "20-06-91 15:06",  None, "inspection_site", "ofw_wf_a7",  "v001", 2, "v004", 1, "inspection_site_campaign", True),
        ("15-06-91 12:00", "20-06-91 15:06",  None, "inspection_site", "ofw_wf_a8",  "v001", 2, "v004", 1, "inspection_site_campaign", True),
        ("17-06-91 15:00", "20-06-91 15:06",  None, "inspection_site", "ofw_wf_a9",  "v001", 2, "v004", 1, "inspection_site_campaign", True),
        ("18-06-91 23:00", "20-06-91 15:06",  None, "inspection_site", "ofw_wf_a6",  "v001", 2, "v004", 1, "inspection_site_campaign", True),
        ("01-07-91 8:00",  "26-09-91 23:36",  None, "inspection_site", "owc_cpo_a1", "v100", 4, "v004", 1, "inspection_site_campaign", False),
        ("19-07-91 17:00", "16-02-92 9:30",   None, "inspection_site", "owc_cpo_a2", "v100", 4, "v004", 1, "inspection_site_campaign", True),
        ("30-07-91 13:00", "16-02-92 9:30",   None, "inspection_site", "owc_cpo_a3", "v100", 4, "v004", 1, "inspection_site_campaign", True),
        ("09-08-91 21:00", "16-02-92 9:30",   None, "inspection_site", "owc_cpo_a4", "v100", 4, "v004", 1, "inspection_site_campaign", False),
        ("01-09-91 8:00",  "19-09-91 16:30",  None, "inspection_site", "opv_a6",     "v100", 4, "v004", 1, "inspection_site_campaign", False),
    ]
    cols = ["d_trigger","d_end","d_end_stat_chart","event","id","vessel_1","n_vessel_1",
            "vessel_2","n_vessel_2","comments","shutdown"]
    df = pd.DataFrame(rows, columns=cols)

    # add columns the code references (it sets/reads them)
    for c in ["d_end_leadtime","d_end_wait_start","d_end_dur_net_port","d_end_transit_ts",
              "d_end_wait_site","d_end_dur_net_site","d_end_transit_tp"]:
        df[c] = pd.NaT

    # ensure NaN in d_end_stat_chart (per your request)
    df["d_end_stat_chart"] = np.nan
    return df


# --------- Expected dicts computed from the same inspections ---------

def expected_dicts_from_inspections(inspections):
    def months_to_list(m): return m if isinstance(m, list) else [m]
    campaign = {}
    for s in inspections:
        ins = s.insp_class
        if ins.vessel2 and getattr(ins.vessel2, "mother_vessel", False):
            for m in months_to_list(ins.months):
                key = (m, ins.day_start)
                campaign.setdefault(key, []).append(ins.id)
    id_to_groups = {}
    for k, ids in campaign.items():
        for _id in ids:
            id_to_groups.setdefault(_id, []).append(k)
    id_month_to_group = {}
    for k, ids in campaign.items():
        m, _d = k
        for _id in ids:
            id_month_to_group[(_id, m)] = k
    # sort for deterministic compare
    campaign_sorted = {k: sorted(v) for k, v in campaign.items()}
    id_to_groups_sorted = {k: sorted(v) for k, v in id_to_groups.items()}
    return campaign_sorted, id_to_groups_sorted, id_month_to_group


# --------- The test ---------

class TestStatChartInspectionCampaignEndToEnd(unittest.TestCase):

    @patch("oriom.core.functions.vessels_manager.VesselChartInspCampaign.log_event_convert_stringtime")
    def test_dicts_and_create_stat_chart(self, mock_convert):
        # Patch converter to parse day-first strings used in input
        def _convert(df):
            for col in ["d_trigger","d_end","d_end_stat_chart"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")
            return df
        mock_convert.side_effect = _convert

        inspections = build_inspections_from_provided_table()
        stat = Stat_chart_inspection_campaign(inspections_site_stat=inspections)

        # Check dictionaries match expectations derived from the same table
        exp_campaign, exp_id_to_groups, exp_id_month_to_group = expected_dicts_from_inspections(inspections)
        got_campaign = {k: sorted(v) for k, v in stat.campaign_inspection_dict.items()}
        got_id_to_groups = {k: sorted(v) for k, v in stat.id_to_groups.items()}
        got_id_month_to_group = stat.id_month_to_group
        self.assertDictEqual(got_campaign, exp_campaign)
        self.assertDictEqual(got_id_to_groups, exp_id_to_groups)
        self.assertDictEqual(got_id_month_to_group, exp_id_month_to_group)

        # Run create_stat_chart_inspection_campaign on the provided df (with NaN stat chart)
        df = build_provided_df()
        vessels = [DummyVessel("v004")]  # df uses lowercase 'v004'
        df_empty = pd.DataFrame({'comments': ['Check vessel logs', 'Schedule maintenance', 'Review safety report']})
        df_out_untuched = stat.create_stat_chart_inspection_campaign(df=df_empty, vessels=DummyVessel, percentile=0.9)
        pdt.assert_frame_equal(df_empty, df_out_untuched)
        df_out = stat.create_stat_chart_inspection_campaign(df=df.copy(), vessels=vessels, percentile=0.9)

        # For all campaign rows, d_end_stat_chart should be filled (not NaN)
        mask_campaign = df_out["comments"] == "inspection_site_campaign"
        self.assertTrue(df_out.loc[mask_campaign, "d_end_stat_chart"].notna().all())

        # APRIL 1990: opv_a2 & opv_a4 should share the block; stat_end == max end of the block
        apr_mask = (df_out["id"].isin(["opv_a2","opv_a4"])) & (df_out["d_trigger"].dt.year == 1990)
        self.assertTrue(apr_mask.any())
        expected_apr_end = pd.to_datetime("13-04-90 17:12", dayfirst=True)
        self.assertTrue((df_out.loc[apr_mask, "d_end_stat_chart"] == expected_apr_end).all())

        # JUNE 1990: ofw_wf_a* block; stat_end == 20-06-90 15:06
        june_ids = ["ofw_wf_a1","ofw_wf_a2","ofw_wf_a7","ofw_wf_a8","ofw_wf_a9","ofw_wf_a6"]
        jun_mask = (df_out["id"].isin(june_ids)) & (df_out["d_trigger"].dt.year == 1990)
        self.assertTrue(jun_mask.any())
        expected_jun_end = pd.to_datetime("20-06-90 15:06", dayfirst=True)
        self.assertTrue((df_out.loc[jun_mask, "d_end_stat_chart"] == expected_jun_end).all())

        # JULY 1990: owc_cpo_a1 must have non-NaN stat end (no exact value asserted)
        jul_mask = (df_out["id"] == "owc_cpo_a1") & (df_out["d_trigger"].dt.year == 1990)
        self.assertTrue(df_out.loc[jul_mask, "d_end_stat_chart"].notna().all())

def make_inspection(id_, months, day_start, mother_vessel=True):
    """
    Creates a minimal inspection.insp_class object with the attributes used by the class:
    - id
    - months
    - day_start
    - vessel2.mother_vessel
    """
    vessel2 = SimpleNamespace(mother_vessel=mother_vessel)
    insp_class = SimpleNamespace(
        id=id_,
        months=months,
        day_start=day_start,
        vessel2=vessel2,
    )
    # Wrapper similar to InspectionsSiteStat with an insp_class attribute
    return SimpleNamespace(insp_class=insp_class)


def make_vessel(id_):
    """Minimal Vessel object with only an id."""
    return SimpleNamespace(id=id_)


class TestStatChartInspectionCampaign(unittest.TestCase):
    def setUp(self):
        # Two inspections in the same campaign (month 5, day 10)
        insp_stat_A = make_inspection("inspA", months=5, day_start=10)
        insp_stat_B = make_inspection("inspB", months=5, day_start=10)

        self.obj = Stat_chart_inspection_campaign([insp_stat_A, insp_stat_B])

    def test_campaign_dict_and_mappings(self):
        """
        Verifies that campaign dictionaries are correctly built
        from two inspections that share the same (month, day_start).
        """
        # campaign_inspection_dict: {(5,10): ['inspA','inspB']}
        self.assertIn((5, 10), self.obj.campaign_inspection_dict)
        self.assertCountEqual(
            self.obj.campaign_inspection_dict[(5, 10)],
            ["inspA", "inspB"],
        )

        # id_to_groups: 'inspA' and 'inspB' → [(5,10)]
        self.assertEqual(self.obj.id_to_groups["inspA"], [(5, 10)])
        self.assertEqual(self.obj.id_to_groups["inspB"], [(5, 10)])

        # id_month_to_group: ('inspA',5) → (5,10), same for 'inspB'
        self.assertEqual(self.obj.id_month_to_group[("inspA", 5)], (5, 10))
        self.assertEqual(self.obj.id_month_to_group[("inspB", 5)], (5, 10))

    @patch(
        "oriom.core.functions.vessels_manager.VesselChartInspCampaign.log_event_convert_stringtime",
        side_effect=lambda df: df,
    )
    def test_create_stat_chart_inspection_campaign_simple_group(self, _m_convert):
        """
        Simple scenario:
        - Two rows from the same campaign (same (month, day_start), same vessel_2)
        - Block duration is max_end - min_trigger
        - The percentile on a single block returns the same duration
        - d_end_stat_chart must match max_end for all rows in the block
        """
        vessel_id = "MV1"
        vessel = make_vessel(vessel_id)

        # Two events of the same campaign in the same year
        t0 = datetime(2025, 5, 10, 8, 0, 0)
        t1 = t0 + timedelta(days=2)           # d_end row 0
        t2 = t0 + timedelta(hours=2)          # d_trigger row 1
        t3 = t0 + timedelta(days=3, hours=1)  # d_end row 1 (block max_end)

        df = pd.DataFrame(
            {
                "id": ["inspA", "inspB"],
                "d_trigger": [t0, t2],
                "d_end": [t1, t3],
                "comments": ["inspection_site_campaign", "inspection_site_campaign"],
                "vessel_2": [vessel_id, vessel_id],
                # column that will be overwritten
                "d_end_stat_chart": [pd.NaT, pd.NaT],
            }
        )

        df_out = self.obj.create_stat_chart_inspection_campaign(
            df=df,
            vessels=[vessel],
            percentile=0.9,  # with a single block this does not change anything
        )

        # Block max_end
        expected_stat_end = t3

        # All rows must have d_end_stat_chart equal to expected_stat_end
        self.assertTrue(
            all(df_out["d_end_stat_chart"] == expected_stat_end),
            msg=f"d_end_stat_chart does not match {expected_stat_end}",
        )

        # Also check dtype
        self.assertTrue(
            pd.api.types.is_datetime64_any_dtype(df_out["d_end_stat_chart"]),
        )
        

if __name__ == "__main__":
    unittest.main(verbosity=2)
