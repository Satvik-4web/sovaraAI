import os
from qdrant_client import QdrantClient
from Rag.embed import get_embedding

COLLECTION_NAME = "sovara_knowledge"
QDRANT_PATH = os.path.join(os.path.dirname(__file__), "qdrant_data")

def init_qdrant_client():
    try:
        return QdrantClient(path=QDRANT_PATH)
    except Exception as e:
        raise RuntimeError(f"Qdrant unavailable or failed to initialize: {e}")

def search_knowledge(query, limit=5):
    try:
        client = init_qdrant_client()
        
        if not client.collection_exists(COLLECTION_NAME):
            return []
            
        query_vector = get_embedding(query)
        
        # Use newer search method
        search_result = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=limit
        ).points
        
        results = []
        for scored_point in search_result:
            payload = scored_point.payload
            results.append({
                "text": payload.get("text", ""),
                "source": payload.get("source", ""),
                "page": payload.get("page", None),
                "chunk_id": payload.get("chunk_id", ""),
                "document_id": payload.get("document_id", ""),
                "score": scored_point.score
            })
            
        return results
        
    except Exception as e:
        raise RuntimeError(f"Search failed: {e}")

if __name__ == "__main__":
    import sys
    query = "Why is the pump vibrating?"
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        
    print(f"Searching for: '{query}'\n")
    try:
        results = search_knowledge(query, limit=3)
        for i, res in enumerate(results):
            print(f"Result {i+1} (Score: {res['score']:.4f})")
            print(f"Source: {res['source']} (Page: {res['page']})")
            print(f"Text snippet: {res['text'][:100]}...\n")
    except Exception as e:
        print(f"Error: {e}")
