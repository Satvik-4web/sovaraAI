def fix():
    with open('datasets/benchmark/benchmark_runner.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'import sys' not in content:
        content = content.replace('import json', 'import json\nimport sys')
        
    with open('datasets/benchmark/benchmark_runner.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix()
