# =====================================================================
# KingsCode - corrida FINAL de una mitad de las 992 (GPU-2 = parte 1, GPU-3 = parte 2)
#
#   powershell -ExecutionPolicy Bypass -File tools\kingscode_mitad.ps1 -Parte 1     (GPU-2)
#   powershell -ExecutionPolicy Bypass -File tools\kingscode_mitad.ps1 -Parte 2     (GPU-3)
#   ... -Resume   si se corto (reanuda sin repetir lo hecho)
#
# Configuracion final (la mejor medida en la muestra): -Recomendada -PromptVersion v6
#   = Qwen3-8B BF16 temp 0 + BM25 + grafo + consultas por opcion, k=8, prompt v6, citas completadas
#     y 5 menciones verificadas (+ parser que recupera JSON en bloque de codigo). v7, v9, hibrido y
#     fit se midieron y no superaron a v6.
# Corpus: el de Luis (39,02 con v4). Se busca su respaldo en OneDrive / C:\ / Descargas; si existe
# y el corpus local no es identico, se restaura y se verifica archivo por archivo. Si no existe, se usa
# el corpus local (o el diagnostico lo descarga de las fuentes oficiales).
# Al terminar: valida la mitad y la copia a OneDrive\KingsCode\final_p<N>.jsonl para unir.
# =====================================================================
param(
    [Parameter(Mandatory = $true)] [ValidateSet("1", "2")] [string]$Parte,
    [switch]$Resume,
    [string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia"
)
$ErrorActionPreference = "Stop"
function Paso($m) { Write-Host ""; Write-Host "================ $m ================" -ForegroundColor Cyan }
foreach ($v in "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE") { Remove-Item "Env:$v" -ErrorAction SilentlyContinue }
Set-Location $Work
$Py = "$Work\.venv\Scripts\python.exe"
$Run = "final_p$Parte"
Write-Host "Parte $Parte | commit $((git rev-parse --short HEAD).Trim()) | corrida $Run"

Paso "1/5 Corpus: buscar el respaldo de Luis (el mejor)"
$Candidatos = @("$HOME\kc_snapshot_luis", "$env:OneDrive\KingsCode\kc_snapshot_luis", "C:\kc_snapshot_luis", "$HOME\Downloads\kc_snapshot_luis",
                "$HOME\Downloads\kc_snapshot_luis\kc_snapshot_luis", "$HOME\kc_snapshot_luis")
$Snap = $Candidatos | Where-Object { $_ -and (Test-Path "$_\SHA256SUMS.txt") } | Select-Object -First 1
if ($Resume) {
    Write-Host "-Resume: se conserva el corpus actual (debe ser el mismo con el que empezo esta mitad)."
} elseif ($Snap) {
    Write-Host "Respaldo de Luis encontrado: $Snap"
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\kingscode_snapshot.ps1 -Accion verificar -Origen $Snap
    if ($LASTEXITCODE -ne 0) {
        Write-Host "El corpus local no es el de Luis: se restaura." -ForegroundColor Yellow
        powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\kingscode_snapshot.ps1 -Accion restaurar -Origen $Snap
        if ($LASTEXITCODE -ne 0) { throw "STOP: no se pudo restaurar el corpus de Luis desde $Snap (copia incompleta?)." }
    } else { Write-Host "El corpus local YA es el de Luis." -ForegroundColor Green }
} else {
    Write-Host "AVISO: no se encontro el respaldo de Luis en: $($Candidatos -join ' | '). Se usa el corpus local (o se descarga)." -ForegroundColor Yellow
}

Paso "2/5 GPU libre"
$Gpu = (& nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | Select-Object -First 1).Trim()
Write-Host "VRAM ocupada: $Gpu MiB"
if ([int]$Gpu -gt 3000) { query user 2>$null; throw "STOP: la GPU esta ocupada ($Gpu MiB). Cierra la interfaz u otra sesion (logoff <ID>) y repite." }

Paso "3/5 Partir las 992 (deterministico, igual en ambos PCs)"
& $Py tools\split_test.py data\test_992.jsonl 2
if ($LASTEXITCODE -ne 0) { throw "fallo split_test" }

Paso "4/5 Correr la parte $Parte con la configuracion final (~2,3 h)"
# Start-Process joins arguments with spaces: the multi-word value must carry its own quotes,
# otherwise -PromptVersion v6 is lost (2026-10-03: a half started as v4).
$Args2 = @("-Flags", "`"-Recomendada -PromptVersion v6`"", "-InputFile", "data\test_992.parte$Parte.jsonl", "-RunName", $Run)
if ($Resume) { $Args2 += "-Resume" }
$p = Start-Process -FilePath "powershell.exe" -NoNewWindow -Wait -PassThru -ArgumentList (@("-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
     "`"$((Resolve-Path .\tools\kingscode_final.ps1).Path)`"") + $Args2)
$Sub = "reports\decoder_diagnostic\$Run\batch\submissions.jsonl"
if (-not (Test-Path $Sub)) { throw "No existe ${Sub}; revisar arriba y repetir con -Resume." }

Paso "5/5 Validar la mitad y copiarla para unir"
& $Py tools\validate_test_submission.py --test "data\test_992.parte$Parte.jsonl" $Sub
$Dest = $(if ($env:OneDrive) { "$env:OneDrive\KingsCode" } else { "$HOME" })
New-Item -ItemType Directory -Force $Dest | Out-Null
Copy-Item $Sub "$Dest\final_p$Parte.jsonl" -Force
Write-Host "Mitad $Parte lista: $Dest\final_p$Parte.jsonl" -ForegroundColor Green
Write-Host "Verificacion en vivo de los ids de esta mitad: en ESTE PC, sin cambiar codigo ni corpus hasta las 17:00." -ForegroundColor Green
