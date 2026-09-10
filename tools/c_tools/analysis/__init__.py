"""
Data analysis package providing structured inspection for CSV and Excel files.
"""

from tools.c_tools.analysis.csv_analyzer import analyze_csv
from tools.c_tools.analysis.excel_analyzer import analyze_excel

__all__ = [
    "analyze_csv",
    "analyze_excel",
]
