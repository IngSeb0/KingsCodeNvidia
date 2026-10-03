# =====================================================================
# KingsCode - pasar el corpus de un PC a otro por GitHub (rama aparte "corpus-39"; main no se toca)
#
# En el PC que TIENE el corpus bueno (GPU-1):
#   powershell -ExecutionPolicy Bypass -File tools\compartir_corpus.ps1 -Accion subir
# En los PCs que lo NECESITAN (GPU-2, GPU-3):
#   powershell -ExecutionPolicy Bypass -File tools\compartir_corpus.ps1 -Accion bajar
#   -> deja el respaldo en C:\kc_snapshot_luis (lo usa tools\kingscode_mitad.ps1 automaticamente)
#
# subir: crea el respaldo (tools\kingscode_snapshot.ps1), lo parte en trozos de 45 MB (limite de
# GitHub: 100 MB por archivo) y los sube a la rama corpus-39 con un worktree temporal. Solo lee el
# corpus: se puede correr mientras otra ventana usa la GPU.
# bajar: trae la rama, junta los trozos y verifica el SHA-256 del paquete contra SHA256SUMS.txt.
# =====================================================================
param(
    [Parameter(Mandatory = $true)] [ValidateSet("subir", "bajar")] [string]$Accion,
    [string]$Rama = "corpus-39",
    [string]$Destino = "C:\kc_snapshot_luis",
    [string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia"
)
$ErrorActionPreference = "Stop"
Set-Location $Work
$Py = "$Work\.venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
$Split = @'
import sys, pathlib
src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]); size = 45 * 1024 * 1024
data = src.read_bytes()
for i in range(0, len(data), size):
    (out / f"{src.name}.part{i // size:02d}").write_bytes(data[i:i + size])
print(f"{len(data) / 2**20:.1f} MB en {-(-len(data) // size)} trozos")
'@
$Join = @'
import sys, pathlib
src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
parts = sorted(src.glob("*.tar.gz.part*"))
if not parts: sys.exit("no hay trozos en " + str(src))
name = parts[0].name.split(".part")[0]
(dst / name).write_bytes(b"".join(p.read_bytes() for p in parts))
print(f"unido {name} ({len(parts)} trozos)")
'@

if ($Accion -eq "subir") {
    $Tmp = "$env:TEMP\kc_snapshot_subir"
    Remove-Item $Tmp -Recurse -Force -ErrorAction SilentlyContinue
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\kingscode_snapshot.ps1 -Accion crear -Destino $Tmp
    if ($LASTEXITCODE -ne 0) { throw "fallo el respaldo del corpus" }
    $Tar = Get-ChildItem "$Tmp\kingscode_corpus_*.tar.gz" | Select-Object -First 1
    $Wt = "$env:TEMP\kc_corpus_wt"
    git worktree remove --force $Wt 2>$null; Remove-Item $Wt -Recurse -Force -ErrorAction SilentlyContinue
    git worktree add --detach $Wt
    if ($LASTEXITCODE -ne 0) { throw "no se pudo crear el worktree" }
    Push-Location $Wt
    git checkout --orphan "tmp-$Rama" 2>$null
    git rm -rq --cached . 2>$null; Get-ChildItem -Force | Where-Object { $_.Name -ne ".git" } | Remove-Item -Recurse -Force
    $Split | & $Py - $Tar.FullName $Wt
    Copy-Item "$Tmp\SHA256SUMS.txt", "$Tmp\SNAPSHOT_HASHES.json" $Wt
    git add -A
    git commit -qm "Corpus del 39,02 (respaldo verificable para restaurar en otras GPUs)"
    git push -f origin "HEAD:refs/heads/$Rama"
    $ok = $LASTEXITCODE
    Pop-Location
    git worktree remove --force $Wt 2>$null
    if ($ok -ne 0) { throw "fallo el push de la rama $Rama (credenciales de GitHub en este PC?)" }
    Write-Host "Corpus subido a la rama $Rama. En GPU-2 y GPU-3: tools\compartir_corpus.ps1 -Accion bajar" -ForegroundColor Green
    exit 0
}

git fetch origin $Rama
if ($LASTEXITCODE -ne 0) { throw "no existe la rama $Rama en GitHub todavia (la GPU-1 debe terminar -Accion subir)" }
$Wt = "$env:TEMP\kc_corpus_bajar"
git worktree remove --force $Wt 2>$null; Remove-Item $Wt -Recurse -Force -ErrorAction SilentlyContinue
git worktree add --detach $Wt FETCH_HEAD
New-Item -ItemType Directory -Force $Destino | Out-Null
$Join | & $Py - $Wt $Destino
Copy-Item "$Wt\SHA256SUMS.txt", "$Wt\SNAPSHOT_HASHES.json" $Destino -Force
git worktree remove --force $Wt 2>$null
$Tar = Get-ChildItem "$Destino\kingscode_corpus_*.tar.gz" | Select-Object -First 1
$Esperado = (Get-Content "$Destino\SHA256SUMS.txt" | Where-Object { $_ -like "*$($Tar.Name)" }) -split "\s+" | Select-Object -First 1
if ((Get-FileHash $Tar.FullName -Algorithm SHA256).Hash.ToLower() -ne $Esperado) { throw "STOP: el paquete unido no coincide con SHA256SUMS.txt" }
Write-Host "Corpus del 39 listo en $Destino (verificado). Ahora: tools\kingscode_mitad.ps1 -Parte <1|2>" -ForegroundColor Green
