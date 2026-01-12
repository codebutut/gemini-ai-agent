import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from gemini_agent.core.tools import search_codebase, get_agent_capabilities, TOOL_REGISTRY

class TestNewFeatures(unittest.TestCase):
    def test_search_codebase_fallback(self):
        # Create a dummy file to search
        with open("test_search_dummy.py", "w") as f:
            f.write("def dummy_function():\n    print('found me')")
            
        try:
            # Test search (should use fallback since rg is missing)
            result = search_codebase(query="found me", directory=".", file_pattern="*.py")
            self.assertIn("test_search_dummy.py", result)
            self.assertIn("found me", result)
        finally:
            if os.path.exists("test_search_dummy.py"):
                os.remove("test_search_dummy.py")

    def test_get_agent_capabilities(self):
        result = get_agent_capabilities(category="all")
        self.assertIn("## Available Tools", result)
        self.assertIn("search_codebase", result)
        self.assertIn("## Core Competencies", result)
        
        # Test registry
        self.assertIn("search_codebase", TOOL_REGISTRY)
        self.assertIn("get_agent_capabilities", TOOL_REGISTRY)

if __name__ == '__main__':
    unittest.main()

