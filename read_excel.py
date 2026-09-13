import openpyxl
wb = openpyxl.load_workbook('demo/pump_inspection.xlsx')
ws = wb.active
for row in ws.iter_rows(values_only=True):
    print(row)
