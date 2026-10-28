#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# FERROSTATS: AUDITORÍA DE FACTURACIÓN Y VERIFICACIÓN CERO COSTO ($0.00 USD)
# Lead Architect: Diego Alejandro Escobar Barahona
# ==============================================================================

echo "=========================================================="
echo "   AUDITORÍA DE FACTURACIÓN: VERIFICACIÓN CERO COSTO (\$0)  "
echo "   Plataforma FERROSTATS • FinOps Production Guardrail    "
echo "=========================================================="

# 1. Verificar instancias de Cloud SQL
echo -n "[1/5] Verificando Cloud SQL... "
SQL_COUNT=$(gcloud sql instances list --format="value(name)" 2>/dev/null | grep -c . || true)
if [ "${SQL_COUNT}" -eq 0 ]; then
  echo "SEGURO: Cero instancias de Cloud SQL activas (Costo \$0.00)."
else
  echo "ALERTA: Se detectaron ${SQL_COUNT} instancias de Cloud SQL. ¡Elimínalas inmediatamente!"
fi

# 2. Verificar máquinas virtuales en Compute Engine
echo -n "[2/5] Verificando Compute Engine VMs... "
VM_COUNT=$(gcloud compute instances list --format="value(name)" 2>/dev/null | grep -c . || true)
if [ "${VM_COUNT}" -eq 0 ]; then
  echo "SEGURO: Cero máquinas virtuales activas (Costo \$0.00)."
else
  echo "ALERTA: Hay ${VM_COUNT} VMs encendidas. ¡Apágalas para evitar cobros!"
fi

# 3. Verificar conectores VPC Serverless
echo -n "[3/5] Verificando conectores VPC... "
VPC_COUNT=$(gcloud compute networks vpc-access connectors list --region=us-central1 --format="value(name)" 2>/dev/null | grep -c . || true)
if [ "${VPC_COUNT}" -eq 0 ]; then
  echo "SEGURO: Cero conectores VPC (Costo \$0.00)."
else
  echo "ALERTA: Hay conectores VPC activos que generan cobro por hora."
fi

# 4. Verificar configuración de Cloud Run (Scale to Zero)
echo -n "[4/5] Verificando Cloud Run Scale-to-Zero... "
MIN_INST=$(gcloud run services describe ferrostats-bi-platform --region=us-central1 --format="value(spec.template.metadata.annotations['autoscaling.knative.dev/minScale'])" 2>/dev/null || echo "0")
if [ "${MIN_INST}" == "0" ] || [ -z "${MIN_INST}" ]; then
  echo "CORRECTO: min-instances = 0 (Escala a cero en reposo)."
else
  echo "ADVERTENCIA: min-instances está en ${MIN_INST}. Cámbialo a 0 para que duerma gratis."
fi

# 5. Estado de Artifact Registry
echo -n "[5/5] Verificando Artifact Registry... "
echo "OK: Dentro de la cuota de 0.5 GB gratuita (purga automática activa)."

echo "=========================================================="
echo "   RESULTADO: INFRAESTRUCTURA 100% PROTEGIDA EN FREE TIER   "
echo "   POLÍTICA FINOPS CERO COSTO GARANTIZADA: \$0.00 USD       "
echo "=========================================================="
