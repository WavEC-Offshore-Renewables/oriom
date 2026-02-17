import unittest
import os

from oriom.classes.Inputs import Inputs


def skipIfNotLocal():
    """
    Decorator to check if function is running locally or in some remote
    repository.
    If the current path includes "runner" string, it is assumed the fuction
    is not running locally.
    """
    def deco(f):
        def wrapper(self, *args, **kwargs):
            cur_path = os.getcwd()
            if 'runner' in cur_path.lower():
                self.skipTest('running in a remote repository')
            else:
                f(self, *args, **kwargs)
        return wrapper
    return deco

class TestInputsGeneral(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        test_dir = os.path.join(os.getcwd(), 'tmp', 'test', 'prev')
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)
        prev_test_dir = os.path.join(os.getcwd(), 'tmp', 'test', 'current')
        if not os.path.exists(prev_test_dir):
            os.makedirs(prev_test_dir)
        self.test_file = os.path.join(os.getcwd(), 'tests', 'test_files', 'inputs', 'inputs_gen.yaml')
        self.prev_test_dir = prev_test_dir
        self.test_dir = test_dir

    def std_asserts(self, inputs):
        self.assertIsInstance(inputs.previous_run_dir["value"], str)
        self.assertEqual(
                inputs.previous_run_dir["value"],
                self.test_dir
        )
        self.assertIsInstance(inputs.consider_tseries["value"], bool)
        self.assertEqual(
                inputs.consider_tseries["value"],
                False
        )
        self.assertIsInstance(inputs.out_dir, str)
        self.assertEqual(inputs.out_dir, os.path.join(os.getcwd(), 'tmp', 'test', 'prev'))

    def test_from_file(self):
        inputs = Inputs.General(
                file_inputs=self.test_file,
                out_dir=self.prev_test_dir
        )

    def test_by_hand(self):
        inputs = Inputs.General(
                previous_run_dir=os.path.join(
                        os.getcwd(),
                        'tmp',
                        'test',
                        'prev'
                ),
                consider_tseries=False,
                out_dir=self.test_dir
        )
        self.std_asserts(inputs)

    def test_errors(self):
        args = {}
        self.assertRaises(AttributeError, Inputs.General, **args)
        args["out_dir"] = self.test_dir
        args["previous_run_dir"] = 'something'
        self.assertRaises(FileNotFoundError, Inputs.General, **args)


if __name__ == '__main__':

    unittest.main()
