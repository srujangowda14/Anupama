import numpy as np

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