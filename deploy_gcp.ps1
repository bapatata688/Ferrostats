# ==============================================================================
# FERROSTATS: DESPLIEGUE EN GOOGLE CLOUD RUN (POWERSHELL / $0.00 FREE TIER)
# Lead Architect: Diego Alejandro Escobar Barahona
# ==============================================================================

param (
    [string]$ProjectId = "ferrostats",
    [string]$Region = "us-central1",
    [string]$ServiceName = "ferrostats-bi-platform"
)

$ErrorActionPreference = "Stop"

# Auto-detección y carga de gcloud en PATH si no está en la sesión actual
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    $gcloudBin = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin"
    if (Test-Path $gcloudBin) {
        $env:Path = "$gcloudBin;$env:Path"
    }
}

if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Error "No se encontró el ejecutable de gcloud. Asegúrate de tener instalado el Google Cloud SDK."
    exit 1
}

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  DESPLEGANDO FERROSTATS EN GOOGLE CLOUD RUN (POWERSHELL)" -ForegroundColor Cyan
Write-Host "  Proyecto GCP: $ProjectId | Región: $Region" -ForegroundColor Cyan
Write-Host "  Política FinOps: 100% Free Tier (Scale-to-Zero, `$0.00 USD)" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Configurar proyecto y habilitar APIs serverless
Write-Host "==> 1. Configurando proyecto GCP y servicios esenciales..." -ForegroundColor Yellow
gcloud config set project $ProjectId
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# 2. Desplegar en Cloud Run con Scale-to-Zero
Write-Host "==> 2. Construyendo y desplegando servicio Cloud Run (min-instances=0)..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
  --source . `
  --region $Region `
  --platform managed `
  --allow-unauthenticated `
  --min-instances 0 `
  --max-instances 2 `
  --memory 512Mi `
  --cpu 1 `
  --concurrency 80 `
  --timeout 60s `
  --quiet `
  --set-env-vars="ENV=production,DB_PATH=/tmp/ferrostats.db,ENABLE_BIGQUERY_SYNC=true"

# 3. Limpieza de imágenes antiguas en Artifact Registry
Write-Host "==> 3. Purgando versiones previas en Artifact Registry para respetar cuota gratuita (<0.5 GB)..." -ForegroundColor Yellow
$imageRepo = "$Region-docker.pkg.dev/$ProjectId/cloud-run-source-deploy/$ServiceName"
$prevEAP = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
$images = (& gcloud artifacts docker images list $imageRepo --sort-by=~UPDATE_TIME --format="value(version)" 2>$null)
$ErrorActionPreference = $prevEAP

if ($images) {
    $imgList = $images -split "`r?`n" | Where-Object { $_ -ne "" }
    if ($imgList.Count -gt 2) {
        $oldImages = $imgList | Select-Object -Skip 2
        $prevEAP2 = $ErrorActionPreference
        $ErrorActionPreference = "SilentlyContinue"
        foreach ($oldVersion in $oldImages) {
            $shortDigest = $oldVersion.Substring(0, [Math]::Min(18, $oldVersion.Length))
            Write-Host "  Eliminando digest antiguo: $shortDigest..." -ForegroundColor DarkGray
            (& gcloud artifacts docker images delete "$imageRepo@$oldVersion" --quiet 2>&1 | Out-Null)
        }
        $ErrorActionPreference = $prevEAP2
    }
}

$serviceUrl = gcloud run services describe $ServiceName --region $Region --format="value(status.url)" 2>$null

Write-Host "==================================================================" -ForegroundColor Green
Write-Host "  ¡DESPLIEGUE COMPLETADO EXITOSAMENTE!" -ForegroundColor Green
Write-Host "  URL Pública de Producción: $serviceUrl" -ForegroundColor Green
Write-Host "  Costo en Reposo: `$0.00 USD (Escalado a CERO instancias)" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
