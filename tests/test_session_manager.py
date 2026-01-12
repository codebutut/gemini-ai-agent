import unittest
import json
import shutil
import tempfile
from pathlib import Path
from core.session_manager import SessionManager

class TestSessionManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.history_file = Path(self.test_dir) / "history.json"
        self.sm = SessionManager(history_file=self.history_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_init_loads_history(self):
        data = {"session1": {"title": "Test Session", "messages": []}}
        with open(self.history_file, "w") as f:
            json.dump(data, f)
        
        sm = SessionManager(history_file=self.history_file)
        self.assertEqual(sm.sessions, data)

    def test_create_session(self):
        session_id = self.sm.create_session("New Chat", sync=True)
        self.assertIn(session_id, self.sm.sessions)
        self.assertEqual(self.sm.sessions[session_id]["title"], "New Chat")
        self.assertEqual(self.sm.current_session_id, session_id)

    def test_delete_session(self):
        session_id = self.sm.create_session("To Delete", sync=True)
        self.assertTrue(self.sm.delete_session(session_id, sync=True))
        self.assertNotIn(session_id, self.sm.sessions)
        self.assertIsNone(self.sm.current_session_id)

    def test_add_message(self):
        session_id = self.sm.create_session(sync=True)
        self.sm.add_message(session_id, "user", "Hello", sync=True)
        
        session = self.sm.get_session(session_id)
        self.assertEqual(len(session["messages"]), 1)
        self.assertEqual(session["messages"][0]["role"], "user")
        self.assertEqual(session["messages"][0]["text"], "Hello")

    def test_update_session_title(self):
        session_id = self.sm.create_session("Old Title", sync=True)
        self.sm.update_session_title(session_id, "New Title", sync=True)
        self.assertEqual(self.sm.sessions[session_id]["title"], "New Title")

    def test_clear_current_session(self):
        session_id = self.sm.create_session(sync=True)
        self.sm.add_message(session_id, "user", "Hello", sync=True)
        self.sm.update_session_plan(session_id, "Plan", sync=True)
        self.sm.update_session_specs(session_id, "Specs", sync=True)
        
        self.sm.clear_current_session(sync=True)
        session = self.sm.get_session(session_id)
        self.assertEqual(session["messages"], [])
        self.assertEqual(session["plan"], "")
        self.assertEqual(session["specs"], "")

if __name__ == "__main__":
    unittest.main()
