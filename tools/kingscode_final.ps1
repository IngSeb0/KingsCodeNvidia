# =====================================================================
# KingsCode - corrida final + DOCUMENTO_FINAL.md (un solo comando)
#
# Corre la configuracion elegida con progreso en vivo y verificacion en vivo simulada, y al terminar
# escribe <corrida>\DOCUMENTO_FINAL.md (puntaje, tiempo, verificacion, calidad del texto y de las
# citas, taxonomia y decision) con tools\final_document.py. Sin RAGAS salvo -Ragas (gasta credito).
#
# Muestra (eleccion de la configuracion):
#   powershell -ExecutionPolicy Bypass -File tools\kingscode_final.ps1
#   powershell -ExecutionPolicy Bypass -File tools\kingscode_final.ps1 -Flags "-Recomendada -MaxContext 16384"
# Sabado, set ciego (misma configuracion; si se corta, repetir con -Resume y el mismo -RunName):
#   powershell -ExecutionPolicy Bypass -File tools\kingscode_final.ps1 -Flags "<flags elegidos>" -InputFile data\test_992.jsonl -RunName final_992
#   powershell -ExecutionPolicy Bypass -File tools\kingscode_final.ps1 -Flags "<flags elegidos>" -InputFile data\test_992.jsonl -RunName final_992 -Resume
# =====================================================================
param(
    [string]$Flags = "-Recomendada",
    [string]$InputFile = "data\sample_50.jsonl",
    [string]$RunName = "",
    [switch]$Resume,
    [switch]$Ragas,
    [switch]$Pull,
    [string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia"
)
$ErrorActionPreference = "Stop"
Set-Location $Work
if ($Pull) { git pull --ff-only origin main; if ($LASTEXITCODE -ne 0) { throw "git pull fallo" } }
if (-not $RunName) { $RunName = "final_$((Get-Date).ToString('yyyyMMdd_HHmmss'))" }
$Py = "$Work\.venv\Scripts\python.exe"
$S = (Resolve-Path ".\tools\kingscode_pc_nueva_diagnostico.ps1").Path
$Args2 = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$S`"", "-SkipSmoke", "-NoPull",
           "-InputFile", $InputFile, "-RunName", $RunName) + @($Flags -split "\s+" | Where-Object { $_ })
if ($Resume) { $Args2 += "-Resume" }
if ($Ragas) { $Args2 += "-Ragas" }
Write-Host "Commit: $((git rev-parse --short HEAD).Trim()) | Flags: $Flags | Entrada: $InputFile | Corrida: $RunName" -ForegroundColor Cyan
# Attached to this console: the [batch] progress lines are shown live.
$p = Start-Process -FilePath "powershell.exe" -ArgumentList $Args2 -NoNewWindow -Wait -PassThru
$Out = "reports\decoder_diagnostic\$RunName"
if ($p.ExitCode -ne 0) { Write-Host "La corrida termino con codigo $($p.ExitCode); se genera el documento con lo que haya en $Out." -ForegroundColor Yellow }
if (-not (Test-Path "$Out\batch\submissions.jsonl")) { throw "No existe $Out\batch\submissions.jsonl: revisar la salida de arriba (reanudar con -Resume -RunName $RunName)." }
& $Py tools\final_document.py $Out
Write-Host "`nDocumento final: $Work\$Out\DOCUMENTO_FINAL.md" -ForegroundColor Green
if ($InputFile -notlike "*sample_50*") { Write-Host "Entrega: $Work\submissions.jsonl (copiada por el diagnostico). No borrar $Out ni el corpus hasta terminar la verificacion en vivo." -ForegroundColor Green }
