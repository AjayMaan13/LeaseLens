"""Score all three extraction systems against whatever gold labels exist
right now. Designed to be re-run as more documents get labeled -- results
will only get more reliable as the gold set grows past its current 15/42.
"""
import csv, json, pathlib
from src.schema import FIELDS
from src.evaluate.metrics import score, summarize
from src.evaluate.normalize import normalize_field, values_match

GOLD = pathlib.Path("data/gold")
PRED = pathlib.Path("data/predictions")
RESULTS = pathlib.Path("results"); RESULTS.mkdir(exist_ok=True)

SYSTEMS = ["regex_baseline", "ner_hybrid", "llm_structured"]


def load_gold():
    gold = {}
    for p in sorted(GOLD.glob("*.json")):
        rec = json.loads(p.read_text())
        gold[rec["doc_id"]] = rec["fields"]
    return gold


def load_predictions(name):
    return json.loads((PRED / f"{name}.json").read_text())


def dump_errors(gold, preds_by_system, out_path):
    """Every FP and FN, one row each, for manual error-taxonomy review."""
    rows = []
    for system, preds in preds_by_system.items():
        for doc_id, g_rec in gold.items():
            p_rec = preds.get(doc_id, {})
            for f in FIELDS:
                g = normalize_field(f, g_rec.get(f))
                p = normalize_field(f, p_rec.get(f))
                if g is None and p is None:
                    continue
                if g is not None and p is None:
                    rows.append({"system": system, "doc_id": doc_id, "field": f,
                                 "error_type": "FN_missed", "gold": g, "pred": p})
                elif g is None and p is not None:
                    rows.append({"system": system, "doc_id": doc_id, "field": f,
                                 "error_type": "FP_hallucinated", "gold": g, "pred": p})
                elif not values_match(f, g, p):
                    rows.append({"system": system, "doc_id": doc_id, "field": f,
                                 "error_type": "FP_FN_wrong_value", "gold": g, "pred": p})
    with open(out_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["system", "doc_id", "field", "error_type", "gold", "pred"])
        writer.writeheader()
        writer.writerows(rows)
    return rows


def format_results_md(gold, all_summaries):
    n_gold = len(gold)
    n_usable = len(sorted(pathlib.Path("data/interim").glob("edgar_*.txt"))) - len(
        json.loads((pathlib.Path("data/interim") / "excluded_doc_ids.json").read_text())["excluded"])
    lines = [
        "# Extraction Results",
        "",
        f"Scored against **{n_gold} labeled gold documents** (of {n_usable} usable EDGAR documents total).",
        "",
        "## Micro / Macro P/R/F1 by system",
        "",
        "| System | Micro P | Micro R | Micro F1 | Macro P | Macro R | Macro F1 |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, s in all_summaries.items():
        mi, ma = s["micro"], s["macro"]
        lines.append(f"| {name} | {mi[0]:.3f} | {mi[1]:.3f} | {mi[2]:.3f} "
                      f"| {ma[0]:.3f} | {ma[1]:.3f} | {ma[2]:.3f} |")

    lines += ["", "## Per-field F1 by system", "",
              "| Field | " + " | ".join(all_summaries.keys()) + " |",
              "|---|" + "---|" * len(all_summaries)]
    for f in FIELDS:
        row = [f]
        for name, s in all_summaries.items():
            pf = s["per_field"].get(f)
            support = s["support"].get(f, {})
            n = sum(support.values()) if support else 0
            row.append(f"{pf[2]:.3f} (n={n})" if pf else "n=0")
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines) + "\n"


def run():
    gold = load_gold()
    if not gold:
        print("No gold labels found in data/gold/. Label at least one document first.")
        return

    all_summaries, preds_by_system = {}, {}
    for name in SYSTEMS:
        preds = load_predictions(name)
        preds_by_system[name] = preds
        counts = score(gold, preds)
        all_summaries[name] = summarize(counts)

    md = format_results_md(gold, all_summaries)
    (RESULTS / "extraction_results.md").write_text(md)
    print(md)

    with open(RESULTS / "extraction_results.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["system", "micro_p", "micro_r", "micro_f1",
                                                  "macro_p", "macro_r", "macro_f1", "n_gold"])
        writer.writeheader()
        for name, s in all_summaries.items():
            mi, ma = s["micro"], s["macro"]
            writer.writerow({"system": name, "micro_p": round(mi[0], 3), "micro_r": round(mi[1], 3),
                              "micro_f1": round(mi[2], 3), "macro_p": round(ma[0], 3),
                              "macro_r": round(ma[1], 3), "macro_f1": round(ma[2], 3), "n_gold": len(gold)})

    rows = dump_errors(gold, preds_by_system, RESULTS / "errors.csv")
    print(f"\n{len(rows)} errors written to results/errors.csv for manual review")


if __name__ == "__main__":
    run()
