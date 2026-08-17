# LeaseLens — document extraction & rent forecasting for real estate

[![CI](https://github.com/AjayMaan13/LeaseLens/actions/workflows/ci.yml/badge.svg)](https://github.com/AjayMaan13/LeaseLens/actions/workflows/ci.yml)
[Live demo](#) · [Bias report](docs/bias-report.md) · [Evaluation methodology](docs/evaluation.md) · [Data provenance](docs/data-provenance.md)

<!-- TODO before submitting: replace the "#" above with the real Streamlit Community
     Cloud URL once deployed. Verify the CI badge is actually green on GitHub first. -->

Extracts 10 structured financial fields from commercial lease agreements and
forecasts neighbourhood rents. Built as an **evaluation-first** project:
three extraction systems benchmarked against a hand-labelled gold set, with
disaggregated performance analysis and a CI regression gate on model quality.

## Results

### Extraction — 40 real SEC EDGAR lease exhibits, hand-labelled

| System | Micro P | Micro R | Micro F1 | Macro F1 | Ungrounded outputs | Cost/doc |
|---|---|---|---|---|---|---|
| Regex baseline | 0.458 | 0.237 | 0.313 | 0.247 | 0.0% | $0 |
| BERT NER + rules | 0.284 | 0.103 | 0.151 | 0.089 | 2.4% | $0 |
| LLM structured | 0.837 | 0.772 | **0.803** | 0.795 | 5.5%* | <$0.10 |

\* Groundedness is field-aware (dates checked by equivalence, categorical
fields exempted from literal-substring matching — a naive version flagged
normalized values as false hallucinations). Manually spot-checked: most
remaining flags are legitimate multi-part address composites the checker
can't parse, not real hallucinations. Full breakdown: [docs/evaluation.md](docs/evaluation.md).

*Synthetic Ontario residential leases (n=25) generated separately with free
ground truth — used for development/debugging only, never merged into the
figures above. See [docs/evaluation.md](docs/evaluation.md) §5.*

### Performance by property type

| slice | n | F1 | 90% CI |
|---|---|---|---|
| commercial | 24 | 0.767 | 0.716–0.812 |
| industrial | 10 | 0.807 | 0.750–0.861 |
| other | 3 | 0.923 | 0.893–0.958 |
| residential | 3 | 0.920 | 0.850–0.967 |

**Largest gap with real support: document length, not property type.**
Long documents (>100k chars, n=14) score F1 0.747 vs. 0.851 for
medium-length ones (n=14) — the one gap in this audit with both
statistical support and a known mechanism (a fixed 24k-character chunking
budget sees a shrinking fraction of longer documents). Mechanism and
recommendation in [docs/bias-report.md](docs/bias-report.md).

### Rent forecasting — rolling-origin CV, h=12, 8 folds

Forecasts Toronto's StatCan CPI rented-accommodation **index** (not raw
dollar rent — a relative price index, StatCan base 2002=100), 666 months
of history (1971–2026).

| Model | MAE | RMSE | MAPE | vs. seasonal-naive |
|---|---|---|---|---|
| Seasonal naive (baseline) | 3.515 | 3.650 | 2.55% | — |
| Naive | 2.247 | 2.493 | 1.65% | +36.1% |
| SARIMA | **1.571** | **1.747** | **1.11%** | **+55.3%** |
| Prophet | — | — | — | not fit: cmdstan backend unavailable on this machine, a stretch goal per the build plan |

## How it works

```
scrape → text extraction + QC flags → hand annotation → 3 extractors →
tested metric harness → slice analysis → forecasting → CI gate
```

- **Scrape**: SEC EDGAR full-text search + BeautifulSoup (`src/scrape/`)
- **Extract**: regex baseline, BERT NER + rules, LLM structured output —
  one shared interface, one evaluation harness (`src/extract/`)
- **Evaluate**: tested P/R/F1 core, field-aware match rules, error taxonomy
  (`src/evaluate/`, `tests/test_metrics.py`)
- **Audit**: bootstrap-CI slice analysis across property type, region,
  urbanicity, document length (`src/evaluate/slice_eval.py`)
- **Forecast**: rolling-origin SARIMA/Prophet vs. baselines (`src/forecast/`)
- **Ship**: CI regression gate + Streamlit dashboard (`app/streamlit_app.py`)

## Data & provenance

Real sources (SEC EDGAR, StatCan, City of Toronto Open Data), access
policies honoured (rate limits, robots.txt, User-Agent), real vs. synthetic
data kept in separate directories and never mixed in headline results.
Full source-by-source log: [docs/data-provenance.md](docs/data-provenance.md).

## Evaluation methodology

Match rules per field (fuzzy text thresholds, numeric tolerance, date
equivalence), why `null` ≠ "not found", groundedness/hallucination
checking, and the full error taxonomy from manually reviewed FP/FN rows:
[docs/evaluation.md](docs/evaluation.md).

## Limitations

- 40 documents; several bias-audit slices have n<10 and wide confidence
  intervals — reported as directional, not conclusive, where that's true.
- **Labeling provenance**: the original 15 documents were hand-labelled;
  the remaining 25 and corrections to the first 15 were labelled by Claude
  at the project owner's direction, logged with reasoning in
  [docs/label-changelog.md](docs/label-changelog.md). This changes what
  "gold" means for this dataset and is stated here plainly rather than
  glossed over. The self-agreement re-label the build plan calls for
  (one human labelling twice, 24 hours apart) does not apply as designed
  for the same reason.
- US-skewed corpus (EDGAR over-represents large public filers); one
  Canadian and one Swiss document. No retail-tagged documents at all —
  a representation gap, not a performance gap the audit can speak to.
- No fine-tuning: 40 labels is insufficient for that. Reported NER results
  are off-the-shelf + rules, not a lease-specific model.
- LLM extraction results are cached per exact input (so re-running this
  repo reproduces the same reported numbers), but the underlying model
  call itself is not guaranteed deterministic — this model generation
  rejects an explicit `temperature=0` parameter as deprecated, so a fresh
  (uncached) run against the live API could plausibly return different
  values than reported here.
- Forecast is a StatCan CPI index, not dollar rent — see the note above.
- `base_rent_amount` has no cross-frequency tolerance yet: a correct
  monthly/annual transposition of the same real rent currently scores as
  a full miss on two fields at once (documented, not yet fixed —
  [docs/evaluation.md](docs/evaluation.md) §4.1).

## Reproduce

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m src.scrape.edgar              # harvest lease documents
python -m src.scrape.rent_data          # pull rent/geography series
python -m src.ingest.to_text            # clean text + QC flags
python -m src.ingest.synth_leases       # synthetic dev/debug corpus
streamlit run app/label.py              # hand-label the gold set

python -m src.extract.run_all           # run all 3 extraction systems
python -m src.evaluate.run_eval         # score against gold
python -m src.evaluate.slice_eval       # disaggregated bias audit
python -m src.forecast.run_forecast     # rolling-origin backtest

streamlit run app/streamlit_app.py      # results dashboard
pytest tests/ -v                        # full test suite + CI regression gate
```
