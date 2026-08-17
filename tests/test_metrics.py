"""Hand-built fixtures with known answers. If metrics.py has a bug, every
number in the repo is wrong with nothing to catch it -- these tests are
that check."""

from src.evaluate.metrics import score, summarize, prf


def test_prf_basic():
    p, r, f = prf(tp=40, fp=12, fn=10)
    assert round(p, 3) == 0.769 and round(r, 3) == 0.800 and round(f, 3) == 0.784


def test_wrong_value_counts_as_both():
    gold = {"d1": {"base_rent_amount": 4500}}
    pred = {"d1": {"base_rent_amount": 3200}}
    c = score(gold, pred)["base_rent_amount"]
    assert c == {"tp": 0, "fp": 1, "fn": 1}


def test_null_gold_null_pred_not_scored():
    assert score({"d1": {"tenant_name": None}}, {"d1": {"tenant_name": None}}) == {}


def test_hallucination_is_fp():
    c = score({"d1": {"base_rent_amount": None}}, {"d1": {"base_rent_amount": 3200}})
    assert c["base_rent_amount"]["fp"] == 1


def test_gave_up_is_fn_only():
    c = score({"d1": {"base_rent_amount": 4500}}, {"d1": {"base_rent_amount": None}})
    assert c["base_rent_amount"] == {"tp": 0, "fp": 0, "fn": 1}


def test_money_normalization_equivalence():
    c = score({"d1": {"base_rent_amount": "$4,500.00"}}, {"d1": {"base_rent_amount": 4500}})
    assert c["base_rent_amount"]["tp"] == 1


def test_address_fuzzy_match():
    c = score({"d1": {"property_address": "123 Main Street, Toronto"}},
              {"d1": {"property_address": "123 Main St. Toronto"}})
    assert c["property_address"]["tp"] == 1


def test_address_too_different_not_matched():
    c = score({"d1": {"property_address": "123 Main Street, Toronto"}},
              {"d1": {"property_address": "999 Different Avenue, Vancouver"}})
    assert c["property_address"] == {"tp": 0, "fp": 1, "fn": 1}


def test_micro_pools_across_fields():
    gold = {"d1": {"base_rent_amount": 4500, "tenant_name": "Acme"}}
    pred = {"d1": {"base_rent_amount": 4500, "tenant_name": None}}
    s = summarize(score(gold, pred))
    p, r, f = s["micro"]
    assert (p, r) == (1.0, 0.5)


def test_macro_averages_per_field_equally():
    # base_rent_amount: perfect (F1=1.0). tenant_name: total miss (F1=0.0).
    # Macro should average the two F1s, not pool the raw counts.
    gold = {"d1": {"base_rent_amount": 4500, "tenant_name": "Acme"}}
    pred = {"d1": {"base_rent_amount": 4500, "tenant_name": None}}
    s = summarize(score(gold, pred))
    assert round(s["macro"][2], 3) == 0.5
