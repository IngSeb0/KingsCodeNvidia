<#
.SYNOPSIS
Runs the official sample evaluator with RAGAS on two already-generated submissions.
.DESCRIPTION
Does not run the decoder or alter either submission. Writes timestamped evaluator
reports beside each submission and prints a paired comparison. A comparison with
judge failures is flagged as non-comparable.
#>
param(
    [string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia",
    [string]$ControlSubmission = "",
    [string]$CandidateSubmission = ""
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
Set-Location $Work

$Py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { throw "Falta el entorno Python: $Py" }

function Resolve-Submission([string]$Path, [string]$Label) {
    if (-not $Path) { $Path = Read-Host "Ruta al submissions.jsonl de $Label" }
    if (-not [IO.Path]::IsPathRooted($Path)) { $Path = Join-Path (Get-Location) $Path }
    $Resolved = (Resolve-Path -LiteralPath $Path).Path
    if ([IO.Path]::GetFileName($Resolved) -ne "submissions.jsonl") {
        throw "$Label debe apuntar al archivo submissions.jsonl: $Resolved"
    }
    return $Resolved
}

$Control = Resolve-Submission $ControlSubmission "Recomendada/control"
$Candidate = Resolve-Submission $CandidateSubmission "DocCap 3/candidato"
if ($Control -eq $Candidate) { throw "Control y candidato apuntan al mismo archivo." }

& $Py -m pip install -r scripts\requirements-evaluador.txt --quiet
if ($LASTEXITCODE -ne 0) { throw "Falló la instalación de dependencias del evaluador." }

$PreviousKey = $env:OPENROUTER_API_KEY
$PreviousOffline = $env:HF_HUB_OFFLINE
$Pointer = [IntPtr]::Zero
try {
    if (-not $env:OPENROUTER_API_KEY -and -not (Test-Path scripts\.env) -and -not (Test-Path data\.env)) {
        $Secure = Read-Host "Llave de OpenRouter para el juez RAGAS" -AsSecureString
        $Pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
        $env:OPENROUTER_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Pointer)
    }
    Remove-Item Env:\HF_HUB_OFFLINE -ErrorAction SilentlyContinue

    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $ControlOut = Join-Path (Split-Path $Control) "evaluation_ragas_control_$Stamp.json"
    $CandidateOut = Join-Path (Split-Path $Candidate) "evaluation_ragas_candidate_$Stamp.json"

    foreach ($Run in @(
        @{ label = "Recomendada/control"; submission = $Control; output = $ControlOut },
        @{ label = "DocCap 3/candidato"; submission = $Candidate; output = $CandidateOut }
    )) {
        Write-Host "`n>>> RAGAS: $($Run.label)" -ForegroundColor Cyan
        & $Py scripts\evaluate.py --submission $Run.submission --split sample --ragas --out $Run.output
        if ($LASTEXITCODE -ne 0) { throw "Falló el evaluador para $($Run.label)." }
    }

    $ControlReport = Get-Content $ControlOut -Raw | ConvertFrom-Json
    $CandidateReport = Get-Content $CandidateOut -Raw | ConvertFrom-Json
    $A = $ControlReport.correccion_ragas
    $B = $CandidateReport.correccion_ragas
    $ControlWithoutRagas = [double]$ControlReport.cerradas.puntos +
        [double]$ControlReport.citas.puntos + [double]$ControlReport.abstencion.puntos
    $CandidateWithoutRagas = [double]$CandidateReport.cerradas.puntos +
        [double]$CandidateReport.citas.puntos + [double]$CandidateReport.abstencion.puntos
    $Comparable = (
        [int]$A.n_fallidos -eq 0 -and [int]$B.n_fallidos -eq 0 -and
        [int]$A.n_juzgados -eq [int]$B.n_juzgados -and
        $A.modelo_juez -eq $B.modelo_juez -and $A.encoder -eq $B.encoder
    )

    Write-Host "`n===== COMPARACIÓN PAREADA =====" -ForegroundColor Green
    Write-Host ("Control: sin RAGAS {0}/50; RAGAS {1}/30 (correctness {2}, {3}/{4} respondidos, {5} fallos); total {6}/80" -f `
        $ControlWithoutRagas, $A.puntos, $A.correctness, $A.n_respondidos, $A.n_juzgados, $A.n_fallidos, $ControlReport.total_automatico.obtenidos)
    Write-Host ("DocCap 3: sin RAGAS {0}/50; RAGAS {1}/30 (correctness {2}, {3}/{4} respondidos, {5} fallos); total {6}/80" -f `
        $CandidateWithoutRagas, $B.puntos, $B.correctness, $B.n_respondidos, $B.n_juzgados, $B.n_fallidos, $CandidateReport.total_automatico.obtenidos)
    Write-Host ("Delta DocCap 3 - control: {0:+0.00;-0.00;0.00}/50 sin RAGAS; {1:+0.00;-0.00;0.00}/30 RAGAS; {2:+0.00;-0.00;0.00}/80 total" -f `
        ($CandidateWithoutRagas - $ControlWithoutRagas),
        ([double]$B.puntos - [double]$A.puntos),
        ([double]$CandidateReport.total_automatico.obtenidos - [double]$ControlReport.total_automatico.obtenidos))
    Write-Host "Comparación válida, sin fallos del juez: $Comparable"
    Write-Host "Reportes: $ControlOut ; $CandidateOut"
} finally {
    if ($null -eq $PreviousKey) { Remove-Item Env:\OPENROUTER_API_KEY -ErrorAction SilentlyContinue }
    else { $env:OPENROUTER_API_KEY = $PreviousKey }
    if ($null -eq $PreviousOffline) { Remove-Item Env:\HF_HUB_OFFLINE -ErrorAction SilentlyContinue }
    else { $env:HF_HUB_OFFLINE = $PreviousOffline }
    if ($Pointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Pointer)
    }
}
