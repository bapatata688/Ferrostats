#!/usr/bin/env python3
"""
FERROSTATS: DEPLOY DATAFORM SILVER & GOLD MODELS TO GOOGLE BIGQUERY
Compiles and executes the Dataform SQLX Medallion transformations (Silver & Gold)
directly in Google BigQuery at $0.00 USD (Always Free Tier) so Looker Studio
can connect immediately to `ferrostats_gold`.
"""
import subprocess
import urllib.request
import urllib.error
import json
import os

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "ferrostats")
GCLOUD_CMD = os.path.expandvars(r"%LOCALAPPDATA%\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd")
if not os.path.exists(GCLOUD_CMD):
    GCLOUD_CMD = "gcloud"


def get_token() -> str:
    res = subprocess.run([GCLOUD_CMD, "auth", "print-access-token"], capture_output=True, text=True, check=True)
    return res.stdout.strip()


def run_bq_query(token: str, sql: str, description: str):
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT_ID}/queries"
    payload = {
        "query": sql,
        "useLegacySql": False,
        "location": "US"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("jobComplete"):
                print(f"[OK] {description}")
            else:
                print(f"[RUNNING] {description} (Job ID: {data.get('jobReference', {}).get('jobId')})")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"[ERROR] {description}: {e.code} -> {err_body}")
        raise


def main():
    print("=================================================================")
    print("  FERROSTATS: COMPILING DATAFORM MEDALLION MODELS IN BIGQUERY")
    print("  Silver Layer (Views) -> Gold Layer (Tables for Looker Studio)")
    print("=================================================================")
    token = get_token()

    # 1. SILVER: stg_products
    sql_stg_products = f"""
    CREATE OR REPLACE VIEW `{PROJECT_ID}.ferrostats_silver.stg_products` AS
    SELECT
      CAST(p.product_id AS INT64) AS product_id,
      TRIM(p.sku) AS sku,
      TRIM(p.product_name) AS product_name,
      CAST(p.category_id AS INT64) AS category_id,
      TRIM(c.category_code) AS category_code,
      TRIM(c.category_name) AS category_name,
      CAST(c.target_margin_pct AS FLOAT64) AS target_margin_pct,
      CAST(p.supplier_id AS INT64) AS supplier_id,
      TRIM(s.supplier_name) AS supplier_name,
      CAST(s.lead_time_days AS INT64) AS lead_time_days,
      TRIM(p.unit_measure) AS unit_measure,
      ROUND(CAST(p.unit_cost_usd AS FLOAT64), 2) AS unit_cost_usd,
      ROUND(CAST(p.unit_price_usd AS FLOAT64), 2) AS unit_price_usd,
      ROUND(CAST(p.unit_price_usd AS FLOAT64) - CAST(p.unit_cost_usd AS FLOAT64), 2) AS unit_margin_usd,
      CAST(p.current_stock AS INT64) AS current_stock,
      CAST(p.min_stock AS INT64) AS min_stock,
      TRIM(p.aisle_location) AS aisle_location,
      CASE
        WHEN CAST(p.current_stock AS INT64) = 0 THEN 'OUT_OF_STOCK'
        WHEN CAST(p.current_stock AS INT64) <= CAST(p.min_stock AS INT64) THEN 'LOW_STOCK'
        ELSE 'OPTIMAL'
      END AS stock_status
    FROM
      `{PROJECT_ID}.ferrostats_bronze.raw_products` p
    LEFT JOIN
      (SELECT * FROM `{PROJECT_ID}.ferrostats_bronze.raw_categories` QUALIFY ROW_NUMBER() OVER (PARTITION BY CAST(category_id AS INT64) ORDER BY category_id) = 1) c
      ON CAST(p.category_id AS INT64) = CAST(c.category_id AS INT64)
    LEFT JOIN
      (SELECT * FROM `{PROJECT_ID}.ferrostats_bronze.raw_suppliers` QUALIFY ROW_NUMBER() OVER (PARTITION BY CAST(supplier_id AS INT64) ORDER BY supplier_id) = 1) s
      ON CAST(p.supplier_id AS INT64) = CAST(s.supplier_id AS INT64)
    QUALIFY
      ROW_NUMBER() OVER (PARTITION BY CAST(p.product_id AS INT64) ORDER BY p.updated_at DESC) = 1;
    """
    run_bq_query(token, sql_stg_products, "Silver View: ferrostats_silver.stg_products")

    # 2. SILVER: stg_sales
    sql_stg_sales = f"""
    CREATE OR REPLACE VIEW `{PROJECT_ID}.ferrostats_silver.stg_sales` AS
    SELECT
      CAST(sale_id AS INT64) AS sale_id,
      TRIM(transaction_uuid) AS transaction_uuid,
      SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', sale_timestamp) AS sale_timestamp,
      DATE(SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', sale_timestamp)) AS sale_date,
      FORMAT_DATE('%Y-%m-%d', DATE(SAFE.PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', sale_timestamp))) AS date_key,
      CAST(user_id AS INT64) AS user_id,
      UPPER(TRIM(customer_type)) AS customer_type,
      UPPER(TRIM(payment_method)) AS payment_method,
      ROUND(CAST(total_cost_usd AS FLOAT64), 2) AS total_cost_usd,
      ROUND(CAST(total_amount_usd AS FLOAT64), 2) AS total_amount_usd,
      ROUND(CAST(gross_profit_usd AS FLOAT64), 2) AS gross_profit_usd,
      SAFE_DIVIDE(CAST(gross_profit_usd AS FLOAT64), NULLIF(CAST(total_amount_usd AS FLOAT64), 0)) * 100.0 AS margin_pct
    FROM
      `{PROJECT_ID}.ferrostats_bronze.raw_sales`
    WHERE
      sale_id IS NOT NULL
    QUALIFY
      ROW_NUMBER() OVER (PARTITION BY CAST(sale_id AS INT64) ORDER BY sale_timestamp DESC) = 1;
    """
    run_bq_query(token, sql_stg_sales, "Silver View: ferrostats_silver.stg_sales")

    # 3. SILVER: stg_sale_items
    sql_stg_sale_items = f"""
    CREATE OR REPLACE VIEW `{PROJECT_ID}.ferrostats_silver.stg_sale_items` AS
    SELECT
      CAST(si.sale_item_id AS INT64) AS sale_item_id,
      CAST(si.sale_id AS INT64) AS sale_id,
      CAST(si.product_id AS INT64) AS product_id,
      CAST(si.quantity AS INT64) AS quantity,
      ROUND(CAST(si.unit_cost_snapshot_usd AS FLOAT64), 2) AS unit_cost_usd,
      ROUND(CAST(si.unit_price_snapshot_usd AS FLOAT64), 2) AS unit_price_usd,
      ROUND(CAST(si.subtotal_usd AS FLOAT64), 2) AS subtotal_usd,
      ROUND(CAST(si.quantity AS INT64) * CAST(si.unit_cost_snapshot_usd AS FLOAT64), 2) AS item_cogs_usd,
      ROUND(CAST(si.subtotal_usd AS FLOAT64) - (CAST(si.quantity AS INT64) * CAST(si.unit_cost_snapshot_usd AS FLOAT64)), 2) AS item_profit_usd
    FROM
      `{PROJECT_ID}.ferrostats_bronze.raw_sale_items` si
    WHERE
      si.sale_item_id IS NOT NULL
    QUALIFY
      ROW_NUMBER() OVER (PARTITION BY CAST(si.sale_item_id AS INT64) ORDER BY si.sale_item_id DESC) = 1;
    """
    run_bq_query(token, sql_stg_sale_items, "Silver View: ferrostats_silver.stg_sale_items")

    # 4. GOLD: fct_daily_sales
    sql_fct_daily_sales = f"""
    CREATE OR REPLACE TABLE `{PROJECT_ID}.ferrostats_gold.fct_daily_sales` AS
    WITH daily_sales_base AS (
      SELECT
        s.date_key,
        s.sale_date,
        p.category_code,
        p.category_name,
        COUNT(DISTINCT s.sale_id) AS total_transactions,
        SUM(si.quantity) AS units_sold,
        ROUND(SUM(si.subtotal_usd), 2) AS gross_revenue_usd,
        ROUND(SUM(si.item_cogs_usd), 2) AS cogs_usd,
        ROUND(SUM(si.item_profit_usd), 2) AS gross_profit_usd
      FROM
        `{PROJECT_ID}.ferrostats_silver.stg_sales` s
      INNER JOIN
        `{PROJECT_ID}.ferrostats_silver.stg_sale_items` si ON s.sale_id = si.sale_id
      INNER JOIN
        `{PROJECT_ID}.ferrostats_silver.stg_products` p ON si.product_id = p.product_id
      GROUP BY
        1, 2, 3, 4
    )
    SELECT
      date_key,
      sale_date,
      category_code,
      category_name,
      total_transactions,
      units_sold,
      gross_revenue_usd,
      cogs_usd,
      gross_profit_usd,
      ROUND(SAFE_DIVIDE(gross_profit_usd, NULLIF(gross_revenue_usd, 0)) * 100.0, 2) AS gross_margin_pct,
      CURRENT_TIMESTAMP() AS etl_updated_at
    FROM
      daily_sales_base
    ORDER BY
      date_key DESC, gross_revenue_usd DESC;
    """
    run_bq_query(token, sql_fct_daily_sales, "Gold Table: ferrostats_gold.fct_daily_sales")

    # 5. GOLD: mart_inventory_pareto_abc
    sql_mart_pareto = f"""
    CREATE OR REPLACE TABLE `{PROJECT_ID}.ferrostats_gold.mart_inventory_pareto_abc` AS
    WITH sales_30d AS (
      SELECT
        si.product_id,
        SUM(si.quantity) AS units_sold_30d,
        ROUND(SUM(si.subtotal_usd), 2) AS revenue_30d_usd,
        ROUND(SUM(si.item_profit_usd), 2) AS profit_30d_usd
      FROM
        `{PROJECT_ID}.ferrostats_silver.stg_sale_items` si
      GROUP BY
        1
    ),
    products_base AS (
      SELECT
        p.product_id,
        p.sku,
        p.product_name,
        p.category_code,
        p.category_name,
        p.supplier_name,
        p.lead_time_days,
        p.aisle_location,
        p.unit_measure,
        p.unit_cost_usd,
        p.unit_price_usd,
        p.current_stock,
        p.min_stock,
        p.stock_status,
        COALESCE(v.units_sold_30d, 0) AS units_sold_30d,
        COALESCE(v.revenue_30d_usd, 0.0) AS revenue_30d_usd,
        COALESCE(v.profit_30d_usd, 0.0) AS profit_30d_usd
      FROM
        `{PROJECT_ID}.ferrostats_silver.stg_products` p
      LEFT JOIN
        sales_30d v ON p.product_id = v.product_id
    ),
    pareto_calc AS (
      SELECT
        b.*,
        SUM(b.revenue_30d_usd) OVER() AS total_revenue_all,
        SUM(b.revenue_30d_usd) OVER(
          ORDER BY b.revenue_30d_usd DESC, b.units_sold_30d DESC, b.product_id ASC
          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_revenue
      FROM
        products_base b
    ),
    pareto_enriched AS (
      SELECT
        pc.*,
        ROUND(SAFE_DIVIDE(pc.running_revenue, NULLIF(pc.total_revenue_all, 0)) * 100.0, 2) AS cumulative_rev_pct,
        ROUND(pc.units_sold_30d / 30.0, 3) AS daily_burn_rate
      FROM
        pareto_calc pc
    )
    SELECT
      product_id,
      sku,
      product_name,
      category_code,
      category_name,
      supplier_name,
      lead_time_days,
      aisle_location,
      unit_measure,
      unit_cost_usd,
      unit_price_usd,
      current_stock,
      min_stock,
      stock_status,
      units_sold_30d,
      revenue_30d_usd,
      profit_30d_usd,
      cumulative_rev_pct,
      CASE
        WHEN cumulative_rev_pct <= 80.0 THEN 'A'
        WHEN cumulative_rev_pct <= 95.0 THEN 'B'
        ELSE 'C'
      END AS abc_class,
      daily_burn_rate,
      CASE
        WHEN daily_burn_rate > 0 THEN ROUND(current_stock / daily_burn_rate, 1)
        ELSE 999.0
      END AS days_of_inventory_left,
      CASE
        WHEN current_stock <= min_stock THEN GREATEST(
          CAST(min_stock + CEIL(daily_burn_rate * lead_time_days) + CEIL(daily_burn_rate * 15) - current_stock AS INT64),
          min_stock,
          5
        )
        ELSE 0
      END AS recommended_reorder_qty,
      ROUND(current_stock * unit_cost_usd, 2) AS inventory_valuation_cost_usd,
      ROUND(current_stock * unit_price_usd, 2) AS inventory_valuation_retail_usd,
      CURRENT_TIMESTAMP() AS etl_updated_at
    FROM
      pareto_enriched
    ORDER BY
      revenue_30d_usd DESC;
    """
    run_bq_query(token, sql_mart_pareto, "Gold Table: ferrostats_gold.mart_inventory_pareto_abc")

    # 6. GOLD: dim_products
    sql_dim_products = f"""
    CREATE OR REPLACE TABLE `{PROJECT_ID}.ferrostats_gold.dim_products` AS
    SELECT
      product_id,
      sku,
      product_name,
      category_id,
      category_code,
      category_name,
      target_margin_pct,
      supplier_id,
      supplier_name,
      lead_time_days,
      unit_measure,
      unit_cost_usd,
      unit_price_usd,
      unit_margin_usd,
      ROUND(SAFE_DIVIDE(unit_margin_usd, NULLIF(unit_price_usd, 0)) * 100.0, 2) AS catalog_margin_pct,
      current_stock,
      min_stock,
      aisle_location,
      stock_status
    FROM
      `{PROJECT_ID}.ferrostats_silver.stg_products`;
    """
    run_bq_query(token, sql_dim_products, "Gold Table: ferrostats_gold.dim_products")

    # 7. Clean up legacy Spanish Gold tables so only canonical English tables remain
    for old_table in ("fct_ventas_diarias", "mart_inventario_pareto_abc", "dim_productos", "dw_fact_daily_sales", "dw_mart_product_abc_health"):
        run_bq_query(
            token,
            f"DROP TABLE IF EXISTS `{PROJECT_ID}.ferrostats_gold.{old_table}`;",
            f"Cleanup Legacy Gold Table: ferrostats_gold.{old_table}"
        )

    print("=================================================================")
    print("  [SUCCESS] GOLD & SILVER MEDALLION MODELS READY FOR LOOKER STUDIO!")
    print("  Tables available in `ferrostats.ferrostats_gold`:")
    print("    1. fct_daily_sales")
    print("    2. mart_inventory_pareto_abc")
    print("    3. dim_products")
    print("=================================================================")


if __name__ == "__main__":
    main()
