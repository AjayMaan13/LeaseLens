# Model Card — LeaseLens Extraction Pipeline

## Intended use

Extracting 10 structured fields (parties, premises, dates, term, rent) from
commercial real-estate lease agreements and lease-related exhibits, to
support **preliminary** review and triage in real-estate underwriting or
portfolio-analysis workflows. Intended as a first-pass extraction aid that
surfaces candidate values for a human to verify, not as a source of truth
consumed directly by downstream financial decisions.

## Out-of-scope use

- **Not for underwriting decisions without human review.** A wrong
  `base_rent_amount` silently entering a financial model corrupts an
  investment decision; this system's own evaluation (`docs/evaluation.md`)
  found genuine hallucinated values, at a measured but non-zero rate.
- Not validated on residential leases at any real-world scale (only 3
  residential-tagged documents in the gold set) or on non-US/non-Canadian
  jurisdictions.
- Not a substitute for legal review — the system does not verify a
  document is enforceable, complete, or that extracted terms reflect the
  parties' current obligations (e.g. after further unlogged amendments).
- Not intended for equipment, aircraft, or personal-property leases — the
  schema and system prompt are built around real-estate premises fields
  (`property_address`, `premises_area_sqft`) and were not designed for
  other asset classes. Documents of this type were explicitly excluded
  from the training/eval corpus (`docs/ingest-review.md`).

## Training / eval data

- **40 real SEC EDGAR lease exhibits**, harvested via EDGAR's full-text
  search API across 3 filing quarters (2022 Q4, 2023 Q2, 2024 Q1) for
  property-type/company diversity, with a 2-document-per-company cap.
- **25 synthetic Ontario-style residential leases** (Faker-generated, free
  ground truth) — used for development/debugging only, never merged into
  reported metrics.
- No fine-tuning performed: the BERT NER component is used off-the-shelf
  (`dslim/bert-base-NER`); the LLM component is prompted, not fine-tuned.
  40 labelled documents is well below what token-classifier fine-tuning
  needs (hundreds to thousands of examples) to avoid overfitting with no
  held-out set left to detect it.
- **Labeling provenance** (stated plainly, not glossed over): the original
  15 gold documents were hand-labelled; the remaining 25, and corrections
  to systemic errors found in the first 15, were labelled by Claude at the
  project owner's explicit direction. Full reasoning and before/after
  values logged in `docs/label-changelog.md`. This means the gold set's
  independence from any LLM is weaker than a fully human-labelled set
  would be — a real limitation for how much this evaluation's numbers
  should be trusted as ground truth, not just a footnote.

## Chunking strategy

Documents in this corpus range from ~2,400 to ~250,000 characters —far
past what can be sent to any model in one call. Chunking differs by
extractor: the BERT NER pipeline is hard-capped at 512 tokens per call and
processes a whitespace-aware sliding window over the first 30,000
characters plus a guaranteed tail window (last ~6,000 characters); the LLM
extractor sends the first 8,000 characters, the last 3,000, and
keyword-triggered windows around mentions of "base rent," "square feet,"
"term of," capped at 24,000 characters total. This is a deliberate
engineering tradeoff, not a limitation glossed over: verified empirically
(`docs/bias-report.md` finding 1) that documents over 100,000 characters
score meaningfully worse (F1 0.747 vs 0.851 for medium-length documents),
directly attributable to this fixed character budget.

## Metrics

Micro/macro precision, recall, F1 per field, computed with field-aware
match rules (fuzzy text matching, numeric tolerance, date equivalence —
`src/evaluate/normalize.py`). A wrong (non-null, non-matching) value counts
as both a false positive and a false negative, not averaged away.
Groundedness (hallucination) rate reported separately per system, also
field-aware after an earlier naive version was found to mislabel
normalized/derived values as false hallucinations.

**Headline (40-document gold set): LLM structured extraction achieves
micro-F1 0.803** (P 0.837, R 0.772), vs. 0.313 for the regex baseline and
0.151 for BERT NER + rules. Full per-field breakdown: `results/extraction_results.md`.

## Disaggregated results

Full slice analysis with bootstrap confidence intervals across property
type, region (US Census bucket), urbanicity, and document length:
`docs/bias-report.md`. Headline finding: document length is the one gap
with both statistical support and a known, actionable mechanism (see
Chunking strategy above). No meaningful regional gap found. Zero
retail-tagged documents in the corpus — a representation gap the audit
cannot speak to, not a measured performance gap.

## Ethical considerations

- **Precision was prioritized over recall by design** for the fields that
  matter most financially: a silently wrong rent figure entering an
  underwriting model is worse than a blank field a human would catch and
  fill in (`00-BEFORE-YOU-START.md` §B2).
- The system can and does hallucinate on rare occasions (confirmed via
  manual verification, not just the automated groundedness check) — a
  plausible-looking invented value is a real, if infrequent, failure mode
  that any deployment must design around (e.g. routing low-confidence or
  unusual-magnitude extractions to human review).
- The gold set's own construction (see Labeling provenance above) means
  this evaluation should be treated as a strong first-pass measurement,
  not an independently, fully human-audited ground truth.

## Maintenance

- Re-run `python -m src.evaluate.run_eval` and `python -m src.evaluate.slice_eval`
  after any change to extraction logic, prompts, or the gold set — the CI
  regression gate (`tests/test_extraction_regression.py`) fails the build
  if `llm_structured` or `regex_baseline` micro-F1 drops below a recorded
  floor on a committed 10-document fixture set.
- Groundedness checks and match-rule thresholds are defined in code
  (`src/extract/guards.py`, `src/evaluate/normalize.py`), not tuned per
  result — any change to them should be logged with reasoning, the same
  standard applied to gold-label corrections in this project.
