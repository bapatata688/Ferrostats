# ==============================================================================
# FERROSTATS: INTERRUPTOR DE EMERGENCIA (KILL-SWITCH INSTANTÁNEO)
# Versión Nativa de PowerShell
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

Write-Host "==================================================================" -ForegroundColor Red
Write-Host "  ACTIVANDO INTERRUPTOR DE EMERGENCIA: SCALE-TO-ZERO ABSOLUTO     " -ForegroundColor Red
Write-Host "  Servicio: $ServiceName | Región: $Region                        " -ForegroundColor Red
Write-Host "==================================================================" -ForegroundColor Red

Write-Host "==> Escalando a CERO instancias máximas en Cloud Run..." -ForegroundColor Yellow
gcloud run services update $ServiceName --region $Region --max-instances 0

Write-Host "==> [OK] El servicio ha sido congelado por completo." -ForegroundColor Green
Write-Host "==> No se procesará ni una sola petición y el costo es estrictamente `$0.00 USD." -ForegroundColor Green
Write-Host ""
Write-Host "==> Para reactivar el servicio en producción:" -ForegroundColor Cyan
Write-Host "    gcloud run services update $ServiceName --region $Region --max-instances 2" -ForegroundColor White
Write-Host "==================================================================" -ForegroundColor Red
