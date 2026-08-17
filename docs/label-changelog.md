# Gold Label Changelog

Per `docs/annotation-guidelines.md` §6: corrections are logged here with a
reason, made only against document text and the guidelines, never against
a model's output.

## 2026-08-15 — signatory-vs-entity error found during Phase 5 evaluation, corrected

While building the Phase 5 evaluation harness, `landlord_name`/
`tenant_name` scored ~0% F1 across all three extraction systems, which was
suspicious enough to check by hand before trusting it as a real result.
Checked one document's raw text directly and found the gold label had
picked up the individual who signed near the signature block rather than
the entity named in the document's opening paragraph. Checked all 15
labelled documents with a heuristic (2-3 title-case words, no LLC/Inc/Corp
keyword) and found the same pattern in 14 of 15.

**Root cause guess, not confirmed:** the labelling tool's default keyword
search is "rent," which tends to surface text near the middle/end of a
lease (rent clauses, then signature blocks) rather than the opening
"by and between" paragraph where the actual party names are stated.

**Corrected against each document's opening paragraph:**

| doc_id | landlord_name: before → after | tenant_name: before → after |
|---|---|---|
| edgar_0000024741_..._glw4309191-ex103 | Erin M. Parks → BA Leasing BSC, LLC | Scott A. Forester → Solar Technology LLC |
| edgar_0000029332_..._ex10-53leaseagreementbetwe | Kamyar Mateen → Adairsville GA, LLC | Allen L. Danzey → TDG Operations, LLC |
| edgar_0000768835_..._ex102biglotslease | Benjamin Clark → Bankers Commercial Corporation | Jonathon E. Ramsden → AVDC, LLC |
| edgar_0000879911_..._ea180790ex10-1-applied | Sheri L. Hill → Arizona Board of Regents for and on behalf of the University of Arizona | Kathryn B. Nelson → Campus Research Corporation |
| edgar_0000879911_..._ea180931ex10-1-applied | Mary Jacobs → Campus Research Corporation | Gregory J. Quarles → Applied Energetics, Inc. |
| edgar_0000895464_..._yubo-ex101 | Wang Yang → Sichuan Anyi Hengke Technology Co., Ltd. | (already correct — Yubo Jingzhi Biotechnology (Chengdu) Co., Ltd) |
| edgar_0000899923_..._phasei-leaseterminationagr | Michael Dorris → HCPI/UTAH II, LLC | R. Bryan Giffsbee → Myriad Genetics, Inc. |
| edgar_0000899923_..._phaseii-leaseterminationag | Michael Dorris → HCPI/UTAH II, LLC | R. Bryan Riggsbee → Myriad Genetics, Inc. |
| edgar_0001017303_..._ef20015290-ex10-16 | Robert T. Dean → Bomax Properties, LLC | Richard L. Cote → Transact Technologies Incorporated |
| edgar_0001040161_..._sanjoseleaseamendmentex1019 | Kenneth Young → Hudson Concourse, LLC | Haley Aman → Pixelworks, Inc. |
| edgar_0001074828_..._knwn-ex1031 | Phil Bosua → **unchanged** (genuine individual landlord, verified correct) | Ron Erickson → Know Labs, Inc. |
| edgar_0001095315_..._freeportlease-pfswebexecut | Chad Parrish → CRP/AI Freeport Parkway Owner, L.P. | Zach Thomann → Priority Fulfillment Services, Inc. |
| edgar_0001131312_..._f10k2023ex10-4-zionoil | Dan Jones → Hartman SPE, LLC | William H. Avery → Zion Oil & Gas, Inc. |
| edgar_0001279620_..._ea169621ex10-3-zonedpro | Bryan McLaren → ZP RE MI Woodward, LLC | Thomas Naffs → Rapid Fish 2 LLC |
| edgar_0001075531_..._saleleasebackspaexredacted | Dirk Holder → **null** (see note below) | Maria Rocha Barros → **null** |

**One exception, not a name swap:** `edgar_0001075531_..._saleleasebackspaexredacted`
turned out not to be a Landlord/Tenant document at all on inspection — it's
a Sale and Purchase Agreement for a sale-leaseback transaction (Booking.com
Real Estate Amsterdam B.V. as Seller, D-IE Wiis Oosterdok Coöperatief U.A.
as Purchaser, Booking.com Holding B.V. as Guarantor). Set both fields to
`null` rather than guess which party maps to "landlord"/"tenant" — the
actual lease terms likely live in a referenced schedule not clearly
separated in this extraction. Flagged `uncertain: true` in the record's
notes for a human follow-up read.

**One field turned out already correct:** `edgar_0001074828_..._knwn-ex1031`'s
landlord really is an individual, "Phil Bosua" — confirmed against the
document text (guideline §4.9 covers this: the test is whether the opening
paragraph names a person or a company, not whether the value looks like a
person's name). Only its `tenant_name` needed fixing.

**Not yet re-verified:** only the first row above was checked against
source text before this batch; the rest were corrected using the same
"by and between" opening-paragraph pattern without a second independent
read. Worth a spot-check in a future session, not assumed infallible.

All other fields (rent, dates, sqft, property type) were unaffected by
this issue and were not re-checked.
