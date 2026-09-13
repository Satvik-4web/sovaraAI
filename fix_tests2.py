def fix_tests():
    with open('tests/test_e2e_workflow.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace('res["status"] != "error"', 'res.get("success", False) is True')

    with open('tests/test_e2e_workflow.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix_tests()
