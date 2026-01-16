import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Adjust path to include src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from gemini_agent.core.sub_agent import SubAgent
from gemini_agent.core.tools import delegate_to_agent


class TestSubAgent(unittest.IsolatedAsyncioTestCase):
    @patch("gemini_agent.core.sub_agent.genai.Client")
    @patch("gemini_agent.core.sub_agent.AppConfig")
    async def test_sub_agent_run(self, MockAppConfig, MockGenaiClient):
        # Setup mocks
        mock_client = MockGenaiClient.return_value
        mock_client.aio.models.generate_content = AsyncMock()

        # Mock response sequence: 1. Tool Call, 2. Final Answer
        mock_response_tool = MagicMock()
        mock_response_tool.candidates = [MagicMock()]
        mock_part_tool = MagicMock()
        mock_part_tool.function_call.name = "list_files"
        mock_part_tool.function_call.args = {"directory": "."}
        mock_response_tool.candidates[0].content.parts = [mock_part_tool]

        mock_response_final = MagicMock()
        mock_response_final.candidates = [MagicMock()]
        mock_part_final = MagicMock()
        mock_part_final.function_call = None
        mock_part_final.text = "Files listed."
        mock_response_final.candidates[0].content.parts = [mock_part_final]
        mock_response_final.text = "Files listed."

        # Configure side effect for successive calls
        mock_client.aio.models.generate_content.side_effect = [
            mock_response_tool,
            mock_response_final,
        ]

        # Initialize agent
        agent = SubAgent("TestBot")

        # Run agent
        result = await agent.run("List files")

        # Verify
        self.assertEqual(result, "Files listed.")
        self.assertEqual(mock_client.aio.models.generate_content.call_count, 2)

    @patch("gemini_agent.core.sub_agent.SubAgent")
    def test_delegate_tool(self, MockSubAgent):
        # Mock the async run method of the agent instance
        mock_agent_instance = MockSubAgent.return_value
        mock_agent_instance.run = AsyncMock(return_value="Mission Accomplished")

        # Run tool
        result = delegate_to_agent("Specialist", "Do the thing")

        # Verify
        self.assertIn("Sub-Agent 'Specialist' Result", result)
        self.assertIn("Mission Accomplished", result)
        MockSubAgent.assert_called_with(name="Specialist")
        mock_agent_instance.run.assert_called_with("Do the thing")


if __name__ == "__main__":
    unittest.main()
