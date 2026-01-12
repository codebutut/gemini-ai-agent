import unittest
from PyQt6.QtWidgets import QApplication, QDockWidget
from PyQt6.QtCore import Qt
import sys
import os

# Ensure we can import from src/gemini_agent
sys.path.append(os.path.join(os.getcwd(), "src", "gemini_agent"))

from ui.components import ChatHeader

# Mocking a few things to avoid full app initialization if possible
# but for UI tests we usually need a QApplication
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

class TestUIStructure(unittest.TestCase):
    def test_chat_header_structure(self):
        header = ChatHeader()
        
        # Check for expected buttons
        self.assertTrue(hasattr(header, 'btn_terminal'))
        self.assertTrue(hasattr(header, 'btn_settings'))
        
        # Check signals
        self.assertTrue(hasattr(header, 'terminal_toggle_requested'))
        self.assertTrue(hasattr(header, 'settings_requested'))

if __name__ == '__main__':
    unittest.main()
