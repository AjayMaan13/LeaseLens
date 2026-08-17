"""Per-field normalization and match rules. Documented here because a
silently fuzzy-matched comparison is not a defensible methodology --
"we count an address correct at >=90 token-set similarity" is."""
import re
from dateutil import parser as dparse
from rapidfuzz import fuzz


def norm_money(v):
    if v in (None, ""):
        return None
    try:
        return round(float(re.sub(r"[^\d.\-]", "", str(v))), 2)
    except ValueError:
        return None


def norm_date(v):
    if v in (None, ""):
        return None
    try:
        return dparse.parse(str(v), fuzzy=True).date().isoformat()
    except Exception:
        return None


def norm_text(v):
    if v in (None, ""):
        return None
    s = re.sub(r"[^\w\s]", " ", str(v).lower())
    return re.sub(r"\s+", " ", s).strip() or None


def norm_int(v):
    if v in (None, ""):
        return None
    try:
        return int(float(re.sub(r"[^\d.\-]", "", str(v))))
    except ValueError:
        return None


NORMALIZERS = {
    "base_rent_amount": norm_money, "premises_area_sqft": norm_money,
    "lease_start_date": norm_date, "lease_end_date": norm_date,
    "term_length_months": norm_int,
    "landlord_name": norm_text, "tenant_name": norm_text,
    "property_address": norm_text, "property_type": norm_text, "rent_frequency": norm_text,
}


def normalize_field(field, value):
    return NORMALIZERS.get(field, norm_text)(value)


# Fuzzy text fields: token-set similarity threshold below which two strings
# don't count as a match. address/names get real formatting variance
# ("123 Main St." vs "123 Main Street") that exact-match would punish
# unfairly, so this is a deliberate, documented leniency -- not silent.
FUZZY_FIELDS = {"property_address": 90, "landlord_name": 88, "tenant_name": 88}

# Numeric fields get a relative tolerance instead of exact match, since
# sqft in particular is sometimes rounded differently by different sources.
NUMERIC_TOL = {"premises_area_sqft": 0.01}   # 1% relative tolerance


def values_match(field, g, p):
    """Documented match rule per field -- see docs/evaluation.md."""
    if g is None or p is None:
        return False
    if field in FUZZY_FIELDS:
        return fuzz.token_set_ratio(g, p) >= FUZZY_FIELDS[field]
    if field in NUMERIC_TOL and isinstance(g, float):
        return abs(g - p) <= NUMERIC_TOL[field] * max(abs(g), 1)
    return g == p
