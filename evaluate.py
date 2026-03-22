import numpy as np
from collections import Counter
import math
import torch

from dataset import (
    tokenize, DISTORTION_LABELS, CRISIS_LABELS,
)

def classification_report(all_preds, all_labels, class_names):
    n = len(class_names)
    tp = [0] * n; fp = [0] * n; fn = [0] * n

    for p, l in zip(all_preds, all_labels):
        if p == l:
            tp[p] += 1
        else:
            fp[p] += 1
            fn[l] += 1

    report = {}
    for i, name in enumerate(class_names):
        prec = tp[i] / (tp[i] + fp[i] + 1e-9)
        rec = tp[i] / (tp[i] + fn[i] + 1e-9)
        f1 = 2 * prec * rec / (prec + rec + 1e-9)
        report[name] = {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3)}

    macro_f1 = np.mean([v["f1"] for v in report.values()])
    acc = sum(p == l for p, l in zip(all_preds, all_labels)) / len(all_preds)
    report["macro_f1"] = round(macro_f1, 3)
    report["accuracy"] = round(acc, 3)
    return report

def ngrams(tokens, n):
    return Counter(tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1))


def bleu_score(references, hypotheses, max_n=4):
    """Corpus BLEU-1 through BLEU-n."""
    scores = []
    for n in range(1, max_n + 1):
        clipped = 0
        total_hyp = 0
        for ref, hyp in zip(references, hypotheses):
            ref_ng = ngrams(ref, n)
            hyp_ng = ngrams(hyp, n)
            clipped += sum(min(c, ref_ng[gram]) for gram, c in hyp_ng.items())
            total_hyp += max(len(hyp) - n + 1, 0)
        precision = clipped / (total_hyp + 1e-9)
        scores.append(precision)

    # Brevity penalty
    ref_len = sum(len(r) for r in references)
    hyp_len = sum(len(h) for h in hypotheses)
    bp = 1 if hyp_len >= ref_len else math.exp(1 - ref_len / (hyp_len + 1e-9))

    bleu = bp * math.exp(sum(math.log(s + 1e-9) for s in scores) / max_n)
    return {f"bleu_{n}": round(scores[n-1], 4) for n in range(1, max_n + 1)} | {"bleu": round(bleu, 4)}


def distinct_n(all_tokens, n):
    """Distinct-n: ratio of unique n-grams (measures diversity)."""
    all_ng = []
    for tokens in all_tokens:
        all_ng.extend(tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1))
    if not all_ng:
        return 0.0
    return round(len(set(all_ng)) / len(all_ng), 4)

@torch.no_grad()
def evaluate_crisis(engine, test_samples):
    preds, labels = [], []
    for s in test_samples:
        cls = engine.classify(s["text"])
        preds.append(CRISIS_LABELS.index(cls.crisis_label))
        labels.append(s["label"])
    return classification_report(preds, labels, CRISIS_LABELS)


@torch.no_grad()
def evaluate_sentiment(engine, test_samples):
    preds, labels, valences = [], [], []
    for s in test_samples:
        cls = engine.classify(s["text"])
        preds.append(cls.mood_score)
        labels.append(s["label"] + 1)  # back to 1-indexed
        valences.append(cls.valence)

    acc = sum(p == l for p, l in zip(preds, labels)) / len(preds)
    mae = np.mean(np.abs(np.array(preds) - np.array(labels)))

    # Pearson correlation between predicted valence and true label
    corr = np.corrcoef(valences, labels)[0, 1]

    return {
        "accuracy": round(acc, 3),
        "mae": round(mae, 3),
        "pearson_r": round(corr, 3),
    }


@torch.no_grad()
def evaluate_distortion(engine, test_samples):
    preds, labels = [], []
    for s in test_samples:
        cls = engine.classify(s["text"])
        preds.append(DISTORTION_LABELS.index(cls.distortion))
        labels.append(s["label"])
    return classification_report(preds, labels, DISTORTION_LABELS)


@torch.no_grad()
def evaluate_generator(engine, test_pairs, n_samples=200, mode="support"):
    references, hypotheses = [], []

    for pair in test_pairs[:n_samples]:
        result = engine.respond(pair["src"], mode=mode)
        hyp_tokens = tokenize(result.text)
        ref_tokens = tokenize(pair["tgt"])
        hypotheses.append(hyp_tokens)
        references.append(ref_tokens)

    bleu = bleu_score(references, hypotheses)
    dist1 = distinct_n(hypotheses, 1)
    dist2 = distinct_n(hypotheses, 2)
    avg_len = np.mean([len(h) for h in hypotheses])

    return {
        **bleu,
        "distinct_1": dist1,
        "distinct_2": dist2,
        "avg_response_length": round(avg_len, 1),
    }



