"""
Sample script demonstrating basic Python code execution using SOVARA execute_python.
"""

import sys
import os
import json

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tools.c_tools.sandbox.python_executor import execute_python

def main():
    print("--- 1. Executing Basic Arithmetic ---")
    code_arithmetic = "print(125 * 48)"
    res1 = execute_python(code_arithmetic)
    print("Code:", code_arithmetic)
    print("Response:")
    print(json.dumps(res1, indent=2))
    print()

    print("--- 2. Executing Math Calculation ---")
    code_math = "import math\nprint(math.sqrt(144))"
    res2 = execute_python(code_math)
    print("Code:", code_math)
    print("Response:")
    print(json.dumps(res2, indent=2))
    print()

if __name__ == "__main__":
    main()
