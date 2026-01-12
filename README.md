# Gemini AI Agent - Professional Edition

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-PyQt6-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![AI Model](https://img.shields.io/badge/AI-Gemini%201.5%20Pro-orange.svg)](https://deepmind.google/technologies/gemini/)

A high-performance, autonomous AI Agent Desktop Application designed for professional software engineers. Gemini AI Agent integrates advanced LLM capabilities directly with your local development environment, enabling seamless code analysis, refactoring, and system automation.

## 🚀 Key Features

### 🧠 Intelligent Orchestration
- **Conductor System**: Execute complex, multi-step engineering workflows (Refactor, Debug, Security Audit) using specialized prompt templates.
- **Autonomous Tool Execution**: The agent can read/write files, execute shell commands, manage processes, and perform git operations.
- **Sub-Agent Delegation**: Break down massive tasks by delegating to specialized sub-agents.

### 🛠️ Developer-Centric UI
- **Integrated Project Explorer**: Easily attach files and directories to provide context to the AI.
- **Symbol Browser**: Navigate and attach specific code symbols (classes, functions) using the built-in indexer.
- **Real-time Terminal**: Monitor tool execution and system output directly within the chat interface.
- **Markdown & Syntax Highlighting**: Beautifully rendered responses with full support for code blocks and technical formatting.

### 🛡️ Safety & Control
- **Deep Review System**: Every destructive or system-level action requires explicit user confirmation or modification.
- **Session Management**: Full history tracking with export to Markdown and comprehensive backup/restore capabilities.
- **Usage Monitoring**: Real-time token tracking and cost estimation per session.

### 🔌 Extensibility
- **Plugin Architecture**: Extend the agent's capabilities with custom plugins.
- **Custom Tool Registry**: Easily add new Python-based tools using a simple decorator-based registration system.

## 📦 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/codebutut/gemini-ai-agent.git
   cd gemini-ai-agent
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API Key:**
   - Launch the application.
   - Open **Settings** (⚙️) and enter your Google Gemini API Key.

## 🎮 Usage

Run the application using the entry point:
```bash
python run.py
```

### Common Commands
- `/clear`: Clear the current chat history.
- `/conductor`: Open the Conductor Orchestrator dialog.
- `/help`: Display available tools and commands.

## 🏗️ Architecture Overview

The project follows a modular MVC-inspired architecture:
- **`src/gemini_agent/ui/`**: PyQt6-based user interface components.
- **`src/gemini_agent/core/`**: Core logic including the worker thread, tool registry, and session management.
- **`src/gemini_agent/config/`**: Application configuration and logging setup.
- **`conductor/`**: Specialized prompt templates for complex task orchestration.
- **`plugins/`**: Dynamic extension points for the agent.

## 🧪 Testing

Run the comprehensive test suite using `pytest`:
```bash
pytest tests/
```



