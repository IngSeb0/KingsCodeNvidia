# Evalua una unica mejora de retrieval: plan por area -> norma -> sentencia.
# Control pareado: configuracion recomendada vigente. RAGAS se ejecuta una sola vez.
param([string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia")
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
Set-Location $Work
if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "Falta .venv; prepara primero la PC con el runbook GPU." }
if (git status --porcelain --untracked-files=no) { throw "Hay cambios versionados sin guardar. Congela el commit antes de la prueba." }
$Sha = (git rev-parse HEAD).Trim()
$Py = ".\.venv\Scripts\python.exe"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Runs = @(
    @{ name = "arbol_control_$Stamp"; flags = @("-Recomendada") },
    @{ name = "arbol_candidato_$Stamp"; flags = @("-Recomendada", "-RetrievalMode", "option_plan") }
)
$Clock = [Diagnostics.Stopwatch]::StartNew()
foreach ($Run in $Runs) {
    Write-Host "`n>>> $($Run.name): $($Run.flags -join ' ')" -ForegroundColor Cyan
    $RunFlags = [string[]]$Run.flags
    powershell -ExecutionPolicy Bypass -File .\tools\kingscode_pc_nueva_diagnostico.ps1 -Work $Work -RunName $Run.name -SkipSmoke -NoPull @RunFlags
    if ($LASTEXITCODE -ne 0) { throw "Fallo la corrida $($Run.name)." }
}

function Read-Run($Name) {
    $Dir = Join-Path "reports\decoder_diagnostic" $Name
    $Summary = Get-Content (Join-Path $Dir "RESUMEN.json") -Raw | ConvertFrom-Json
    $Official = Get-Content (Join-Path $Dir "evaluation_official.json") -Raw | ConvertFrom-Json
    $Submission = Join-Path $Dir "batch\submissions.jsonl"
    $Rows = @(Get-Content $Submission | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json })
    if ($Summary.main_sha -ne $Sha -or -not $Summary.completo -or [int]$Summary.filas -ne 50 -or
        $Rows.Count -ne 50 -or @($Rows.id | Select-Object -Unique).Count -ne 50 -or
        [int]$Official.validacion.errores -ne 0 -or -not $Summary.verificacion_en_vivo.all_match) {
        throw "Corrida incompleta, invalida o no reproducible: $Dir"
    }
    $Proxy = & $Py tools\analyze_ragas_proxy.py $Submission --no-encoder | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "Fallo el proxy: $Dir" }
    $Alignment = & $Py tools\analyze_citation_alignment.py $Submission | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw "Fallo el analisis de citas: $Dir" }
    return [pscustomobject]@{ dir=$Dir; summary=$Summary; official=$Official; submission=$Submission;
        proxy=$Proxy; alignment=$Alignment }
}
$Control = Read-Run $Runs[0].name
$Candidate = Read-Run $Runs[1].name
if ($Control.summary.passages_sha256 -ne $Candidate.summary.passages_sha256) {
    throw "Los corpus difieren; la comparacion no es valida."
}
$FastEnough = [double]$Candidate.summary.proyeccion_992_horas -le 5
$Better = [double]$Candidate.official.total_automatico.obtenidos -gt [double]$Control.official.total_automatico.obtenidos
$ClosedSafe = [double]$Candidate.official.cerradas.puntos -ge [double]$Control.official.cerradas.puntos
$CitationsSafe = [int]$Candidate.official.citas.citas_sin_respaldo -eq 0
$ProxySafe = [double]$Candidate.proxy.token_f1_mean -ge [double]$Control.proxy.token_f1_mean -and
    [double]$Candidate.proxy.bleu4_mean -ge [double]$Control.proxy.bleu4_mean
$AlignmentSafe = [double]$Candidate.alignment.tasa_alineadas -ge [double]$Control.alignment.tasa_alineadas -and
    [double]$Candidate.alignment.tasa_debiles -le [double]$Control.alignment.tasa_debiles
$Accepted = $FastEnough -and $Better -and $ClosedSafe -and $CitationsSafe -and $ProxySafe -and $AlignmentSafe
$Selected = if ($Accepted) { $Candidate } else { $Control }
Write-Host ("Control: {0}/50, {1} s/preg, {2} h/992" -f $Control.official.total_automatico.obtenidos,
    $Control.summary.segundos_por_pregunta, $Control.summary.proyeccion_992_horas)
Write-Host ("Arbol: {0}/50, {1} s/preg, {2} h/992" -f $Candidate.official.total_automatico.obtenidos,
    $Candidate.summary.segundos_por_pregunta, $Candidate.summary.proyeccion_992_horas)
Write-Host "Candidato aceptado: $Accepted; perfil para RAGAS: $($Selected.dir)" -ForegroundColor Cyan
if ([double]$Selected.summary.proyeccion_992_horas -gt 5) {
    throw "Ningun perfil cabe en el margen de 5 horas para 992 preguntas. Se conserva el diagnostico sin RAGAS."
}

& $Py -m pip install -r scripts\requirements-evaluador.txt reportlab pypdf --quiet
if ($LASTEXITCODE -ne 0) { throw "Fallo la instalacion de dependencias de RAGAS/PDF." }
$PreviousKey = $env:OPENROUTER_API_KEY
$PreviousOffline = $env:HF_HUB_OFFLINE
$Pointer = [IntPtr]::Zero
try {
    if (-not $env:OPENROUTER_API_KEY -and -not (Test-Path "scripts\.env")) {
        $Secure = Read-Host "Llave de OpenRouter para el juez oficial" -AsSecureString
        $Pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
        $env:OPENROUTER_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Pointer)
    }
    Remove-Item Env:\HF_HUB_OFFLINE -ErrorAction SilentlyContinue
    & $Py scripts\evaluate.py --submission $Selected.submission --split sample --ragas --out (Join-Path $Selected.dir "evaluation_ragas.json")
    if ($LASTEXITCODE -ne 0) { throw "Fallo RAGAS." }
} finally {
    if ($null -eq $PreviousKey) { Remove-Item Env:\OPENROUTER_API_KEY -ErrorAction SilentlyContinue }
    else { $env:OPENROUTER_API_KEY = $PreviousKey }
    if ($null -eq $PreviousOffline) { Remove-Item Env:\HF_HUB_OFFLINE -ErrorAction SilentlyContinue }
    else { $env:HF_HUB_OFFLINE = $PreviousOffline }
    if ($Pointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Pointer) }
}
$RagasPath = Join-Path $Selected.dir "evaluation_ragas.json"
$Ragas = Get-Content $RagasPath -Raw | ConvertFrom-Json
if ([int]$Ragas.validacion.errores -ne 0 -or $null -eq $Ragas.correccion_ragas.n_fallidos -or
    [int]$Ragas.correccion_ragas.n_fallidos -ne 0 -or [int]$Ragas.correccion_ragas.n_respondidos -le 0 -or
    [double]$Ragas.total_automatico.posibles -ne 80) { throw "RAGAS incompleto; no se genera informe final." }
$ComparisonPath = "reports\legal_tree_comparison_$Stamp.json"
[ordered]@{
    commit = $Sha; passages_sha256 = $Selected.summary.passages_sha256
    control_run = $Control.dir; control_score_50 = $Control.official.total_automatico.obtenidos
    candidate_run = $Candidate.dir; candidate_score_50 = $Candidate.official.total_automatico.obtenidos
    candidate_seconds_per_question = $Candidate.summary.segundos_por_pregunta
    candidate_projected_992_hours = $Candidate.summary.proyeccion_992_horas
    gates = [ordered]@{ speed = $FastEnough; score = $Better; closed = $ClosedSafe
        citations = $CitationsSafe; proxy = $ProxySafe; alignment = $AlignmentSafe }
    candidate_accepted = $Accepted; selected_run = $Selected.dir
    ragas_report = $RagasPath; ragas_failed_judgments = $Ragas.correccion_ragas.n_fallidos
    total_with_ragas_80 = $Ragas.total_automatico.obtenidos
} | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $ComparisonPath

$Pdf = "informe\INFORME_TECNICO.pdf"
& $Py tools\generate_informe_tecnico.py --run-dir $Selected.dir --output $Pdf --candidate-accepted ([string]$Accepted)
if ($LASTEXITCODE -ne 0) { throw "Fallo la generacion del PDF." }
$Clock.Stop()
Write-Host "Total de pared: $([math]::Round($Clock.Elapsed.TotalMinutes, 1)) min" -ForegroundColor Green
Write-Host "PDF: $((Resolve-Path $Pdf).Path)" -ForegroundColor Green
Write-Host "Comparacion: $((Resolve-Path $ComparisonPath).Path)" -ForegroundColor Green
Write-Host "Resultado medido: $($Ragas.total_automatico.obtenidos)/80 (incluye RAGAS)" -ForegroundColor Green
