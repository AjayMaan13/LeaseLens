"""Run all three extraction systems across the 42 usable EDGAR documents
(Phase 2's 7 excluded docs are skipped automatically). Runs on every
document regardless of labelling status -- extraction doesn't need gold
labels, only Phase 5's scoring does.
"""
import json, pathlib
from src.extract.baseline_regex import RegexExtractor
from src.extract.ner_extractor import NERExtractor
from src.extract.llm_extractor import LLMExtractor
from src.extract.guards import grounded
from src.schema import FIELDS

INTERIM = pathlib.Path("data/interim")
OUT = pathlib.Path("data/predictions"); OUT.mkdir(parents=True, exist_ok=True)

excluded_path = INTERIM / "excluded_doc_ids.json"
excluded_ids = set()
if excluded_path.exists():
    excluded_ids = {e["doc_id"] for e in json.loads(excluded_path.read_text())["excluded"]}

docs = sorted(p for p in INTERIM.glob("edgar_*.txt") if p.stem not in excluded_ids)


def run():
    summary = {}
    for ex in [RegexExtractor(), NERExtractor(), LLMExtractor()]:
        preds = {}
        ungrounded_count, grounded_checks = 0, 0
        for p in docs:
            text = p.read_text()
            fields = ex.extract(text).model_dump()
            preds[p.stem] = fields
            for f in FIELDS:
                v = fields.get(f)
                if v is None:
                    continue
                grounded_checks += 1
                if not grounded(f, v, text):
                    ungrounded_count += 1
            print(f"{ex.name} {p.stem}")
        (OUT / f"{ex.name}.json").write_text(json.dumps(preds, indent=2))
        rate = (ungrounded_count / grounded_checks) if grounded_checks else 0.0
        summary[ex.name] = {"documents": len(preds), "ungrounded_rate": round(rate, 4),
                             "ungrounded_count": ungrounded_count, "grounded_checks": grounded_checks}
        print(f"-- {ex.name}: {len(preds)} docs, ungrounded rate {rate:.1%} "
              f"({ungrounded_count}/{grounded_checks} non-null values)")
    (OUT / "run_summary.json").write_text(json.dumps(summary, indent=2))
    print("\n", json.dumps(summary, indent=2))


if __name__ == "__main__":
    run()
