import os
import unittest
from pathlib import Path
from unittest.mock import patch
import warnings
import importlib.util
from unittest import skip

import pandas as pd
from pandas.testing import assert_frame_equal

from oriom.inputs.Configuration import ConfigRun
import oriom.main as main_module

warnings.simplefilter("ignore")
pd.options.mode.chained_assignment = None  # Disable SettingWithCopyWarning
warnings.filterwarnings("ignore",category=FutureWarning)
warnings.filterwarnings("ignore",category=DeprecationWarning)

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

            if exp_path.name == "kpi_yearly_final.csv":
                df_exp = (
                    df_exp
                    .sort_values("vessel_id", na_position="first")
                    .reset_index(drop=True)
                )
                df_act = (
                    df_act
                    .sort_values("vessel_id", na_position="first")
                    .reset_index(drop=True)
                )

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
            print('\n\n***')
            print('private repo detected based on check_files module presence. Using private repo inputs and expected outputs.')
            print('***\n')
            expected_result0_dir = excel_dir / "repo_private" / "result_0"
        else:
            print('\n\n***')
            print('private repo not detected. Using public repo inputs and expected outputs.')
            print('***\n')
            expected_result0_dir = excel_dir / "repo_public" / "result_0"

        # This is the value you want to inject into inputs.general.failureevent_file["value"]
        repo_root_failure_dir = os.path.join(repo_root, "tests", "test_files", "test_end_to_end", "repo_public")

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
            PROJECT_NAME="test_E2E",
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

        self._assert_csv_dirs_equal(expected_dir=expected_result0_dir, actual_dir=actual_result0_dir)

    @skip
    def test_ST_main_end_to_end_outputs_match_golden_csvs(self):
        """
        Execute the real Short-Term O&M pipeline and validate its CSV outputs.

        Use dedicated ST golden files when available. Without ST golden files,
        check that the ST pipeline produces readable, nonempty CSV outputs.
        Never compare ST outputs against the normal-run golden CSVs.

        Optional environment variables:
            ORIOM_ST_INPUT_DIR: ST user data folder (default: ST_test_user_data).
            ORIOM_ST_GOLDEN_DIR: directory containing dedicated ST golden CSVs.
            ORIOM_ST_FORECAST_CSV: local timestamp-indexed forecast CSV.
        """
        import importlib
        import random
        from contextlib import ExitStack

        import numpy as np

        repo_root = self._repo_root()
        excel_dir = repo_root / "tests" / "test_files" / "test_end_to_end"
        failure_input_dir = excel_dir / "repo_public"

        self.assertTrue(excel_dir.is_dir(), f"Excel directory not found: {excel_dir}")
        self.assertTrue((excel_dir / "form_test.xlsx").is_file(), "Missing form_test.xlsx")
        self.assertTrue(
            failure_input_dir.is_dir(),
            f"Failure input directory not found: {failure_input_dir}",
        )

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
            PROJECT_NAME="test_E2E_ST",
            BASEFILES_FROM_EXCEL=False,
            EXCEL_FILE_PATH=str(excel_dir),
            SOURCE_PATH_SHAREPOINT="",
            FORM_NAME="form_test.xlsx",
            TIME_FAIL_OP_IMMEDIATELY=0.02,
            ST=True,
            DIRS_OVERWRITE_PATH=os.environ.get("ORIOM_ST_INPUT_DIR", "ST_test_user_data"),
        )

        # Keep the same deterministic failure input override as the original ST test.
        original_inputs_init = main_module.Inputs.__init__

        def patched_inputs_init(inputs_instance, *args, **kwargs):
            original_inputs_init(inputs_instance, *args, **kwargs)
            try:
                inputs_instance.general.failureevent_file["value"] = str(failure_input_dir)
            except (AttributeError, KeyError, TypeError) as exc:
                raise AssertionError(
                    "Cannot override inputs.general.failureevent_file['value']"
                ) from exc

        random.seed(0)
        np.random.seed(0)
        choose_loc_values = [2, 5, 4]

        with ExitStack() as stack:
            stack.enter_context(
                patch.object(main_module.Inputs, "__init__", new=patched_inputs_init)
            )
            stack.enter_context(
                patch(
                    "oriom.core.functions.layout_power.aux_layout_power_func.choose_loc",
                    side_effect=choose_loc_values,
                )
            )

            # Only replace live forecast acquisition when a local ST fixture is supplied.
            forecast_setting = os.environ.get("ORIOM_ST_FORECAST_CSV")
            if forecast_setting:
                forecast_path = Path(forecast_setting).expanduser().resolve()
                self.assertTrue(
                    forecast_path.is_file(),
                    f"ST forecast fixture does not exist: {forecast_path}",
                )
                forecast_df = pd.read_csv(forecast_path, index_col=0)
                forecast_df.index = pd.to_datetime(forecast_df.index, errors="coerce")
                self.assertFalse(
                    forecast_df.empty or forecast_df.index.isna().any(),
                    "ORIOM_ST_FORECAST_CSV must have a valid datetime index",
                )

                class LocalForecastManager:
                    def __init__(self, forecast_user_data, save_dir):
                        self.timeseries_file = str(forecast_path)
                        self.forecast_df = forecast_df

                patched_modules = []
                for module_name in (
                    "oriom.core.functions.private.user_inputs",
                    "oriom.inputs.user_inputs",
                ):
                    try:
                        module = importlib.import_module(module_name)
                    except ImportError:
                        continue
                    if hasattr(module, "Forecast_manager"):
                        stack.enter_context(
                            patch.object(module, "Forecast_manager", LocalForecastManager)
                        )
                        patched_modules.append(module_name)

                self.assertTrue(
                    patched_modules,
                    "Cannot locate the ST Forecast_manager dependency to patch",
                )

            # Real ST pipeline: no patch on main.run, ST_switcher or KPI generation.
            dirs = main_module.run(config=config)

        actual_result0_dir = Path(dirs.result_dir) / "result_0"
        self.assertTrue(
            actual_result0_dir.is_dir(),
            f"ST simulation did not create: {actual_result0_dir}",
        )

        # Strict comparison only with ST-specific baselines, never LT baselines.
        golden_setting = os.environ.get("ORIOM_ST_GOLDEN_DIR")
        if golden_setting:
            expected_st_dir = Path(golden_setting).expanduser().resolve()
            self.assertTrue(
                expected_st_dir.is_dir(),
                f"ST golden directory does not exist: {expected_st_dir}",
            )
        else:
            baseline_variant = "repo_private" if check_files_spec else "repo_public"
            candidates = (
                excel_dir / baseline_variant / "ST_result_0",
                excel_dir / baseline_variant / "result_0_ST",
                excel_dir / "ST_test_user_data" / "result_0",
            )
            expected_st_dir = next(
                (
                    folder
                    for folder in candidates
                    if folder.is_dir() and any(folder.glob("*.csv"))
                ),
                None,
            )

        if expected_st_dir is not None:
            self._assert_csv_dirs_equal(
                expected_dir=expected_st_dir,
                actual_dir=actual_result0_dir,
            )
        else:
            # The full ST pipeline was still executed. Validate real generated data,
            # but do not claim a numeric golden comparison without ST references.
            csv_files = sorted(actual_result0_dir.glob("*.csv"))
            self.assertTrue(
                csv_files,
                f"ST simulation generated no CSV files in {actual_result0_dir}",
            )
            self.assertIn(
                "kpi_yearly_final.csv",
                {path.name for path in csv_files},
                "ST simulation did not create kpi_yearly_final.csv",
            )
            for csv_path in csv_files:
                with self.subTest(csv=csv_path.name):
                    df = self._read_csv_normalized(csv_path)
                    self.assertGreater(
                        len(df.columns), 0,
                        f"Invalid CSV without columns: {csv_path}",
                    )
            print(
                "ST simulation executed successfully; CSV structure verified. "
                "Set ORIOM_ST_GOLDEN_DIR for numerical regression comparisons."
            )

if __name__ == "__main__":
    unittest.main(verbosity=2)