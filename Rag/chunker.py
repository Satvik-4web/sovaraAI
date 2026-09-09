def chunk_text(text, chunk_size=800, overlap=120):
    if overlap >= chunk_size:
        raise ValueError(f"Overlap ({overlap}) cannot be greater than or equal to chunk_size ({chunk_size}).")
    
    if not text or not text.strip():
        return []
        
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        
        # Don't add empty strings or strings with only whitespace
        if chunk.strip():
            chunks.append(chunk)
            
        start += (chunk_size - overlap)
        
    return chunks
