"""Disaggregated evaluation: same gold set, same predictions, scored
separately within each slice so an aggregate F1 can't hide a system that
works great on one segment and badly on another.
"""
import json, pathlib
import pandas as pd
from src.evaluate.metrics import score, summarize
from src.evaluate.bootstrap import bootstrap_f1

# Raw state codes (US-CA, US-TX, ...) are too fragmented for this corpus --
# no state has more than 5 documents, most have 1-3. A state-level bootstrap
# would mostly measure sampling noise, not a real geographic effect, so
# region is bucketed into US Census regions instead (still small n, but
# defensible n instead of comparing single documents to each other).
US_CENSUS_REGION = {
    "US-CT": "Northeast", "US-ME": "Northeast", "US-MA": "Northeast", "US-NH": "Northeast",
    "US-RI": "Northeast", "US-VT": "Northeast", "US-NJ": "Northeast", "US-NY": "Northeast",
    "US-PA": "Northeast",
    "US-IL": "Midwest", "US-IN": "Midwest", "US-MI": "Midwest", "US-OH": "Midwest",
    "US-WI": "Midwest", "US-IA": "Midwest", "US-KS": "Midwest", "US-MN": "Midwest",
    "US-MO": "Midwest", "US-NE": "Midwest", "US-ND": "Midwest", "US-SD": "Midwest",
    "US-DE": "South", "US-FL": "South", "US-GA": "South", "US-MD": "South", "US-NC": "South",
    "US-SC": "South", "US-VA": "South", "US-DC": "South", "US-WV": "South", "US-AL": "South",
    "US-KY": "South", "US-MS": "South", "US-TN": "South", "US-AR": "South", "US-LA": "South",
    "US-OK": "South", "US-TX": "South",
    "US-AZ": "West", "US-CO": "West", "US-ID": "West", "US-MT": "West", "US-NV": "West",
    "US-NM": "West", "US-UT": "West", "US-WY": "West", "US-AK": "West", "US-CA": "West",
    "US-HI": "West", "US-OR": "West", "US-WA": "West",
}


def region_bucket(region: str) -> str:
    if not region:
        return "unknown"
    if region in US_CENSUS_REGION:
        return US_CENSUS_REGION[region]
    return "non-US" if not region.startswith("US-") else "unknown"


def doc_length_bucket(doc_chars: int) -> str:
    if doc_chars < 15000:
        return "short (<15k chars)"
    if doc_chars < 100000:
        return "medium (15k-100k)"
    return "long (>100k chars)"


def slice_report(gold_records, preds, dim="property_type"):
    groups = {}
    for doc_id, rec in gold_records.items():
        slices = rec["slices"]
        if dim == "region_bucket":
            value = region_bucket(slices.get("region", ""))
        elif dim == "doc_length_bucket":
            value = doc_length_bucket(slices.get("doc_chars", 0))
        else:
            value = slices.get(dim, "unknown") or "unknown"
        groups.setdefault(value, []).append(doc_id)

    rows = []
    for value, ids in groups.items():
        g = {d: gold_records[d]["fields"] for d in ids}
        p = {d: preds.get(d, {}) for d in ids}
        micro = summarize(score(g, p))["micro"]
        mean, lo, hi = bootstrap_f1(g, p, ids)
        rows.append({"dimension": dim, "slice": value, "n": len(ids),
                     "precision": round(micro[0], 3), "recall": round(micro[1], 3),
                     "f1": round(micro[2], 3), "ci_low": round(lo, 3), "ci_high": round(hi, 3)})
    return pd.DataFrame(rows).sort_values("f1")


def load_gold():
    gold = {}
    for p in sorted(pathlib.Path("data/gold").glob("*.json")):
        rec = json.loads(p.read_text())
        gold[rec["doc_id"]] = rec
    return gold


def load_predictions(name):
    return json.loads((pathlib.Path("data/predictions") / f"{name}.json").read_text())


if __name__ == "__main__":
    gold = load_gold()
    preds = load_predictions("llm_structured")
    for dim in ["property_type", "region_bucket", "urbanicity", "doc_length_bucket"]:
        df = slice_report(gold, preds, dim)
        print(f"\n=== {dim} ===")
        print(df.to_string(index=False))
