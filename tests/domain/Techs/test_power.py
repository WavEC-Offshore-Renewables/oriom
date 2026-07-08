import unittest
from unittest.case import skip
import os
from copy import deepcopy
import tempfile

from oriom.domain.Techs.Power import Curve
from oriom.domain.Techs.Power import Matrix
from oriom.domain.Techs.Power import Power_Losses


class TestCurve(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.file = os.path.join(os.getcwd(), 'tests', 'test_files', 'pcurve_wind.csv')
        cls.pcurve = Curve(
            file_=cls.file,
            c_in=3,
            c_off=25,
            rated=8000
        )

    def test_init(self):
        pcurve = Curve(
            file_=self.file,
            c_in='3',
            c_off='25',
            rated='8000'
        )

        self.assertIsInstance(pcurve.c_in, float)
        self.assertAlmostEqual(pcurve.c_in, 3)

        self.assertIsInstance(pcurve.c_off, float)
        self.assertAlmostEqual(pcurve.c_off, 25)

        self.assertEqual(self.pcurve.array[0], 0)
        self.assertEqual(self.pcurve.array[7], 1850)
        self.assertEqual(self.pcurve.array[-1], 0)

    def test_errors(self):
        args_default = {
            'file_': self.file,
            'c_in': 3.0,
            'c_off': 25.0,
            'rated': 8000
        }

        args = deepcopy(args_default)
        args["c_in"] = None
        self.assertRaises(TypeError, Curve, **args)

        args = deepcopy(args_default)
        args["c_off"] = None
        self.assertRaises(TypeError, Curve, **args)

        args = deepcopy(args_default)
        args["rated"] = None
        self.assertRaises(TypeError, Curve, **args)

        args = deepcopy(args_default)
        args["c_in"] = 'three'
        self.assertRaises(ValueError, Curve, **args)

        args = deepcopy(args_default)
        args["c_off"] = 'twenty-five'
        self.assertRaises(ValueError, Curve, **args)

        args = deepcopy(args_default)
        args["rated"] = 'eight thousand'
        self.assertRaises(ValueError, Curve, **args)

        args = deepcopy(args_default)
        args["c_in"] = -1
        self.assertRaises(ValueError, Curve, **args)

        args = deepcopy(args_default)
        args["c_off"] = -1
        self.assertRaises(ValueError, Curve, **args)

        args = deepcopy(args_default)
        args["rated"] = -1
        self.assertRaises(ValueError, Curve, **args)

        args = deepcopy(args_default)
        args["file_"] = 'other_file'
        self.assertRaises(FileNotFoundError, Curve, **args)


class TestMatrixCurve(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.file = os.path.join(os.getcwd(), 'tests', 'test_files', 'pmatrix_wave.csv')
        cls.pmatrix = Matrix(
            file_=cls.file,
            rated=450
        )

    def test_init(self):
        pmatrix = Matrix(
            file_=self.file,
            rated='450'
        )

        self.assertIsInstance(pmatrix.rated, float)
        self.assertAlmostEqual(pmatrix.rated, 450)

    @skip
    def test_errors(self):
        args_default = {
            'file_': self.file,
            'rated': 8000
        }

        args = deepcopy(args_default)
        args["rated"] = None
        self.assertRaises(TypeError, Matrix, **args)

        args = deepcopy(args_default)
        args["rated"] = 'eight thousand'
        self.assertRaises(ValueError, Matrix, **args)

        args = deepcopy(args_default)
        args["file_"] = 'other_file'
        self.assertRaises(FileNotFoundError, Matrix, **args)


class TestPowerLosses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.TemporaryDirectory()

        cls.file_electric_loss = cls._write_csv(
            'electric_loss.csv',
            'p_wind_kw;power_loss\n'
            '2;0.20\n'
            '0;0.00\n'
            '2;0.40\n'
            '1;0.10\n'
        )

        cls.file_wake_loss = cls._write_csv(
            'wake_loss.csv',
            'wind_speed_m/s;power_loss\n'
            '0;0.00\n'
            '1;0.05\n'
            '2;0.10\n'
        )

    @classmethod
    def tearDownClass(cls):
        cls.tmp_dir.cleanup()

    @classmethod
    def _write_csv(cls, file_name, content):
        file_ = os.path.join(cls.tmp_dir.name, file_name)

        with open(file_, 'w', encoding='utf-8') as f:
            f.write(content)

        return file_

    def test_init_without_losses(self):
        p_losses = Power_Losses()

        self.assertFalse(p_losses.power_loss)
        self.assertTrue(p_losses.electric_loss.empty)
        self.assertTrue(p_losses.wake_loss.empty)

    def test_init_with_electric_loss(self):
        p_losses = Power_Losses(
            file_electric_loss=self.file_electric_loss
        )

        self.assertTrue(p_losses.power_loss)
        self.assertFalse(p_losses.electric_loss.empty)
        self.assertTrue(p_losses.wake_loss.empty)

        self.assertEqual(
            p_losses.electric_loss.columns.to_list(),
            ['p_wind_kw', 'power_loss']
        )

        self.assertEqual(
            p_losses.electric_loss['p_wind_kw'].to_list(),
            [0, 1, 2]
        )

        expected_power_loss = [0.00, 0.10, 0.30]

        for result, expected in zip(p_losses.electric_loss['power_loss'].to_list(), expected_power_loss):
            self.assertAlmostEqual(result, expected)

    def test_init_with_wake_loss(self):
        p_losses = Power_Losses(file_wake_loss=self.file_wake_loss)

        self.assertTrue(p_losses.power_loss)
        self.assertTrue(p_losses.electric_loss.empty)
        self.assertFalse(p_losses.wake_loss.empty)

        self.assertEqual(
            p_losses.wake_loss.columns.to_list(),
            ['ws', 'power_loss']
        )

        self.assertEqual(
            p_losses.wake_loss['ws'].to_list(),
            [0, 1, 2]
        )

        expected_power_loss = [0.00, 0.05, 0.10]

        for result, expected in zip(
            p_losses.wake_loss['power_loss'].to_list(),
            expected_power_loss
        ):
            self.assertAlmostEqual(result, expected)

    def test_init_with_electric_and_wake_losses(self):
        p_losses = Power_Losses(
            file_electric_loss=self.file_electric_loss,
            file_wake_loss=self.file_wake_loss
        )

        self.assertTrue(p_losses.power_loss)
        self.assertFalse(p_losses.electric_loss.empty)
        self.assertFalse(p_losses.wake_loss.empty)

    def test_error_file_not_found(self):
        file_ = os.path.join(self.tmp_dir.name, 'missing_file.csv')

        self.assertRaises(
            FileNotFoundError,
            Power_Losses,
            file_electric_loss=file_
        )

    def test_error_missing_column(self):
        file_ = self._write_csv(
            'missing_column.csv',
            'p_wind_kw\n'
            '0\n'
            '1\n'
        )

        self.assertRaises(
            IndexError,
            Power_Losses,
            file_electric_loss=file_
        )

    def test_error_too_many_columns(self):
        file_ = self._write_csv(
            'too_many_columns.csv',
            'p_wind_kw;power_loss;extra_column\n'
            '0;0.00;1\n'
            '1;0.10;1\n'
        )

        self.assertRaises(
            IndexError,
            Power_Losses,
            file_electric_loss=file_
        )

    def test_error_wrong_power_loss_column_name(self):
        file_ = self._write_csv(
            'wrong_power_loss_column.csv',
            'p_wind_kw;loss\n'
            '0;0.00\n'
            '1;0.10\n'
        )

        self.assertRaises(
            ValueError,
            Power_Losses,
            file_electric_loss=file_
        )

    def test_error_invalid_independent_variable_column(self):
        file_ = self._write_csv(
            'invalid_independent_variable.csv',
            'wrong_variable;power_loss\n'
            '0;0.00\n'
            '1;0.10\n'
        )

        self.assertRaises(
            ValueError,
            Power_Losses,
            file_electric_loss=file_
        )

    def test_error_non_numeric_power_loss(self):
        file_ = self._write_csv(
            'non_numeric_power_loss.csv',
            'p_wind_kw;power_loss\n'
            '0;0.00\n'
            '1;wrong_value\n'
        )

        self.assertRaises(
            TypeError,
            Power_Losses,
            file_electric_loss=file_
        )

    def test_error_negative_power_loss(self):
        file_ = self._write_csv(
            'negative_power_loss.csv',
            'wind_speed_m/s;power_loss\n'
            '0;0.00\n'
            '1;-0.10\n'
        )

        self.assertRaises(
            ValueError,
            Power_Losses,
            file_electric_loss=file_
        )

    def test_error_power_loss_greater_than_one(self):
        file_ = self._write_csv(
            'power_loss_greater_than_one.csv',
            'p_wind_kw;power_loss\n'
            '0;0.00\n'
            '1;1.10\n'
        )

        self.assertRaises(
            ValueError,
            Power_Losses,
            file_electric_loss=file_
        )

    def test_nan_values_are_dropped_from_both_columns(self):
        file_ = self._write_csv(
            'nan_values_are_dropped.csv',
            'p_wind_kw;power_loss\n'
            '0.0;0.00\n'
            ';0.10\n'
            '2.0;\n'
            '3.0;0.30\n'
            '5.0;0.50\n'
        )

        p_losses = Power_Losses(file_electric_loss=file_)

        self.assertTrue(p_losses.power_loss)
        self.assertFalse(p_losses.electric_loss.empty)

        self.assertEqual(
            p_losses.electric_loss['p_wind_kw'].to_list(),
            [0.0, 3.0, 5.0]
        )

        expected_power_loss = [0.00, 0.30, 0.50]

        for result, expected in zip(
            p_losses.electric_loss['power_loss'].to_list(),
            expected_power_loss
        ):
            self.assertAlmostEqual(result, expected)

    def test_long_unordered_irregular_steps(self):
        file_ = self._write_csv(
            'long_unordered_irregular_steps.csv',
            'p_wind_kw;power_loss\n'
            '12.5;0.30\n'
            '0.0;0.00\n'
            '7.2;0.12\n'
            '3.0;0.03\n'
            '15.0;0.45\n'
            '1.5;0.01\n'
            '9.8;0.20\n'
            '4.7;0.07\n'
            '20.0;0.80\n'
            '6.1;0.10\n'
            '18.4;0.65\n'
            '2.2;0.02\n'
            '11.0;0.25\n'
            '13.7;0.35\n'
            '5.5;0.09\n'
        )

        p_losses = Power_Losses(file_electric_loss=file_)

        expected_p_wind_kw = [
            0.0, 1.5, 2.2, 3.0, 4.7,
            5.5, 6.1, 7.2, 9.8, 11.0,
            12.5, 13.7, 15.0, 18.4, 20.0
        ]

        expected_power_loss = [
            0.00, 0.01, 0.02, 0.03, 0.07,
            0.09, 0.10, 0.12, 0.20, 0.25,
            0.30, 0.35, 0.45, 0.65, 0.80
        ]

        self.assertEqual(
            p_losses.electric_loss['p_wind_kw'].to_list(),
            expected_p_wind_kw
        )

        for result, expected in zip(
            p_losses.electric_loss['power_loss'].to_list(),
            expected_power_loss
        ):
            self.assertAlmostEqual(result, expected)

    def test_long_unordered_irregular_steps_with_nan_values(self):
        file_ = self._write_csv(
            'long_unordered_irregular_steps_with_nan.csv',
            'p_wind_kw;power_loss\n'
            '12.5;0.30\n'
            '0.0;0.00\n'
            ';0.99\n'
            '7.2;0.12\n'
            '3.0;0.03\n'
            '15.0;\n'
            '1.5;0.01\n'
            '9.8;0.20\n'
            '4.7;0.07\n'
            '20.0;0.80\n'
            '6.1;0.10\n'
            '18.4;0.65\n'
            '2.2;0.02\n'
            '11.0;0.25\n'
            '13.7;0.35\n'
            '5.5;0.09\n'
        )

        p_losses = Power_Losses(file_electric_loss=file_)

        expected_p_wind_kw = [
            0.0, 1.5, 2.2, 3.0, 4.7,
            5.5, 6.1, 7.2, 9.8, 11.0,
            12.5, 13.7, 18.4, 20.0
        ]

        expected_power_loss = [
            0.00, 0.01, 0.02, 0.03, 0.07,
            0.09, 0.10, 0.12, 0.20, 0.25,
            0.30, 0.35, 0.65, 0.80
        ]

        self.assertEqual(
            p_losses.electric_loss['p_wind_kw'].to_list(),
            expected_p_wind_kw
        )

        for result, expected in zip(
            p_losses.electric_loss['power_loss'].to_list(),
            expected_power_loss
        ):
            self.assertAlmostEqual(result, expected)

    def test_unordered_irregular_steps_with_duplicated_values(self):
        file_ = self._write_csv(
            'unordered_irregular_steps_with_duplicates.csv',
            'p_wind_kw;power_loss\n'
            '10.0;0.20\n'
            '0.0;0.00\n'
            '4.5;0.08\n'
            '10.0;0.30\n'
            '1.2;0.01\n'
            '7.7;0.15\n'
            '4.5;0.10\n'
            '15.5;0.50\n'
            '2.8;0.04\n'
        )

        p_losses = Power_Losses(file_electric_loss=file_)

        expected_p_wind_kw = [
            0.0, 1.2, 2.8, 4.5, 7.7, 10.0, 15.5
        ]

        expected_power_loss = [
            0.00, 0.01, 0.04, 0.09, 0.15, 0.25, 0.50
        ]

        self.assertEqual(
            p_losses.electric_loss['p_wind_kw'].to_list(),
            expected_p_wind_kw
        )

        for result, expected in zip(
            p_losses.electric_loss['power_loss'].to_list(),
            expected_power_loss
        ):
            self.assertAlmostEqual(result, expected)

    def test_unordered_irregular_steps_with_duplicates_and_nan_values(self):
        file_ = self._write_csv(
            'unordered_irregular_steps_with_duplicates_and_nan.csv',
            'p_wind_kw;power_loss\n'
            '10.0;0.20\n'
            '0.0;0.00\n'
            '4.5;0.08\n'
            '10.0;0.30\n'
            ';0.99\n'
            '1.2;0.01\n'
            '7.7;0.15\n'
            '4.5;\n'
            '4.5;0.10\n'
            '15.5;0.50\n'
            '2.8;0.04\n'
        )

        p_losses = Power_Losses(file_electric_loss=file_)

        expected_p_wind_kw = [
            0.0, 1.2, 2.8, 4.5, 7.7, 10.0, 15.5
        ]

        expected_power_loss = [
            0.00, 0.01, 0.04, 0.09, 0.15, 0.25, 0.50
        ]

        self.assertEqual(
            p_losses.electric_loss['p_wind_kw'].to_list(),
            expected_p_wind_kw
        )

        for result, expected in zip(
            p_losses.electric_loss['power_loss'].to_list(),
            expected_power_loss
        ):
            self.assertAlmostEqual(result, expected)

    def test_irregular_steps_are_not_interpolated(self):
        file_ = self._write_csv(
            'irregular_steps_not_interpolated.csv',
            'p_wind_kw;power_loss\n'
            '0.0;0.00\n'
            '0.5;0.01\n'
            '2.7;0.05\n'
            '8.3;0.20\n'
            '20.0;0.75\n'
        )

        p_losses = Power_Losses(file_electric_loss=file_)

        self.assertEqual(len(p_losses.electric_loss), 5)

        self.assertEqual(
            p_losses.electric_loss['p_wind_kw'].to_list(),
            [0.0, 0.5, 2.7, 8.3, 20.0]
        )

        expected_power_loss = [0.00, 0.01, 0.05, 0.20, 0.75]

        for result, expected in zip(
            p_losses.electric_loss['power_loss'].to_list(),
            expected_power_loss
        ):
            self.assertAlmostEqual(result, expected)


if __name__ == '__main__':
    unittest.main()