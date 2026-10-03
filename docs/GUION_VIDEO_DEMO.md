# Guion de video demo — KingsCode

Duración sugerida: 3–4 minutos. Grabar en la máquina con la RTX 4090 y el corpus de la corrida que se presenta. No mostrar ni usar el set ciego en el video.

## Qué estamos usando

KingsCode es un RAG jurídico de dos capas. La capa de conocimiento de A entrega pasajes del corpus con su norma, artículo y fuente. La configuración medida que se presenta usa recuperación BM25, recuperación por opciones para preguntas cerradas y un router que activa expansión del grafo jurídico cuando la pregunta y la evidencia inicial lo justifican. Devuelve hasta ocho pasajes. El perfil seleccionado es BM25: la ruta densa con embeddings y reranker existe, pero no forma parte de esta corrida seleccionada.

La capa B normaliza la consulta, arma el contexto con esos pasajes y usa Qwen3-8B abierto, local, en BF16, con temperatura 0 y decodificación greedy. El prompt v6 estructura la respuesta según el formato. El parser valida el JSON y la guarda de citas limita las referencias a las normas presentes en la evidencia recuperada; si hay un fallo de guarda, la pregunta puede abstenerse.

RAGAS es evaluación sobre las 50 preguntas conocidas, separada de la generación competitiva. El script pide la llave de OpenRouter de forma oculta y no la guarda. No se corre RAGAS sobre el set ciego de 992.

## Narración y pantalla

| Tiempo | En pantalla | Narración |
|---|---|---|
| 0:00–0:20 | Portada con nombre del equipo y KingsCode | “Construimos KingsCode, un asistente para preguntas de derecho colombiano. La respuesta se genera a partir de evidencia recuperada de fuentes jurídicas trazables.” |
| 0:20–0:55 | Diagrama sencillo: pregunta → BM25 y router de grafo → pasajes → Qwen3-8B → guarda → JSON | “El sistema tiene dos capas. A organiza el conocimiento y recupera artículos mediante BM25; el router usa el grafo solo cuando ayuda a resolver relaciones entre normas. B genera la respuesta con un modelo abierto de ocho mil millones de parámetros. Para la corrida mostrada usamos BM25 y ocho pasajes; el perfil denso con reranker no se seleccionó por su costo de tiempo.” |
| 0:55–1:20 | Abrir la interfaz y señalar la franja de configuración | “La interfaz muestra qué decoder, prompt, recuperación, cantidad de evidencia e identidad del índice están activos. Así podemos verificar la configuración antes de enviar una consulta.” |
| 1:20–2:20 | Escribir una pregunta jurídica independiente de la muestra y pulsar “Analizar pregunta”; abrir un pasaje citado y su enlace oficial | “La consulta pasa por la recuperación y el modelo recibe los pasajes como contexto. Aquí vemos la respuesta, los artículos que aparecen en la evidencia y los fragmentos recuperados con su fuente. La coincidencia de una norma confirma que aparece en los pasajes; por sí sola no certifica que el fragmento sostenga semánticamente toda afirmación.” |
| 2:20–2:50 | Abrir “JSON de la entrega (schema oficial)” | “La salida conserva el formato exigido por la entrega: respuesta, abstención y pasajes recuperados. La guarda impide emitir referencias legales ausentes de la evidencia.” |
| 2:50–3:25 | Mostrar reporte de evaluación y commit/snapshot, sin mostrar llaves | “En la medición documentada con v6, commit `bc480e7` y el snapshot de Turing, el evaluador oficial dio 38,08 de 50 sin RAGAS. Ese número pertenece a esa ejecución y a ese corpus. RAGAS se registra por separado y no se debe mezclar con otra corrida.” |
| 3:25–3:45 | Cierre con el equipo | “El siguiente paso es conservar juntos la configuración, el corpus, la entrega y sus evaluaciones para que otra máquina pueda comprobar el resultado.” |

## Iniciar la interfaz para grabar

Desde la raíz del repositorio, en la máquina con la GPU y el corpus ya construido:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ui.txt
.\.venv\Scripts\python.exe -m streamlit run interfaz\app.py
```

Confirma que la franja superior muestre `qwen3-8b`, `grounded-formats-v6`, BM25, `k=8` y el hash de `passages.jsonl`. Si la carga del decoder real falla, la interfaz se detendrá con un error visible; no grabar una pantalla en modo `DummyDecoder` como si fuera una respuesta del modelo.

## Afirmaciones que deben mantenerse precisas

- El repo no contiene evidencia reproducible que identifique un resultado de **37,02** ni un `evaluation_ragas.json` asociado a ese número. No presentarlo como resultado verificado.
- La corrida histórica documentada para `bc480e7` y v6 registra **38,08/50 sin RAGAS** sobre el snapshot de Turing. El resultado no prueba que cualquier copia local del corpus produzca lo mismo.
- El estado de corpus en `KINGSCODE_STATE.json` dice `frozen_for_competition: false`; el snapshot de recuperación de A no equivale a un freeze end-to-end de toda la arquitectura B.
- Si no se puede verificar la identidad del índice, mostrarla como no verificada. No afirmar que la interfaz reproduce el puntaje del evaluador.

## PowerShell: reproducir y guardar una corrida v6 con RAGAS

Ejecutar desde una copia limpia del repositorio en la PC que conserva el snapshot de Turing. Este bloque usa solo `sample_50.jsonl`; no ejecuta RAGAS sobre el set ciego. RAGAS consume créditos y el script solicitará la llave de OpenRouter oculta.

```powershell
$ErrorActionPreference = "Stop"
$Work = (Get-Location).Path
$Snapshot = Join-Path $HOME "kc_snapshot"
$RunName = "v6_turing_sample_ragas_20261003"
$CommitEsperado = "bc480e7"

# No cambiar de commit con modificaciones locales pendientes.
$Cambios = @(git status --porcelain)
if ($Cambios.Count -gt 0) { throw "Working tree no está limpio. Use una copia limpia para repetir la medición histórica." }
git switch --detach $CommitEsperado
if ((git rev-parse --short HEAD).Trim() -ne $CommitEsperado) { throw "No quedó activo el commit esperado $CommitEsperado." }

# Verifica el snapshot del corpus/índice que se usó en la corrida documentada.
if (-not (Test-Path $Snapshot)) { throw "No está el respaldo $Snapshot. Copie kc_snapshot desde la PC Turing antes de seguir." }
powershell -ExecutionPolicy Bypass -File .\tools\kingscode_snapshot.ps1 `
  -Accion verificar -Origen $Snapshot -Work $Work
if ($LASTEXITCODE -ne 0) { throw "El corpus/índice actual no coincide con kc_snapshot." }

# Corre las 50 preguntas, evaluación oficial y RAGAS. No agrega -Pull: conserva el commit.
powershell -ExecutionPolicy Bypass -File .\tools\kingscode_final.ps1 `
  -Work $Work `
  -Flags "-Recomendada -PromptVersion v6" `
  -InputFile "data\sample_50.jsonl" `
  -RunName $RunName `
  -Ragas
if ($LASTEXITCODE -ne 0) { throw "La corrida o una de sus evaluaciones terminó con error." }

# Comprueba que el resultado completo exista antes de empaquetarlo.
$Run = Join-Path $Work "reports\decoder_diagnostic\$RunName"
$Necesarios = @(
  (Join-Path $Run "batch\submissions.jsonl"),
  (Join-Path $Run "batch\batch_report.json"),
  (Join-Path $Run "evaluation_official.json"),
  (Join-Path $Run "evaluation_ragas.json"),
  (Join-Path $Run "RESUMEN.json"),
  (Join-Path $Run "DOCUMENTO_FINAL.md")
)
$Faltan = @($Necesarios | Where-Object { -not (Test-Path $_) })
if ($Faltan.Count -gt 0) { throw "No se empaqueta: faltan artefactos: $($Faltan -join ', ')" }

# Verifica el SHA-256 del tar del corpus guardado.
$LineasTar = @(Get-Content (Join-Path $Snapshot "SHA256SUMS.txt") | Where-Object { $_ -match '\s+kingscode_corpus_.*\.tar\.gz$' })
if ($LineasTar.Count -eq 0) { throw "SHA256SUMS.txt no registra un tar del corpus." }
foreach ($Linea in $LineasTar) {
  $Partes = $Linea -split '\s+'
  $TarPath = Join-Path $Snapshot $Partes[-1]
  if (-not (Test-Path $TarPath)) { throw "Falta el tar $TarPath" }
  if ((Get-FileHash $TarPath -Algorithm SHA256).Hash.ToLower() -ne $Partes[0].ToLower()) { throw "Hash incorrecto para $TarPath" }
}

# Paquete único con la corrida RAGAS, sus resúmenes y el snapshot del corpus.
$EntregaRoot = Join-Path $HOME "kc_entrega_ragas"
New-Item -ItemType Directory -Force $EntregaRoot | Out-Null
$Paquete = Join-Path $EntregaRoot $RunName
$Zip = "$Paquete.zip"
if ((Test-Path $Paquete) -or (Test-Path $Zip)) { throw "Ya existe $Paquete o $Zip; cambie RunName para no sobrescribirlo." }
New-Item -ItemType Directory -Path $Paquete | Out-Null
$RunCopy = Join-Path $Paquete "run"
New-Item -ItemType Directory -Path $RunCopy | Out-Null
Copy-Item -Path (Join-Path $Run "*") -Destination $RunCopy -Recurse
$CorpusCopy = Join-Path $Paquete "kc_snapshot"
New-Item -ItemType Directory -Path $CorpusCopy | Out-Null
Copy-Item -Path (Join-Path $Snapshot "*") -Destination $CorpusCopy -Recurse
$Metadata = [ordered]@{
  commit = (git rev-parse HEAD).Trim()
  run_name = $RunName
  input = "data/sample_50.jsonl"
  corpus_snapshot = $Snapshot
  submission_sha256 = (Get-FileHash (Join-Path $Run "batch\submissions.jsonl") -Algorithm SHA256).Hash.ToLower()
  official_evaluation_sha256 = (Get-FileHash (Join-Path $Run "evaluation_official.json") -Algorithm SHA256).Hash.ToLower()
  ragas_evaluation_sha256 = (Get-FileHash (Join-Path $Run "evaluation_ragas.json") -Algorithm SHA256).Hash.ToLower()
  created_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
}
$Metadata | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 (Join-Path $Paquete "SNAPSHOT_ENTREGA.json")
Compress-Archive -Path (Join-Path $Paquete "*") -DestinationPath $Zip -CompressionLevel Optimal
Get-FileHash $Zip -Algorithm SHA256 | Format-List Algorithm, Hash, Path
Write-Host "Entrega con RAGAS guardada en $Zip" -ForegroundColor Green
```

`tools/kingscode_snapshot.ps1` por sí solo solo respalda corpus e índice; el bloque de arriba añade la corrida, `submissions.jsonl`, evaluación oficial, RAGAS y el hash del paquete. Si ya existe una corrida RAGAS completa, conserva su `RunName` y ejecuta desde la sección “Comprueba que el resultado completo exista” para empaquetarla sin volver a consumir créditos.
