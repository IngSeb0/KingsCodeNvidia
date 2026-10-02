# =====================================================================
# KingsCode - TODO en un comando: mismo corpus en los dos PCs + pruebas contra 39,02
#
# PC donde salio el 39,02 (corpus nuevo):
#   powershell -ExecutionPolicy Bypass -File tools\kingscode_todo.ps1 -Rol fuente -Compartida "<carpeta compartida>"
# Otro PC:
#   powershell -ExecutionPolicy Bypass -File tools\kingscode_todo.ps1 -Rol destino -Compartida "<carpeta compartida>"
#
# <carpeta compartida>: una ruta que vean los dos PCs (OneDrive sincronizado, carpeta de red o USB).
# La fuente deja ahi el respaldo del corpus; el destino espera a que aparezca, lo restaura y verifica.
# Despues cada PC corre su mitad de las pruebas contra la base 39,02 y muestra la tabla final.
#   fuente : v6, doccap3            destino: recomendada (debe reproducir 39,02), option_plan
# El respaldo de la fuente es tambien el respaldo para el sabado.
# =====================================================================
param(
    [Parameter(Mandatory = $true)] [ValidateSet("fuente", "destino")] [string]$Rol,
    [Parameter(Mandatory = $true)] [string]$Compartida,
    [double]$Base = 39.02,
    [string[]]$Variantes = @(),
    [string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia",
    [int]$EsperaMaxMin = 60
)
$ErrorActionPreference = "Stop"
function Paso($m) { Write-Host ""; Write-Host ">>> $m" -ForegroundColor Cyan }
Set-Location $Work

Paso "1. Codigo actualizado (main)"
git fetch origin main
$Rama = (git branch --show-current).Trim()
if ($Rama -ne "main") { git checkout main; if ($LASTEXITCODE -ne 0) { throw "No se pudo pasar a main (hay cambios locales sin guardar?)" } }
git pull --ff-only origin main
if ($LASTEXITCODE -ne 0) { throw "git pull fallo: si es por carpetas de reports sin seguimiento, muevelas fuera del repo y repite." }
Write-Host "main @ $((git rev-parse --short HEAD).Trim())"

Paso "2. GPU libre"
$Gpu = (& nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader,nounits | Select-Object -First 1) -split ","
Write-Host ("{0}: {1} / {2} MiB ocupados" -f $Gpu[0].Trim(), $Gpu[1].Trim(), $Gpu[2].Trim())
if ([int]$Gpu[1].Trim() -gt 3000) {
    & nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
    query user 2>$null
    throw "STOP: la GPU ya esta ocupada. Cierra la interfaz/corrida que la usa o la sesion del otro usuario (logoff <ID>) y repite."
}

New-Item -ItemType Directory -Force $Compartida | Out-Null
if ($Rol -eq "fuente") {
    Paso "3. Respaldo del corpus de este PC (el del 39,02) en $Compartida"
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\kingscode_snapshot.ps1 -Accion crear -Destino $Compartida
    if ($LASTEXITCODE -ne 0) { throw "fallo el respaldo del corpus" }
    if (-not $Variantes) { $Variantes = @("v6", "doccap3") }
} else {
    Paso "3. Esperar el respaldo de la fuente en $Compartida (hasta $EsperaMaxMin min) y restaurarlo"
    $Limite = (Get-Date).AddMinutes($EsperaMaxMin)
    while (-not (Test-Path "$Compartida\SHA256SUMS.txt")) {
        if ((Get-Date) -gt $Limite) { throw "No aparecio $Compartida\SHA256SUMS.txt: la fuente aun no termina el respaldo o la carpeta no esta compartida." }
        Write-Host "  esperando el respaldo ... $((Get-Date).ToString('HH:mm:ss'))"
        Start-Sleep -Seconds 30
    }
    Start-Sleep -Seconds 20   # deja terminar la sincronizacion del tar.gz
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\kingscode_snapshot.ps1 -Accion restaurar -Origen $Compartida
    if ($LASTEXITCODE -ne 0) { throw "la restauracion o la verificacion del corpus fallo (copia incompleta o corrupta: repetir cuando termine de sincronizar)" }
    if (-not $Variantes) { $Variantes = @("recomendada", "option_plan") }
}

Paso "4. Pruebas contra la base $Base : $($Variantes -join ', ')"
$p = Start-Process -FilePath "powershell.exe" -NoNewWindow -Wait -PassThru -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$((Resolve-Path .\tools\kingscode_variantes.ps1).Path)`"",
    "-Variantes", ($Variantes -join ","), "-Base", [string]$Base)
Write-Host ""
Write-Host "Listo ($Rol). Pegar la tabla final y las lineas del proxy y de alineacion de citas." -ForegroundColor Green
if ($Rol -eq "destino") { Write-Host "'recomendada' debe dar ${Base}; si coincide, los dos PCs son intercambiables (sabado: repartir las 992 y verificar en cualquiera)." -ForegroundColor Green }
Write-Host "Respaldo del corpus para el sabado: $Compartida (copiarlo tambien a una USB)." -ForegroundColor Green
