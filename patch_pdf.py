def patch_pdf_processor():
    with open('multimodal/pdf_processor.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace fitz.open(str(pdf_path)) with fitz.open(str(Path(pdf_path).resolve()))
    content = content.replace('fitz.open(str(pdf_path))', 'fitz.open(str(Path(pdf_path).resolve()))')
    
    with open('multimodal/pdf_processor.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    patch_pdf_processor()
