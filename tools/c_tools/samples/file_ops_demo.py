"""
Sample script demonstrating secure file operations in SOVARA.
"""

import sys
import os
import json

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tools.c_tools.file_ops.file_manager import (
    write_file_content,
    read_file_content,
    list_workspace_directory,
    delete_workspace_file,
)
from tools.c_tools.file_ops.path_security import validate_workspace_path

def main():
    print("--- 1. Writing Workspace File ---")
    res_write = write_file_content("demo/sample.txt", "SOVARA Confidential Data Log\nLine 2", overwrite=True)
    print(json.dumps(res_write, indent=2))
    print()

    print("--- 2. Reading Workspace File ---")
    res_read = read_file_content("demo/sample.txt")
    print(json.dumps(res_read, indent=2))
    print()

    print("--- 3. Path Traversal Attack Defense Demo ---")
    try:
        validate_workspace_path("../../etc/passwd")
    except ValueError as e:
        print("Blocked Path Traversal Attempt:")
        print(f"  Error: {e}")
    print()

    print("--- 4. Listing Workspace Directory ---")
    res_list = list_workspace_directory("demo")
    print(json.dumps(res_list, indent=2))

if __name__ == "__main__":
    main()
