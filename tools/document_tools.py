from pydantic import BaseModel
from .registry import registry
import os

class WriteFileInput(BaseModel):
    file_path: str
    content: str

def write_file(file_path: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Success: wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"

registry.register("write_file", "Write content to a file", write_file, WriteFileInput, str)