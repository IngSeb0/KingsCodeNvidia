# =====================================================================
# KingsCode - CORRER TODO, nuevo, en un solo comando (sin parametros obligatorios)
#
#   powershell -ExecutionPolicy Bypass -File tools\kingscode_corre_todo.ps1
#
# 1. Codigo: pasa a main y lo actualiza.
# 2. GPU: se detiene con instrucciones si otra sesion/proceso ya la ocupa.
# 3. Corpus ACTUALIZADO: aparta el corpus actual (lo renombra a *.antes_<fecha>, no lo borra) y el
#    diagnostico vuelve a descargar HOY las fuentes oficiales + adiciones versionadas (asi salio el 39,02).
#    -MantenerCorpus usa el corpus que ya esta en la maquina.
# 4. Corre la base (v4, -Recomendada) y la mejor version (v6) sobre ese corpus y las compara.
# 5. Respalda el corpus usado en $HOME\kc_snapshot (para el sabado: -Accion restaurar).
# 6. Escribe DOCUMENTO_FINAL.md de la mejor version y dice cual usar.
# =====================================================================
param(
    [switch]$MantenerCorpus,
    [string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia"
)
$ErrorActionPreference = "Stop"
function Paso($m) { Write-Host ""; Write-Host "================ $m ================" -ForegroundColor Cyan }
$Inicio = Get-Date
Set-Location $Work
$Py = "$Work\.venv\Scripts\python.exe"

Paso "1/6 Codigo actualizado (main)"
git fetch origin main
if ((git branch --show-current).Trim() -ne "main") { git checkout main; if ($LASTEXITCODE -ne 0) { throw "No se pudo pasar a main (cambios locales sin guardar?)" } }
git pull --ff-only origin main
if ($LASTEXITCODE -ne 0) { throw "git pull fallo: si es por carpetas de reports sin seguimiento, muevelas fuera del repo y repite." }
$Commit = (git rev-parse --short HEAD).Trim()
Write-Host "main @ $Commit"

Paso "2/6 GPU libre"
$Gpu = (& nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader,nounits | Select-Object -First 1) -split ","
Write-Host ("{0}: {1} / {2} MiB ocupados" -f $Gpu[0].Trim(), $Gpu[1].Trim(), $Gpu[2].Trim())
if ([int]$Gpu[1].Trim() -gt 3000) {
    & nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
    query user 2>$null
    throw "STOP: la GPU ya esta ocupada. Cierra la interfaz/corrida que la usa o la sesion del otro usuario (logoff <ID>) y repite."
}

Paso "3/6 Corpus actualizado"
if ($MantenerCorpus) {
    Write-Host "-MantenerCorpus: se usa el corpus que ya esta en la maquina."
} else {
    $Stamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
    foreach ($d in @("corpus", "corpus_v01_v02", "corpus_v01_v02_a1", ".kingscode_corpus_origin.txt")) {
        if (Test-Path $d) { Rename-Item $d "$d.antes_$Stamp"; Write-Host "Apartado: $d -> $d.antes_$Stamp" }
    }
    Write-Host "El diagnostico descargara hoy las fuentes oficiales y reconstruira el corpus (10-20 min la primera vez)." -ForegroundColor Yellow
}

Paso "4/6 Base (v4) y mejor version (v6) sobre el mismo corpus"
$Antes = @(Get-ChildItem reports\decoder_diagnostic -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.Name })
$p = Start-Process -FilePath "powershell.exe" -NoNewWindow -Wait -PassThru -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$((Resolve-Path .\tools\kingscode_variantes.ps1).Path)`"",
    "-Variantes", "recomendada,v6", "-Base", "39.02")
$Nuevas = @(Get-ChildItem reports\decoder_diagnostic -Directory | Where-Object { $Antes -notcontains $_.Name -and (Test-Path "$($_.FullName)\evaluation_official.json") } | Sort-Object LastWriteTime)
$Res = foreach ($r in $Nuevas) {
    $e = Get-Content "$($r.FullName)\evaluation_official.json" -Raw | ConvertFrom-Json
    $s = Get-Content "$($r.FullName)\RESUMEN.json" -Raw | ConvertFrom-Json
    [pscustomobject]@{ corrida = $r.Name; dir = $r.FullName; prompt = $s.prompt_version; total = [double]$e.total_automatico.obtenidos
                       cerradas = [double]$e.cerradas.puntos; sin_respaldo = [double]$e.citas.tasa_sin_respaldo; horas_992 = [double]$s.proyeccion_992_horas }
}
if (-not $Res) { throw "No se produjo ninguna corrida evaluada: revisar la salida de arriba." }
$Res | Select-Object corrida, prompt, total, cerradas, sin_respaldo, horas_992 | Format-Table -AutoSize

Paso "5/6 Respaldo del corpus usado (para el sabado)"
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\kingscode_snapshot.ps1 -Accion crear -Destino "$HOME\kc_snapshot"

Paso "6/6 Documento final y decision"
$V4 = $Res | Where-Object { $_.prompt -like "*v4*" } | Select-Object -Last 1
$V6 = $Res | Where-Object { $_.prompt -like "*v6*" } | Select-Object -Last 1
$Gana = $V4
if ($V6 -and (-not $V4 -or ($V6.total -gt $V4.total -and $V6.cerradas -ge $V4.cerradas -and $V6.sin_respaldo -eq 0 -and $V6.horas_992 -le 5))) { $Gana = $V6 }
& $Py tools\final_document.py $Gana.dir | Out-Null
$Flags = $(if ($Gana -eq $V6) { "-Recomendada -PromptVersion v6" } else { "-Recomendada" })
Write-Host ""
Write-Host ("MEJOR VERSION: {0}  ->  {1}/50 sin RAGAS (cerradas {2}, {3} h para 992)" -f $Flags, $Gana.total, $Gana.cerradas, $Gana.horas_992) -ForegroundColor Green
if ($V4 -and $V6) { Write-Host ("v4 {0} | v6 {1} | diferencia {2:+0.00;-0.00}" -f $V4.total, $V6.total, ($V6.total - $V4.total)) -ForegroundColor Green }
Write-Host "Documento: $($Gana.dir)\DOCUMENTO_FINAL.md" -ForegroundColor Green
Write-Host "Respaldo del corpus: $HOME\kc_snapshot  (copiarlo a USB/OneDrive)" -ForegroundColor Green
Write-Host "Sabado: git checkout $Commit ; kingscode_snapshot.ps1 -Accion restaurar -Origen <copia> ; kingscode_final.ps1 -Flags `"$Flags`" -InputFile <set ciego> -RunName final_992" -ForegroundColor Green
Write-Host ("Total: {0:N0} min" -f ((Get-Date) - $Inicio).TotalMinutes) -ForegroundColor Green
