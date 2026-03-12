import os
from pathlib import Path
from dataclasses import dataclass
import re
import torch
import numpy as np

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
    
    @classmethod
    def load(cls, checkpoint_dir: str, device_str: str = "auto") -> "Anupama":
        """Load model from a training checkpoint directory."""
        if device_str == "auto":
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            device = torch.device(device_str)

        ckpt_dir = Path(checkpoint_dir)

        vocab = Vocabulary.load(ckpt_dir / "vocab.pkl")
        embed_matrix = np.load(ckpt_dir / "embed_matrix.npy")

        model = AnupamaModel(embed_matrix, len(vocab), pad_idx=vocab.pad_idx)

        # Load best model or fall back to final
        ckpt_path = ckpt_dir / "best_model.pt"
        if not ckpt_path.exists():
            ckpt_path = ckpt_dir / "final_model.pt"

        ckpt = torch.load(ckpt_path, map_location=device)
        model.load_state_dict(ckpt["model_state"])
        print(f"[Engine] Loaded model from {ckpt_path}")

        return cls(model, vocab, device)

    # ── Tokenize & encode ──────────────────────────────────────────────────

    def _encode(self, text: str):
        tokens = tokenize(text)
        ids = self.vocab.encode(tokens)
        if not ids:
            ids = [self.vocab.unk_idx]
        id_tensor = torch.tensor([ids], dtype=torch.long, device=self.device)
        lengths = torch.tensor([len(ids)])
        return id_tensor, lengths
    
    @torch.no_grad()
    def classify(self, text: str) -> ClassifierOutputs:
        id_tensor, lengths = self._encode(text)

        # Crisis
        crisis_labels, crisis_probs = self.model.crisis.predict(id_tensor, lengths)
        c_label = CRISIS_LABELS[crisis_labels[0].item()]
        c_probs = crisis_probs[0].tolist()

        # Sentiment
        mood_labels, valence, sent_probs = self.model.sentiment.predict(id_tensor, lengths)
        mood = mood_labels[0].item()
        v = valence[0].item()

        # Distortion
        dist_labels, dist_probs = self.model.distortion.predict(id_tensor, lengths)
        d_label = DISTORTION_LABELS[dist_labels[0].item()]
        d_probs = dist_probs[0].tolist()

        return ClassifierOutputs(
            crisis_label=c_label,
            crisis_probs=c_probs,
            mood_score=mood,
            valence=round(v, 2),
            distortion=d_label,
            distortion_probs=d_probs,
        )
    
    # ── Build conditioning tokens from classifier outputs ──────────────────

    def _build_cond_tokens(self, cls_out: ClassifierOutputs, mode: str) -> list[str]:
        cond = []

        # Crisis token
        cond.append(f"<{cls_out.crisis_label.upper()}>")

        # Mood token
        cond.append(f"<MOOD_{cls_out.mood_score}>")

        # Mode token
        cond.append(self.MODE_COND_TOKENS.get(mode, "<MODE_SUPPORT>"))

        # Distortion signal
        if cls_out.distortion != "none":
            cond.append("<DISTORTION>")
        else:
            cond.append("<NO_DISTORTION>")

        return cond

    # ── Generate response ──────────────────────────────────────────────────

    @torch.no_grad()
    def _generate(self, text: str, cond_tokens: list[str]) -> str:
        id_tensor, lengths = self._encode(text)

        cond_ids = [
            self.vocab.word2idx.get(tok, self.vocab.unk_idx)
            for tok in cond_tokens
        ]

        token_ids = self.model.generator.generate(
            src_ids=id_tensor,
            src_lengths=lengths,
            cond_ids=cond_ids,
            sos_idx=self.vocab.sos_idx,
            eos_idx=self.vocab.eos_idx,
            max_len=self.max_gen_len,
            temperature=self.temperature,
            top_p=self.top_p,
        )

        tokens = self.vocab.decode(token_ids)
        # Strip special tokens that leaked through
        tokens = [t for t in tokens if not (t.startswith("<") and t.endswith(">"))]
        return tokens_to_sentence(tokens)




