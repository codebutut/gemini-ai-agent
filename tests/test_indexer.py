import os
import shutil
import tempfile
import unittest

from core.indexer import Indexer


class TestIndexer(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.indexer = Indexer(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_test_file(self, filename, content):
        path = os.path.join(self.test_dir, filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_index_simple_file(self):
        content = """
class MyClass:
    \"\"\"Docstring for MyClass\"\"\"
    def my_method(self, x):
        return x

def my_function(y):
    return y
"""
        self.create_test_file("test.py", content)
        self.indexer.index_project()

        symbols = self.indexer.get_all_symbols()
        self.assertEqual(len(symbols), 3)

        names = [s.name for s in symbols]
        self.assertIn("MyClass", names)
        self.assertIn("my_method", names)
        self.assertIn("my_function", names)

        my_class = next(s for s in symbols if s.name == "MyClass")
        self.assertEqual(my_class.kind, "class")
        self.assertEqual(my_class.docstring, "Docstring for MyClass")

        my_method = next(s for s in symbols if s.name == "my_method")
        self.assertEqual(my_method.kind, "method")
        self.assertEqual(my_method.parent, "MyClass")

        my_function = next(s for s in symbols if s.name == "my_function")
        self.assertEqual(my_function.kind, "function")
        self.assertIsNone(my_function.parent)

    def test_search(self):
        content = "def search_me(): pass"
        self.create_test_file("search.py", content)
        self.indexer.index_project()

        results = self.indexer.search("search")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "search_me")

    def test_skip_directories(self):
        self.create_test_file("env/ignored.py", "def ignored(): pass")
        self.create_test_file("src/included.py", "def included(): pass")
        self.indexer.index_project()

        symbols = self.indexer.get_all_symbols()
        names = [s.name for s in symbols]
        self.assertIn("included", names)
        self.assertNotIn("ignored", names)


if __name__ == "__main__":
    unittest.main()
