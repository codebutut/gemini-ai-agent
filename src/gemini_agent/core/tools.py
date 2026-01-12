import os
import sys
import subprocess
import io
import ast
import json
import time
import re
import inspect
import importlib
import tempfile
import shutil
import psutil
import threading
import tokenize
import logging
from typing import Any, Dict, List, Tuple, Optional, Union, Callable
from pathlib import Path
from datetime import datetime
import traceback
import webbrowser
import platform
import signal
from functools import wraps
from pydantic import BaseModel, Field, ValidationError
from google.genai import types

try:
    from utils.introspection import auto_generate_declaration
except ImportError:
    from gemini_agent.utils.introspection import auto_generate_declaration

# Configure logging
logger = logging.getLogger(__name__)

# --- Tool Registry ---

TOOL_REGISTRY: Dict[str, Callable] = {}

def tool(func: Callable) -> Callable:
    """Decorator to register a function as a tool."""
    TOOL_REGISTRY[func.__name__] = func
    return func

# --- Pydantic Models for Validation ---

class FilePathArgs(BaseModel):
    filepath: str = Field(..., description="The path to the file.")

class DirectoryArgs(BaseModel):
    directory: str = Field(".", description="The path to the directory.")

class WriteFileArgs(BaseModel):
    filepath: str = Field(..., description="The destination path.")
    content: str = Field(..., description="The text content to write.")

class CodeArgs(BaseModel):
    code: str = Field(..., description="The Python code snippet to execute.")

class StartAppArgs(BaseModel):
    app_path: str = Field(..., description="Path to the application executable.")
    args: Optional[List[str]] = Field(None, description="Command line arguments.")
    wait: bool = Field(False, description="Whether to wait for the application to complete.")

class KillProcessArgs(BaseModel):
    process_name: str = Field(..., description="Name or PID of process to kill.")
    force: bool = Field(False, description="Force kill if process doesn't respond.")

class RefactorArgs(BaseModel):
    filepath: str = Field(..., description="Path to Python file.")
    changes: List[Dict[str, Any]] = Field(..., description="List of refactoring operations.")

class GenerateTestsArgs(BaseModel):
    filepath: str = Field(..., description="Path to Python file to generate tests for.")
    output_dir: Optional[str] = Field(None, description="Directory to save test files.")

class DebugArgs(BaseModel):
    code: str = Field(..., description="Python code to debug.")
    breakpoints: Optional[List[int]] = Field(None, description="Line numbers to break at.")

class ProfileArgs(BaseModel):
    code: str = Field(..., description="Python code to profile.")
    function_name: Optional[str] = Field(None, description="Specific function to profile.")

class GitArgs(BaseModel):
    operation: str = Field(..., description="git command (clone, pull, commit, push, etc.).")
    args: Optional[List[str]] = Field(None, description="Additional arguments.")

class InstallPackageArgs(BaseModel):
    package_name: str = Field(..., description="Name of package to install.")
    upgrade: bool = Field(False, description="Whether to upgrade if already installed.")
    dev: bool = Field(False, description="Whether to install dev dependencies.")

class FetchUrlArgs(BaseModel):
    url: str = Field(..., description="URL to fetch.")
    method: str = Field("GET", description="HTTP method.")
    data: Optional[Dict[str, Any]] = Field(None, description="POST data (if any).")

class SearchFilesArgs(BaseModel):
    directory: str = Field(..., description="Directory to search in.")
    pattern: str = Field(..., description="Search pattern.")
    recursive: bool = Field(True, description="Whether to search recursively.")

class SearchCodebaseArgs(BaseModel):
    query: str = Field(..., description="Regex pattern to search for.")
    directory: str = Field(".", description="Root directory to search.")
    file_pattern: Optional[str] = Field(None, description="Glob pattern for file filtering (e.g., '*.py').")
    case_sensitive: bool = Field(False, description="Case sensitive search.")

class IntrospectionArgs(BaseModel):
    category: str = Field("all", description="Category to inspect: 'capabilities', 'tools', 'config', 'all'.")

class FindInFilesArgs(BaseModel):
    directory: str = Field(..., description="Directory to search in.")
    search_text: str = Field(..., description="Text to search for.")
    file_pattern: str = Field("*.py", description="File pattern to search within.")

class ExecutePythonEnvArgs(BaseModel):
    code: str = Field(..., description="Python code to execute.")
    imports: Optional[List[str]] = Field(None, description="List of modules to import before execution.")

class DelegateArgs(BaseModel):
    agent_name: str = Field(..., description="Name/Role of the sub-agent (e.g., 'Researcher', 'Coder').")
    objective: str = Field(..., description="The specific task or objective for the sub-agent.")

# --- Validation Decorator ---

def validate_args(model: type[BaseModel]):
    """Decorator to validate function arguments using a Pydantic model."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Bind args/kwargs to the function's signature
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                
                # Validate using the model
                validated_args = model(**bound_args.arguments)
                return func(**validated_args.model_dump())
            except ValidationError as e:
                return f"Validation Error: {str(e)}"
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                return f"Error: {str(e)}"
        return wrapper
    return decorator

# --- Original Tool Functions ---

@tool
@validate_args(DirectoryArgs)
def list_files(directory: str = ".") -> str:
    """
    Lists all files and directories in the specified path.
    
    Args:
        directory: The path to list. Defaults to current directory.

    Returns:
        str: A newline-separated list of items or an error message.
    """
    try:
        path = Path(directory)
        if not path.exists():
            return f"Error: Directory '{directory}' does not exist."
        if not path.is_dir():
            return f"Error: '{directory}' is not a directory."
        
        items = os.listdir(directory)
        return "\n".join(items) if items else "(Empty Directory)"
    except PermissionError:
        return f"Error: Permission denied for directory '{directory}'."

@tool
@validate_args(FilePathArgs)
def read_file(filepath: str) -> str:
    """
    Reads the full content of a file.
    
    Args:
        filepath: The path to the file to read.

    Returns:
        str: File content or an error message.
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return f"Error: File '{filepath}' does not exist."
        if not path.is_file():
            return f"Error: '{filepath}' is not a file."
        
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except PermissionError:
        return f"Error: Permission denied for file '{filepath}'."

@tool
@validate_args(WriteFileArgs)
def write_file(filepath: str, content: str) -> str:
    """
    Writes content to a file. Overwrites the file if it exists.
    
    Args:
        filepath: The destination path.
        content: The text content to write.

    Returns:
        str: Success or error message.
    """
    try:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
            
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to '{filepath}'."
    except PermissionError:
        return f"Error: Permission denied writing to '{filepath}'."

@tool
@validate_args(CodeArgs)
def run_python(code: str) -> str:
    """
    Executes Python code in a separate process and returns stdout/stderr.
    Useful for calculations, data processing, or running generated scripts.
    
    Args:
        code: The Python code snippet to execute.

    Returns:
        str: Combined stdout and stderr or an error message.
    """
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = ""
            if result.stdout:
                output += f"Output:\n{result.stdout}\n"
            if result.stderr:
                output += f"Errors:\n{result.stderr}\n"
                
            return output if output else "(No output to stdout/stderr)"
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out (30s limit)."

@tool
@validate_args(StartAppArgs)
def start_application(app_path: str, args: Optional[List[str]] = None, wait: bool = False) -> str:
    """
    Starts a local application.
    
    Args:
        app_path: Path to the application executable.
        args: Command line arguments.
        wait: Whether to wait for the application to complete.

    Returns:
        str: Status message or execution output.
    """
    try:
        path = Path(app_path)
        if not path.exists():
            return f"Error: Application '{app_path}' not found."
        
        cmd = [str(path)]
        if args:
            cmd.extend(args)
            
        if wait:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            output = []
            if result.stdout:
                output.append(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                output.append(f"STDERR:\n{result.stderr}")
            return f"Application completed with code {result.returncode}\n" + "\n".join(output)
        else:
            if platform.system() == "Windows":
                subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            else:
                subprocess.Popen(cmd, start_new_session=True)
            return f"Application started in background: {app_path}"
    except subprocess.TimeoutExpired:
        return "Error: Application execution timed out (300s limit)."

@tool
@validate_args(KillProcessArgs)
def kill_process(process_name: str, force: bool = False) -> str:
    """
    Kills a running process by name or PID.
    
    Args:
        process_name: Name or PID of process to kill.
        force: Force kill if process doesn't respond.

    Returns:
        str: Success or error message.
    """
    try:
        try:
            pid = int(process_name)
            proc = psutil.Process(pid)
            if force:
                proc.kill()
            else:
                proc.terminate()
            return f"Terminated process {pid}"
        except (ValueError, psutil.NoSuchProcess):
            killed = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if process_name.lower() in proc.info['name'].lower():
                        if force:
                            proc.kill()
                        else:
                            proc.terminate()
                        killed.append(str(proc.info['pid']))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return f"Terminated processes: {', '.join(killed)}" if killed else f"No processes found with name or PID: {process_name}"
    except Exception as e:
        return f"Error killing process: {str(e)}"

@tool
def list_processes() -> str:
    """
    Lists all running processes with resource usage.

    Returns:
        str: Formatted list of top 50 processes.
    """
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                processes.append(f"PID: {info['pid']} | {info['name']} | CPU: {info['cpu_percent']:.1f}% | MEM: {info['memory_percent']:.1f}%")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return "\n".join(processes[:50])
    except Exception as e:
        return f"Error listing processes: {str(e)}"

# --- Code Analysis & Refactoring Tools ---

class CodeAnalyzer:
    """Static code analysis utilities."""
    
    @staticmethod
    def analyze_code(filepath: str) -> str:
        """Analyzes Python code for complexity, style, and potential issues."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
            
            tree = ast.parse(code)
            analysis = {
                'functions': 0,
                'classes': 0,
                'imports': 0,
                'complex_functions': [],
                'issues': []
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis['functions'] += 1
                    complexity = CodeAnalyzer._calculate_complexity(node)
                    if complexity > 10:
                        analysis['complex_functions'].append(f"  - {node.name}: complexity {complexity}")
                elif isinstance(node, ast.ClassDef):
                    analysis['classes'] += 1
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    analysis['imports'] += 1
                
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    analysis['issues'].append(f"Bare except clause found (line {node.lineno})")
                elif isinstance(node, ast.Assert):
                    analysis['issues'].append(f"Assert statement found (line {node.lineno})")
            
            report = [
                f"File: {filepath}",
                f"Functions: {analysis['functions']}",
                f"Classes: {analysis['classes']}",
                f"Imports: {analysis['imports']}"
            ]
            if analysis['complex_functions']:
                report.append("Complex functions (>10):")
                report.extend(analysis['complex_functions'])
            if analysis['issues']:
                report.append("Potential issues:")
                report.extend(analysis['issues'])
            
            return "\n".join(report)
        except Exception as e:
            return f"Error analyzing code: {str(e)}"
    
    @staticmethod
    def _calculate_complexity(node: ast.AST) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.Try)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

@tool
@validate_args(FilePathArgs)
def analyze_python_file(filepath: str) -> str:
    """
    Analyze Python code for complexity, style, and potential issues.
    
    Args:
        filepath: Path to Python file to analyze.

    Returns:
        str: Analysis report or error message.
    """
    return CodeAnalyzer.analyze_code(filepath)

@tool
@validate_args(RefactorArgs)
def refactor_code(filepath: str, changes: List[Dict[str, Any]]) -> str:
    """
    Refactors code based on specified changes.
    
    Args:
        filepath: Path to Python file.
        changes: List of refactoring operations.

    Returns:
        str: Success message or error message.
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return f"Error: File '{filepath}' not found."
            
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        backup_path = filepath + ".backup"
        shutil.copy2(filepath, backup_path)
        
        for change in changes:
            if change.get('type') == 'rename':
                old_name = change.get('old_name')
                new_name = change.get('new_name')
                if not old_name or not new_name: continue
                
                try:
                    tokens = list(tokenize.generate_tokens(io.StringIO(content).readline))
                except tokenize.TokenError:
                    return "Error: Could not tokenize file (syntax error?)"
                
                replacements = [t for t in tokens if t.type == tokenize.NAME and t.string == old_name]
                lines = content.splitlines(keepends=True)
                new_lines = []
                replacements_by_line = {}
                for t in replacements:
                    row = t.start[0] - 1 
                    replacements_by_line.setdefault(row, []).append(t)
                
                for i, line in enumerate(lines):
                    if i in replacements_by_line:
                        line_repls = sorted(replacements_by_line[i], key=lambda t: t.start[1], reverse=True)
                        for t in line_repls:
                            line = line[:t.start[1]] + new_name + line[t.end[1]:]
                        new_lines.append(line)
                    else:
                        new_lines.append(line)
                content = "".join(new_lines)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Code refactored. Backup saved to {backup_path}"
    except Exception as e:
        return f"Error refactoring code: {str(e)}"

@tool
@validate_args(GenerateTestsArgs)
def generate_tests(filepath: str, output_dir: Optional[str] = None) -> str:
    """
    Generates test stubs for a Python module.
    
    Args:
        filepath: Path to Python file to generate tests for.
        output_dir: Directory to save test files (default: tests/ in same directory).

    Returns:
        str: Success message or error message.
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return f"Error: File '{filepath}' not found."
            
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        tree = ast.parse(code)
        test_code = ["import unittest", "import pytest", "", f"from {path.stem} import *", "", "class TestGenerated(unittest.TestCase):"]
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                test_code.extend([
                    f"\n    def test_{node.name}(self):",
                    f"        '''Auto-generated test for function {node.name}'''",
                    "        # TODO: Implement test logic",
                    "        self.skipTest('Test not implemented')"
                ])
        
        test_code.extend(["", "if __name__ == '__main__':", "    unittest.main()"])
        
        final_output_dir = Path(output_dir) if output_dir else path.parent / "tests"
        final_output_dir.mkdir(exist_ok=True, parents=True)
        
        test_file = final_output_dir / f"test_{path.name}"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(test_code))
        return f"Test stubs generated: {test_file}"
    except Exception as e:
        return f"Error generating tests: {str(e)}"

@tool
@validate_args(DebugArgs)
def debug_python(code: str, breakpoints: Optional[List[int]] = None) -> str:
    """
    Debugs Python code with breakpoint support.
    
    Args:
        code: Python code to debug.
        breakpoints: Line numbers to break at.

    Returns:
        str: Debugging output.
    """
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='_debug.py', delete=False, encoding='utf-8') as tmp:
            debug_code = f"import sys\nimport traceback\n\n{code}"
            tmp.write(debug_code)
            tmp_path = tmp.name
        
        try:
            result = subprocess.run([sys.executable, tmp_path], capture_output=True, text=True, timeout=30)
            output = []
            if result.stdout: output.append(f"Output:\n{result.stdout}")
            if result.stderr: output.append(f"Errors:\n{result.stderr}")
            return "\n".join(output) if output else "(No output)"
        finally:
            if os.path.exists(tmp_path): os.remove(tmp_path)
    except subprocess.TimeoutExpired:
        return "Error: Debug session timed out (30s limit)."

@tool
@validate_args(ProfileArgs)
def profile_code(code: str, function_name: Optional[str] = None) -> str:
    """
    Profiles Python code for performance analysis.
    
    Args:
        code: Python code to profile.
        function_name: Specific function to profile (optional).

    Returns:
        str: Profiling results.
    """
    try:
        profile_script = f"import cProfile, pstats, io\ndef run_code():\n{chr(10).join('    ' + l for l in code.splitlines())}\nif __name__ == '__main__':\n    profiler = cProfile.Profile()\n    profiler.enable()\n    try: run_code()\n    except Exception as e: print(f'Error: {{e}}')\n    profiler.disable()\n    s = io.StringIO()\n    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')\n    ps.print_stats(20)\n    print(s.getvalue())"
        result = subprocess.run([sys.executable, '-c', profile_script], capture_output=True, text=True, timeout=60)
        output = []
        if result.stdout: output.append(f"Profiling Results:\n{result.stdout}")
        if result.stderr: output.append(f"Profiling Errors:\n{result.stderr}")
        return "\n".join(output) if output else "No profiling output"
    except subprocess.TimeoutExpired:
        return "Error: Profiling timed out (60s limit)."

@tool
@validate_args(GitArgs)
def git_operation(operation: str, args: Optional[List[str]] = None) -> str:
    """
    Executes Git operations.
    
    Args:
        operation: git command (clone, pull, commit, push, etc.).
        args: Additional arguments.

    Returns:
        str: Git operation output.
    """
    try:
        cmd = ['git', operation]
        if args: cmd.extend(args)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        output = []
        if result.stdout: output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr: output.append(f"STDERR:\n{result.stderr}")
        return f"Git {operation} completed with code {result.returncode}\n" + "\n".join(output)
    except subprocess.TimeoutExpired:
        return f"Error: Git {operation} timed out (60s limit)."

@tool
@validate_args(InstallPackageArgs)
def install_package(package_name: str, upgrade: bool = False, dev: bool = False) -> str:
    """
    Installs Python packages using pip.
    
    Args:
        package_name: Name of package to install.
        upgrade: Whether to upgrade if already installed.
        dev: Whether to install dev dependencies.

    Returns:
        str: Installation output.
    """
    try:
        cmd = [sys.executable, '-m', 'pip', 'install']
        if upgrade: cmd.append('--upgrade')
        cmd.append(package_name + '[dev]' if dev else package_name)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        output = []
        if result.stdout: output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr: output.append(f"STDERR:\n{result.stderr}")
        return f"Package installation completed\n" + "\n".join(output)
    except subprocess.TimeoutExpired:
        return "Error: Package installation timed out (300s limit)."

@tool
@validate_args(FetchUrlArgs)
def fetch_url(url: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> str:
    """
    Fetches data from a URL.
    
    Args:
        url: URL to fetch.
        method: HTTP method.
        data: POST data (if any).

    Returns:
        str: Response content or error message.
    """
    try:
        import httpx
        headers = {'User-Agent': 'Mozilla/5.0'}
        if method.upper() == "GET":
            response = httpx.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            response = httpx.post(url, json=data, headers=headers, timeout=10)
        else:
            return f"Unsupported HTTP method: {method}"
        response.raise_for_status()
        try: return json.dumps(response.json(), indent=2)
        except: return response.text[:5000]
    except Exception as e:
        return f"Request Error: {str(e)}"

@tool
@validate_args(SearchFilesArgs)
def search_files(directory: str, pattern: str, recursive: bool = True) -> str:
    """
    Searches for files matching a pattern.
    
    Args:
        directory: Directory to search in.
        pattern: Search pattern (supports * and ? wildcards).
        recursive: Whether to search recursively.

    Returns:
        str: List of found files or message.
    """
    try:
        import fnmatch
        matches = []
        if not Path(directory).exists(): return f"Error: Directory '{directory}' not found."
        if recursive:
            for root, _, files in os.walk(directory):
                for file in files:
                    if fnmatch.fnmatch(file, pattern): matches.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                if fnmatch.fnmatch(file, pattern): matches.append(os.path.join(directory, file))
        return f"Found {len(matches)} files:\n" + "\n".join(matches[:50]) if matches else "No files found matching the pattern."
    except Exception as e:
        return f"Error searching files: {str(e)}"

@tool
@validate_args(SearchCodebaseArgs)
def search_codebase(query: str, directory: str = ".", file_pattern: Optional[str] = None, case_sensitive: bool = False) -> str:
    """
    Fast code search using ripgrep (rg) if available, falling back to python.
    
    Args:
        query: Regex pattern to search for.
        directory: Root directory.
        file_pattern: Glob pattern (e.g., '*.py').
        case_sensitive: Case sensitive search.

    Returns:
        str: Search results.
    """
    try:
        # Try running rg
        cmd = ['rg', '--line-number', '--no-heading', '--color=never']
        if not case_sensitive:
            cmd.append('--ignore-case')
        if file_pattern:
            cmd.extend(['--glob', file_pattern])
        
        cmd.extend([query, directory])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return f"Ripgrep Matches:\n{result.stdout}"[:10000] # Limit output
            elif result.returncode == 1:
                return "No matches found (rg)."
            elif result.returncode == 2:
                # rg error, fall through to python fallback
                pass
        except FileNotFoundError:
            # rg not installed
            pass
            
        # Fallback to Python implementation
        return find_in_files(directory, query, file_pattern or "*")
            
    except Exception as e:
        return f"Error searching codebase: {str(e)}"

@tool
@validate_args(IntrospectionArgs)
def get_agent_capabilities(category: str = "all") -> str:
    """
    Introspects the agent's own capabilities, configuration, and available tools.
    
    Args:
        category: 'capabilities', 'tools', 'config', 'all'

    Returns:
        str: Introspection report.
    """
    lines = []
    
    if category in ("tools", "all"):
        lines.append("## Available Tools")
        for name, func in TOOL_REGISTRY.items():
            doc = inspect.getdoc(func) or "No description."
            first_line = doc.split('\n')[0]
            lines.append(f"- **{name}**: {first_line}")
        lines.append("")

    if category in ("capabilities", "all"):
        lines.append("## Core Competencies")
        lines.append("1. System Operations (Files, Processes, Git)")
        lines.append("2. Python Engineering (Analysis, Refactoring, Testing)")
        lines.append("3. Deep Review & Orchestration")
        lines.append("4. Intelligent Search (Ripgrep/Native)")
        lines.append("")

    if category in ("config", "all"):
        lines.append("## Runtime Configuration")
        lines.append(f"Working Directory: {os.getcwd()}")
        lines.append(f"Python Version: {sys.version.split()[0]}")
        lines.append(f"Platform: {sys.platform}")
        
    return "\n".join(lines)

@tool
@validate_args(FindInFilesArgs)
def find_in_files(directory: str, search_text: str, file_pattern: str = "*.py") -> str:
    """
    Searches for text within files.
    
    Args:
        directory: Directory to search in.
        search_text: Text to search for.
        file_pattern: File pattern to search within (e.g., *.py).

    Returns:
        str: Found results or message.
    """
    try:
        import fnmatch
        results = []
        if not Path(directory).exists(): return f"Error: Directory '{directory}' not found."
        for root, _, files in os.walk(directory):
            for file in files:
                if fnmatch.fnmatch(file, file_pattern):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            if search_text in f.read(): results.append(f"{filepath}: Contains '{search_text}'")
                    except: continue
        return f"Found in {len(results)} files:\n" + "\n".join(results[:20]) if results else f"Text '{search_text}' not found in any {file_pattern} files."
    except Exception as e:
        return f"Error searching in files: {str(e)}"

@tool
@validate_args(ExecutePythonEnvArgs)
def execute_python_with_env(code: str, imports: Optional[List[str]] = None) -> str:
    """
    Executes Python code with pre-loaded imports.
    
    Args:
        code: Python code to execute.
        imports: List of modules to import before execution.

    Returns:
        str: Combined stdout and stderr or error message.
    """
    try:
        import_code = "".join(f"import {imp}\n" for imp in (imports or []))
        full_code = f"{import_code}\n{code}"
        result = subprocess.run([sys.executable, '-c', full_code], capture_output=True, text=True, timeout=30)
        output = []
        if result.stdout: output.append(f"Output:\n{result.stdout}")
        if result.stderr: output.append(f"Errors:\n{result.stderr}")
        return "\n".join(output) if output else "(No output)"
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out (30s limit)."

@tool
def update_plan(content: str) -> str:
    """
    Updates the 'plan.md' file to track project progress and next steps.
    
    Args:
        content: The full updated content for plan.md.

    Returns:
        str: Success or error message.
    """
    return write_file(filepath="plan.md", content=content)

@tool
def update_specs(content: str) -> str:
    """
    Updates the 'specs.md' file to document technical specifications and architecture.
    
    Args:
        content: The full updated content for specs.md.

    Returns:
        str: Success or error message.
    """
    return write_file(filepath="specs.md", content=content)

@tool
@validate_args(DelegateArgs)
def delegate_to_agent(agent_name: str, objective: str) -> str:
    """
    Delegates a complex task to a specialized sub-agent.
    
    Args:
        agent_name: Name of the specialized agent (e.g., "QA_Tester", "Researcher").
        objective: The detailed goal for the sub-agent to achieve.

    Returns:
        str: The result or report from the sub-agent.
    """
    try:
        # Dynamic import to avoid circular dependency
        from gemini_agent.core.sub_agent import SubAgent
        import asyncio
        
        agent = SubAgent(name=agent_name)
        result = asyncio.run(agent.run(objective))
        return f"Sub-Agent '{agent_name}' Result:\n{result}"
    except Exception as e:
        return f"Error delegating to agent: {str(e)}"

# --- Registry for Gemini ---

TOOL_FUNCTIONS = TOOL_REGISTRY

def get_tool_config(extra_declarations: Optional[List[types.FunctionDeclaration]] = None) -> types.Tool:
    """
    Returns the complete tool configuration for Gemini API.
    """
    declarations = [auto_generate_declaration(f) for f in TOOL_REGISTRY.values()]
    if extra_declarations: declarations.extend(extra_declarations)
    return types.Tool(function_declarations=declarations)
