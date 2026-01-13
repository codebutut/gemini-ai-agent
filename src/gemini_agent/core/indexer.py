import ast
import os
import logging
import json
import functools
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from concurrent.futures import ProcessPoolExecutor

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

def _index_file_worker(file_path: str, root_dir: str) -> Optional[Dict[str, Any]]:
    """Worker function for parallel indexing. Must be top-level for pickling."""
    try:
        mtime = os.path.getmtime(file_path)
        
        # Check file size before reading (1MB limit for indexing)
        if os.path.getsize(file_path) > 1024 * 1024:
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)
        
        rel_path = os.path.relpath(file_path, root_dir)
        visitor = SymbolVisitor(file_path, rel_path)
        visitor.visit(tree)
        
        return {
            'path': file_path,
            'mtime': mtime,
            'symbols': [s.to_dict() for s in visitor.symbols]
        }
    except Exception as e:
        # We don't log here to avoid issues with logging in subprocesses
        return None

class Indexer:
    """Handles project-wide indexing of Python symbols with persistent caching."""
    def __init__(self, root_dir: str) -> None:
        self.root_dir = root_dir
        self.symbols: List[Symbol] = []
        self.name_map: Dict[str, List[Symbol]] = {}
        self.file_cache: Dict[str, Dict[str, Any]] = {} # path -> {mtime, symbols}
        self.load_cache()

    def _get_cache_path(self) -> str:
        """Returns the path to the persistent cache file."""
        return os.path.join(self.root_dir, ".gemini_index_cache.json")

    def load_cache(self) -> None:
        """Loads the index cache from disk."""
        cache_path = self._get_cache_path()
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert dicts back to Symbol objects
                    self.file_cache = {}
                    for path, entry in data.items():
                        symbols = [Symbol(**s) for s in entry['symbols']]
                        self.file_cache[path] = {
                            'mtime': entry['mtime'],
                            'symbols': symbols
                        }
                logger.info(f"Loaded index cache from {cache_path}")
            except Exception as e:
                logger.warning(f"Failed to load index cache: {e}")

    def save_cache(self) -> None:
        """Saves the index cache to disk."""
        cache_path = self._get_cache_path()
        try:
            # Convert Symbol objects to dicts for JSON serialization
            serializable_cache = {}
            for path, entry in self.file_cache.items():
                serializable_cache[path] = {
                    'mtime': entry['mtime'],
                    'symbols': [s.to_dict() for s in entry['symbols']]
                }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_cache, f, indent=2)
            logger.info(f"Saved index cache to {cache_path}")
        except Exception as e:
            logger.error(f"Failed to save index cache: {e}")

    def index_project(self) -> None:
        """Recursively scans the project directory for Python files and indexes symbols in parallel."""
        files_to_index = []
        current_files = set()

        for root, dirs, files in os.walk(self.root_dir):
            # Skip hidden directories and common non-source dirs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('env', 'venv', '__pycache__', 'node_modules')]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    current_files.add(file_path)
                    
                    # Check if needs update
                    try:
                        mtime = os.path.getmtime(file_path)
                        if file_path not in self.file_cache or self.file_cache[file_path]['mtime'] != mtime:
                            files_to_index.append(file_path)
                    except OSError:
                        continue

        # Parallel indexing for new/changed files
        if files_to_index:
            logger.info(f"Indexing {len(files_to_index)} files in parallel...")
            worker_func = functools.partial(_index_file_worker, root_dir=self.root_dir)
            
            # Use max_workers=None to let it decide based on CPU count
            with ProcessPoolExecutor() as executor:
                results = list(executor.map(worker_func, files_to_index))
            
            for res in results:
                if res:
                    self.file_cache[res['path']] = {
                        'mtime': res['mtime'],
                        'symbols': [Symbol(**s) for s in res['symbols']]
                    }

        # Clean up cache for deleted files
        self.file_cache = {path: data for path, data in self.file_cache.items() if path in current_files}
        
        # Rebuild global symbols and name_map from cache
        self.symbols = []
        self.name_map = {}
        for data in self.file_cache.values():
            file_symbols = data['symbols']
            self.symbols.extend(file_symbols)
            for s in file_symbols:
                self.name_map.setdefault(s.name.lower(), []).append(s)
        
        self.save_cache()

    def search(self, query: str) -> List[Symbol]:
        """Searches for symbols matching the query string.
        
        Args:
            query: The search query.

        Returns:
            List[Symbol]: A list of matching symbols.
        """
        query = query.lower()
        # Exact match O(1)
        if query in self.name_map:
            return self.name_map[query]
        # Partial match O(N)
        return [s for s in self.symbols if query in s.name.lower()]

    def get_all_symbols(self) -> List[Symbol]:
        """Returns all indexed symbols."""
        return self.symbols
