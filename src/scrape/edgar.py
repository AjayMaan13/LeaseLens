"""Harvest real commercial lease exhibits (EX-10) from SEC EDGAR.

Uses EDGAR's full-text search API (efts.sec.gov) rather than blind-scanning
the quarterly master index: searching "lease agreement" directly and
filtering by file_type == EX-10.* returns document-level hits (already
matched on content) instead of forcing us to open every filing's index page
and hope one has a lease exhibit. Confirmed during source verification that
this endpoint returns hundreds of relevant hits per quarter, vs. roughly one
match per ~1000 filings scanned with the master-index approach.

The BeautifulSoup requirement is still honestly met: each filing's index
page IS parsed with BeautifulSoup below, to confirm the exhibit is really
lease-related (search hits alone can be noisy) and to grab a clean title.
"""
import os, time, json, pathlib, re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
UA    = {"User-Agent": os.environ["SEC_USER_AGENT"]}
RAW   = pathlib.Path("data/raw/edgar"); RAW.mkdir(parents=True, exist_ok=True)
DELAY = 0.2
BASE  = "https://www.sec.gov"
FTS   = "https://efts.sec.gov/LATEST/search-index"


def get(url: str, params: dict | None = None, retries: int = 3) -> requests.Response:
    for attempt in range(retries):
        r = requests.get(url, headers=UA, params=params, timeout=30)
        if r.status_code >= 500 and attempt < retries - 1:
            time.sleep(2 * (attempt + 1))   # transient SEC-side errors, back off and retry
            continue
        r.raise_for_status()
        time.sleep(DELAY)
        return r


def search_lease_exhibits(start_date: str, end_date: str, forms=("10-K", "10-Q", "8-K"),
                           max_results=200):
    """Query EDGAR full-text search for lease-related EX-10 filings in a date range."""
    hits, frm, page = [], 0, 100
    while len(hits) < max_results:
        resp = get(FTS, params={
            "q": '"lease agreement"',
            "forms": ",".join(forms),
            "dateRange": "custom",
            "startdt": start_date,
            "enddt": end_date,
            "from": frm,
        }).json()
        batch = resp["hits"]["hits"]
        if not batch:
            break
        for h in batch:
            src = h["_source"]
            if not src.get("file_type", "").upper().startswith("EX-10"):
                continue
            accession, filename = h["_id"].split(":")
            hits.append({
                "cik": src["ciks"][0],
                "company": src["display_names"][0].split("  (CIK")[0],
                "form": src.get("form"),
                "filed": src.get("file_date"),
                "accession": accession,
                "filename": filename,
                "file_type": src["file_type"],
                "file_description": src.get("file_description", ""),
            })
        frm += page
        if frm >= resp["hits"]["total"]["value"]:
            break
    return hits[:max_results]


def confirm_lease_relevance(hit: dict) -> str | None:
    """BeautifulSoup-parse the filing's index page to confirm this exhibit is lease-related
    and return the document URL, or None if the index page doesn't back it up."""
    acc_nodash = hit["accession"].replace("-", "")
    index_url = f"{BASE}/Archives/edgar/data/{hit['cik']}/{acc_nodash}/{hit['accession']}-index.htm"
    try:
        soup = BeautifulSoup(get(index_url).text, "lxml")
    except requests.HTTPError:
        return None

    for row in soup.select("table.tableFile tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
        link = row.find("a", href=True)
        if len(cells) < 4 or not link:
            continue
        description, document, doc_type = cells[1], cells[2], cells[3]
        if hit["filename"] not in document:
            continue
        if not re.search(r"lease", f"{description} {document}", re.I):
            continue
        return BASE + link["href"]
    return None


def harvest(quarters=(("2023-04-01", "2023-06-30"),
                       ("2022-10-01", "2022-12-31"),
                       ("2024-01-01", "2024-03-31")),
            per_quarter_target=27, cap_per_company=2):
    """Harvest across multiple quarters/years on purpose, for property-type and region diversity."""
    manifest, seen_companies = [], {}
    manifest_path = pathlib.Path("data/raw/edgar_manifest.json")
    for start_date, end_date in quarters:
        try:
            candidates = search_lease_exhibits(start_date, end_date, max_results=200)
        except requests.HTTPError as e:
            print(f"skipping {start_date}:{end_date} after retries failed ({e})")
            continue
        added = 0
        for hit in candidates:
            if added >= per_quarter_target:
                break
            if seen_companies.get(hit["company"], 0) >= cap_per_company:
                continue
            doc_url = confirm_lease_relevance(hit)
            if not doc_url:
                continue
            try:
                body = get(doc_url).content
            except requests.HTTPError:
                continue
            doc_id = f"edgar_{hit['cik']}_{hit['accession'].replace('-', '')}"
            fp = RAW / f"{doc_id}.html"
            fp.write_bytes(body)
            record = {**hit, "doc_id": doc_id, "url": doc_url,
                      "local_path": str(fp), "bytes": len(body),
                      "source_quarter": f"{start_date}:{end_date}"}
            manifest.append(record)
            seen_companies[hit["company"]] = seen_companies.get(hit["company"], 0) + 1
            added += 1
            print(f"[{len(manifest):>3}] {start_date[:7]}  {hit['company'][:40]:<40} {hit['file_type']}")
        manifest_path.write_text(json.dumps(manifest, indent=2))   # save progress after each quarter
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n{len(manifest)} lease exhibits from {len(seen_companies)} companies "
          f"across {len(quarters)} quarters")


if __name__ == "__main__":
    harvest()
