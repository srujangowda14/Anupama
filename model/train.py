import argparse
import random
import torch
import numpy as np
import torch.nn as nn
import os
import json
import time
import torch.optim as optim
from torch.utils.data import DataLoader, random_split

from dataset import (
    Vocabulary, build_embedding_matrix,
    ClassificationDataset, Seq2SeqDataset,
    load_counsel_chat, load_mental_health_counseling,
    load_crisis_data, load_sentiment_data, load_distortion_data,
    tokenize, DISTORTION_LABELS,
)

from model.models import AnupamaModel


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

def main():
    args = get_args()
    set_seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Train] Device: {device}")
    os.makedirs(args.output_dir, exist_ok=True)

    # ── 1. Load raw data ──────────────────────────────────────────────────────
    print("[Data] Loading datasets...")
    gen_pairs = load_counsel_chat(args.counsel_chat)
    if args.mental_health:
        gen_pairs += load_mental_health_counseling(args.mental_health)

    crisis_samples = load_crisis_data(args.crisis)
    sentiment_samples = load_sentiment_data(args.sentiment)
    distortion_samples = load_distortion_data(args.distortion)

    print(f"  Seq2seq pairs: {len(gen_pairs):,}")
    print(f"  Crisis samples: {len(crisis_samples):,}")
    print(f"  Sentiment samples: {len(sentiment_samples):,}")
    print(f"  Distortion samples: {len(distortion_samples):,}")

    # ── 2. Build vocabulary ───────────────────────────────────────────────────
    print("[Vocab] Building...")
    vocab = Vocabulary(min_freq=2)
    all_texts = (
        [tokenize(p["src"]) for p in gen_pairs] +
        [tokenize(p["tgt"]) for p in gen_pairs] +
        [tokenize(s["text"]) for s in crisis_samples] +
        [tokenize(s["text"]) for s in sentiment_samples] +
        [tokenize(s["text"]) for s in distortion_samples]
    )
    vocab.fit(all_texts)
    vocab.build()
    vocab.save(os.path.join(args.output_dir, "vocab.pkl"))

    # ── 3. Build embedding matrix ─────────────────────────────────────────────
    print("[Embeddings] Building from Word2Vec...")
    embed_matrix = build_embedding_matrix(vocab, args.w2v_path)
    np.save(os.path.join(args.output_dir, "embed_matrix.npy"), embed_matrix)

    # ── 4. Build datasets ─────────────────────────────────────────────────────
    def split(ds, val_ratio=0.1):
        n_val = max(1, int(len(ds) * val_ratio))
        return random_split(ds, [len(ds) - n_val, n_val])

    crisis_ds = ClassificationDataset(crisis_samples, vocab)
    sent_ds = ClassificationDataset(sentiment_samples, vocab)
    dist_ds = ClassificationDataset(distortion_samples, vocab)
    gen_ds = Seq2SeqDataset(gen_pairs, vocab)

    crisis_train, crisis_val = split(crisis_ds)
    sent_train, sent_val = split(sent_ds)
    dist_train, dist_val = split(dist_ds)
    gen_train, gen_val = split(gen_ds)

    B = args.batch_size
    collate_cls = ClassificationDataset.collate
    collate_gen = Seq2SeqDataset.collate

    crisis_train_dl = DataLoader(crisis_train, B, shuffle=True, collate_fn=collate_cls)
    crisis_val_dl = DataLoader(crisis_val, B, collate_fn=collate_cls)
    sent_train_dl = DataLoader(sent_train, B, shuffle=True, collate_fn=collate_cls)
    sent_val_dl = DataLoader(sent_val, B, collate_fn=collate_cls)
    dist_train_dl = DataLoader(dist_train, B, shuffle=True, collate_fn=collate_cls)
    dist_val_dl = DataLoader(dist_val, B, collate_fn=collate_cls)
    gen_train_dl = DataLoader(gen_train, B, shuffle=True, collate_fn=collate_gen)
    gen_val_dl = DataLoader(gen_val, B, collate_fn=collate_gen)

    # ── 5. Build model ────────────────────────────────────────────────────────
    model = AnupamaModel(embed_matrix, len(vocab), pad_idx=vocab.pad_idx).to(device)
    model.summary()

    optimizer = optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=args.lr, weight_decay=1e-4
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs_cls + args.epochs_joint
    )
    loss_fn = MultiTaskLoss(len(vocab), vocab.pad_idx, device=device)

    history = []
    best_crisis_acc = 0.0

    # ── 6. Phase 1: Classifier-only training ─────────────────────────────────
    print(f"\n[Phase 1] Training classifiers for {args.epochs_cls} epochs...")
    for epoch in range(1, args.epochs_cls + 1):
        t0 = time.time()
        train_loss = train_classifiers_epoch(
            model, crisis_train_dl, sent_train_dl, dist_train_dl,
            optimizer, loss_fn, device, args.clip_grad
        )
        val_metrics = evaluate_classifiers(
            model, crisis_val_dl, sent_val_dl, dist_val_dl, device
        )
        scheduler.step()

        row = {"epoch": epoch, "phase": 1, "train_loss": train_loss, **val_metrics}
        history.append(row)

        print(f"  Ep {epoch:02d} | loss={train_loss:.4f} | "
              f"crisis={val_metrics['crisis_acc']:.3f} | "
              f"sent={val_metrics['sentiment_acc']:.3f} | "
              f"dist={val_metrics['distortion_acc']:.3f} | "
              f"{time.time()-t0:.1f}s")

        # Save best classifier checkpoint
        if val_metrics["crisis_acc"] > best_crisis_acc:
            best_crisis_acc = val_metrics["crisis_acc"]
            torch.save({
                "epoch": epoch,
                "model_state": model.state_dict(),
                "vocab_size": len(vocab),
            }, os.path.join(args.output_dir, "best_classifiers.pt"))

    # ── 7. Phase 2: Joint training ────────────────────────────────────────────
    print(f"\n[Phase 2] Joint training for {args.epochs_joint} epochs...")
    best_gen_loss = float("inf")

    for epoch in range(1, args.epochs_joint + 1):
        t0 = time.time()

        # Decrease teacher forcing over time (curriculum)
        tf_ratio = max(0.1, 0.9 - 0.04 * epoch)

        cls_loss = train_classifiers_epoch(
            model, crisis_train_dl, sent_train_dl, dist_train_dl,
            optimizer, loss_fn, device, args.clip_grad
        )
        gen_loss = train_generator_epoch(
            model, gen_train_dl, optimizer, loss_fn, device,
            args.clip_grad, teacher_forcing_ratio=tf_ratio
        )
        val_metrics = evaluate_classifiers(
            model, crisis_val_dl, sent_val_dl, dist_val_dl, device
        )
        scheduler.step()

        ppl = compute_perplexity(gen_loss / loss_fn.w_gen)

        row = {
            "epoch": args.epochs_cls + epoch,
            "phase": 2,
            "cls_loss": cls_loss,
            "gen_loss": gen_loss,
            "perplexity": ppl,
            **val_metrics,
        }
        history.append(row)

        print(f"  Ep {epoch:02d} | cls={cls_loss:.4f} | gen={gen_loss:.4f} | "
              f"ppl={ppl:.1f} | tf={tf_ratio:.2f} | "
              f"crisis={val_metrics['crisis_acc']:.3f} | {time.time()-t0:.1f}s")

        if gen_loss < best_gen_loss:
            best_gen_loss = gen_loss
            torch.save({
                "epoch": args.epochs_cls + epoch,
                "model_state": model.state_dict(),
                "vocab_size": len(vocab),
            }, os.path.join(args.output_dir, "best_model.pt"))

    # ── 8. Save final ─────────────────────────────────────────────────────────
    torch.save({
        "model_state": model.state_dict(),
        "vocab_size": len(vocab),
    }, os.path.join(args.output_dir, "final_model.pt"))

    with open(os.path.join(args.output_dir, "training_history.json"), "w") as f:
        json.dump(history, f, indent=2)

    print(f"\nTraining complete. Best model saved to {args.output_dir}/best_model.pt")


if __name__ == "__main__":
    main()


