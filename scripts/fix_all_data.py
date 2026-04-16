# scripts/fix_all_data.py
import json, random
from collections import Counter

# ── Fix 1: Add at_risk examples to crisis data ────────────────────────────────
print("Fixing crisis data...")

at_risk_examples = [
    "I don't know how much longer I can keep going like this",
    "I feel completely hopeless about my future",
    "Nothing ever gets better no matter what I do",
    "I can't see a way out of this situation",
    "I feel like a burden to everyone around me",
    "I've been thinking that everyone would be better off without me",
    "I don't see the point in trying anymore",
    "I feel trapped and don't know what to do",
    "I've lost all hope that things will improve",
    "I feel like I'm disappearing and no one notices",
    "I'm exhausted and don't want to fight anymore",
    "Sometimes I wish I could just not wake up",
    "I feel like giving up on everything",
    "I can't go on pretending everything is okay",
    "I feel completely empty inside",
    "There's no reason to keep trying",
    "I don't want to be here anymore",
    "I feel like the world would be better without me",
    "I've been having dark thoughts I can't shake",
    "I feel like I'm at the end of my rope",
    "Every day feels pointless and I don't know why I bother",
    "I feel so alone even when people are around me",
    "I've been isolating myself because nothing feels worth it",
    "I feel numb and disconnected from everything",
    "I don't care what happens to me anymore",
]

with open("data/crisis_balanced.jsonl") as f:
    existing = [json.loads(l) for l in f]

safe_rows   = [r for r in existing if r["label"] == "safe"][:1500]
crisis_rows = [r for r in existing if r["label"] == "crisis"][:1500]

# Build at_risk rows — oversample to 1500
at_risk_rows = []
while len(at_risk_rows) < 1500:
    for text in at_risk_examples:
        at_risk_rows.append({"text": text, "label": "at_risk"})
        if len(at_risk_rows) >= 1500:
            break

balanced = safe_rows + at_risk_rows + crisis_rows
random.shuffle(balanced)

with open("data/crisis_fixed.jsonl", "w") as f:
    for r in balanced:
        f.write(json.dumps(r) + "\n")

dist = Counter(r["label"] for r in balanced)
print(f"  Crisis fixed: {dict(dist)} — total {len(balanced)}")


# ── Fix 2: Expand distortion data massively ───────────────────────────────────
print("Expanding distortion data...")

distortion_examples = [
    # all_or_nothing (label 1)
    ("I never do anything right", "all_or_nothing"),
    ("I always mess everything up", "all_or_nothing"),
    ("Everything I try fails", "all_or_nothing"),
    ("I completely ruined it", "all_or_nothing"),
    ("Nobody ever supports me", "all_or_nothing"),
    ("I totally failed at this", "all_or_nothing"),
    ("Things never work out for me", "all_or_nothing"),
    ("I always say the wrong thing", "all_or_nothing"),
    ("I never get anything done", "all_or_nothing"),
    ("Everything is either perfect or pointless", "all_or_nothing"),
    ("I either succeed completely or I'm a failure", "all_or_nothing"),
    ("There is no middle ground for me", "all_or_nothing"),

    # catastrophizing (label 0)
    ("This is going to be a total disaster", "catastrophizing"),
    ("Everything is falling apart around me", "catastrophizing"),
    ("This will ruin my entire life", "catastrophizing"),
    ("The worst is definitely going to happen", "catastrophizing"),
    ("I can't handle this, it's too much", "catastrophizing"),
    ("This small mistake will cost me everything", "catastrophizing"),
    ("I'm going to lose everything because of this", "catastrophizing"),
    ("This is the end for me", "catastrophizing"),
    ("Things are spiraling completely out of control", "catastrophizing"),
    ("One bad day means my whole life is falling apart", "catastrophizing"),
    ("This is absolutely terrible and won't get better", "catastrophizing"),

    # mind_reading (label 2)
    ("I know they all think I'm stupid", "mind_reading"),
    ("She must hate me after what I said", "mind_reading"),
    ("They're definitely judging me right now", "mind_reading"),
    ("He thinks I'm a complete failure", "mind_reading"),
    ("Everyone can tell how anxious I am", "mind_reading"),
    ("I know my boss thinks I'm incompetent", "mind_reading"),
    ("They didn't reply so they must be angry at me", "mind_reading"),
    ("I can tell she was disappointed in me", "mind_reading"),
    ("Everyone in that room was thinking badly of me", "mind_reading"),
    ("They obviously don't like me", "mind_reading"),

    # fortune_telling (label 3)
    ("I know this interview will go badly", "fortune_telling"),
    ("I'm definitely going to fail the exam", "fortune_telling"),
    ("Things are only going to get worse from here", "fortune_telling"),
    ("I'll never find anyone who loves me", "fortune_telling"),
    ("I know I'm going to embarrass myself", "fortune_telling"),
    ("This relationship is doomed to fail", "fortune_telling"),
    ("I just know something bad is coming", "fortune_telling"),
    ("There's no point trying, I'll fail anyway", "fortune_telling"),

    # emotional_reasoning (label 4)
    ("I feel like a failure so I must be one", "emotional_reasoning"),
    ("I feel scared so something bad must happen", "emotional_reasoning"),
    ("I feel worthless so I am worthless", "emotional_reasoning"),
    ("I feel guilty so I must have done something wrong", "emotional_reasoning"),
    ("I feel stupid so I must be stupid", "emotional_reasoning"),
    ("I feel like a bad person so I must be one", "emotional_reasoning"),
    ("My feelings are proof that things are bad", "emotional_reasoning"),

    # should_statements (label 5)
    ("I should always be productive", "should_statements"),
    ("I must never make mistakes", "should_statements"),
    ("I should be able to handle this on my own", "should_statements"),
    ("I ought to be stronger than this", "should_statements"),
    ("I should always put others first", "should_statements"),
    ("I must be perfect at everything I do", "should_statements"),
    ("I should never need help from anyone", "should_statements"),
    ("I must always stay in control", "should_statements"),

    # labeling (label 6)
    ("I'm just a loser", "labeling"),
    ("I'm a complete failure as a person", "labeling"),
    ("I'm so stupid", "labeling"),
    ("I'm worthless", "labeling"),
    ("I'm a terrible person", "labeling"),
    ("I'm such an idiot", "labeling"),
    ("I'm a burden to everyone", "labeling"),
    ("I'm broken and can't be fixed", "labeling"),
    ("I'm a disappointment", "labeling"),

    # personalization (label 7)
    ("It's all my fault things went wrong", "personalization"),
    ("I ruined everything for everyone", "personalization"),
    ("The argument happened because of me", "personalization"),
    ("If I had been better this wouldn't have happened", "personalization"),
    ("Everyone is upset and it's because of me", "personalization"),
    ("I caused all of this", "personalization"),

    # mental_filter (label 8)
    ("Despite everything going well I keep thinking about that one mistake", "mental_filter"),
    ("I can only focus on the bad parts", "mental_filter"),
    ("All I notice is what went wrong", "mental_filter"),
    ("Even though people said nice things I only remember the criticism", "mental_filter"),
    ("I got good feedback but one negative comment ruined it", "mental_filter"),
    ("I can't stop focusing on that one failure", "mental_filter"),

    # discounting_positives (label 9)
    ("Sure I did well but it doesn't really count", "discounting_positives"),
    ("Anyone could have done that it wasn't a big deal", "discounting_positives"),
    ("The good things don't matter", "discounting_positives"),
    ("I only succeeded because I got lucky", "discounting_positives"),
    ("That compliment doesn't mean anything", "discounting_positives"),
    ("It doesn't count because it was easy", "discounting_positives"),

    # none (label 10)
    ("I had a pretty good day today", "none"),
    ("Things went okay this morning", "none"),
    ("I'm feeling a bit tired but managing", "none"),
    ("I talked to my friend and felt better", "none"),
    ("Work was busy but I got through it", "none"),
    ("I went for a walk and it helped", "none"),
    ("I'm not sure how I feel right now", "none"),
    ("Today was just a normal day", "none"),
    ("I finished the project and feel okay about it", "none"),
    ("I had lunch with a colleague", "none"),
    ("I am feeling a little stressed but it is manageable", "none"),
    ("Things could be better but I am coping", "none"),
]

# Oversample to ~150 total (balanced across 11 classes)
expanded = []
per_class = {}
for text, label in distortion_examples:
    per_class.setdefault(label, []).append(text)

target_per_class = 15
for label, texts in per_class.items():
    while len([e for e in expanded if e["distortion"] == label]) < target_per_class:
        for text in texts:
            expanded.append({"text": text, "distortion": label})
            if len([e for e in expanded if e["distortion"] == label]) >= target_per_class:
                break

random.shuffle(expanded)
with open("data/distortion_fixed.jsonl", "w") as f:
    for r in expanded:
        f.write(json.dumps(r) + "\n")

dist2 = Counter(r["distortion"] for r in expanded)
print(f"  Distortion fixed: {len(expanded)} total examples")
print(f"  Per class: {dict(dist2)}")

print("\n✅ Done. Use crisis_fixed.jsonl and distortion_fixed.jsonl for retraining.")