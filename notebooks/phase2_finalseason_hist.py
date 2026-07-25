import json
import numpy as np
import pandas as pd

res = pd.read_json("data/processed/_phase2_finalseason_full.json")
counts, edges = np.histogram(res["delta"].clip(-3, 3), bins=30)
out = {"counts": counts.tolist(), "edges": [round(float(e), 3) for e in edges]}
with open("data/processed/_phase2_finalseason_hist.json", "w", encoding="utf-8") as f:
    json.dump(out, f)
print(out)
