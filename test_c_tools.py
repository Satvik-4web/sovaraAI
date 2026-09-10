from tools.c_tools_integration import execute_python, read_file_content, write_file_content, analyze_csv, generate_docx

# 1. Python execution
res1 = execute_python(code="print('Hello World')\nresult = 5 + 5")
print("Python Execute:", res1)

# 2. Python timeout
res2 = execute_python(code="import time\ntime.sleep(5)", timeout=2)
print("Python Timeout:", res2)

# 3. Path Security
try:
    res3 = read_file_content(file_path="../../secret.txt")
    print("Path Security (Read):", res3)
except Exception as e:
    print("Path Security Error:", e)

# 4. Generate DOCX
res4 = generate_docx(filename="test_output.docx", title="Test Title", sections=[{"heading": "Test", "content": "Hello"}])
print("Generate DOCX:", res4)

