import json
with open('datasets/benchmark/questions.json', 'r', encoding='utf-8') as f:
    qs = json.load(f)

for q in qs:
    if "expected" in q and "required_evidence" in q["expected"]:
        for ev in q["expected"]["required_evidence"]:
            if ev["source"] == "pump_manual.pdf":
                ev["source"] = "pump_manual.txt"
            elif ev["source"] == "maintenance_sop.pdf":
                ev["source"] = "maintenance_sop.txt"

with open('datasets/benchmark/questions.json', 'w', encoding='utf-8') as f:
    json.dump(qs, f, indent=2)
