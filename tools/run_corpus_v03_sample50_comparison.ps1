[CmdletBinding()]
param(
    [string]$Work = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$IndependentGateReport = "reports\corpus_v03_independent_retrieval_comparison.json",
    [switch]$AllowCorpusGateNotPassed,
    [switch]$AllowBusyGpu,
    [switch]$SkipSmoke
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Repo = (Resolve-Path -LiteralPath $Work).Path
Set-Location $Repo
$ExpectedBranch = "main"
$Branch = (& git branch --show-current).Trim()
if ($Branch -ne $ExpectedBranch) { throw "STOP: checkout $ExpectedBranch first (current: $Branch)." }
$Commit = (& git rev-parse HEAD).Trim()
$Dirty = @(& git status --porcelain --untracked-files=no)
if ($Dirty.Count -gt 0) { throw "STOP: tracked source tree is dirty; commit or restore it before a paired GPU run.`n$($Dirty -join "`n")" }

$GatePath = Join-Path $Repo $IndependentGateReport
if (-not (Test-Path -LiteralPath $GatePath)) { throw "STOP: independent C1 report missing: $GatePath" }
$Gate = Get-Content -LiteralPath $GatePath -Raw | ConvertFrom-Json
if ($Gate.status -ne "PASS" -and -not $AllowCorpusGateNotPassed) {
    throw "STOP: C1 independent retrieval gate is $($Gate.status). For the explicitly requested exploratory hybrid sample_50 comparison, rerun with -AllowCorpusGateNotPassed. This does not qualify the corpus for freeze."
}
if ($Gate.status -ne "PASS") {
    Write-Warning "C1=$($Gate.status). Continuing only as an exploratory hybrid comparison; this corpus is not eligible for competitive freeze."
}

$CorpusDir = Join-Path $Repo "corpus_v03_candidate"
$ManifestPath = Join-Path $CorpusDir "manifest.json"
$ExpectedCorpus = $Gate.candidate_run.corpus
function Assert-CandidateCorpus {
    param([string]$Directory, [object]$Expected)
    $ManifestFile = Join-Path $Directory "manifest.json"
    if (-not (Test-Path -LiteralPath $ManifestFile)) { throw "STOP: corpus candidate manifest missing: $ManifestFile" }
    $Manifest = Get-Content -LiteralPath $ManifestFile -Raw | ConvertFrom-Json
    foreach ($Property in $Expected.hashes.PSObject.Properties) {
        $Artifact = Join-Path $Directory ($Property.Name.Replace("/", "\"))
        if (-not (Test-Path -LiteralPath $Artifact)) { throw "STOP: candidate artifact missing: $Artifact" }
        $Actual = (Get-FileHash -LiteralPath $Artifact -Algorithm SHA256).Hash.ToLower()
        if ($Actual -ne $Property.Value) { throw "STOP: candidate artifact hash differs for $($Property.Name)." }
    }
    $Bm25 = (Get-FileHash -LiteralPath (Join-Path $Directory "index\bm25.json") -Algorithm SHA256).Hash.ToLower()
    if ($Bm25 -ne $Expected.bm25_sha256 -or $Manifest.status -ne "diagnostic_not_competitive_freeze") {
        throw "STOP: candidate BM25/status does not match the independently evaluated corpus."
    }
}

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$CommonArgs = @(
    "-Work", $Repo, "-CorpusSet", "v01+v02+v03", "-InputFile", "data\sample_50.jsonl",
    "-NoPull", "-Recomendada", "-PromptVersion", "v6",
    "-RetrievalMode", "option", "-K", "8", "-CandidateK", "30", "-GraphBudget", "10"
)
if ($AllowBusyGpu) { $CommonArgs += "-AllowBusyGpu" }
if ($SkipSmoke) { $CommonArgs += "-SkipSmoke" }
$Runs = @(
    @{ Name = "corpus_v03_v6_bm25_$Stamp"; Retriever = "bm25"; Rerank = $false; ExactLocator = $false; NativeOptionFusion = $false },
    @{ Name = "corpus_v03_v6_hybrid_full_$Stamp"; Retriever = "hybrid"; Rerank = $true; ExactLocator = $true; NativeOptionFusion = $true }
)
$Python = Join-Path $Repo ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) { throw "STOP: crea/verifica .venv antes de la corrida." }
$Results = @()
foreach ($Profile in $Runs) {
    if (Test-Path -LiteralPath $ManifestPath) {
        Assert-CandidateCorpus -Directory $CorpusDir -Expected $ExpectedCorpus
    } elseif (Test-Path -LiteralPath $CorpusDir) {
        throw "STOP: incomplete generated candidate directory exists at $CorpusDir; inspect it before removing or rebuilding."
    } elseif ($Profile.Retriever -ne "bm25") {
        throw "STOP: the first BM25 control must build the candidate before hybrid can run."
    }
    $Args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\tools\kingscode_pc_nueva_diagnostico.ps1") + $CommonArgs + @("-RetrieverMode", $Profile.Retriever, "-RunName", $Profile.Name)
    if ($Profile.Rerank) { $Args += "-Rerank" }
    if ($Profile.ExactLocator) { $Args += "-ExactLocator" }
    if ($Profile.NativeOptionFusion) { $Args += "-NativeOptionFusion" }
    & powershell @Args
    if ($LASTEXITCODE -ne 0) { throw "STOP: falló $($Profile.Name); los artefactos de la corrida se conservaron." }
    Assert-CandidateCorpus -Directory $CorpusDir -Expected $ExpectedCorpus

    $Out = Join-Path $Repo "reports\decoder_diagnostic\$($Profile.Name)"
    $Summary = Get-Content -LiteralPath (Join-Path $Out "RESUMEN.json") -Raw | ConvertFrom-Json
    $Evaluation = Get-Content -LiteralPath (Join-Path $Out "evaluation_official.json") -Raw | ConvertFrom-Json
    $CitationDiagnostic = Get-Content -LiteralPath (Join-Path $Out "diagnostico_citas.json") -Raw | ConvertFrom-Json
    $BatchReport = Get-Content -LiteralPath (Join-Path $Out "batch\batch_report.json") -Raw | ConvertFrom-Json
    $BatchPath = Join-Path $Out "batch\submissions.jsonl"
    $Rows = @([IO.File]::ReadAllLines($BatchPath) | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json })
    $Ids = @($Rows | ForEach-Object { [string]$_.id })
    $UniqueIds = @($Ids | Sort-Object -Unique)
    if ($Rows.Count -ne 50 -or $UniqueIds.Count -ne 50) { throw "STOP: $($Profile.Name) no produjo 50 filas/IDs únicos." }
    & $Python tools\validate_test_submission.py --test data\sample_50.jsonl $BatchPath | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "STOP: schema/ID validation failed for $($Profile.Name)." }
    $Results += [ordered]@{
        run = $Profile.Name; retriever = $Profile.Retriever; rerank = $Profile.Rerank
        exact_locator = $Profile.ExactLocator; native_option_fusion = $Profile.NativeOptionFusion
        summary = $Summary; official = $Evaluation
        rows = $Rows.Count; unique_ids = $UniqueIds.Count
        submission_sha256 = (Get-FileHash -LiteralPath $BatchPath -Algorithm SHA256).Hash.ToLower()
        timing_ms = [ordered]@{ retrieval_p50 = $Summary.diagnostics.retrieval_ms_p50; retrieval_p95 = $Summary.diagnostics.retrieval_ms_p95
                               generation_p50 = $Summary.diagnostics.generation_ms_p50; generation_p95 = $Summary.diagnostics.generation_ms_p95
                               seconds_per_question = $Summary.segundos_por_pregunta; projected_hours_992 = $Summary.proyeccion_992_horas }
        peak_reserved_vram_gb = $Summary.diagnostics.peak_reserved_vram_gb
        citation_metrics = $CitationDiagnostic.metrics
        unsupported_citation_rate_official = $Evaluation.citas.tasa_sin_respaldo
        fallback_ids = $BatchReport.fallback_ids
        evidence_and_batch_diagnostics = $BatchReport.diagnostics
    }
}

$ProxyLines = @(& $Python tools\analyze_ragas_proxy.py --no-encoder `
    (Join-Path $Repo "reports\decoder_diagnostic\$($Runs[0].Name)\batch\submissions.jsonl") `
    (Join-Path $Repo "reports\decoder_diagnostic\$($Runs[1].Name)\batch\submissions.jsonl"))
if ($LASTEXITCODE -ne 0) { throw "No se pudieron calcular proxies locales de sample_50." }
$AlignmentLines = @(& $Python tools\analyze_citation_alignment.py `
    (Join-Path $Repo "reports\decoder_diagnostic\$($Runs[0].Name)\batch\submissions.jsonl") `
    (Join-Path $Repo "reports\decoder_diagnostic\$($Runs[1].Name)\batch\submissions.jsonl"))
if ($LASTEXITCODE -ne 0) { throw "No se pudo calcular alineación de citas." }
$Proxy = @($ProxyLines | ForEach-Object { $_ | ConvertFrom-Json })
$Alignment = @($AlignmentLines | ForEach-Object { $_ | ConvertFrom-Json })

$BaselineScore = [double]$Results[0].official.total_automatico.obtenidos
$CandidateScore = [double]$Results[1].official.total_automatico.obtenidos
$ScoreGate = $CandidateScore -gt $BaselineScore
$ClosedGate = [double]$Results[1].official.cerradas.puntos -ge [double]$Results[0].official.cerradas.puntos
$NoUnsupportedCitations = @($Results | Where-Object { $_.official.citas.tasa_sin_respaldo -ne 0 }).Count -eq 0
$CitationGate = $NoUnsupportedCitations -and
                [double]$Results[1].official.citas.puntos -ge ([double]$Results[0].official.citas.puntos - 0.5)
$RuntimeGate = [double]$Results[1].summary.proyeccion_992_horas -le 5
$StructureGate = $Results[1].official.validacion.errores -eq 0 -and
                  $Results[1].summary.fallbacks_pipeline_error -le $Results[0].summary.fallbacks_pipeline_error
$ProxyGate = [double]$Proxy[1].token_f1_mean -ge ([double]$Proxy[0].token_f1_mean - 0.03) -and
             [double]$Proxy[1].bleu4_mean -ge ([double]$Proxy[0].bleu4_mean - 0.03)
$Eligible = $ScoreGate -and $ClosedGate -and $CitationGate -and $RuntimeGate -and $StructureGate -and $ProxyGate
$Comparison = [ordered]@{
    status = $(if ($Eligible) { "HYBRID_ELIGIBLE_FOR_REVIEW" } else { "HYBRID_NOT_ADOPTED" })
    branch = $Branch; commit = $Commit; sample_sha256 = (Get-FileHash -LiteralPath "data\sample_50.jsonl" -Algorithm SHA256).Hash.ToLower()
    model_lock_sha256 = (Get-FileHash -LiteralPath "config\models.lock.json" -Algorithm SHA256).Hash.ToLower()
    candidate_corpus = $ExpectedCorpus; independent_c1_report_sha256 = (Get-FileHash -LiteralPath $GatePath -Algorithm SHA256).Hash.ToLower()
    runs = $Results; local_proxy = $Proxy; citation_alignment = $Alignment
    gates = [ordered]@{ score_strictly_higher = $ScoreGate; closed_not_lower = $ClosedGate; citations_no_material_regression = $CitationGate
                       projected_runtime_le_5h = $RuntimeGate; schema_ids_fallbacks = $StructureGate; lexical_proxy_not_collapsed = $ProxyGate }
    experiment = "v6 BM25 control vs v6 hybrid + rerank + exact locator + native option fusion; same candidate corpus and sample_50"
    ragas = "not run; requires separate explicit approval after a single complete candidate wins"
}
$ComparisonPath = Join-Path $Repo "reports\corpus_v03_sample50_comparison_$Stamp.json"
$Comparison | ConvertTo-Json -Depth 12 | Out-File -LiteralPath $ComparisonPath -Encoding utf8
$Comparison | ConvertTo-Json -Depth 6
Write-Host "Comparación guardada: $ComparisonPath" -ForegroundColor Green
