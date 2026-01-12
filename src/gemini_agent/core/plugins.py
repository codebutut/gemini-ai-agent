import os
import importlib.util
import inspect
import logging
from typing import List, Dict, Any, Type, Optional
from google.genai import types

class Plugin:
    """Base class for all plugins."""
    name: str = "Base Plugin"
    description: str = "Description of the plugin."
    version: str = "0.1.0"
    author: str = "Unknown"

    def __init__(self):
        self.enabled = True

    def get_tools(self) -> List[types.FunctionDeclaration]:
        """Return a list of tool definitions provided by this plugin."""
        return []

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool provided by this plugin."""
        raise NotImplementedError("Plugins must implement execute_tool if they provide tools.")

class PluginManager:
    """Manages discovery and loading of plugins."""
    def __init__(self, plugins_dir: str = "plugins"):
        self.plugins_dir = plugins_dir
        self.plugins: Dict[str, Plugin] = {}
        self.logger = logging.getLogger(__name__)

        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)

    def discover_plugins(self):
        """Discover and load plugins from the plugins directory."""
        self.plugins = {}
        for filename in os.listdir(self.plugins_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                filepath = os.path.join(self.plugins_dir, filename)
                self.load_plugin(filepath)

    def load_plugin(self, filepath: str):
        """Load a plugin from a file."""
        try:
            module_name = os.path.splitext(os.path.basename(filepath))[0]
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, Plugin) and obj is not Plugin:
                        plugin_instance = obj()
                        self.plugins[plugin_instance.name] = plugin_instance
                        self.logger.info(f"Loaded plugin: {plugin_instance.name}")
        except Exception as e:
            self.logger.error(f"Failed to load plugin from {filepath}: {e}")

    def get_enabled_plugins(self) -> List[Plugin]:
        """Return a list of currently enabled plugins."""
        return [p for p in self.plugins.values() if p.enabled]

    def get_all_tools(self) -> List[types.FunctionDeclaration]:
        """Collect all tools from enabled plugins."""
        all_tools = []
        for plugin in self.get_enabled_plugins():
            all_tools.extend(plugin.get_tools())
        return all_tools

    def execute_plugin_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Find the plugin that provides the tool and execute it."""
        for plugin in self.get_enabled_plugins():
            for tool_decl in plugin.get_tools():
                if tool_decl.name == tool_name:
                    return plugin.execute_tool(tool_name, args)
        raise ValueError(f"Tool '{tool_name}' not found in any enabled plugin.")
