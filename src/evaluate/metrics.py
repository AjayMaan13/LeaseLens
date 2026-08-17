"""The core P/R/F1 engine. Every number the repo reports flows through this
file, which is exactly why tests/test_metrics.py exists -- a bug here would
corrupt every downstream number with nothing to catch it against."""
from collections import defaultdict
from src.schema import FIELDS
from src.evaluate.normalize import normalize_field, values_match


def score(gold: dict, pred: dict) -> dict:
    """gold/pred: {doc_id: {field: value}} -> {field: {tp, fp, fn}}"""
    counts = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    for doc_id, g_rec in gold.items():
        p_rec = pred.get(doc_id, {})
        for f in FIELDS:
            g = normalize_field(f, g_rec.get(f))
            p = normalize_field(f, p_rec.get(f))
            if g is None and p is None:
                continue                                       # true negative, not scored
            elif g is not None and p is None:
                counts[f]["fn"] += 1
            elif g is None and p is not None:
                counts[f]["fp"] += 1                            # hallucination
            elif values_match(f, g, p):
                counts[f]["tp"] += 1
            else:
                counts[f]["fp"] += 1
                counts[f]["fn"] += 1                             # wrong answer: bad guess AND a miss
    return dict(counts)


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def summarize(counts):
    per_field = {f: prf(c["tp"], c["fp"], c["fn"]) for f, c in counts.items()}
    tp = sum(c["tp"] for c in counts.values())
    fp = sum(c["fp"] for c in counts.values())
    fn = sum(c["fn"] for c in counts.values())
    micro = prf(tp, fp, fn)
    n = max(len(per_field), 1)
    macro = tuple(sum(v[i] for v in per_field.values()) / n for i in range(3))
    return {"per_field": per_field, "micro": micro, "macro": macro,
            "support": {f: c for f, c in counts.items()}}
