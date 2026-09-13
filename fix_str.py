def fix():
    with open('agents/planner.py', 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('\\"\\"\\"', '\"\"\"')
    with open('agents/planner.py', 'w', encoding='utf-8') as f:
        f.write(content)
if __name__ == '__main__':
    fix()
