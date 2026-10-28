-- ==============================================================================
-- FERROSTATS: ESQUEMA ANALÍTICO DIMENSIONAL (OLAP - STAR SCHEMA & DATA MARTS)
-- Lead Architect: Diego Alejandro Escobar Barahona
-- Base de Datos: SQLite WAL Mode / Data Mart Local
-- ==============================================================================

-- 1. Tabla de Hechos: Agregación Diaria de Ventas por Familia Ferretera
CREATE TABLE IF NOT EXISTS dw_fact_daily_sales (
    date_key TEXT NOT NULL,
    category_code TEXT NOT NULL,
    total_transactions INTEGER NOT NULL,
    units_sold INTEGER NOT NULL,
    gross_revenue_usd REAL NOT NULL,
    cogs_usd REAL NOT NULL,
    gross_profit_usd REAL NOT NULL,
    gross_margin_pct REAL NOT NULL,
    PRIMARY KEY (date_key, category_code)
);

CREATE INDEX IF NOT EXISTS idx_dw_fact_date ON dw_fact_daily_sales(date_key);
CREATE INDEX IF NOT EXISTS idx_dw_fact_category ON dw_fact_daily_sales(category_code);

-- 2. Data Mart de Salud de Inventario y Clasificación ABC de Pareto
CREATE TABLE IF NOT EXISTS dw_mart_product_abc_health (
    product_id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL,
    product_name TEXT NOT NULL,
    category_name TEXT NOT NULL,
    current_stock INTEGER NOT NULL,
    min_stock INTEGER NOT NULL,
    stock_status TEXT NOT NULL CHECK (stock_status IN ('OPTIMO', 'BAJO_STOCK', 'AGOTADO')),
    units_sold_30d INTEGER NOT NULL,
    revenue_30d_usd REAL NOT NULL,
    profit_30d_usd REAL NOT NULL,
    cumulative_rev_pct REAL NOT NULL,
    abc_class TEXT NOT NULL CHECK (abc_class IN ('A', 'B', 'C')),
    daily_burn_rate REAL NOT NULL,
    days_of_inventory_left REAL NOT NULL,
    recommended_reorder_qty INTEGER NOT NULL,
    inventory_valuation_cost_usd REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dw_mart_sku ON dw_mart_product_abc_health(sku);
CREATE INDEX IF NOT EXISTS idx_dw_mart_abc ON dw_mart_product_abc_health(abc_class);
CREATE INDEX IF NOT EXISTS idx_dw_mart_status ON dw_mart_product_abc_health(stock_status);

-- 3. Tabla de Observabilidad, Calidad de Datos (DQ) y Linaje del Pipeline ETL
CREATE TABLE IF NOT EXISTS dw_etl_audit_log (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp TEXT NOT NULL,
    trigger_source TEXT NOT NULL,
    rows_extracted INTEGER NOT NULL,
    dq_checks_passed INTEGER NOT NULL,
    dq_checks_failed INTEGER NOT NULL,
    execution_time_ms REAL NOT NULL,
    status TEXT NOT NULL,
    summary_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dw_etl_timestamp ON dw_etl_audit_log(run_timestamp);
