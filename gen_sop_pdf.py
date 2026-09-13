from tools.c_tools.documents.pdf_generator import write_pdf
import os

md_path = "datasets/synthetic_plant/documents/P101_Maintenance_SOP.md"
with open(md_path, "r", encoding="utf-8") as f:
    text = f.read()

res = write_pdf(file_path="demo/maintenance_sop.pdf", content=text)
print("PDF creation:", res)
