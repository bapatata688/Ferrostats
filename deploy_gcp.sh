#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# FERROSTATS: DESPLIEGUE AUTOMATIZADO EN GOOGLE CLOUD RUN (FREE TIER $0.00 USD)
# Lead Architect: Diego Alejandro Escobar Barahona
# ==============================================================================

PROJECT_ID="${1:-ferrostats}"
REGION="us-central1"
SERVICE_NAME="ferrostats-bi-platform"

echo "=================================================================="
echo "  DESPLEGANDO FERROSTATS EN GOOGLE CLOUD RUN"
echo "  Proyecto GCP: ${PROJECT_ID} | Región: ${REGION}"
echo "  Política FinOps: 100% Free Tier (Scale-to-Zero, \$0.00 USD)"
echo "=================================================================="

# 1. Configurar proyecto y habilitar APIs serverless
echo "==> 1. Configurando proyecto GCP y servicios esenciales..."
gcloud config set project "${PROJECT_ID}"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# 2. Desplegar en Cloud Run con Scale-to-Zero
echo "==> 2. Construyendo y desplegando servicio Cloud Run (min-instances=0)..."
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
  --set-env-vars="ENV=production,DB_PATH=/tmp/ferrostats.db,ENABLE_BIGQUERY_SYNC=true"

# 3. Limpieza de imágenes antiguas en Artifact Registry
echo "==> 3. Purgando versiones previas en Artifact Registry para respetar cuota gratuita (<0.5 GB)..."
IMAGE_REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${SERVICE_NAME}"
gcloud artifacts docker images list "${IMAGE_REPO}" \
  --sort-by=~UPDATE_TIME --format="get(version)" 2>/dev/null | tail -n +3 | while read -r VERSION; do
    if [ -n "${VERSION}" ]; then
      echo "  Eliminando digest antiguo: ${VERSION:0:18}..."
      gcloud artifacts docker images delete \
        "${IMAGE_REPO}@${VERSION}" \
        --quiet || true
    fi
done

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format="value(status.url)")

echo "=================================================================="
echo "  ¡DESPLIEGUE COMPLETADO EXITOSAMENTE!"
echo "  URL Pública de Producción: ${SERVICE_URL}"
echo "  Costo en Reposo: \$0.00 USD (Escalado a CERO instancias)"
echo "=================================================================="
