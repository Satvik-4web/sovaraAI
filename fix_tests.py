def fix_tests():
    with open('tests/test_e2e_workflow.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace('tasks_db[task_id] = {"id": task_id, "status": "CREATED", "events": []}', 'tasks_db[task_id] = {"id": task_id, "status": "CREATED", "events": []}\n    files_db[task_id] = []')
    
    # And import files_db
    content = content.replace('from api_server import app, tasks_db', 'from api_server import app, tasks_db, files_db')

    with open('tests/test_e2e_workflow.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix_tests()
