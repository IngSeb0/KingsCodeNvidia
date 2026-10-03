# =====================================================================
# KingsCode - subir el resultado de una corrida a una rama aparte de GitHub (main no se toca)
#
#   GPU-2:  powershell -ExecutionPolicy Bypass -File tools\subir_resultado.ps1 -Corrida final_p1
#   GPU-3:  powershell -ExecutionPolicy Bypass -File tools\subir_resultado.ps1 -Corrida final_p2
#   GPU-1:  powershell -ExecutionPolicy Bypass -File tools\subir_resultado.ps1 -Corrida final_992_v6c
#
# Sube reports\decoder_diagnostic\<corrida>\ (submissions.jsonl, RESUMEN, evaluacion, items y
# verify_live.json) a la rama entrega-<corrida>, desde un worktree temporal. Desde ahi se unen y
# validan las mitades y se publica submissions.jsonl en main. Solo lee la corrida.
# =====================================================================
param(
    [Parameter(Mandatory = $true)] [string]$Corrida,
    [string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia"
)
$ErrorActionPreference = "Continue"
Set-Location $Work
$Src = Join-Path $Work "reports\decoder_diagnostic\$Corrida"
if (-not (Test-Path (Join-Path $Src "batch\submissions.jsonl"))) { throw "STOP: no existe $Src\batch\submissions.jsonl (la corrida no termino)." }
$Rama = "entrega-$Corrida"
$Wt = Join-Path $env:TEMP "kc_resultado_wt"
if (Test-Path $Wt) { git worktree remove --force $Wt 2>&1 | Out-Null; Remove-Item $Wt -Recurse -Force -ErrorAction SilentlyContinue }
git worktree prune 2>&1 | Out-Null
git worktree add --detach $Wt 2>&1 | Out-Host
if (-not (Test-Path (Join-Path $Wt ".git"))) { throw "no se pudo crear el worktree en $Wt" }
Push-Location $Wt
git checkout --orphan "tmp-$Rama-$((Get-Date).ToString('HHmmss'))" 2>&1 | Out-Null
git rm -rq --cached . 2>&1 | Out-Null
Get-ChildItem -Force | Where-Object { $_.Name -ne ".git" } | Remove-Item -Recurse -Force
New-Item -ItemType Directory -Force "resultado" | Out-Null
Copy-Item (Join-Path $Src "*") "resultado" -Recurse -Force
"maquina: $env:COMPUTERNAME`nusuario: $env:USERNAME`ncommit: $((git -C $Work rev-parse HEAD).Trim())`ncorpus: $((Get-FileHash (Join-Path $Work 'corpus\passages.jsonl') -Algorithm SHA256).Hash)" |
    Set-Content -Encoding ascii "resultado\ORIGEN.txt"
git add -A 2>&1 | Out-Null
git commit -qm "Resultado $Corrida ($env:COMPUTERNAME / $env:USERNAME)" 2>&1 | Out-Host
git push -f origin "HEAD:refs/heads/$Rama" 2>&1 | Out-Host
$ok = $LASTEXITCODE
Pop-Location
git worktree remove --force $Wt 2>&1 | Out-Null
if ($ok -ne 0) { throw "fallo el push de $Rama (credenciales de GitHub en este PC?)" }
Write-Host "Subido a la rama $Rama. Avisa para unir y publicar." -ForegroundColor Green
