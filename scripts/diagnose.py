# scripts/diagnose.py
import sys
sys.path.insert(0, ".")

import torch
import pickle
import numpy as np
from itertools import cycle
from torch.utils.data import DataLoader

from model.dataset import (
    Vocabulary, ClassificationDataset,
    load_crisis_data, load_distortion_data, load_sentiment_data,
    tokenize
)

# Load vocab
with open("checkpoints/vocab.pkl", "rb") as f:
    vocab = pickle.load(f)

# Load data
crisis_samples    = load_crisis_data("data/crisis_balanced.jsonl")
dist_samples      = load_distortion_data("data/distortion.jsonl")
sentiment_samples = load_sentiment_data("data/sentiment.jsonl")

print(f"Crisis samples:     {len(crisis_samples)}")
print(f"Distortion samples: {len(dist_samples)}")
print(f"Sentiment samples:  {len(sentiment_samples)}")

# Check label distribution
from collections import Counter
print("\nCrisis label dist:",    Counter(s["label"] for s in crisis_samples))
print("Distortion label dist:", Counter(s["label"] for s in dist_samples))
print("Sentiment label dist:",  Counter(s["label"] for s in sentiment_samples))

# Check dataloader lengths
crisis_ds = ClassificationDataset(crisis_samples, vocab)
dist_ds   = ClassificationDataset(dist_samples, vocab)
sent_ds   = ClassificationDataset(sentiment_samples, vocab)

crisis_dl = DataLoader(crisis_ds, 32, collate_fn=ClassificationDataset.collate)
dist_dl   = DataLoader(dist_ds,   32, collate_fn=ClassificationDataset.collate)
sent_dl   = DataLoader(sent_ds,   32, collate_fn=ClassificationDataset.collate)

print(f"\nDataloader lengths:")
print(f"  crisis:     {len(crisis_dl)} batches")
print(f"  distortion: {len(dist_dl)} batches")
print(f"  sentiment:  {len(sent_dl)} batches")

# Check val split sizes
n_dist_val = max(1, int(len(dist_ds) * 0.1))
print(f"\nDistortion val split size: {n_dist_val} samples")
print(f"If all val samples are 'none', dist acc = 0.0 always")

# Test one forward pass
embed_matrix = np.load("checkpoints/embed_matrix.npy")
from model.models import AnupamaModel
model = AnupamaModel(embed_matrix, len(vocab), pad_idx=vocab.pad_idx)
model.load_state_dict(torch.load("checkpoints/best_model.pt", map_location="cpu")["model_state"])
model.eval()

# Try a known distortion
test = "I always fail at everything I do"
from model.dataset import tokenize, DISTORTION_LABELS
tokens = tokenize(test)
ids = torch.tensor([vocab.encode(tokens)])
lengths = torch.tensor([len(tokens)])

with torch.no_grad():
    logits = model.distortion(ids, lengths)
    probs = torch.softmax(logits, dim=-1)
    pred = torch.argmax(probs, dim=-1).item()

print(f"\nTest: '{test}'")
print(f"Predicted distortion: {DISTORTION_LABELS[pred]}")
print(f"Probabilities: {dict(zip(DISTORTION_LABELS, [round(p,3) for p in probs[0].tolist()]))}")