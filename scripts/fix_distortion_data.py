# scripts/fix_distortion_data.py
import json

examples = [
    # all_or_nothing
    ("I never succeed at anything", "all_or_nothing"),
    ("Everything I do turns out wrong", "all_or_nothing"),
    ("I always ruin things", "all_or_nothing"),
    ("Nobody ever listens to me", "all_or_nothing"),
    ("I completely failed again", "all_or_nothing"),
    # catastrophizing
    ("This is going to be a total disaster", "catastrophizing"),
    ("Everything is falling apart", "catastrophizing"),
    ("I can't handle this, it's too much", "catastrophizing"),
    ("This will ruin my entire life", "catastrophizing"),
    ("The worst is definitely going to happen", "catastrophizing"),
    # mind_reading
    ("I know they all think I'm stupid", "mind_reading"),
    ("She must hate me after that", "mind_reading"),
    ("They're judging me right now", "mind_reading"),
    ("He thinks I'm a failure", "mind_reading"),
    ("Everyone can see how anxious I am", "mind_reading"),
    # fortune_telling
    ("I know this interview will go badly", "fortune_telling"),
    ("I'm going to fail the exam", "fortune_telling"),
    ("Things are only going to get worse", "fortune_telling"),
    ("I'll never find anyone who loves me", "fortune_telling"),
    # emotional_reasoning
    ("I feel like a failure so I must be one", "emotional_reasoning"),
    ("I feel scared so something bad must happen", "emotional_reasoning"),
    ("I feel worthless so I am worthless", "emotional_reasoning"),
    # should_statements
    ("I should always be productive", "should_statements"),
    ("I must never make mistakes", "should_statements"),
    ("I should be able to handle this", "should_statements"),
    ("I ought to be stronger than this", "should_statements"),
    # labeling
    ("I'm just a loser", "labeling"),
    ("I'm a complete failure as a person", "labeling"),
    ("I'm so stupid", "labeling"),
    ("I'm worthless", "labeling"),
    # personalization
    ("It's all my fault things went wrong", "personalization"),
    ("I ruined everything for everyone", "personalization"),
    ("The argument happened because of me", "personalization"),
    # mental_filter
    ("Despite everything going well, I keep thinking about that one mistake", "mental_filter"),
    ("I can only focus on the bad parts", "mental_filter"),
    ("All I notice is what went wrong", "mental_filter"),
    # discounting_positives
    ("Sure I did well but it doesn't really count", "discounting_positives"),
    ("Anyone could have done that, it wasn't a big deal", "discounting_positives"),
    ("The good things don't matter", "discounting_positives"),
    # none
    ("I had a pretty good day today", "none"),
    ("Things went okay this morning", "none"),
    ("I'm feeling a bit tired but managing", "none"),
    ("I talked to my friend and felt better", "none"),
    ("Work was busy but I got through it", "none"),
    ("I went for a walk and it helped", "none"),
    ("I'm not sure how I feel right now", "none"),
    ("Today was just a normal day", "none"),
]

with open("data/distortion.jsonl", "w") as f:
    for text, label in examples:
        f.write(json.dumps({"text": text, "distortion": label}) + "\n")

print(f"Saved {len(examples)} distortion examples")