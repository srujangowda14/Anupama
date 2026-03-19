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

    def classifier_loss(self, crisis_logits, crisis_labels,
                         sent_logits, sent_valence, sent_labels,
                         dist_logits, dist_labels):
        l_crisis = self.crisis_ce(crisis_logits, crisis_labels)

        # Sentiment: classification + regression
        l_sent_cls = self.sentiment_ce(sent_logits, sent_labels)
        l_sent_reg = self.valence_mse(sent_valence, sent_labels.float() + 1)  # 1-indexed
        l_sentiment = l_sent_cls + 0.3 * l_sent_reg

        l_dist = self.distortion_ce(dist_logits, dist_labels)

        total = (self.w_crisis * l_crisis
                 + self.w_sentiment * l_sentiment
                 + self.w_distortion * l_dist)
        return total, {"crisis": l_crisis.item(), "sentiment": l_sentiment.item(), "distortion": l_dist.item()}
    
    def generator_loss(self, gen_logits, targets):
        """
        gen_logits: (B, T-1, vocab_size)
        targets:    (B, T-1)
        """
        B, T, V = gen_logits.shape
        l_gen = self.gen_ce(gen_logits.reshape(B * T, V), targets.reshape(B * T))
        return self.w_gen * l_gen, {"gen": l_gen.item()}
    
def accuracy(logits, labels):
    preds = logits.argmax(dim=-1)
    return (preds == labels).float().mean().item()


def compute_perplexity(avg_nll_loss):
    return np.exp(avg_nll_loss)


def train_classifiers_epoch(
    model, crisis_loader, sent_loader, dist_loader,
    optimizer, loss_fn, device, clip
):
    model.train()
    total_loss = 0
    n = 0

    # Zip the three dataloaders — iterate together
    for (c_ids, c_labels, c_lens), (s_ids, s_labels, s_lens), (d_ids, d_labels, d_lens) in zip(
        crisis_loader, sent_loader, dist_loader
    ):
        c_ids, c_labels, c_lens = c_ids.to(device), c_labels.to(device), c_lens
        s_ids, s_labels, s_lens = s_ids.to(device), s_labels.to(device), s_lens
        d_ids, d_labels, d_lens = d_ids.to(device), d_labels.to(device), d_lens

        optimizer.zero_grad()

        crisis_logits = model.crisis(c_ids, c_lens)
        sent_logits, sent_valence = model.sentiment(s_ids, s_lens)
        dist_logits = model.distortion(d_ids, d_lens)

        loss, details = loss_fn.classifier_loss(
            crisis_logits, c_labels,
            sent_logits, sent_valence, s_labels,
            dist_logits, d_labels,
        )

        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), clip)
        optimizer.step()

        total_loss += loss.item()
        n += 1

    return total_loss / max(n, 1)

def train_generator_epoch(
    model, gen_loader, optimizer, loss_fn, device, clip,
    teacher_forcing_ratio=0.5
):
    model.train()
    total_loss = 0
    n = 0

    for src, dec_input, dec_target in gen_loader:
        src = src.to(device)
        dec_input = dec_input.to(device)
        dec_target = dec_target.to(device)

        src_lengths = (src != 0).sum(dim=1)

        optimizer.zero_grad()

        gen_logits = model.generator(
            src, src_lengths, dec_input,
            teacher_forcing_ratio=teacher_forcing_ratio
        )

        # Align: gen_logits is (B, T-1, V), targets are dec_target[:, 1:]
        targets = dec_target[:, 1:gen_logits.size(1) + 1]
        loss, details = loss_fn.generator_loss(gen_logits, targets)

        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), clip)
        optimizer.step()

        total_loss += loss.item()
        n += 1

    return total_loss / max(n, 1)

@torch.no_grad()
def evaluate_classifiers(model, crisis_loader, sent_loader, dist_loader, device):
    model.eval()
    crisis_acc = sent_acc = dist_acc = 0.0
    n = 0

    for (c_ids, c_labels, c_lens), (s_ids, s_labels, s_lens), (d_ids, d_labels, d_lens) in zip(
        crisis_loader, sent_loader, dist_loader
    ):
        c_ids, c_labels = c_ids.to(device), c_labels.to(device)
        s_ids, s_labels = s_ids.to(device), s_labels.to(device)
        d_ids, d_labels = d_ids.to(device), d_labels.to(device)

        crisis_acc += accuracy(model.crisis(c_ids, c_lens), c_labels)
        s_logits, _ = model.sentiment(s_ids, s_lens)
        sent_acc += accuracy(s_logits, s_labels)
        dist_acc += accuracy(model.distortion(d_ids, d_lens), d_labels)
        n += 1

    return {
        "crisis_acc": crisis_acc / max(n, 1),
        "sentiment_acc": sent_acc / max(n, 1),
        "distortion_acc": dist_acc / max(n, 1),
    }


