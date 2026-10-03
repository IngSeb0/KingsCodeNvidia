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
#   ... -CiteMentions 3                                    (citas a nivel de cuerpo de normas NOMBRADAS en la evidencia)
#   ... -Recomendada                                       (configuracion recomendada: v4 + CitationFill + CiteMentions 5)
#   ... -Recomendada -K 10                                 (entrega 10 pasajes: los que mira el evaluador)
#   ... -Recomendada -PromptVersion v6                    (prompt v6: razonamiento juridico, sin escudarse en la evidencia)
#   ... -Recomendada -MaxContext 16384                    (contexto de 16k: el modelo ve los 8 pasajes completos)
#   ... -Recomendada -DocCap 3                             (maximo 3 pasajes por documento: evidencia mas diversa)
#   ... -Recomendada -RetrievalMode option_plan            (texto libre con consultas extra del planner Qwen; cerradas igual)
#   ... -SkipVerify                                        (omite regenerar 3 preguntas para comprobar reproducibilidad)
#   ... -ShowAnswers                                       (imprime pregunta y respuesta al completar cada ítem)
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
    [ValidateSet("v01+v02", "v01+v02+v03", "v01")] [string]$CorpusSet = "v01+v02",
    [switch]$AllowKnownLocalCorpusDrift,
    [switch]$AllowBusyGpu,
    [switch]$FitPassages,   # recorta los pasajes largos en el prompt para que el modelo vea los 8   # no detenerse si otra sesion/proceso ya ocupa la VRAM
    [ValidateSet("bm25", "dense", "hybrid")] [string]$RetrieverMode = "bm25",
    [ValidateRange(1, 500)] [int]$CandidateK = 30,
    [ValidateRange(1, 10)] [int]$K = 8,
    [ValidateRange(0, 8)] [int]$DocCap = 0,
    [string]$HybridFormats = "",   # p.ej. "semi_open,open_ended": BM25+semantica en esos formatos (requiere -RetrieverMode hybrid)
    [ValidateSet(0, 12288, 16384)] [int]$MaxContext = 0,   # 0 = 8192 del config; 16384: el modelo ve todos los pasajes   # >0: maximo N pasajes por documento (trae 10 y diversifica)
    [ValidateSet("option", "option_plan")] [string]$RetrievalMode = "option",   # option_plan: cerradas por opcion, texto libre con plan de Qwen   # pasajes entregados; el evaluador mira los 10 primeros
    [ValidateSet("1", "2")] [int]$RerankerBatchSize = 2,
    [ValidateRange(0, 100)] [int]$GraphBudget = 10,
    [switch]$Rerank,
    [switch]$NativeOptionFusion,
    [switch]$RerankerScoreCache,
    [switch]$ExactLocator,
    [ValidateSet("v3", "v4", "v6", "v7", "v8", "v9")] [string]$PromptVersion = "v3",
    [string]$InputFile = "data\sample_50.jsonl",
    [switch]$Resume,
    [switch]$CitationFill,
    [int]$CiteMentions = 0,
    [switch]$Recomendada,
    [switch]$SkipVerify,
    [switch]$Ragas,
    [switch]$ShowAnswers,
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
if ($Recomendada) { if ($PromptVersion -eq "v3") { $PromptVersion = "v4" }; $CitationFill = [switch]::new($true); if ($CiteMentions -eq 0) { $CiteMentions = 5 } }
if (-not $RunName) { $RunName = "${Model}_${RetrieverMode}$(if ($K -ne 8) { "_k$K" })$(if ($RetrievalMode -eq "option_plan") { "_oplan" })$(if ($DocCap -gt 0) { "_cap$DocCap" })$(if ($FitPassages) { "_fit" })$(if ($MaxContext -gt 0) { "_ctx$MaxContext" })_c${CandidateK}_rb${RerankerBatchSize}_gb${GraphBudget}$(if ($Rerank) { '_rerank' })$(if ($NativeOptionFusion) { '_nativeopt' })$(if ($RerankerScoreCache) { '_rcache' })$(if ($ExactLocator) { '_locator' })_p$PromptVersion$(if ($CitationFill) { '_fill' })$(if ($CiteMentions -gt 0) { "_men$CiteMentions" })_$Stamp" }

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
if ($CorpusSet -eq "v01+v02+v03") {
    $CorpusDir = "corpus_v03_candidate"
    & $Py tools\build_corpus_v03_additions.py | Out-Null; Check "build_corpus_v03_additions"
    $Inputs = @("corpus", "corpora\corpus-v0.2", "corpora\corpus-additions-v1", "corpora\corpus-v03-additions")
    if (-not (Test-Path "$CorpusDir\manifest.json")) {
        $BuildArgs = @("tools\build_combined_corpus.py", "--base", $Inputs[0])
        foreach ($Addition in $Inputs[1..($Inputs.Length - 1)]) { $BuildArgs += @("--addition", $Addition) }
        $BuildArgs += @("--out", $CorpusDir)
        & $Py @BuildArgs | Out-Null; Check "build_combined_corpus v0.3 candidate"
    } else {
        $Candidate = Get-Content "$CorpusDir\manifest.json" -Raw | ConvertFrom-Json
        foreach ($InputDir in $Inputs) {
            $InputKey = $InputDir.Replace("\", "/")
            $EntryProperty = $Candidate.inputs.PSObject.Properties[$InputKey]
            if (-not $EntryProperty) { throw "STOP: corpus candidato sin entrada congelada $InputKey; no lo sobrescribo." }
            $InputManifest = Get-Content "$InputDir\manifest.json" -Raw | ConvertFrom-Json
            $ManifestHash = (Get-FileHash "$InputDir\manifest.json" -Algorithm SHA256).Hash.ToLower()
            $PassagesHash = (Get-FileHash "$InputDir\passages.jsonl" -Algorithm SHA256).Hash.ToLower()
            if ($EntryProperty.Value.manifest_sha256 -ne $ManifestHash -or $EntryProperty.Value.passages_sha256 -ne $PassagesHash) {
                throw "STOP: $CorpusDir está obsoleto frente a $InputKey. Archiva ese directorio generado y vuelve a ejecutar."
            }
        }
        $PreflightDir = Join-Path ([System.IO.Path]::GetTempPath()) ("corpus-v03-preflight-" + [guid]::NewGuid().ToString("N"))
        & $Py tools\analyze_corpus_coverage.py --corpus $CorpusDir --output-json "$PreflightDir\coverage.json" --output-md "$PreflightDir\coverage.md" | Out-Null
        Check "verificación del corpus candidato existente"
    }
} elseif ($CorpusSet -eq "v01+v02") {
    # Con corpora\corpus-additions-v1 (normas faltantes en v0.1, 2026-10-02) se usa un directorio propio.
    $CorpusDir = $(if (Test-Path "corpora\corpus-additions-v1\manifest.json") { "corpus_v01_v02_a1" } else { "corpus_v01_v02" })
    if (-not (Test-Path "$CorpusDir\manifest.json")) { & $Py tools\build_combined_corpus.py --out $CorpusDir | Out-Null; Check "build_combined_corpus" }
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
Step "[6] Diagnostico sample_50: $Model + $RetrieverMode (k=$K) + router, guardas (sin seleccion)"
# Busy GPU check (2026-10-02): another Windows session (e.g. a Streamlit UI with Qwen loaded) keeps
# ~18 GB of VRAM; the run then spills to shared memory and crawls with NO error and no [batch] line.
try {
    $Gpu = (& nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits | Select-Object -First 1) -split ","
    $UsedMiB = [int]$Gpu[0].Trim(); $TotalMiB = [int]$Gpu[1].Trim()
    Write-Host "VRAM ocupada antes de empezar: $UsedMiB / $TotalMiB MiB"
    if ($UsedMiB -gt 3000) {
        & nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
        $Msg = "La GPU ya tiene $UsedMiB MiB ocupados por otro proceso o sesion (lista arriba; los de otra sesion de Windows pueden no aparecer). Cierra la interfaz/corrida que la usa o cierra la sesion del otro usuario (query user / logoff <ID>)."
        if (-not $AllowBusyGpu) { throw "STOP: $Msg Para correr igual: -AllowBusyGpu." }
        Warn $Msg
    }
} catch [System.Management.Automation.CommandNotFoundException] { Warn "nvidia-smi no disponible: no se pudo comprobar la VRAM libre." }
$Run = "$Out\batch"
if ($ExactLocator -and -not $Rerank) {
    # A's Retriever adds locator candidates to the pool but orders by BM25/fused score: a locator-only
    # hit scores 0 and never reaches the top k. Only the reranker can promote it (2026-10-01: an
    # -ExactLocator run without -Rerank produced a byte-identical submissions.jsonl).
    Warn "-ExactLocator sin -Rerank no cambia el resultado (el locator agrega candidatos que solo el reranker puede subir). Usa -Rerank -ExactLocator."
}
# Same configuration for the batch and for the live-verification replay below.
$CommonArgs = @(
    "--input", $InputFile, "--retrieval-mode", $RetrievalMode,
    "--retriever-mode", $RetrieverMode, "--graph-policy", "router",
    "--k", "$K", "--candidate-k", "$CandidateK", "--graph-budget", "$GraphBudget", "--corpus", $CorpusDir, "--model", $Model,
    "--reranker-batch-size", "$RerankerBatchSize", "--precision", "bf16", "--prompt-version", $PromptVersion
)
if ($Rerank) { $CommonArgs += "--rerank" }
if ($NativeOptionFusion) { $CommonArgs += "--native-option-fusion" }
if ($RerankerScoreCache) { $CommonArgs += "--reranker-score-cache" }
if ($ExactLocator) { $CommonArgs += "--exact-locator" }
if ($CitationFill) { $CommonArgs += "--citation-fill" }
if ($CiteMentions -gt 0) { $CommonArgs += @("--cite-mentions", [string]$CiteMentions) }
if ($DocCap -gt 0) { $CommonArgs += @("--doc-cap", [string]$DocCap) }
if ($HybridFormats) { $CommonArgs += @("--hybrid-formats", $HybridFormats) }
if ($FitPassages) { $CommonArgs += "--fit-passages" }
if ($MaxContext -gt 0) {
    Warn "-MaxContext $MaxContext es EXPERIMENTAL: prompts de hasta ~12k tokens pueden desbordar la VRAM de 24 GB (la atencion determinista no cabe) y la corrida se vuelve casi congelada. Si [batch] muestra sigue generando > 120 s por pregunta, cortar con Ctrl+C."
    $CommonArgs += @("--max-context", [string]$MaxContext)
}
$PlanSeconds = 0
if ($RetrievalMode -eq "option_plan") {
    # Frozen query plans (Qwen planner, public question text only) for the free-text questions.
    # Resumable: an existing plan set with the same identity is reused, never regenerated.
    $PlanWatch = [Diagnostics.Stopwatch]::StartNew()
    $PlanOut = & $Py tools\member_b.py plan --input $InputFile --retrieval-mode option_plan --model $Model --precision bf16
    Check "planner (option_plan)"
    $PlanSeconds = [math]::Round($PlanWatch.Elapsed.TotalSeconds, 1)
    $PlanText = ($PlanOut | Out-String); $At = $PlanText.LastIndexOf("`n{"); if ($PlanText.StartsWith("{")) { $At = 0 } elseif ($At -ge 0) { $At += 1 }
    $PlansDir = ($PlanText.Substring([math]::Max(0, $At)) | ConvertFrom-Json).plans
    if (-not $PlansDir) { throw "STOP: el planner no devolvio la carpeta de planes." }
    Write-Host "Planes congelados: $PlansDir ($PlanSeconds s)" -ForegroundColor Green
    $CommonArgs += @("--plans", $PlansDir)
}
# -Resume: reuse validated checkpoints (same identity enforced by BatchRunner); never --fresh.
# Build the array explicitly: $(if ...) unrolls a one-element array into a string, and splatting a
# string passes it character by character ("- - f r e s h", 2026-10-01).
$FreshArg = @()
if (-not $Resume) { $FreshArg += "--fresh" }
$ShowAnswersArg = @()
if ($ShowAnswers) { $ShowAnswersArg += "--show-answers" }
& $Py tools\member_b.py batch --run-dir $Run @FreshArg --retries 0 @CommonArgs @ShowAnswersArg
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
    if (-not $Ids) { Warn "sin preguntas respondidas para regenerar (todas abstencion): verificacion omitida." }
    else { try {
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
    } }
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
$CitationDiagnostic = $null
if ($IsSample) {
    Step "[8] Diagnóstico de cobertura de citas (post-run, solo lectura)"
    $CitationDiagnosticPath = "$Out\diagnostico_citas.json"
    & $Py tools\diagnose_citation_pipeline.py --run $Run --output $CitationDiagnosticPath
    Check "diagnóstico de citas"
    $CitationDiagnostic = Get-Content $CitationDiagnosticPath -Raw | ConvertFrom-Json
    $Cm = $CitationDiagnostic.metrics
    Write-Host ("Citas de referencia: cobertura en evidencia {0:P1} | recall citado y respaldado {1:P1} | faltantes por contexto {2} | faltantes de evidencia {3} | evidencia sin citar {4}" -f `
        $Cm.evidence_coverage, $Cm.supported_citation_recall, $Cm.expected_bodies_dropped_for_context,
        $Cm.expected_bodies_missing_from_delivered_evidence, $Cm.expected_bodies_available_but_not_cited) -ForegroundColor Cyan
}

# ---------------------------------------------------------------------
Step "Resumen"
$Br = Get-Content "$Run\batch_report.json" -Raw | ConvertFrom-Json
$Ev = $(if ($IsSample) { Get-Content "$Out\evaluation_official.json" -Raw | ConvertFrom-Json } else { $null })
$Rg = $(if ($Ragas -and $IsSample -and (Test-Path "$Out\evaluation_ragas.json")) { Get-Content "$Out\evaluation_ragas.json" -Raw | ConvertFrom-Json } else { $null })
# Seconds of this session over the items generated in it (resumed items are not re-timed).
$Processed = [math]::Max(1, [int]$Br.rows - [int]$Br.counts.resumed)
$Spq = [math]::Round(($Br.seconds + $PlanSeconds) / $Processed, 1)   # incluye el planner de option_plan
$Summary = [ordered]@{
    main_sha = $Sha; model = $Model; gpu = $Rt.gpu; vram_gb = $Rt.vram_gb; torch = $Rt.torch
    retrieval = "$RetrieverMode$(if ($HybridFormats) { " (hibrido solo en $HybridFormats; resto bm25)" })$(if ($Rerank) { ' + Qwen reranker' }) candidate_k=$CandidateK graph_budget=$GraphBudget reranker_batch_size=$RerankerBatchSize$(if ($NativeOptionFusion) { ' + native option fusion' })$(if ($RerankerScoreCache) { ' + reranker score cache' })$(if ($ExactLocator) { ' + locator exacto' }) k=$K graph router (diagnostico, no freeze)"
    prompt_version = "grounded-formats-$PromptVersion"; citation_fill = [bool]$CitationFill; cite_mentions = $CiteMentions; max_context_tokens = $(if ($MaxContext -gt 0) { $MaxContext } else { 8192 }); doc_cap = $DocCap; verificacion_en_vivo = $Verify
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
    diagnostico_citas = $(if ($CitationDiagnostic) { "$CitationDiagnosticPath" } else { "no ejecutado" })
    ragas = $(if ($Rg) { [ordered]@{ archivo = "$Out\evaluation_ragas.json"; correctness = $Rg.correccion_ragas.correctness
        puntos = $Rg.correccion_ragas.puntos; items_juzgados = $Rg.correccion_ragas.n_juzgados
        fallidos = $Rg.correccion_ragas.n_fallidos; juez = $Rg.correccion_ragas.modelo_juez; encoder = $Rg.correccion_ragas.encoder } }
        elseif ($Ragas) { [ordered]@{ archivo = "$Out\evaluation_ragas.json"; estado = "sin resultado" } }
        else { "no ejecutado" })
}
$Summary | ConvertTo-Json -Depth 8 | Out-File -Encoding utf8 "$Out\RESUMEN.json"
Write-Host ("{0}: {1} automatico sin RAGAS | cerradas {2}, citas {3}, abstencion {4} | {5} s/pregunta -> 992 en {6} h | fallbacks {7}" -f `
    $Model, $Summary.automatico_sin_ragas, $Summary.cerradas, $Summary.citas, $Summary.abstencion, $Spq, $Summary.proyeccion_992_horas, $Summary.fallbacks_pipeline_error) -ForegroundColor Green
if ($Rg) {
    $Rj = $Rg.correccion_ragas
    Write-Host ("RAGAS: correctness {0:P2} | {1}/{2} puntos | juez fallido {3}/{4} | modelo {5} | encoder {6}" -f `
        $Rj.correctness, $Rj.puntos, 30, $Rj.n_fallidos, $Rj.n_juzgados, $Rj.modelo_juez, $Rj.encoder) -ForegroundColor Green
    if ($Rj.n_fallidos -gt 0) { Warn "RAGAS dejó ítems sin veredicto: se cuentan como cero; revisar $Out\evaluation_ragas.json." }
} elseif ($Ragas) {
    Warn "Se pidió RAGAS pero no apareció evaluation_ragas.json; revisar el log del juez."
}
if ($Summary.proyeccion_992_horas -gt 5) { Warn "la proyeccion para 992 supera 5 h: la ventana del sabado es de 6 h." }
# Presupuesto del enunciado (B.5): ~22 s/pregunta para 992 en 6 h. Margen de seguridad: 20 s.
if ($Spq -gt 20) { Warn "$Spq s/pregunta supera el margen de 20 s (presupuesto 22 s): esta configuracion NO es apta para el sabado." }
$D = $Br.diagnostics
Write-Host ("Tiempos: generacion p50 {0} ms / p95 {1} ms | retrieval p50 {2} ms / p95 {3} ms | VRAM pico reservado {4} GB | reranker omitido {5}" -f `
    [math]::Round([double]$D.generation_ms_p50), [math]::Round([double]$D.generation_ms_p95), [math]::Round([double]$D.retrieval_ms_p50),
    [math]::Round([double]$D.retrieval_ms_p95), $D.peak_reserved_vram_gb, $D.rerank_skipped)
if ($D.peak_reserved_vram_gb -gt 22) { Warn "VRAM pico $($D.peak_reserved_vram_gb) GB (tarjeta 24 GB): riesgo de desborde a RAM del sistema y caida de velocidad." }
if ($D.rerank_skipped -gt 0) { Warn "$($D.rerank_skipped) preguntas usaron el orden previo al reranker (pasaje mas largo que max_length del reranker)." }
Write-Host "Archivos: $Out\RESUMEN.json, $Out\evaluation_official.json, $Run\batch_report.json$(if ($Rg) { ", $Out\evaluation_ragas.json" })$(if ($CitationDiagnostic) { ", $CitationDiagnosticPath" })"
