# Actualiza los secretos B2_KEY_ID y B2_APP_KEY del Worker de recepcion QR
# (recepcion-ilutrek) para que coincidan con las credenciales B2 que usa
# actualmente la app de escritorio (leidas directamente del .env, sin
# necesidad de copiar/pegar a mano y arriesgarse a un error de transcripcion).
#
# Antes de ejecutar este script, en la misma terminal:
#   $env:CLOUDFLARE_API_TOKEN = "tu_token_de_cloudflare"
#
# Luego, desde la carpeta cloudflare-worker-recepcion:
#   .\actualizar_secretos_b2.ps1

$ErrorActionPreference = "Stop"

if (-not $env:CLOUDFLARE_API_TOKEN) {
    Write-Host "Falta CLOUDFLARE_API_TOKEN. Ejecuta primero:" -ForegroundColor Red
    Write-Host '  $env:CLOUDFLARE_API_TOKEN = "tu_token_de_cloudflare"'
    exit 1
}

$envPath = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path $envPath)) {
    throw "No se encuentra el .env en: $envPath"
}
$envContent = Get-Content $envPath

function Get-EnvValue($name) {
    $line = $envContent | Where-Object { $_ -match "^$name=" } | Select-Object -First 1
    if (-not $line) { throw "No se encontro la variable $name en el .env" }
    return ($line -replace "^$name=", "").Trim()
}

$keyId = Get-EnvValue "B2_KEY_ID"
$appKey = Get-EnvValue "B2_APPLICATION_KEY"

Write-Host "KEY_ID leido del .env: $keyId (longitud $($keyId.Length))"
Write-Host "APP_KEY leido del .env: longitud $($appKey.Length) caracteres"

Write-Host "`nActualizando secreto B2_KEY_ID en el Worker..." -ForegroundColor Cyan
$keyId | npx wrangler secret put B2_KEY_ID

Write-Host "`nActualizando secreto B2_APP_KEY en el Worker..." -ForegroundColor Cyan
$appKey | npx wrangler secret put B2_APP_KEY

Write-Host "`nListo. Comprueba la lista de secretos con:" -ForegroundColor Green
Write-Host "  npx wrangler secret list"
