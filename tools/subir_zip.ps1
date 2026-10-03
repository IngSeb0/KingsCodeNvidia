# KingsCode - sube dist\corpus_KingsCode.zip a la rama corpus-entrega en trozos de 45 MB, para
# publicarlo como descarga del repositorio (Release). Correr en el PC que lo armo (GPU-3).
#   powershell -ExecutionPolicy Bypass -File tools\subir_zip.ps1
param([string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia")
$ErrorActionPreference = "Continue"
Set-Location $Work
$Zip = Join-Path $Work "dist\corpus_KingsCode.zip"
if (-not (Test-Path $Zip)) { throw "STOP: no existe $Zip (correr antes tools\preparar_entrega.ps1)" }
$Py = "$Work\.venv\Scripts\python.exe"
$Wt = Join-Path $env:TEMP "kc_zip_wt"
if (Test-Path $Wt) { git worktree remove --force $Wt 2>&1 | Out-Null; Remove-Item $Wt -Recurse -Force -ErrorAction SilentlyContinue }
git worktree prune 2>&1 | Out-Null
git worktree add --detach $Wt 2>&1 | Out-Null
Push-Location $Wt
git checkout --orphan "tmp-zip-$((Get-Date).ToString('HHmmss'))" 2>&1 | Out-Null
git rm -rq --cached . 2>&1 | Out-Null
Get-ChildItem -Force | Where-Object { $_.Name -ne ".git" } | Remove-Item -Recurse -Force
@'
import sys, pathlib, hashlib
src = pathlib.Path(sys.argv[1]); data = src.read_bytes(); size = 45 * 1024 * 1024
for i in range(0, len(data), size):
    pathlib.Path(f"{src.name}.part{i // size:02d}").write_bytes(data[i:i + size])
pathlib.Path("SHA256.txt").write_text(hashlib.sha256(data).hexdigest() + "  " + src.name + "\n")
print(f"{len(data) / 2**20:.1f} MB en {-(-len(data) // size)} trozos")
'@ | & $Py - $Zip
git add -A 2>&1 | Out-Null
git commit -qm "corpus_KingsCode.zip en trozos" 2>&1 | Out-Null
git push -f origin "HEAD:refs/heads/corpus-entrega" 2>&1 | Out-Host
$ok = $LASTEXITCODE
Pop-Location
git worktree remove --force $Wt 2>&1 | Out-Null
if ($ok -ne 0) { throw "fallo el push" }
Write-Host "Zip subido a la rama corpus-entrega. Avisar." -ForegroundColor Green
