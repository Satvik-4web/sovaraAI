import time
import requests
import json
import traceback

OLLAMA_HOST = "http://localhost:11434"
TIMEOUT_SEC = 60

results = []

def record(component, status, latency, error=""):
    results.append({
        "Component": component,
        "Status": status,
        "Latency": f"{latency:.2f}s" if latency is not None else "N/A",
        "Error": str(error) if error else "None"
    })
    print(f"[{component}] {status} in {latency:.2f}s" if latency is not None else f"[{component}] {status}")
    if error:
        print(f"  -> Error: {error}")

def test_ollama_tags():
    start = time.time()
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        r.raise_for_status()
        models = [m["name"] for m in r.json().get("models", [])]
        record("Ollama", "PASS", time.time() - start)
        return models
    except Exception as e:
        record("Ollama", "FAIL", time.time() - start, e)
        return []

def test_chat(model):
    start = time.time()
    try:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
            "stream": False
        }
        r = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=TIMEOUT_SEC)
        r.raise_for_status()
        record(f"{model.split(':')[0].capitalize()}", "PASS", time.time() - start)
    except Exception as e:
        record(f"{model.split(':')[0].capitalize()}", "FAIL", time.time() - start, e)

def test_embedding():
    start = time.time()
    try:
        payload = {
            "model": "nomic-embed-text",
            "prompt": "Test embedding"
        }
        r = requests.post(f"{OLLAMA_HOST}/api/embeddings", json=payload, timeout=TIMEOUT_SEC)
        r.raise_for_status()
        record("Embedding", "PASS", time.time() - start)
    except Exception as e:
        record("Embedding", "FAIL", time.time() - start, e)

def test_qdrant():
    start = time.time()
    try:
        from Rag.search import search_knowledge
        # Requires embedding under the hood, but tests retrieval part specifically
        # Let's time just retrieval
        from Rag.embed import get_embedding
        vec = get_embedding("Why is the pump vibrating?")
        
        t0 = time.time()
        from qdrant_client import QdrantClient
        client = QdrantClient(path="./Rag/qdrant_data")
        res = client.query_points(collection_name="sovara_knowledge", query=vec, limit=1).points
        record("Qdrant", "PASS", time.time() - t0)
    except Exception as e:
        record("Qdrant", "FAIL", time.time() - start, e)

def test_rag():
    start = time.time()
    try:
        from Rag.rag import answer_with_rag
        res = answer_with_rag("Why is the pump vibrating?")
        if not res.get("success"):
            record("RAG", "FAIL", time.time() - start, res.get("error"))
        else:
            record("RAG", "PASS", time.time() - start)
    except Exception as e:
        record("RAG", "FAIL", time.time() - start, e)

def test_planner():
    start = time.time()
    try:
        from agents.planner import generate_plan
        plan = generate_plan("Analyze this pump inspection", run_id="test")
        record("Planner", "PASS", time.time() - start)
    except Exception as e:
        record("Planner", "FAIL", time.time() - start, e)

def test_langgraph():
    start = time.time()
    try:
        from agents.graph import build_graph
        graph = build_graph()
        # Just run up to select_action to avoid full execution
        initial_state = {
            "run_id": "test", "user_query": "test", "task": "", "plan": None,
            "current_step": 0, "step_count": 0, "retrieved_context": [],
            "tool_results": [], "selected_model": "qwen3:4b",
            "execution_events": [], "final_answer": "", "verification_result": None,
            "risk_result": None, "human_review_required": False, "status": "RUNNING",
            "errors": []
        }
        res = graph.invoke(initial_state, config={"recursion_limit": 5})
        record("LangGraph", "PASS", time.time() - start)
    except Exception as e:
        record("LangGraph", "FAIL", time.time() - start, e)

def test_full_pipeline():
    start = time.time()
    try:
        from main import run_sovara_task
        res = run_sovara_task("Why is the pump vibrating?")
        if res.get("status") == "FAILED":
            record("Full Pipeline", "FAIL", time.time() - start, res.get("errors"))
        else:
            record("Full Pipeline", "PASS", time.time() - start)
    except Exception as e:
        record("Full Pipeline", "FAIL", time.time() - start, e)


print("\\n--- STARTING DIAGNOSTICS ---\\n")
models = test_ollama_tags()
if "qwen3:4b" in models or "qwen3:4b:latest" in models:
    test_chat("qwen3:4b")
else:
    record("Qwen3", "FAIL", None, "Model not found")

if "gemma3:4b" in models or "gemma3:4b:latest" in models:
    test_chat("gemma3:4b")
else:
    record("Gemma3", "FAIL", None, "Model not found")

test_embedding()
test_qdrant()
test_rag()
test_planner()
test_langgraph()
test_full_pipeline()

print("\\n--- DIAGNOSTIC RESULTS ---\\n")
print(f"{'Component':<15} | {'Status':<6} | {'Latency':<8} | {'Error'}")
print("-" * 50)
for r in results:
    err = r['Error']
    if len(err) > 40: err = err[:37] + "..."
    print(f"{r['Component']:<15} | {r['Status']:<6} | {r['Latency']:<8} | {err}")
print("\\n----------------------------\\n")
