import unittest
from pathlib import Path
import json
import shutil
import tempfile
from core.session_manager import SessionManager
from config.app_config import ModelRegistry

class TestUsageTracking(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.history_file = self.test_dir / "history.json"
        self.session_manager = SessionManager(history_file=self.history_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_initial_usage(self):
        session_id = self.session_manager.create_session("Test Session")
        session = self.session_manager.get_session(session_id)
        self.assertIn("usage", session)
        self.assertEqual(session["usage"]["total_tokens"], 0)

    def test_update_usage(self):
        session_id = self.session_manager.create_session("Test Session", sync=True)
        self.session_manager.update_session_usage(session_id, 100, 50, sync=True)
        
        session = self.session_manager.get_session(session_id)
        self.assertEqual(session["usage"]["input_tokens"], 100)
        self.assertEqual(session["usage"]["output_tokens"], 50)
        self.assertEqual(session["usage"]["total_tokens"], 150)
        
        # Cumulative update
        self.session_manager.update_session_usage(session_id, 200, 100, sync=True)
        session = self.session_manager.get_session(session_id)
        self.assertEqual(session["usage"]["input_tokens"], 300)
        self.assertEqual(session["usage"]["output_tokens"], 150)
        self.assertEqual(session["usage"]["total_tokens"], 450)

    def test_cost_calculation_logic(self):
        # This test simulates the logic used in main.py
        model_id = "gemini-1.5-pro"
        pricing = ModelRegistry.MODEL_PRICING.get(model_id)
        self.assertIsNotNone(pricing)
        
        input_tokens = 1_000_000
        output_tokens = 1_000_000
        
        input_cost = (input_tokens / 1_000_000) * pricing[0]
        output_cost = (output_tokens / 1_000_000) * pricing[1]
        total_cost = input_cost + output_cost
        
        # For gemini-1.5-pro, it should be 3.50 + 10.50 = 14.00
        self.assertAlmostEqual(total_cost, 14.00)

if __name__ == "__main__":
    unittest.main()
