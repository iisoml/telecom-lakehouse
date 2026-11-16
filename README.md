# Telecom Data Automation Platform

A medallion lakehouse (bronze → silver → gold) for synthetic telecom data. It has data
contracts, a quarantine zone for bad rows, dbt marts, quality gates, observability, and an
Azure ADLS Gen2 backend provisioned with Terraform.

I built it step by step as a data engineering portfolio project.

## Architecture

```
generators (towers + CDRs, optional "chaos")
        │
        ▼
 bronze  ── Delta Lake, append-only, raw
        │
        ▼
 data contracts (lakehouse/quality.py)
   │                         │
   ▼                         ▼
 silver (Delta, MERGE     quarantine (Delta, one
 on call_sid)             reject_reason per row)
   │
   ▼
 dbt on DuckDB ──► gold: customer_360, mart_churn_risk
   │
 quality gates: reject rate ≤ 5% and dbt tests pass, otherwise gold is NOT published
```

Storage is switchable. By default the lake is local folders under `data/`. With
`LAKE_BACKEND=azure` the same code reads and writes Azure Data Lake Storage Gen2.

## Stack

- Python 3.12, uv, pandas, numpy, pyarrow
- Delta Lake (`deltalake`) for bronze, silver and quarantine tables
- DuckDB and dbt (`dbt-duckdb`) for the gold marts and tests
- OpenTelemetry (spans) and OpenLineage-style events (`data/lineage.jsonl`)
- Terraform (`azurerm`) and Azure ADLS Gen2
- pytest, ruff, GitHub Actions

## Project structure

```
ingestion/        synthetic data generators (towers, CDRs, chaos injection)
lakehouse/
  storage.py      where tables live (local or Azure)
  bronze.py       append-only landing with _batch_id and _ingested_at
  quality.py      data contracts, standardisation, dedupe, quarantine split
  silver.py       contract check + MERGE into silver
  observability.py  OpenTelemetry spans and lineage events
dbt/              dbt project (staging view, customer_360, mart_churn_risk, tests)
infra/            Terraform for the Azure storage account and containers
tests/            pytest suite
run_bronze.py     demo: generate and land in bronze
run_pipeline.py   full pipeline with quality gates
stream_sim.py     simulated micro-batch stream
```

## Design decisions

- **One shared tower registry.** Feeds that invent their own tower IDs break joins, so every
  feed picks towers from a single `generate_towers()` registry.
- **Bronze is append-only.** Raw data is never modified, so any later step can be replayed.
  Running a load twice doubles the rows on purpose.
- **Bad rows are quarantined, not dropped.** Each rejected row keeps a `reject_reason`, so
  data quality problems stay visible.
- **Silver is idempotent.** It uses a MERGE on the business key `call_sid`, so re-running a
  batch changes nothing. A test covers this.
- **Gold is gated.** Publishing is blocked when the contract reject rate exceeds 5% or any
  dbt test fails.
- **Keyless Azure access.** Shared keys are disabled on the storage account. Access goes
  through Azure AD and a role assignment.

## Data contracts

Rules applied in `lakehouse/quality.py`:

| Rule | Action |
|---|---|
| `duration_seconds < 0` | reject (`negative_duration`) |
| null `cell_tower_id` | reject (`null_tower`) |
| tower not in the registry | reject (`unknown_tower`) |
| invalid `call_type` or `network_type` | reject |
| null `start_time` | reject |
| SMS with a non-zero duration | reject |
| `LTE` | standardised to `4G` |
| duplicate `call_sid` | deduplicated, latest ingest wins |

## Run it locally

```bash
uv sync
uv run pytest
uv run python run_pipeline.py 0.02   # 2% chaos: passes, gold published
uv run python run_pipeline.py 0.2    # 20% chaos: gate fails, gold blocked
```

The number is the `chaos` rate, the share of rows deliberately corrupted (negative
durations, null towers, replayed duplicates).

## Results

| Run | Bronze rows | Rejected | Reject rate | Outcome |
|---|---|---|---|---|
| chaos 0.02 | [fill] | [fill] | [fill] | gold published |
| chaos 0.20 | [fill] | [fill] | [fill] | gate failed, dbt skipped |



## Observability

Each pipeline step runs inside an OpenTelemetry span with row counts and reject rates as
attributes. It also writes START, COMPLETE or FAIL lineage events (OpenLineage format) to
`data/lineage.jsonl`.

## Deploy to Azure

`infra/` creates a resource group, an ADLS Gen2 storage account with `bronze`, `silver`,
`gold` and `quarantine` containers, and a role assignment for the signed-in user.

```bash
az login
cd infra
terraform init
terraform apply
cd ..

set LAKE_BACKEND=azure
set AZURE_STORAGE_ACCOUNT=<storage_account from terraform output>
uv run python run_bronze.py
uv run python -c "from lakehouse.silver import build_silver_cdr; print(build_silver_cdr())"
```

When finished: `cd infra && terraform destroy`.


Region note: the subscription I used only allows a small set of regions, so the Terraform
default is `francecentral`. Change `location` in `infra/main.tf` if your subscription differs.

Current limitation: dbt reads the local silver copy. Reading directly from ADLS through
DuckDB's `azure` extension is a next step.

## Tests

`uv run pytest` covers the generators (shared registry, reproducible seed, chaos),
append-only bronze, contract behaviour, idempotent silver MERGE, and the reject rate
scaling with chaos.

## Possible next steps

- Event Hubs ingestion instead of the micro-batch simulator
- dbt on ADLS data with the DuckDB `azure` extension
- Orchestration with Airflow or Azure Data Factory
- Using the churn mart as the input for a model