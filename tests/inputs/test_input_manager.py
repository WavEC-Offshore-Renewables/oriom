# tests/test_inputs_module.py
import os
import tempfile
import unittest
from unittest.mock import patch  # <-- manca nel tuo file

from logistic_tools.inputs.Input_manager import (
    Input_Files,
    extract_input_from_excel,
    handle_overwrite_previous,
    FILE_MAP,
)


class TestInputFilesMore(unittest.TestCase):
    def setUp(self):
        self.tmp_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_ctx.cleanup)
        self.base_dir = self.tmp_ctx.name
        self.files = Input_Files(self.base_dir)

    def test_validate_success_when_all_exist(self):
        for _, fname in FILE_MAP.items():
            path = os.path.join(self.base_dir, fname)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("# present\n")

        missing = self.files.validate(must_exist=True)
        self.assertEqual(missing, [])

    def test_iterators_and_as_dict_match_FILE_MAP(self):
        d = self.files.as_dict()
        self.assertEqual(set(d.keys()), set(FILE_MAP.keys()))
        vals = list(self.files.values())
        items = list(self.files.items())
        self.assertEqual(len(vals), len(FILE_MAP))
        self.assertEqual(len(items), len(FILE_MAP))
        for key, path in items:
            self.assertTrue(path.endswith(os.path.join(self.base_dir, FILE_MAP[key])))


class TestExtractInputFromExcelOverwriteAndEdge(unittest.TestCase):
    def setUp(self):
        self.cwd_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.cwd_ctx.cleanup)
        self.old_cwd = os.getcwd()
        os.chdir(self.cwd_ctx.name)

        class FakeDirs:
            pass

        self.dirs = FakeDirs()
        self.dirs.tmp_dir = os.path.join(os.getcwd(), "tmp")
        self.dirs.base_dir = os.path.join(os.getcwd(), "out_base")
        os.makedirs(self.dirs.tmp_dir, exist_ok=True)
        os.makedirs(self.dirs.base_dir, exist_ok=True)

    def tearDown(self):
        # Torna fuori prima di distruggere la TemporaryDirectory (evita lock su Windows)
        os.chdir(self.old_cwd)

    @patch("logistic_tools.inputs.Input_manager.excel_to_yaml")
    def test_local_excel_overwrites_existing_yaml(self, m_excel_to_yaml):
        target_yaml = os.path.join(self.dirs.base_dir, "inputs_gen.yaml")
        with open(target_yaml, "w", encoding="utf-8") as f:
            f.write("OLD")

        local_dir = os.path.join(os.getcwd(), "local_inputs")
        os.makedirs(local_dir, exist_ok=True)

        extract_input_from_excel(
            dirs=self.dirs,
            base_file_excel=False,
            sharepoint_file_path=None,
            excel_file_path=local_dir,
            form_name="Form.xlsx",
        )

        m_excel_to_yaml.assert_called_once_with(
            file_excel=os.path.join(local_dir, "Form.xlsx"),
            out_dir=self.dirs.base_dir,
        )

    def test_fallback_only_yaml_yml_copied_and_overwritten(self):
        tests_inputs_dir = os.path.join(os.getcwd(), "tests", "test_files", "inputs")
        os.makedirs(tests_inputs_dir, exist_ok=True)

        with open(os.path.join(tests_inputs_dir, "a.yaml"), "w", encoding="utf-8") as f:
            f.write("SRC_A")
        with open(os.path.join(tests_inputs_dir, "b.yml"), "w", encoding="utf-8") as f:
            f.write("SRC_B")
        with open(os.path.join(tests_inputs_dir, "c.txt"), "w", encoding="utf-8") as f:
            f.write("IGNORE")

        dest_a = os.path.join(self.dirs.base_dir, "a.yaml")
        with open(dest_a, "w", encoding="utf-8") as f:
            f.write("OLD_A")

        extract_input_from_excel(
            dirs=self.dirs,
            base_file_excel=False,
            sharepoint_file_path=None,
            excel_file_path=None,
            form_name="ignored.xlsx",
        )

        self.assertTrue(os.path.exists(os.path.join(self.dirs.base_dir, "a.yaml")))
        self.assertTrue(os.path.exists(os.path.join(self.dirs.base_dir, "b.yml")))
        self.assertFalse(os.path.exists(os.path.join(self.dirs.base_dir, "c.txt")))
        with open(os.path.join(self.dirs.base_dir, "a.yaml"), "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "SRC_A")

    @patch("logistic_tools.inputs.Input_manager.msoffice365_sharepoint.download_file")
    @patch("logistic_tools.inputs.Input_manager.excel_to_yaml")
    def test_sharepoint_branch_downloads_and_converts(self, m_excel_to_yaml, m_download):
        extract_input_from_excel(
            dirs=self.dirs,
            base_file_excel=True,
            sharepoint_file_path="/Share/Forms/FormA.xlsx",
            excel_file_path=None,
            form_name="FormA.xlsx",
        )
        m_download.assert_called_once()
        m_excel_to_yaml.assert_called_once_with(
            file_excel=os.path.join(os.getcwd(), "tmp", "FormA.xlsx"),
            out_dir=self.dirs.base_dir,
        )


class TestHandleOverwritePreviousMore(unittest.TestCase):
    def setUp(self):
        self.cwd_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(self.cwd_ctx.cleanup)
        self.old_cwd = os.getcwd()
        os.chdir(self.cwd_ctx.name)

        self.run_dir = os.path.join(os.getcwd(), "tmp", "RunY")
        self.prev_dir = os.path.join(os.getcwd(), "tmp", "PrevY")
        os.makedirs(self.run_dir, exist_ok=True)
        os.makedirs(self.prev_dir, exist_ok=True)

        self.operation_dir = os.path.join(self.run_dir, "operation_dir")
        self.graph_dir = os.path.join(self.run_dir, "graph_dir")
        self.result_dir = os.path.join(self.run_dir, "result_dir")
        self.result_dir_avg = os.path.join(self.run_dir, "result_dir_avg")
        self.base_dir = os.path.join(self.run_dir, "base_files")
        for d in [self.operation_dir, self.graph_dir, self.result_dir, self.result_dir_avg, self.base_dir]:
            os.makedirs(d, exist_ok=True)

        with open(os.path.join(self.run_dir, "keep.txt"), "w", encoding="utf-8") as f:
            f.write("move me")

        os.makedirs(os.path.join(self.prev_dir, "graph_dir"), exist_ok=True)
        os.makedirs(os.path.join(self.prev_dir, "result_dir"), exist_ok=True)
        with open(os.path.join(self.prev_dir, "result_dir", "old.txt"), "w", encoding="utf-8") as f:
            f.write("old")
        with open(os.path.join(self.prev_dir, "keep.txt"), "w", encoding="utf-8") as f:
            f.write("old-keep")
        with open(os.path.join(self.prev_dir, "logging.log"), "w", encoding="utf-8") as f:
            f.write("old log")

        class FakeDirs:
            pass

        self.dirs = FakeDirs()
        self.dirs.run_dir = self.run_dir
        self.dirs.graph_dir = self.graph_dir
        self.dirs.operation_dir = self.operation_dir
        self.dirs.result_dir = self.result_dir
        self.dirs.result_dir_avg = self.result_dir_avg
        self.dirs.base_dir = self.base_dir

        class InputsGen:
            overwrite_previous = {"value": True}
            previous_run_dir = {"value": self.prev_dir}

        self.inputs = InputsGen

    def tearDown(self):
        os.chdir(self.old_cwd)

    def test_moves_over_conflicts_and_updates_paths(self):
        handle_overwrite_previous(self.inputs, self.dirs)

        self.assertEqual(self.dirs.run_dir, self.prev_dir)
        self.assertFalse(os.path.exists(os.path.join(self.prev_dir, "logging.log")))

        self.assertTrue(os.path.exists(os.path.join(self.prev_dir, "graph_dir")))
        self.assertTrue(os.path.exists(os.path.join(self.prev_dir, "result_dir")))
        self.assertTrue(os.path.exists(os.path.join(self.prev_dir, "result_dir_avg")))
        self.assertTrue(os.path.exists(os.path.join(self.prev_dir, "base_files")))
        self.assertTrue(os.path.exists(os.path.join(self.prev_dir, "keep.txt")))

        self.assertFalse(os.path.exists(os.path.join(self.prev_dir, "result_dir", "old.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.prev_dir, "operation_dir")))
        self.assertFalse(os.path.exists(self.run_dir))

        self.assertEqual(self.dirs.graph_dir, os.path.join(self.prev_dir, "graph_dir"))
        self.assertEqual(self.dirs.operation_dir, os.path.join(self.prev_dir, "operation_dir"))
        self.assertEqual(self.dirs.result_dir, os.path.join(self.prev_dir, "result_dir"))
        self.assertEqual(self.dirs.base_dir, os.path.join(self.prev_dir, "base_files"))

    def test_no_overwrite_when_flag_false(self):
        class InputsGen:
            overwrite_previous = {"value": False}
            previous_run_dir = {"value": self.prev_dir}

        handle_overwrite_previous(InputsGen, self.dirs)
        self.assertTrue(os.path.exists(self.run_dir))
        self.assertEqual(self.dirs.run_dir, self.run_dir)

    def test_typeerror_is_swallowed(self):
        class TypeErrorInputs:
            overwrite_previous = None  # non-subscriptable -> TypeError

        handle_overwrite_previous(TypeErrorInputs, self.dirs)
        self.assertTrue(os.path.exists(self.run_dir))
        self.assertEqual(self.dirs.run_dir, self.run_dir)


if __name__ == '__main__':
    unittest.main(verbosity=2)
