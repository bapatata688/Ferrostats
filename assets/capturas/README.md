# FERROSTATS — Data Platform Visual Assets & Screenshots

Production screenshots and vector architectural diagrams of the **FERROSTATS** Medallion Data Lakehouse running live on **Google Cloud Platform (GCP)**.

| Filename | Layer / Scope | Description |
|---|---|---|
| `architecture_flow_en.png` | **End-to-End Architecture (EN)** | 5-Stage Cloud Data Engineering Infographic (`1920x1071`): Edge POS Producer $\to$ Serverless Compute (Cloud Run + SQLite WAL) $\to$ BigQuery Streaming API $\to$ Medallion Lakehouse (Bronze / Silver Dataform SQLX / Gold Star Schema & Pareto 80/20) $\to$ Looker Studio BI |
| `arquitectura_gcp_end_to_end.svg` | **End-to-End Architecture (ES)** | Diagrama vectorial en español del pipeline Medallón end-to-end y arquitectura serverless en GCP |
| `compiled_dag.png` | **Google Cloud Dataform** | Compiled SQLX dependency graph (`raw_*` $\to$ `stg_*` $\to$ `dim_products`, `fct_daily_sales`, `mart_inventory_pareto_abc` & Data Quality assertions) |
| `datasets_bigquery.png` | **Google BigQuery** | BigQuery Explorer showing `ferrostats_bronze` (7 raw tables), `ferrostats_silver` (3 views), and `ferrostats_gold` (3 Star Schema marts) |
| `looker_studio_1.png` | **Looker Studio BI (Page 1)** | Executive Revenue, COGS, and Gross Margin evolution powered by `ferrostats_gold.fct_daily_sales` |
| `looker_studio_2.png` | **Looker Studio BI (Page 2)** | Dynamic 80/20 Pareto ABC Matrix, Stock Status, Burn Rate, and Days of Inventory (DOI) powered by `ferrostats_gold.mart_inventory_pareto_abc` |
| `looker_studio_3.png` | **Looker Studio BI (Page 3)** | Working Capital Valuation & SKU Distribution by ABC Class powered by `dim_products` and `mart_inventory_pareto_abc` |
| `ferrostats_pos.png` | **Upstream OLTP Source A (`/pos`)** | Synthetic POS checkout event producer streaming sales transactions into `ferrostats_bronze.raw_sales` |
| `ferrostats_warehouse.png` | **Upstream OLTP Source B (`/`)** | Physical warehouse aisle audit view streaming stock adjustments into `ferrostats_bronze.raw_inventory_movements` |
