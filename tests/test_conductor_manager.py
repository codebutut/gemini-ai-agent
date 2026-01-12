import unittest
import json
import shutil
import tempfile
from pathlib import Path
from core.conductor_manager import ConductorManager

class TestConductorManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.ext_dir = Path(self.test_dir) / "extension"
        self.commands_dir = self.ext_dir / "commands" / "conductor"
        self.commands_dir.mkdir(parents=True)
        
        # Create a dummy command with top-level keys
        command_data = "prompt = 'Test Prompt'\ndescription = 'Test Description'"
        (self.commands_dir / "test_cmd.toml").write_text(command_data)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_load_commands(self):
        cm = ConductorManager(extension_path=str(self.ext_dir))
        self.assertIn("test_cmd", cm.get_available_commands())
        self.assertEqual(cm.get_command_prompt("test_cmd"), "Test Prompt")

    def test_is_setup(self):
        cm = ConductorManager(extension_path=str(self.ext_dir))
        project_path = Path(self.test_dir) / "project"
        project_path.mkdir()
        
        self.assertFalse(cm.is_setup(str(project_path)))
        
        conductor_dir = project_path / "conductor"
        conductor_dir.mkdir()
        for f in ["product.md", "tech-stack.md", "workflow.md"]:
            (conductor_dir / f).write_text("content")
            
        self.assertTrue(cm.is_setup(str(project_path)))

    def test_get_setup_state(self):
        cm = ConductorManager(extension_path=str(self.ext_dir))
        project_path = Path(self.test_dir) / "project"
        conductor_dir = project_path / "conductor"
        conductor_dir.mkdir(parents=True)
        
        state_file = conductor_dir / "setup_state.json"
        state_data = {"status": "completed"}
        with open(state_file, "w") as f:
            json.dump(state_data, f)
            
        self.assertEqual(cm.get_setup_state(str(project_path)), state_data)

if __name__ == "__main__":
    unittest.main()
