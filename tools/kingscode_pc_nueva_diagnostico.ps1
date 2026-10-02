# =====================================================================
# KingsCode - PC NUEVA con GPU: de Windows limpio al diagnostico Qwen3-8B + BM25
#
# Un solo script, sin admin, Windows PowerShell 5.1. Cada paso se salta si ya esta hecho.
#   [0] Git y Python 3.12 (los instala con winget en el usuario si faltan); GPU NVIDIA.
#   [1] Clona o actualiza main en -Work.
#   [2] .venv + dependencias + PyTorch CUDA segun el driver.
#   [3] Corpus v0.1, en este orden: archivo local (-CorpusArchive), release publico o,
#       si no hay ninguno, descarga de las fuentes oficiales con el acquire + build de A
#       (config/sources.json). Compara documento por documento contra los hashes de v0.1
#       (corpus_manifest.json) y lo registra; un corpus descargado que no sea identico
#       sirve para diagnostico, no como freeze.
#  [3b] Corpus combinado v0.1 + v0.2 (corpora\corpus-v0.2, 4 documentos provisionales)
#       en corpus_v01_v02\ con tools\build_combined_corpus.py. -CorpusSet v01 lo omite.
#   [4] Pesos fijados por lock: Qwen3-8B (decoder) + embedding/reranker 0.6B (smoke).
#   [5] Smoke real en GPU (BF16, temperatura 0).
#   [6] Diagnostico: sample_50 con Qwen3-8B + retrieval elegido (k=8) + guardas,
#       y evaluador oficial automatico (sin RAGAS).
#   [7] RAGAS SOLO con -Ragas (gasta creditos de OpenRouter; la llave se pide oculta
#       y nunca se escribe a disco).
#
# Esto es un DIAGNOSTICO OPERATIVO (tiempos, JSON valido, advertencias, abstenciones),
# no la seleccion de decoder ni de retrieval: eso espera el freeze de A.
#
# Uso (desde cualquier carpeta):
#   powershell -ExecutionPolicy Bypass -File kingscode_pc_nueva_diagnostico.ps1
#   ... -CorpusArchive "D:\kingscode-corpus-v0.1.tar.gz"   (con snapshot-files.sha256.json al lado)
#   ... -Ragas                                             (solo con autorizacion de Esteban)
#   ... -AllowKnownLocalCorpusDrift -RetrieverMode hybrid -Rerank
#   ... -ExactLocator                                      (locator exacto de A; cambiar una variable por corrida)
#   ... -PromptVersion v4                                  (prompt v4: abstencion listada, minimos de extension, justificacion primero)
#   ... -CitationFill                                      (hasta 5 citas verificadas en referencia_legal/justificacion)
#   ... -CitationFill -CitationFillExtra 0                 (solo fuentes declaradas por Qwen)
#   ... -CitationFill -CitationFillExtra 1                 (a lo sumo una fuente adicional)
#   ... -CiteMentions 3                                    (citas a nivel de cuerpo de normas NOMBRADAS en la evidencia)
#   ... -Recomendada                                       (c1: v4 + CitationFill; CiteMentions sigue opt-in)
#   ... -SkipVerify                                        (omite regenerar 3 preguntas para comprobar reproducibilidad)
#   SABADO (set ciego, misma configuracion elegida):
#   ... -InputFile data\test_992.jsonl -RunName final_992 <flags elegidos>      -> copia submissions.jsonl a la raiz
#   ... -InputFile data\test_992.jsonl -RunName final_992 -Resume <mismos flags> (si se corta: reanuda sin repetir)
#   ... -Work "D:\KingsCode"  -RunName "qwen3_8b_bm25_prueba2"
# =====================================================================
param(
    [string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia",
    [string]$GitHubRepo = "IngSeb0/KingsCodeNvidia",
    [string]$Tag = "corpus-v0.1-snapshot",
    [string]$CorpusArchive = "",
    [string]$Model = "qwen3-8b",
    [string]$RunName = "",
    [ValidateSet("v01+v02", "v01")] [string]$CorpusSet = "v01+v02",
    [switch]$AllowKnownLocalCorpusDrift,
    [ValidateSet("bm25", "dense", "hybrid")] [string]$RetrieverMode = "bm25",
    [ValidateRange(1, 500)] [int]$CandidateK = 30,
    [ValidateSet("1", "2")] [int]$RerankerBatchSize = 2,
    [ValidateRange(0, 100)] [int]$GraphBudget = 10,
    [switch]$Rerank,
    [switch]$NativeOptionFusion,
    [switch]$ExactLocator,
    [ValidateSet("v3", "v4")] [string]$PromptVersion = "v3",
    [string]$InputFile = "data\sample_50.jsonl",
    [switch]$Resume,
    [switch]$CitationFill,
    [ValidateRange(-1, 5)] [int]$CitationFillExtra = -1,
    [int]$CiteMentions = 0,
    [switch]$Recomendada,
    [switch]$SkipVerify,
    [switch]$Ragas,
    [switch]$SkipSmoke,
    [switch]$PilotRun,
    [switch]$NoPull   # congela el codigo actual (comparaciones y sabado): no hace git pull
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
function Step($m) { Write-Host ""; Write-Host ">>> $m" -ForegroundColor Cyan }
function Warn($m) { Write-Host "AVISO: $m" -ForegroundColor Yellow }
function Check($w) { if ($LASTEXITCODE -ne 0) { throw "STOP: $w (exit $LASTEXITCODE)" } }
function RefreshPath { $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine") }
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
if ($Recomendada) { $PromptVersion = "v4"; $CitationFill = [switch]::new($true) }
if ($CitationFillExtra -ge 0 -and -not $CitationFill) { throw "-CitationFillExtra requiere -CitationFill." }
if (-not $RunName) { $RunName = "${Model}_${RetrieverMode}_c${CandidateK}_rb${RerankerBatchSize}_gb${GraphBudget}$(if ($Rerank) { '_rerank' })$(if ($NativeOptionFusion) { '_nativeopt' })$(if ($ExactLocator) { '_locator' })_p$PromptVersion$(if ($CitationFill) { '_fill' })$(if ($CitationFillExtra -ge 0) { "_x$CitationFillExtra" })$(if ($CiteMentions -gt 0) { "_men$CiteMentions" })_$Stamp" }

# ---------------------------------------------------------------------
Step "[0] Herramientas: Git, Python 3.12, GPU"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw "STOP: falta Git y no hay winget. Instala Git desde https://git-scm.com/download/win y vuelve a correr." }
    winget install --id Git.Git -e --scope user --accept-source-agreements --accept-package-agreements
    RefreshPath
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "STOP: Git no quedo en el PATH. Cierra y abre PowerShell y vuelve a correr." }
}
function Find-Python {
    foreach ($c in @(@{Exe = "py"; Args = @("-3.12")}, @{Exe = "py"; Args = @("-3.11")}, @{Exe = "python"; Args = @()})) {
        try {
            $v = & $c.Exe @($c.Args) -c "import sys; print(sys.version_info >= (3, 11))" 2>$null
            if ($v -eq "True") { return $c }
        } catch { }
    }
    return $null
}
$PyCmd = Find-Python
if (-not $PyCmd) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw "STOP: falta Python 3.12. Instalalo desde python.org ('Install for me only', marcar 'Add to PATH')." }
    winget install --id Python.Python.3.12 -e --scope user --accept-source-agreements --accept-package-agreements
    RefreshPath
    $PyCmd = Find-Python
    if (-not $PyCmd) { throw "STOP: Python no quedo en el PATH. Cierra y abre PowerShell y vuelve a correr." }
}
Write-Host ("Python base: {0} {1}" -f $PyCmd.Exe, ($PyCmd.Args -join " "))
if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) { throw "STOP: no hay nvidia-smi. Instala el driver NVIDIA (>= 12.1 CUDA) y vuelve a correr." }
$DriverCuda = [double]((nvidia-smi | Select-String "CUDA Version:\s*([0-9.]+)").Matches[0].Groups[1].Value)
Write-Host "Driver NVIDIA con CUDA $DriverCuda"

# ---------------------------------------------------------------------
Step "[1] Repo: main en $Work"
if (-not (Test-Path "$Work\.git")) {
    New-Item -ItemType Directory -Force (Split-Path $Work) | Out-Null
    git clone "https://github.com/$GitHubRepo.git" $Work; Check "git clone"
}
Set-Location $Work
if (git status --porcelain --untracked-files=no) { git status --short; throw "STOP: $Work tiene cambios locales en archivos versionados; revisalos (no se descartan solos)." }
if ($NoPull) { Write-Host "-NoPull: se usa el commit local sin actualizar." -ForegroundColor Yellow }
else { git checkout main; Check "checkout main"; git pull --ff-only origin main; Check "pull main" }
$Sha = (git rev-parse HEAD).Trim()
Write-Host "main @ $Sha"
# Si esta copia (p. ej. bajada de raw.githubusercontent, que cachea minutos) difiere de la del
# repo recien actualizado, se relanza la del repo con los mismos parametros.
$RepoScript = "$Work\tools\kingscode_pc_nueva_diagnostico.ps1"
if ((Test-Path $RepoScript) -and ((Get-FileHash $PSCommandPath).Hash -ne (Get-FileHash $RepoScript).Hash)) {
    Write-Host "Esta copia del script es distinta de la de main; se usa $RepoScript" -ForegroundColor Yellow
    & $RepoScript @PSBoundParameters
    exit $LASTEXITCODE
}

# ---------------------------------------------------------------------
Step "[2] Entorno Python (.venv) y PyTorch CUDA"
if (-not (Test-Path ".venv\Scripts\python.exe")) { & $PyCmd.Exe @($PyCmd.Args) -m venv .venv; Check "crear .venv" }
$Py = "$Work\.venv\Scripts\python.exe"
& $Py -m pip install --upgrade pip --quiet; Check "pip"
& $Py -m pip install -r requirements-knowledge.txt --quiet; Check "requirements-knowledge"
$HasCuda = $false
try { & $Py -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)" 2>$null; $HasCuda = ($LASTEXITCODE -eq 0) } catch { }
if (-not $HasCuda) {
    $Index = if ($DriverCuda -ge 12.6) { "cu126" } elseif ($DriverCuda -ge 12.4) { "cu124" } elseif ($DriverCuda -ge 12.1) { "cu121" } else { "" }
    if (-not $Index) { throw "STOP: el driver solo admite CUDA $DriverCuda; actualiza el driver NVIDIA (>= 12.1)." }
    & $Py -m pip install torch --index-url "https://download.pytorch.org/whl/$Index"; Check "PyTorch $Index"
}
& $Py -m pip install -r requirements-gpu.txt --quiet; Check "requirements-gpu"
$Rt = (& $Py -c "import json,torch; p=torch.cuda.get_device_properties(0); print(json.dumps({'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':p.name,'vram_gb':round(p.total_memory/2**30,1),'bf16':torch.cuda.is_bf16_supported()}))") | ConvertFrom-Json
Write-Host ("GPU {0}, {1} GB, BF16={2}, torch {3} / CUDA {4}" -f $Rt.gpu, $Rt.vram_gb, $Rt.bf16, $Rt.torch, $Rt.cuda)
if (-not $Rt.bf16) { throw "STOP: la GPU no soporta BF16; el decoder esta fijado en BF16 (int8/int4 solo con registro de OOM)." }
if ($Rt.vram_gb -lt 20) { Warn "menos de 20 GB de VRAM: Qwen3-8B en BF16 usa ~19 GB y puede dar OOM (queda registrado)." }

# ---------------------------------------------------------------------
Step "[3] Corpus v0.1: archivo local > release > descarga oficial (acquire de A)"
$CorpusOrigin = "existente"
if (-not (Test-Path "corpus\manifest.json")) {
    $Archive = $null
    if ($CorpusArchive) {
        if (-not (Test-Path $CorpusArchive)) { throw "STOP: no existe $CorpusArchive (quita -CorpusArchive para descargar de las fuentes oficiales)." }
        $Archive = (Resolve-Path $CorpusArchive).Path
        $Files = Join-Path (Split-Path $Archive) "snapshot-files.sha256.json"
        if (-not (Test-Path $Files)) { throw "STOP: falta snapshot-files.sha256.json junto a $Archive (lo genera package_corpus_snapshot.py pack)." }
        $CorpusOrigin = "archivo $Archive"
    } else {
        $Dl = "$HOME\kingscode_descargas"
        New-Item -ItemType Directory -Force $Dl | Out-Null
        $Url = "https://github.com/$GitHubRepo/releases/download/$Tag"
        try {
            foreach ($f in @("kingscode-corpus-v0.1.tar.gz", "snapshot-files.sha256.json")) {
                if (-not (Test-Path "$Dl\$f")) { Write-Host "Descargando $f del release ..."; Invoke-WebRequest -UseBasicParsing -Uri "$Url/$f" -OutFile "$Dl\$f" }
            }
            $Archive, $Files = "$Dl\kingscode-corpus-v0.1.tar.gz", "$Dl\snapshot-files.sha256.json"
            $CorpusOrigin = "release $Tag"
        } catch {
            Remove-Item "$Dl\kingscode-corpus-v0.1.tar.gz", "$Dl\snapshot-files.sha256.json" -ErrorAction SilentlyContinue
            Warn "no hay release $Tag; se descarga de las fuentes oficiales con el acquire de A."
        }
    }
    if ($Archive) {
        & $Py tools\package_corpus_snapshot.py verify $Archive --files $Files; Check "verificacion del snapshot antes de extraer"
        tar -xzf $Archive -C $Work; Check "tar -xzf"
    } else {
        # Descarga oficial (config/sources.json, 163 objetivos) y reconstruccion determinista.
        $AcqReport = "$HOME\kingscode_acquire_$Stamp.json"
        # Sin --corpus: el default de A es ROOT/corpus (absoluto). Una ruta relativa rompe raw.relative_to(ROOT).
        & $Py tools\member_a.py acquire --workers 3 | Out-File -Encoding utf8 $AcqReport
        Check "acquire (descarga de fuentes oficiales)"
        $Acq = Get-Content $AcqReport -Raw | ConvertFrom-Json
        Write-Host ("Descargados {0} de {1} objetivos oficiales." -f $Acq.downloaded, $Acq.targets)
        if ($Acq.downloaded -lt 1) {
            $Acq.failed | Group-Object { ($_.error -split "`n")[0].Substring(0, [Math]::Min(120, ($_.error -split "`n")[0].Length)) } |
                Sort-Object Count -Descending | Select-Object -First 5 | ForEach-Object { Write-Host ("  {0,3} x {1}" -f $_.Count, $_.Name) -ForegroundColor Yellow }
            throw ("STOP: no se descargo ningun documento oficial (errores arriba; reporte en $AcqReport).`n" +
                   "  Probar la red:  curl.exe -sS -o NUL -w ""%{http_code}"" https://www.funcionpublica.gov.co/`n" +
                   "  Alternativa exacta: copiar el corpus de Luis y correr con -CorpusArchive.")
        }
        & $Py tools\member_a.py build | Out-Null; Check "build (pasajes, grafo, BM25)"
        git checkout -- corpus_manifest.json 2>$null   # build reescribe el manifest versionado de v0.1; se conserva la referencia
        $global:LASTEXITCODE = 0
        $CorpusOrigin = "descarga oficial (acquire + build)"
    }
    # Marcador fuera de corpus\ (no versionado): las corridas siguientes recuerdan el origen.
    $CorpusOrigin | Out-File -Encoding ascii "$Work\.kingscode_corpus_origin.txt"
} elseif (Test-Path "$Work\.kingscode_corpus_origin.txt") {
    $CorpusOrigin = (Get-Content "$Work\.kingscode_corpus_origin.txt" -Raw).Trim()
}
$Cmp = (& $Py -c @"
import hashlib, json
from pathlib import Path
ref = {d['doc_id']: d['source_sha256'] for d in json.loads(Path('corpus_manifest.json').read_text(encoding='utf-8'))['documentos']}
got = {d['doc_id']: d['source_sha256'] for d in json.loads(Path('corpus/manifest.json').read_text(encoding='utf-8'))['documentos']}
same = sorted(k for k in ref if got.get(k) == ref[k])
ref_at = {d['doc_id']: d.get('retrieved_at') for d in json.loads(Path('corpus_manifest.json').read_text(encoding='utf-8'))['documentos']}
got_at = {d['doc_id']: d.get('retrieved_at') for d in json.loads(Path('corpus/manifest.json').read_text(encoding='utf-8'))['documentos']}
print(json.dumps({'v01_docs': len(ref), 'identical_raw': len(same), 'changed': sorted(k for k in ref if k in got and got[k] != ref[k]), 'missing': sorted(set(ref) - set(got)),
                  'same_retrieved_at': sum(1 for k in ref_at if got_at.get(k) == ref_at[k])}))
"@) | ConvertFrom-Json
# Corpus construido antes del marcador: si ninguna fecha de descarga coincide con v0.1, se descargo en esta PC.
if ($CorpusOrigin -eq "existente" -and $Cmp.same_retrieved_at -eq 0) {
    $CorpusOrigin = "descarga oficial (acquire + build, detectada por fechas)"
    $CorpusOrigin | Out-File -Encoding ascii "$Work\.kingscode_corpus_origin.txt"
}
Write-Host ("Corpus ({0}): {1}/{2} documentos con bytes identicos a v0.1; cambiados {3}; faltantes {4}" -f $CorpusOrigin, $Cmp.identical_raw, $Cmp.v01_docs, @($Cmp.changed).Count, @($Cmp.missing).Count)
# verify_member_a_v02 compara contra corpus\manifest.json (el propio); un corpus reconstruido
# lo pasaria aunque difiera de v0.1. "Exacto" exige ademas los 163 documentos identicos a v0.1.
& $Py tools\verify_member_a_v02.py | Out-Null
$CorpusExact = ($LASTEXITCODE -eq 0) -and ($Cmp.identical_raw -eq $Cmp.v01_docs)
# Referencias conocidas de passages.jsonl: 3b2b7a7b... (corpus_manifest.json versionado = tmp\benchmark_corpus_v1
# del freeze 4090) y f048d303... (corpus\ de la 4090 de Luis, 2026-10-01). Se registra, no se decide aqui.
$PassagesSha = (Get-FileHash corpus\passages.jsonl -Algorithm SHA256).Hash.ToLower()
$PassagesRef = $(if ($PassagesSha -like "3b2b7a7b*") { "igual a corpus_manifest.json (benchmark_corpus_v1)" } elseif ($PassagesSha -like "f048d303*") { "igual al corpus de la 4090 de Luis" } else { "distinto de ambas referencias" })
Write-Host "passages.jsonl $($PassagesSha.Substring(0,12))... : $PassagesRef"
git checkout -- reports/member_a_v02/verification.json 2>$null  # el verificador reescribe este archivo versionado
$global:LASTEXITCODE = 0
if ($CorpusExact) { Write-Host "Corpus v0.1 verificado byte a byte contra los hashes de A." -ForegroundColor Green }
elseif ($CorpusOrigin -like "descarga oficial*") { Warn "el corpus descargado NO es identico a v0.1 (las fuentes cambiaron); sirve para diagnostico, no como freeze. Queda registrado." }
elseif ($AllowKnownLocalCorpusDrift -and $CorpusOrigin -eq "existente" -and
        $PassagesSha -eq "f048d30388d29235ff71a956555444f2d32b67884050f6fc4cb0f63e8d380d9f") {
    Warn "se permite el corpus local conocido de Luis aunque difiera de v0.1; esta corrida es solo diagnostica y no competitiva."
}
else { throw "STOP: el corpus no coincide con los hashes de A (verify_member_a_v02)." }

Step "[3b] Corpus combinado v0.1 + v0.2 (corpora\corpus-v0.2, provisional)"
if ($CorpusSet -eq "v01+v02") {
    if (-not (Test-Path "corpus_v01_v02\manifest.json")) { & $Py tools\build_combined_corpus.py | Out-Null; Check "build_combined_corpus" }
    $CorpusDir = "corpus_v01_v02"
} else { $CorpusDir = "corpus" }
Write-Host "Corpus para el diagnostico: $CorpusDir"
if ($RetrieverMode -in @("dense", "hybrid")) {
    & $Py tools\prepare_models.py --download-retrieval; Check "preparacion de modelos de retrieval"
    & $Py tools\prepare_models.py --verify Qwen/Qwen3-Embedding-0.6B; Check "verificacion del encoder Qwen"
    if (-not (Test-Path "$CorpusDir\index\dense.meta.json")) {
        & $Py tools\member_a.py dense --corpus $CorpusDir; Check "construccion del indice denso combinado"
    }
}
if ($Rerank) { & $Py tools\prepare_models.py --verify Qwen/Qwen3-Reranker-0.6B; Check "verificacion del reranker Qwen" }

# ---------------------------------------------------------------------
Step "[4] Pesos fijados por lock (solo archivos del lock, verificados contra el Hub)"
$FreeGb = [math]::Round((Get-PSDrive (Split-Path $Work -Qualifier).TrimEnd(":")).Free / 1GB, 1)
Write-Host "Espacio libre: $FreeGb GB (Qwen3-8B ~16 GB + retrieval ~2,5 GB)"
if ($FreeGb -lt 25) { Warn "menos de 25 GB libres; la descarga puede fallar." }
& $Py tools\prepare_models.py --download $Model; Check "descarga $Model"
& $Py tools\prepare_models.py --verify $Model; Check "verificacion $Model"
if (-not $SkipSmoke) { & $Py tools\prepare_models.py --download-retrieval; Check "modelos de retrieval para el smoke" }
$env:HF_HUB_OFFLINE = "1"   # desde aqui todo es local: ninguna llamada a la red de Hugging Face

# ---------------------------------------------------------------------
$Out = "reports\decoder_diagnostic\$RunName"
$IsSample = ((Split-Path $InputFile -Leaf) -eq "sample_50.jsonl")
if (-not (Test-Path $InputFile)) { throw "STOP: no existe el archivo de preguntas $InputFile" }
if ((Test-Path $Out) -and -not $Resume) { throw "STOP: ya existe $Out; usa otro -RunName, o -Resume -RunName $RunName para continuar esa corrida." }
New-Item -ItemType Directory -Force $Out | Out-Null
if (-not $SkipSmoke) {
    Step "[5] Smoke real en GPU ($Model, BF16, temperatura 0)"
    & $Py tools\gpu_smoke.py --model $Model --output-root "$Out\smoke"
    if ($LASTEXITCODE -ne 0) { throw "STOP: el smoke fallo; revisa $Out\smoke (si es CUDA_OOM, ese registro habilita int8/int4)." }
}

# ---------------------------------------------------------------------
Step "[6] Diagnostico sample_50: $Model + $RetrieverMode (k=8) + router, guardas (sin seleccion)"
$Run = "$Out\batch"
if ($ExactLocator -and -not $Rerank) {
    # A's Retriever adds locator candidates to the pool but orders by BM25/fused score: a locator-only
    # hit scores 0 and never reaches the top k. Only the reranker can promote it (2026-10-01: an
    # -ExactLocator run without -Rerank produced a byte-identical submissions.jsonl).
    Warn "-ExactLocator sin -Rerank no cambia el resultado (el locator agrega candidatos que solo el reranker puede subir). Usa -Rerank -ExactLocator."
}
# Same configuration for the batch and for the live-verification replay below.
$CommonArgs = @(
    "--input", $InputFile, "--retrieval-mode", "option",
    "--retriever-mode", $RetrieverMode, "--graph-policy", "router",
    "--k", "8", "--candidate-k", "$CandidateK", "--graph-budget", "$GraphBudget", "--corpus", $CorpusDir, "--model", $Model,
    "--reranker-batch-size", "$RerankerBatchSize", "--precision", "bf16", "--prompt-version", $PromptVersion
)
if ($Rerank) { $CommonArgs += "--rerank" }
if ($NativeOptionFusion) { $CommonArgs += "--native-option-fusion" }
if ($ExactLocator) { $CommonArgs += "--exact-locator" }
if ($CitationFill) { $CommonArgs += "--citation-fill" }
if ($CitationFillExtra -ge 0) { $CommonArgs += @("--citation-fill-extra", [string]$CitationFillExtra) }
if ($CiteMentions -gt 0) { $CommonArgs += @("--cite-mentions", [string]$CiteMentions) }
# -Resume: reuse validated checkpoints (same identity enforced by BatchRunner); never --fresh.
# Build the array explicitly: $(if ...) unrolls a one-element array into a string, and splatting a
# string passes it character by character ("- - f r e s h", 2026-10-01).
$FreshArg = @()
if (-not $Resume) { $FreshArg += "--fresh" }
& $Py tools\member_b.py batch --run-dir $Run @FreshArg --retries 0 @CommonArgs
Check "corrida integrada (conserva $Run; reanudar con -Resume -RunName $RunName)"
if ($IsSample) {
    & $Py scripts\evaluate.py --submission "$Run\submissions.jsonl" --split sample --out "$Out\evaluation_official.json"
    Check "evaluador oficial"
} else {
    # Blind set: no labels. BatchRunner already checked every id, no duplicates and the schema.
    if (-not $PilotRun) {
        Copy-Item "$Run\submissions.jsonl" "$Work\submissions.jsonl" -Force
        Write-Host ("Entrega: $Work\submissions.jsonl  sha256 {0}" -f (Get-FileHash "$Run\submissions.jsonl" -Algorithm SHA256).Hash.ToLower()) -ForegroundColor Green
    } else {
        Write-Host "Piloto diagnostico: no se copia una entrega a la raiz del repositorio." -ForegroundColor Yellow
    }
}

# ---------------------------------------------------------------------
$Verify = "omitida (-SkipVerify)"
if (-not $SkipVerify) {
    Step "[6b] Verificacion en vivo simulada: regenerar 3 preguntas (cerrada, semiabierta, abierta) y comparar"
    $Rows = Get-Content "$Run\submissions.jsonl" | ForEach-Object { $_ | ConvertFrom-Json }
    $Ids = @("multiple_choice", "semi_open", "open_ended") | ForEach-Object { $f = $_; ($Rows | Where-Object { $_.formato -eq $f -and -not $_.abstencion } | Select-Object -First 1).id } | Where-Object { $_ -ne $null }
    try {
        $VerifyOut = & $Py tools\member_b.py verify --delivered "$Run\submissions.jsonl" --only ($Ids -join ",") @CommonArgs
        $VerifyOut | Out-File -Encoding utf8 "$Out\verify_live.json"
        # member_b prints one indented JSON object last: parse from the last '{' at column 0.
        $Text = ($VerifyOut | Out-String)
        $At = $Text.LastIndexOf("`n{"); if ($Text.StartsWith("{")) { $At = 0 } elseif ($At -ge 0) { $At += 1 }
        $V = $Text.Substring([math]::Max(0, $At)) | ConvertFrom-Json
        $Verify = [ordered]@{ ids = $Ids; all_match = $V.all_match; row_identical = @($V.results | ForEach-Object { $_.row_identical }) }
        if ($V.all_match) { Write-Host "Reproducibilidad: normas y pasajes coinciden en $($Ids -join ', ')." -ForegroundColor Green }
        else { Warn "REPRODUCIBILIDAD FALLA en alguna pregunta (ver $Out\verify_live.json): riesgo de descalificacion en la verificacion en vivo." }
    } catch {
        # Never lose the run summary because the replay output could not be parsed.
        $Verify = [ordered]@{ ids = $Ids; all_match = $null; error = "$($_.Exception.Message)"; raw = "$Out\verify_live.json" }
        Warn "No se pudo leer la verificacion en vivo ($($_.Exception.Message)); revisa $Out\verify_live.json. El resumen se escribe igual."
    }
}

# ---------------------------------------------------------------------
if ($Ragas -and -not $IsSample) { Warn "RAGAS solo aplica a sample_50 (el set ciego no tiene respuestas esperadas); se omite." }
if ($Ragas -and $IsSample) {
    Step "[7] RAGAS (gasta creditos de OpenRouter)"
    & $Py -m pip install -r scripts\requirements-evaluador.txt --quiet; Check "dependencias del juez RAGAS"
    $JudgeKey = Read-Host "Pega la llave autorizada de OpenRouter" -AsSecureString
    $KeyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($JudgeKey)
    try {
        $env:OPENROUTER_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($KeyPointer)
        Remove-Item Env:\HF_HUB_OFFLINE -ErrorAction SilentlyContinue   # el juez descarga su modelo de similitud
        & $Py scripts\evaluate.py --submission "$Run\submissions.jsonl" --split sample --ragas --out "$Out\evaluation_ragas.json"
        Check "juez RAGAS"
    } finally {
        Remove-Item Env:\OPENROUTER_API_KEY -ErrorAction SilentlyContinue
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($KeyPointer)
    }
} else {
    Write-Host ""; Write-Host "[7] RAGAS omitido (usa -Ragas solo con autorizacion; gasta creditos)." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------
Step "Resumen"
$Br = Get-Content "$Run\batch_report.json" -Raw | ConvertFrom-Json
$Ev = $(if ($IsSample) { Get-Content "$Out\evaluation_official.json" -Raw | ConvertFrom-Json } else { $null })
# Seconds of this session over the items generated in it (resumed items are not re-timed).
$Processed = [math]::Max(1, [int]$Br.rows - [int]$Br.counts.resumed)
$Spq = [math]::Round($Br.seconds / $Processed, 1)
$Summary = [ordered]@{
    main_sha = $Sha; model = $Model; gpu = $Rt.gpu; vram_gb = $Rt.vram_gb; torch = $Rt.torch
    retrieval = "$RetrieverMode$(if ($Rerank) { ' + Qwen reranker' }) candidate_k=$CandidateK graph_budget=$GraphBudget reranker_batch_size=$RerankerBatchSize$(if ($NativeOptionFusion) { ' + native option fusion' })$(if ($ExactLocator) { ' + locator exacto' }) k=8 graph router (diagnostico, no freeze)"
    prompt_version = "grounded-formats-$PromptVersion"; citation_fill = [bool]$CitationFill; citation_fill_extra = $CitationFillExtra; cite_mentions = $CiteMentions; verificacion_en_vivo = $Verify
    corpus = $CorpusDir; corpus_origin = $CorpusOrigin; corpus_v01_raw_identical_and_verified = $CorpusExact; corpus_v01_comparison = $Cmp
    corpus_diagnostic_override = ($AllowKnownLocalCorpusDrift -and -not $CorpusExact)
    passages_sha256 = $PassagesSha; passages_reference = $PassagesRef
    input = $InputFile; filas = $Br.rows; completo = $Br.complete; reanudadas = $Br.counts.resumed
    automatico_sin_ragas = $(if ($Ev) { "$($Ev.total_automatico.obtenidos) / $($Ev.total_automatico.posibles)" } else { "n/a (set ciego)" })
    cerradas = $Ev.cerradas.puntos; citas = $Ev.citas.puntos; abstencion = $Ev.abstencion.puntos
    errores_validacion = $Ev.validacion.errores
    fallbacks_pipeline_error = @($Br.fallback_ids).Count
    segundos_por_pregunta = $Spq; proyeccion_992_horas = [math]::Round($Spq * 992 / 3600, 2)
    diagnostics = $Br.diagnostics
    ragas = $(if ($Ragas) { "$Out\evaluation_ragas.json" } else { "no ejecutado" })
}
$Summary | ConvertTo-Json -Depth 8 | Out-File -Encoding utf8 "$Out\RESUMEN.json"
Write-Host ("{0}: {1} automatico sin RAGAS | cerradas {2}, citas {3}, abstencion {4} | {5} s/pregunta -> 992 en {6} h | fallbacks {7}" -f `
    $Model, $Summary.automatico_sin_ragas, $Summary.cerradas, $Summary.citas, $Summary.abstencion, $Spq, $Summary.proyeccion_992_horas, $Summary.fallbacks_pipeline_error) -ForegroundColor Green
if ($Summary.proyeccion_992_horas -gt 5) { Warn "la proyeccion para 992 supera 5 h: la ventana del sabado es de 6 h." }
# Presupuesto del enunciado (B.5): ~22 s/pregunta para 992 en 6 h. Margen de seguridad: 20 s.
if ($Spq -gt 20) { Warn "$Spq s/pregunta supera el margen de 20 s (presupuesto 22 s): esta configuracion NO es apta para el sabado." }
$D = $Br.diagnostics
Write-Host ("Tiempos: generacion p50 {0} ms / p95 {1} ms | retrieval p50 {2} ms / p95 {3} ms | VRAM pico reservado {4} GB | reranker omitido {5}" -f `
    [math]::Round([double]$D.generation_ms_p50), [math]::Round([double]$D.generation_ms_p95), [math]::Round([double]$D.retrieval_ms_p50),
    [math]::Round([double]$D.retrieval_ms_p95), $D.peak_reserved_vram_gb, $D.rerank_skipped)
if ($D.peak_reserved_vram_gb -gt 22) { Warn "VRAM pico $($D.peak_reserved_vram_gb) GB (tarjeta 24 GB): riesgo de desborde a RAM del sistema y caida de velocidad." }
if ($D.rerank_skipped -gt 0) { Warn "$($D.rerank_skipped) preguntas usaron el orden previo al reranker (pasaje mas largo que max_length del reranker)." }
Write-Host "Envia a Esteban: $Work\$Out\RESUMEN.json, $Out\evaluation_official.json y $Run\batch_report.json"
