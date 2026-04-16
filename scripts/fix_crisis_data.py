# scripts/fix_crisis_data.py
import json, random

with open("data/crisis.jsonl") as f:
    rows = [json.loads(l) for l in f]

safe    = [r for r in rows if r["label"] == "safe"]
at_risk = [r for r in rows if r["label"] == "at_risk"]
crisis  = [r for r in rows if r["label"] == "crisis"]

print(f"Before — safe: {len(safe)}, at_risk: {len(at_risk)}, crisis: {len(crisis)}")

# Oversample minority classes to match safe count (cap at 2000)
target = min(len(safe), 2000)
safe    = random.sample(safe, target)
at_risk = at_risk * (target // max(len(at_risk), 1) + 1)
at_risk = at_risk[:target]
crisis  = crisis  * (target // max(len(crisis), 1) + 1)
crisis  = crisis[:target]

balanced = safe + at_risk + crisis
random.shuffle(balanced)

with open("data/crisis_balanced.jsonl", "w") as f:
    for r in balanced:
        f.write(json.dumps(r) + "\n")

print(f"After  — safe: {len(safe)}, at_risk: {len(at_risk)}, crisis: {len(crisis)}")
print(f"Total: {len(balanced)} rows saved to data/crisis_balanced.jsonl")