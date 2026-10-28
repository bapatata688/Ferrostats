# SPEC 01 (Commit 1): Arquitectura del Sistema, Reglas para Antigravity y FinOps GCP (<$5 USD)

## Metadatos del Commit y del Proyecto
| Atributo | Detalle |
| :--- | :--- |
| **Proyecto** | **FERROSTATS** — Plataforma de Inteligencia de Negocios, Pipeline ETL y Control Transaccional para Ferreterías |
| **Autor** | Diego Alejandro Escobar Barahona |
| **Enfoque de Perfil** | Data Engineer / Analista de Datos Técnico / Desarrollador de Pipelines ETL |
| **Metodología** | Spec-Driven Development (SDD) asistido por **Antigravity** |
| **Tiempo Objetivo de Construcción** | Sprint intensivo de 24 horas (Entrega: Mañana) |
| **Presupuesto Cloud** | **GCP Free Tier** (Tope máximo estricto: **$5.00 USD**; costo real proyectado: **$0.00 – $0.35 USD**) |
| **Mensaje de Commit Sugerido** | `docs(spec-01): define hybrid OLTP-ETL-OLAP architecture, antigravity rules, and GCP $5 finops guardrails` |

## 1. Visión Arquitectónica con Enfoque en Ingeniería de Datos (HTAP Ligero)

Para destacar el perfil de **Ingeniero de Datos y Analista Técnico de ETLs**, **FERROSTATS** no se diseña como un simple CRUD web, sino como una arquitectura híbrida **OLTP + Pipeline ETL + OLAP (Data Mart Analítico)** ejecutable dentro de un único servicio ultraligero que corre gratis en Google Cloud Run:

1. **Capa Transaccional Operativa (OLTP — 3FN):**
   - Captura en tiempo real las ventas en mostrador (POS), los ajustes físicos desde dispositivos móviles en pasillos de bodega y el catálogo de productos SKU con garantías estrictas **ACID** (Atomicidad, Consistencia, Aislamiento y Durabilidad).
2. **Capa de Ingeniería de Datos y Pipeline ETL/ELT (Core Diferenciador):**
   - Proceso automatizado y ejecutable bajo demanda (`POST /api/v1/etl/run`) que extrae las transacciones crudas del motor OLTP, ejecuta **compuertas de Calidad de Datos (Data Quality Checks)**, calcula métricas avanzadas de cadena de suministro (**Clasificación ABC de Pareto 80/20**, **Velocidad Diaria de Rotación**, **Días de Inventario Restantes [DOI]**, **Punto de Reorden [ROP]** y **Margen Bruto Real**) y carga tablas dimensionales y de hechos en un **Esquema Estrella (OLAP)**.
3. **Capa Analítica y de Visualización (OLAP + BI Dashboard):**
   - Alimenta el Dashboard Gerencial leyendo directamente de los Data Marts precalculados (latencia `< 50 ms`) y expone un panel de **Observabilidad del Pipeline ETL** (última corrida, filas procesadas, reglas de calidad superadas y sincronización opcional con **Google BigQuery Free Tier**).

## 2. Estrategia FinOps en GCP: Cómo No Gastar Más de $5 USD (Evitando Trampas de Facturación)

Para mantener el gasto entre **$0.00 y $0.50 USD** durante todo el ciclo de pruebas y producción, Antigravity debe respetar estrictamente las siguientes decisiones de infraestructura en Google Cloud Platform:

| Servicio en GCP | ¿Por qué se elige o se prohíbe? | Configuración de Capa Gratuita (Free Tier) | Costo Estimado |
| :--- | :--- | :--- | :--- |
| **Cloud Run** *(Elegido)* | Incluye 2 millones de peticiones/mes y 360,000 vCPU-segundos gratis. Escala a cero cuando nadie usa la app. | `--min-instances=0`, `--max-instances=2`, `--memory=512Mi`, `--cpu=1`, región `us-central1`. | **$0.00 USD** |
| **Cloud Storage (GCS) Volume Mount** *(Elegido)* | Permite montar un bucket como disco persistente en Cloud Run (5 GB gratis en `us-central1`) para persistir la base SQLite/DuckDB sin pagar servidores. | Bucket Standard en `us-central1` montado en `/mnt/data/ferrostats.db`. | **$0.00 USD** |
| **BigQuery Sandbox / Free Tier** *(Elegido para OLAP)* | Da 10 GB de almacenamiento activo y 1 TB de consultas SQL al mes gratis. Ideal para demostrar habilidades de Data Engineer. | Dataset `ferrostats_dw` en `US` multi-región para replicar los Data Marts del ETL. | **$0.00 USD** |
| **Artifact Registry** *(Elegido)* | Almacena la imagen Docker del proyecto. Incluye 0.5 GB gratis al mes. | Política de limpieza automática para conservar solo las últimas 2 imágenes Docker. | **$0.00 USD** |
| **Cloud SQL** *(PROHIBIDO)* | **Trampa presupuestaria:** No tiene capa gratuita; cobra por hora encendido (~$9–$15/mes + costo por IP pública IPv4) y agotaría los $5 USD en pocos días. | **No aprovisionar Cloud SQL bajo ninguna circunstancia.** | **Evitado** |
| **VPC Serverless Connector** *(PROHIBIDO)* | Cobra instancias `e2-micro` permanentes (~$14/mes). | **No crear conectores VPC.** Conectar a APIs de GCP por HTTPS público autenticado con IAM. | **Evitado** |

## 3. Árbol de Directorios Objetivo del Repositorio

Cuando Antigravity implemente las fases posteriores, deberá construir exactamente esta estructura modular y limpia (sin sobre-ingeniería, lista para desplegar en menos de 24 horas):

```text
ferrostats/
├── specs/                                  # Especificaciones SDD (1 archivo = 1 fase / commit)
│   ├── SPEC_01_COMMIT_1_ARCHITECTURE_AND_GCP_FINOPS.md
│   ├── SPEC_02_COMMIT_2_DATA_MODEL_AND_SYNTHETIC_SEED.md
│   ├── SPEC_03_COMMIT_3_ETL_PIPELINE_AND_DATA_QUALITY.md
│   ├── SPEC_04_COMMIT_4_BACKEND_API_AND_ACID_POS.md
│   ├── SPEC_05_COMMIT_5_FRONTEND_BI_POS_AND_MOBILE.md
│   └── SPEC_06_COMMIT_6_GCP_DEPLOY_DOCKER_AND_QA.md
├── data/
│   ├── seeds/                              # Datos sintéticos iniciales (CSV / JSON)
│   │   ├── categories.csv
│   │   ├── suppliers.csv
│   │   ├── users.csv
│   │   ├── products_sku.csv
│   │   └── historical_transactions.csv
│   └── db/                                 # Base de datos local / punto de montaje GCS
├── app/
│   ├── main.py                             # Punto de entrada FastAPI y montaje de archivos estáticos
│   ├── config.py                           # Variables de entorno y rutas de base de datos
│   ├── db/
│   │   ├── schema_oltp.sql                 # DDL de tablas relacionales 3FN con restricciones ACID
│   │   ├── schema_olap.sql                 # DDL de tablas dimensionales / Data Marts analíticos
│   │   └── connection.py                   # Gestor de conexiones SQLite (WAL mode) + transacciones
│   ├── etl/
│   │   ├── pipeline.py                     # Orquestador Extract -> Validate -> Transform -> Load
│   │   ├── data_quality.py                 # Reglas de validación de integridad y anomalías
│   │   ├── transformations.py              # Cálculo de Pareto ABC, ROP, DOI y márgenes
│   │   └── bigquery_sync.py                # Exportador opcional hacia BigQuery Free Tier
│   ├── api/
│   │   ├── routes_inventory.py             # Endpoints CRUD SKU y ajustes móviles de bodega
│   │   ├── routes_pos.py                   # Endpoint de venta atómica con bloqueo de stock
│   │   ├── routes_analytics.py             # Endpoints BI que leen del esquema OLAP y estado ETL
│   │   └── auth_rbac.py                    # Middleware ligero de roles (Admin, Cajero, Bodeguero)
│   └── static/
│       ├── index.html                      # SPA unificada (Dashboard BI + POS + Vista Móvil + Monitor ETL)
│       ├── styles.css                      # Diseño responsivo (Desktop Data-Dense + Mobile Cards <768px)
│       └── app.js                          # Cliente HTTP, gráficos Chart.js y conmutador de vistas por rol
├── Dockerfile                              # Imagen ligera python:3.11-slim optimizada para Cloud Run
├── requirements.txt                        # Dependencias mínimas (fastapi, uvicorn, pandas, pydantic)
└── deploy_gcp.sh                           # Script declarativo de despliegue en Cloud Run Free Tier
```

## 4. Instrucciones de Control para Antigravity (Prompt de Sistema por Fase)

Para construir el proyecto en Antigravity sin desviaciones ni errores que consuman tiempo:

1. **Regla de Oro de Ejecución Secuencial:** Antigravity debe leer un archivo `SPEC_0X` a la vez, implementar únicamente los componentes descritos en esa especificación, verificar los criterios de aceptación locales y dejar el árbol de trabajo listo para el commit correspondiente.
2. **Cero Dependencias Pesadas:** No instalar paquetes innecesarios (como Celery, Redis, RabbitMQ o frameworks de frontend con compilación pesada de Node/Webpack). Toda la interfaz debe servirse desde FastAPI con HTML5, CSS moderno y JavaScript vainilla + Chart.js para garantizar tiempos de compilación de contenedor menores a 45 segundos.
3. **Resiliencia en Demo:** Si las credenciales de BigQuery no están configuradas en el entorno local o en el contenedor de Cloud Run, el módulo `bigquery_sync.py` debe degradar de forma elegante (modo *local-first OLAP* sobre SQLite/vistas analíticas) registrando el evento en la bitácora del ETL sin lanzar excepciones fatales.

## 5. Criterios de Aceptación de la Fase 1 (Commit 1)
- [ ] El repositorio cuenta con la carpeta `specs/` y este documento como base arquitectónica.
- [ ] Las reglas de negocio, el límite estricto de $5 USD en GCP y la separación en tres capas de datos (**OLTP Transaccional**, **Pipeline ETL con Data Quality** y **OLAP Estrella para BI**) quedan definidos sin ambigüedades para las siguientes fases.
