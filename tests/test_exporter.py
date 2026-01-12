import unittest
import json
import zipfile
from pathlib import Path
import tempfile
import shutil
from core.exporter import Exporter

class TestExporter(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.session_data = {
            "title": "Test Session",
            "created_at": "2023-10-27T10:00:00",
            "plan": "Test Plan",
            "specs": "Test Specs",
            "messages": [
                {"role": "user", "text": "Hello", "timestamp": "2023-10-27T10:01:00"},
                {"role": "model", "text": "Hi there!", "timestamp": "2023-10-27T10:01:05"}
            ]
        }

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_session_to_markdown(self):
        md = Exporter.session_to_markdown(self.session_data)
        self.assertIn("# Test Session", md)
        self.assertIn("## Plan", md)
        self.assertIn("Test Plan", md)
        self.assertIn("## Chat History", md)
        self.assertIn("### User", md)
        self.assertIn("Hello", md)
        self.assertIn("### Model", md)
        self.assertIn("Hi there!", md)

    def test_export_to_file(self):
        filepath = self.test_dir / "export.md"
        success = Exporter.export_to_file(self.session_data, filepath)
        self.assertTrue(success)
        self.assertTrue(filepath.exists())
        content = filepath.read_text(encoding="utf-8")
        self.assertIn("# Test Session", content)

    def test_create_backup(self):
        sessions = {"sess1": self.session_data}
        backup_path = self.test_dir / "backup.zip"
        success = Exporter.create_backup(sessions, backup_path)
        self.assertTrue(success)
        self.assertTrue(backup_path.exists())
        
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            self.assertIn("history.json", zipf.namelist())
            self.assertIn("sessions/Test_Session_sess1.md", zipf.namelist())

    def test_restore_backup(self):
        sessions = {"sess1": self.session_data}
        backup_path = self.test_dir / "backup.zip"
        Exporter.create_backup(sessions, backup_path)
        
        restored = Exporter.restore_backup(backup_path)
        self.assertEqual(restored["sess1"]["title"], "Test Session")

if __name__ == "__main__":
    unittest.main()
