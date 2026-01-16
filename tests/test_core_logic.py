import html
import shutil
import tempfile
import unittest
from pathlib import Path

# Fix imports to use the package structure
from config.app_config import AppConfig
from core.attachment_manager import AttachmentManager
from core.review_engine import ReviewEngine
from core.session_manager import SessionManager
from utils.helpers import RateLimiter


class TestCoreLogic(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config_file = Path(self.test_dir) / "settings.json"
        self.history_file = Path(self.test_dir) / "history.json"

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_app_config(self):
        # Test default creation
        config = AppConfig(self.config_file)
        self.assertEqual(config.get("theme"), "Dark")

        # Test save and load
        config.set("theme", "Light")
        config.save(sync=True)

        new_config = AppConfig(self.config_file)
        self.assertEqual(new_config.get("theme"), "Light")

    def test_session_manager(self):
        manager = SessionManager(self.history_file)

        # Create session
        sess_id = manager.create_session("Test Chat", sync=True)
        self.assertIsNotNone(sess_id)
        self.assertEqual(manager.current_session_id, sess_id)

        # Add message
        manager.add_message(sess_id, "user", "Hello", sync=True)
        session = manager.get_session(sess_id)
        self.assertEqual(len(session["messages"]), 1)
        self.assertEqual(session["messages"][0]["text"], "Hello")

        # Rename
        manager.update_session_title(sess_id, "Renamed Chat", sync=True)
        self.assertEqual(manager.get_session(sess_id)["title"], "Renamed Chat")

        # Delete
        manager.delete_session(sess_id, sync=True)
        self.assertIsNone(manager.get_session(sess_id))

    def test_attachment_manager(self):
        manager = AttachmentManager()

        # Create dummy file
        dummy_file = Path(self.test_dir) / "test.txt"
        dummy_file.write_text("content")

        # Add attachment
        processed = manager.add_attachment(str(dummy_file))
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0], str(dummy_file))

        # Check list
        self.assertEqual(len(manager.get_attachments()), 1)

        # Clear
        manager.clear_attachments()
        self.assertEqual(len(manager.get_attachments()), 0)

        manager.cleanup()

    def test_rate_limiter(self):
        limiter = RateLimiter(max_requests=2, period=1, auto_refill=False)

        self.assertTrue(limiter.acquire(blocking=False))
        self.assertTrue(limiter.acquire(blocking=False))
        self.assertFalse(limiter.acquire(blocking=False))  # Should fail

        limiter.release()
        self.assertTrue(limiter.acquire(blocking=False))  # Should succeed

    def test_review_engine(self):
        engine = ReviewEngine()

        old = "def foo():\n    pass"
        new = "def foo():\n    print('hello')"

        diff = engine.generate_diff_html(old, new)
        # Check for escaped content
        expected = html.escape("print('hello')")
        self.assertIn(expected, diff)
        self.assertIn("background-color", diff)  # Check for styling


if __name__ == "__main__":
    unittest.main()
