import os
from pathlib import Path
from dataclasses import dataclass
import re

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from dataset import (
    Vocabulary, tokenize, DISTORTION_LABELS, CRISIS_LABELS,
    PAD_TOKEN, SOS_TOKEN, EOS_TOKEN,
)

@dataclass
class ClassifierOutputs:
    crisis_label: str           # "safe" | "at_risk" | "crisis"
    crisis_probs: list[float]
    mood_score: int             # 1–5
    valence: float              # continuous 1–5
    distortion: str             # distortion label or "none"
    distortion_probs: list[float]

@dataclass
class EngineResponse:
    text: str
    classifiers: ClassifierOutputs
    is_crisis: bool
    conditioning_tokens: list[str]

def tokens_to_sentence(tokens: list[str]) -> str:
    """Detokenize: join tokens and clean up spacing around punctuation."""
    text = " ".join(tokens)
    text = re.sub(r" ([?.!,])", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    # Ensure sentence ends with punctuation
    if text and text[-1] not in ".?!":
        text += "."
    return text