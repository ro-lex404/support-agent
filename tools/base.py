import inspect
import json
from typing import Callable, Dict, Any, List, Optional, get_type_hints

def python_type_to_json_type(py_type: Any) -> str:
    """Maps Python types to JSON Schema primitive types."""
    if py_type in (int, float):
        return "number" if py_type is float else "integer"
    elif py_type is str:
        return "string"
    elif py_type is bool:
        return "boolean"
    elif py_type in (list, List):
        return "array"
    elif py_type in (dict, Dict):
        return "object"
    return "string"

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: List[Dict[str, Any]] = []

    def register(self, func: Optional[Callable] = None, name: Optional[str] = None, description: Optional[str] = None):
        """
        Decorator or direct method to register a Python function as an agent tool.
        Automatically derives OpenAI-compatible tool schema from function signature and docstrings.
        """
        def decorator(f: Callable):
            tool_name = name or f.__name__
            tool_doc = description or (inspect.getdoc(f) or "No description provided.")
            
            sig = inspect.signature(f)
            type_hints = get_type_hints(f) if hasattr(f, "__annotations__") else {}
            
            properties: Dict[str, Any] = {}
            required: List[str] = []
            
            for param_name, param in sig.parameters.items():
                if param_name in ("self", "cls"):
                    continue
                
                param_type = type_hints.get(param_name, str)
                json_type = python_type_to_json_type(param_type)
                
                properties[param_name] = {
                    "type": json_type,
                    "description": f"Parameter: {param_name}"
                }
                
                if param.default is inspect.Parameter.empty:
                    required.append(param_name)

            schema = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_doc,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    }
                }
            }
            
            self._tools[tool_name] = f
            self._schemas.append(schema)
            return f

        if func is None:
            return decorator
        return decorator(func)

    def get_schemas(self) -> List[Dict[str, Any]]:
        return self._schemas

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found in registry. Available: {list(self._tools.keys())}")
        func = self._tools[tool_name]
        return func(**arguments)

# Default global registry
registry = ToolRegistry()
tool = registry.register
