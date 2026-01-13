# Gemini AI Agent - Professional Edition

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-PyQt6-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![AI Model](https://img.shields.io/badge/AI-Gemini%203.0%20Pro-orange.svg)](https://deepmind.google/technologies/gemini/)
[![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE)

**Gemini AI Agent** is a high-performance, autonomous AI desktop application engineered for professional software developers. It seamlessly integrates advanced Large Language Model (LLM) capabilities—specifically the Google Gemini 1.5/2.0/2.5/3.0 series—directly into your local development environment.

Unlike standard chat interfaces, this agent possesses direct system access, enabling it to analyze codebases, execute complex refactoring, automate system tasks, and orchestrate multi-step engineering workflows with precision and autonomy.

---

## 🚀 Key Features

### 🧠 Intelligent Orchestration (Conductor System)
The **Conductor** system allows the agent to execute sophisticated, multi-step engineering workflows using specialized prompt templates.
- **Security Audit**: Automated vulnerability scanning and security analysis.
- **Refactor**: Intelligent code transformation and modernization.
- **Debug & Trace**: Automated root cause analysis and bug fixing.
- **Performance Profiling**: Identification of bottlenecks and optimization suggestions.
- **Best Practices**: Alignment of code with industry standards and PEP 8.

### 🛠️ Autonomous Tool Execution
The agent is equipped with a robust suite of local tools:
- **File Operations**: Advanced search (Ripgrep integration), read/write, and batch processing.
- **System Management**: Process monitoring, application control, and shell execution.
- **Git Integration**: Full lifecycle management (commit, push, pull, branch management).
- **Python Engineering**: AST-based analysis, test generation, and performance profiling.
- **Sub-Agent Delegation**: Ability to spawn specialized sub-agents for parallel task processing.

### 🛡️ Safety & Control
- **Deep Review Engine**: Intercepts all destructive or system-level actions (e.g., `write_file`, `kill_process`) for explicit user confirmation.
- **Local-First Execution**: Operates directly on your machine, ensuring data privacy and low latency.
- **Token & Cost Tracking**: Real-time monitoring of API usage and estimated costs per session.

### 🔌 Extensibility
- **Plugin Architecture**: Easily extend the agent's capabilities with custom Python plugins.
- **Custom Tool Registry**: A simple decorator-based system (`@tool`) for adding new capabilities.

---

## 🏗️ Architecture Overview

The project follows a modular, event-driven architecture designed for stability and performance:

- **`src/gemini_agent/ui/`**: Responsive PyQt6-based interface with real-time terminal and markdown rendering.
- **`src/gemini_agent/core/`**: The "Brain" of the agent, managing the worker thread, tool registry, and session state.
- **`src/gemini_agent/config/`**: Centralized configuration management with support for multiple Gemini models and themes.
- **`conductor/`**: A library of specialized workflow templates for complex task orchestration.
- **`plugins/`**: Dynamic extension points for third-party or custom integrations.

---

## 📦 Installation

### Prerequisites
- Python 3.10 or higher
- A Google Gemini API Key ([Get one here](https://aistudio.google.com/app/apikey))

### Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-repo/gemini-ai-agent.git
   cd gemini-ai-agent
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv env
   # On Windows:
   env\Scripts\activate
   # On macOS/Linux:
   source env/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the application:**
   ```bash
   python run.py
   ```

---

## 🎮 Usage

### Getting Started
1. Open **Settings** (⚙️) and enter your **Gemini API Key**.
2. Select your preferred **Model** (e.g., Gemini 3 Pro).
3. Use the **Project Explorer** to attach files or directories for context.

### Commands & Shortcuts
- `/clear`: Reset the current chat session.
- `/conductor`: Launch the Conductor Orchestrator for complex tasks.
- `/help`: List all available tools and their descriptions.
- **Ctrl+Enter**: Send message.

---

## 🛠️ Tool Reference (Partial List)

| Category | Tool | Description |
| :--- | :--- | :--- |
| **Files** | `read_file`, `write_file` | Basic I/O operations. |
| **Search** | `search_codebase` | Fast regex search using Ripgrep. |
| **System** | `run_python`, `start_application` | Execute code or launch apps. |
| **Git** | `git_operation` | Execute any git command. |
| **Analysis** | `analyze_python_file` | Static analysis for complexity and issues. |
| **Dev** | `refactor_code`, `generate_tests` | Automated engineering tasks. |

---

## 🧪 Testing

The project includes a comprehensive test suite covering core logic and tool execution.
```bash
pytest tests/
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
