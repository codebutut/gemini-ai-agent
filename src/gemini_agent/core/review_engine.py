import difflib
import ast
import re
import html
import subprocess
import tempfile
import os
import sys
import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

class ReviewEngine:
    """
    Core logic for the Deep Review system.
    Handles diff generation, static analysis, and security scanning.
    """

    # Pre-compiled and combined security patterns for performance
    _SECURITY_PATTERN = re.compile(
        r"(?P<aws>AKIA[0-9A-Z]{16})|"
        r"(?P<api_key>api_key\s*=\s*['\"][a-zA-Z0-9_\-]{20,}['\"])|"
        r"(?P<password>password\s*=\s*['\"][^'\"]{6,}['\"])|"
        r"(?P<syscall>os\.system\(|subprocess\.call\(|eval\()",
        re.IGNORECASE
    )
    
    _RISK_LABELS = {
        "aws": "AWS Key",
        "api_key": "Generic API Key",
        "password": "Hardcoded Password",
        "syscall": "Dangerous System Call"
    }

    @staticmethod
    def generate_diff_html(old_content: str, new_content: str, theme_mode: str = "Dark") -> str:
        """
        Generates a side-by-side or unified diff in HTML format.
        
        Args:
            old_content: Original text content.
            new_content: Modified text content.
            theme_mode: UI theme ('Dark' or 'Light').

        Returns:
            str: HTML formatted diff.
        """
        if not old_content:
            old_content = ""
        if not new_content:
            new_content = ""

        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        diff = difflib.unified_diff(
            old_lines, new_lines, 
            fromfile='Current', tofile='Proposed', 
            lineterm=''
        )
        
        # Theme-aware colors
        if theme_mode == "Dark":
            add_bg = "#1e3a1e"
            add_fg = "#afffbe"
            rem_bg = "#442a2a"
            rem_fg = "#ffa3a3"
            info_fg = "#8be9fd"
            default_fg = "#888"
        else:
            add_bg = "#e6ffec"
            add_fg = "#22863a"
            rem_bg = "#ffebe9"
            rem_fg = "#cb2431"
            info_fg = "#005cc5"
            default_fg = "#6a737d"

        # Convert to HTML
        html_output = [f"<pre style='font-family: monospace; white-space: pre; color: {default_fg};'>"]
        for line in diff:
            escaped_line = html.escape(line)
            if line.startswith('+'):
                html_output.append(f"<div style='color: {add_fg}; background-color: {add_bg};'>{escaped_line}</div>")
            elif line.startswith('-'):
                html_output.append(f"<div style='color: {rem_fg}; background-color: {rem_bg};'>{escaped_line}</div>")
            elif line.startswith('^'):
                html_output.append(f"<div style='color: {info_fg};'>{escaped_line}</div>")
            elif line.startswith('@@'):
                html_output.append(f"<div style='color: {info_fg}; font-weight: bold;'>{escaped_line}</div>")
            else:
                html_output.append(f"<div>{escaped_line}</div>")
        html_output.append("</pre>")
        
        return "\n".join(html_output)

    @staticmethod
    def analyze_code(code: str) -> List[str]:
        """
        Performs static analysis on the code using AST, ruff (primary), and pylint (fallback).
        
        Args:
            code: The Python code string to analyze.

        Returns:
            List[str]: A list of issues found.
        """
        issues: List[str] = []
        
        # 1. Basic AST check
        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(f"CRITICAL: Syntax Error at line {e.lineno}: {e.msg}")
            return issues 
        except Exception as e:
            issues.append(f"Error parsing code: {str(e)}")
            logger.error(f"AST parse error: {e}", exc_info=True)
            return issues

        # 2. Advanced analysis
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
                tmp.write(code)
                tmp_path = tmp.name

            # Try Ruff first (much faster)
            try:
                result = subprocess.run(
                    ['ruff', 'check', '--no-cache', '--output-format=concise', tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.stdout:
                    for line in result.stdout.splitlines():
                        if tmp_path in line:
                            clean_line = line.replace(tmp_path, "code.py").strip()
                            issues.append(f"LINT (ruff): {clean_line}")
                
                # If ruff is found and executed (even with 0 issues), we skip pylint
            except FileNotFoundError:
                # Fallback to pylint if ruff is not installed
                result = subprocess.run(
                    [
                        sys.executable,
                        '-m',
                        'pylint', 
                        '--max-line-length=120', 
                        '--reports=n', 
                        '--score=n',
                        '--disable=C0114,C0115,C0116',
                        tmp_path
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if result.stdout:
                    for line in result.stdout.splitlines():
                        if not line.startswith('************* Module') and tmp_path in line:
                            clean_line = line.replace(tmp_path, "code.py")
                            issues.append(f"LINT (pylint): {clean_line}")
            
        except subprocess.TimeoutExpired:
            issues.append("LINT: Analysis timed out.")
        except Exception as e:
            issues.append(f"LINT: Error running analysis: {str(e)}")
            logger.error(f"Analysis execution error: {e}", exc_info=True)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
            
        return issues

    @staticmethod
    def scan_security(code: str) -> List[str]:
        """
        Scans for potential security risks using regex patterns.
        
        Args:
            code: The Python code string to scan.

        Returns:
            List[str]: A list of potential security risks.
        """
        risks: List[str] = []
        
        # Use combined regex for single-pass scanning
        for match in ReviewEngine._SECURITY_PATTERN.finditer(code):
            for group_name, value in match.groupdict().items():
                if value:
                    label = ReviewEngine._RISK_LABELS.get(group_name, "Unknown Risk")
                    risks.append(f"WARNING: Potential {label} detected.")
                
        return list(set(risks)) # Return unique risks
