# Extraction Results

Scored against **15 labeled gold documents** (of 42 usable EDGAR documents total -- labeling in progress, this will be re-run as more are labeled).

## Micro / Macro P/R/F1 by system

| System | Micro P | Micro R | Micro F1 | Macro P | Macro R | Macro F1 |
|---|---|---|---|---|---|---|
| regex_baseline | 0.250 | 0.121 | 0.163 | 0.155 | 0.129 | 0.137 |
| ner_hybrid | 0.178 | 0.065 | 0.095 | 0.053 | 0.057 | 0.055 |
| llm_structured | 0.673 | 0.532 | 0.595 | 0.655 | 0.528 | 0.582 |

## Per-field F1 by system

| Field | regex_baseline | ner_hybrid | llm_structured |
|---|---|---|---|
| landlord_name | 0.000 (n=14) | 0.276 (n=25) | 0.963 (n=14) |
| tenant_name | 0.000 (n=14) | 0.069 (n=28) | 0.963 (n=14) |
| property_address | 0.000 (n=14) | 0.207 (n=26) | 0.583 (n=17) |
| property_type | 0.148 (n=25) | 0.000 (n=14) | 0.296 (n=23) |
| premises_area_sqft | 0.250 (n=14) | 0.000 (n=11) | 0.632 (n=13) |
| lease_start_date | 0.222 (n=24) | 0.000 (n=14) | 0.348 (n=19) |
| lease_end_date | 0.455 (n=17) | 0.000 (n=10) | 0.667 (n=12) |
| term_length_months | 0.000 (n=10) | 0.000 (n=10) | 0.632 (n=13) |
| base_rent_amount | 0.125 (n=15) | 0.000 (n=10) | 0.353 (n=14) |
| rent_frequency | 0.167 (n=22) | 0.000 (n=13) | 0.381 (n=17) |
