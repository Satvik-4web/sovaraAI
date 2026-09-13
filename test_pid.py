import os
from multimodal.adapter import MultimodalAdapter
import logging
logging.basicConfig(level=logging.DEBUG)

file_path = os.path.abspath("demo/pump_pid.png")
res = MultimodalAdapter.analyze_pid(file_path)
print("PID Results:")
print("Success:", res.get("success"))
print("Equipment:", res.get("equipment"))
print("Labels:", len(res.get("labels", [])))
print("Errors:", res.get("uncertainties"))
