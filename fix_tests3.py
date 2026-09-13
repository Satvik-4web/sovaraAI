def fix_tests():
    with open('tests/test_e2e_workflow.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace('tasks_db[task_id] = {"id": task_id, "status": "CREATED", "events": []}\n    \n    files', 'tasks_db[task_id] = {"id": task_id, "status": "CREATED", "events": []}\n    files_db[task_id] = []\n    \n    files')

    with open('tests/test_e2e_workflow.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix_tests()
