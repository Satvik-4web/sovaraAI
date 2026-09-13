import sys
with open('api_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'chat_router' not in content:
    content = content.replace('from main import run_sovara_task', 'from main import run_sovara_task\nfrom patch_api import chat_router')
    content = content.replace('app = FastAPI(title="SOVARA API")', 'app = FastAPI(title="SOVARA API")\napp.include_router(chat_router)')
    
    with open('api_server.py', 'w', encoding='utf-8') as f:
        f.write(content)
