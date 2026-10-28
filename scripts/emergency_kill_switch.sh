#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# FERROSTATS: INTERRUPTOR DE EMERGENCIA (KILL-SWITCH INSTANTÁNEO)
# Lead Architect: Diego Alejandro Escobar Barahona
# ==============================================================================

SERVICE_NAME="ferrostats-bi-platform"
REGION="us-central1"

echo "=================================================================="
echo "  ACTIVANDO INTERRUPTOR DE EMERGENCIA: SCALE-TO-ZERO ABSOLUTO     "
echo "  Servicio: ${SERVICE_NAME} | Región: ${REGION}                   "
echo "=================================================================="

echo "==> Escalando a CERO instancias máximas en Cloud Run..."
gcloud run services update "${SERVICE_NAME}" \
  --region "${REGION}" \
  --max-instances 0

echo "==> [OK] El servicio ha sido congelado por completo."
echo "==> No se procesará ni una sola petición y el costo es estrictamente \$0.00 USD."
echo ""
echo "==> Para reactivar el servicio en producción:"
echo "    gcloud run services update ${SERVICE_NAME} --region ${REGION} --max-instances 2"
echo "=================================================================="
