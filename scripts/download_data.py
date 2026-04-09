# scripts/download_data.py
from datasets import load_dataset
import json, os

os.makedirs("data", exist_ok=True)

# ── Seq2Seq (response generator) ──────────────────────
print("Downloading Counsel Chat...")
ds = load_dataset("nbertagnolli/counsel-chat")
with open("data/counsel_chat.jsonl", "w") as f:
    for row in ds["train"]:
        q = (row.get("questionText") or "").strip()
        a = (row.get("answerText") or "").strip()
        if q and a:
            f.write(json.dumps({"src": q, "tgt": a}) + "\n")

print("Downloading Mental Health Conversations...")
ds2 = load_dataset("Amod/mental_health_counseling_conversations")
with open("data/mental_health.jsonl", "w") as f:
    for row in ds2["train"]:
        ctx  = row.get("Context", "").strip()
        resp = row.get("Response", "").strip()
        if ctx and resp:
            f.write(json.dumps({"Context": ctx, "Response": resp}) + "\n")

# ── Crisis classifier ──────────────────────────────────
print("Downloading crisis proxy data...")
ds3 = load_dataset("vibhorag101/suicide_prediction_dataset_phr")

with open("data/crisis.jsonl", "w") as f:
    for row in ds3["train"]:
        text = (row.get("text") or "").strip()
        label = (row.get("label") or "").strip().lower()

        if not text or not label:
            continue

        # Map dataset labels into your 3-class scheme
        if label == "suicide":
            mapped = "crisis"
        else:
            mapped = "safe"   # or "at_risk" if you want a less conservative mapping

        f.write(json.dumps({
            "text": text[:300],
            "label": mapped
        }) + "\n")

# ── Sentiment ──────────────────────────────────────────
print("Downloading sentiment data...")
ds4 = load_dataset("dair-ai/emotion")
score_map = {
    "sadness": 1, "fear": 2, "anger": 2,
    "surprise": 3, "joy": 5, "love": 4
}
with open("data/sentiment.jsonl", "w") as f:
    for row in ds4["train"]:
        label_name = ds4["train"].features["label"].int2str(row["label"])
        score = score_map.get(label_name, 3)
        f.write(json.dumps({"text": row["text"], "score": score}) + "\n")

# ── CBT Distortions ────────────────────────────────────
# Best free proxy — use the cogdistortions dataset if you can get it,
# otherwise this generates a small synthetic seed set
print("Building distortion seed data...")
examples = [
    ("I always mess everything up, every single time", "all_or_nothing"),
    ("I never do anything right", "all_or_nothing"),
    ("Everything is going to fall apart", "catastrophizing"),
    ("This is going to be a complete disaster", "catastrophizing"),
    ("I just know they think I'm an idiot", "mind_reading"),
    ("She's definitely angry at me", "mind_reading"),
    ("Something bad is going to happen today", "fortune_telling"),
    ("I feel terrible so things must be going wrong", "emotional_reasoning"),
    ("I should always be productive", "should_statements"),
    ("I must never make mistakes", "should_statements"),
    ("I'm just a failure as a person", "labeling"),
    ("I'm completely worthless", "labeling"),
    ("It's all my fault things went wrong", "personalization"),
    ("I only notice the bad things that happen", "mental_filter"),
    ("The one good thing doesn't count", "discounting_positives"),
    ("I had a decent day today", "none"),
    ("Things went okay this morning", "none"),
    ("I'm feeling a bit tired but fine", "none"),
]
with open("data/distortion.jsonl", "w") as f:
    for text, label in examples:
        f.write(json.dumps({"text": text, "distortion": label}) + "\n")

print(" All data saved to data/")