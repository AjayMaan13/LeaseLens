# Ingestion Review — manual pass over flagged documents

Date: 2026-08-15. Every document flagged by `src/ingest/to_text.py` (either
`likely_scanned` or missing the `rent` keyword) was opened and read before
any labelling began, per the annotation-before-extraction rule in
`00-BEFORE-YOU-START.md` §B3.

## Category 1 — Image-embedded / scanned, effectively zero extractable text

These EX-10 documents wrap scanned page images (`<img src="...jpg">`) inside
the HTML shell instead of real text. `pdfplumber`/BeautifulSoup correctly
extract almost nothing because there is almost nothing to extract — this is
not an ingestion bug, it's the real-world scanned-document case the plan
anticipated, just arriving as image-in-HTML rather than a scanned PDF.

| doc_id | chars | Decision |
|---|---|---|
| edgar_0000827099_000165495424003883_cpwr-ex1067 | 72 | **Exclude** — no recoverable text without OCR |
| edgar_0000827099_000165495424003883_cpwr-ex1068 | 72 | **Exclude** — same filing, same issue |
| edgar_0001128353_000147793223002620_etck-ex102 | 89 | **Exclude** — no recoverable text |
| edgar_0001851860_000121390022077385_ea169583ex10-1-smartfor | 149 | **Exclude** — no recoverable text |

## Category 2 — Wrong document type: equipment/personal-property leases, not real estate

Both matched the "lease agreement" search and carry an EX-10 type, but on
inspection are **equipment leases** (DocuSign-wrapped equipment lease and an
explicit "Equipment Lease Agreement" schedule) — out of scope for a project
whose schema is premises/property fields (`premises_area_sqft`,
`property_address`, `property_type`). Keeping these would silently
contaminate the corpus with a document type the schema was never designed
to describe.

| doc_id | chars | Decision |
|---|---|---|
| edgar_0001553264_000168316822008699_aquapower-ex1010 | 2,013 | **Exclude** — equipment lease, not real estate |
| edgar_0001832483_000121390024018566_ea0200355ex10-17-serverobot | 16,987 | **Exclude** — "Lease Schedule" to an Equipment Lease Agreement |

## Category 3 — Real property lease amendments/guaranties, legitimately no "rent" keyword

Genuine real-estate lease documents. The `rent` keyword check is a naive
heuristic and these are exactly its false positives:

- Amendments frequently modify only specific clauses (e.g. term, notice
  address) without restating the rent clause at all.
- A **Guaranty** references "the Lease" by name but is a separate
  instrument — a third party guaranteeing the tenant's obligations — and
  does not itself restate lease economics.

| doc_id | chars | Decision |
|---|---|---|
| edgar_0001823239_000182323924000032_aex1017xflandersleaseamend | 5,996 | **Keep** — Second Amendment to Lease; annotate per guideline §4.5 (label the amendment's own stated values only, most fields likely null) |
| edgar_0000879911_000121390023051014_ea180790ex10-1-applied | 3,767 | **Keep** — First Amendment to Lease; same rule. Also note: uses "Lessor/Lessee" terminology, not "Landlord/Tenant" — a real phrasing variant to account for in the regex baseline later |
| edgar_0001095315_000109531522000095_freeportleasepfswebguarant | 11,036 | **Exclude** — this is a Guaranty, not the Lease itself; the referenced Lease is a separate exhibit not in our corpus |

## Summary

- 49 EDGAR documents harvested, 9 flagged, all 9 manually reviewed.
- **7 excluded** from the annotation set (4 unrecoverable scanned/image
  documents, 2 wrong document type, 1 guaranty referencing an absent lease).
- **2 kept** as legitimate hard cases (lease amendments) — annotate per
  guidelines §4.5 when Phase 3 begins.
- Usable EDGAR lease corpus going into Phase 3: **42 documents** (49 − 7).

## Note on the synthetic corpus's flags

All 25 synthetic documents were flagged `likely_scanned` by the same
`chars < 500` heuristic. This is a **false positive specific to the
synthetic generator**, not a real defect: the synthetic leases were
deliberately written as short, single-page field-only documents (landlord,
tenant, address, rent, term, dates — no boilerplate legal text), so they are
short by design. The heuristic is tuned for multi-page real filings and
should not be applied to the synthetic set without adjustment. No action
taken; documented here so the flag isn't misread later as 25 broken
documents.
