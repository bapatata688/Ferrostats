# FERROSTATS — Pipeline de Ingesta OLTP-a-OLAP y Data Lakehouse Medallón en Google Cloud

<p align="center">
  <img src="assets/logo.png" alt="Logo de FERROSTATS" width="220" />
</p>

<p align="center">
  <strong>Proyecto de Portafolio de Ingeniería de Datos: Ingesta Streaming Serverless OLTP-a-OLAP, Data Lakehouse Medallón Automatizado (Google BigQuery + Dataform SQLX), Analítica Dinámica de Inventario Pareto 80/20 y Gobernanza FinOps de $0.00/mes.</strong>
</p>

<p align="center">
  <a href="https://www.credly.com/badges/e27fea72-5eaf-47ee-a43c-43faa3a8fb10"><img src="https://img.shields.io/badge/Google%20Cloud%20Certified-Associate%20Data%20Practitioner-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white" alt="GCP Certified Associate Data Practitioner" /></a>
  <a href="https://cloud.google.com/bigquery"><img src="https://img.shields.io/badge/Google%20Cloud-BigQuery%20Lakehouse-38bdf8?style=for-the-badge&logo=googlecloud&logoColor=white" alt="BigQuery" /></a>
  <a href="https://cloud.google.com/dataform"><img src="https://img.shields.io/badge/Google%20Cloud-Dataform%20SQLX-38bdf8?style=for-the-badge&logo=googlecloud&logoColor=white" alt="Dataform" /></a>
  <a href="https://lookerstudio.google.com/"><img src="https://img.shields.io/badge/Google%20Cloud-Looker%20Studio%20BI-38bdf8?style=for-the-badge&logo=googlelooker&logoColor=white" alt="Looker Studio" /></a>
  <a href="https://cloud.google.com/run"><img src="https://img.shields.io/badge/Google%20Cloud-Cloud%20Run%20Serverless-38bdf8?style=for-the-badge&logo=googlecloud&logoColor=white" alt="GCP Cloud Run" /></a>
  <a href="finops/gcp_free_tier_policy.json"><img src="https://img.shields.io/badge/FinOps-$0.00%20USD%20Always%20Free%20Tier-10b981?style=for-the-badge" alt="FinOps" /></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://www.sqlite.org/wal.html"><img src="https://img.shields.io/badge/Edge%20OLTP-SQLite%20WAL%20ACID-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite WAL" /></a>
</p>

<p align="center">
  <strong>Idioma / Language:</strong> <strong>Español</strong> | <a href="README.md">English Version</a>
</p>

> [!NOTE]
> **Alcance de Ingeniería de Datos y Carga Sintética:** Este repositorio demuestra una **Arquitectura de Ingeniería de Datos y Cloud Data Lakehouse** de extremo a extremo operando con un costo permanente de **$0.00 USD/mes** en Google Cloud Platform. Todos los SKUs, movimientos de inventario y transacciones POS son generados sintéticamente (semilla determinista de 180 ventas sobre 30 SKUs ferreteros estandarizados en inglés). Las interfaces web (`/` y `/pos`) funcionan como **productores de eventos transaccionales en el borde** construidos bajo **Spec-Driven Development (SDD)** para alimentar en tiempo real el pipeline Medallón en BigQuery.

---

## Enlaces de Demostración en Vivo (Google Cloud Platform)

| Componente | URL / Recurso en Vivo | Rol Arquitectónico |
|---|---|---|
| **Reporte Ejecutivo Looker Studio BI** | [Informe Analítico FERROSTATS](https://datastudio.google.com/reporting/2389e684-fc9b-431d-9c56-487b3067eb87/page/p_dwbfqrtk8d) | Suite BI de 3 páginas conectada nativamente a los Data Marts Gold de BigQuery (`fct_daily_sales`, `mart_inventory_pareto_abc`, `dim_products`). |
| **Portal de Auditoría de Bodega & BI** | [https://ferrostats-bi-platform-s72yk4nsvq-uc.a.run.app](https://ferrostats-bi-platform-s72yk4nsvq-uc.a.run.app) | Productor de eventos de ajuste de inventario por pasillos y portal con Looker BI embebido. |
| **Simulador POS Productor de Eventos** | [https://ferrostats-bi-platform-s72yk4nsvq-uc.a.run.app/pos](https://ferrostats-bi-platform-s72yk4nsvq-uc.a.run.app/pos) | Terminal de cobro ACID (<50 ms) que transmite eventos transaccionales en vivo hacia `ferrostats_bronze`. |
| **Documentación Swagger / OpenAPI 3.0** | [https://ferrostats-bi-platform-s72yk4nsvq-uc.a.run.app/docs](https://ferrostats-bi-platform-s72yk4nsvq-uc.a.run.app/docs) | Contratos de datos REST, llaves de idempotencia y endpoints de observabilidad del pipeline. |
| **Presentación Ejecutiva Interactiva** | [https://ferrostats-bi-platform-s72yk4nsvq-uc.a.run.app/presentacion](https://ferrostats-bi-platform-s72yk4nsvq-uc.a.run.app/presentacion) | Presentación interactiva con el desglose del DAG Medallón y gobernanza FinOps. |
| **Proyecto GCP & Dataform** | `ferrostats` (`us-central1`) | Repositorio Dataform: `ferrostats-pipeline` (`main-workspace`) • Datasets: `ferrostats_bronze`, `ferrostats_silver`, `ferrostats_gold`. |

---

## Autoría de Ingeniería y Transparencia en Spec-Driven Development (SDD)

Al ser un portafolio especializado en **Ingeniería de Datos y Arquitectura Cloud**, este proyecto documenta con total transparencia qué componentes fueron diseñados y programados directamente por el autor frente a dónde se empleó **Spec-Driven Development (SDD)** y generación asistida por IA (específicamente en el andamiaje HTML/CSS/JS del frontend web, dado que el desarrollo web full-stack no es el foco principal de este portafolio):

| Dominio de Ingeniería | Modelo de Autoría y Ejecución | Entregables Técnicos |
|---|---|---|
| **Arquitectura Cloud y Diseño del Lakehouse Medallón** | **100% Diseñado por el Autor**<br>*(Diego Alejandro Escobar Barahona)* | Topología desacoplada OLTP-a-OLAP, partición de datasets en Google BigQuery (`ferrostats_bronze`, `ferrostats_silver`, `ferrostats_gold`) y modelado dimensional en Esquema Estrella (`fct_daily_sales`, `mart_inventory_pareto_abc`, `dim_products`). |
| **Pipelines Dataform SQLX y SQL Analítico** | **100% Programado por el Autor**<br>*(Diego Alejandro Escobar Barahona)* | Orquestación declarativa de DAGs en SQLX, aserciones de Calidad de Datos (`uniqueKey`, `nonNull`, `rowConditions`), funciones de ventana para Pareto 80/20, Daily Burn Rate, Days of Inventory (DOI) y Reorder Point (ROP). |
| **Gobernanza FinOps ($0.00/mes Free Tier)** | **100% Diseñado por el Autor**<br>*(Diego Alejandro Escobar Barahona)* | Sustitución de Cloud SQL y VPC Connectors por contenedores Cloud Run scale-to-zero, tokens OAuth vía servidor de metadatos interno de GCP y purga automatizada de imágenes en Artifact Registry (<0.3 GB). |
| **Contratos OLTP, Reglas ACID e Idempotencia** | **Especificado vía SDD** ([`specs/`](specs/))<br>+ *Verificado en Python/SQLite WAL* | Esquema relacional 3NF, bloqueos `BEGIN IMMEDIATE`, descuentos atómicos con cláusula de guarda (`current_stock >= :qty`) e idempotencia mediante `transaction_uuid`. |
| **Interfaz Web Frontend (`app/static/*.html`, `*.js`, `*.css`)** | **SDD + Andamiaje Asistido por IA**<br>*(Dirigido mediante [`spec_05`](specs/spec_05_commit_5_frontend_bi_pos_and_mobile.md))* | Aplicaciones SPA para el simulador de caja POS y auditoría de pasillos, generadas a partir de especificaciones formales para actuar como productores visuales de eventos hacia el pipeline de datos. |

---

## 1. Arquitectura de Datos End-to-End

```mermaid
flowchart TD
    subgraph CLIENT["Productores de Eventos en el Borde (Simuladores Web SDD)"]
        UI_POS["Terminal POS (/pos)\n- Checkout ACID <50ms\n- Emisor de UUID Idempotente"]
        UI_MGR["Portal de Bodega y BI (/)\n- Auditoría de Pasillos (Aisle A-01..E-03)\n- Recepción de Proveedores\n- Looker Studio BI Embebido"]
    end

    subgraph CLOUD_RUN["Ingesta Serverless en el Borde (Google Cloud Run us-central1 - $0.00 USD)"]
        FASTAPI["API de Ingesta FastAPI (Python 3.11)\n- Validación de Contratos Pydantic v2\n- Scale-to-Zero (min=0, max=2)"]
        SQLITE["Motor SQLite WAL (OLTP Local)\n- Aislamiento BEGIN IMMEDIATE\n- Descuento Protegido (current_stock >= requested_qty)\n- Bitácora Inmutable de Movimientos"]
        SYNC_ENGINE["Cliente Streaming BigQuery\n- Tokens OAuth vía Servidor de Metadatos IAM\n- Cero SDKs Pesados (urllib REST)\n- Ingesta Asíncrona No Bloqueante"]
    end

    subgraph GCP_DATA_PLATFORM["Google Cloud Platform (BigQuery Medallion Lakehouse - $0.00 USD)"]
        subgraph BRONZE["Capa Bronze (ferrostats_bronze — Ingesta Cruda Inmutable)"]
            BQ_RAW_SALES["raw_sales"]
            BQ_RAW_ITEMS["raw_sale_items"]
            BQ_RAW_PROD["raw_products"]
            BQ_RAW_CAT["raw_categories & raw_suppliers"]
            BQ_RAW_MOV["raw_inventory_movements"]
        end

        subgraph SILVER["Capa Silver (ferrostats_silver — Staging y Calidad en Dataform SQLX)"]
            DF_STG_SALES["stg_sales (Tipado Estricto, Margen %)"]
            DF_STG_ITEMS["stg_sale_items (COGS y Ganancia por Línea)"]
            DF_STG_PROD["stg_products (Catálogo + Enum stock_status)"]
            DF_ASSERT["Aserciones Dataform (uniqueKey, nonNull, rowConditions)"]
        end

        subgraph GOLD["Capa Gold (ferrostats_gold — Data Marts en Esquema Estrella)"]
            DM_SALES["fct_daily_sales (Ventas Diarias, COGS y Margen Bruto)"]
            DM_PARETO["mart_inventory_pareto_abc (Pareto 80/20, Burn Rate, DOI, ROP)"]
            DM_PROD["dim_products (Dimensión Maestra de Catálogo SKU -> Nombre)"]
        end
    end

    subgraph BI_VIZ["Capa de Business Intelligence"]
        LOOKER["Google Looker Studio (Reporte Ejecutivo de 3 Páginas)\n- Pág 1: Ingresos, Margen Bruto y Tendencias por Categoría\n- Pág 2: Matriz Pareto 80/20, DOI y Prioridad de Reposición\n- Pág 3: Valoración de Capital de Trabajo por Clase ABC"]
    end

    UI_POS -->|HTTP POST /api/v1/pos/checkout| FASTAPI
    UI_MGR -->|HTTP POST /api/v1/inventory/adjust| FASTAPI
    FASTAPI -->|Escritura ACID <50ms| SQLITE
    SQLITE -->|Confirmación| FASTAPI
    FASTAPI -->|Evento Transaccional| SYNC_ENGINE
    SYNC_ENGINE -->|Streaming REST| BRONZE

    BRONZE -->|DAG Dataform SQLX| SILVER
    SILVER -->|Funciones de Ventana y Agregación| GOLD
    GOLD -->|Conector Nativo BigQuery| LOOKER
    LOOKER -.->|Iframe Embebido| UI_MGR
```

---

## 2. Capas del Lakehouse Medallón en BigQuery y Dataform

| Capa Medallón | Dataset en BigQuery | Objetos en Dataform / BigQuery | Propósito en Ingeniería de Datos |
|---|---|---|---|
| **Bronze (Cruda)** | `ferrostats_bronze` | `raw_sales`<br>`raw_sale_items`<br>`raw_products`<br>`raw_categories`<br>`raw_suppliers`<br>`raw_inventory_movements` | Zona de aterrizaje inmutable (append-only) que preserva los eventos transaccionales e instantáneas históricas. |
| **Silver (Curada)** | `ferrostats_silver` | `stg_sales`<br>`stg_sale_items`<br>`stg_products` | Vistas declarativas en Dataform SQLX con casteo estricto (`INT64`, `FLOAT64`, `TIMESTAMP`), derivación de COGS/margen y clasificación estandarizada `stock_status` (`OPTIMAL`, `LOW_STOCK`, `OUT_OF_STOCK`). |
| **Gold (Marts)** | `ferrostats_gold` | `fct_daily_sales`<br>`mart_inventory_pareto_abc`<br>`dim_products` | Tablas de hechos y dimensiones en Esquema Estrella pre-agregadas para consultas en sub-segundos desde Looker Studio. |

---

## 3. Arquitecto de Datos Líder y Contacto

- **Autor y Arquitecto de Datos Líder:** Diego Alejandro Escobar Barahona
- **Certificación:** [Google Cloud Certified — Associate Data Practitioner](https://www.credly.com/badges/e27fea72-5eaf-47ee-a43c-43faa3a8fb10) (Credential ID: `23e3584a246f4c149f26fea03cebcbbb`)
- **LinkedIn:** [linkedin.com/in/diego-escobar-459256394](https://linkedin.com/in/diego-escobar-459256394)
- **Correo Electrónico:** `diegoalejandroescobarahona1@gmail.com`
- **Licencia:** Distribuido bajo la [Licencia MIT](LICENSE).
