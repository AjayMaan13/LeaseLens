# Data Provenance

Verified 2026-08-15. Each source checked for reachability, robots.txt, and terms of use before any scraping code was written.

| Source | URL | Date accessed | robots.txt result | Terms note | User-Agent used | Rate limit honored |
|---|---|---|---|---|---|---|
| SEC EDGAR (full-index) | https://www.sec.gov/Archives/edgar/full-index/2023/QTR2/master.idx | 2026-08-15 | Standard; access governed by fair-access policy, not robots.txt | Public filings, free to reuse; requires descriptive User-Agent | `Ajaypartap Singh Maan you@email.com` (replace with real email) | Yes — 403 "Request Rate Threshold Exceeded" observed under light testing; enforce `time.sleep(0.2-0.3)` + backoff |
| SEC EDGAR (full-text search) | https://efts.sec.gov/LATEST/search-index | 2026-08-15 | Same as above | Same as above | Same as above | Same as above |
| TRREB Market Watch | https://trreb.ca/market-data/market-watch/ | 2026-08-15 | `Disallow: /wp-admin/` only | Public market stats, PDF distribution | `Mozilla/5.0` (generic) | Not high-volume; a few PDF fetches |
| CMHC Housing Market Information Portal | https://www03.cmhc-schl.gc.ca/hmip-pimh/ | 2026-08-15 | Not explicitly checked (govt portal, JS-driven) | Public housing market data | n/a | Confirm underlying data endpoint before scraping |
| City of Toronto Open Data (CKAN) | https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_search | 2026-08-15 | `Disallow: /wp-admin/` only (main open.toronto.ca site) | Open Government Licence – Toronto | Default | Standard API, no special limit observed |
| Statistics Canada WDS | https://www150.statcan.gc.ca/t1/wds/rest/ | 2026-08-15 | Only blocks `gsa-crawler` bot | Statistics Canada Open Licence | Default | Standard API |
| Ontario Standard Lease Form 2229E | https://forms.mgcs.gov.on.ca/dataset/047-2229 | 2026-08-15 | Effectively empty, no restriction | Public government form, official template | Default | Single PDF downloads, no scraping loop |

## Sites explicitly NOT scraped

Realtor.ca, Zillow, Kijiji, Zumper, PadMapper — terms of use prohibit scraping and they actively block automated access. Excluded on policy grounds, not attempted.

## Corrections found during verification (see 00-BEFORE-YOU-START.md Part E for detail)

- StatCan CPI "Rented accommodation" table is product ID **18100004**, not 18100002 (the latter is a food-prices table).
- Ontario Standard Lease Form 2229E is not at the originally guessed `dataset/2229e` URL (404). Correct direct PDF links are in Part E4 of `00-BEFORE-YOU-START.md`.
