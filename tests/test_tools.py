import unittest
import os
import sys
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.tools import list_files, read_file, write_file, run_python

class TestFileTools(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.txt")
        with open(self.test_file, "w") as f:
            f.write("Hello World")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_list_files(self):
        result = list_files(self.test_dir)
        self.assertIn("test.txt", result)

    def test_read_file(self):
        content = read_file(self.test_file)
        self.assertEqual(content, "Hello World")

    def test_write_file(self):
        new_file = os.path.join(self.test_dir, "new.txt")
        result = write_file(new_file, "New Content")
        self.assertIn("Successfully wrote", result)
        self.assertEqual(read_file(new_file), "New Content")

class TestPythonExecution(unittest.TestCase):
    def test_run_python_simple(self):
        code = "print('Hello from Python')"
        result = run_python(code)
        self.assertIn("Hello from Python", result)

    def test_run_python_error(self):
        code = "raise ValueError('Oops')"
        result = run_python(code)
        self.assertIn("ValueError: Oops", result)

if __name__ == '__main__':
    unittest.main()