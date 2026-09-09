import os
import hashlib
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

from Rag.loader import load_text_file
from Rag.chunker import chunk_text
from Rag.embed import get_embedding

COLLECTION_NAME = "sovara_knowledge"
QDRANT_PATH = os.path.join(os.path.dirname(__file__), "qdrant_data")

def get_stable_id(text: str) -> str:
    """Generate a stable 32-character hex string hash from text."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def init_qdrant_client():
    try:
        return QdrantClient(path=QDRANT_PATH)
    except Exception as e:
        raise RuntimeError(f"Qdrant unavailable or failed to initialize: {e}")

def ingest_document(file_path):
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}
        
    source = os.path.basename(file_path)
    
    # 1. Load Text
    try:
        text = load_text_file(file_path)
    except Exception as e:
        return {"success": False, "error": f"Failed to load document: {e}"}
        
    if not text or not text.strip():
        return {"success": False, "error": "Document is empty"}

    # 2. Chunk Text
    chunks = chunk_text(text)
    if not chunks:
        return {"success": False, "error": "No valid chunks generated"}
        
    # Document ID based on the file name/path
    document_id = get_stable_id(source)
    
    # 3. Get Embeddings and Prepare Points
    points = []
    
    try:
        # Determine vector size from the first chunk
        test_vector = get_embedding(chunks[0])
        vector_size = len(test_vector)
        
        client = init_qdrant_client()
        
        if not client.collection_exists(COLLECTION_NAME):
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            
        for chunk in chunks:
            chunk_id_str = get_stable_id(document_id + chunk)
            # Qdrant local accepts UUID string format or uint64. 
            # We can use a UUID generated from our hash
            import uuid
            chunk_uuid = str(uuid.UUID(hex=chunk_id_str))
            
            vector = get_embedding(chunk)
            
            payload = {
                "text": chunk,
                "source": source,
                "page": None,
                "chunk_id": chunk_uuid,
                "document_id": document_id
            }
            
            points.append(
                PointStruct(
                    id=chunk_uuid,
                    vector=vector,
                    payload=payload
                )
            )
            
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        
    except Exception as e:
        return {"success": False, "error": str(e)}

    return {
        "success": True,
        "source": source,
        "document_id": document_id,
        "chunks_added": len(points)
    }

if __name__ == "__main__":
    import sys
    
    # Simple runnable example
    file_to_ingest = os.path.join(os.path.dirname(__file__), "documents", "pump_manual.txt")
    
    print(f"Ingesting {file_to_ingest}...")
    result = ingest_document(file_to_ingest)
    print(result)