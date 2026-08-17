"""Post-hoc check: does an extracted literal actually appear in the source
text? Cheap guard against hallucination -- catches a large fraction of
plausible-but-invented values with a small amount of code.

Field-aware on purpose: a first pass treated every field as "must appear
verbatim," which flagged normalized dates (2023-03-15 vs "March 15, 2023")
and mapped categories (property_type="commercial" derived from the word
"office") as "ungrounded" even though nothing was invented -- just
normalized. Those fields get a pass here; the check stays strict only
where an invented value is the actual risk (money, area, names, address).
"""
from dateutil import parser as dparse
import re

# Fields where normalization/derivation legitimately produces a value that
# won't appear as a literal substring of the source. Not skipped because
# they can't be wrong -- skipped because literal-substring can't tell
# "normalized correctly" from "hallucinated," so it isn't a useful check here.
NOT_LITERALLY_GROUNDABLE = {"property_type", "rent_frequency", "term_length_months"}


def _date_grounded(value: str, text: str) -> bool:
    try:
        target = dparse.parse(str(value), fuzzy=True).date()
    except Exception:
        return False
    for m in re.finditer(r"\b(?:\w+\s+\d{1,2},\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b", text):
        try:
            if dparse.parse(m.group(), fuzzy=False).date() == target:
                return True
        except Exception:
            continue
    return False


def grounded(field: str, value, text: str) -> bool:
    if value is None:
        return True
    if field in NOT_LITERALLY_GROUNDABLE:
        return True
    if field in {"lease_start_date", "lease_end_date"}:
        return _date_grounded(value, text)

    s = str(value)
    if s.replace(".", "").replace("-", "").isdigit():
        try:
            n = float(s)
        except ValueError:
            return s.lower()[:25] in text.lower()
        cands = [f"{n:,.2f}", f"{n:,.0f}", f"{n:.2f}", f"{int(n)}", f"{n:,}"]
        return any(c in text for c in cands)
    return s.lower()[:25] in text.lower()
