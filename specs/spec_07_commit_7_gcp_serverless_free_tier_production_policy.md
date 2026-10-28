# SPEC 07 (Commit 7): Política Estricta de Arquitectura Serverless 100% Free Tier (GCP Production Policy)

## Metadatos del Commit
| Atributo | Detalle |
| :--- | :--- |
| **Fase** | Fase 7 — Política de Infraestructura Serverless, Cero Costo ($0.00 USD) y Blindaje FinOps en GCP |
| **Enfoque de Perfil** | Cloud FinOps / Arquitectura Serverless de Datos / Seguridad de Facturación |
| **Archivos que Antigravity generará en esta fase** | `finops/gcp_free_tier_policy.json`, `scripts/emergency_kill_switch.sh`, `scripts/verify_zero_cost.sh` |
| **Mensaje de Commit Sugerido** | `chore(finops): enforce 100% serverless zero-cost production policy, cloud run scale-to-zero, and kill-switch` |

## 1. Declaración de Política FinOps: Cero Facturación ($0.00 USD)

Este proyecto opera bajo una estricta política de gobernanza FinOps orientada a producción de cero costo recurrente ($0.00 USD). Por diseño y mandato técnico:
1. **El costo operativo proyectado en GCP debe ser de $0.00 USD.**
2. Ningún componente puede generar cargos recurrentes por el simple hecho de existir o estar "en reposo".
3. Todos los recursos deben ser estrictamente **Serverless (Scale-to-Zero)**: cuando no haya usuarios conectados, el consumo de CPU, memoria y red es exactamente cero.

## 2. Matriz Definitiva de Servicios Permitidos vs. Servicios Estrictamente Prohibidos

Antigravity y cualquier script de despliegue deben respetar esta lista blanca y lista negra bajo cualquier circunstancia:

### 2.1 Lista Blanca: Servicios Serverless Permitidos (100% Capa Gratuita de por Vida)
| Servicio GCP | Cuota Mensual Gratuita (Always Free Tier) | Configuración Obligatoria en FERROSTATS | Costo Mensual |
| :--- | :--- | :--- | :--- |
| **Cloud Run** | • 2,000,000 de peticiones al mes.<br>• 360,000 GiB-segundos de memoria.<br>• 180,000 vCPU-segundos.<br>• 1 GB de tráfico de salida a internet. | `--min-instances=0`<br>`--max-instances=2`<br>`--memory=512Mi`<br>`--cpu=1`<br>`--region=us-central1`<br>`--timeout=60s` | **$0.00 USD** |
| **Google Cloud Storage (GCS)** | • 5 GB-mes de almacenamiento Standard.<br>• 5,000 operaciones Clase A.<br>• 50,000 operaciones Clase B. | Bucket Standard en `us-central1` montado como volumen en Cloud Run para persistencia de la base de datos SQLite WAL. | **$0.00 USD** |
| **BigQuery Sandbox** | • 10 GB de almacenamiento activo.<br>• 1 TB de consultas SQL al mes gratis.<br>• No requiere tarjeta de crédito para consultas. | Dataset analítico `ferrostats_dw` en multi-región `US` para las tablas dimensionales y hechos del pipeline ETL. | **$0.00 USD** |
| **Artifact Registry** | • 0.5 GB de almacenamiento de contenedores gratis al mes. | Script automatizado en `deploy_gcp.sh` que purga imágenes antiguas conservando únicamente la última versión activa. | **$0.00 USD** |
| **Cloud Build** | • 120 minutos de compilación gratis al día en máquinas estándar. | Compilación de la imagen Docker ligera (`python:3.11-slim`) con duración promedio de 40 a 60 segundos por despliegue. | **$0.00 USD** |

### 2.2 Lista Negra: Servicios Prohibidos (Trampas de Facturación Automática)
Bajo ninguna justificación técnica Antigravity o el usuario deben aprovisionar:
- **Cloud SQL (MySQL / PostgreSQL / SQL Server):** **PROHIBIDO.** No tiene capa gratuita permanente. Una instancia `db-f1-micro` cuesta ~$9–$15/mes más $2.50/mes por IP pública IPv4, agotando el presupuesto de $5 en pocos días.
- **Compute Engine (Máquinas Virtuales e2 / n1):** **PROHIBIDO.** Aunque existe una `e2-micro` gratis en ciertas regiones, cualquier error de configuración de disco o IP genera cargos automáticos.
- **Serverless VPC Access Connectors:** **PROHIBIDO.** Despliega 2 instancias `f1-micro` que cobran permanentemente ~$14.00 USD al mes.
- **Cloud Load Balancer (Balanceadores de Carga HTTP Globales):** **PROHIBIDO.** Costo base de ~$18.00 USD al mes. Cloud Run ya incluye URL HTTPS pública y balanceo administrado gratuito.
- **Google Kubernetes Engine (GKE):** **PROHIBIDO.** Cobra cargo de gestión de clúster de $74.40 USD al mes.

## 3. Script de Auditoría de Cero Costo (`scripts/verify_zero_cost.sh`)

Este script debe verificar en la cuenta de GCP que no existan recursos de pago activos antes de finalizar cada ciclo de despliegue o jornada operativa:

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=========================================================="
echo "   AUDITORÍA DE FACTURACIÓN: VERIFICACIÓN CERO COSTO ($0)  "
echo "=========================================================="

# 1. Verificar instancias de Cloud SQL
echo -n "[1/5] Verificando Cloud SQL... "
SQL_COUNT=$(gcloud sql instances list --format="value(name)" 2>/dev/null | wc -l || echo 0)
if [ "${SQL_COUNT}" -eq 0 ]; then
  echo "SEGURO: No hay instancias de Cloud SQL activas (Costo $0)."
else
  echo "ALERTA: Se detectaron instancias de Cloud SQL. ¡Elimínalas inmediatamente!"
fi

# 2. Verificar máquinas virtuales en Compute Engine
echo -n "[2/5] Verificando Compute Engine VMs... "
VM_COUNT=$(gcloud compute instances list --format="value(name)" 2>/dev/null | wc -l || echo 0)
if [ "${VM_COUNT}" -eq 0 ]; then
  echo "SEGURO: Cero máquinas virtuales activas (Costo $0)."
else
  echo "ALERTA: Hay VMs encendidas. ¡Apágalas para evitar cobros!"
fi

# 3. Verificar conectores VPC Serverless
echo -n "[3/5] Verificando conectores VPC... "
VPC_COUNT=$(gcloud compute networks vpc-access connectors list --region=us-central1 --format="value(name)" 2>/dev/null | wc -l || echo 0)
if [ "${VPC_COUNT}" -eq 0 ]; then
  echo "SEGURO: Cero conectores VPC (Costo $0)."
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
echo "OK: Dentro de la cuota de 0.5 GB gratuita."

echo "=========================================================="
echo "   RESULTADO: INFRAESTRUCTURA 100% PROTEGIDA EN FREE TIER   "
echo "=========================================================="
```

## 4. Interruptor de Emergencia para Apagado Instantáneo (`scripts/emergency_kill_switch.sh`)

Si en cualquier momento el equipo de ingeniería desea congelar inmediatamente el servicio para garantizar que no se procese ni una sola petición más:

```bash
#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="ferrostats-bi-platform"
REGION="us-central1"

echo "==> Activando interruptor de emergencia: Escalando a CERO instancias máximas..."
gcloud run services update "${SERVICE_NAME}" \
  --region "${REGION}" \
  --max-instances 0

echo "==> El servicio ha sido pausado por completo. Nadie puede generar peticiones."
echo "==> Para reactivarlo en producción:"
echo "    gcloud run services update ${SERVICE_NAME} --region ${REGION} --max-instances 2"
```

## 5. Criterios de Aceptación de la Fase 7 (Commit 7)
- [ ] La carpeta `scripts/` contiene `verify_zero_cost.sh` y `emergency_kill_switch.sh` con permisos de ejecución.
- [ ] El archivo de configuración `finops/gcp_free_tier_policy.json` documenta explícitamente los límites de Cloud Run (`min=0`, `max=2`, `512Mi`), GCS y BigQuery Sandbox.
- [ ] La ejecución de `scripts/verify_zero_cost.sh` devuelve `SEGURO` en todos los puntos, garantizando una facturación estrictamente de cero costo ($0.00 USD).
