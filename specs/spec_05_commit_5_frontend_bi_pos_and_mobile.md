# SPEC 05 (Commit 5): Interfaces Adaptativas (Dashboard BI + Monitor ETL, POS Escritorio y Vista Móvil Bodega)

## Metadatos del Commit
| Atributo | Detalle |
| :--- | :--- |
| **Fase** | Fase 5 — Construcción del Frontend Adaptativo por Rol y Visualización Estadística |
| **Enfoque de Perfil** | Visualización de Datos Ejecutiva (BI), Observabilidad de Pipelines ETL y Ergonomía Operativa |
| **Archivos que Antigravity generará en esta fase** | `app/static/index.html`, `app/static/styles.css`, `app/static/app.js` |
| **Mensaje de Commit Sugerido** | `feat(ui): implement executive BI dashboard, ETL data quality monitor, desktop POS, and mobile warehouse view` |

## 1. Arquitectura de Interfaz Unificada con Conmutador Instantáneo de Rol

Para facilitar tanto la operación real como la demostración académica frente al tribunal evaluador, la barra superior (`Navbar`) debe incluir un **Selector Rápido de Rol / Vista Activa** que adapta la interfaz y los permisos al instante:

1. **Modo `ADMIN` — Inteligencia de Negocios & Ingeniería de Datos (Escritorio):**
   - Muestra el **Dashboard Gerencial BI** y el **Monitor del Pipeline ETL & Data Quality**.
2. **Modo `CAJERO` — Terminal de Punto de Venta Rápido (Escritorio):**
   - Muestra el **Buscador Instantáneo SKU + Carrito de Facturación POS** con cálculo de cambio y emisión de comprobante.
3. **Modo `BODEGUERO` — Auditoría y Recepción en Pasillos (Mobile-First):**
   - Diseñado para pantallas móviles (`< 768px` o simulador móvil en pantalla), ocultando tablas anchas y presentando **Tarjetas Táctiles de Acción Rápida (+1, +5, +10, Ingreso de Proveedor)** ordenadas por código de pasillo (`Pasillo A-01`, `Bodega Pesados P-01`, etc.).

## 2. Especificación Visual del Dashboard Gerencial BI y Monitor ETL

### 2.1 Cinta Superior de 5 Tarjetas KPI Ejecutivas
- **KPI 1 — Ingresos Brutos (30d):** Monto en `$ USD` y total de transacciones procesadas.
- **KPI 2 — Utilidad Bruta y Margen Real:** Ganancia neta sobre costo (`$ USD`) y porcentaje de margen bruto (`%`).
- **KPI 3 — Valoración del Inventario en Bodega:** Capital total invertido a costo (`$ USD`) y valor comercial de venta (`$ USD`).
- **KPI 4 — Alertas Críticas de Stock:** Conteo de SKU en estado `AGOTADO` (rojo) y `BAJO_STOCK` (ámbar) que requieren compra inmediata.
- **KPI 5 — Estado del Pipeline ETL & Data Quality:** Badge verde (`6/6 Reglas DQ Superadas`), latencia de la última corrida en `ms` y botón **"Ejecutar ETL Ahora"**.

### 2.2 Cuatro Visualizaciones Estadísticas Interactivas (Chart.js)
1. **Gráfico 1 — Evolución Diaria de Ingresos vs. Utilidad Bruta (30 Días):** Gráfico combinado de barras/líneas mostrando la tendencia diaria desde `dw_fact_daily_sales`.
2. **Gráfico 2 — Curva de Pareto ABC (80/20) de Productos Estrella:** Gráfico de barras (ingresos por SKU) + línea acumulada (`%`) destacando los productos Clase A que sostienen el flujo de caja de la ferretería.
3. **Gráfico 3 — Rentabilidad e Ingresos por Categoría Ferretera:** Gráfico de barras horizontales comparando las 6 familias (`Materiales de Construcción`, `Herramientas Eléctricas`, `Fontanería PVC`, etc.).
4. **Gráfico 4 — Distribución de Salud de Stock:** Gráfico de dona/barras con la proporción de artículos en estado `OPTIMO`, `BAJO_STOCK` y `AGOTADO`.

### 2.3 Tabla Inteligente de Prioridad de Reabastecimiento (Actionable BI)
Debajo de los gráficos, mostrar la tabla de órdenes de compra sugeridas generada por el ETL (`reorder_priority_list`):
- Columnas: `Código SKU`, `Artículo`, `Clase ABC`, `Ubicación`, `Stock Actual / Mínimo`, `Velocidad Diaria (Burn Rate)`, `Días Restantes (DOI)`, `Cantidad Sugerida a Pedir`, `Proveedor y Teléfono` y un botón rápido **"Recibir Pedido"** que pre-carga el ingreso de mercadería.

### 2.4 Panel de Observabilidad de Ingeniería de Datos (Pestaña / Sección ETL)
Para resaltar el perfil de **Data Engineer**, incluir un bloque técnico desplegable o pestaña que muestre:
- Diagrama visual de las 4 etapas del pipeline (`Extract OLTP` $\rightarrow$ `6 Reglas Data Quality` $\rightarrow$ `Transformaciones ABC/ROP` $\rightarrow$ `Load OLAP Star Schema / BigQuery`).
- Tabla de estado de las 6 reglas de calidad (`DQ-01` a `DQ-06`) con insignia `PASS` y fecha/hora exacta de evaluación.
- Historial de las últimas 10 ejecuciones registradas en `dw_etl_audit_log`.

## 3. Especificación de la Terminal POS (Escritorio) y Vista Móvil (Bodega)

### 3.1 Vista POS Mostrador (`CAJERO`)
- Campo de búsqueda con foco automático (`autofocus`) que filtra en `< 50 ms` por código SKU (ej. `MC-001`, `HE-002`) o nombre parcial.
- Indicador claro de stock disponible en cada resultado (deshabilitando el botón de agregar si el SKU está `AGOTADO`).
- Tabla de carrito a la derecha con controles `+ / -`, selector de tipo de cliente (`CONSUMIDOR_FINAL`, `CONTRATISTA`, `TALLER_INDUSTRIAL`), método de pago y botón **"Confirmar Venta Atómica (ACID)"**.
- Al confirmar, mostrar modal de comprobante y actualizar instantáneamente las métricas y el stock.

### 3.2 Vista Móvil de Pasillos (`BODEGUERO`)
- Filtro rápido por pasillo (`Todos`, `Pasillo A`, `Pasillo B`, `Pasillo C`, `Pasillo D`, `Pasillo E`, `Bodega Pesados`, `Bodega Tubos`) y filtro de `Solo Críticos / Agotados`.
- Cada artículo se presenta como una **Tarjeta Compacta Móvil** con:
  - Encabezado: `SKU` + Badge de Pasillo (`Pasillo B-01`) + Semáforo (`BAJO STOCK` / `AGOTADO` / `ÓPTIMO`).
  - Cuerpo: Nombre del artículo, unidad de medida y número grande con el **Stock Físico Actual**.
  - Pie de tarjeta: Botones táctiles grandes (`+1`, `+5`, `+10`, `Registrar Ingreso Proveedor`, `Ajuste por Conteo`) con campo breve para nota o número de factura de proveedor.

## 4. Criterios de Aceptación de la Fase 5 (Commit 5)
- [ ] Al vender un artículo en la vista `CAJERO` hasta dejar su stock por debajo de `min_stock`, el semáforo cambia a `BAJO_STOCK` y aparece inmediatamente en la tabla de prioridad de reabastecimiento del Dashboard `ADMIN`.
- [ ] En resoluciones móviles (`375px` de ancho), la vista de `BODEGUERO` no presenta desplazamiento horizontal y permite registrar un ingreso de mercadería en menos de 3 toques.
