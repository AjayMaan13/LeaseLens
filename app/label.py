"""Minimal Streamlit annotation tool for the 60-document gold set.

Only lists real EDGAR documents that survived Phase 2's ingestion review
(data/interim/excluded_doc_ids.json) -- synthetic documents already have
ground truth from generation and are never manually labelled.

Run: streamlit run app/label.py
"""
import json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import streamlit as st
import streamlit.components.v1 as components
from src.schema import FIELDS

INTERIM, GOLD, RAW = pathlib.Path("data/interim"), pathlib.Path("data/gold"), pathlib.Path("data/raw/edgar")
GOLD.mkdir(parents=True, exist_ok=True)

excluded_path = INTERIM / "excluded_doc_ids.json"
excluded_ids = set()
if excluded_path.exists():
    excluded_ids = {e["doc_id"] for e in json.loads(excluded_path.read_text())["excluded"]}

docs = sorted(
    p for p in INTERIM.glob("edgar_*.txt")
    if p.stem not in excluded_ids
)

st.set_page_config(layout="wide")
st.title("LeaseLens — Gold Set Annotation")

if not docs:
    st.error("No documents found in data/interim/. Run Phase 2 (src/ingest/to_text.py) first.")
    st.stop()

labelled_count = sum(1 for p in docs if (GOLD / f"{p.stem}.json").exists())
st.caption(f"{labelled_count} / {len(docs)} labelled")

i = st.number_input("Doc index", 0, len(docs) - 1, 0)
doc = docs[i]
out = GOLD / f"{doc.stem}.json"
st.caption(f"**{doc.stem}** — {i + 1}/{len(docs)} — {'✅ labelled' if out.exists() else '⬜ unlabelled'}")

text = doc.read_text()
left, right = st.columns([3, 2])

with left:
    view = st.radio("View", ["Extracted text", "Original rendered document"], horizontal=True)

    if view == "Extracted text":
        q = st.text_input("Jump to keyword", "rent")
        if q:
            pos = text.lower().find(q.lower())
            if pos != -1:
                st.info(f"First match at char {pos}: …{text[max(0, pos-150):pos+150]}…")
            else:
                st.warning(f"'{q}' not found in this document")
        st.text_area("Document text", text, height=600)
    else:
        raw_path = RAW / f"{doc.stem}.html"
        if raw_path.exists():
            raw = raw_path.read_text(errors="ignore")
            # SEC wraps the real HTML in <DOCUMENT>/<TYPE>/<TEXT> tags -- pull out
            # just the inner document so the browser renders it cleanly, not the
            # SEC wrapper markup as literal text.
            m = re.search(r"<TEXT>(.*)</TEXT>", raw, re.S | re.I)
            html_body = m.group(1) if m else raw
            components.html(html_body, height=600, scrolling=True)
            st.caption(f"Rendering original: {raw_path}")
        else:
            st.warning(f"No raw HTML found at {raw_path} — falling back to extracted text")
            st.text_area("Document text", text, height=600)

with right:
    prev = json.loads(out.read_text()) if out.exists() else {"fields": {}, "slices": {}, "notes": ""}

    st.markdown("**Fields**")
    vals = {f: st.text_input(f, str(prev["fields"].get(f, "") or "")) for f in FIELDS}

    st.markdown("**Slices** (analysis only — model never sees these)")
    prev_slices = prev.get("slices", {})
    slices = {
        "property_type": st.selectbox(
            "slice: property_type",
            ["commercial", "retail", "industrial", "residential", "other"],
            index=["commercial", "retail", "industrial", "residential", "other"].index(
                prev_slices.get("property_type", "commercial")
            ) if prev_slices.get("property_type") in
                ["commercial", "retail", "industrial", "residential", "other"] else 0,
        ),
        "region": st.text_input("slice: region (e.g. US-CA, US-TX)", prev_slices.get("region", "")),
        "urbanicity": st.selectbox(
            "slice: urbanicity", ["urban", "suburban", "rural", "unknown"],
            index=["urban", "suburban", "rural", "unknown"].index(
                prev_slices.get("urbanicity", "unknown")
            ) if prev_slices.get("urbanicity") in ["urban", "suburban", "rural", "unknown"] else 3,
        ),
        "scanned": st.checkbox("scanned", value=prev_slices.get("scanned", False)),
        "doc_chars": len(text),
    }

    notes = st.text_area("notes (hard cases, uncertainty, amendment context, etc.)",
                          prev.get("notes", ""))

    if st.button("Save", type="primary"):
        out.write_text(json.dumps({
            "doc_id": doc.stem, "source": "edgar",
            "slices": slices, "notes": notes,
            "fields": {k: (v.strip() or None) for k, v in vals.items()},
        }, indent=2))
        st.success(f"saved {out}")
