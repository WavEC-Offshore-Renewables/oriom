import os
import unittest
from pathlib import Path
from unittest.mock import patch
import warnings
import importlib.util

import pandas as pd
from pandas.testing import assert_frame_equal

from oriom.inputs.Configuration import ConfigRun
import oriom.main as main_module

warnings.simplefilter("ignore")
pd.options.mode.chained_assignment = None  # Disable SettingWithCopyWarning

try:
    check_files_spec = importlib.util.find_spec(
        "oriom.core.functions.private.check_files"
    )
except ModuleNotFoundError:
    check_files_spec = None

class TestMainEndToEnd(unittest.TestCase):
    """End-to-end regression test for oriom.main."""

    @staticmethod
    def _repo_root() -> Path:
        # If this test file is inside <repo>/tests/, parents[1] is <repo>.
        return Path(__file__).resolve().parents[1]

    @staticmethod
    def _read_csv_normalized(path: Path) -> pd.DataFrame:
        df = pd.read_csv(path)

        # Drop auto-generated index columns if present.
        unnamed_cols = [c for c in df.columns if str(c).startswith("Unnamed")]
        if unnamed_cols:
            df = df.drop(columns=unnamed_cols)

        return df

    def _assert_csv_dirs_equal(self, expected_dir: Path, actual_dir: Path):
        expected_files = sorted(expected_dir.glob("*.csv"))
        self.assertTrue(expected_files, f"No expected CSV files found in: {expected_dir}")

        actual_files = sorted(actual_dir.glob("*.csv"))
        self.assertTrue(actual_files, f"No actual CSV files found in: {actual_dir}")

        expected_names = {p.name for p in expected_files}
        actual_names = {p.name for p in actual_files}

        self.assertSetEqual(
            actual_names,
            expected_names,
            f"{actual_files} CSV file set mismatch.\nExpected: {sorted(expected_names)}\nActual: {sorted(actual_names)}",
        )

        for exp_path in expected_files:
            act_path = actual_dir / exp_path.name

            df_exp = self._read_csv_normalized(exp_path)
            df_act = self._read_csv_normalized(act_path)
            try:
                assert_frame_equal(
                    df_act,
                    df_exp,
                    check_dtype=False,
                    check_exact=False,
                    rtol=1e-10,
                    atol=1e-12,
                )
            except AssertionError:
                raise AssertionError(f'\n Error in file {exp_path.name}')


    def test_main_end_to_end_outputs_match_golden_csvs(self):
        """
        Run the full pipeline using the Excel inputs in tests/test_files/test_end_to_end,
        overwrite inputs.general.failureevent_file["value"] right after Inputs(...) is created,
        force deterministic location selection via choose_loc mock, and compare produced CSV
        outputs with the golden files in tests/test_files/test_end_to_end/result_0.
        """
        repo_root = self._repo_root()
        excel_dir = repo_root / "tests" / "test_files" / "test_end_to_end"

        if check_files_spec:
            expected_result0_dir = excel_dir / "private" / "result_0"
            repo_root_failure_dir = os.path.join(repo_root, "tests", "test_files", "test_end_to_end", "private")
        else:
            expected_result0_dir = excel_dir / "public" / "result_0"
            # This is the value you want to inject into inputs.general.failureevent_file["value"]
            repo_root_failure_dir = os.path.join(repo_root, "tests", "test_files", "test_end_to_end", "public")

        self.assertTrue(excel_dir.exists(), f"Excel directory not found: {excel_dir}")
        self.assertTrue((excel_dir / "form_test.xlsx").exists(), "Missing form_test.xlsx")
        self.assertTrue(expected_result0_dir.exists(), f"Expected golden output dir not found: {expected_result0_dir}")

        # Reproducibility for randomness (Monte Carlo etc.)
        import random
        import numpy as np
        random.seed(0)
        np.random.seed(0)

        config = ConfigRun(
            STATISTICAL_CHART=True,
            DIFF_DISTANCE=True,
            DIFF_KM_DISTANCE=5,
            KM_MOTHER_VESSEL=5,
            VESSEL_DIST_REDUCED_LIST=["ctv", "sv"],
            FUEL_TO_ADD={},
            MOBILISATION_TO_ADD={},
            ENERGY_AVAILABILITY_CALCULATION=True,
            ENERGY_STATISTICAL_CALCULATION=False,
            PROJECT_NAME="TEST_E2E",
            BASEFILES_FROM_EXCEL=False,
            EXCEL_FILE_PATH=str(excel_dir),
            SOURCE_PATH_SHAREPOINT="",
            FORM_NAME="form_test.xlsx",
            TIME_FAIL_OP_IMMEDIATELY=0.02,
        )

        # ---- Patch Inputs.__init__ to overwrite failureevent_file after Inputs(...) is created ----
        original_inputs_init = main_module.Inputs.__init__

        def patched_inputs_init(self, *args, **kwargs):
            # Call the real constructor first
            original_inputs_init(self, *args, **kwargs)

            # Overwrite failureevent_file["value"] immediately after creation
            # (guarded in case YAML/schema changes)
            try:
                self.general.failureevent_file["value"] = repo_root_failure_dir
            except Exception as e:
                raise AssertionError(
                    f"Cannot override inputs.general.failureevent_file['value']. "
                    f"Attribute not found or wrong structure. Error: {e}"
                ) from e

        # ---- Patch choose_loc to return values you decide in the test ----
        # Sequence of values (one per call) will follow the test implemented
        # If choose_loc is called more times than the list length, it will raise StopIteration.
        choose_loc_values = [2, 5, 4, 6, 3, 4, 3, 2, 4]

        choose_loc_side_effect = choose_loc_values

        with patch.object(main_module.Inputs, "__init__", new=patched_inputs_init):
            with patch(
                "oriom.core.functions.layout_power.aux_layout_power_func.choose_loc",
                side_effect=choose_loc_side_effect,
            ):
                dirs = main_module.run(config=config)

        # Compare CSVs in result_0
        actual_result0_dir = Path(dirs.result_dir) / "result_0"
        self.assertTrue(actual_result0_dir.exists(), f"Actual result_0 directory not found: {actual_result0_dir}")

        print(expected_result0_dir)
        print(expected_result0_dir)
        print(expected_result0_dir)

        self._assert_csv_dirs_equal(expected_dir=expected_result0_dir, actual_dir=actual_result0_dir)



if __name__ == "__main__":
    unittest.main(verbosity=2)
