# =====================================================================
# KingsCode - pruebas rapidas de variantes sobre sample_50 (una variable por corrida)
#
# Corre cada variante con tools\kingscode_pc_nueva_diagnostico.ps1 (-SkipSmoke -SkipVerify para
# ahorrar ~2 min por variante), sigue aunque una falle y al final imprime una tabla contra la base.
# La verificacion en vivo se hace solo en la configuracion final (sin -SkipVerify).
#
# Uso (2026-10-02 noche: experimentos sobre la configuracion final 37,46/50):
#   PC #1:  powershell -ExecutionPolicy Bypass -File tools\kingscode_variantes.ps1 -Pc 1 -Pull   (v6 y despues doccap3)
#   PC #2:  powershell -ExecutionPolicy Bypass -File tools\kingscode_variantes.ps1 -Pc 2 -Pull   (option_plan)
#   Al final: tabla de esta tanda + proxy de RAGAS (ROUGE-1/BLEU-4/legibilidad, sin credito) + taxonomia.
#   powershell -ExecutionPolicy Bypass -File tools\kingscode_variantes.ps1
#   ... -Variantes prompt_v4,citas            (solo esas)
#   ... -Variantes final -Final "-PromptVersion v4 -CitationFill -Rerank -ExactLocator"
#
# Variantes (orden: mayor valor esperado y menor costo primero):
#   prompt_v4       -PromptVersion v4          (~13 min; sin costo extra de tiempo)
#   citas           -CitationFill              (~13 min; sin costo extra de tiempo)
#   rerank_locator  -Rerank -ExactLocator      (~15 min; el locator solo actua con reranker)
#   rerank          -Rerank                    (~15 min; separa el efecto del locator)
#   hybrid          -RetrieverMode hybrid      (indice denso la primera vez, ~5-10 min con el build ordenado por largo)
#   alia            -Model alia-legal-7b       (descarga ~15 GB la primera vez)
#   v6              -Recomendada -PromptVersion v6           (prompt de razonamiento juridico; ~15 min)
#   option_plan     -Recomendada -RetrievalMode option_plan  (planner Qwen para texto libre; ~20 min)
#   doccap3         -Recomendada -DocCap 3                   (max 3 pasajes por documento; ~15 min)
#   ctx16k          -Recomendada -MaxContext 16384           (EXPERIMENTAL: con prompts de ~12k tokens la atencion puede desbordar
#                   la VRAM y quedar casi congelada; NO esta en la tanda por defecto)
#   v6_ctx16k       -Recomendada -PromptVersion v6 -MaxContext 16384 (v6 necesita 16k: con 8k recorta pasajes en 30/50)
# =====================================================================
param(
    [string[]]$Variantes = @(),
    [ValidateSet("", "1", "2")] [string]$Pc = "",
    [double]$Base = 37.46,   # total sin RAGAS de -Recomendada con el corpus de ESTA maquina (39.02 con el corpus nuevo)
    [string]$Final = "",
    [string]$Work = "$HOME\KingsCodeGPU\KingsCodeNvidia",
    [switch]$Pull   # por defecto NO actualiza durante la tanda: todas las variantes usan el mismo commit
)
$ErrorActionPreference = "Continue"
# With powershell -File, "a,b,c" arrives as ONE string: split it here.
$Variantes = @($Variantes | ForEach-Object { $_ -split "," } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if (-not $Variantes) {
    $Variantes = switch ($Pc) { "1" { @("v6", "doccap3") } "2" { @("option_plan") } default { @("v6", "option_plan", "doccap3") } }
}
Set-Location $Work
if ($Pull) { git pull --ff-only origin main }
Write-Host "Commit congelado para toda la tanda: $((git rev-parse --short HEAD).Trim())" -ForegroundColor Cyan
$S = ".\tools\kingscode_pc_nueva_diagnostico.ps1"
$Catalogo = [ordered]@{
    "prompt_v4"      = @("-PromptVersion", "v4")
    "citas"          = @("-CitationFill")
    "menciones"      = @("-PromptVersion", "v4", "-CitationFill", "-CiteMentions", "3")
    "recomendada"    = @("-Recomendada")
    "rerank_locator" = @("-Rerank", "-ExactLocator")
    "rerank"         = @("-Rerank")
    "hybrid"         = @("-RetrieverMode", "hybrid")
    "alia"           = @("-Model", "alia-legal-7b")
    "v6"             = @("-Recomendada", "-PromptVersion", "v6")
    "v7_concise"     = @("-Recomendada", "-PromptVersion", "v7")
    "option_plan"    = @("-Recomendada", "-RetrievalMode", "option_plan")
    "doccap3"        = @("-Recomendada", "-DocCap", "3")
    "ctx16k"         = @("-Recomendada", "-MaxContext", "16384")
    "v6_ctx16k"      = @("-Recomendada", "-PromptVersion", "v6", "-MaxContext", "16384")
}
# Runs the diagnostic in a child PowerShell attached to THIS console (Start-Process -NoNewWindow):
# invoked as "powershell -File ..." from a script, PowerShell 5.1 redirects the child's streams and
# the [batch] progress lines (stderr) only appeared at the end (2026-10-02).
function Invoke-Diagnostico([string[]]$Flags) {
    $ArgList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$((Resolve-Path $S).Path)`"") + $Flags
    $p = Start-Process -FilePath "powershell.exe" -ArgumentList $ArgList -NoNewWindow -Wait -PassThru
    if ($p.ExitCode -ne 0) { Write-Host "La corrida termino con codigo $($p.ExitCode) (se sigue con la siguiente)." -ForegroundColor Yellow }
}
$Inicio = Get-Date
foreach ($v in $Variantes) {
    if ($v -eq "final") {
        if (-not $Final) { Write-Host "final requiere -Final '<flags>'" -ForegroundColor Yellow; continue }
        $a = @($Final -split "\s+" | Where-Object { $_ })
        Write-Host "`n################ CONFIGURACION FINAL (con verificacion en vivo): $Final ################" -ForegroundColor Magenta
        Invoke-Diagnostico (@("-SkipSmoke", "-NoPull") + $a)
        continue
    }
    if (-not $Catalogo.Contains($v)) { Write-Host "Variante desconocida: $v" -ForegroundColor Yellow; continue }
    $a = @($Catalogo[$v]) + @("-SkipSmoke", "-SkipVerify", "-NoPull")
    $t0 = Get-Date
    Write-Host "`n################ VARIANTE: $v ($($Catalogo[$v] -join ' ')) ################" -ForegroundColor Magenta
    Invoke-Diagnostico $a
    Write-Host ("Variante {0}: {1:N1} min" -f $v, ((Get-Date) - $t0).TotalMinutes) -ForegroundColor Cyan
}

# ---------------------------------------------------------------------
$Filas = Get-ChildItem ".\reports\decoder_diagnostic" -Directory | Where-Object { $_.LastWriteTime -ge $Inicio } | Sort-Object LastWriteTime | ForEach-Object {
    $f = "$($_.FullName)\RESUMEN.json"
    if (Test-Path $f) {
        $r = Get-Content $f -Raw | ConvertFrom-Json; $d = $r.diagnostics
        $tot = [double](($r.automatico_sin_ragas -split "/")[0].Trim())
        [pscustomobject]@{
            corrida = $_.Name; total = $tot; delta = [math]::Round($tot - $Base, 2)
            cerr = $r.cerradas; citas = $r.citas; abst = $r.abstencion; fb = $r.fallbacks_pipeline_error
            s_preg = $r.segundos_por_pregunta; ret_p95_ms = [math]::Round([double]$d.retrieval_ms_p95)
            vram_gb = $d.peak_reserved_vram_gb; verif = $r.verificacion_en_vivo.all_match
            apta = ($r.proyeccion_992_horas -le 5)
        }
    }
}
$Filas | Format-Table -AutoSize

# Per run: why each fallback happened (saved since PR #22) and how often the parser had to fix shape.
Write-Host "`nDetalle por corrida (fallbacks y correcciones del parser):" -ForegroundColor Cyan
Get-ChildItem ".\reports\decoder_diagnostic" -Directory | Where-Object { $_.LastWriteTime -ge $Inicio } | Sort-Object LastWriteTime | ForEach-Object {
    $run = $_
    if (-not (Test-Path "$($run.FullName)\RESUMEN.json")) { return }
    $r = Get-Content "$($run.FullName)\RESUMEN.json" -Raw | ConvertFrom-Json
    $why = Get-ChildItem "$($run.FullName)\batch\errors" -ErrorAction SilentlyContinue | ForEach-Object {
        $e = Get-Content $_.FullName -Raw | ConvertFrom-Json
        $reason = $e.attempts[0].detail.reason
        if (-not $reason) { $reason = $e.attempts[0].code }
        "{0}: {1}" -f $e.id, $reason
    }
    $co = $r.diagnostics.field_coercions
    $coText = $(if ($co) { ($co.PSObject.Properties | ForEach-Object { "$($_.Name)=$($_.Value.n)" }) -join ", " } else { "-" })
    $fw = $r.diagnostics.format_warnings
    $fwText = $(if ($fw) { ($fw.PSObject.Properties | ForEach-Object { "$($_.Name)=$($_.Value.n)" }) -join ", " } else { "-" })
    Write-Host ("  {0}`n    fallbacks: {1}`n    correcciones: {2}`n    avisos de extension: {3}" -f $run.Name, $(if ($why) { $why -join " | " } else { "ninguno" }), $coText, $fwText)
}
Write-Host "`nProxy de RAGAS (sin credito; token_f1 = ROUGE-1) y alineacion cita-afirmacion. Base: token_f1 0.275, bleu4 0.087, pct_mas_del_doble 0.229, tasa_alineadas 0.689, tasa_debiles 0.109:" -ForegroundColor Cyan
Get-ChildItem ".\reports\decoder_diagnostic" -Directory | Where-Object { $_.LastWriteTime -ge $Inicio -and (Test-Path "$($_.FullName)\batch\submissions.jsonl") } | Sort-Object LastWriteTime | ForEach-Object {
    Write-Host "  $($_.Name)"
    .\.venv\Scripts\python.exe tools\analyze_ragas_proxy.py "$($_.FullName)\batch\submissions.jsonl" --no-encoder
    .\.venv\Scripts\python.exe tools\analyze_citation_alignment.py "$($_.FullName)\batch\submissions.jsonl"
    .\.venv\Scripts\python.exe tools\analyze_taxonomy.py "$($_.FullName)\batch\submissions.jsonl" --md "$($_.FullName)\taxonomia.md" | Out-Null
}
Write-Host ("Total: {0:N0} min. Base: {1}/50. Se adopta solo si total > base, cerradas >= 12, 0 citas sin respaldo y apta (<= 5 h para 992). Taxonomia por corrida en <corrida>\taxonomia.md." -f ((Get-Date) - $Inicio).TotalMinutes, $Base) -ForegroundColor Green
$Filas | Export-Csv -NoTypeInformation -Encoding UTF8 ".\reports\decoder_diagnostic\comparacion.csv"
Write-Host "Tabla guardada en reports\decoder_diagnostic\comparacion.csv"
