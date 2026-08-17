# Extraction Results

Scored against **40 labeled gold documents** (of 40 usable EDGAR documents total).

## Micro / Macro P/R/F1 by system

| System | Micro P | Micro R | Micro F1 | Macro P | Macro R | Macro F1 |
|---|---|---|---|---|---|---|
| regex_baseline | 0.458 | 0.237 | 0.313 | 0.270 | 0.237 | 0.247 |
| ner_hybrid | 0.284 | 0.103 | 0.151 | 0.086 | 0.094 | 0.089 |
| llm_structured | 0.837 | 0.772 | 0.803 | 0.829 | 0.766 | 0.795 |

## Per-field F1 by system

| Field | regex_baseline | ner_hybrid | llm_structured |
|---|---|---|---|
| landlord_name | 0.000 (n=39) | 0.390 (n=62) | 0.987 (n=39) |
| tenant_name | 0.000 (n=39) | 0.154 (n=72) | 0.961 (n=40) |
| property_address | 0.000 (n=30) | 0.348 (n=57) | 0.871 (n=35) |
| property_type | 0.406 (n=55) | 0.000 (n=38) | 0.667 (n=50) |
| premises_area_sqft | 0.341 (n=34) | 0.000 (n=28) | 0.769 (n=32) |
| lease_start_date | 0.521 (n=54) | 0.000 (n=37) | 0.656 (n=43) |
| lease_end_date | 0.421 (n=45) | 0.000 (n=26) | 0.750 (n=30) |
| term_length_months | 0.000 (n=25) | 0.000 (n=25) | 0.898 (n=27) |
| base_rent_amount | 0.217 (n=41) | 0.000 (n=25) | 0.625 (n=33) |
| rent_frequency | 0.567 (n=48) | 0.000 (n=33) | 0.762 (n=39) |
