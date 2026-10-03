# =====================================================================
# KingsCode - pasar el corpus de un PC a otro por GitHub (rama aparte "corpus-39"; main no se toca)
#
# En el PC que TIENE el corpus bueno (GPU-1):
#   powershell -ExecutionPolicy Bypass -File tools\compartir_corpus.ps1 -Accion subir
# En los PCs que lo NECESITAN (GPU-2, GPU-3):
#   powershell -ExecutionPolicy Bypass -File tools\compartir_corpus.ps1 -Accion bajar
#   -> deja el respaldo en C:\kc_snapshot_luis (lo usa tools\kingscode_mitad.ps1 automaticamente)
#
# subir: crea el respaldo (o reutiliza uno ya creado en %TEMP%\kc_snapshot_subir), lo parte en
# trozos de 45 MB (limite de GitHub: 100 MB por archivo) y los sube a la rama corpus-39 desde un
# worktree temporal. Solo lee el corpus: se puede correr mientras otra ventana usa la GPU.
# bajar: trae la rama, junta los trozos y verifica el SHA-256 del paquete contra SHA256SUMS.txt.
# =====================================================================
param(
    [Parameter(Mandatory = $true)] [ValidateSet("subir", "bajar")] [string]$Accion,
    [string]$Rama = "corpus-39",
    [string]$Destino = "C:\kc_snapshot_luis",
    [string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia"
)
# Continue: git writes harmless notices to stderr and PS 5.1 would turn them into terminating
# errors; every step that matters is checked explicitly.
$ErrorActionPreference = "Continue"
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
function Remove-Worktree($Path) {
    if (Test-Path $Path) {
        git worktree remove --force $Path 2>&1 | Out-Null
        Remove-Item $Path -Recurse -Force -ErrorAction SilentlyContinue
    }
    git worktree prune 2>&1 | Out-Null
}

if ($Accion -eq "subir") {
    $Tmp = Join-Path $env:TEMP "kc_snapshot_subir"
    $Tar = Get-ChildItem (Join-Path $Tmp "kingscode_corpus_*.tar.gz") -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($Tar -and (Test-Path (Join-Path $Tmp "SHA256SUMS.txt"))) {
        Write-Host "Se reutiliza el respaldo ya creado: $($Tar.FullName)"
    } else {
        Remove-Item $Tmp -Recurse -Force -ErrorAction SilentlyContinue
        powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\kingscode_snapshot.ps1 -Accion crear -Destino $Tmp
        if ($LASTEXITCODE -ne 0) { throw "fallo el respaldo del corpus" }
        $Tar = Get-ChildItem (Join-Path $Tmp "kingscode_corpus_*.tar.gz") | Select-Object -First 1
    }
    $Wt = Join-Path $env:TEMP "kc_corpus_wt"
    Remove-Worktree $Wt
    git worktree add --detach $Wt 2>&1 | Out-Host
    if (-not (Test-Path (Join-Path $Wt ".git"))) { throw "no se pudo crear el worktree en $Wt" }
    Push-Location $Wt
    git checkout --orphan "tmp-$Rama-$((Get-Date).ToString('HHmmss'))" 2>&1 | Out-Null
    git rm -rq --cached . 2>&1 | Out-Null
    Get-ChildItem -Force | Where-Object { $_.Name -ne ".git" } | Remove-Item -Recurse -Force
    $Split | & $Py - $Tar.FullName $Wt
    Copy-Item (Join-Path $Tmp "SHA256SUMS.txt"), (Join-Path $Tmp "SNAPSHOT_HASHES.json") $Wt
    git add -A 2>&1 | Out-Null
    git commit -qm "Corpus del 39,02 (respaldo verificable para restaurar en otras GPUs)" 2>&1 | Out-Host
    git push -f origin "HEAD:refs/heads/$Rama" 2>&1 | Out-Host
    $ok = $LASTEXITCODE
    Pop-Location
    Remove-Worktree $Wt
    if ($ok -ne 0) { throw "fallo el push de la rama $Rama (credenciales de GitHub en este PC?)" }
    Write-Host "Corpus subido a la rama $Rama. En GPU-2 y GPU-3: tools\compartir_corpus.ps1 -Accion bajar" -ForegroundColor Green
    exit 0
}

git fetch origin $Rama 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { throw "no existe la rama $Rama en GitHub todavia (la GPU-1 debe terminar -Accion subir)" }
$Wt = Join-Path $env:TEMP "kc_corpus_bajar"
Remove-Worktree $Wt
git worktree add --detach $Wt FETCH_HEAD 2>&1 | Out-Host
if (-not (Test-Path (Join-Path $Wt "SHA256SUMS.txt"))) { throw "no se pudo abrir la rama $Rama en $Wt" }
New-Item -ItemType Directory -Force $Destino | Out-Null
Get-ChildItem (Join-Path $Destino "kingscode_corpus_*.tar.gz") -ErrorAction SilentlyContinue | Remove-Item -Force
$Join | & $Py - $Wt $Destino
Copy-Item (Join-Path $Wt "SHA256SUMS.txt"), (Join-Path $Wt "SNAPSHOT_HASHES.json") $Destino -Force
Remove-Worktree $Wt
$Tar = Get-ChildItem (Join-Path $Destino "kingscode_corpus_*.tar.gz") | Select-Object -First 1
$Esperado = (Get-Content (Join-Path $Destino "SHA256SUMS.txt") | Where-Object { $_ -like "*$($Tar.Name)" }) -split "\s+" | Select-Object -First 1
if ((Get-FileHash $Tar.FullName -Algorithm SHA256).Hash.ToLower() -ne $Esperado) { throw "STOP: el paquete unido no coincide con SHA256SUMS.txt" }
Write-Host "Corpus del 39 listo en $Destino (verificado). Ahora: tools\kingscode_mitad.ps1 -Parte <1|2>" -ForegroundColor Green
