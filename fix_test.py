def fix():
    with open('tests/test_fallback_pipeline.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Change test_fallback_pipeline_rag to use a complex query that triggers fallback
    content = content.replace(
        'res = run_sovara_task("What is the maintenance procedure?")',
        'res = run_sovara_task("Analyze complex PID with SOP", files=["demo/pump_pid.png", "datasets/synthetic_plant/documents/P101_Maintenance_SOP.md"])'
    )
    
    content = content.replace(
        'assert "search" in str(res["plan"])',
        'assert "multimodal" in str(res["plan"]) and "search" in str(res["plan"])'
    )
    
    with open('tests/test_fallback_pipeline.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix()
