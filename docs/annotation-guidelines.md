# Annotation Guidelines v1.0
Author: Ajaypartap Singh Maan · Date: 2026-08-15

## 1. Purpose
Define how each of the 10 schema fields (`src/schema.py`) is labelled so
that labels are reproducible across documents and across sessions. Written
and committed **before** any document is labelled — the git history of
"guidelines first" is the proof of process.

## 2. Golden rule
`null` means **THE VALUE IS NOT STATED IN THE DOCUMENT.**
`null` NEVER means "I could not find it." If unsure, search again (try
`rent`, `term`, `premises`, `landlord`, `tenant`, `commencement`); if still
unsure after a real search, label your best reading and add
`"uncertain": true` in that field's context inside `notes`. A `null` you
didn't earn corrupts recall — it moves a true-positive opportunity into
"correctly stayed quiet" and makes the model look better than it is.

## 3. Field definitions

### landlord_name (str)
The party named as Landlord/Lessor at signing. Use the legal entity name as
written (e.g. "CRP/AI Freeport Parkway Owner, L.P."), not an abbreviation.

### tenant_name (str)
The party named as Tenant/Lessee at signing. See §4.1 for multiple tenants.

### property_address (str)
The street address of the leased premises, as stated. If only a building
name or legal description is given with no street address, record what's
given and note the limitation.

### property_type (enum: residential | commercial | retail | industrial | other)
Inferred from stated use of the premises, not from the tenant's industry.
An office lease for a biotech company is `commercial`, not `industrial`.

### premises_area_sqft (float)
Total leased square footage as stated. If given as a range or multiple
suites, sum them and note the breakdown.

### lease_start_date (str, ISO YYYY-MM-DD)
The commencement date of the initial term. See §4.6 if execution date and
commencement date differ (they often do).

### lease_end_date (str, ISO YYYY-MM-DD)
End of the initial term only — see §4.3, never includes renewal options.

### term_length_months (int)
Initial term only, in months. If stated in years, convert (5 years = 60).

### base_rent_amount (float)
The recurring base/minimum rent payable by the tenant for the premises,
**excluding** operating costs, TMI/CAM, taxes, insurance, utilities, and
percentage rent.
- Escalating schedule (e.g. $4,000 yrs 1–2, $4,400 yrs 3–5) → record the
  **year-1 amount**. Note the escalation schedule in `notes`.
- Stated as annual $/sq ft (e.g. "$32.00 PSF annual") → record the PSF
  figure as-is, set `rent_frequency = annual`, and put the derived total
  monthly rent in `notes`. **Never silently convert — the recorded value
  must match what the document actually says.**
- Redacted (e.g. `[***]`) → `null` + note `"redacted"`. Genuinely not
  recoverable; this is a legitimate null, not a miss.

### rent_frequency (enum: monthly | annual | weekly | other)
Matches how `base_rent_amount` is actually stated in the document (see
above) — these two fields must agree.

## 4. Hard cases and rulings

**4.1 Multiple tenants named** → label the tenant of record at signing
(the primary named party), not co-tenants or later assignees.

**4.2 PSF (per-square-foot) rent** → see `base_rent_amount` above. This is
the single most common source of inconsistent labelling — always double
check `rent_frequency` matches what was recorded.

**4.3 Renewal options** (e.g. "5-year term with two 5-year renewal
options") → label the **initial term only**. `term_length_months = 60`,
not 180. Note the renewal options exist.

**4.4 Multiple premises in one lease** → label the primary premises (the
first described, or the largest by square footage). Note the others in
`notes` rather than trying to encode multiple addresses in one field.

**4.5 Amendments to an earlier lease** (confirmed present in our corpus —
see `docs/ingest-review.md`) → label **only the values the amendment
itself states**. An amendment that only changes the notice address will
leave `base_rent_amount`, `lease_start_date`, etc. as `null` — that is
correct, not a missed field, because the amendment document genuinely
doesn't restate them. Note in `notes` that the source is an amendment and
what it actually amends.

**4.6 Execution date vs. commencement date differ** → `lease_start_date`
is the commencement date (when the tenancy actually begins), not the date
the parties signed the document, when the two are distinguished. If the
document only gives one date, use it and note which kind it is.

**4.7 "Lessor/Lessee" vs "Landlord/Tenant" terminology** (confirmed present
in our corpus) → same fields, different words. Don't let terminology
variation cause a missed field.

**4.8 Wrong document type** (equipment leases, guaranties referencing an
absent lease) → these were excluded during Phase 2 ingestion review
(`data/interim/excluded_doc_ids.json`) and should not reach labelling at
all. If one slips through, label all fields `null` and note
`"out of scope: <reason>"` rather than silently skipping the document.

**4.9 Signatory vs. named entity** (found during Phase 5 evaluation — 14 of
the first 15 labelled documents had this error, see
`docs/label-changelog.md`) → `landlord_name`/`tenant_name` are the **party
named in the opening paragraph** ("this Agreement, made between LANDLORD
CO. LLC and TENANT INC."), never the individual who signs on that party's
behalf near the signature block ("By: _____, its Manager"). A signature
block name is evidence of *who signed*, not *who the party is*. When the
landlord/tenant is itself an individual (rare but real — e.g. a residential
sublease), the person's name is correct; the test is whether the opening
paragraph names a person or a company, not whether the value looks like a
person's name.

## 5. Slice attributes (not extracted — analysis only)
Recorded outside `fields`, in `slices`. The model never sees these; they
exist only for the Phase 6 bias audit.

- `property_type` — same taxonomy as the extracted field, assigned by you
  from context even when the extracted field itself is null.
- `region` — two-letter jurisdiction code from context (e.g. `US-CA`,
  `US-TX`) inferred from the property address or governing-law clause.
- `urbanicity` — `urban` / `suburban` / `rural` / `unknown`, your best
  judgement from the address; default to `unknown` rather than guessing.
- `scanned` — `true` if the source document was scanned/image-based (see
  Phase 2 review; these were already excluded, so this should stay `false`
  for everything reaching this stage).
- `doc_chars` — filled automatically by the labelling tool from the
  ingested text length.

## 6. Quality control
- Guidelines committed before labelling began — verify with `git log`.
- **10 documents re-labelled blind, 24 hours after first labelling**,
  without looking at the original answers. Self-agreement rate reported in
  `docs/evaluation.md` in Phase 5. Your model's F1 cannot meaningfully
  exceed this number — if you disagree with yourself 12% of the time on
  rent, a 0.94 F1 there is a signal to check for a bug, not celebrate.
- Corrections made after labelling started are logged in
  `docs/label-changelog.md` with the reason, and only ever made against the
  document text and these guidelines — never against a model's output
  (that would contaminate the gold set, see 00-BEFORE-YOU-START.md §B3).

## 7. Changelog
v1.0 2026-08-15 — initial version, written before labelling begins.
Hard cases §4.5–§4.8 pre-populated from Phase 2's manual document review
rather than discovered mid-labelling, since those patterns were already
observed in this specific corpus.
