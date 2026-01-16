import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Adjust path to include src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from PyQt6.QtWidgets import QApplication

from gemini_agent.config.app_config import AppConfig
from gemini_agent.main import ChatController


class TestWorkerIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # ensure QApplication exists
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()

    @patch("gemini_agent.main.GeminiWorker")
    @patch("gemini_agent.main.GeminiWorkerThread")
    def test_send_message_starts_thread(self, MockWorkerThread, MockWorker):
        # Setup mocks
        mock_worker_instance = MockWorker.return_value
        mock_thread_instance = MockWorkerThread.return_value

        # Setup dependencies for Controller
        config = MagicMock(spec=AppConfig)
        config.api_key = "dummy_key"
        config.get.return_value = "dummy_value"

        session_mgr = MagicMock()
        session_mgr.current_session_id = "sess_1"
        session_mgr.get_session.return_value = {"messages": [], "config": {}}

        attachment_mgr = MagicMock()
        attachment_mgr.get_attachments.return_value = []

        conductor_mgr = MagicMock()
        indexer = MagicMock()
        plugin_mgr = MagicMock()
        checkpoint_mgr = MagicMock()

        # Instantiate Controller
        controller = ChatController(
            config, session_mgr, attachment_mgr, conductor_mgr, indexer, plugin_mgr, checkpoint_mgr
        )

        # Act
        controller.send_message("Hello")

        # Assert
        # Check if Worker was instantiated
        MockWorker.assert_called()

        # Check if Thread was instantiated with the worker
        MockWorkerThread.assert_called_with(mock_worker_instance)

        # Check if thread.start() was called
        mock_thread_instance.start.assert_called_once()

        # Check if error handling works (signals connected)
        mock_worker_instance.finished.connect.assert_called()


if __name__ == "__main__":
    unittest.main()
