import requests

OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"

def get_embedding(text):
    payload = {
        "model": EMBED_MODEL,
        "prompt": text
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=300
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise ConnectionError("Embedding service (Ollama) is unavailable at http://localhost:11434. Is Ollama running?")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Embedding service error: {e}")

    return response.json()["embedding"]