# SPEC 03 (Commit 3): Pipeline ETL/ELT, Reglas de Calidad de Datos y Analítica ABC

## Metadatos del Commit
| Atributo | Detalle |
| :--- | :--- |
| **Fase** | Fase 3 — Construcción del Motor ETL, Validación Data Quality y Transformaciones Analíticas |
| **Enfoque de Perfil** | **Core del Perfil:** Ingeniería de Datos, Pipelines ETL/ELT, Observabilidad y Modelado Dimensional |
| **Archivos que Antigravity generará en esta fase** | `app/etl/data_quality.py`, `app/etl/transformations.py`, `app/etl/pipeline.py`, `app/etl/bigquery_sync.py` |
| **Mensaje de Commit Sugerido** | `feat(etl): implement extract-validate-transform-load pipeline, DQ assertions, and ABC pareto marts` |

## 1. Arquitectura del Pipeline ETL (`app/etl/pipeline.py`)

El pipeline debe estructurarse en cuatro etapas explícitas y medibles (**Extract $\rightarrow$ Validate [DQ] $\rightarrow$ Transform $\rightarrow$ Load**) que se ejecutan automáticamente al iniciar la aplicación, después de cada venta/ajuste (en modo incremental ligero) o manualmente desde el botón **"Ejecutar Pipeline ETL Ahora"** del Dashboard:

```text
[OLTP SQLite: products, sales, sale_items, inventory_movements]
        │
        ▼  1. EXTRACT (Lectura transaccional consistente)
[DataFrames / Estructuras en Memoria]
        │
        ▼  2. VALIDATE (6 Compuertas de Calidad de Datos — data_quality.py)
[Reporte DQ: Passed / Failed + Conteo de Anomalías]
        │
        ▼  3. TRANSFORM (Clasificación ABC Pareto, Burn Rate, DOI, ROP y Márgenes)
[Data Marts Dimensionales Calculados]
        │
        ▼  4. LOAD (Reemplazo atómico en Tablas OLAP Locales + Sync Opcional a BigQuery)
[dw_fact_daily_sales, dw_mart_product_abc_health, dw_etl_audit_log]
```

## 2. Compuertas de Calidad de Datos (`app/etl/data_quality.py`)

Para demostrar rigor de **Analista de Datos Técnico / Data Engineer**, antes de transformar los datos el módulo `data_quality.py` debe ejecutar exactamente estas **6 reglas de calidad de datos (Data Quality Assertions)** y guardar el resultado en JSON dentro de `dw_etl_audit_log`:

| ID Regla | Nombre de la Regla DQ | Condición Lógica Verificada | Acción ante Fallo |
| :--- | :--- | :--- | :--- |
| **DQ-01** | `NO_NEGATIVE_STOCK` | `COUNT(*) FROM products WHERE current_stock < 0` debe ser `0`. | Registrar alerta crítica y bloquear sobrescritura del Mart si hay corrupción. |
| **DQ-02** | `PRICE_ABOVE_COST_INVARIANT` | `COUNT(*) FROM products WHERE unit_price_usd < unit_cost_usd` debe ser `0`. | Marcar SKU con bandera de margen negativo en el reporte de auditoría. |
| **DQ-03** | `REFERENTIAL_INTEGRITY_SALES` | Todo `sale_items.product_id` y `sale_items.sale_id` existe en sus tablas maestras. | Filtrar registros huérfanos y contabilizarlos en `dq_checks_failed`. |
| **DQ-04** | `UNIQUE_TRANSACTION_UUID` | `COUNT(DISTINCT transaction_uuid) == COUNT(*)` en la tabla `sales`. | Deduplicar por `transaction_uuid` conservando el primer registro cronológico. |
| **DQ-05** | `SALES_SUBTOTAL_CONSISTENCY` | En `sale_items`, `ABS(subtotal_usd - (quantity * unit_price_snapshot_usd)) < 0.01`. | Recalcular `subtotal_usd` en la capa de transformación y registrar advertencia. |
| **DQ-06** | `FRESHNESS_CHECK` | Verificar que existan registros de ventas o movimientos en la ventana operativa. | Emitir estado `HEALTHY` o `STALE_DATA` en el monitor del pipeline. |

## 3. Especificación Matemática de Transformaciones (`app/etl/transformations.py`)

El módulo de transformación debe calcular las siguientes métricas de negocio e ingeniería de datos para poblar `dw_mart_product_abc_health` y `dw_fact_daily_sales`:

1. **Estado Semafórico de Existencias (`stock_status`):**
   - Si `current_stock == 0` $\rightarrow$ `'AGOTADO'`
   - Si `0 < current_stock <= min_stock` $\rightarrow$ `'BAJO_STOCK'`
   - Si `current_stock > min_stock` $\rightarrow$ `'OPTIMO'`
2. **Velocidad de Rotación Diaria (`daily_burn_rate`) y Días de Inventario Restantes (`days_of_inventory_left` — DOI):**
   - $\text{Unidades Vendidas 30d} = \sum \text{quantity}$ de los últimos 30 días para cada SKU.
   - $\text{daily\_burn\_rate} = \frac{\text{Unidades Vendidas 30d}}{30.0}$
   - Si $\text{daily\_burn\_rate} > 0$, entonces $\text{days\_of\_inventory\_left} = \text{round}\left(\frac{\text{current\_stock}}{\text{daily\_burn\_rate}}, 1\right)$; de lo contrario, asignar `999.0` (baja rotación sin consumo reciente).
3. **Cantidad Recomendada de Reabastecimiento (`recommended_reorder_qty`):**
   - Utilizando el `lead_time_days` del proveedor asignado al SKU y un stock de seguridad equivalente a `min_stock`:
   - $\text{Demanda en Lead Time} = \lceil \text{daily\_burn\_rate} \times \text{lead\_time\_days} \rceil$
   - $\text{Nivel Objetivo} = \text{min\_stock} + \text{Demanda en Lead Time} + \lceil \text{daily\_burn\_rate} \times 15 \rceil$ (cobertura para 15 días adicionales).
   - Si `current_stock <= min_stock`, entonces $\text{recommended\_reorder\_qty} = \max(0, \text{Nivel Objetivo} - \text{current\_stock})$; si `current_stock > min_stock`, entonces `0`.
4. **Clasificación ABC de Pareto (`abc_class`):**
   - Ordenar todos los SKU de forma descendente por ingresos de los últimos 30 días (`revenue_30d_usd`).
   - Calcular el porcentaje acumulado de ingresos (`cumulative_rev_pct`).
   - Asignar:
     - Clase **`'A'`** a los productos que representan hasta el **80.0%** del ingreso acumulado (artículos críticos que nunca deben agotarse).
     - Clase **`'B'`** a los productos entre el **80.01% y el 95.0%** del ingreso acumulado.
     - Clase **`'C'`** al **5.0% restante** (artículos de cola larga o rotación esporádica).
5. **Valoración Financiera del Inventario (`inventory_valuation_cost_usd`):**
   - $\text{inventory\_valuation\_cost\_usd} = \text{round}(\text{current\_stock} \times \text{unit\_cost\_usd}, 2)$.

## 4. Conector Opcional con Google BigQuery Free Tier (`app/etl/bigquery_sync.py`)

- Si la variable de entorno `ENABLE_BIGQUERY_SYNC=true` y `GCP_PROJECT_ID` están definidas, tras actualizar las tablas OLAP locales el pipeline enviará los registros de `dw_fact_daily_sales` y `dw_mart_product_abc_health` al dataset `ferrostats_dw` en BigQuery utilizando la librería estándar o API REST.
- Si `ENABLE_BIGQUERY_SYNC` es `false` (por defecto en desarrollo local o cuando se desee operar 100% sin credenciales externas), el conector devolverá `{"bigquery_sync": "SKIPPED_LOCAL_OLAP_ACTIVE"}` sin interrumpir la ejecución.

## 5. Criterios de Aceptación de la Fase 3 (Commit 3)
- [ ] Ejecutar el pipeline pobla `dw_fact_daily_sales` (30 días por categoría), `dw_mart_product_abc_health` (30 SKU clasificados en A, B y C) y registra una fila en `dw_etl_audit_log` con `dq_checks_passed = 6` y `status = 'SUCCESS'`.
- [ ] El tiempo total de ejecución del pipeline ETL para el dataset sintético es menor a **250 milisegundos**.
