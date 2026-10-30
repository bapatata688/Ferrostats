# SPEC 04 (Commit 4): Backend API RESTful, Motor Transaccional ACID y Seguridad RBAC

## Metadatos del Commit
| Atributo | Detalle |
| :--- | :--- |
| **Fase** | Fase 4 — Servicios API REST, Prevención de Condiciones de Carrera (ACID) y Control por Roles |
| **Enfoque de Perfil** | Ingeniería de Backend de Datos, Transacciones Atómicas, Idempotencia y Contratos JSON |
| **Archivos que Antigravity generará en esta fase** | `app/main.py`, `app/db/connection.py`, `app/api/auth_rbac.py`, `app/api/routes_inventory.py`, `app/api/routes_pos.py`, `app/api/routes_analytics.py` |
| **Mensaje de Commit Sugerido** | `feat(api): build FastAPI REST endpoints, ACID POS checkout engine, and RBAC middleware` |

## 1. Matriz de Seguridad y Control de Acceso Basado en Roles (RBAC)

El módulo `app/api/auth_rbac.py` debe validar el encabezado `X-User-Role` y `X-User-Id` (o selector de sesión activa en la interfaz para demostración ágil ante el jurado) aplicando estrictamente la siguiente matriz de permisos:

| Operación / Endpoint | `ADMIN` (Gerencia / Data Eng) | `CAJERO` (Mostrador POS) | `BODEGUERO` (Pasillos Móvil) |
| :--- | :---: | :---: | :---: |
| Consultar Catálogo SKU y Stock (`GET /api/v1/products`) | Permitido | Permitido | Permitido |
| Registrar Venta en Mostrador (`POST /api/v1/pos/checkout`) | Permitido | Permitido | **Denegado (`403`)** |
| Registrar Ingreso o Ajuste Físico (`POST /api/v1/inventory/adjust`) | Permitido | **Denegado (`403`)** | Permitido |
| Crear / Editar Precios y Costos SKU (`POST` / `PUT /api/v1/products`) | Permitido | **Denegado (`403`)** | **Denegado (`403`)** |
| Ver Dashboard BI, Márgenes y Ejecutar ETL (`GET /api/v1/analytics/*`, `POST /api/v1/etl/run`) | Permitido | **Denegado (`403`)** | **Denegado (`403`)** |

## 2. Algoritmo Transaccional ACID para el Punto de Venta (`POST /api/v1/pos/checkout`)

Para cumplir con el objetivo de **cero condiciones de carrera** cuando dos cajeros intentan vender las últimas unidades del mismo artículo simultáneamente, el endpoint de facturación debe ejecutar la siguiente secuencia transaccional atómica:

```sql
BEGIN IMMEDIATE TRANSACTION;
-- 1. Verificar idempotencia por transaction_uuid (si ya existe, devolver venta original con HTTP 200 y cabecera Idempotent-Replay: true)
-- 2. Para cada artículo del carrito:
SELECT current_stock, unit_cost_usd, unit_price_usd
FROM products
WHERE product_id = :product_id;

-- Si current_stock < :quantity_requested -> ejecutar ROLLBACK y devolver HTTP 409 Conflict
-- indicando exactamente qué SKU no tiene stock suficiente.

-- 3. Descuento atómico con cláusula de guarda adicional:
UPDATE products
SET current_stock = current_stock - :quantity_requested,
    updated_at = CURRENT_TIMESTAMP
WHERE product_id = :product_id
  AND current_stock >= :quantity_requested;

-- 4. Insertar encabezado en `sales`, renglones en `sale_items` y movimiento en `inventory_movements`.
COMMIT;
```
- Inmediatamente después del `COMMIT`, disparar el refresco incremental del Pipeline ETL (`run_etl_pipeline(trigger_source="POS_SALE")`) para que el Dashboard Gerencial refleje el nuevo ingreso y el nuevo estado de stock en tiempo real.

## 3. Contratos de Endpoints REST (`/api/v1/*`)

### 3.1 Catálogo y Bodega (`routes_inventory.py`)
1. **`GET /api/v1/products`**
   - Parámetros Query opcionales: `q` (búsqueda instantánea por código SKU o nombre), `category_id`, `stock_status` (`OPTIMO`, `BAJO_STOCK`, `AGOTADO`), `abc_class` (`A`, `B`, `C`).
   - Respuesta `200 OK`: Lista de productos enriquecida con su estado semafórico, ubicación en pasillo (`aisle_location`), clasificación ABC y cantidad recomendada de reorden.
2. **`POST /api/v1/inventory/adjust`**
   - Payload JSON:
     ```json
     {
       "product_id": 2,
       "user_id": 4,
       "movement_type": "INGRESO_PROVEEDOR",
       "quantity_delta": 20,
       "reference_note": "Recepción Factura #F-9021 IMPOSOY en Pasillo A-01"
     }
     ```
   - Regla: Si `current_stock + quantity_delta < 0`, rechazar con `HTTP 400 Bad Request`. Al confirmar, insertar registro inmutable en `inventory_movements`, actualizar `products.current_stock` y refrescar el Mart analítico.

### 3.2 Punto de Venta POS (`routes_pos.py`)
1. **`POST /api/v1/pos/checkout`**
   - Payload JSON:
     ```json
     {
       "transaction_uuid": "pos-20261021-0001",
       "user_id": 3,
       "customer_type": "CONTRATISTA",
       "payment_method": "EFECTIVO",
       "items": [
         {"product_id": 21, "quantity": 5},
         {"product_id": 22, "quantity": 10}
       ]
     }
     ```
   - Respuesta `200 OK`: Comprobante digital con `sale_id`, desglose de artículos, total cobrado, utilidad bruta calculada y alertas de stock disparadas. Si se reenvía un `transaction_uuid` existente, se devuelve la venta original con la cabecera `Idempotent-Replay: true`.

### 3.3 Analítica BI y Observabilidad ETL (`routes_analytics.py`)
1. **`GET /api/v1/analytics/dashboard`**
   - Lee directamente de las tablas OLAP (`dw_fact_daily_sales`, `dw_mart_product_abc_health`, `dw_etl_audit_log`) y devuelve en una sola llamada JSON (`< 50 ms`):
     - **`kpis`**: Ingresos 30d (`USD`), Utilidad Bruta 30d (`USD`), Margen Bruto Promedio (`%`), Valoración Total del Inventario a Costo (`USD`), Total SKU en Alerta (`BAJO_STOCK` + `AGOTADO`), Tiempo Medio de Respuesta.
     - **`daily_trend`**: Serie temporal de 30 días con ingresos, costos y utilidad bruta diaria.
     - **`category_breakdown`**: Ingresos, unidades vendidas y margen por cada una de las 6 familias ferreteras.
     - **`pareto_top_skus`**: Top 10 artículos Clase A con sus ingresos, % acumulado de Pareto, stock actual y días de inventario restantes (`DOI`).
     - **`reorder_priority_list`**: Artículos en estado `AGOTADO` o `BAJO_STOCK` ordenados por criticidad (Clase A primero) con su `recommended_reorder_qty` y proveedor asignado.
     - **`etl_health`**: Última corrida del pipeline (`run_timestamp`, `execution_time_ms`, `dq_checks_passed`, `dq_checks_failed`, `status`, detalle de las 6 reglas DQ).
2. **`POST /api/v1/etl/run`**
   - Ejecuta manualmente el ciclo completo `Extract -> Validate -> Transform -> Load` y devuelve el nuevo registro de auditoría de `dw_etl_audit_log`.

## 4. Criterios de Aceptación de la Fase 4 (Commit 4)
- [ ] Todos los endpoints responden en menos de **150 ms** localmente y están documentados automáticamente en `/docs` (Swagger UI de FastAPI).
- [ ] Una petición de venta que excede el `current_stock` devuelve `HTTP 409 Conflict` sin modificar el saldo de ningún artículo del carrito (prueba de atomicidad ACID).
