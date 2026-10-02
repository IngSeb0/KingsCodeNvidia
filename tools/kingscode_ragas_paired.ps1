# Compara una sola técnica contra -Recomendada (39.02/50), con el mismo corpus y RAGAS en ambos perfiles.
# Uso: -CandidateTechnique doccap3|v7-concise. Requiere que el control reproduzca 39.02/50;
# si da otro puntaje, detiene el par y presenta hashes/identidad para auditar PCs y corpus.
param(
    [ValidateSet("doccap3", "v7-concise")] [string]$CandidateTechnique = "doccap3",
    [string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia"
)
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
Set-Location $Work
if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "Falta .venv; prepara primero la PC con el runbook GPU." }
if (git status --porcelain --untracked-files=no) { throw "Hay cambios versionados sin guardar. Congela el commit antes de la prueba." }
$Sha = (git rev-parse HEAD).Trim()
$Py = ".\.venv\Scripts\python.exe"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$CandidateSpec = switch ($CandidateTechnique) {
    "doccap3" { @{ name = "doccap3"; flags = @("-Recomendada", "-DocCap", "3") } }
    "v7-concise" { @{ name = "v7concise"; flags = @("-Recomendada", "-PromptVersion", "v7") } }
}
$Runs = @(
    @{ name = "ragas_recomendada_control_$Stamp"; flags = @("-Recomendada") },
    @{ name = "ragas_$($CandidateSpec.name)_candidato_$Stamp"; flags = $CandidateSpec.flags }
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
    $BatchReport = Get-Content (Join-Path $Dir "batch\batch_report.json") -Raw | ConvertFrom-Json
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
    return [pscustomobject]@{ dir=$Dir; summary=$Summary; official=$Official; batch=$BatchReport; submission=$Submission;
        proxy=$Proxy; alignment=$Alignment }
}
$Control = Read-Run $Runs[0].name
$CandidateRun = Read-Run $Runs[1].name
foreach ($Run in @($Control, $CandidateRun)) {
    Write-Host ("Identidad {0}: commit={1}; pasajes={2}; modelo={3}; prompt={4}; context={5}; submission={6}" -f
        (Split-Path $Run.dir -Leaf), $Run.summary.main_sha, $Run.summary.passages_sha256,
        $Run.summary.model, $Run.summary.prompt_version, $Run.summary.max_context_tokens,
        $Run.batch.submission_sha256) -ForegroundColor DarkCyan
}
if ([double]$Control.official.total_automatico.obtenidos -ne 39.02) {
    throw ("-Recomendada no reprodujo la base 39.02/50 (dio {0}/50). No se corre el candidato; compara commit, SHA de pasajes, modelo/pesos, prompt y dependencias entre PCs." -f $Control.official.total_automatico.obtenidos)
}
if ($Control.summary.passages_sha256 -ne $CandidateRun.summary.passages_sha256) {
    throw "Los corpus difieren; la comparacion no es valida."
}
if ($Control.summary.prompt_version -ne "grounded-formats-v4" -or
    $Control.summary.model -ne "qwen3-8b" -or $CandidateRun.summary.model -ne $Control.summary.model -or
    $Control.summary.citation_fill -ne $true -or [int]$Control.summary.cite_mentions -ne 5 -or
    $CandidateRun.summary.citation_fill -ne $Control.summary.citation_fill -or
    [int]$CandidateRun.summary.cite_mentions -ne [int]$Control.summary.cite_mentions -or
    [int]$Control.summary.doc_cap -ne 0 -or
    ($CandidateTechnique -eq "doccap3" -and ([int]$CandidateRun.summary.doc_cap -ne 3 -or $CandidateRun.summary.prompt_version -ne $Control.summary.prompt_version)) -or
    ($CandidateTechnique -eq "v7-concise" -and ([int]$CandidateRun.summary.doc_cap -ne 0 -or $CandidateRun.summary.prompt_version -ne "grounded-formats-v7")) -or
    [int]$CandidateRun.summary.max_context_tokens -ne [int]$Control.summary.max_context_tokens) {
    throw "El control no coincide con -Recomendada o el candidato cambió más de una variable ($CandidateTechnique)."
}
$FastEnough = [double]$CandidateRun.summary.proyeccion_992_horas -le 5
$ScoreNonRegressive = [double]$CandidateRun.official.total_automatico.obtenidos -ge [double]$Control.official.total_automatico.obtenidos
$ScoreDelta = [double]$CandidateRun.official.total_automatico.obtenidos - [double]$Control.official.total_automatico.obtenidos
$ClosedSafe = [double]$CandidateRun.official.cerradas.puntos -ge [double]$Control.official.cerradas.puntos
$CitationsSafe = [int]$CandidateRun.official.citas.citas_sin_respaldo -eq 0
$ProxySafe = [double]$CandidateRun.proxy.token_f1_mean -ge [double]$Control.proxy.token_f1_mean -and
    [double]$CandidateRun.proxy.bleu4_mean -ge [double]$Control.proxy.bleu4_mean
$AlignmentSafe = [double]$CandidateRun.alignment.tasa_alineadas -ge [double]$Control.alignment.tasa_alineadas -and
    [double]$CandidateRun.alignment.tasa_debiles -le [double]$Control.alignment.tasa_debiles
$Selected = $Control
Write-Host ("Control: {0}/50, {1} s/preg, {2} h/992" -f $Control.official.total_automatico.obtenidos,
    $Control.summary.segundos_por_pregunta, $Control.summary.proyeccion_992_horas)
Write-Host ("{0}: {1}/50, {2} s/preg, {3} h/992" -f $CandidateTechnique, $CandidateRun.official.total_automatico.obtenidos,
    $CandidateRun.summary.segundos_por_pregunta, $CandidateRun.summary.proyeccion_992_horas)
Write-Host ("Gate de puntaje: delta {0:+0.00;-0.00;0.00}/50; no regresión={1}. Un empate puede aceptarse si RAGAS mejora y pasan los demás gates." -f $ScoreDelta, $ScoreNonRegressive) -ForegroundColor Cyan
Write-Host "Se ejecutará RAGAS sobre ambos perfiles; velocidad es un gate operativo separado." -ForegroundColor Cyan
& $Py -m pip install -r scripts\requirements-evaluador.txt --quiet
if ($LASTEXITCODE -ne 0) { throw "Fallo la instalacion de dependencias de RAGAS." }
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
    $RunsToScore = @($Control, $CandidateRun)
    foreach ($Run in $RunsToScore) {
        $RagasOut = Join-Path $Run.dir "evaluation_ragas.json"
        Write-Host "RAGAS pareado: $($Run.dir)" -ForegroundColor Cyan
        & $Py scripts\evaluate.py --submission $Run.submission --split sample --ragas --out $RagasOut
        if ($LASTEXITCODE -ne 0) { throw "Fallo RAGAS para $($Run.dir)." }
    }
} finally {
    if ($null -eq $PreviousKey) { Remove-Item Env:\OPENROUTER_API_KEY -ErrorAction SilentlyContinue }
    else { $env:OPENROUTER_API_KEY = $PreviousKey }
    if ($null -eq $PreviousOffline) { Remove-Item Env:\HF_HUB_OFFLINE -ErrorAction SilentlyContinue }
    else { $env:HF_HUB_OFFLINE = $PreviousOffline }
    if ($Pointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Pointer) }
}
$ControlRagasPath = Join-Path $Control.dir "evaluation_ragas.json"
$ControlRagas = Get-Content $ControlRagasPath -Raw | ConvertFrom-Json
$RagasRuns = @($ControlRagas)
$CandidateRagasPath = Join-Path $CandidateRun.dir "evaluation_ragas.json"
$CandidateRagas = Get-Content $CandidateRagasPath -Raw | ConvertFrom-Json
$RagasRuns += $CandidateRagas
$RagasComparable = ([int]$CandidateRagas.correccion_ragas.n_fallidos -eq 0 -and
    [int]$ControlRagas.correccion_ragas.n_fallidos -eq 0 -and
    [int]$CandidateRagas.correccion_ragas.n_juzgados -eq [int]$ControlRagas.correccion_ragas.n_juzgados -and
    $CandidateRagas.correccion_ragas.modelo_juez -eq $ControlRagas.correccion_ragas.modelo_juez -and
    $CandidateRagas.correccion_ragas.encoder -eq $ControlRagas.correccion_ragas.encoder)
$RagasBetter = $RagasComparable -and
    [double]$CandidateRagas.correccion_ragas.correctness -gt [double]$ControlRagas.correccion_ragas.correctness
$Accepted = $FastEnough -and $ScoreNonRegressive -and $ClosedSafe -and $CitationsSafe -and $ProxySafe -and $AlignmentSafe -and $RagasBetter
$Selected = if ($Accepted) { $CandidateRun } else { $Control }
$SelectedRagas = if ($Accepted) { $CandidateRagas } else { $ControlRagas }
Write-Host ("RAGAS control: {0}/30 ({1}); {2}: {3}/30 ({4}); comparable={5}" -f
    $ControlRagas.correccion_ragas.puntos, $ControlRagas.correccion_ragas.correctness,
    $CandidateTechnique, $CandidateRagas.correccion_ragas.puntos, $CandidateRagas.correccion_ragas.correctness, $RagasComparable) -ForegroundColor Cyan
foreach ($R in $RagasRuns) {
    if ([int]$R.validacion.errores -ne 0 -or [int]$R.correccion_ragas.n_fallidos -ne 0 -or
        [int]$R.correccion_ragas.n_respondidos -le 0 -or [double]$R.total_automatico.posibles -ne 80) {
        throw "RAGAS incompleto; revise la corrida antes de comparar."
    }
}
Write-Host "Perfil seleccionado: $($Selected.dir); candidato $CandidateTechnique aceptado: $Accepted" -ForegroundColor Green
Write-Host "Entrega score: $($Selected.official.total_automatico.obtenidos)/50; RAGAS $($SelectedRagas.correccion_ragas.puntos)/30" -ForegroundColor Green
$Clock.Stop()
Write-Host "Total de pared: $([math]::Round($Clock.Elapsed.TotalMinutes, 1)) min" -ForegroundColor Green
