import json

with open("datasets/benchmark/questions.json", "r") as f:
    questions = json.load(f)

id_counter = len(questions) + 1

def add_q(cat, q, files, expected_facts, req_ev, req_tools, exp_risk="LOW", hr=False, num=None, forbidden=None, out=None, paraphrases=None):
    global id_counter
    questions.append({
        "id": f"{cat.upper()}-{id_counter:03d}",
        "category": cat,
        "question": q,
        "paraphrases": paraphrases or [],
        "inputs": files,
        "expected": {
            "required_facts": expected_facts,
            "numerical_values": num or [],
            "forbidden_claims": forbidden or [],
            "required_evidence": req_ev,
            "required_tools": req_tools,
            "forbidden_tools": [],
            "required_outputs": out or [],
            "expected_risk": exp_risk,
            "human_review_expected": hr
        }
    })
    id_counter += 1

for i in range(15):
    add_q("rag", f"Placeholder RAG question {i}", [], ["placeholder"], [{"source": "Qdrant"}], ["rag"], "LOW", False)

for i in range(10):
    add_q("excel", f"Placeholder EXCEL question {i}", ["demo/pump_inspection.xlsx"], ["placeholder"], [{"source": "pump_inspection.xlsx"}], ["analyze_excel"], "LOW", False)

with open("datasets/benchmark/questions.json", "w") as f:
    json.dump(questions, f, indent=2)
print(f"Expanded to {len(questions)} rigorous benchmark questions.")
