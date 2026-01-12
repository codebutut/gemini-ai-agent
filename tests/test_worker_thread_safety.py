import unittest
from unittest.mock import MagicMock, patch
import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from gemini_agent.core.worker import GeminiWorker, WorkerConfig

class TestWorkerThreadSafety(unittest.TestCase):
    def test_confirm_tool_uses_call_soon_threadsafe(self):
        # Setup
        config = MagicMock(spec=WorkerConfig)
        config.session_id = "test-session"
        worker = GeminiWorker(config)
        
        # Mock loop
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        worker._loop = mock_loop
        
        # Mock event
        worker._confirmation_event = MagicMock()
        worker._current_confirmation_id = "test_id"
        
        # Act
        worker.confirm_tool("test_id", True, {})
        
        # Assert
        # Should call loop.call_soon_threadsafe with event.set
        mock_loop.call_soon_threadsafe.assert_called_once_with(worker._confirmation_event.set)
        
        # Should NOT call set() directly
        worker._confirmation_event.set.assert_not_called()

    def test_confirm_tool_fallback_when_no_loop(self):
        # Setup
        config = MagicMock(spec=WorkerConfig)
        config.session_id = "test-session"
        worker = GeminiWorker(config)
        
        # No loop set
        worker._loop = None
        
        # Mock event
        worker._confirmation_event = MagicMock()
        worker._current_confirmation_id = "test_id"
        
        # Act
        worker.confirm_tool("test_id", True, {})
        
        # Assert
        # Should call set() directly as fallback
        worker._confirmation_event.set.assert_called_once()

if __name__ == '__main__':
    unittest.main()
