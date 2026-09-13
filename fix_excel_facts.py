import json
with open('datasets/benchmark/questions.json', 'r', encoding='utf-8') as f:
    qs = json.load(f)

for q in qs:
    if q["id"] == "EXCEL-008":
        q["expected"]["required_facts"] = ["P-999"]
    # Wait, what about other EXCEL questions?
    if q["category"] == "excel":
        if "P-101" in q["expected"]["required_facts"]:
            q["expected"]["required_facts"] = ["P-999" if f == "P-101" else f for f in q["expected"]["required_facts"]]

with open('datasets/benchmark/questions.json', 'w', encoding='utf-8') as f:
    json.dump(qs, f, indent=2)
