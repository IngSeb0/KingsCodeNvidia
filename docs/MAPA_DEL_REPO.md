# Mapa del repositorio KingsCode — carpeta por carpeta

Estado descrito: `main` en `d9f1899` (29-sep-2026), con A y B integrados (PR #1–#5 mergeados).
Si algo aquí contradice `docs/KINGSCODE_STATE.json` o `docs/DECISION_LOG.md`, mandan esos dos.

---

## 1. Qué estamos construyendo, en un párrafo

Un sistema RAG que responde derecho colombiano con un modelo abierto de ≤ 8B parámetros. El sábado recibimos 992 preguntas (cerradas, semiabiertas y abiertas) y entregamos `submissions.jsonl`, que califica `scripts/evaluate.py` (oficial, 80 de 100 puntos). Los otros 20 son interfaz, bitácora del corpus, video y reproducibilidad. La ventaja no viene del modelo sino del **corpus propio** y de **recuperar bien** las normas: toda cita debe estar respaldada por un pasaje recuperado.

### Recorrido de una pregunta

```
pregunta (solo texto público: id, pregunta, formato, opciones)
  │  B  kingscode/reasoning/query.py        normaliza, detecta "Ley 1010 de 2006", "art. 90 del CGP"…
  │  B  planner.py (opcional, modo PLAN)    Qwen propone ≤3 consultas extra; la pregunta original siempre va
  ▼
  A  kingscode/retrieval.py  retrieve(pregunta, k, graph_mode, query_views)
        BM25 (+ denso Qwen + reranker en GPU) + locator exacto (solo sobre la pregunta original) + grafo
  ▼  8–10 pasajes con norma, artículo, URL oficial
  B  policy.py      ¿hay evidencia suficiente? (cerradas nunca se abstienen salvo evidencia vacía)
  B  decoder        Qwen3-8B / ALIA / Salamandra (GPU) — hoy DummyDecoder que se abstiene
  B  citation_repair.py → citation_builder.py → guards.py (citation_guard)
        corrige o suprime citas sin respaldo; la cita final sale de los metadatos del pasaje
  ▼
  fila JSON del esquema oficial → batch.py (992 con checkpoints) → submissions.jsonl → evaluate.py
```

**A (Luis)** es dueño de la capa de conocimiento: corpus, parser, grafo, índices, locator, benchmarks de recuperación.
**B (Esteban)** es dueño de consulta, planner, decoder, citas, abstención, ejecución de las 992, interfaz y entrega.
Se comunican solo por `retrieve(...)` → pasajes y `answer(...)` → fila.

---

## 2. Aclaración importante: ¿dónde está el corpus?

Hay **dos** carpetas de corpus y no son lo mismo:

| Carpeta | Qué es | Tamaño | ¿En git? |
|---|---|---|---|
| `corpus/` | **Corpus v0.1, el corpus principal.** 163 documentos oficiales, 26.558 pasajes, grafo de 59k nodos / 75k aristas, índice BM25 y (en la PC de la 4090) `dense.npy`. Es sobre el que se midieron todos los resultados de la 4090. | cientos de MB | **No** (está en `.gitignore`). Existe en la PC de Luis. Se transfiere empaquetado con `tools/package_corpus_snapshot.py` (ver §2.1); no re-adquirir. |
| `corpora/corpus-v0.2/` | **Agregado provisional de v0.2.** Solo 4 documentos nuevos con 72 pasajes (Decreto 046 de 2024; sentencias SL-648-2018, SP-1167-2022, SP-1680-2022) + 1 bloqueado (SP-1945-2019). Su manifest dice `status: provisional_not_competitive_freeze` y `v01_included: False`. | ~8,8 MB | **Sí** |

Conclusión: **`corpora/corpus-v0.2` no reemplaza a `corpus/`**; es lo que se sumará a v0.1 cuando A congele la v0.2. Responder las 992 solo con la v0.2 (72 pasajes) no sirve. Verificado el 29-sep: los 18 hashes de su manifest coinciden, el `Retriever` de A la carga (72 pasajes) y el pipeline de B corre sobre ella de punta a punta (50/50 filas, 0 errores del validador oficial; puntaje del dummy, no competitivo).

### 2.1 Cómo mover el corpus v0.1 entre PCs

El corpus v0.1 **no está en ninguna rama de GitHub** (tampoco en `feat/member-a-gpu-results-4090-20260928`: esa rama solo guarda sus rutas y hashes en `reports/gpu_freeze_4090/CRITICAL_ARTIFACT_HASHES.*`; su archivo más grande pesa 1,3 MB, mientras `passages.jsonl` pesa 84 MB y `bm25.json` 131 MB). Se mueve así:

1. En la PC que tiene `corpus/`: `python tools/package_corpus_snapshot.py pack` → `dist/corpus_snapshot/` con `kingscode-corpus-v0.1.tar.gz`, `snapshot-files.sha256.json`, `SHA256SUMS.txt` y `LEEME.txt` (fuera de git).
2. Subir esos archivos a Drive/OneDrive (también es el entregable 5, junto con `dense.npy` y un `LICENSE`).
3. En la PC que lo recibe: `python tools/package_corpus_snapshot.py verify <ruta>/kingscode-corpus-v0.1.tar.gz`, luego `tar -xzf … -C .` y `python tools/verify_member_a_v02.py`.

**Script único (PowerShell, sin admin):** en la PC que tiene `corpus\` y GPU, `powershell -ExecutionPolicy Bypass -File tools\kingscode_gpu_todo.ps1`. Trabaja en una copia limpia de `main` (`%USERPROFILE%\KingsCodeRun`, sin tocar el repo fuente), valida el corpus y el índice denso con las reglas de `DenseIndex`, publica corpus + índice + `LICENSE` como release `corpus-v0.1-snapshot`, instala CUDA en el venv, descarga el decoder, corre el smoke, congela planes, ejecuta `sample_50` con el evaluador oficial, proyecta el tiempo a 992 y sube los resultados a una rama `lab/<fecha>`.

El paquete no incluye `dense.npy` (106.741.888 bytes, SHA-256 `0c156c5e9…`): para los modos denso/híbrido hay que traerlo aparte o reconstruirlo en GPU con `tools/member_a.py dense`. Hash de un paquete ya generado reportado por el equipo: `fef7300ccfe731c0b4edb07e9199f7db830a38071f9549fd5b6f0f3120b2d851` (el hash del `.tar.gz` puede variar entre builds de zlib; la verificación autoritativa es por archivo).

### Dentro de `corpora/corpus-v0.2/`

| Ruta | Contenido |
|---|---|
| `manifest.json` | Identidad de la versión, 5 documentos (4 procesados, 1 bloqueado), 4 fuentes de auditoría, 18 hashes SHA-256, política del snapshot. |
| `raw/` | Bytes oficiales tal como se descargaron (HTML/PDF): los 4 documentos, el bloqueado y las fuentes de auditoría del parser (Ley 137 de 1994, C-355/2006, SU-214/2016). Nunca se editan. |
| `clean/` | Texto limpio extraído de cada documento procesado. |
| `passages.jsonl` | Los 72 pasajes estructurales (unidad: artículo o sección), con norma, artículo, jerarquía, URL e ids canónicos. |
| `graph/nodes.jsonl`, `graph/edges.jsonl` | Grafo jurídico: 33 nodos, 29 aristas, todas `CONTIENE` (estructurales). |
| `graph/review_queue.jsonl` | Relaciones semánticas (modifica, deroga, remite…) esperando revisión humana. **Hoy está vacía (0 filas).** |
| `index/bm25.json` | Índice léxico BM25 de esos 72 pasajes. No hay índice denso (`dense_built: false`). |

---

## 2.2 Ramas de Luis y la corrida en la RTX 4090

Todas las ramas de Luis tienen **0 commits fuera de `main`**: su trabajo ya está integrado. Qué fue cada una:

| Rama | Qué hizo |
|---|---|
| `feat/member-a-metadata-retrieval-v06` | Metadatos canónicos, deduplicación, taxonomía de fallos, experimentos R6–R8. |
| `feat/member-a-retrieval-benchmark-v1` | Benchmark interno v1 (200 casos) y su evaluador sin fuga de etiquetas. |
| `feat/member-a-gpu-benchmark-execution-v1` | *Harness* para correr el benchmark en GPU (commit WIP); quedó contenido en la rama siguiente. |
| `feat/member-a-gpu-results-4090-20260928` | **La primera ejecución CUDA en la 4090** y su freeze de evidencia (`reports/gpu_freeze_4090/`, `reports/benchmark/search_v2*`, `r1_qwen`, `r2_qwen`, `gpu_overnight/`). |
| `feat/member-a-corpus-quality-audit-v07` | Auditoría preregistrada de calidad del corpus (`reports/corpus_quality_v07/`). |
| `docs/state-reconciliation-20260928` | Reconciliación de documentos de estado. |
| `feat/member-a-corpus-v02-locator` | Corpus v0.2 provisional, locator productivo, benchmark independiente KC-COL-IR (JEP/Externado). |

**Qué salió de la 4090** (Search V2, benchmark interno v1, 39 variantes; métrica EC@8 = evidencia completa en los 8 primeros pasajes):

| Variante | Dev (120) | Validation (40) |
|---|---:|---:|
| BM25 profundidad 30 | 0,733 | 0,650 |
| BM25 profundidad 120 | 0,800 | 0,825 |
| Híbrido BM25 + denso Qwen, profundidad 120 | 0,833 | 0,800 |
| **Con locator exacto** (mejor: `HYB120_LOC_META_1p25`) | **0,992** | **1,000** |

Lectura: el salto viene del **locator exacto** (inyecta el artículo citado en la pregunta). El benchmark v1 tiene solo referencias explícitas, así que esto no prueba calidad en preguntas semánticas; por eso existe KC-COL-IR (hoy con 0 respuestas de referencia aceptadas). No hubo decoder: en la 4090 solo se corrió recuperación.

## 3. Raíz del repositorio

| Archivo | Para qué sirve |
|---|---|
| `README.md` | Portada: cómo empezar, interfaz, comando único, sección `## Corpus e índice` (enlace pendiente). |
| `START_HERE.md` | Orden de lectura para humanos y agentes; primer bloque = estado vigente. |
| `CORPUS.md`, `corpus_manifest.json` | Bitácora oficial del corpus v0.1 (entregable 4). |
| `README_KINGSCODE.md` | Resumen histórico del proyecto. |
| `run.sh`, `Dockerfile`, `.dockerignore` | Comando único de reproducción (entregable de reproducibilidad). `./run.sh --fixture` corre sin corpus. |
| `preflight.sh`, `preflight.ps1` | Chequeo inicial del material oficial, sin GPU. |
| `requirements-*.txt` | Dependencias por capa: `knowledge` (CPU/BM25), `neural` (Transformers), `gpu` (+accelerate), `quantization` (bitsandbytes, solo tras un OOM registrado), `ui` (Streamlit). |
| `gpu_execution_tests_first.txt` | Salida guardada de una corrida de tests de A en la PC GPU (evidencia histórica). |

---

## 4. Material oficial (no se modifica nunca; hashes en `docs/OFFICIAL_SHA256.txt`)

| Carpeta | Contenido |
|---|---|
| `data/` | `sample_50.jsonl` (50 preguntas de muestra **con respuestas**: solo el evaluador y herramientas de medición pueden leer sus etiquetas) y `seed_targets.json` (fuentes normativas sugeridas). |
| `schema/` | `submission.schema.json`: contrato de cada fila de la entrega. |
| `scripts/` | Evaluador oficial: `evaluate.py`, `citations.py` (extractor de citas que usa el jurado), `common.py`, requisitos del juez RAGAS. |
| `entregables/` | Instrucciones y plantillas: `viernes/` (reporte de avance) y `sabado/` (README del equipo, CORPUS.md, informe técnico, manifest de ejemplo). |
| `Ejemplo de entrega/` | Entrega de referencia con 5 preguntas. |

---

## 5. Código — `kingscode/`

### Capa A (Luis): conocimiento y recuperación

| Módulo | Función |
|---|---|
| `acquisition.py` | Descarga solo documentos oficiales, conserva bytes y evidencia HTTP. |
| `acquisition_backlog.py` | Clasifica objetivos de adquisición sin resolver. |
| `corpus.py` | Extrae texto oficial, pasajes estructurales y grafo en una sola pasada (parser `legal-blocks`). |
| `corpus_v02.py` | Reparaciones de fuente aisladas por versión para la v0.2. |
| `metadata.py` | Identidad jurídica canónica (`canonical_document_id`, `canonical_fragment_id`) y metadatos v0.6. |
| `retrieval.py` | `Retriever` y `retrieve()`: BM25/denso/híbrido, grafo acotado, `query_views` (multi-consulta), locator exacto opcional. |
| `legal_locator.py` | Locator exacto: resuelve "artículo 90 del CGP" y lo inyecta en los candidatos (solo sobre la pregunta original). |
| `neural.py` | Adaptadores Qwen3 abiertos (embeddings y reranker) con revisiones fijas. |
| `diversify.py` | Deduplicación, diversificación y rasgos de metadatos para retrieval. |
| `metadata_experiments.py` | Experimentos R6/R7/R8. |
| `benchmark_builder.py`, `retrieval_benchmark.py`, `benchmark_analysis.py`, `benchmark_runtime.py`, `benchmark_v2.py`, `retrieval_diagnostics.py`, `failure_analysis.py`, `coverage_report.py` | Benchmarks internos de recuperación, bootstrap pareado, taxonomía de fallos, cobertura. |
| `evaluation.py` | Benchmark offline de desarrollo; **única capa de A que puede leer etiquetas**. |
| `validation.py` | Validación de artefactos, procedencia, grafo e integridad oficial. |
| `gpu_environment.py`, `model_assets.py` | Diagnóstico de GPU (sin instalar nada) y snapshots de modelos verificados por hash. |
| `common.py` | Utilidades de IO y texto compartidas. |

### Capa B (Esteban): razonamiento — `kingscode/reasoning/`

| Módulo | Función |
|---|---|
| `contracts.py` | `Question` pública: solo id, pregunta, formato, opciones. Las etiquetas nunca cruzan esta frontera. |
| `query.py` | Normaliza la pregunta sin destruir referencias jurídicas. |
| `legal.py` | Reconocedor propio de referencias (más estricto que el oficial). |
| `planner.py`, `plan_store.py` | Planner Qwen (Q0 + máx. 3 vistas), esquema estricto, congelado y replay de planes. |
| `routing.py`, `policy.py` | Cuándo usar el grafo; cuándo abstenerse (cerradas nunca, salvo sin evidencia). |
| `decoder.py` | Contrato `Decoder`, `DummyDecoder`, fila de abstención. |
| `pipeline.py` | `Pipeline.run`: modos BASE / OPTION / PLAN, fusión RRF, diagnósticos por pregunta, red de seguridad de citas. |
| `citation_repair.py`, `citation_builder.py`, `guards.py`, `official.py` | Reparación de citas antes de la guarda, cita final desde metadatos, guarda final y acceso de solo lectura al extractor oficial. |
| `batch.py` | Ejecución robusta de las 992: checkpoints atómicos, resume, reintentos, respaldo por ítem, chequeo 992/992, verificación en vivo. |
| `presentation.py` | Vista para el jurado (evidencia exacta, citado vs recuperado) separada de la traza técnica. |
| `experiments.py`, `evaluation.py` | Registro histórico de Gate 1B y puente al evaluador oficial. |

### Capa B: generación — `kingscode/generation/`

| Módulo | Función |
|---|---|
| `hf_decoder.py` | Decoder real con Transformers (lazy, BF16, snapshots bloqueados). |
| `prompts.py` | Prompts por formato (`grounded-formats-v3` con `pasajes_usados`), parser estricto y normalizador de sobre JSON. |
| `config.py` | Carga y valida `config/decoder_bakeoff.json`. |
| `planner_backend.py` | Backend Qwen del planner. |
| `experiments.py`, `retrieval_experiments.py`, `bakeoff.py`, `gpu_smoke.py` | Corridas de decoder sobre evidencia congelada, freeze de retrieval, contrato del bakeoff, smoke de GPU. |

---

## 6. `tools/` — comandos

| Grupo | Scripts |
|---|---|
| A: corpus | `member_a.py` (acquire/build/reproduce/dense/query), `acquire_corpus_v02.py`, `plan_corpus_v02.py`, `audit_corpus_quality_v07.py`, `document_member_a.py` |
| A: benchmarks | `build_retrieval_benchmark.py`, `evaluate_retrieval_benchmark.py`, `analyze_retrieval_benchmark.py`, `benchmark_v2.py`, `benchmark_source_intake.py`, `independent_ir_v2.py` (KC-COL-IR, con gate), `audit_kc_col_ir_tokens.py` (token audit CPU/local-only), `retrieval_matrix.py`, `gpu_search_v2_dev.py`, `gpu_search_v2_validation.py` |
| A: verificación | `verify_member_a_v02.py`, `verify_member_a_second.py`, `verify_kc_col_ir_v01.py` |
| B | `member_b.py` (smoke, decoder-smoke, sample, bakeoff, **batch**, **verify**, **plan**), `analyze_query_plans.py`, `analyze_citation_ceiling.py`, `verify_member_b_second.py` |
| GPU / entorno | `kingscode_gpu_todo.ps1` (script único de la PC con GPU), `build_combined_corpus.py` (corpus_v01_v02/: v0.1 + v0.2 por concatenación, BM25 reconstruido, diagnóstico; admite rutas relativas desde la raíz del repo), `kingscode_pc_nueva_diagnostico.ps1` (PC con GPU: verifica el corpus, construye el combinado, puede indexar dense y probar BM25/dense/hybrid + reranker con Qwen3-8B en sample_50; corpus local conocido divergente solo con `-AllowKnownLocalCorpusDrift`, siempre diagnóstico y no freeze; RAGAS solo con `-Ragas`), `run_b_gpu_4090.ps1` (B en la 4090 con el `.venv` existente: `-Phase prep` hoy; `-Phase decoder` solo con el freeze de A), `check_cuda.py`, `prepare_gpu_environment.py`, `prepare_models.py`, `prepare_neural.py`, `neural_smoke.py`, `gpu_smoke.py`, `verify_gate2_prep.py`, `benchmark_budget.py` |
| Material oficial | `preflight.py`, `inspect_challenge.py` |

---

## 7. `config/`

| Archivo | Qué fija |
|---|---|
| `models.lock.json` | Revisión inmutable de cada modelo (Qwen embedding/reranker, Qwen3-8B, ALIA, Salamandra, Llama). |
| `decoder_bakeoff.json` | Candidatos de decoder, BF16, tokens máximos, prompt v3, `max_used_passages`. |
| `neural.json` | Encoder/reranker Qwen, `cuda:0`, bfloat16. |
| `reasoning.json` | Configuración histórica de Gate 1B (dummy + BM25). |
| `strategy.json`, `experiment_matrix.json` | Estrategia vigente y matriz de experimentos. |
| `sources.json`, `corpus_v02_sources.json` | Fuentes oficiales de v0.1 y del lote v0.2. |
| `corpus_passage.schema.json`, `legal_graph.schema.json` | Esquemas de pasajes y grafo. |
| `evaluation_gpu.json` | Parámetros de evaluación en GPU. |

---

## 8. `benchmarks/` — cómo medimos la recuperación

| Carpeta | Qué es |
|---|---|
| `kingscode_ir/` | **Benchmark interno v1** (200 casos: 120 dev, 40 validation, 40 holdout), derivado del corpus con plantillas; 100 % referencias explícitas. Validation v1 **cerrada** para tuning. |
| `kingscode_ir_v2/` | Piloto técnico v2; su manifest dice `not_selectable`. |
| `kc_col_ir_v0.1/` | **Benchmark independiente KC-COL-IR** con preguntas de otras instituciones (JEP, Externado). Gate: ≥ 10 respuestas de referencia aceptadas; hoy **0 aceptadas** (candidatos en revisión humana). Los textos de las preguntas viven en `tmp/` de la PC de Luis, verificados por hash. Aquí correrá el experimento BASE vs PLAN. |

Regla común: los rankings se escriben **antes** de leer el gold; el holdout no se toca.

---

## 9. `reports/` — evidencia de lo que ya se corrió

| Ruta | Contenido |
|---|---|
| `gpu_freeze_4090/` | Resultados de la RTX 4090: Search V2 (dev EC@8 0,9917; validation 1,0 con locator), hashes de artefactos, `nvidia-smi`, `pip freeze`. |
| `benchmark/` | Corridas R0–R8, Search V2, estadística, selección (`selection/`), `freeze_handoff/`. |
| `member_a_v02/`, `corpus_quality_v07/` | Progreso de v0.2 y auditoría de calidad del corpus. |
| `member_b/` | Corridas de Gate 1B (dummy). |
| `retrieval_*`, `acquisition_backlog_v06.json`, `corpus_coverage_v06.json` | Métricas BM25 de v0.1, fallos por pregunta, backlog de adquisición, cobertura. |
| `lab_session/<fecha>/` | (se crea en la sesión GPU) salida de `tools/kingscode_gpu_todo.ps1`. |
| `query_plans/<id>/` | (se crea al congelar planes) planes del planner con su manifest. |

---

## 10. `docs/` — lo que hay que leer

| Documento | Para qué |
|---|---|
| `KINGSCODE_STATE.json` | Estado de máquina del proyecto (incluye `member_b_v2`). |
| `DECISION_LOG.md` | Todas las decisiones, en orden, con motivo. |
| `experiments/B_BASE_VS_PLAN_v1.json` | Experimento BASE vs PLAN predeclarado (no ejecutado). |
| `TEAM_SPLIT.md`, `INTEGRATION_CONTRACTS.md` | Quién hace qué y el contrato A↔B. |
| `GPU_DAY_RUNBOOK.md`, `MODEL_LOCKS_GATE2.md` | Día de GPU y licencias/revisiones de modelos. |
| `MEMBER_A_RUNBOOK.md`, `MEMBER_B_RUNBOOK.md` | Cómo operar cada capa. |
| `BENCHMARK_METHODOLOGY.md`, `BENCHMARK_V2_METHODOLOGY.md` | Reglas de medición. |
| Resto (`ARCHITECTURE_*`, `ROADMAP`, `LITERATURE_REVIEW…`) | Historial de diseño. |

---

## 11. Resto de carpetas

| Carpeta | Qué es |
|---|---|
| `tests/` | Suite CPU (265 tests). `fixtures/` tiene pasajes oficiales reales para probar sin corpus. Correr: `python -m unittest discover -s tests -v`. |
| `interfaz/` | `app.py` (Streamlit, identidad Software Colombia). `streamlit run interfaz/app.py`; requiere `corpus/`. |
| `artifacts/` | Salidas del preflight y verificaciones iniciales. |
| `corpus/`, `models/`, `tmp/`, `runs/`, `.venv/` | **Locales, fuera de git.** Corpus v0.1, pesos de modelos, artefactos temporales (pools de benchmarks de A), corridas del batch, entorno Python. |

---

## 12. Qué falta para el sábado (según `entregables/sabado/README.md`)

| Entregable | Estado |
|---|---|
| 2. README con dependencias, arquitectura y comando único | Hay README y `run.sh`; falta completar arquitectura final y el enlace del corpus. |
| 3. `submissions.jsonl` de 992 | Pendiente: requiere decoder real (GPU) y el freeze de retrieval de A. `tools/member_b.py batch` está listo. |
| 4. `CORPUS.md` y `corpus_manifest.json` | Existen para v0.1; actualizar si se adopta v0.2. |
| 5. Corpus e índice en la nube con `LICENSE` | Pendiente: `tools/package_corpus_snapshot.py pack` en la PC de Luis, subir el paquete + `dense.npy` + `LICENSE` y declarar el enlace. |
| 6. Informe técnico (≤ 3 páginas) | Pendiente. Plantilla en `entregables/sabado/INFORME_TECNICO.md`. |
| 7. Video (≤ 5 min) | Pendiente. |
| 8. Interfaz | Implementada; falta probarla con el corpus real y un decoder real. |
| `LICENSE` en la raíz | Falta. |
