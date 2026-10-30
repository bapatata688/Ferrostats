# SPEC 02 (Commit 2): Modelo de Datos (OLTP 3FN + OLAP Estrella) y Dataset Sintético

## Metadatos del Commit
| Atributo | Detalle |
| :--- | :--- |
| **Fase** | Fase 2 — Modelado Relacional ACID, Esquema Analítico Estrella y Semilla de Datos Sintéticos |
| **Enfoque de Perfil** | Data Modeling (3FN vs. Dimensional Star Schema) e Ingesta de Datos Semilla |
| **Archivos que Antigravity generará en esta fase** | `app/db/schema_oltp.sql`, `app/db/schema_olap.sql`, `data/seeds/*.csv` y script de carga inicial `app/db/seed_loader.py` |
| **Mensaje de Commit Sugerido** | `feat(data-model): define 3NF OLTP schema, OLAP star schema, and realistic hardware store synthetic dataset` |

## 1. Especificación del Esquema Transaccional Operativo (OLTP — 3FN)

El motor transaccional debe activar claves foráneas (`PRAGMA foreign_keys = ON;`) y modo de escritura concurrente (`PRAGMA journal_mode = WAL;`). Debe contener exactamente las siguientes 6 tablas normalizadas en Tercera Forma Normal (3FN) con restricciones de dominio (`CHECK`):

### 1.1 Tabla `categories` (Familias de Productos Ferreteros)
- `category_id` (`INTEGER PRIMARY KEY`)
- `category_code` (`TEXT UNIQUE NOT NULL`) — Ej. `HER-MAN`, `HER-ELE`, `TOR-FIJ`, `FON-PVC`, `MAT-CON`, `PIN-QUI`
- `category_name` (`TEXT NOT NULL`)
- `target_margin_pct` (`REAL NOT NULL CHECK (target_margin_pct >= 0 AND target_margin_pct <= 100)`)

### 1.2 Tabla `suppliers` (Proveedores Locales y Regionales)
- `supplier_id` (`INTEGER PRIMARY KEY`)
- `supplier_name` (`TEXT NOT NULL`)
- `contact_phone` (`TEXT NOT NULL`)
- `lead_time_days` (`INTEGER NOT NULL CHECK (lead_time_days >= 1)`) — Tiempo promedio de entrega en días para cálculo de Punto de Reorden (ROP)
- `city` (`TEXT NOT NULL`)

### 1.3 Tabla `users` (Control de Acceso Basado en Roles — RBAC)
- `user_id` (`INTEGER PRIMARY KEY`)
- `username` (`TEXT UNIQUE NOT NULL`)
- `full_name` (`TEXT NOT NULL`)
- `role` (`TEXT NOT NULL CHECK (role IN ('ADMIN', 'CAJERO', 'BODEGUERO'))`)
- `pin` (`TEXT NOT NULL`)
- `is_active` (`INTEGER NOT NULL DEFAULT 1`)

### 1.4 Tabla `products` (Catálogo Maestro de Artículos SKU)
- `product_id` (`INTEGER PRIMARY KEY`)
- `sku` (`TEXT UNIQUE NOT NULL`) — Indexado mediante índice único B-Tree (`idx_products_sku`)
- `product_name` (`TEXT NOT NULL`)
- `category_id` (`INTEGER NOT NULL REFERENCES categories(category_id)`)
- `supplier_id` (`INTEGER NOT NULL REFERENCES suppliers(supplier_id)`)
- `unit_measure` (`TEXT NOT NULL`) — Ej. `Unidad`, `Caja x100`, `Bolsa 42.5kg`, `Galón`, `Metro`
- `unit_cost_usd` (`REAL NOT NULL CHECK (unit_cost_usd > 0)`)
- `unit_price_usd` (`REAL NOT NULL CHECK (unit_price_usd >= unit_cost_usd)`)
- `current_stock` (`INTEGER NOT NULL CHECK (current_stock >= 0)`)
- `min_stock` (`INTEGER NOT NULL CHECK (min_stock >= 0)`)
- `aisle_location` (`TEXT NOT NULL`) — Ubicación física en bodega (ej. `Pasillo A-01`, `Bodega Pesados P-03`)
- `updated_at` (`TEXT NOT NULL`) — Marca temporal ISO-8601

### 1.5 Tabla `sales` (Encabezado de Transacciones en Punto de Venta)
- `sale_id` (`INTEGER PRIMARY KEY AUTOINCREMENT`)
- `transaction_uuid` (`TEXT UNIQUE NOT NULL`) — Clave de idempotencia para evitar cobros duplicados
- `sale_timestamp` (`TEXT NOT NULL`) — Fecha y hora ISO-8601 (`YYYY-MM-DD HH:MM:SS`)
- `user_id` (`INTEGER NOT NULL REFERENCES users(user_id)`)
- `customer_type` (`TEXT NOT NULL CHECK (customer_type IN ('CONSUMIDOR_FINAL', 'CONTRATISTA', 'TALLER_INDUSTRIAL'))`)
- `payment_method` (`TEXT NOT NULL CHECK (payment_method IN ('EFECTIVO', 'TRANSFERENCIA_QR', 'TARJETA'))`)
- `total_cost_usd` (`REAL NOT NULL CHECK (total_cost_usd >= 0)`)
- `total_amount_usd` (`REAL NOT NULL CHECK (total_amount_usd >= 0)`)
- `gross_profit_usd` (`REAL NOT NULL`)

### 1.6 Tabla `sale_items` y Tabla `inventory_movements` (Detalle y Bitácora de Auditoría)
- **`sale_items`**:
  - `sale_item_id` (`INTEGER PRIMARY KEY AUTOINCREMENT`)
  - `sale_id` (`INTEGER NOT NULL REFERENCES sales(sale_id) ON DELETE CASCADE`)
  - `product_id` (`INTEGER NOT NULL REFERENCES products(product_id)`)
  - `quantity` (`INTEGER NOT NULL CHECK (quantity > 0)`)
  - `unit_cost_snapshot_usd` (`REAL NOT NULL`)
  - `unit_price_snapshot_usd` (`REAL NOT NULL`)
  - `subtotal_usd` (`REAL NOT NULL`)
- **`inventory_movements`** (Inmutable para trazabilidad de auditoría y fuente de extracción ETL):
  - `movement_id` (`INTEGER PRIMARY KEY AUTOINCREMENT`)
  - `movement_timestamp` (`TEXT NOT NULL`)
  - `product_id` (`INTEGER NOT NULL REFERENCES products(product_id)`)
  - `user_id` (`INTEGER NOT NULL REFERENCES users(user_id)`)
  - `movement_type` (`TEXT NOT NULL CHECK (movement_type IN ('VENTA_POS', 'INGRESO_PROVEEDOR', 'AJUSTE_AUDITORIA'))`)
  - `quantity_delta` (`INTEGER NOT NULL`) — Negativo en salidas, positivo en entradas
  - `stock_before` (`INTEGER NOT NULL`)
  - `stock_after` (`INTEGER NOT NULL CHECK (stock_after >= 0)`)
  - `reference_note` (`TEXT NOT NULL`)

## 2. Especificación del Esquema Analítico (OLAP — Star Schema / Data Marts)

Para demostrar competencias de **Data Engineering**, el archivo `app/db/schema_olap.sql` debe crear las siguientes tablas analíticas que son pobladas y refrescadas por el Pipeline ETL:

1. **`dw_fact_daily_sales`** (Tabla de Hechos Diaria):
   - `date_key` (`TEXT`), `category_code` (`TEXT`), `total_transactions` (`INTEGER`), `units_sold` (`INTEGER`), `gross_revenue_usd` (`REAL`), `cogs_usd` (`REAL`), `gross_profit_usd` (`REAL`), `gross_margin_pct` (`REAL`).
2. **`dw_mart_product_abc_health`** (Data Mart de Clasificación ABC de Pareto y Riesgo de Quiebre):
   - `product_id` (`INTEGER PRIMARY KEY`), `sku` (`TEXT`), `product_name` (`TEXT`), `category_name` (`TEXT`), `current_stock` (`INTEGER`), `min_stock` (`INTEGER`), `stock_status` (`TEXT`: `'OPTIMO'`, `'BAJO_STOCK'`, `'AGOTADO'`), `units_sold_30d` (`INTEGER`), `revenue_30d_usd` (`REAL`), `profit_30d_usd` (`REAL`), `cumulative_rev_pct` (`REAL`), `abc_class` (`TEXT`: `'A'`, `'B'`, `'C'`), `daily_burn_rate` (`REAL`), `days_of_inventory_left` (`REAL`), `recommended_reorder_qty` (`INTEGER`), `inventory_valuation_cost_usd` (`REAL`).
3. **`dw_etl_audit_log`** (Tabla de Observabilidad y Linaje del Pipeline ETL):
   - `run_id` (`INTEGER PRIMARY KEY AUTOINCREMENT`), `run_timestamp` (`TEXT`), `trigger_source` (`TEXT`), `rows_extracted` (`INTEGER`), `dq_checks_passed` (`INTEGER`), `dq_checks_failed` (`INTEGER`), `execution_time_ms` (`REAL`), `status` (`TEXT`), `summary_json` (`TEXT`).

## 3. Dataset Sintético Oficial para el Proyecto (Listo para Ingesta)

El cargador de semillas (`seed_loader.py`) debe insertar exactamente los siguientes catálogos base y generar de forma determinista (`random.seed(2026)`) el historial de transacciones de los últimos 30 días para que el Dashboard BI luzca lleno de información realista desde el primer arranque:

### 3.1 Semilla de Categorías (`data/seeds/categories.csv`)
```csv
category_id,category_code,category_name,target_margin_pct
1,HER-MAN,Herramientas Manuales,35.0
2,HER-ELE,Herramientas Eléctricas y Accesorios,28.0
3,TOR-FIJ,Tornillería, Pernos y Fijaciones,48.0
4,FON-PVC,Fontanería, Tubería PVC y Grifería,38.0
5,MAT-CON,Materiales Pesados de Construcción,22.0
6,PIN-QUI,Pinturas, Solventes y Químicos,32.0
```

### 3.2 Semilla de Proveedores Salvadoreños (`data/seeds/suppliers.csv`)
```csv
supplier_id,supplier_name,contact_phone,lead_time_days,city
1,Distribuidora Ferretera Salvadoreña S.A. de C.V.,2221-4500,2,San Salvador
2,Importadora Industrial Soyapango (IMPOSOY),2277-8910,1,Soyapango
3,Plásticos y Tuberías de Centroamérica,2250-3320,3,Ilopango
4,Cementos y Agregados Nacionales,2209-1100,2,Metapán / San Salvador
5,Pinturas y Recubrimientos del Istmo,2288-6400,3,Santa Tecla
6,Corporación de Tornillos y Aceros (CORTAC),2235-7712,4,San Salvador
```

### 3.3 Semilla de Usuarios por Rol (`data/seeds/users.csv`)
```csv
user_id,username,full_name,role,pin,is_active
1,descobar,Diego Alejandro Escobar Barahona (Admin / Lead Data Engineer),ADMIN,admin2026,1
2,evasquez,Elena Vásquez (Operations & Inventory Manager),ADMIN,gerencia2026,1
3,cmartinez,Carlos Martínez (Front Desk / POS Cashier),CAJERO,caja101,1
4,rflores,Roberto Flores (Warehouse & Receiving Supervisor),BODEGUERO,bodega202,1
```

### 3.4 Semilla de Productos Ferreteros (`data/seeds/products_sku.csv` — 30 SKU Principales)
*(Nota: Incluye intencionalmente artículos en estado `OPTIMO`, `BAJO_STOCK` y `AGOTADO` para demostrar las alertas en tiempo real durante la defensa del proyecto).*

```csv
product_id,sku,product_name,category_id,supplier_id,unit_measure,unit_cost_usd,unit_price_usd,current_stock,min_stock,aisle_location
1,HM-001,Martillo de uña curva 16 oz mango fibra de vidrio Truper,1,1,Unidad,5.20,8.50,28,10,Pasillo A-01
2,HM-002,Cinta métrica profesional 5 metros contra impacto,1,1,Unidad,2.80,4.75,8,12,Pasillo A-01
3,HM-003,Juego de destornilladores precisión y fuerza (6 piezas),1,1,Juego,6.50,10.90,19,8,Pasillo A-02
4,HM-004,Alicate universal de electricista 8 pulgadas aislado,1,1,Unidad,4.40,7.25,5,10,Pasillo A-02
5,HM-005,Llave ajustable cromada (Perica) de 10 pulgadas,1,1,Unidad,5.80,9.50,15,6,Pasillo A-03
6,HE-001,Taladro percutor industrial 1/2 pulg 750W velocidad variable,2,2,Unidad,38.00,56.50,11,5,Pasillo B-01
7,HE-002,Esmeriladora angular (Pulidora) 4-1/2 pulg 850W,2,2,Unidad,34.50,49.90,3,5,Pasillo B-01
8,HE-003,Disco de corte fino para metal 4-1/2 x 1/16 pulg,2,2,Unidad,0.75,1.50,145,50,Pasillo B-02
9,HE-004,Disco diamantado segmentado para concreto 4-1/2 pulg,2,2,Unidad,3.90,6.80,18,15,Pasillo B-02
10,HE-005,Juego de brocas de alta velocidad HSS para metal (13 pzas),2,2,Juego,7.20,12.50,0,6,Pasillo B-03
11,TF-001,Tornillo goloso para lámina 2 pulg con arandela neopreno (Ciento),3,6,Caja x100,4.10,7.80,42,15,Pasillo C-01
12,TF-002,Tornillo para tabla roca (Drywall) 6x1 pulg punta fina (Ciento),3,6,Caja x100,1.65,3.25,65,20,Pasillo C-01
13,TF-003,Perno hexagonal grado 5 de 3/8 x 2 pulg con tuerca (Docena),3,6,Docena,2.40,4.50,9,12,Pasillo C-02
14,TF-004,Anclaje expansivo para concreto (Chazo metálico) 3/8 x 3 pulg,3,6,Unidad,0.45,0.95,110,40,Pasillo C-02
15,TF-005,Clavo de acero con cabeza para madera 2-1/2 pulg (Libra),3,6,Libra,0.85,1.60,18,25,Pasillo C-03
16,FP-001,Tubo PVC agua potable 1/2 pulg SDR-26 de 6 metros (315 PSI),4,3,Lance 6m,3.80,6.25,54,25,Bodega Tubos T-01
17,FP-002,Tubo PVC drenaje sanitario 4 pulg de 6 metros,4,3,Lance 6m,14.20,21.50,16,10,Bodega Tubos T-02
18,FP-003,Pegamento solvente para PVC pesado 1/4 de pinta con aplicador,4,3,Lata,2.60,4.40,7,15,Pasillo D-01
19,FP-004,Válvula de bola (Llave de paso) PVC roscable 1/2 pulg,4,3,Unidad,1.40,2.65,32,15,Pasillo D-02
20,FP-005,Cinta teflón de alta densidad 3/4 pulg x 10 metros,4,3,Rollo,0.30,0.75,190,50,Pasillo D-02
21,MC-001,Cemento gris uso general tipo UGC bolsa de 42.5 kg,5,4,Bolsa 42.5kg,7.85,9.75,85,40,Bodega Pesados P-01
22,MC-002,Hierro corrugado de 3/8 pulg grado 40 (Varilla de 6 metros),5,4,Varilla,4.15,5.60,120,50,Bodega Pesados P-02
23,MC-003,Alambre de amarre recocido calibre 18 (Libra),5,4,Libra,0.90,1.55,14,30,Bodega Pesados P-02
24,MC-004,Lámina galvanizada acanalada calibre 26 de 3 metros,5,4,Lámina,13.50,17.90,22,15,Bodega Pesados P-03
25,MC-005,Mortero premezclado para repello fino bolsa de 40 kg,5,4,Bolsa 40kg,5.40,7.25,0,20,Bodega Pesados P-01
26,PQ-001,Pintura látex acrílica blanco mate interior/exterior (Galón),6,5,Galón,11.50,16.90,24,10,Pasillo E-01
27,PQ-002,Pintura anticorrosiva alquídica rojo óxido para metal (Galón),6,5,Galón,14.80,21.50,6,8,Pasillo E-01
28,PQ-003,Solvente mineral / Thinner acrílico estándar (Botella 750 ml),6,5,Botella,1.35,2.40,48,20,Pasillo E-02
29,PQ-004,Silicona acética transparente multiusos tubo 280 ml,6,5,Cartucho,2.20,3.85,29,12,Pasillo E-03
30,PQ-005,Brocha profesional de cerda natural 4 pulgadas,6,5,Unidad,2.10,3.60,35,15,Pasillo E-03
```

### 3.5 Especificación del Generador Determinista de Historial Transaccional (30 Días)
El script `app/db/seed_loader.py` debe verificar si la tabla `sales` está vacía al iniciar la aplicación. Si está vacía, además de cargar los CSV anteriores, debe generar automáticamente **180 ventas históricas distribuidas en los últimos 30 días** (`2026-09-21` a `2026-10-21`) cumpliendo la distribución de Pareto (80/20):
- **Productos Clase A (Alta rotación — 70% de probabilidad de aparición en tickets):** `MC-001` (Cemento), `MC-002` (Hierro 3/8), `HE-003` (Disco corte), `FP-001` (Tubo PVC 1/2), `TF-001` (Tornillo lámina), `PQ-001` (Pintura látex blanco), `HE-001` (Taladro 750W).
- **Productos Clase B (Rotación media — 20% de probabilidad):** `HM-001`, `HM-002`, `HE-002`, `FP-002`, `FP-003`, `MC-004`, `PQ-002`, `PQ-003`.
- **Productos Clase C (Rotación baja — 10% de probabilidad):** Resto de los artículos del catálogo.
- Por cada venta generada, `seed_loader.py` debe insertar sus filas correspondientes en `sale_items` y registrar el evento en `inventory_movements`, además de insertar **15 registros de `INGRESO_PROVEEDOR`** y **8 registros de `AJUSTE_AUDITORIA`** hechos por el usuario `rflores` (Bodeguero).

## 4. Criterios de Aceptación de la Fase 2 (Commit 2)
- [ ] Al ejecutar `python3 -m app.db.seed_loader`, se crea la base de datos con las 6 tablas OLTP y las 3 tablas OLAP sin errores de sintaxis SQL.
- [ ] Existen exactamente 6 categorías, 6 proveedores, 4 usuarios, 30 productos SKU (con al menos 8 productos en estado crítico `current_stock <= min_stock`, incluyendo 2 agotados con `current_stock = 0`) y 180 ventas históricas de los últimos 30 días.
