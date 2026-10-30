-- ==============================================================================
-- FERROSTATS: ESQUEMA TRANSACCIONAL OPERATIVO (OLTP - 3FN CON RESTRICCIONES ACID)
-- Lead Architect: Diego Alejandro Escobar Barahona
-- Base de Datos: SQLite WAL Mode
-- ==============================================================================

PRAGMA foreign_keys = ON;

-- 1. Familias de Productos Ferreteros
CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY,
    category_code TEXT UNIQUE NOT NULL,
    category_name TEXT NOT NULL,
    target_margin_pct REAL NOT NULL CHECK (target_margin_pct >= 0 AND target_margin_pct <= 100)
);

-- 2. Proveedores Locales y Regionales
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INTEGER PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    lead_time_days INTEGER NOT NULL CHECK (lead_time_days >= 1),
    city TEXT NOT NULL
);

-- 3. Control de Acceso Basado en Roles (RBAC)
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('ADMIN', 'CAJERO', 'BODEGUERO')),
    pin TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

-- 4. Catálogo Maestro de Artículos SKU
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    sku TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    supplier_id INTEGER NOT NULL REFERENCES suppliers(supplier_id),
    unit_measure TEXT NOT NULL,
    unit_cost_usd REAL NOT NULL CHECK (unit_cost_usd > 0),
    unit_price_usd REAL NOT NULL CHECK (unit_price_usd >= unit_cost_usd),
    current_stock INTEGER NOT NULL CHECK (current_stock >= 0),
    min_stock INTEGER NOT NULL CHECK (min_stock >= 0),
    aisle_location TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_supplier ON products(supplier_id);

-- 5. Encabezado de Transacciones en Punto de Venta (POS)
CREATE TABLE IF NOT EXISTS sales (
    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_uuid TEXT UNIQUE NOT NULL,
    sale_timestamp TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    customer_type TEXT NOT NULL CHECK (customer_type IN ('CONSUMIDOR_FINAL', 'CONTRATISTA', 'TALLER_INDUSTRIAL')),
    payment_method TEXT NOT NULL CHECK (payment_method IN ('EFECTIVO', 'TRANSFERENCIA_QR', 'TARJETA')),
    total_cost_usd REAL NOT NULL CHECK (total_cost_usd >= 0),
    total_amount_usd REAL NOT NULL CHECK (total_amount_usd >= 0),
    gross_profit_usd REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sales_timestamp ON sales(sale_timestamp);
CREATE INDEX IF NOT EXISTS idx_sales_user ON sales(user_id);

-- 6. Detalle de Artículos por Venta
CREATE TABLE IF NOT EXISTS sale_items (
    sale_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL REFERENCES sales(sale_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_cost_snapshot_usd REAL NOT NULL,
    unit_price_snapshot_usd REAL NOT NULL,
    subtotal_usd REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sale_items_sale ON sale_items(sale_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_product ON sale_items(product_id);

-- 7. Bitácora Inmutable de Movimientos de Inventario (Auditoría)
CREATE TABLE IF NOT EXISTS inventory_movements (
    movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    movement_timestamp TEXT NOT NULL,
    product_id INTEGER NOT NULL REFERENCES products(product_id),
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    movement_type TEXT NOT NULL CHECK (movement_type IN ('VENTA_POS', 'INGRESO_PROVEEDOR', 'AJUSTE_AUDITORIA')),
    quantity_delta INTEGER NOT NULL,
    stock_before INTEGER NOT NULL,
    stock_after INTEGER NOT NULL CHECK (stock_after >= 0),
    reference_note TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_movements_product ON inventory_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_movements_timestamp ON inventory_movements(movement_timestamp);
