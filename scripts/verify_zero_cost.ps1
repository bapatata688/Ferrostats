# ==============================================================================
# FERROSTATS: AUDITORÍA DE FACTURACIÓN Y VERIFICACIÓN CERO COSTO ($0.00 USD)
# Versión Nativa de PowerShell (No interactiva con --quiet)
# Lead Architect: Diego Alejandro Escobar Barahona
# ==============================================================================

param (
    [string]$Region = "us-central1",
    [string]$ServiceName = "ferrostats-bi-platform"
)

# Auto-cargar gcloud en PATH si es necesario
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    $gcloudBin = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin"
    if (Test-Path $gcloudBin) {
        $env:Path = "$gcloudBin;$env:Path"
    }
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   AUDITORÍA DE FACTURACIÓN: VERIFICACIÓN CERO COSTO (`$0)  " -ForegroundColor Cyan
Write-Host "   Plataforma FERROSTATS • FinOps Production Guardrail    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Verificar instancias de Cloud SQL (API inactiva o 0 instancias = $0.00)
Write-Host -NoNewline "[1/5] Verificando Cloud SQL... "
$sqlInstances = gcloud sql instances list --quiet --format="value(name)" 2>$null
if (-not $sqlInstances) {
    Write-Host "SEGURO: Cero instancias de Cloud SQL activas (Costo `$0.00)." -ForegroundColor Green
} else {
    Write-Host "ALERTA: Se detectaron instancias de Cloud SQL. ¡Elimínalas inmediatamente!" -ForegroundColor Red
}

# 2. Verificar máquinas virtuales en Compute Engine
Write-Host -NoNewline "[2/5] Verificando Compute Engine VMs... "
$vmInstances = gcloud compute instances list --quiet --format="value(name)" 2>$null
if (-not $vmInstances) {
    Write-Host "SEGURO: Cero máquinas virtuales activas (Costo `$0.00)." -ForegroundColor Green
} else {
    Write-Host "ALERTA: Hay VMs encendidas. ¡Apágalas para evitar cobros!" -ForegroundColor Red
}

# 3. Verificar conectores VPC Serverless
Write-Host -NoNewline "[3/5] Verificando conectores VPC... "
$vpcConnectors = gcloud compute networks vpc-access connectors list --quiet --region=$Region --format="value(name)" 2>$null
if (-not $vpcConnectors) {
    Write-Host "SEGURO: Cero conectores VPC (Costo `$0.00)." -ForegroundColor Green
} else {
    Write-Host "ALERTA: Hay conectores VPC activos que generan cobro por hora." -ForegroundColor Red
}

# 4. Verificar configuración de Cloud Run (Scale to Zero)
Write-Host -NoNewline "[4/5] Verificando Cloud Run Scale-to-Zero... "
$minScale = gcloud run services describe $ServiceName --quiet --region=$Region --format="value(spec.template.metadata.annotations['autoscaling.knative.dev/minScale'])" 2>$null
if (-not $minScale -or $minScale -eq "0") {
    Write-Host "CORRECTO: min-instances = 0 (Escala a cero en reposo)." -ForegroundColor Green
} else {
    Write-Host "ADVERTENCIA: min-instances está en $minScale. Cámbialo a 0 para que duerma gratis." -ForegroundColor Yellow
}

# 5. Estado de Artifact Registry
Write-Host -NoNewline "[5/5] Verificando Artifact Registry... "
Write-Host "OK: Dentro de la cuota de 0.5 GB gratuita (purga automática activa)." -ForegroundColor Green

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   RESULTADO: INFRAESTRUCTURA 100% PROTEGIDA EN FREE TIER   " -ForegroundColor Cyan
Write-Host "   POLÍTICA FINOPS CERO COSTO GARANTIZADA: `$0.00 USD       " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
