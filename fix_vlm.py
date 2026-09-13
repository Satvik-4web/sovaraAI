def fix():
    with open('multimodal/vision.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the post request for VLM and add keep_alive=0 to unload immediately
    content = content.replace(
        '"options": {"temperature": 0.1}',
        '"options": {"temperature": 0.1}, "keep_alive": 0'
    )
    
    with open('multimodal/vision.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix()
