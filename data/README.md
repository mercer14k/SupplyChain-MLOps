# Data dictionary and provenance

The canonical observation schema is `schemas/observation.schema.json`, generated from Pydantic. Units are base units per day and elapsed days; no currencies or hidden conversions are used.

| Field | Meaning |
|---|---|
| id | Stable record ID, 1–160 permitted identifier characters |
| source_id | Source dataset/generator identifier |
| ingested_at | Timezone-aware source ingestion timestamp; dataset `created_at` records actual API ingestion |
| validation_status | `valid` for canonical rows; invalid input lives in the dataset report |
| lineage | Optional bounded string metadata, including generator/seed or upstream record IDs |
| day | Observation date |
| sku / location | Series identity; observations are unique by date/SKU/location |
| demand | Nonnegative observed daily demand/usage units; <= 10 million |
| stock_on_hand | Nonnegative closing stock in base units |
| lead_time_days | Nonnegative replenishment lead time, <= 365 days |
| fulfillment_rate | Fraction in [0,1]; actual synthetic rate or explicitly documented ConsignAI proxy |
| promotion | Known planned promotion indicator |
| stockout | Censoring flag; excludes the observation from forecast fitting/calibration/scoring |
| is_anomaly | Evaluation label only, never used as a model feature or threshold input |

## Committed samples

- `sample/demand.jsonl`: 720 observations, 4 series × 180 days, seed 42. Weekly seasonality, trend, promotion effects, Gaussian measurement noise and two seeded late lead-time/fulfillment shocks per series.
- `sample/drift.jsonl`: seed 43, demand ×1.7, lead time +6 days and fulfillment -0.10. Same calendar context, intentionally changed observed distributions.
- `sample/consignai.jsonl`: 770 canonical observations adapted from the actual ConsignAI mini archive. Usage movements are aggregated by day/SKU/location, joined to contractor/field snapshots; explicit zero-usage days are preserved. Material lead time and a stock-availability fulfillment proxy are clearly marked in lineage. Labels are unavailable; anomaly promotion is blocked for this data.
- `sample/invalid.jsonl`: a valid row, negative demand and broken JSON. Both invalid lines are reported. The whole version remains ineligible for training.
- `sample/ground-truth.json`: stable anomaly record IDs from the standalone generator and a description of seeded distribution changes.
- `upstream/consignai-mini.jsonl.gz`: unmodified source archive; SHA-256 in `upstream/provenance.json`. Original ground-truth position labels and notices are retained. These position-level labels are not mislabeled as per-day fulfillment labels.

All dates and source timestamps are synthetic. Stable fixture timestamps make generation byte-reproducible. A fixed Python `random.Random(seed)` drives noise. Invalid conditions are regression fixtures rather than hidden silent corrections. Tests also cover zero demand, stockout censoring, duplicate IDs, missing series, constant-feature drift and contaminated anomaly calibration.

**DemandSense does not exist yet.** The demand generator is original to this repository. A future DemandSense adapter must preserve its real identifiers and document its semantics; no current connector is claimed.

Regenerate with `scml generate`. Create larger datasets with `python -m scml.data.generator --days 365 --series 40 --seed 42 --output output/large-demand.jsonl`. Keep large generated files out of Git; use the performance harness to measure them. Data can be imported through the UI/API; all rows are validated again on import.
