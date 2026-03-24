
import os
import unittest
import tempfile
from datetime import datetime

from oriom.inputs.Configuration import ConfigRun, ProjectDirs


class DummyLogger:
    """Minimal logger to capture .info calls."""
    def __init__(self):
        self.messages = []

    def info(self, msg, *args):
        if args:
            try:
                formatted = msg % args
            except TypeError:
                formatted = msg.format(*args)
            self.messages.append(formatted)
        else:
            self.messages.append(msg)


class TestConfigRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid_kwargs = {
            "PROJECT_NAME": "MyProject",
            "BASEFILES_FROM_EXCEL": False,
            "EXCEL_FILE_PATH": "/tmp/example.xlsx",
            "FORM_NAME": "MyForm",
        }

    def test_default_constructor_raises_due_to_required_fields(self):
        with self.assertRaises(ValueError):
            ConfigRun()

    def test_valid_config_without_excel_source_is_ok(self):
        cfg = ConfigRun(**self.valid_kwargs)
        self.assertTrue(cfg.STATISTICAL_CHART)
        self.assertEqual(cfg.PROJECT_NAME, "MyProject")
        self.assertFalse(cfg.BASEFILES_FROM_EXCEL)
        self.assertEqual(cfg.EXCEL_FILE_PATH, "/tmp/example.xlsx")
        self.assertEqual(cfg.FORM_NAME, "MyForm")
        for fname in (
            "attributes.yaml",
            "activities.csv",
            "workability.csv",
            "startability.csv",
            "operation_schedule.csv",
            'towing_inspection_log.csv'
        ):
            self.assertIn(fname, cfg.OPERATION_FILES)

    def test_excel_source_requires_sharepoint_path(self):
        bad_kwargs = dict(self.valid_kwargs, BASEFILES_FROM_EXCEL=True, SOURCE_PATH_SHAREPOINT=None)
        with self.assertRaises(ValueError):
            ConfigRun(**bad_kwargs)

        ok_kwargs = dict(bad_kwargs, SOURCE_PATH_SHAREPOINT="/mnt/share/ProjectA")
        cfg = ConfigRun(**ok_kwargs)
        self.assertEqual(cfg.SOURCE_PATH_SHAREPOINT, "/mnt/share/ProjectA")

    def test_log_parameters_emits_expected_blocks(self):
        cfg = ConfigRun(**self.valid_kwargs)
        logger = DummyLogger()

        class InputsGen:
            previous_run_dir = {"value": "/runs/2025-09-25_12-00-00"}

        cfg.log_parameters(logger, inputs_gen=InputsGen())
        joined = "\n".join(logger.messages)
        self.assertIn("INPUTS - GENERAL", joined)
        self.assertIn("STATISTICAL_CHART: True", joined)
        self.assertIn("PROJECT_NAME: MyProject", joined)
        self.assertIn("TIME_FAIL_OP_IMMEDIATELY: 0.02", joined)
        self.assertIn("previous timeseries: /runs/2025-09-25_12-00-00", joined)

    def test_log_parameters_ignores_bad_inputs_gen(self):
        cfg = ConfigRun(**self.valid_kwargs)
        logger = DummyLogger()

        class BadInputsGen:
            something_else = 123

        cfg.log_parameters(logger, inputs_gen=BadInputsGen())
        self.assertFalse(any("previous timeseries:" in m for m in logger.messages))


class TestProjectDirs(unittest.TestCase):
    def setUp(self):
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_ctx.cleanup)
        self.original_cwd = os.getcwd()
        os.chdir(self.tmp_ctx.name)

    def tearDown(self):
        os.chdir(self.original_cwd)

    def test_create_builds_all_directories_under_tmp(self):
        d = ProjectDirs.create(project_name="UnitTestProj")
        self.assertTrue(os.path.isdir(d.tmp_dir))
        self.assertTrue(os.path.isdir(d.run_dir))
        for sub in (
            d.operation_dir,
            d.graph_dir,
            d.result_dir,
            d.result_dir_avg,
            d.base_dir,
        ):
            self.assertTrue(os.path.isdir(sub))
        rep = repr(d)
        self.assertIn("UnitTestProj", rep)
        self.assertIn("ProjectDirs(", rep)

    def test_direct_instantiation_respects_cwd_tmp(self):
        d = ProjectDirs("DirectProj")
        self.assertTrue(os.path.isdir(d.tmp_dir))
        self.assertIn("DirectProj", d.run_dir)
        for sub in (
            d.operation_dir,
            d.graph_dir,
            d.result_dir,
            d.result_dir_avg,
            d.base_dir,
        ):
            self.assertTrue(os.path.isdir(sub))


if __name__ == '__main__':
    unittest.main(verbosity=2)

