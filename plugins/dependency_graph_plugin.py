import os
import ast
from gemini_agent.core.plugins import Plugin
from typing import List, Dict, Any
from google.genai import types

class DependencyGraphPlugin(Plugin):
    name = "Dependency Graph"
    description = "Analyzes Python files to map out imports and dependencies."
    version = "1.0.0"
    author = "Conductor Team"

    def get_tools(self) -> List[types.FunctionDeclaration]:
        return [
            types.FunctionDeclaration(
                name="get_dependency_graph",
                description="Analyze Python files in a directory to map out imports and dependencies between modules.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "directory": types.Schema(
                            type=types.Type.STRING,
                            description="The directory to analyze (default is current directory)."
                        ),
                        "recursive": types.Schema(
                            type=types.Type.BOOLEAN,
                            description="Whether to search recursively (default is True)."
                        )
                    }
                )
            )
        ]

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "get_dependency_graph":
            directory = args.get("directory", ".")
            recursive = args.get("recursive", True)
            return self._generate_graph(directory, recursive)
        return None

    def _generate_graph(self, directory: str, recursive: bool) -> Dict[str, List[str]]:
        graph = {}
        try:
            for root, _, files in os.walk(directory):
                if not recursive and root != directory:
                    continue
                
                # Skip hidden directories and __pycache__
                parts = root.split(os.sep)
                if any((part.startswith('.') and part not in ('.', '..')) or part == '__pycache__' for part in parts):
                    continue

                for file in files:
                    if file.endswith(".py"):
                        filepath = os.path.join(root, file)
                        rel_path = os.path.relpath(filepath, directory)
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                tree = ast.parse(f.read(), filename=filepath)
                            
                            imports = []
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Import):
                                    for alias in node.names:
                                        imports.append(alias.name)
                                elif isinstance(node, ast.ImportFrom):
                                    if node.module:
                                        imports.append(node.module)
                            
                            graph[rel_path] = sorted(list(set(imports)))
                        except Exception as e:
                            graph[rel_path] = [f"Error parsing: {str(e)}"]
        except Exception as e:
            return {"error": str(e)}
        return graph
