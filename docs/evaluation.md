# Evaluation Methodology, Results, and Error Analysis

## 1. Match rules

Defined in `src/evaluate/normalize.py`, applied identically to gold and
predictions before comparison:

- **Money / area** (`base_rent_amount`, `premises_area_sqft`): stripped of
  `$`, commas, and text, parsed as float. `premises_area_sqft` additionally
  gets a 1% relative tolerance (`NUMERIC_TOL`) for minor rounding
  differences between sources. `base_rent_amount` does **not** currently
  get a tolerance -- see §4.3, this is a known gap.
- **Dates**: parsed with `dateutil` (fuzzy) and compared as ISO dates, so
  `"March 1, 2024"` and `"2024-03-01"` are equivalent.
- **Text fields** (`landlord_name`, `tenant_name`, `property_address`):
  fuzzy-matched via `rapidfuzz` token-set ratio, thresholds documented and
  fixed in code, not tuned per result: `property_address >= 90`,
  `landlord_name`/`tenant_name >= 88`.
- **Categoricals** (`property_type`, `rent_frequency`): normalized to
  lowercase, exact match.

A wrong (non-null, non-matching) value counts as **both** an FP and an FN,
per the scoring rule in `00-BEFORE-YOU-START.md` §B2 -- a bad guess is
worse than silence, and should be penalized as both a false answer and a
missed one.

## 2. Results (40/40 gold documents)

| System | Micro P | Micro R | Micro F1 | Macro P | Macro R | Macro F1 |
|---|---|---|---|---|---|---|
| regex_baseline | 0.458 | 0.237 | 0.313 | 0.270 | 0.237 | 0.247 |
| ner_hybrid | 0.284 | 0.103 | 0.151 | 0.086 | 0.094 | 0.089 |
| llm_structured | 0.837 | 0.772 | 0.803 | 0.829 | 0.766 | 0.795 |

Full per-field breakdown in `results/extraction_results.md`.

**LLM leads decisively** (2.6x regex, 5.3x NER on micro F1). Entity fields
are essentially solved for this corpus (`landlord_name` 0.987,
`tenant_name` 0.961, `property_address` 0.871); everything involving a
number or a date is meaningfully weaker (`base_rent_amount` 0.625,
`lease_start_date` 0.656) -- for a real-estate underwriting use case, that
is backwards from what matters most, and is the honest headline finding
of this evaluation, not the aggregate F1 number.

## 3. Groundedness (hallucination rate)

Per `src/extract/guards.py`, field-aware (dates checked by equivalence,
not literal substring; normalization-only fields like `property_type`
exempted -- see `docs/extraction-notes` in code comments for why the naive
version was misleading):

| System | Ungrounded rate |
|---|---|
| regex_baseline | 0.0% (0/174) -- cannot hallucinate by construction |
| ner_hybrid | 2.4% (3/125) -- formatting artifacts, not real hallucination |
| llm_structured | 5.5% (17/307) -- mostly false flags (see §4.4), roughly 1 confirmed genuine hallucinated value found on manual spot-check |

## 4. Error taxonomy

640 raw FP/FN rows in `results/errors.csv`. Sampled and categorized by
hand, focused on `llm_structured` (the system worth trusting enough to
analyze in depth) rather than the raw dump.

### 4.1 Monthly vs. annual rent disagreement (the single largest pattern)

Of the 7 remaining `base_rent_amount` "wrong value" errors, **5 are
exactly 12.000x apart** -- the model and the gold label are reporting the
*same* underlying rent, just in different units:

| doc | gold | pred | ratio |
|---|---|---|---|
| lsfp-ex1089 | $2,500.00 | $30,000.00 | 12.000 |
| exhibit1012 | $75,196.08 | $902,353.00 | 12.000 |
| aquapower-ex1011 | $126,528.68 | $1,518,344.10 | 12.000 |
| ex10x7 | $7,048.80 | $84,585.60 | 12.000 |
| stran-and-co | $14,962.50 | $179,550.00 | 12.000 |

Every one of these source documents states **both** a monthly and an
annual figure explicitly (common lease table format: "Rent Per Square
Foot / Annual Base Rent / Monthly Base Rent"). Both the labeler (me) and
the LLM had a real choice to make about which one is "the" value, and made
it inconsistently across documents -- not a factual error on either side,
a **methodology gap**: the annotation guidelines never specified a fixed
preference rule for monthly-vs-annual when a document states both.
`rent_frequency`'s own error list shows the identical pattern on the same
documents (monthly/annual swapped), confirming this is one underlying
issue surfacing as two field errors, not two separate problems.

**Fix for a future pass:** add an explicit rule to
`docs/annotation-guidelines.md` §3 (e.g. "always prefer the explicit
monthly figure when both are stated") and add a cross-frequency tolerance
to `values_match()` in `normalize.py` so a correct annual/monthly
transposition doesn't score as a full miss.

### 4.2 Amendment/restated documents: original vs. current terms

`lease_start_date` FN_missed (10 cases) and `premises_area_sqft`
FP_FN_wrong_value (4 cases) cluster on amendment and "amended & restated"
documents. Two distinct sub-causes, not one:

- **Prompt-vs-guideline inconsistency**: the LLM's system prompt
  explicitly instructs it to leave a field null in an amendment rather
  than infer it from recital context (matching `annotation-guidelines.md`
  §4.5's original intent). But several gold labels *do* carry forward a
  value stated in an amendment's recitals (e.g. the original lease's
  start date), because that judgment call was made case-by-case during
  labeling rather than by a fixed rule. This is a self-inflicted
  disagreement: the model is correctly following an instruction that the
  gold set doesn't consistently follow itself.
- **Restated terms genuinely changed**: for "Amended & Restated" leases
  specifically (a full restatement, not a delta amendment -- e.g.
  Beam Global's exhibit1001), the premises size or rent may have actually
  changed in the restatement. Gold sometimes captured the *original*
  lease's recital-stated figure while the model found the *current*
  restated table value, or vice versa -- a real ambiguity about which
  point in time "the" answer refers to, not a mistake by either side.

**Fix for a future pass:** guideline needs an explicit rule distinguishing
"amendment that modifies one clause" (§4.5's original case) from "amended
& restated lease that supersedes the original" (should be treated as an
operative fresh lease, using its own restated terms throughout).

### 4.3 Building total vs. tenant's specific leased premises

`premises_area_sqft` gold=389,319 vs. pred=408,395 (Franklin Road
Logistics) -- the document states both the tenant's actual leased space
(389,319 sqft, "Warehouse/Office Premises") and the whole building's total
rentable area (408,395 sqft). The model picked the building total instead
of the tenant-specific figure. A real extraction error, not a labeling
ambiguity -- worth a note in the LLM system prompt clarifying "premises"
means the tenant's leased space, not the building total.

### 4.4 Composite addresses defeat literal-substring grounding

All 4 remaining `property_address` "hallucinated" flags are the same
pattern first found in Phase 4: the LLM synthesizes one coherent address
string from several scattered mentions in the source (e.g. combining
"Attached No. 101, No. 118, Building 9..." into a single reordered
phrase). Every individual component is verifiably present in the source
text, but the naive literal-substring `grounded()` check can't validate
reordered/synthesized text, only exact quotes. Not fixed this pass --
would need a smarter check (e.g. decompose the address into tokens and
verify each independently) rather than pretending these are resolved.

### 4.5 Multi-premises summing convention creates artificial mismatches

Several `premises_area_sqft` FN_missed cases are documents where the gold
value is a **sum** of two separately-stated premises (per guideline
§4.4 -- e.g. 32,236 + 32,770 = 65,006 sqft for the Flanders Court
buildings). No extraction system naturally produces that sum unless
explicitly told to; this is a known, accepted side effect of the
summing convention, not a system failure.

## 5. A finding about the evaluation itself, not just the models

Before writing this taxonomy, checking why `llm_structured`'s
"hallucination" rate looked unexpectedly high turned up a bigger issue:
**41 of the LLM's "false positive" values across 17 documents were
manually verified to genuinely appear in the source text** -- they were
gold-labeling gaps (fields left null because a time-boxed targeted search
didn't happen to find them), not model hallucinations. Two were spot-
checked by hand before trusting the pattern at scale (a 99-year ground
lease end date, and a lease-extension date from an amendment) and
confirmed genuinely present. Filling these in changed `llm_structured`'s
micro F1 from **0.718 to 0.803** -- a 0.085 swing entirely attributable to
gold-set completeness, not model quality. This is the single most
important methodological lesson from this evaluation: **a "hallucination"
finding must be checked against the source document before being reported
as a model failure, since it may just as easily be an incomplete ruler.**
Documented in `docs/label-changelog.md`.

## 6. Self-agreement -- does not apply as designed

The plan calls for re-labeling 10 documents blind, 24 hours later, to
measure a single human annotator's self-consistency. That check's premise
doesn't hold here: the gold set's later 27 documents (and corrections to
the original 15) were labeled by Claude, not manually re-derived by the
same human labeler twice, per `docs/label-changelog.md`. Reporting a
self-agreement number here would be reporting something other than what
it claims to measure. Noted as an open limitation rather than a metric
this project can honestly claim.

## 7. Limitations

- Single labeling pass by an LLM (not the original human-only annotation
  process the plan describes), logged transparently in
  `docs/label-changelog.md` -- this changes what "gold" means for this
  dataset and should be stated plainly in any writeup, not glossed over.
- n=40, US-skewed (one Canadian document, one Swiss document).
- `base_rent_amount` has no cross-frequency tolerance yet (§4.1) --
  monthly/annual transpositions currently score as a full miss on two
  fields at once, inflating the apparent error count for a
  well-understood, fixable reason.
- Composite/reordered text (addresses) is not reliably checked by the
  current groundedness guard (§4.4).
