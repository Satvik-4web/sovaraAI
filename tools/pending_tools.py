from pydantic import BaseModel
from tools.registry import registry

class MockToolInput(BaseModel):
    file_path: str

def analyze_excel(file_path: str) -> str:
    return "Error: Integration pending (Person C Excel tool missing)"

def analyze_csv(file_path: str) -> str:
    return "Error: Integration pending (Person C CSV tool missing)"

def read_file(file_path: str) -> str:
    return "Error: Integration pending (Person C File Read tool missing)"

def generate_docx(file_path: str) -> str:
    return "Error: Integration pending (Person C DOCX tool missing)"

def generate_xlsx(file_path: str) -> str:
    return "Error: Integration pending (Person C XLSX tool missing)"

def generate_pptx(file_path: str) -> str:
    return "Error: Integration pending (Person C PPTX tool missing)"

def generate_pdf(file_path: str) -> str:
    return "Error: Integration pending (Person C PDF tool missing)"

registry.register("analyze_excel", "Analyze an Excel file", analyze_excel, MockToolInput, str)
registry.register("analyze_csv", "Analyze a CSV file", analyze_csv, MockToolInput, str)
registry.register("read_file", "Read file contents", read_file, MockToolInput, str)
registry.register("generate_docx", "Generate a Word document", generate_docx, MockToolInput, str)
registry.register("generate_xlsx", "Generate an Excel spreadsheet", generate_xlsx, MockToolInput, str)
registry.register("generate_pptx", "Generate a PowerPoint presentation", generate_pptx, MockToolInput, str)
registry.register("generate_pdf", "Generate a PDF document", generate_pdf, MockToolInput, str)
