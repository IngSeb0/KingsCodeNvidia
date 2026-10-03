# =====================================================================
# KingsCode - verificacion en vivo (15:00-17:00): regenerar ids entregados y comparar normas y pasajes
#
#   powershell -ExecutionPolicy Bypass -File tools\verificar_id.ps1 -Ids 25
#   powershell -ExecutionPolicy Bypass -File tools\verificar_id.ps1 -Ids 25,300,812
#
# Lee docs\ENTREGA_ORIGEN_FILAS.json: cada id se regenera con la configuracion de la corrida que lo
# produjo, contra el submissions.jsonl entregado. Si un id es de otro PC, lo dice y no lo corre.
# La GPU debe estar libre: cerrar antes la interfaz (Ctrl+C en su ventana).
# =====================================================================
param([Parameter(Mandatory = $true)] [int[]]$Ids, [string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia")
$ErrorActionPreference = "Continue"
Set-Location $Work
$Py = "$Work\.venv\Scripts\python.exe"
git fetch origin main 2>&1 | Out-Null
git checkout origin/main -- submissions.jsonl docs/ENTREGA_ORIGEN_FILAS.json 2>&1 | Out-Null
$Origen = (Get-Content docs\ENTREGA_ORIGEN_FILAS.json -Raw -Encoding UTF8 | ConvertFrom-Json).filas
$env:HF_HUB_OFFLINE = "1"
$Base = @("--input", "data\test_992.jsonl", "--retrieval-mode", "option", "--graph-policy", "router", "--k", "8",
          "--candidate-k", "30", "--graph-budget", "10", "--corpus", "corpus_v01_v02_a1", "--model", "qwen3-8b",
          "--reranker-batch-size", "2", "--precision", "bf16", "--prompt-version", "v6", "--citation-fill",
          "--cite-mentions", "5", "--delivered", "submissions.jsonl")
foreach ($Grupo in ($Ids | Group-Object { $Origen."$_".corrida })) {
    $Corrida = $Grupo.Name
    $Lista = ($Grupo.Group -join ",")
    if (-not (Test-Path "reports\decoder_diagnostic\$Corrida")) {
        $Pc = $Origen."$($Grupo.Group[0])".pc
        Write-Host "ids $Lista -> corrida $Corrida, se verifican en $Pc (no en este PC)." -ForegroundColor Yellow
        continue
    }
    $Modo = $(if ($Corrida -like "mejora_*") { @("--retriever-mode", "hybrid", "--hybrid-formats", "semi_open,open_ended") } else { @("--retriever-mode", "bm25") })
    Write-Host "Regenerando ids $Lista (corrida $Corrida)..." -ForegroundColor Cyan
    & $Py tools\member_b.py verify --only $Lista @Base @Modo
}
