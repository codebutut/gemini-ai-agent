import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from core.attachment_manager import AttachmentManager


class TestAttachmentManager(unittest.TestCase):
    def setUp(self):
        self.am = AttachmentManager()
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        self.am.cleanup()
        shutil.rmtree(self.test_dir)

    def test_add_single_file(self):
        test_file = Path(self.test_dir) / "test.txt"
        test_file.write_text("hello")

        files = self.am.add_attachment(str(test_file))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], str(test_file))
        self.assertIn(str(test_file), self.am.get_attachments())

    def test_add_directory(self):
        test_dir = Path(self.test_dir) / "test_dir"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("1")
        (test_dir / "file2.txt").write_text("2")

        files = self.am.add_attachment(str(test_dir))
        self.assertEqual(len(files), 2)
        self.assertTrue(any("file1.txt" in f for f in files))
        self.assertTrue(any("file2.txt" in f for f in files))

    def test_add_zip_archive(self):
        zip_path = Path(self.test_dir) / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr("archived.txt", "content")

        files = self.am.add_attachment(str(zip_path))
        self.assertEqual(len(files), 1)
        self.assertIn("archived.txt", files[0])
        self.assertTrue(Path(files[0]).exists())

    def test_clear_attachments(self):
        test_file = Path(self.test_dir) / "test.txt"
        test_file.write_text("hello")
        self.am.add_attachment(str(test_file))

        self.am.clear_attachments()
        self.assertEqual(len(self.am.get_attachments()), 0)

    def test_cleanup(self):
        am = AttachmentManager()
        temp_dir = am.temp_dir
        self.assertTrue(temp_dir.exists())
        am.cleanup()
        self.assertFalse(temp_dir.exists())


if __name__ == "__main__":
    unittest.main()
