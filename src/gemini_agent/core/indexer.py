import ast
import os
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

@dataclass
class Symbol:
    """Represents a code symbol (class, function, method) found during indexing."""
    name: str
    kind: str  # 'class', 'function', 'method'
    line: int
    file_path: str
    docstring: Optional[str] = None
    parent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converts the Symbol object to a dictionary."""
        return {
            "name": self.name,
            "kind": self.kind,
            "line": self.line,
            "file_path": self.file_path,
            "docstring": self.docstring,
            "parent": self.parent
        }

class SymbolVisitor(ast.NodeVisitor):
    """AST visitor to extract symbols from a Python file."""
    def __init__(self, file_path: str, rel_path: str) -> None:
        self.file_path = file_path
        self.rel_path = rel_path
        self.symbols: List[Symbol] = []
        self._current_class: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visits a class definition and records it as a symbol."""
        self.symbols.append(Symbol(
            name=node.name,
            kind='class',
            line=node.lineno,
            file_path=self.rel_path,
            docstring=ast.get_docstring(node)
        ))
        old_class = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visits a function or method definition and records it as a symbol."""
        kind = 'method' if self._current_class else 'function'
        self.symbols.append(Symbol(
            name=node.name,
            kind=kind,
            line=node.lineno,
            file_path=self.rel_path,
            docstring=ast.get_docstring(node),
            parent=self._current_class
        ))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visits an async function or method definition and records it as a symbol."""
        kind = 'method' if self._current_class else 'function'
        self.symbols.append(Symbol(
            name=node.name,
            kind=kind,
            line=node.lineno,
            file_path=self.rel_path,
            docstring=ast.get_docstring(node),
            parent=self._current_class
        ))
        self.generic_visit(node)

class Indexer:
    """Handles project-wide indexing of Python symbols."""
    def __init__(self, root_dir: str) -> None:
        self.root_dir = root_dir
        self.symbols: List[Symbol] = []

    def index_project(self) -> None:
        """Recursively scans the project directory for Python files and indexes symbols."""
        self.symbols = []
        for root, dirs, files in os.walk(self.root_dir):
            # Skip hidden directories and common non-source dirs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('env', 'venv', '__pycache__', 'node_modules')]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    self.index_file(file_path)

    def index_file(self, file_path: str) -> None:
        """Indexes symbols in a single Python file.
        
        Args:
            file_path: The absolute path to the Python file.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
            
            rel_path = os.path.relpath(file_path, self.root_dir)
            visitor = SymbolVisitor(file_path, rel_path)
            visitor.visit(tree)
            self.symbols.extend(visitor.symbols)
        except (SyntaxError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error indexing {file_path}: {e}", exc_info=True)

    def search(self, query: str) -> List[Symbol]:
        """Searches for symbols matching the query string.
        
        Args:
            query: The search query.

        Returns:
            List[Symbol]: A list of matching symbols.
        """
        query = query.lower()
        return [s for s in self.symbols if query in s.name.lower()]

    def get_all_symbols(self) -> List[Symbol]:
        """Returns all indexed symbols."""
        return self.symbols
