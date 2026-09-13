def patch_planner():
    with open('agents/planner.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    old_except = '''    except Exception as e:
        return {"goal": "fallback", "steps": [{"id": 1, "action": "generic_response", "required_capability": "rag"}]}'''
    new_except = '''    except Exception as e:
        print(f"PLANNER ERROR: {e}")
        return {"goal": "fallback", "steps": [{"id": 1, "action": "generic_response", "required_capability": "rag"}]}'''
    
    content = content.replace(old_except, new_except)
    with open('agents/planner.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    patch_planner()
