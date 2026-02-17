import unittest
from unittest.case import skip
import os
from copy import deepcopy

from oriom.classes.Power import Curve
from oriom.classes.Power import Matrix


class TestCurve(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.file = os.path.join(os.getcwd(), 'tests', 'test_files', 'pcurve_wind.csv')
        self.pcurve = Curve(
                file_=self.file,
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
        self.assertAlmostEquals(pcurve.c_in, 3)
        self.assertIsInstance(pcurve.c_off, float)
        self.assertAlmostEquals(pcurve.c_off, 25)

        self.assertEqual(self.pcurve.array[0], 0)
        self.assertEqual(self.pcurve.array[7], 1850)
        self.assertEqual(self.pcurve.array[-1], 0)

    def test_errors(self):
        args_default = [
                self.file,
                3.0, 25.0,
                8000
        ]
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
    def setUpClass(self):
        self.file = os.path.join(os.getcwd(), 'tests', 'test_files', 'pmatrix_wave.csv')
        self.pmatrix = Matrix(
                file_=self.file,
                rated=450
        )

    def test_init(self):
        pcurve = Matrix(
                file_=self.file,
                rated='450'
        )
        self.assertIsInstance(pcurve.rated, float)
        self.assertAlmostEquals(pcurve.rated, 450)

    @skip
    def test_errors(self):
        args_default = {
                'file_': self.file,
                'rated': 8000
        }
        args = deepcopy(args_default)
        args["c_in"] = None
        self.assertRaises(TypeError, Matrix, **args)
        args = deepcopy(args_default)
        args["c_off"] = None
        self.assertRaises(TypeError, Matrix, **args)
        args = deepcopy(args_default)
        args["rated"] = None
        self.assertRaises(TypeError, Matrix, **args)

        args = deepcopy(args_default)
        args["c_in"] = 'three'
        self.assertRaises(ValueError, Matrix, **args)
        args = deepcopy(args_default)
        args["c_off"] = 'twenty-five'
        self.assertRaises(ValueError, Matrix, **args)
        args = deepcopy(args_default)
        args["rated"] = 'eight thousand'
        self.assertRaises(ValueError, Matrix, **args)

        args = deepcopy(args_default)
        args["file_"] = 'other_file'
        self.assertRaises(FileNotFoundError, Matrix, **args)


if __name__ == '__main__':
    unittest.main()
