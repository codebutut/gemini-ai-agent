import difflib
import ast
import re
import html
import subprocess
import tempfile
import os
import sys
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class ReviewEngine:
    """
    Core logic for the Deep Review system.
    Handles diff generation, static analysis, and security scanning.
    """

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
        Performs static analysis on the code using AST and pylint.
        
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
            return issues # Stop here if syntax is broken
        except Exception as e:
            issues.append(f"Error parsing code: {str(e)}")
            logger.error(f"AST parse error: {e}", exc_info=True)
            return issues

        # 2. Advanced analysis with pylint
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
                tmp.write(code)
                tmp_path = tmp.name

            # Run pylint as a module using the current python executable
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
            
            # Pylint output is in stdout
            if result.stdout:
                for line in result.stdout.splitlines():
                    # Skip the module header line
                    if line.startswith('************* Module'):
                        continue
                    if tmp_path in line:
                        # Clean up the temporary filename from the output
                        clean_line = line.replace(tmp_path, "code.py")
                        issues.append(f"LINT: {clean_line}")
        except FileNotFoundError:
            issues.append("LINT: pylint not found. Please install it for advanced analysis.")
        except subprocess.TimeoutExpired:
            issues.append("LINT: pylint timed out.")
        except Exception as e:
            issues.append(f"LINT: Error running pylint: {str(e)}")
            logger.error(f"pylint execution error: {e}", exc_info=True)
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
        
        # Regex patterns for common secrets
        patterns = {
            "AWS Key": r"AKIA[0-9A-Z]{16}",
            "Generic API Key": r"api_key\s*=\s*['\"][a-zA-Z0-9]{20,}['\"]",
            "Hardcoded Password": r"password\s*=\s*['\"][^'\"]{6,}['\"]",
            "Dangerous System Call": r"os\.system\(|subprocess\.call\(|eval\("
        }
        
        for name, pattern in patterns.items():
            if re.search(pattern, code, re.IGNORECASE):
                risks.append(f"WARNING: Potential {name} detected.")
                
        return risks
