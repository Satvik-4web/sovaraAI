def fix():
    with open('agents/planner.py', 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace(
        '"options": {"temperature": 0.1}',
        '"options": {"temperature": 0.1}, "keep_alive": 0'
    )
    
    with open('agents/planner.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
    with open('agents/executor.py', 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace(
        '"options": {"temperature": 0.2}',
        '"options": {"temperature": 0.2}, "keep_alive": 0'
    )
    
    with open('agents/executor.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix()
