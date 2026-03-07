import os
import re
import json
import pickle
import numpy as np
from collections import Counter
from typing import Optional
import csv

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

class ClassificationDataset(Dataset):
    """
    For crisis classifier, sentiment detector, and CBT distortion tagger.
    Each sample: (text_tokens, label_int)
    """

    def __init__(
        self,
        samples: list[dict],   # [{"text": str, "label": int}, ...]
        vocab: Vocabulary,
        max_len: int = 128,
    ):
        self.vocab = vocab
        self.max_len = max_len
        self.data = []

        for s in samples:
            tokens = tokenize(s["text"])[:max_len]
            ids = vocab.encode(tokens)
            self.data.append({
                "ids": torch.tensor(ids, dtype=torch.long),
                "label": torch.tensor(s["label"], dtype=torch.long),
                "length": len(ids),
            })

    def __len__(self): return len(self.data)
    def __getitem__(self, i): return self.data[i]

    @staticmethod
    def collate(batch):
        ids = pad_sequence(
            [b["ids"] for b in batch], batch_first=True, padding_value=0
        )
        labels = torch.stack([b["label"] for b in batch])
        lengths = torch.tensor([b["length"] for b in batch])
        return ids, labels, lengths
    
class Seq2SeqDataset(Dataset):
    """
    For the response generator.
    Each sample: (src_tokens, tgt_tokens, conditioning_tokens)
    conditioning_tokens are prepended to the decoder input.
    """

    def __init__(
        self,
        pairs: list[dict],   # [{"src": str, "tgt": str, "cond": [str, ...]}]
        vocab: Vocabulary,
        max_src: int = 150,
        max_tgt: int = 100,
    ):
        self.vocab = vocab
        self.max_src = max_src
        self.max_tgt = max_tgt
        self.data = []

        sos = vocab.sos_idx
        eos = vocab.eos_idx

        for p in pairs:
            src_tokens = tokenize(p["src"])[:max_src]
            tgt_tokens = tokenize(p["tgt"])[:max_tgt]

            src_ids = vocab.encode(src_tokens)
            tgt_ids = vocab.encode(tgt_tokens)

            # Conditioning token indices (e.g. <CRISIS>, <MOOD_2>, <MODE_SUPPORT>)
            cond_ids = [vocab.word2idx.get(c, vocab.unk_idx) for c in p.get("cond", [])]

            # Decoder input:  [SOS, cond..., tgt...]
            # Decoder target: [cond..., tgt..., EOS]
            dec_input = [sos] + cond_ids + tgt_ids
            dec_target = cond_ids + tgt_ids + [eos]

            self.data.append({
                "src": torch.tensor(src_ids, dtype=torch.long),
                "dec_input": torch.tensor(dec_input, dtype=torch.long),
                "dec_target": torch.tensor(dec_target, dtype=torch.long),
            })

    def __len__(self): return len(self.data)
    def __getitem__(self, i): return self.data[i]

    @staticmethod
    def collate(batch):
        src = pad_sequence([b["src"] for b in batch], batch_first=True, padding_value=0)
        dec_input = pad_sequence([b["dec_input"] for b in batch], batch_first=True, padding_value=0)
        dec_target = pad_sequence([b["dec_target"] for b in batch], batch_first=True, padding_value=0)
        return src, dec_input, dec_target
    
# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADERS (for the 4 public datasets)
# ─────────────────────────────────────────────────────────────────────────────

def load_counsel_chat(jsonl_path: str) -> list[dict]:
    """
    Load Counsel Chat dataset as seq2seq pairs.
    HuggingFace: nbertagnolli/counsel-chat
    Format: {"questionText": ..., "answerText": ...}
    """
    pairs = []
    with open(jsonl_path) as f:
        for line in f:
            obj = json.loads(line)
            q = obj.get("questionText", "").strip()
            a = obj.get("answerText", "").strip()
            if q and a and len(a) < 400:
                pairs.append({"src": q, "tgt": a, "cond": ["<SAFE>", "<MOOD_3>", "<MODE_SUPPORT>"]})
    return pairs


def load_empathetic_dialogues(csv_path: str) -> list[dict]:
    """
    EmpatheticDialogues (Facebook Research).
    https://github.com/facebookresearch/EmpatheticDialogues
    """
    pairs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        prev = None
        for row in reader:
            utt = row.get("utterance", "").replace("_comma_", ",").strip()
            if row.get("speaker_idx") == "0":
                prev = utt
            elif prev and utt:
                pairs.append({"src": prev, "tgt": utt, "cond": ["<SAFE>", "<MOOD_3>", "<MODE_SUPPORT>"]})
                prev = None
    return pairs

def load_mental_health_counseling(jsonl_path: str) -> list[dict]:
    """
    HuggingFace: Amod/mental_health_counseling_conversations
    Format: {"Context": ..., "Response": ...}
    """
    pairs = []
    with open(jsonl_path) as f:
        for line in f:
            obj = json.loads(line)
            ctx = obj.get("Context", "").strip()
            resp = obj.get("Response", "").strip()
            if ctx and resp:
                pairs.append({"src": ctx[:300], "tgt": resp[:300], "cond": ["<SAFE>", "<MOOD_2>", "<MODE_SUPPORT>"]})
    return pairs


def load_crisis_data(jsonl_path: str) -> list[dict]:
    """
    Expected format: {"text": str, "label": "safe"|"at_risk"|"crisis"}
    Sources: CLPsych 2015/2016 shared task, CSSRS-based datasets.
    """
    label_map = {"safe": 0, "at_risk": 1, "crisis": 2}
    samples = []
    with open(jsonl_path) as f:
        for line in f:
            obj = json.loads(line)
            label = label_map.get(obj.get("label", "safe"), 0)
            samples.append({"text": obj["text"], "label": label})
    return samples


def load_sentiment_data(jsonl_path: str) -> list[dict]:
    """
    Expected format: {"text": str, "score": 1-5}
    Sources: SemEval emotional tweets, DAIC-WOZ PHQ scores mapped to 1-5.
    """
    samples = []
    with open(jsonl_path) as f:
        for line in f:
            obj = json.loads(line)
            score = max(1, min(5, int(obj.get("score", 3))))
            samples.append({"text": obj["text"], "label": score - 1})  # 0-indexed
    return samples










