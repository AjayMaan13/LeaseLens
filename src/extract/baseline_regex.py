"""Regex baseline: dumb, free, deterministic. This is the floor every other
extraction system has to clear -- if a fancier system doesn't beat it,
that's a reportable finding, not something to hide."""
import re
from dateutil import parser as dparse
from src.extract.base import Extractor
from src.schema import LeaseFields

MONEY = re.compile(r"\$\s?([\d,]+(?:\.\d{2})?)")
SQFT = re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:square feet|sq\.?\s?ft\.?|sf)\b", re.I)
RENT_CUE, NEG_CUE = re.compile(r"\brent\b", re.I), re.compile(r"deposit|security|late fee|penalt", re.I)


def _f(s):
    return float(s.replace(",", ""))


class RegexExtractor(Extractor):
    name = "regex_baseline"

    def extract(self, text: str) -> LeaseFields:
        out = {}
        # rent: money mentions in a rent-y sentence that isn't a deposit sentence
        best = None
        for m in MONEY.finditer(text):
            window = text[max(0, m.start() - 200): m.end() + 200]
            if RENT_CUE.search(window) and not NEG_CUE.search(window):
                v = _f(m.group(1))
                if 300 <= v <= 500_000 and (best is None or v > best):   # plausibility band
                    best = v
        out["base_rent_amount"] = best
        out["rent_frequency"] = ("annual" if re.search(r"per annum|annual(ly)? rent", text, re.I)
                                  else "monthly" if re.search(r"per month|monthly", text, re.I) else None)
        if (m := SQFT.search(text)):
            out["premises_area_sqft"] = _f(m.group(1))
        dates = []
        for m in re.finditer(r"\b(?:\w+\s+\d{1,2},\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4})\b", text[:20000]):
            try:
                dates.append(dparse.parse(m.group(), fuzzy=False))
            except Exception:
                pass
        if dates:
            out["lease_start_date"] = min(dates).date().isoformat()
            out["lease_end_date"] = max(dates).date().isoformat() if len(dates) > 1 else None
        for kw, t in [("retail", "retail"), ("industrial", "industrial"), ("warehouse", "industrial"),
                      ("office", "commercial"), ("residential", "residential"), ("apartment", "residential")]:
            if re.search(kw, text[:15000], re.I):
                out["property_type"] = t
                break
        return LeaseFields(**out)
