---
name: data-pipeline-drift
description: "ONLY trigger when the user explicitly types /data-pipeline-drift. Detects data drift in parquet pipeline outputs across ds= partitions or environments by exploring the actual data, then diagnoses root causes."
---

# Data Pipeline Drift Detection

Detect and diagnose data drift in the medallion pipeline by loading parquet files from S3, exploring their structure, and comparing across `ds=` dates or environments.

## Prerequisites

```bash
conda activate dp
```

Project root: `~/codes/data_pipeline/`

## Step 1: Determine What to Compare

Ask the user for:
- **Client name** (e.g., `sheko-group`, `blackroll`)
- **Layer and entity** (e.g., gold/sales, platinum/stock_data)
- **Comparison type**: date-vs-date, prod-vs-dev 

## Step 2: Explore the Data

Build S3 paths using `build_simple_path` from `data_pipeline.io.s3_keys`:

```python
from data_pipeline.io.s3_keys import build_simple_path

path = build_simple_path(
    bucket="bucket-name-{env}", customer="{client}",
    layer="{layer}", entity="{entity}", schema_version=1, ds=date(...)
)
```

Sample path format: `s3://bucket-name-{env}/{client}/{layer}/v{version}/{entity}/ds={YYYY-MM-DD}/{entity}.parquet`

Load the parquet files and **inspect them before comparing**:
- Schema (column names, dtypes)
- Row count
- Sample rows
- Null rates per column
- Value distributions for key columns

Understanding the shape of the data first is essential — the comparison approach (join columns, tolerance, which columns matter) depends on what the data actually looks like.

## Step 3: Compare

Use `TableComparer` from `data_pipeline.io.table_compare` for the comparison. Choose join columns based on what you observed in Step 2 — look for natural keys (IDs, dates, composite keys) rather than guessing.

```python
from data_pipeline.io.table_compare import TableComparer

comparer = TableComparer(
    df1=df_a, df2=df_b,
    join_columns=[...],  # determined from data exploration
    df1_name="...", df2_name="...",
)
result = comparer.compare()
comparer.report(html_file="drift_report.html")
```

## Step 4: Diagnose

Read the comparison output and present a summary table, then diagnose root causes in this order:

1. **Row count change** — New/removed rows suggest upstream source changes (new products, deactivated SKUs, SRF config change). Check `settings.source_accounts_config`.
2. **Column schema change** — Missing or added columns point to a schema version bump or code change. Check git log for the relevant transform and model files.
3. **Value drift in specific columns** — Identify which columns have mismatches:
   - Numeric columns (`quantity`, `price`, `demand`) → upstream data change or rounding logic
   - ID columns (`variant_id`, `variant_asin`) 
   - Date/time columns → timezone or parsing change

Present the diagnosis with specific file paths and git commits when possible.
