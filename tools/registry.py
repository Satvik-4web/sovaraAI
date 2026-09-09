from typing import Dict, Any, Callable, List
from pydantic import BaseModel

class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name: str, description: str, func: Callable, input_schema: Any, output_schema: Any, local_only: bool = True):
        self.tools[name] = {
            "name": name,
            "description": description,
            "func": func,
            "input_schema": input_schema,
            "output_schema": output_schema,
            "local_only": local_only
        }
    
    def get_tool(self, name: str):
        return self.tools.get(name)

    def execute(self, name: str, kwargs: Dict[str, Any]):
        tool = self.tools.get(name)
        if not tool:
            raise ValueError(f"Tool {name} not found")
        return tool["func"](**kwargs)

    def get_all_tools_schema(self) -> List[Dict]:
        schemas = []
        for name, tool in self.tools.items():
            schemas.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool["description"],
                    "parameters": tool["input_schema"].model_json_schema()
                }
            })
        return schemas

registry = ToolRegistry()