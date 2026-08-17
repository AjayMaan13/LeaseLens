"""Bootstrap confidence intervals for micro-F1 within a slice.

Six lines of actual logic, but this is what separates "I noticed a
difference" from "I measured a difference with an interval" -- with n as
small as 3-7 documents in some slices here, that distinction is not
optional.
"""
import numpy as np
from src.evaluate.metrics import score, summarize


def bootstrap_f1(gold, pred, doc_ids, n=1000, seed=13):
    rng, ids, out = np.random.default_rng(seed), np.array(doc_ids), []
    for _ in range(n):
        sample = rng.choice(ids, size=len(ids), replace=True)
        g = {f"{d}#{i}": gold[d] for i, d in enumerate(sample)}
        p = {f"{d}#{i}": pred.get(d, {}) for i, d in enumerate(sample)}
        out.append(summarize(score(g, p))["micro"][2])
    lo, hi = np.percentile(out, [5, 95])
    return float(np.mean(out)), float(lo), float(hi)
