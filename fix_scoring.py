def fix():
    with open('datasets/benchmark/scoring.py', 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace("Questions: {summary.get('completed_questions', 0)}", "Executions Completed: {summary.get('completed_executions', 0)}")
    with open('datasets/benchmark/scoring.py', 'w', encoding='utf-8') as f:
        f.write(content)
if __name__ == '__main__':
    fix()
