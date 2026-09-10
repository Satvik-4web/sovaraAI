import pandas as pd
import os

try:
    df = pd.DataFrame({"Pump": ["PUMP P-999"], "Status": ["VIBRATION DETECTED"], "Pressure": [120.5]})
    df.to_excel('demo/pump_inspection.xlsx', index=False)
    print("Created real Excel file for pump_inspection.xlsx")
except Exception as e:
    print("Failed:", e)
