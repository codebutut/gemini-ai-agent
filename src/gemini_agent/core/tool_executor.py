import logging
import time
from typing import Any, Dict, Optional, Callable, Tuple
from gemini_agent.core import tools
from gemini_agent.config.app_config import AppConfig
from gemini_agent.core.plugins import PluginManager

class ToolExecutor:
    """
    Handles execution of tools, including special session-specific tools.
    """
    def __init__(
        self, 
        status_callback: Callable[[str], None],
        terminal_callback: Callable[[str, str], None],
        confirmation_callback: Callable[[str, Dict[str, Any]], Tuple[bool, Optional[Dict[str, Any]]]],
        plugin_manager: Optional[PluginManager] = None
    ):
        self.status_callback = status_callback
        self.terminal_callback = terminal_callback
        self.confirmation_callback = confirmation_callback
        self.plugin_manager = plugin_manager
        
        # Session state managed by the worker but updated via tools
        self.current_plan = ""
        self.current_specs = ""
        
        # Handlers for special tools
        self.special_handlers = {
            "update_plan": self._handle_update_plan,
            "update_specs": self._handle_update_specs,
            "read_file": self._handle_read_file,
            "write_file": self._handle_write_file,
        }

    def execute(self, fn_name: str, fn_args: Dict[str, Any]) -> str:
        """Execute a tool and return the result."""
        sanitized_args = self._sanitize_args(fn_name, fn_args)
        
        # Check for special handlers
        if fn_name in self.special_handlers:
            return self.special_handlers[fn_name](fn_args)

        # Check for dangerous tools
        if fn_name in AppConfig.DANGEROUS_TOOLS:
            allowed, modified_args = self.confirmation_callback(fn_name, fn_args)
            if not allowed:
                self.status_callback(f"🚫 Denied: {fn_name}")
                self.terminal_callback(f"🚫 Denied: {fn_name}\n", "error")
                return f"Error: User denied execution of '{fn_name}'."
            
            if modified_args:
                fn_args = modified_args
                sanitized_args = self._sanitize_args(fn_name, fn_args) # Re-sanitize
                self.terminal_callback(f"✏️ Args modified by user.\n", "info")

        self.status_callback(f"⚙️ Executing: {fn_name}...")
        self.terminal_callback(f"⚙️ Executing: {fn_name}({sanitized_args})\n", "info")
        time.sleep(0.1)
        
        try:
            if fn_name in tools.TOOL_FUNCTIONS:
                result = tools.TOOL_FUNCTIONS[fn_name](**fn_args)
                self.status_callback(f"✅ Completed: {fn_name}")
                self.terminal_callback(f"✅ {fn_name} completed.\n", "success")
                return str(result)
            elif self.plugin_manager:
                try:
                    result = self.plugin_manager.execute_plugin_tool(fn_name, fn_args)
                    self.status_callback(f"✅ Completed (Plugin): {fn_name}")
                    self.terminal_callback(f"✅ {fn_name} (Plugin) completed.\n", "success")
                    return str(result)
                except ValueError:
                    return f"Error: Tool '{fn_name}' not found."
            else:
                return f"Error: Tool '{fn_name}' not found."
        except Exception as e:
            error_msg = f"Error in {fn_name}: {str(e)}"
            logging.error(f"Execution failure for {fn_name}: {e}", exc_info=True)
            self.status_callback(f"❌ Failed: {fn_name}")
            self.terminal_callback(f"❌ {error_msg}\n", "error")
            return error_msg

    def _sanitize_args(self, fn_name: str, fn_args: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitizes sensitive information in tool arguments."""
        sanitized = fn_args.copy()
        sensitive_keys = ["api_key", "password", "token", "secret", "content"]
        
        for key in sanitized:
            if any(sk in key.lower() for sk in sensitive_keys):
                if isinstance(sanitized[key], str):
                    if len(sanitized[key]) > 20:
                        sanitized[key] = f"{sanitized[key][:5]}...[REDACTED]...{sanitized[key][-5:]}"
                    else:
                        sanitized[key] = "[REDACTED]"
        return sanitized

    def _handle_update_plan(self, fn_args: Dict[str, Any]) -> str:
        self.current_plan = fn_args.get("content", "")
        self.status_callback(f"✅ Plan updated")
        self.terminal_callback(f"📝 Plan updated\n", "success")
        return "Plan updated successfully in session context."

    def _handle_update_specs(self, fn_args: Dict[str, Any]) -> str:
        self.current_specs = fn_args.get("content", "")
        self.status_callback(f"✅ Specifications updated")
        self.terminal_callback(f"📝 Specifications updated\n", "success")
        return "Specifications updated successfully in session context."

    def _handle_read_file(self, fn_args: Dict[str, Any]) -> str:
        filepath = fn_args.get("filepath", "")
        if filepath == "plan.md":
            self.status_callback(f"📖 Reading virtual plan.md")
            return self.current_plan if self.current_plan else "plan.md is currently empty."
        if filepath == "specs.md":
            self.status_callback(f"📖 Reading virtual specs.md")
            return self.current_specs if self.current_specs else "specs.md is currently empty."
        
        # Fallback to real file read
        return str(tools.read_file(**fn_args))

    def _handle_write_file(self, fn_args: Dict[str, Any]) -> str:
        filepath = fn_args.get("filepath", "")
        content = fn_args.get("content", "")
        if filepath == "plan.md":
            self.current_plan = content
            self.status_callback(f"✅ Plan updated (via write_file)")
            self.terminal_callback(f"📝 Plan updated (via write_file)\n", "success")
            return "Successfully updated plan.md in session context."
        if filepath == "specs.md":
            self.current_specs = content
            self.status_callback(f"✅ Specifications updated (via write_file)")
            self.terminal_callback(f"📝 Specifications updated (via write_file)\n", "success")
            return "Successfully updated specs.md in session context."
        
        # Fallback to real file write
        return str(tools.write_file(**fn_args))
