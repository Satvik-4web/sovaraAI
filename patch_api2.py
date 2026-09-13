def patch_api():
    with open('api_server.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace('file_path = os.path.join(upload_dir, file.filename)', 'file_path = os.path.join(upload_dir, os.path.basename(file.filename))')
    
    with open('api_server.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    patch_api()
