"""LeaseLens dashboard -- four tabs, each mapping to a JD duty.

Runs entirely on cached results and predictions, no live API calls. This
is deliberate, not a shortcut: a publicly deployed demo with a live
Anthropic key behind it is a real cost/abuse risk (anyone can hammer the
"Extract" tab and run up your bill), and the plan's own guidance is that
cached demo mode is the safe call for a public deployment. If you want to
extract a *new* document, run `python -m src.extract.run_all` locally
with your own key -- this dashboard is for showing results, not for
running the pipeline live.

Run: streamlit run app/streamlit_app.py
"""
import json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from src.extract.guards import grounded
from src.schema import FIELDS

ROOT = pathlib.Path(__file__).resolve().parent.parent
INTERIM, PREDICTIONS, GOLD, RESULTS = (
    ROOT / "data/interim", ROOT / "data/predictions", ROOT / "data/gold", ROOT / "results")

st.set_page_config(page_title="LeaseLens", layout="wide")
st.title("LeaseLens — lease extraction & rent forecasting")
st.caption(
    "Evaluation-first project: three extraction systems benchmarked against a hand-labelled "
    "gold set, with disaggregated performance analysis and a CI regression gate on model quality. "
    "This dashboard shows cached results only -- no live API calls."
)

t1, t2, t3, t4 = st.tabs(["Extract", "Benchmark", "Fairness audit", "Rent forecast"])

# ---------------------------------------------------------------------------
with t1:
    st.caption(
        "Pick one of the 40 hand-labelled EDGAR lease exhibits and see what each system extracted, "
        "with a groundedness check flagging any value not found verbatim in the source document."
    )
    excluded_path = INTERIM / "excluded_doc_ids.json"
    excluded_ids = set()
    if excluded_path.exists():
        excluded_ids = {e["doc_id"] for e in json.loads(excluded_path.read_text())["excluded"]}
    doc_ids = sorted(p.stem for p in GOLD.glob("*.json"))

    if not doc_ids:
        st.warning("No gold-labelled documents found in data/gold/.")
    else:
        doc_id = st.selectbox("Document", doc_ids)
        gold_rec = json.loads((GOLD / f"{doc_id}.json").read_text())
        text_path = INTERIM / f"{doc_id}.txt"
        text = text_path.read_text() if text_path.exists() else ""

        cols = st.columns(4)
        systems = ["gold (hand-labelled)", "regex_baseline", "ner_hybrid", "llm_structured"]
        for col, system in zip(cols, systems):
            with col:
                st.markdown(f"**{system}**")
                if system == "gold (hand-labelled)":
                    fields = gold_rec["fields"]
                else:
                    pred_path = PREDICTIONS / f"{system}.json"
                    all_preds = json.loads(pred_path.read_text()) if pred_path.exists() else {}
                    fields = all_preds.get(doc_id, {})
                for f in FIELDS:
                    v = fields.get(f)
                    if v is None:
                        st.text(f"{f}: —")
                    elif system == "gold (hand-labelled)":
                        st.text(f"{f}: {v}")
                    else:
                        ok = grounded(f, v, text) if text else True
                        icon = "✅" if ok else "⚠️"
                        st.text(f"{f}: {v} {icon}")

        with st.expander("Document text"):
            st.text_area("", text, height=300, label_visibility="collapsed")

# ---------------------------------------------------------------------------
with t2:
    st.caption("Three extraction systems scored on the same hand-labelled gold set.")
    results_csv = RESULTS / "extraction_results.csv"
    if results_csv.exists():
        df = pd.read_csv(results_csv)
        st.dataframe(df, use_container_width=True)
        st.caption("Per-field F1 (llm_structured)")
        # Parse per-field table out of the markdown results since that's the
        # richer source; fall back gracefully if the file's shape changes.
        md_path = RESULTS / "extraction_results.md"
        if md_path.exists():
            md = md_path.read_text()
            if "## Per-field F1 by system" in md:
                table_md = md.split("## Per-field F1 by system")[1].strip()
                st.markdown(table_md)
    else:
        st.warning("results/extraction_results.csv not found -- run `python -m src.evaluate.run_eval`.")

# ---------------------------------------------------------------------------
with t3:
    st.caption(
        "Micro-F1 by property type, region, urbanicity, and document length, with 90% bootstrap "
        "confidence intervals. Slices with small n are shown but should not be read as conclusive "
        "-- see docs/bias-report.md for the full write-up and mechanism analysis."
    )
    slice_csv = RESULTS / "slice_results.csv"
    if slice_csv.exists():
        df = pd.read_csv(slice_csv)
        dim = st.selectbox("Dimension", sorted(df["dimension"].unique()))
        st.dataframe(df[df["dimension"] == dim].sort_values("f1"), use_container_width=True)
        st.caption("Full findings and mechanisms: docs/bias-report.md")
    else:
        st.warning("results/slice_results.csv not found -- run `python -m src.evaluate.slice_eval`.")

# ---------------------------------------------------------------------------
with t4:
    st.caption(
        "Rolling-origin cross-validation (never a shuffled split) on Toronto's StatCan CPI "
        "rented-accommodation index, benchmarked against naive and seasonal-naive baselines."
    )
    forecast_csv = RESULTS / "forecast_results.csv"
    if forecast_csv.exists():
        df = pd.read_csv(forecast_csv)
        st.dataframe(df, use_container_width=True)
        st.bar_chart(df.set_index("model")[["mae", "rmse"]])
    else:
        st.warning("results/forecast_results.csv not found -- run `python -m src.forecast.run_forecast`.")
