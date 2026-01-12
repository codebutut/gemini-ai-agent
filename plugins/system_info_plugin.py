import platform
import psutil
from gemini_agent.core.plugins import Plugin
from typing import List, Dict, Any
from google.genai import types

class SystemInfoPlugin(Plugin):
    name = "System Info"
    description = "Provides information about the host system (CPU, Memory, OS)."
    version = "1.0.0"
    author = "Conductor Team"

    def get_tools(self) -> List[types.FunctionDeclaration]:
        return [
            types.FunctionDeclaration(
                name="get_system_info",
                description="Get information about the host system's CPU, memory, and operating system.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={}
                )
            )
        ]

    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name == "get_system_info":
            try:
                cpu_freq = psutil.cpu_freq()
                cpu_freq_val = cpu_freq.current if cpu_freq else "Unknown"
                
                return {
                    "os": platform.system(),
                    "os_release": platform.release(),
                    "cpu_count": psutil.cpu_count(),
                    "cpu_freq": cpu_freq_val,
                    "memory_total": f"{psutil.virtual_memory().total / (1024**3):.2f} GB",
                    "memory_available": f"{psutil.virtual_memory().available / (1024**3):.2f} GB"
                }
            except Exception as e:
                return {"error": str(e)}
        return None
