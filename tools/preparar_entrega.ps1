# =====================================================================
# KingsCode - carpeta final para subir (OneDrive) con todo lo que pide la entrega del sabado
#
#   powershell -ExecutionPolicy Bypass -File tools\preparar_entrega.ps1
#
# Correr en el PC que tiene el indice semantico (GPU-3). Trae los archivos de entrega de main
# (sin tocar el codigo con el que se genero la corrida), arma corpus_KingsCode.zip con el indice
# vectorial y copia todo a OneDrive\KingsCode\ENTREGA_FINAL. Luego: poner ahi el video y
# compartir con "Cualquier persona con el vinculo".
# =====================================================================
param([string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia")
$ErrorActionPreference = "Continue"
Set-Location $Work
$Py = "$Work\.venv\Scripts\python.exe"
git fetch origin main 2>&1 | Out-Null
git checkout origin/main -- submissions.jsonl README.md CORPUS.md corpus_manifest.json LICENSE informe docs/video docs/GUION_VIDEO.md interfaz tools/package_corpus_entrega.py 2>&1 | Out-Null
if (-not (Test-Path "corpus_v01_v02_a1\index\dense.npy")) { throw "STOP: este PC no tiene corpus_v01_v02_a1\index\dense.npy (usar GPU-3 o GPU-1)." }

Write-Host "Armando corpus_KingsCode.zip (1-2 min)..." -ForegroundColor Cyan
& $Py tools\package_corpus_entrega.py --corpus corpus_v01_v02_a1
if ($LASTEXITCODE -ne 0) { throw "fallo el empaquetado del corpus" }

$Base = $(if ($env:OneDrive) { "$env:OneDrive\KingsCode" } else { "$HOME\KingsCode" })
$Dest = Join-Path $Base "ENTREGA_FINAL"
New-Item -ItemType Directory -Force $Dest, "$Dest\informe", "$Dest\presentacion" | Out-Null
Copy-Item dist\corpus_KingsCode.zip, submissions.jsonl, README.md, CORPUS.md, corpus_manifest.json, LICENSE $Dest -Force
Copy-Item informe\INFORME_TECNICO.pdf "$Dest\informe\" -Force
Copy-Item docs\video\presentacion.html "$Dest\presentacion\" -Force
New-Item -ItemType Directory -Force "$Dest\interfaz\assets" | Out-Null
Copy-Item interfaz\assets\software_colombia_logo.png "$Dest\interfaz\assets\" -Force
Copy-Item docs\GUION_VIDEO.md "$Dest\presentacion\" -Force
# la presentacion busca el logo en ../../interfaz/assets: se ajusta la ruta en la copia
(Get-Content "$Dest\presentacion\presentacion.html" -Raw -Encoding UTF8).Replace("../../interfaz/assets/", "../interfaz/assets/") |
    Set-Content "$Dest\presentacion\presentacion.html" -Encoding UTF8

Write-Host ""
Get-ChildItem $Dest -Recurse -File | Select-Object @{n = "archivo"; e = { $_.FullName.Replace("$Dest\", "") } }, @{n = "MB"; e = { [math]::Round($_.Length / 1MB, 1) } } | Format-Table -AutoSize
$Sha = (Get-FileHash "$Dest\submissions.jsonl" -Algorithm SHA256).Hash.ToLower().Substring(0, 16)
Write-Host "submissions.jsonl sha256 $Sha... (debe coincidir con el de main)" -ForegroundColor Green
Write-Host "Carpeta lista: $Dest" -ForegroundColor Green
Write-Host "1) Copiar ahi el video (MP4).  2) En OneDrive: clic derecho en corpus_KingsCode.zip y en el video -> Compartir -> 'Cualquier persona con el vinculo' -> copiar vinculo.  3) Probar cada vinculo en ventana privada." -ForegroundColor Yellow
