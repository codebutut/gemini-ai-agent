# Gemini AI Agent - Professional Edition

A powerful, extensible desktop AI agent built with Python 3.10+ and PyQt6, leveraging the Google Gemini API for advanced reasoning, tool execution, and project orchestration.

## 🚀 Overview

Gemini AI Agent is more than just a chatbot; it's a comprehensive development and orchestration environment. It integrates deep system access, static code analysis, and a modular extension system to provide a seamless AI-assisted workflow.

## ✨ Key Features

- **Advanced Tool Execution**: Seamlessly execute local Python tools, system commands, and external MCP (Model Context Protocol) servers.
- **RAG-Powered Context**: Integrated semantic search using ChromaDB and AST-based symbol indexing for deep project understanding.
- **Multi-Agent Orchestration**: Delegate complex tasks to specialized sub-agents for parallel processing and specialized expertise.
- **Professional UI/UX**: A modern PyQt6 interface featuring:
    - **Project Explorer**: Navigate and attach files/folders directly from your workspace.
    - **Symbol Browser**: Instantly find and reference Python classes and functions.
    - **Integrated Terminal**: Real-time monitoring of tool execution and system logs.
    - **Session Management**: Persistent chat history with export and backup capabilities.
- **Extensibility**: Install plugins from PyPI or connect to any MCP-compliant server to expand the agent's capabilities.
- **Visual Intelligence**: Generate high-quality images with Imagen 3 and perform deep analysis of visual content.
- **Cost & Usage Monitoring**: Real-time tracking of token consumption and estimated API costs.

## 🛠️ Tech Stack

- **Core**: Python 3.10+
- **GUI**: PyQt6, qasync
- **AI**: Google Gemini API (`google-genai`)
- **Vector DB**: ChromaDB
- **Analysis**: AST (Abstract Syntax Trees), Ripgrep (optional)
- **System**: psutil, subprocess

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/codebutut/gemini-agent.git
   cd gemini-agent
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Usage

Run the application using the entry point:

```bash
python run.py
```

## 🏗️ Architecture

The project follows a modular design:

- `src/gemini_agent/core`: The "brain" of the agent, handling AI logic, tool execution, and state management.
- `src/gemini_agent/ui`: The PyQt6-based interface components.
- `src/gemini_agent/mcp`: Integration layer for the Model Context Protocol.
- `conductor/`: Orchestration logic and project-level workflows.

