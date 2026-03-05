import os
import re
import json
import pickle
import numpy as np
from collections import Counter
from typing import Optional

import torch
from torch.utils.data import Dataset
from torch.nn.utils.rnn import pad_sequence

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

EMBED_DIM = 300
PAD_TOKEN = "<PAD>"
UNK_TOKEN = "<UNK>"
SOS_TOKEN = "<SOS>"
EOS_TOKEN = "<EOS>"
SPECIAL_TOKENS = [PAD_TOKEN, UNK_TOKEN, SOS_TOKEN, EOS_TOKEN]

# Conditioning tokens prepended to decoder input to control response tone
COND_TOKENS = [
    "<CRISIS>", "<AT_RISK>", "<SAFE>",          # crisis level
    "<MOOD_1>", "<MOOD_2>", "<MOOD_3>", "<MOOD_4>", "<MOOD_5>",  # mood
    "<MODE_SUPPORT>", "<MODE_CBT>", "<MODE_INTAKE>",              # session mode
    "<DISTORTION>", "<NO_DISTORTION>",           # CBT signal
]

# CBT cognitive distortion labels
DISTORTION_LABELS = [
    "catastrophizing", "all_or_nothing", "mind_reading", "fortune_telling",
    "emotional_reasoning", "should_statements", "labeling", "personalization",
    "mental_filter", "discounting_positives", "none"
]

CRISIS_LABELS = ["safe", "at_risk", "crisis"]
SENTIMENT_LABELS = [1, 2, 3, 4, 5]  # mood scores

# TEXT PREPROCESSING

def clean_text(text: str) -> str:
    """Normalize raw text for tokenization."""
    text = text.lower().strip()
    text = re.sub(r"http\S+|www\.\S+", "<URL>", text)
    text = re.sub(r"@\w+", "<USER>", text)
    text = re.sub(r"[^\w\s\?\!\.\,\'\-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer."""
    text = clean_text(text)
    # Split on spaces but keep punctuation as tokens
    tokens = re.findall(r"\w+|[?\!.,]", text)
    return tokens

class Vocabulary:
    def __init__(self, min_freq: int = 2):
        self.min_freq = min_freq
        self.word2idx: dict[str, int] = {}
        self.idx2word: dict[int, str] = {}
        self._counter: Counter = Counter()
        self._built = False

        # Pre-insert specials
        for tok in SPECIAL_TOKENS + COND_TOKENS:
            self._add(tok)

    def _add(self, word: str):
        if word not in self.word2idx:
            idx = len(self.word2idx)
            self.word2idx[word] = idx
            self.idx2word[idx] = word

    def fit(self, corpus: list[list[str]]):
        """Count all tokens in a list-of-token-lists."""
        for tokens in corpus:
            self._counter.update(tokens)

    def build(self):
        """Add all tokens that meet min_freq threshold."""
        for word, count in self._counter.items():
            if count >= self.min_freq:
                self._add(word)
        self._built = True
        print(f"[Vocab] Built: {len(self)} tokens (min_freq={self.min_freq})")

    def encode(self, tokens: list[str]) -> list[int]:
        unk = self.word2idx[UNK_TOKEN]
        return [self.word2idx.get(t, unk) for t in tokens]

    def decode(self, indices: list[int]) -> list[str]:
        return [self.idx2word.get(i, UNK_TOKEN) for i in indices]

    @property
    def pad_idx(self): return self.word2idx[PAD_TOKEN]
    @property
    def unk_idx(self): return self.word2idx[UNK_TOKEN]
    @property
    def sos_idx(self): return self.word2idx[SOS_TOKEN]
    @property
    def eos_idx(self): return self.word2idx[EOS_TOKEN]

    def __len__(self): return len(self.word2idx)

    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: str) -> "Vocabulary":
        with open(path, "rb") as f:
            return pickle.load(f)
        

def build_embedding_matrix(
    vocab: Vocabulary,
    w2v_path: str,
    embed_dim: int = EMBED_DIM,
    binary: bool = True,
) -> np.ndarray:
    """
    Load Google News Word2Vec vectors and build an embedding matrix
    aligned to the vocabulary.

    w2v_path: path to GoogleNews-vectors-negative300.bin
              Download: https://code.google.com/archive/p/word2vec/
              (or via: kaggle datasets download -d leadbest/googlenewsvectorsnegative300)
    """
    try:
        from gensim.models import KeyedVectors
    except ImportError:
        raise ImportError("pip install gensim")

    print(f"[Embeddings] Loading Word2Vec from {w2v_path}")
    w2v = KeyedVectors.load_word2vec_format(w2v_path, binary=binary)
    print(f"[Embeddings] Loaded {len(w2v)} vectors")

    # Xavier uniform init for all tokens
    matrix = np.random.uniform(-0.1, 0.1, (len(vocab), embed_dim)).astype(np.float32)

    # Zero out PAD
    matrix[vocab.pad_idx] = np.zeros(embed_dim)

    hits = 0
    for word, idx in vocab.word2idx.items():
        if word in w2v:
            matrix[idx] = w2v[word]
            hits += 1

    print(f"[Embeddings] Coverage: {hits}/{len(vocab)} tokens ({100*hits/len(vocab):.1f}%)")
    return matrix


def build_embedding_matrix_from_gensim(
    vocab: Vocabulary,
    w2v_model,          # already-loaded KeyedVectors
    embed_dim: int = EMBED_DIM,
) -> np.ndarray:
    """Alternative: pass in an already-loaded gensim model."""
    matrix = np.random.uniform(-0.1, 0.1, (len(vocab), embed_dim)).astype(np.float32)
    matrix[vocab.pad_idx] = np.zeros(embed_dim)
    for word, idx in vocab.word2idx.items():
        if word in w2v_model:
            matrix[idx] = w2v_model[word]
    return matrix






