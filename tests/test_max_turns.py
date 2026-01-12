import unittest
import json
import os
from pathlib import Path
from config.app_config import AppConfig

class TestMaxTurns(unittest.TestCase):
    def setUp(self):
        self.config_file = Path("test_settings.json")
        if self.config_file.exists():
            os.remove(self.config_file)
        self.config = AppConfig(config_file=self.config_file)

    def tearDown(self):
        if self.config_file.exists():
            os.remove(self.config_file)

    def test_default_max_turns(self):
        self.assertEqual(self.config.get("max_turns"), 20)

    def test_set_max_turns(self):
        self.config.set("max_turns", 35, sync=True)
        self.assertEqual(self.config.get("max_turns"), 35)
        
        # Verify it's saved to file
        with open(self.config_file, "r") as f:
            data = json.load(f)
            self.assertEqual(data["max_turns"], 35)

    def test_load_max_turns(self):
        with open(self.config_file, "w") as f:
            json.dump({"max_turns": 42}, f)
        
        new_config = AppConfig(config_file=self.config_file)
        self.assertEqual(new_config.get("max_turns"), 42)

if __name__ == "__main__":
    unittest.main()
