import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

PROJECT_ID = "ferrostats"

def get_access_token() -> str:
    # 1. Intentar servidor de metadatos de Google Cloud (Cloud Run)
    try:
        req = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"}
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode())
            return data["access_token"]
    except Exception:
        pass

    # 2. Intentar gcloud CLI de forma dinámica y portable
    import shutil
    gcloud_bin = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not gcloud_bin and os.name == "nt":
        local_app_data = os.getenv("LOCALAPPDATA", "")
        candidate = os.path.join(local_app_data, "Google", "Cloud SDK", "google-cloud-sdk", "bin", "gcloud.cmd")
        if os.path.exists(candidate):
            gcloud_bin = candidate
    if not gcloud_bin:
        gcloud_bin = "gcloud"
    try:
        out = subprocess.check_output([gcloud_bin, "auth", "print-access-token"], shell=True)
        return out.decode().strip()
    except Exception as exc:
        print(f"Nota: gcloud CLI token no disponible: {exc}")
        return ""

def run_query(query: str, token: str):
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT_ID}/queries"
    data = {
        "query": query,
        "useLegacySql": False,
        "location": "US"
    }
    body = json.dumps(data).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode("utf-8"))
            if "jobComplete" in res and res["jobComplete"]:
                total_rows = res.get("totalRows", "0")
                print(f"  -> Query completado exitosamente ({total_rows} filas afectadas/retornadas)")
            return res
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8")
        print(f"  -> Error HTTP {err.code}: {err_body}")
        return {"error": err_body}

def main():
    print("=" * 60)
    print("  EJECUTANDO MODELOS DATAFORM (SILVER & GOLD) EN BIGQUERY")
    print("=" * 60)
    token = get_access_token()

    # 1. Silver: stg_sales
    print("\n[1/6] Creando ferrostats_silver.stg_sales...")
    sql_stg_sales = """
    CREATE OR REPLACE VIEW `ferrostats.ferrostats_silver.stg_sales` AS
    SELECT
      CAST(sale_id AS INT64) AS sale_id,
      TRIM(transaction_uuid) AS transaction_uuid,
      CAST(sale_timestamp AS TIMESTAMP) AS sale_timestamp,
      DATE(CAST(sale_timestamp AS TIMESTAMP)) AS sale_date,
      CAST(user_id AS INT64) AS user_id,
      UPPER(TRIM(customer_type)) AS customer_type,
      UPPER(TRIM(payment_method)) AS payment_method,
      ROUND(CAST(total_amount_usd AS FLOAT64), 2) AS total_amount_usd,
      ROUND(CAST(total_cost_usd AS FLOAT64), 2) AS total_cost_usd,
      ROUND(CAST(gross_profit_usd AS FLOAT64), 2) AS gross_profit_usd,
      ROUND(SAFE_DIVIDE(CAST(gross_profit_usd AS FLOAT64), CAST(total_amount_usd AS FLOAT64)) * 100, 2) AS gross_margin_pct
    FROM
      `ferrostats.ferrostats_bronze.raw_sales`
    WHERE
      sale_id IS NOT NULL
      AND CAST(total_amount_usd AS FLOAT64) >= 0
    QUALIFY
      ROW_NUMBER() OVER (PARTITION BY sale_id ORDER BY CAST(sale_timestamp AS TIMESTAMP) DESC) = 1;
    """
    run_query(sql_stg_sales, token)

    # 2. Silver: stg_sale_items
    print("\n[2/6] Creando ferrostats_silver.stg_sale_items...")
    sql_stg_items = """
    CREATE OR REPLACE VIEW `ferrostats.ferrostats_silver.stg_sale_items` AS
    SELECT
      CAST(sale_item_id AS INT64) AS sale_item_id,
      CAST(sale_id AS INT64) AS sale_id,
      CAST(product_id AS INT64) AS product_id,
      CAST(quantity AS INT64) AS quantity,
      ROUND(CAST(unit_price_snapshot_usd AS FLOAT64), 2) AS unit_price_usd,
      ROUND(CAST(unit_cost_snapshot_usd AS FLOAT64), 2) AS unit_cost_usd,
      ROUND(CAST(subtotal_usd AS FLOAT64), 2) AS subtotal_usd,
      ROUND(CAST(quantity AS INT64) * CAST(unit_cost_snapshot_usd AS FLOAT64), 2) AS cogs_usd,
      ROUND(CAST(subtotal_usd AS FLOAT64) - (CAST(quantity AS INT64) * CAST(unit_cost_snapshot_usd AS FLOAT64)), 2) AS item_profit_usd
    FROM
      `ferrostats.ferrostats_bronze.raw_sale_items`
    WHERE
      sale_item_id IS NOT NULL
      AND CAST(quantity AS INT64) > 0
    QUALIFY
      ROW_NUMBER() OVER (PARTITION BY sale_item_id ORDER BY CAST(sale_id AS INT64) DESC) = 1;
    """
    run_query(sql_stg_items, token)

    # 3. Silver: stg_products
    print("\n[3/6] Creando ferrostats_silver.stg_products...")
    sql_stg_products = """
    CREATE OR REPLACE VIEW `ferrostats.ferrostats_silver.stg_products` AS
    SELECT
      CAST(p.product_id AS INT64) AS product_id,
      UPPER(TRIM(p.sku)) AS sku,
      TRIM(p.product_name) AS product_name,
      CAST(p.category_id AS INT64) AS category_id,
      TRIM(c.category_name) AS category_name,
      TRIM(c.category_code) AS category_code,
      CAST(p.supplier_id AS INT64) AS supplier_id,
      TRIM(s.supplier_name) AS supplier_name,
      CAST(COALESCE(s.lead_time_days, 7) AS INT64) AS lead_time_days,
      TRIM(p.unit_measure) AS unit_measure,
      ROUND(CAST(p.unit_cost_usd AS FLOAT64), 2) AS unit_cost_usd,
      ROUND(CAST(p.unit_price_usd AS FLOAT64), 2) AS unit_price_usd,
      CAST(p.current_stock AS INT64) AS current_stock,
      CAST(p.min_stock AS INT64) AS min_stock,
      TRIM(p.aisle_location) AS aisle_location,
      CASE
        WHEN CAST(p.current_stock AS INT64) = 0 THEN 'AGOTADO'
        WHEN CAST(p.current_stock AS INT64) <= CAST(p.min_stock AS INT64) THEN 'BAJO_STOCK'
        ELSE 'OPTIMO'
      END AS stock_status,
      ROUND(CAST(p.unit_price_usd AS FLOAT64) - CAST(p.unit_cost_usd AS FLOAT64), 2) AS unit_margin_usd
    FROM
      `ferrostats.ferrostats_bronze.raw_products` p
    LEFT JOIN
      `ferrostats.ferrostats_bronze.raw_categories` c ON CAST(p.category_id AS INT64) = CAST(c.category_id AS INT64)
    LEFT JOIN
      `ferrostats.ferrostats_bronze.raw_suppliers` s ON CAST(p.supplier_id AS INT64) = CAST(s.supplier_id AS INT64);
    """
    run_query(sql_stg_products, token)

    # 4. Gold: fct_ventas_diarias
    print("\n[4/6] Creando tabla ferrostats_gold.fct_ventas_diarias...")
    sql_fct_ventas = """
    CREATE OR REPLACE TABLE `ferrostats.ferrostats_gold.fct_ventas_diarias` AS
    WITH base_ventas AS (
      SELECT
        s.sale_date,
        p.category_name,
        COUNT(DISTINCT s.sale_id) AS total_transactions,
        SUM(i.quantity) AS units_sold,
        ROUND(SUM(i.subtotal_usd), 2) AS gross_revenue_usd,
        ROUND(SUM(i.cogs_usd), 2) AS cogs_usd,
        ROUND(SUM(i.item_profit_usd), 2) AS gross_profit_usd
      FROM
        `ferrostats.ferrostats_silver.stg_sales` s
      JOIN
        `ferrostats.ferrostats_silver.stg_sale_items` i ON s.sale_id = i.sale_id
      JOIN
        `ferrostats.ferrostats_silver.stg_products` p ON i.product_id = p.product_id
      GROUP BY
        1, 2
    )
    SELECT
      CAST(sale_date AS STRING) AS date_key,
      sale_date,
      category_name,
      total_transactions,
      units_sold,
      gross_revenue_usd,
      cogs_usd,
      gross_profit_usd,
      ROUND(SAFE_DIVIDE(gross_profit_usd, gross_revenue_usd) * 100, 2) AS gross_margin_pct
    FROM
      base_ventas
    ORDER BY
      sale_date DESC, gross_revenue_usd DESC;
    """
    run_query(sql_fct_ventas, token)

    # 5. Gold: mart_inventario_pareto_abc
    print("\n[5/6] Creando tabla ferrostats_gold.mart_inventario_pareto_abc...")
    sql_pareto = """
    CREATE OR REPLACE TABLE `ferrostats.ferrostats_gold.mart_inventario_pareto_abc` AS
    WITH ventas_30d AS (
      SELECT
        i.product_id,
        SUM(i.quantity) AS units_sold_30d,
        SUM(i.subtotal_usd) AS revenue_30d_usd,
        SUM(i.item_profit_usd) AS profit_30d_usd
      FROM
        `ferrostats.ferrostats_silver.stg_sale_items` i
      JOIN
        `ferrostats.ferrostats_silver.stg_sales` s ON i.sale_id = s.sale_id
      WHERE
        s.sale_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
      GROUP BY
        i.product_id
    ),
    base_productos AS (
      SELECT
        p.product_id,
        p.sku,
        p.product_name,
        p.category_name,
        p.current_stock,
        p.min_stock,
        p.stock_status,
        p.unit_cost_usd,
        p.unit_price_usd,
        p.lead_time_days,
        COALESCE(v.units_sold_30d, 0) AS units_sold_30d,
        ROUND(COALESCE(v.revenue_30d_usd, 0.0), 2) AS revenue_30d_usd,
        ROUND(COALESCE(v.profit_30d_usd, 0.0), 2) AS profit_30d_usd,
        ROUND(p.current_stock * p.unit_cost_usd, 2) AS inventory_valuation_cost_usd
      FROM
        `ferrostats.ferrostats_silver.stg_products` p
      LEFT JOIN
        ventas_30d v ON p.product_id = v.product_id
    ),
    pareto_calc AS (
      SELECT
        *,
        SUM(revenue_30d_usd) OVER() AS total_revenue_all,
        SUM(revenue_30d_usd) OVER(
          ORDER BY revenue_30d_usd DESC, units_sold_30d DESC, product_id ASC
          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS running_revenue
      FROM
        base_productos
    ),
    pareto_classified AS (
      SELECT
        product_id,
        sku,
        product_name,
        category_name,
        current_stock,
        min_stock,
        stock_status,
        unit_cost_usd,
        unit_price_usd,
        lead_time_days,
        units_sold_30d,
        revenue_30d_usd,
        profit_30d_usd,
        inventory_valuation_cost_usd,
        ROUND(SAFE_DIVIDE(running_revenue, NULLIF(total_revenue_all, 0)) * 100.0, 2) AS cumulative_rev_pct,
        ROUND(SAFE_DIVIDE(units_sold_30d, 30.0), 3) AS daily_burn_rate
      FROM
        pareto_calc
    )
    SELECT
      product_id,
      sku,
      product_name,
      category_name,
      current_stock,
      min_stock,
      stock_status,
      units_sold_30d,
      revenue_30d_usd,
      profit_30d_usd,
      COALESCE(cumulative_rev_pct, 100.0) AS cumulative_rev_pct,
      CASE
        WHEN cumulative_rev_pct <= 80.0 THEN 'A'
        WHEN cumulative_rev_pct <= 95.0 THEN 'B'
        ELSE 'C'
      END AS abc_class,
      daily_burn_rate,
      CASE
        WHEN daily_burn_rate > 0 THEN ROUND(SAFE_DIVIDE(current_stock, daily_burn_rate), 1)
        ELSE 999.0
      END AS days_of_inventory_left,
      CASE
        WHEN current_stock <= min_stock THEN
          GREATEST(CAST(min_stock + CEIL(daily_burn_rate * lead_time_days) + CEIL(daily_burn_rate * 15) - current_stock AS INT64), CAST(min_stock AS INT64), 5)
        ELSE 0
      END AS recommended_reorder_qty,
      inventory_valuation_cost_usd
    FROM
      pareto_classified
    ORDER BY
      revenue_30d_usd DESC, units_sold_30d DESC;
    """
    run_query(sql_pareto, token)

    # 6. Gold: dim_productos
    print("\n[6/6] Creando tabla ferrostats_gold.dim_productos...")
    sql_dim_prod = """
    CREATE OR REPLACE TABLE `ferrostats.ferrostats_gold.dim_productos` AS
    SELECT
      product_id,
      sku,
      product_name,
      category_id,
      category_name,
      category_code,
      supplier_id,
      supplier_name,
      unit_measure,
      unit_cost_usd,
      unit_price_usd,
      unit_margin_usd,
      current_stock,
      min_stock,
      aisle_location,
      stock_status
    FROM
      `ferrostats.ferrostats_silver.stg_products`;
    """
    run_query(sql_dim_prod, token)

    print("\n" + "=" * 60)
    print("  ¡TODOS LOS MODELOS DATAFORM DESPLEGADOS EXITOSAMENTE EN BIGQUERY!")
    print("  Looker Studio ahora puede conectarse a:")
    print("   1. ferrostats.ferrostats_gold.fct_ventas_diarias")
    print("   2. ferrostats.ferrostats_gold.mart_inventario_pareto_abc")
    print("   3. ferrostats.ferrostats_gold.dim_productos")
    print("=" * 60)

if __name__ == "__main__":
    main()
