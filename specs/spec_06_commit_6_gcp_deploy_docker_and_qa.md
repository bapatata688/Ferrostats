# SPEC 06 (Commit 6): Despliegue en GCP Cloud Run (Free Tier), Contenedor Docker y Checklist QA

## Metadatos del Commit
| Atributo | Detalle |
| :--- | :--- |
| **Fase** | Fase 6 — Empaquetado Docker, Despliegue Serverless en GCP con Presupuesto <$5 y Validación ISO/IEC 25010 |
| **Enfoque de Perfil** | DataOps / Cloud Deployment en GCP, Control Presupuestario y Aseguramiento de Calidad |
| **Archivos que Antigravity generará en esta fase** | `Dockerfile`, `.dockerignore`, `requirements.txt`, `deploy_gcp.sh`, `README.md` |
| **Mensaje de Commit Sugerido** | `chore(deploy): add slim Dockerfile, GCP Cloud Run scale-to-zero deploy script, and QA verification suite` |

## 1. Especificación de Dependencias y Contenedor (`requirements.txt` y `Dockerfile`)

### 1.1 `requirements.txt` (Ultraligero y de Compilación Rápida)
```text
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.2
pandas==2.2.3
```
*(Opcional: `google-cloud-bigquery` solo si se habilita la exportación en vivo hacia un proyecto de BigQuery; el motor OLAP estrella local funciona al 100% con SQLite + Pandas sin requerir llaves externas).*

### 1.2 Especificación del `Dockerfile`
```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DB_PATH=/tmp/ferrostats.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Al iniciar el contenedor, asegura que la semilla y el pipeline ETL inicial se ejecuten
CMD ["sh", "-c", "python3 -m app.db.seed_loader && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
```
- **Nota sobre Persistencia en Cloud Run:**
  - Por defecto, usar `/tmp/ferrostats.db` (sistema de archivos en memoria de Cloud Run) pre-poblado automáticamente en `< 1 segundo` por `seed_loader.py` y `pipeline.py` en cada arranque en frío, **o bien** montar un bucket de Google Cloud Storage (`--add-volume name=db-vol,type=cloud-storage,bucket=ferrostats-data-... --add-volume-mount volume=db-vol,mount-path=/mnt/data`) definiendo `DB_PATH=/mnt/data/ferrostats.db`. Ambas opciones cuestan **$0.00 USD** dentro del Free Tier.

## 2. Script de Despliegue y Guardarraíl de Presupuesto ($5 USD) en GCP (`deploy_gcp.sh`)

El archivo `deploy_gcp.sh` debe automatizar el despliegue en **Google Cloud Run** garantizando que el servicio escale a cero (`--min-instances=0`) para no consumir centavos cuando nadie lo esté visitando:

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:-tu-proyecto-gcp}"
REGION="us-central1"
SERVICE_NAME="ferrostats-bi-platform"

echo "==> 1. Configurando proyecto GCP: ${PROJECT_ID} en región ${REGION} (Free Tier)"
gcloud config set project "${PROJECT_ID}"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

echo "==> 2. Desplegando en Cloud Run con Scale-to-Zero (Costo $0 en reposo)"
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 2 \
  --memory 512Mi \
  --cpu 1 \
  --concurrency 80 \
  --timeout 60s \
  --set-env-vars="ENV=production,DB_PATH=/tmp/ferrostats.db,ENABLE_BIGQUERY_SYNC=false"

echo "==> 3. Limpiando imágenes antiguas en Artifact Registry para no superar los 0.5 GB gratuitos"
gcloud artifacts docker images list "${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${SERVICE_NAME}" \
  --sort-by=~UPDATE_TIME --format="get(version)" | tail -n +3 | while read -r VERSION; do
    if [ -n "${VERSION}" ]; then
      gcloud artifacts docker images delete \
        "${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${SERVICE_NAME}@${VERSION}" \
        --quiet || true
    fi
done

echo "==> Despliegue completado exitosamente dentro del Free Tier de GCP."
```

### Configuración Manual de Alerta de Presupuesto en Consola GCP (2 Minutos)
1. Ir a **Facturación (Billing) $\rightarrow$ Presupuestos y alertas (Budgets & alerts)** en Google Cloud Console.
2. Crear presupuesto mensual llamado `Tope-Produccion-Ferrostats` con monto objetivo de **$5.00 USD**.
3. Configurar alertas por correo al **20% ($1.00)**, **50% ($2.50)** y **90% ($4.50)**.

## 3. Flujo de Commits para Subir a GitHub

Una vez que Antigravity genere cada fase siguiendo estas 6 especificaciones, la secuencia de commits en tu repositorio de GitHub quedará limpia y auditable como un proyecto profesional de Ingeniería de Datos:

1. **Commit 1:** `docs(spec-01): define hybrid OLTP-ETL-OLAP architecture, antigravity rules, and GCP $5 finops guardrails`
2. **Commit 2:** `feat(data-model): define 3NF OLTP schema, OLAP star schema, and realistic hardware store synthetic dataset`
3. **Commit 3:** `feat(etl): implement extract-validate-transform-load pipeline, DQ assertions, and ABC pareto marts`
4. **Commit 4:** `feat(api): build FastAPI REST endpoints, ACID POS checkout engine, and RBAC middleware`
5. **Commit 5:** `feat(ui): implement executive BI dashboard, ETL data quality monitor, desktop POS, and mobile warehouse view`
6. **Commit 6:** `chore(deploy): add slim Dockerfile, GCP Cloud Run scale-to-zero deploy script, and QA verification suite`

## 4. Guion de Demostración de 3 Minutos para Mañana (Defensa del Proyecto)

1. **Minuto 1 — El Problema y el Pipeline de Ingeniería de Datos (Rol `ADMIN`):**
   - Abrir la URL pública de Cloud Run (`https://ferrostats-bi-platform-...run.app`).
   - Mostrar el **Monitor del Pipeline ETL**: explicar cómo los datos transaccionales pasan por **6 compuertas de Calidad de Datos (DQ)** y se transforman en un **Esquema Estrella (OLAP)** con clasificación **ABC de Pareto** y cálculo automático de **Días de Inventario Restantes (DOI)**.
2. **Minuto 2 — Venta Transaccional ACID en Mostrador (Rol `CAJERO`):**
   - Cambiar al rol `CAJERO`. Buscar el código `HE-002` (Pulidora 4-1/2", stock inicial: `3`, mínimo: `5`) o `HM-001`.
   - Intentar vender más unidades de las existentes para mostrar cómo el motor **ACID** bloquea la venta con `HTTP 409` protegiendo la integridad del inventario; luego registrar una venta válida y mostrar el comprobante instantáneo.
3. **Minuto 3 — Auditoría Móvil en Pasillo y Actualización BI en Tiempo Real (Rol `BODEGUERO` $\rightarrow$ `ADMIN`):**
   - Cambiar a la vista móvil (`BODEGUERO`), filtrar el `Pasillo B-03` donde el artículo `HE-005` (Juego de brocas HSS) aparece `AGOTADO (0 uds)`.
   - Tocar **"Registrar Ingreso Proveedor (+15 uds)"**, volver al Dashboard `ADMIN` y mostrar cómo el valor total del inventario, los gráficos de Chart.js y la bitácora del ETL se actualizaron en menos de 1 segundo.
