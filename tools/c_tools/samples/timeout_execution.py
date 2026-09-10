"""
Sample script demonstrating timeout limit enforcement in SOVARA Docker sandbox.
"""

import sys
import os
import json

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tools.c_tools.sandbox.python_executor import execute_python

def main():
    print("--- Executing Infinite Loop Code with 2s Timeout ---")
    infinite_loop_code = "while True:\n    pass"
    res = execute_python(infinite_loop_code, timeout=2)
    print("Code:", infinite_loop_code)
    print("Response:")
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
