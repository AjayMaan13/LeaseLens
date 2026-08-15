"""Pull neighbourhood/regional rent series for Toronto/GTA + guaranteed StatCan backup.

TRREB Market Watch publishes PDF-only (no HTML table) and CMHC's Housing Market
Information Portal is JS-driven -- neither is a clean BeautifulSoup target
(confirmed during source verification in 00-BEFORE-YOU-START.md Part E2).
So this script:
  1. Pulls StatCan CPI "Rented accommodation" (table 18-10-0004-01) via the WDS
     REST API -> guaranteed real, monthly, long-format backup series.
  2. Pulls the City of Toronto Open Data CKAN API for Neighbourhood Profiles
     -> gives the 158-neighbourhood taxonomy for the `region`/`urbanicity` slices.
  3. Archives the latest TRREB Market Watch PDF as raw bytes for Phase 2 to
     parse with pdfplumber (PDF table extraction, not BeautifulSoup's job).
"""
import io, pathlib, zipfile
import requests
import pandas as pd

SERIES = pathlib.Path("data/series"); SERIES.mkdir(parents=True, exist_ok=True)
RAW = pathlib.Path("data/raw/rent_sources"); RAW.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "lease-lens research project (ajayapsmaanm13@gmail.com)"}

STATCAN_PRODUCT_ID = 18100004          # CPI, monthly, not seasonally adjusted
STATCAN_URL = f"https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/{STATCAN_PRODUCT_ID}/en"


def fetch_statcan_rent_series() -> pd.DataFrame:
    """Bulk-download StatCan CPI table 18-10-0004-01, filter to 'Rented accommodation'."""
    zip_url = requests.get(STATCAN_URL, headers=HEADERS, timeout=60).json()["object"]
    zbytes = requests.get(zip_url, headers=HEADERS, timeout=120).content
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        csv_name = next(n for n in z.namelist() if n.endswith(".csv") and "MetaData" not in n)
        df = pd.read_csv(z.open(csv_name), low_memory=False)

    rent = df[df["Products and product groups"] == "Rented accommodation"].copy()
    rent = rent[["GEO", "REF_DATE", "VALUE"]].rename(
        columns={"GEO": "area_name", "REF_DATE": "period", "VALUE": "value"})
    rent["area_code"] = rent["area_name"].str.slice(0, 12)
    rent["metric"] = "cpi_rented_accommodation"
    out = rent[["area_code", "area_name", "period", "value", "metric"]].dropna(subset=["value"])
    out.to_csv(SERIES / "statcan_rent_cpi.csv", index=False)
    print(f"StatCan: {len(out)} rows, {out['area_name'].nunique()} geographies, "
          f"{out['period'].min()}–{out['period'].max()}")
    return out


def fetch_toronto_neighbourhood_taxonomy() -> pd.DataFrame:
    """Pull the City of Toronto CKAN 'Neighbourhood Profiles' dataset (JSON API, not HTML scrape)."""
    pkg = requests.get(
        "https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show",
        params={"id": "neighbourhood-profiles"}, headers=HEADERS, timeout=30,
    ).json()["result"]
    resource = next(r for r in pkg["resources"] if r["format"].lower() == "csv")
    df = pd.read_csv(resource["url"], low_memory=False)
    df.to_csv(SERIES / "toronto_neighbourhood_profiles.csv", index=False)
    print(f"Toronto Open Data: neighbourhood profiles saved, {df.shape[0]} rows x {df.shape[1]} cols")
    return df


def fetch_trreb_market_watch_pdf() -> pathlib.Path:
    """Archive the latest TRREB Market Watch PDF for Phase 2 pdfplumber extraction."""
    url = "https://trreb.ca/wp-content/files/market-stats/market-watch/mw2607.pdf"
    resp = requests.get(url, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    fp = RAW / "trreb_market_watch_latest.pdf"
    fp.write_bytes(resp.content)
    print(f"TRREB: saved {fp} ({len(resp.content):,} bytes) -- parse with pdfplumber in Phase 2")
    return fp


def build_long_format_series():
    """Combine sources into data/series/rent_by_area.csv, long format."""
    statcan_path = SERIES / "statcan_rent_cpi.csv"
    if not statcan_path.exists():
        return
    out = pd.read_csv(statcan_path)
    out.to_csv(SERIES / "rent_by_area.csv", index=False)
    print(f"rent_by_area.csv: {len(out)} rows written")


if __name__ == "__main__":
    fetch_statcan_rent_series()
    fetch_toronto_neighbourhood_taxonomy()
    fetch_trreb_market_watch_pdf()
    build_long_format_series()
