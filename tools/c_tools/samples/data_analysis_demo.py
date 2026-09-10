"""
Sample script demonstrating CSV data analysis in SOVARA.
"""

import sys
import os
import json

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tools.c_tools.file_ops.file_manager import write_file_content
from tools.c_tools.analysis.csv_analyzer import analyze_csv

def main():
    print("--- 1. Creating Sample CSV Data ---")
    sample_csv = (
        "employee_id,department,salary,active\n"
        "E101,Engineering,95000.50,true\n"
        "E102,Research,105000.00,true\n"
        "E103,Operations,,false\n"
        "E104,Engineering,88000.00,true\n"
    )
    write_file_content("demo/employees.csv", sample_csv, overwrite=True)
    print("Created demo/employees.csv")
    print()

    print("--- 2. Analyzing CSV Data Structure ---")
    analysis_res = analyze_csv("demo/employees.csv", preview_rows=3)
    print(json.dumps(analysis_res, indent=2))

if __name__ == "__main__":
    main()
