import requests
from Rag.search import search_knowledge

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
CHAT_MODEL = "qwen3:4b"

SYSTEM_PROMPT = """You are SOVARA, a private industrial AI assistant.
Answer only using the supplied evidence.
Do not invent facts.
If the supplied evidence is insufficient, explicitly state that the available knowledge base does not contain enough information.
For factual claims, cite the source and page when page information is available."""

def answer_with_rag(query):
    # 1. Retrieve knowledge
    try:
        chunks = search_knowledge(query, limit=5)
    except Exception as e:
        return {
            "success": False,
            "error": f"Search failed: {e}"
        }
        
    if not chunks:
        return {
            "success": False,
            "error": "No search results or knowledge base is empty."
        }
        
    # 2. Construct grounded context
    context_text = "EVIDENCE:\n\n"
    citations = []
    
    for idx, chunk in enumerate(chunks):
        source = chunk.get("source", "Unknown")
        page = chunk.get("page")
        
        page_str = f", page {page}" if page is not None else ""
        context_text += f"[Citation {idx + 1}] Source: {source}{page_str}\n"
        context_text += f"{chunk.get('text', '')}\n\n"
        
        citations.append({
            "source": source,
            "page": page,
            "chunk_id": chunk.get("chunk_id", "")
        })
        
    prompt = f"{context_text}\nQUESTION:\n{query}"
    
    # 3. Send to LLM
    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=300)
        response.raise_for_status()
        data = response.json()
        answer = data.get("message", {}).get("content", "")
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "LLM service (Ollama) is unavailable at http://localhost:11434. Is Ollama running?"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"LLM failure: {e}"
        }
        
    # 4. Return result
    return {
        "success": True,
        "answer": answer.strip(),
        "citations": citations
    }

if __name__ == "__main__":
    import sys
    import json
    
    query = "Why is the pump vibrating?"
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        
    print(f"Question: {query}\n")
    result = answer_with_rag(query)
    print(json.dumps(result, indent=2))
