"""Generate synthetic Ontario-Standard-Lease-style residential leases as PDFs,
with ground truth written alongside for free (Faker generated every value, so
we already know the correct answer).

These exist to stress-test extraction against formatting variety and to give
a residential/Canadian comparison slice against the EDGAR commercial corpus.
They are NEVER merged into headline results -- separate directory, separate
column, always labelled synthetic (see 00-BEFORE-YOU-START.md Part E4/B3).
"""
import json, pathlib, random
from datetime import date, timedelta

from faker import Faker
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from src.schema import LeaseFields

fake = Faker()
Faker.seed(13)
random.seed(13)

OUT = pathlib.Path("data/synthetic"); OUT.mkdir(parents=True, exist_ok=True)

RENT_LABELS = ["Monthly Rent", "Rent Payable", "Total Rent Per Month", "Rent"]
DATE_FORMATS = ["%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%b-%Y"]


def fmt_money(amount: float, style: int) -> str:
    if style == 0:
        return f"${amount:,.2f}"
    if style == 1:
        return f"{amount:,.0f}"
    words = {
        1: "One Thousand", 1500: "One Thousand Five Hundred", 1850: "One Thousand Eight Hundred Fifty",
        2000: "Two Thousand", 2200: "Two Thousand Two Hundred", 2500: "Two Thousand Five Hundred",
    }
    base = min(words.keys(), key=lambda k: abs(k - amount))
    return f"{words[base]} Dollars"


def fmt_date(d: date, style: int) -> str:
    return d.strftime(DATE_FORMATS[style])


def make_lease(idx: int) -> tuple[str, LeaseFields, dict]:
    landlord = fake.name()
    tenant = fake.name()
    address = fake.address().replace("\n", ", ")
    rent = random.choice([1450.0, 1650.0, 1850.0, 2000.0, 2200.0, 2500.0])
    start = date(2024, random.randint(1, 6), 1)
    term_months = random.choice([12, 12, 24])
    end = start + timedelta(days=30 * term_months)

    money_style = random.randint(0, 2)
    date_style = random.randint(0, 3)
    rent_label = random.choice(RENT_LABELS)
    field_order = random.sample(
        ["landlord", "tenant", "address", "rent", "term", "dates"], k=6)
    noisy = idx % 6 == 0   # ~1 in 6 gets whitespace/OCR-style noise

    lines_by_key = {
        "landlord": f"Landlord: {landlord}",
        "tenant": f"Tenant: {tenant}",
        "address": f"Rental Unit Address: {address}",
        "rent": f"{rent_label}: {fmt_money(rent, money_style)}",
        "term": f"Term of Tenancy: {term_months} months",
        "dates": f"Start Date: {fmt_date(start, date_style)}    End Date: {fmt_date(end, date_style)}",
    }
    body_lines = ["ONTARIO STANDARD LEASE (synthetic)", ""]
    body_lines += [lines_by_key[k] for k in field_order]
    text = "\n".join(body_lines)

    if noisy:
        # simulate OCR/whitespace noise: extra spaces, stray line breaks
        text = "\n".join(
            "  ".join(w for w in line.split(" ")) if line else "" for line in text.split("\n")
        )
        text = text.replace(":", " :  ")

    doc_id = f"synth_ontario_{idx:03d}"
    gold = LeaseFields(
        landlord_name=landlord,
        tenant_name=tenant,
        property_address=address,
        property_type="residential",
        premises_area_sqft=None,
        lease_start_date=start.isoformat(),
        lease_end_date=end.isoformat(),
        term_length_months=term_months,
        base_rent_amount=rent,
        rent_frequency="monthly",
    )
    meta = {
        "doc_id": doc_id, "source": "synthetic",
        "slices": {"property_type": "residential", "region": "CA-ON",
                   "urbanicity": "unknown", "scanned": False, "doc_chars": len(text)},
        "notes": f"synthetic; money_style={money_style} date_style={date_style} "
                 f"rent_label='{rent_label}' noisy={noisy}",
        "fields": gold.model_dump(),
    }
    return text, gold, meta


def render_pdf(fp: pathlib.Path, text: str):
    c = canvas.Canvas(str(fp), pagesize=letter)
    width, height = letter
    y = height - 72
    for line in text.split("\n"):
        c.drawString(72, y, line[:110])
        y -= 16
        if y < 72:
            c.showPage()
            y = height - 72
    c.save()


def generate(n=25):
    for i in range(n):
        text, gold, meta = make_lease(i)
        pdf_path = OUT / f"synth_ontario_{i:03d}.pdf"
        render_pdf(pdf_path, text)
        (OUT / f"synth_ontario_{i:03d}.json").write_text(json.dumps(meta, indent=2))
    print(f"{n} synthetic Ontario-style leases written to {OUT}/")


if __name__ == "__main__":
    generate()
