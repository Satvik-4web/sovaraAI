"""
Sample script demonstrating output contract validation and file integrity checks in SOVARA.
"""

import sys
import os
import json

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tools.c_tools.file_ops.file_manager import write_file_content
from tools.c_tools.validation.output_validator import validate_tool_output
from tools.c_tools.validation.file_validator import validate_file_integrity

def main():
    print("--- 1. Validating Valid Tool Output Payload ---")
    valid_payload = {
        "success": True,
        "stdout": "100\n",
        "stderr": "",
        "result": 100,
        "execution_time": 0.012,
    }
    res_val1 = validate_tool_output(valid_payload)
    print(json.dumps(res_val1, indent=2))
    print()

    print("--- 2. Validating Malformed Tool Output Payload ---")
    invalid_payload = {
        "success": True,
        # Missing stdout, stderr, result, execution_time
    }
    res_val2 = validate_tool_output(invalid_payload)
    print(json.dumps(res_val2, indent=2))
    print()

    print("--- 3. Creating Workspace File and Validating Integrity & SHA-256 Checksum ---")
    write_file_content("demo/secure_payload.txt", "SOVARA Top Secret Document 2026", overwrite=True)
    res_file_val = validate_file_integrity("demo/secure_payload.txt")
    print(json.dumps(res_file_val, indent=2))

if __name__ == "__main__":
    main()
