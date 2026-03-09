import os
from pathlib import Path
from dataclasses import dataclass
import re
import torch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from dataset import (
    Vocabulary, tokenize, DISTORTION_LABELS, CRISIS_LABELS,
    PAD_TOKEN, SOS_TOKEN, EOS_TOKEN,
)
from models import AnupamaModel

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

class Anupama:
    CRISIS_PROTOCOL = (
        "I hear you, and I'm genuinely concerned about your safety right now. "
        "Please reach out to a crisis line — they're available 24/7:\n\n"
        "988 Suicide & Crisis Lifeline: Call or text 988 (US)\n"
        "Crisis Text Line: Text HOME to 741741\n"
        "Emergency: Call 911 if you're in immediate danger\n\n"
        "You don't have to go through this alone."
    )

    MODE_COND_TOKENS = {
        "support": "<MODE_SUPPORT>",
        "cbt":     "<MODE_CBT>",
        "intake":  "<MODE_INTAKE>",
    }

    def __init__(
        self,
        model: AnupamaModel,
        vocab: Vocabulary,
        device: torch.device,
        max_gen_len: int = 80,
        temperature: float = 0.85,
        top_p: float = 0.92,
    ):
        self.model = model.to(device)
        self.model.eval()
        self.vocab = vocab
        self.device = device
        self.max_gen_len = max_gen_len
        self.temperature = temperature
        self.top_p = top_p
