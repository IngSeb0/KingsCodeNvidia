# =====================================================================
# KingsCode - respaldo (snapshot) del corpus + indice de HOY y restauracion verificada MANANA
#
# Hoy, en el PC que produjo la configuracion final (sin corridas activas):
#   powershell -ExecutionPolicy Bypass -File tools\kingscode_snapshot.ps1 -Accion crear
#   -> $HOME\kc_snapshot\kingscode_corpus_<fecha>.tar.gz + SNAPSHOT_HASHES.json + SHA256SUMS.txt
#   Copiar esa carpeta a USB/OneDrive (son los datos, no el codigo: el codigo esta en GitHub).
#
# Manana, en cualquier PC con el repo clonado (mismo commit):
#   powershell -ExecutionPolicy Bypass -File tools\kingscode_snapshot.ps1 -Accion restaurar -Origen D:\kc_snapshot
#   -> extrae en el repo y verifica archivo por archivo que el corpus/indice es IDENTICO al de hoy.
# Luego correr siempre con -NoPull (no actualizar codigo) para que todo coincida.
# Los pesos de los modelos no se copian por defecto (se descargan por lock y se verifican); -IncluirModelos los agrega (~18 GB).
# =====================================================================
param(
    [ValidateSet("crear", "restaurar", "verificar")] [string]$Accion = "crear",
    [string]$Origen = "$HOME\kc_snapshot",
    [string]$Destino = "$HOME\kc_snapshot",
    [string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia",
    [switch]$IncluirModelos,   # agrega models\ (~18 GB) por si manana no hay internet para descargar por lock
    [string[]]$Carpetas = @("corpus", "corpus_v01_v02", "corpus_v01_v02_a1", "artifacts", ".kingscode_corpus_origin.txt")
)
$ErrorActionPreference = "Stop"
Set-Location $Work
$Py = "$Work\.venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }

if ($Accion -eq "crear") {
    if ($IncluirModelos) { $Carpetas += "models" }
    $Presentes = @($Carpetas | Where-Object { Test-Path $_ })
    if (-not $Presentes) { throw "No hay carpetas de corpus en $Work (esperaba: $($Carpetas -join ', '))." }
    New-Item -ItemType Directory -Force $Destino | Out-Null
    $Stamp = (Get-Date).ToString("yyyyMMdd_HHmm")
    $Tar = "$Destino\kingscode_corpus_$Stamp.tar.gz"
    Write-Host "Hash por archivo de: $($Presentes -join ', ') ..." -ForegroundColor Cyan
    & $Py tools\snapshot_hashes.py write "$Destino\SNAPSHOT_HASHES.json" @Presentes
    if ($LASTEXITCODE -ne 0) { throw "fallo el calculo de hashes" }
    Write-Host "Empaquetando en $Tar (puede tardar unos minutos) ..." -ForegroundColor Cyan
    tar -czf $Tar @Presentes
    if ($LASTEXITCODE -ne 0) { throw "fallo tar" }
    $Commit = (git rev-parse HEAD).Trim()
    @(
        "commit $Commit",
        ("{0}  {1}" -f (Get-FileHash $Tar -Algorithm SHA256).Hash.ToLower(), (Split-Path $Tar -Leaf)),
        ("{0}  SNAPSHOT_HASHES.json" -f (Get-FileHash "$Destino\SNAPSHOT_HASHES.json" -Algorithm SHA256).Hash.ToLower())
    ) | Set-Content -Encoding ascii "$Destino\SHA256SUMS.txt"
    Get-Content "$Destino\SHA256SUMS.txt"
    Write-Host ("Snapshot listo en {0} ({1:N0} MB). Copiar la carpeta completa a USB/OneDrive." -f $Destino, ((Get-Item $Tar).Length / 1MB)) -ForegroundColor Green
    Write-Host "Manana: git checkout $Commit (o el commit final) y -Accion restaurar -Origen <carpeta copiada>." -ForegroundColor Green
    exit 0
}

$Manifest = "$Origen\SNAPSHOT_HASHES.json"
if ($Accion -eq "restaurar") {
    $Tar = Get-ChildItem "$Origen\kingscode_corpus_*.tar.gz" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $Tar) { throw "No hay kingscode_corpus_*.tar.gz en $Origen" }
    $Esperado = (Get-Content "$Origen\SHA256SUMS.txt" | Where-Object { $_ -like "*$($Tar.Name)" }) -split "\s+" | Select-Object -First 1
    if ((Get-FileHash $Tar.FullName -Algorithm SHA256).Hash.ToLower() -ne $Esperado) { throw "STOP: el archivo $($Tar.Name) no coincide con SHA256SUMS.txt (copia corrupta)." }
    $Dirs = (Get-Content $Manifest -Raw | ConvertFrom-Json).folders
    foreach ($d in $Dirs) { if (Test-Path $d) { Rename-Item $d "$d.antes_$((Get-Date).ToString('HHmmss'))" } }
    Write-Host "Extrayendo $($Tar.Name) en $Work ..." -ForegroundColor Cyan
    tar -xzf $Tar.FullName
    if ($LASTEXITCODE -ne 0) { throw "fallo tar" }
}
& $Py tools\snapshot_hashes.py verify $Manifest
if ($LASTEXITCODE -ne 0) { throw "STOP: el corpus/indice NO es identico al snapshot." }
Write-Host "Corpus e indice identicos al snapshot. Correr con -NoPull para no cambiar el codigo." -ForegroundColor Green
