# Disaggregated Evaluation & Fairness Audit

## Why

An extraction system used in underwriting must perform comparably across
property types, regions, and document characteristics. Errors concentrated
on one segment mean users in that segment are systematically under-served
-- and if that segment correlates with a protected or economically
disadvantaged group (e.g. smaller/rural properties, non-US filers), an
aggregate F1 of 0.803 can hide a real equity problem.

## Method

Micro P/R/F1 computed within each slice on the same 40-document gold set,
scoring `llm_structured` only -- regex/NER's near-zero accuracy overall
makes a slice breakdown for them uninformative (uniformly bad everywhere
isn't a bias finding, it's a floor). 90% confidence intervals from 1,000
bootstrap resamples per slice (`src/evaluate/bootstrap.py`). Region is
bucketed into US Census regions rather than raw state codes -- no single
state has more than 5 documents in this corpus, so a state-level bootstrap
would mostly measure sampling noise, not a real geographic effect.

**Read every table with n in mind.** A slice with 3-4 documents can show a
dramatic-looking F1 gap that's entirely explained by a wide confidence
interval -- not a repeated pattern in the underlying system.

## Results: property_type

| slice | n | P | R | F1 | 90% CI |
|---|---|---|---|---|---|
| commercial | 24 | 0.813 | 0.726 | 0.767 | 0.716-0.812 |
| industrial | 10 | 0.823 | 0.793 | 0.807 | 0.750-0.861 |
| other | 3 | 0.923 | 0.923 | 0.923 | 0.893-0.958 |
| residential | 3 | 0.958 | 0.885 | 0.920 | 0.850-0.967 |

## Results: region (US Census bucket)

| slice | n | P | R | F1 | 90% CI |
|---|---|---|---|---|---|
| Midwest | 7 | 0.830 | 0.750 | 0.788 | 0.733-0.851 |
| Northeast | 4 | 0.778 | 0.800 | 0.789 | 0.718-0.875 |
| non-US | 4 | 0.786 | 0.815 | 0.800 | 0.750-0.868 |
| unknown | 4 | 0.857 | 0.750 | 0.800 | 0.608-0.936 |
| South | 9 | 0.896 | 0.732 | 0.805 | 0.692-0.893 |
| West | 12 | 0.833 | 0.800 | 0.816 | 0.765-0.860 |

## Results: urbanicity

| slice | n | P | R | F1 | 90% CI |
|---|---|---|---|---|---|
| urban | 4 | 0.846 | 0.647 | 0.733 | 0.364-0.875 |
| suburban | 18 | 0.827 | 0.788 | 0.807 | 0.758-0.855 |
| unknown | 16 | 0.847 | 0.777 | 0.810 | 0.760-0.858 |
| rural | 2 | 0.842 | 0.842 | 0.842 | 0.800-0.889 |

## Results: document length

| slice | n | P | R | F1 | 90% CI |
|---|---|---|---|---|---|
| long (>100k chars) | 14 | 0.810 | 0.692 | 0.747 | 0.670-0.809 |
| short (<15k chars) | 12 | 0.831 | 0.793 | 0.812 | 0.765-0.857 |
| medium (15k-100k) | 14 | 0.866 | 0.836 | 0.851 | 0.802-0.896 |

## Findings

1. **Document length is the clearest, most mechanistically explainable
   gap in this audit.** Long documents (F1 0.747, CI 0.670-0.809) score
   meaningfully worse than medium-length ones (F1 0.851, CI 0.802-0.896)
   -- the intervals barely overlap at the edge, unlike every other slice
   in this report. This is not a mysterious model weakness: it's a direct
   consequence of the fixed-budget chunking built in Phase 4
   (`src/extract/llm_extractor.py`'s `chunk()` sends the first 8,000
   characters, the last 3,000, and keyword-triggered windows, capped at
   24,000 characters total). A 250,000-character document gets under 10%
   of itself seen by the model; an 8,000-character document gets nearly
   all of itself seen. **The fix differs from a "the model is worse at
   understanding long documents" story** -- it's an information-loss
   problem with a known lever: raise the character budget, or chunk
   adaptively based on document length rather than a fixed cap.

2. **`urban` looks like the worst-performing property slice (F1 0.733)
   but the evidence doesn't support that conclusion.** n=4, and the 90%
   CI (0.364-0.875) spans more than half the possible F1 range --
   essentially "could be anywhere from bad to good." This is the
   textbook case `00-BEFORE-YOU-START.md` §B4's check question warns
   about: check n and the interval before claiming a gap is real, not
   after. No claim is made here beyond "not enough data to say."

3. **`residential`/`other` property types show the highest F1 (0.920,
   0.923) with non-overlapping CIs against `commercial`'s (0.767)** --
   but both slices have n=3. Directionally interesting, not yet
   conclusive at this sample size. One plausible mechanism, not
   confirmed: `commercial` was the default category reached for whenever
   a mixed-use or ambiguous building didn't clearly fit another category
   during labeling (see `docs/annotation-guidelines.md`) -- if
   `commercial` absorbed more genuinely ambiguous documents, its lower
   accuracy could partly reflect harder documents rather than a model
   weakness specific to commercial leases. Not confirmed; flagged as a
   hypothesis for a larger future sample to test.

4. **Region shows no meaningful gap.** All six buckets land within
   0.788-0.816 F1, heavily overlapping CIs, including the small non-US
   sample (Switzerland, Canada -- n=4). Worth reporting explicitly as a
   negative result: this system does not show an evident geographic bias
   in this sample, which is itself informative, not just an absence of
   findings.

5. **Representation gap, not a performance gap:** the corpus has zero
   `retail`-tagged documents and only 3 `residential` (see slice
   distribution check performed before writing this report). A fairness
   audit can only measure disaggregated *performance* for groups that
   exist in the sample -- it cannot speak to how the system would
   perform on retail leases at all. This is a data-collection gap, not
   an extraction-quality gap, and the fix is collecting more retail
   leases in Phase 1, not touching the model.

## Recommendations

- Raise or make adaptive the LLM chunking budget (`chunk()`'s 24,000-char
  cap) for documents over ~100,000 characters, and re-run this audit --
  finding 1 is the one gap in this report with both statistical and
  mechanistic support.
- Oversample retail leases and expand the residential/other categories in
  a future EDGAR harvest to make findings 1 and 3 testable at a real
  sample size rather than n=3-4.
- Re-run this audit whenever the extraction pipeline changes (chunking,
  prompt, model version) -- a slice breakdown is only valid for the
  system version it was measured against.
- Report per-slice metrics alongside aggregate F1 in any future model
  change, not just the headline number -- this report is what makes that
  a five-minute re-run (`python -m src.evaluate.slice_eval`), not a
  research project each time.

## Limitations

- Single system audited in depth (`llm_structured`); regex/NER's uniform
  low accuracy makes their slice breakdowns uninformative rather than
  omitted out of convenience.
- n=40 total, with several slices at n=2-4 -- most findings in this
  report are appropriately hedged rather than conclusive because of this,
  by design.
- `scanned` slice has zero variation (all `False`) -- scanned documents
  were excluded during Phase 2 ingestion, so this dimension cannot be
  audited with the current corpus.
- Slice assignments (`property_type`, `region`, `urbanicity`) were made
  by the same labeler as the gold fields themselves (see
  `docs/label-changelog.md` on labeling provenance) -- a source of
  correlated error between the labels and the slices they're grouped by,
  not independently verified.
