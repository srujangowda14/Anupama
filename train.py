import argparse
import random
import torch
import numpy as np
import torch.nn as nn


def get_args():
    p = argparse.ArgumentParser()
    p.add_argument("--w2v_path", required=True)
    p.add_argument("--counsel_chat", required=True)
    p.add_argument("--mental_health", default=None)
    p.add_argument("--crisis", required=True)
    p.add_argument("--sentiment", required=True)
    p.add_argument("--distortion", required=True)
    p.add_argument("--output_dir", default="./checkpoints")
    p.add_argument("--batch_size", type=int, default=32)
    p.add_argument("--epochs_cls", type=int, default=10, help="Classifier-only epochs")
    p.add_argument("--epochs_joint", type=int, default=20, help="Joint training epochs")
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--clip_grad", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

class MultiTaskLoss(nn.Module):
    """
    Weighted combination of:
      - Crisis cross-entropy (weighted for class imbalance)
      - Sentiment cross-entropy + MSE regression
      - Distortion cross-entropy
      - Seq2seq token-level cross-entropy
    """
    def __init__(self, vocab_size: int, pad_idx: int = 0, device="cpu"):
        super().__init__()

        # Crisis: up-weight at_risk and crisis
        crisis_weights = torch.tensor([1.0, 3.0, 5.0], device=device)
        self.crisis_ce = nn.CrossEntropyLoss(weight=crisis_weights)

        self.sentiment_ce = nn.CrossEntropyLoss()
        self.valence_mse = nn.MSELoss()

        self.distortion_ce = nn.CrossEntropyLoss()

        self.gen_ce = nn.CrossEntropyLoss(ignore_index=pad_idx)

        # Task weights (tune as needed)
        self.w_crisis = 2.0       # crisis safety is most critical
        self.w_sentiment = 1.0
        self.w_distortion = 1.0
        self.w_gen = 1.5
