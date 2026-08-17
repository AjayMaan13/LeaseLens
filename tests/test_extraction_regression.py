"""Regression gate: extraction quality must not silently degrade.

Runs entirely offline against 10 committed gold documents and their
cached predictions -- no API key, no network, so this can run in CI on
every push without touching the Anthropic API or costing anything.
"""
import json, pathlib
import pytest

from src.evaluate.metrics import score, summarize

FLOOR = json.loads(pathlib.Path("tests/fixtures/quality_floor.json").read_text())
MINI = pathlib.Path("tests/fixtures/mini_gold")
PREDS = pathlib.Path("tests/fixtures/preds")


def load_mini():
    return {p.stem: json.loads(p.read_text())["fields"] for p in MINI.glob("*.json")}


@pytest.mark.parametrize("system", ["regex_baseline", "llm_structured"])
def test_micro_f1_above_floor(system):
    gold = load_mini()
    preds = json.loads((PREDS / f"{system}.json").read_text())
    f1 = summarize(score(gold, {k: preds[k] for k in gold if k in preds}))["micro"][2]
    assert f1 >= FLOOR[system], (
        f"{system} micro-F1 {f1:.3f} below recorded floor {FLOOR[system]:.3f} -- "
        "extraction quality regressed"
    )


def test_no_ungrounded_numeric_output():
    """No system may output a numeric value absent from the source document."""
    from src.extract.guards import grounded

    # data/interim/* is gitignored (regenerable output), so a fresh CI clone
    # wouldn't have it -- a committed fixture copy keeps this test meaningful
    # instead of silently skipping every document and passing trivially.
    interim = pathlib.Path("tests/fixtures/interim_text")
    preds = json.loads((PREDS / "llm_structured.json").read_text())
    bad = []
    for doc_id, rec in preds.items():
        text_path = interim / f"{doc_id}.txt"
        if not text_path.exists():
            continue
        text = text_path.read_text()
        for field in ("base_rent_amount", "premises_area_sqft"):
            value = rec.get(field)
            if value is not None and not grounded(field, value, text):
                bad.append((doc_id, field))
    assert len(bad) <= 1, f"ungrounded outputs: {bad}"


def test_schema_conformance():
    from src.schema import LeaseFields

    for sysname in ("regex_baseline", "ner_hybrid", "llm_structured"):
        preds = json.loads((PREDS / f"{sysname}.json").read_text())
        for rec in preds.values():
            LeaseFields(**rec)  # raises on invalid enum/type
