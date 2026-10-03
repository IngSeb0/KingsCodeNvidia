# =====================================================================
# KingsCode - MEJORA: busqueda semantica (BM25 + encoder Qwen3-Embedding, RRF) en semiabiertas y
# abiertas, repartida en las 3 GPUs. Las cerradas (290) se quedan con la corrida final ya hecha
# (su camino BM25 + opciones no cambia).
#
#   GPU-1:  powershell -ExecutionPolicy Bypass -File tools\kingscode_mejora.ps1 -Parte muestra   (medir, ~12 min)
#           y despues  ... -Parte 3
#   GPU-2:  powershell -ExecutionPolicy Bypass -File tools\kingscode_mejora.ps1 -Parte 1
#   GPU-3:  powershell -ExecutionPolicy Bypass -File tools\kingscode_mejora.ps1 -Parte 2
#   ... -Resume   si se corto (reanuda sin repetir)
#
# Cada parte = 234 preguntas (semi_open + open_ended, reparto round-robin fijo en
# data\test_992.mejora_parteN.jsonl). Al terminar sube el resultado a la rama entrega-mejora_pN.
# Por que: en casos largos BM25 suma palabras sueltas (VIH, medicamento, salud) y trae sentencias
# de salud; la norma clave (p.ej. Ley 1581 de 2012, datos sensibles) no comparte esas palabras.
# El encoder compara significado ("datos en salud" ~ "datos sensibles") y la trae.
# =====================================================================
param(
    [Parameter(Mandatory = $true)] [ValidateSet("1", "2", "3", "muestra")] [string]$Parte,
    [switch]$Resume,
    [string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia"
)
$ErrorActionPreference = "Stop"
function Paso($m) { Write-Host ""; Write-Host "================ $m ================" -ForegroundColor Cyan }
foreach ($v in "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE") { Remove-Item "Env:$v" -ErrorAction SilentlyContinue }
Set-Location $Work
$Py = "$Work\.venv\Scripts\python.exe"
$Flags = "-Recomendada -PromptVersion v6 -RetrieverMode hybrid -HybridFormats semi_open,open_ended"
if ($Parte -eq "muestra") { $Run = "mejora_muestra"; $InFile = "data\sample_50.jsonl" }
else { $Run = "mejora_p$Parte"; $InFile = "data\test_992.mejora_parte$Parte.jsonl" }

Paso "1/5 Codigo de main (con la busqueda semantica)"
$ErrorActionPreference = "Continue"
git fetch origin main 2>&1 | Out-Host
git checkout -B main origin/main 2>&1 | Out-Host
$ok = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($ok -ne 0) { throw "STOP: git no pudo pasar a origin/main (cambios locales en archivos versionados?). Revisar 'git status'." }
Write-Host "commit $((git rev-parse --short HEAD).Trim())"
if (-not (Select-String -Path tools\member_b.py -Pattern "hybrid-formats" -Quiet)) { throw "STOP: este main no trae --hybrid-formats" }

Paso "2/5 Corpus del 39 (el mismo de las mitades)"
$Sha = (Get-FileHash corpus\passages.jsonl -Algorithm SHA256).Hash.ToLower()
Write-Host "corpus\passages.jsonl $($Sha.Substring(0,12))"
if (-not $Sha.StartsWith("58135a0cf92c")) {
    $Snap = @("$HOME\kc_snapshot_luis", "$env:OneDrive\KingsCode\kc_snapshot_luis") | Where-Object { $_ -and (Test-Path "$_\SHA256SUMS.txt") } | Select-Object -First 1
    if (-not $Snap) { throw "STOP: el corpus no es el del 39 y no hay respaldo. Correr: tools\compartir_corpus.ps1 -Accion bajar" }
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\kingscode_snapshot.ps1 -Accion restaurar -Origen $Snap
    if ($LASTEXITCODE -ne 0) { throw "STOP: no se pudo restaurar el corpus desde $Snap" }
}

Paso "3/5 GPU libre"
$Gpu = (& nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | Select-Object -First 1).Trim()
Write-Host "VRAM ocupada: $Gpu MiB"
if ([int]$Gpu -gt 3000) { throw "STOP: la GPU esta ocupada ($Gpu MiB). Cerrar la interfaz (Ctrl+C en su ventana) u otra corrida y repetir." }

Paso "4/5 Correr $Run ($InFile) - la primera vez construye el indice semantico (~5 min)"
if (-not (Test-Path $InFile)) { throw "STOP: no existe $InFile" }
$Args2 = @("-Flags", "`"$Flags`"", "-InputFile", $InFile, "-RunName", $Run)
if ($Resume) { $Args2 += "-Resume" }
$p = Start-Process -FilePath "powershell.exe" -NoNewWindow -Wait -PassThru -ArgumentList (@("-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
     "`"$((Resolve-Path .\tools\kingscode_final.ps1).Path)`"") + $Args2)
$Sub = "reports\decoder_diagnostic\$Run\batch\submissions.jsonl"
if (-not (Test-Path $Sub)) { throw "No existe ${Sub}; revisar arriba y repetir con -Resume." }

Paso "5/5 Subir el resultado (rama entrega-$Run)"
if ($Parte -eq "muestra") {
    $E = "reports\decoder_diagnostic\$Run\evaluation_official.json"
    if (Test-Path $E) { Get-Content $E -Raw | Write-Host }
    Write-Host "Comparar con la base v6 BM25 del corpus del 39 (39,02/50 sin RAGAS). Avisar el numero." -ForegroundColor Yellow
} else {
    & $Py tools\validate_test_submission.py --test $InFile $Sub
}
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\subir_resultado.ps1 -Corrida $Run
Write-Host "$Run listo y subido. No cambiar codigo ni corpus en este PC hasta las 17:00 (verificacion en vivo)." -ForegroundColor Green
