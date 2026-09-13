def fix():
    with open('tests/test_fallback_pipeline.py', 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace(
        'assert len(res["evidence"]) > 0, "Evidence should not be lost on fallback"',
        'assert len(res["evidence"]) > 0, f"Evidence empty! Errors: {res.get(\'errors\')}"'
    )
    
    with open('tests/test_fallback_pipeline.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix()
