# Gemini Agent

Gemini Agent is a fully autonomous AI agent framework designed with direct local system access and Model Context Protocol (MCP) integration. It is capable of executing complex software engineering, system administration, and automation tasks.

## Features

- **Autonomous Workflow:** Self-managing agent capable of planning, executing, and reflecting on tasks.
- **Model Context Protocol (MCP):** Integrated MCP server configuration for standardized tool and context exchange.
- **Plugin System:** Extensible architecture via the `plugins/` directory.
- **System Operations:** Direct management of processes, files, and system resources.
- **Python Engineering:** Built for production-grade Python development with strict typing and testing standards.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd gemini-agent
    ```

2.  **Set up a virtual environment:**
    ```bash
    python -m venv env
    source env/bin/activate  # On Windows: env\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

### MCP Configuration
The agent is configured as an MCP server in `mcp_config.json`:
```json
{
  "mcpServers": {
    "gemini-agent": {
      "command": "python",
      "args": ["-m", "gemini_agent.mcp.server"],
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}
```

### Application Settings
General application settings can be found in `settings.json`.

## Usage

To start the agent:

```bash
python run.py
```

## Development

### Project Structure
- `src/`: Source code for the agent core.
- `conductor/`: Orchestration logic.
- `plugins/`: Extension modules.
- `tests/`: Unit and integration tests.

### Running Tests
```bash
pytest tests/
```

