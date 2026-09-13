import json
with open('datasets/benchmark/questions.json', 'r', encoding='utf-8') as f:
    qs = json.load(f)

for q in qs:
    if "expected" in q and "required_evidence" in q["expected"]:
        for ev in q["expected"]["required_evidence"]:
            if ev["source"] == "Qdrant":
                print(f"{q['id']} expects Qdrant!")
