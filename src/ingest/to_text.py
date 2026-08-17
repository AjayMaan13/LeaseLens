"""Convert raw scraped/downloaded documents (HTML, PDF, TXT) into clean plain text.

PDFs and filed HTML are containers, not text -- this is where a lot of
real-world extraction quality gets decided. An extraction model can't find
a rent your parser destroyed.
"""
import json, pathlib, re
import pdfplumber
from bs4 import BeautifulSoup

RAW, INTERIM = pathlib.Path("data/raw"), pathlib.Path("data/interim")
INTERIM.mkdir(parents=True, exist_ok=True)


def html_to_text(p: pathlib.Path) -> str:
    soup = BeautifulSoup(p.read_bytes(), "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return re.sub(r"\n{3,}", "\n\n", soup.get_text("\n", strip=True))


def pdf_to_text(p: pathlib.Path) -> str:
    with pdfplumber.open(p) as pdf:
        return "\n".join((pg.extract_text() or "") for pg in pdf.pages)


def run(sources=(RAW / "edgar", RAW.parent / "synthetic")):
    report = []
    for src_dir in sources:
        if not src_dir.exists():
            continue
        for p in sorted(src_dir.rglob("*")):
            if p.suffix.lower() not in {".html", ".htm", ".pdf", ".txt"}:
                continue
            text = (pdf_to_text(p) if p.suffix.lower() == ".pdf"
                    else p.read_text(errors="ignore") if p.suffix.lower() == ".txt"
                    else html_to_text(p))
            (INTERIM / f"{p.stem}.txt").write_text(text)
            report.append({
                "doc_id": p.stem, "source_dir": str(src_dir), "chars": len(text),
                "likely_scanned": len(text) < 500,
                "has_rent_kw": bool(re.search(r"\brent\b", text, re.I)),
            })
    pathlib.Path("data/interim/ingest_report.json").write_text(json.dumps(report, indent=2))
    bad = [r for r in report if r["likely_scanned"] or not r["has_rent_kw"]]
    print(f"{len(report)} docs converted, {len(bad)} flagged for review")
    for r in bad:
        print(f"  FLAG {r['doc_id']}: chars={r['chars']} likely_scanned={r['likely_scanned']} "
              f"has_rent_kw={r['has_rent_kw']}")


if __name__ == "__main__":
    run()
