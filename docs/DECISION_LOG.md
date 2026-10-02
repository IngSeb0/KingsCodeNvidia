# KingsCode Decision Log

## 2026-09-27 — v0.1
- Validar starter pack antes de GPU.
- No instalar CUDA/PyTorch a ciegas.

## 2026-09-27 — v0.2
- Equipo de 2 dividido por subsistemas.
- Baseline retrieval: BM25 + Qwen3-Embedding-0.6B + Qwen3-Reranker-0.6B.
- Qwen3-8B como decoder prior inicial.
- Decoder fine-tuning pospuesto; reranker hard-negative FT como primer candidato.
- RTX 4090 24 GB como hardware objetivo; probar BF16 antes de cuantización.

## 2026-09-27 — v0.3 (literatura)
- Retrieval pasa a ser explícitamente la prioridad #1 por evidencia de Legal RAG Bench 2026 y otros benchmarks legales.
- Se añade RRF como fusión baseline.
- Chunking pasa de “por artículo” simple a “structure-aware/adaptive”, preservando jerarquía legal.
- Se añade expansión terminológica controlada para español jurídico, no multi-query libre por defecto.
- Se añade `citation_guard` post-generation como componente obligatorio.
- Se añade ALIA-es-legal-administrative-7B-Instruct al bakeoff de decoders.
- GraphRAG queda como experimento opcional, no baseline.
- Se formaliza gate de fine-tuning: no decoder FT hasta tener retrieval alto.
- Siguiente acción congelada: Corpus v0 + benchmark BM25/retrieval antes de CUDA.

## 2026-09-27 — v0.4 (Graph-aware desde Corpus v0)
- Se corrige la decisión anterior de dejar GraphRAG solo para después del baseline.
- El corpus nace con jerarquía y grafo jurídico desde la ingesta.
- No se adopta GraphRAG pesado para todas las consultas: BM25+dense+RRF sigue siendo el fast path.
- El grafo se usa selectivamente para relaciones jerárquicas/normativas (`REMITE_A`, `MODIFICA`, `DEROGA`, `REGLAMENTA`, etc.).
- Se confirma al iniciar Integrante A que el ZIP oficial **no contiene los textos jurídicos completos**; contiene `seed_targets.json` con 186 objetivos y ubicaciones de búsqueda.
- Se crean schema canónico de pasajes/grafo y plan operativo del Integrante A.

## 2026-09-27 — v0.5 (Agent-ready + roles A/B revisados)
- Se corrige la división antigua: B ya no es solo inferencia/evaluación; ahora posee Query/Reasoning Layer, `graph_router`, generación, guards, evaluación y delivery.
- A pasa a ser explícitamente Knowledge Layer: corpus + provenance + graph + retrieval + reranking + métricas.
- Se crea `AGENTS.md` como protocolo operativo para cualquier agente/humano que continúe el proyecto.
- Se formalizan contratos `retrieve(..., graph_mode)` y `answer(...)`.
- Se crea `MEMBER_B_REASONING_EVAL_PLAN.md`, `INTEGRATION_CONTRACTS.md` y `ARCHITECTURE_V05.md`.
- Roadmap pasa a trabajo paralelo: A construye Corpus v0/BM25 mientras B construye harness pre-GPU/router/citation guard/evaluator.
- CUDA deja de ser un gate que bloquee a ambos; se aborda cuando el harness de B esté listo y haya máquina real.

## 2026-09-27 — Implementación de A / Corpus v0.1

- Se materializa el corpus desde fuentes oficiales: Función Pública, Corte Constitucional, SENA, Comunidad Andina y Corte Suprema. El inventario conserva 28 objetivos sin resolver, en vez de reemplazar años/números por coincidencias aproximadas. HTTPS valida certificados; raw y metadatos quedan disponibles para reconstrucción offline.
- Parser `legal-blocks-1.2`: artículos, numeración compuesta, reformas citadas, jerarquía, parágrafos y numerales; decisiones por estructura explícita. Se preservan páginas PDF y offsets exactos del clean. La portada CAN 486 sin texto utilizable se omite del clean; raw permanece completo.
- La revisión adicional detectó anexos/versiones con el mismo número de artículo. Se excluye de recuperación el grupo ambiguo completo, conservándolo para auditoría. No se decide automáticamente la versión vigente. Este cambio reduce el riesgo de atribuir un anexo al artículo de la norma principal.
- BM25 es el backend activo local pre-GPU. Dense Qwen3, RRF y reranker Qwen3 están implementados con commits fijos y prueba real; no se afirma benchmark neuronal completo. La máquina examinada tiene PyTorch 2.12.0+cpu, CUDA no disponible; 4090 sigue siendo objetivo externo.
- Grafo acotado: un salto, cinco semillas, dos pasajes por vecino, diez expansiones. Se emiten solo CONTIENE, CITA, REMITE_A y patrones explícitos MODIFICA/DEROGA; los demás tipos/tags quedan reservados a evidencia futura. AUTO es una política provisional inyectable por B. Su ausencia de disparos en el sample impide inferir que AUTO mejora OFF; ON se mide como ablation.
- Métricas: identidad canónica de fuente/artículo, no coincidencia de citas mencionadas en fuentes ajenas. `legal_basis` original se audita por separado y nunca llega al índice. MRR se trunca en 10 y nDCG cuenta objetivos distintos; no se afirma score oficial de QA.
- No se cambia decoder ni se inicia fine-tuning: la recuperación baseline aún requiere mejora. El siguiente paso compartido es integrar B y ejecutar comparaciones neuronales en la 4090 bajo el mismo snapshot.

## 2026-09-27 — Gate 1B / integración pre-GPU

- Se añade `kingscode/reasoning` sobre la API pública de A. La integración hace una recuperación OFF, decide con pregunta+evidencia y solicita expansión si corresponde. El adaptador devuelve bool porque A no recibe el contexto plano ni interpreta strings OFF/AUTO/ON en su callback. No se cambian internals de A.
- El límite de entrada del sistema proyecta exclusivamente ID, pregunta, formato y opciones. Las etiquetas solo se leen en el proceso del evaluador oficial; alterar etiquetas no modifica entradas públicas, fingerprint ni resultados del sistema.
- El backend dummy siempre se abstiene. Se verifica el pipeline completo sin producir supuestas respuestas jurídicas de prueba. La CLI bloquea backends reales, retrieval neuronal y RAGAS en este gate; temperatura prevista 0 y muestreo deshabilitado.
- Contradicción del schema oficial: la descripción de `respuesta_correcta` dice «Con abstencion true se admite null», pero su enum solo admite A/B/C/D. Sin modificar el archivo, el dummy usa A como marcador formal, declara que no representa una elección y mantiene abstención true. No se elige la letra según el banco.
- Citation guard más conservador que la puntuación documental del evaluador: comprueba número, año, artículo, identidad primaria de fuente y presencia literal en la evidencia emitida. No usa alias por número ignorando año ni atribuye artículos de un código a todas las leyes mencionadas en su título. No certifica implicación semántica de conclusiones.
- JSON/schema/citas inválidos abortan la corrida y se registran; no hay reparación manual ni publicación de un JSONL final parcial. Evidencia histórica/ambigua, conflictos fuertes o referencias insuficientes disparan abstención.
- Cada corrida conserva directorio nuevo, configuración/hashes/fingerprint, trazas, tiempos y evaluación oficial sin RAGAS. El JSONL y las decisiones son deterministas; las rutas/timestamps/latencias no se comparan como contenido reproducible. Cero citas del dummy no constituye evidencia de calidad de citación.

## 2026-09-28 — Gate 2-Prep, ejecución diferida por el usuario

- Se fija la revisión real de Qwen3-8B, ALIA Legal, Salamandra y Llama opcional desde el Hub oficial; las entradas originales del encoder/reranker permanecen iguales. Salamandra/Llama requieren acceso manual y no se presume autorización. Los conteos reales de los modelos nominales 8B requieren aclarar elegibilidad antes de entrega competitiva.
- La generación real se prepara en `kingscode/generation/` para conservar los módulos, salida y fingerprint del dummy. El backend implementa el protocolo existente, es lazy, usa snapshots locales con hashes, prohíbe remote code y conserva las guardas. No se descargaron decoders.
- Prompts lógicos `grounded-formats-v2`, template nativo de cada tokenizer, Qwen sin thinking; parámetros greedy explícitos comunes. Formato/JSON/citas/contexto inválidos abortan el experimento, sin truncar ni editar la respuesta. El router sigue basado en reglas, sin prompt/modelo generativo.
- Se separa la medición de retrieval de la comparación de decoders: rankings públicos medidos → freeze de ocho evidencias por pregunta → mismos datos para D1–D4. Se evita mantener retrieval y decoder juntos en VRAM. Los tiempos de generación no se presentan como latencia end-to-end en vivo.
- BF16 primero, contexto total 8192 y batch 1 preparados; fit/latencia no verificados. INT8/4-bit requieren registro de OOM BF16 de la misma configuración y evidencia, y nunca se activan automáticamente. El plan de entorno no escoge una build CUDA sin diagnóstico ni instala paquetes.
- La última instrucción del usuario reemplazó la ejecución de verificaciones por preparación sin pruebas. Se añaden 28 tests y dos comandos de verificación, **no ejecutados**. No se declara Gate 2A/2B ni bakeoff completado; los resultados previos A/1B se conservan como históricos.

## 2026-09-28 — v0.6 (Member A knowledge layer: metadata + retrieval)

- Se agrega una capa de derivación determinista (`kingscode/metadata.py`) con identidad canónica independiente de la URL: `canonical_document_id` (p. ej. `ley:1564:2012`, `decreto:410:1971`, `codigo_civil`, `constitucion:1991`, `corte_constitucional:c355:2006`, `corte_suprema:sl3385:2022`) y `canonical_fragment_id` en un espacio de nombres separado (p. ej. `ley:1564:2012:articulo:391`). Las variantes históricas o los encabezados de artículo repetidos se mantienen distintos. No cambia `corpus.py` ni el build; el corpus se reconstruye byte a byte idéntico (mismos hashes que v0.1).
- Metadatos v0.6 aditivos y opcionales: `content_hash` (solo cuerpo semántico, excluye `text_prefix`), `status_assertion`/`status_source_passage_id`/`effective_from`/`effective_to`/`version_date`. La validez legal nunca se infiere: por defecto `unknown`/`null` salvo evidencia explícita de la fuente. No se introduce ningún puntaje de autoridad arbitrario. La procedencia técnica (hash, HTTP, ruta, timestamp) se mantiene fuera del texto de embedding.
- Se separan explícitamente tres planos: metadatos de documento, metadatos de pasaje y **scores de recuperación en tiempo de ejecución** (`bm25_score`, `dense_score`, `rrf_score`, `reranker_score`, `graph_score`, `final_score`), que no se persisten como metadatos del corpus.
- Fase 1: se clasifican los 28 objetivos de adquisición no resueltos (`kingscode/acquisition_backlog.py`) en `resolved`/`not_found`/`ambiguous`/`source_unavailable`/`identifier_suspect`, conservando procedencia y notas. Nunca se sustituye una norma/año/número/decisión similar ni se corrige un identificador dudoso; los sospechosos se marcan para revisión humana. Resultado: 14 `source_unavailable` (Corte Suprema sin resolver verificado), 11 `not_found`, 2 `identifier_suspect`, 1 `ambiguous`.
- Fase 4: deduplicación y diversificación (`kingscode/diversify.py`) agrupables por `canonical_document_id`/`canonical_fragment_id`/`content_hash`. La diversificación es configurable, apta para ablación y **no** se activa por defecto; la procedencia de espejos duplicados se conserva, no se descarta.
- Fase 5: taxonomía de fallos de recuperación (`kingscode/failure_analysis.py`): `corpus_missing`, `correct_document_wrong_passage`, `wrong_document`, `ranking_failure`, `graph_failure`, `ambiguous_ground_truth`, más `success`. No se fuerza una clasificación cuando `legal_basis` es incompleto o contradictorio. Se añade `document_mismatch_rate` (definición propia; no se afirma equivalencia con una métrica académica DRM).
- Fase 6: experimentos R6/R7/R8 opcionales (`kingscode/metadata_experiments.py`) sobre la API pública `retrieve(...)`, sin tocar R0–R5 de B ni cambiar la ruta por defecto. Para referencias explícitas se usa localizador estructurado exacto + recuperación general → unión de candidatos → ranking; los rasgos de metadatos son priores suaves, nunca filtros duros. Registrados en `config/experiment_matrix.json`.
- Fase 7: representación de embedding experimental (`metadata.embedding_representation`) con encabezado Norma/Ley/Artículo/Título; excluye sha256, ruta, HTTP, bytes y `retrieved_at`. Es un experimento, no un reemplazo medido de la representación actual.
- Fase 8: se confirma que toda relación normativa del grafo conserva `source`, `target`, `relation`, `evidence_passage_id` y procedencia (`method`); 0 aristas sin evidencia. Estados temporales `current/historical/repealed/modified/unknown` solo con evidencia; por defecto `unknown`.
- Fase 9: reporte de cobertura v0.6 (`reports/corpus_coverage_v06.json`) que no usa el conteo de documentos como proxy de calidad.
- Verificación: 132 tests (16 A históricos + 44 nuevos v0.6 + 44 B + 28 GPU) en verde; dos verificaciones independientes con reconstrucción byte a byte y recomputación de métricas. Archivos oficiales (19) intactos; implementación de B intacta; sin GPU/bakeoff/RAGAS/fine-tuning; sin indexar `expected_answer`/`legal_basis`.
- La hipótesis de que el corpus deba responder casi cualquier pregunta del dominio se trata solo como hipótesis de diseño, no como requisito oficial del reto.

## 2026-09-28 — Internal retrieval benchmark v1 (Member A)

- Se crea un benchmark interno de recuperación separado del sample oficial: 200 casos deterministas derivados de metadata/pasajes oficiales (120 dev, 40 validation, 40 holdout; 20 por área). Preguntas y gold se guardan en archivos separados; `retrieve` recibe exclusivamente el texto de pregunta y los gold se cargan solo después de capturar rankings. No se usó un modelo cerrado ni se fabricaron preguntas semánticas: 20 paquetes de autoría quedan para revisión humana.
- Se definen métricas de evidencia a k=1/3/5/8/10, MRR/MAP/nDCG, recuperación documental, mismatch documental (definición propia), completitud de evidencia, spans, costo de contexto, subgrupos y bootstrap pareado determinista (seed 0, 10.000 muestras). Holdout tiene declaración preautorizada únicamente para R0 baseline; selección posterior exige registro de validation y cada variante se consume una vez.
- R0 BM25 se ejecuta sobre los tres splits. En validation: Evidence Completeness@8=0.575, Recall@10=0.625, MRR@10=0.3739, nDCG@10=0.4331, Document Mismatch=0.10. El holdout R0 es baseline predeclarado, no tuning ni confirmación de selección.
- R0 graph AUTO/ON y R6/R7/R8 con backend BM25 se registran solo como diagnósticos: no cumplen la definición R3-based y no pueden seleccionar arquitectura. AUTO no cambia Recall/Completeness; ON no mejora Recall/Completeness. El diagnóstico R6-BM25 mejora dev, pero requiere repetición correcta sobre R3 antes de cualquier conclusión. R8-BM25 degrada las métricas del diagnóstico.
- No existe reporte/configuración/index BGE-M3 reproducible en el repo; los valores proporcionados por el usuario se conservan como `user-reported`, no evidencia reproducida. Qwen dense, BGE, híbridos, reranker y R3–R8 reales quedan `GPU_BLOCKED` con prerequisitos exactos. Por tanto no se selecciona arquitectura ni se congela evidencia para B; tampoco se ejecuta confirmación oficial-50 posterior a selección.
- Se preservan resultados negativos/bloqueados y se prohíbe usar el sample oficial para desarrollo del benchmark interno. La siguiente decisión depende de comparaciones same-ID en la 4090, no de preferencia previa.
## 2026-09-28 — Corrección del abort-on-citation en `Pipeline.run`, consolidación de contexto de B

- **Hallazgo (Esteban, verificado contra el código real, no contra documentación):** con un decoder real conectado (`HFDecoder`, ya preparado en Gate 2-Prep), la primera cita sin respaldo generada por el modelo hace que `citation_guard` levante `CitationGuardError`. Esa excepción se propaga sin capturar a través de `Pipeline.run` hasta el bucle `for question in questions` de `run_experiment`, que la deja subir sin publicar `submissions.jsonl` para NINGUNA de las 992 preguntas (política registrada el 2026-09-27: "JSON/schema/citas inválidos abortan la corrida... no hay publicación de un JSONL final parcial"). El sábado, con un decoder real generando texto libre, esto es virtualmente seguro que ocurra al menos una vez en 992 ítems y dejaría al equipo sin entrega.
- **Corrección de arquitectura (requiere revisión cruzada de Luis, integrante A, antes del día de GPU):** se modifica únicamente `Pipeline.run` (`kingscode/reasoning/pipeline.py`) para capturar `CitationGuardError` y, solo ahí, sustituir la fila rechazada por una abstención construida con `abstention_row` sobre la misma evidencia — exactamente el mecanismo que el anexo B.5 del enunciado pide ("verificar que toda norma citada aparece en la evidencia y, si no, suprimir la citación"). **No se toca** `citation_guard`, `_answer` ni la función pública `answer()`: siguen lanzando `CitationGuardError` exactamente igual que antes para cualquier llamador directo, por lo que las pruebas de integridad de evidencia (`test_decoder_cannot_mutate_evidence_to_create_support`, todas las de `GuardSchemaTests`) no cambian. Tampoco se toca el comportamiento ante `SubmissionValidationError` (JSON/schema inválido sigue abortando la corrida sin publicar; ver `test_failed_run_is_registered_without_final_submission`), porque esa es una señal de bug del decoder, no de una cita jurídica cuestionable, y el equipo no ha revisado si debe tratarse igual.
- Se añade `test_unsupported_citation_falls_back_to_abstention_instead_of_aborting_batch` en `tests/test_reasoning.py` y `citation_guard_fallbacks` a las métricas de `run_experiment`, para que quede medible cuántas veces se activa esta salvaguarda en una corrida real.
- **Pendiente, NO aplicado en esta sesión (dejar para revisión de Luis):** `citation_guard` exige, cuando la cita incluye artículo, que ese artículo aparezca también de forma literal en el texto del pasaje (`kingscode/reasoning/guards.py`, filtro extra sobre `supporting_passages`). El evaluador oficial (`scripts/citations.py::score`) solo compara a nivel de cuerpo normativo (`bodies()`), ignorando el artículo por completo. Eso significa que hoy rechazamos como "sin respaldo" citas que el evaluador SÍ pagaría (ej. "artículo 5 de la Ley 1010 de 2006" cuando el pasaje recuperado es el artículo 1 de esa misma ley). Bajar esa exigencia a nivel de cuerpo aumentaría el techo de puntaje de citas sin debilitar la protección real, pero es un cambio a la semántica de coincidencia que Luis diseñó y probó extensamente (16+ tests en `GuardSchemaTests`); se documenta aquí para decidirlo en conjunto, no se aplica unilateralmente.
- **Consolidación de contexto de B:** se integran al árbol canónico los materiales sueltos que traía Esteban en `kingscode_b/` y `kingscode_claude_context_files/` (ambos sin commitear, fuera de la estructura del repo): `CLAUDE.md`, `.claude/commands/`, `docs/B_FINDINGS_2026-09-28.md`, `docs/B_EXTENSION_PLAN.md`, `tools/analyze_citation_ceiling.py` y dos carpetas de prototipos de referencia (`docs/reference_b_prototype/`, `docs/reference_esteban_prototype/`) que documentan ideas pero no se importan al pipeline competitivo. Se construye `interfaz/app.py` (Streamlit) contra el pipeline real (`kingscode.reasoning.Pipeline` + `kingscode.Retriever`), con la identidad visual de Software Colombia, cubriendo el entregable de interfaz que seguía en cero. Se corrige `docs/TEAM_SPLIT.md`, que describía tareas de A/B ya completadas como si fueran "ahora".

## 2026-09-28 — T3/T5/T7 de `docs/B_EXTENSION_PLAN.md`

- **T3, política de abstención mínima:** `kingscode/reasoning/policy.py` gana `blocking_reasons(assessment, format)`, que separa razones "duras" (vacío/conflicto/evidencia no vigente) de razones blandas (referencia exacta ausente, consulta ambigua, vigencia no certificada, solapamiento léxico débil). `multiple_choice` nunca bloquea antes del decoder — adivinar entre opciones dadas supera a abstenerse incluso al azar, según la propia aritmética del enunciado (sección 6.1). Texto libre conserva el bloqueo solo para las razones duras; el resto pasa a `trace["warnings"]` y el decoder lo intenta, protegido por la red de seguridad de citas del punto anterior. `assess_evidence(...).sufficient` y `route_graph` (que lo consume para decidir expansión de grafo) no se tocaron: siguen considerando todas las razones, es un concepto distinto al de bloqueo de abstención.
- **T5, recuperación con opciones en cerradas:** `pipeline.py` gana `query_variants()` (una consulta por opción para `multiple_choice`, orden determinista) y `rrf_merge()` (fusión por rango recíproco sobre los pasajes que A ya devolvió, sin tocar sus internals ni mutar los pasajes). Con una sola variante (cualquier formato sin opciones) la llamada a `retrieve()` es idéntica byte a byte a la de antes. No se pudo medir el efecto real en recall/exactitud: requiere el corpus real, no disponible en esta máquina.
- **T7, entregables sin GPU:** `run.sh` (comando único: instala dependencias, exige o construye `corpus/`, corre tests, Gate 1B smoke y `scripts/evaluate.py --split sample`), `Dockerfile` + `.dockerignore` para la verificación de reproducibilidad en contenedor limpio, y secciones nuevas en el README (`## Comando único de reproducción`, `## Corpus e índice`). No se pudo ejecutar de punta a punta en esta máquina por falta de `corpus/` local — se verificó sintaxis de bash y del snippet Python embebido únicamente.
- **T6, throughput/concurrencia, deliberadamente no implementado:** requiere medición real (GPU + corpus) para no introducir bugs silenciosos en la guarda/citas deterministas; se deja documentado como bloqueado en vez de escribir concurrencia sin poder correrla, siguiendo la regla propia de `CLAUDE.md` de medir antes/después de cualquier cambio de calidad.
- Verificado con `python -m unittest discover -s tests -v`: 91 tests, OK (5 se saltan sin `corpus/` local). Nuevos tests: `test_multiple_choice_never_pre_blocks_on_soft_evidence_reasons`, `test_free_text_still_hard_blocks_on_empty_retrieval`, `test_query_variants_one_per_option_sorted_else_base_only`, `test_rrf_merge_boosts_passages_ranked_in_more_lists`, `test_multiple_choice_fans_out_one_retrieve_per_option_and_fuses_rrf`.

## 2026-09-28 — A v0.2 después del freeze GPU (60ebf7e)

Se reconoce el freeze RTX 4090 y se cierra validation v1 al tuning. Search V2 muestra empates con locator incluso sin boost de metadatos. Se productiviza parsing → identidad canónica → fragmentos → unión de candidatos antes del reranker; no se selecciona metadata_scale=1.25. La clase Retriever conserva defaults históricos para replay; la función pública añade locator y desactiva expansión AUTO en su perfil CPU; ON explícito conserva la expansión acotada del contrato. Los pesos neuronales siguen siendo explícitos.

Se preserva corpus-v0.1 byte a byte; corpus-v0.2 será un árbol separado. Benchmark v2 empieza con schema/piloto técnico determinista y una cola humana para escenarios/temporalidad/excepciones. Ningún modelo cerrado redacta preguntas competitivas. R0–R8 siguen siendo ablaciones, no un catálogo excluyente de arquitecturas finales. Composición, selección inmutable, confirmaciones autorizadas y freeze top 8 se decidirán con nueva evidencia v2. No se cambian B ni sus prompts.


## 2026-09-29 — Benchmark v2 independent source gate and international layer

- Se cierra benchmark v1 a tuning. El piloto v2 derivado de captions del corpus es solo smoke técnico: seis exposiciones DEV registradas, cero preguntas independientes, cero gold v2 independiente y cero SEALED_EVAL. Sus métricas no seleccionan arquitectura.
- El schema v2 admite RETRIEVAL_GOLD con conjuntos mínimos alternativos y END_TO_END_ONLY sin etiquetas de retrieval; las filas actuales se identifican como TECHNICAL_PILOT_ONLY. La recuperación no recibe gold.
- Las URLs oficiales de los PDFs ICFES localizados retornaron 404 en verificación directa; SIRNA confirma que existe una guía, sin banco público de ítems verificado. No se inventan preguntas para cumplir cuotas.
- Se añade inventario internacional selectivo de candidatos CAN/OIT/interamericano. Ratificación o aplicabilidad permanece pendiente de verificación para cada instrumento; no se indexa automáticamente. Benchmark internacional: cero ítems.
- Corpus-v0.1 queda inmutable. Corpus-v0.2 tiene cuatro documentos provisionales y las remediaciones G01/G02/C01/P02/P01/D01 aún no están completas; cada cambio requiere fuente primaria, fixture y prueba.
- Sin gold independiente no existe baseline útil ni distribución de fallos para escoger experimento. La siguiente ejecución será un baseline no ajustado sobre DEV externo revisado.

## 2026-09-29 — Diagnósticos de vistas y estado de remediación A v0.2

- El checkout remoto de `feat/member-a-corpus-v02-locator` estaba limpio en 790bf85. La suite completa pasó con 210 tests después de proporcionar `jsonschema==4.26.0` desde un directorio temporal ignorado; la primera invocación sin esa dependencia falló al importar siete módulos/casos.
- Se implementan métricas puras para Oracle Multi-View Recall, Fusion Loss y Graph Recovery Rate sobre `minimal_evidence_sets`, incluyendo alternativas. Las pruebas verifican alternativas, pérdida de fusión y recuperación condicionada a misses iniciales. No hay ranking/gold independiente; no se reportan valores empíricos ni baseline.
- Los seis hallazgos G01/G02/C01/P02/P01/D01 siguen pendientes. Se registra explícitamente qué evidencias no están en el snapshot. No se cambia v0.1 ni se intenta arreglar el parser por heurística. El grafo v0.2 permanece provisional: 29 `CONTIENE`, cero aristas semánticas activas y cero relaciones revisadas.
- El piloto existente contiene 12 casos corpus-derivados, no independientes ni seleccionables. No se amplía a 20–30 hasta revisar la estructura de las fuentes v0.2; esto evita convertir errores potenciales de parsing en diagnósticos supuestamente correctos.
- No se autoriza un experimento de retrieval: todavía no hay preguntas independientes aceptadas en DEV ni distribución de fallos. Próximo paso recomendado: obtener fuentes oficiales faltantes para las correcciones estructurales y continuar intake de assessment externo accesible; luego revisar bytes/fixtures antes de parser y benchmark.


## 2026-09-29 — Corpus v0.2 source-backed parser repairs and assessment intake update

- Preserve four primary legal sources in `corpora/corpus-v0.2/raw/` with URL, TLS/HTTP metadata and SHA-256 recorded in the v0.2 manifest. These are audit sources; the existing four-document/72-passage v0.2 snapshot was not rebuilt. Corpus v0.1 remains unchanged.
- Add v0.2-only corrections for publisher TOC rows (G02), repeated decision headings (C01), split statute headings (P02), and article termination at a major hierarchy heading (P01). Regression fixtures are checked against exact extracted blocks from the preserved bytes. The parser keeps PDF-specific safeguards when operating through the sanitized-block path.
- Leave G01 semantic relationships and D01 document identity review open; no semantic edges or automatic content-based document merges are activated.
- Official ICFES PDF origins remained unavailable; record indexed-only evidence without ingesting questions. The current SIRNA guide contains illustrative examples but its terms prohibit reproduction/transformation; no assessment examples are copied into benchmark assets. An ICFES 2021 source-rendering exposure is logged as validation candidate only.
- No independent retrieval gold was admitted. The baseline gate remains closed until at least 10 reviewed independent items exist.


## 2026-09-29 — Member A official-source runtime block and G01 candidate review

- The original ICFES Gestión del Conflicto 2026 and Comunicación Jurídica 2021 PDFs, current official module candidates, and the official toolbox landing URL were retried using browser navigation and browser-compatible headers. HTTP 404 in this runtime is recorded as `RUNTIME_ACQUISITION_BLOCKED`, because official ICFES index entries confirm the resources exist; indexed content is not accepted as original bytes.
- Added a hash-gated local intake helper targeting ignored `tmp/official-source-intake/`. It checks the recorded source ID, official ICFES host, input path, PDF signature and SHA-256 before indicating that local extraction may begin. Hash verification alone does not establish authenticity or usage rights.
- Reviewed the seven G01 candidate edges against the exact official containing-source text and recorded source URLs/hashes. Rejected the seven wrong containing-passage targets. The corrected target/modifier claims remain unresolved until their referenced legal instrument bytes are acquired; zero semantic edges are active.
- Added a D01 regression for equal content hashes across distinct canonical legal identities; broader provenance audit remains open.
- Independent extracted questions and retrieval-gold remain zero; no baseline or retrieval experiment is justified. No v0.1 or Member B files changed.

- Validación de esta continuación (segunda pasada final): 226 tests PASS; `python tools/benchmark_v2.py check` PASS con 10 hashes y holdout sin parsear; `python tools/verify_member_a_v02.py` PASS con 19 archivos oficiales, 326 archivos raw/clean v0.1 y 18 hashes v0.2. Sin GPU ni baseline.
- Precisión de adquisición: el PDF ICFES Gestión del Conflicto 2026-2 de mayo es una guía de orientación listada en el catálogo oficial, no un cuadernillo de preguntas. Se excluye de la intake de ítems; la fuente de preguntas original de febrero permanece confirmada por indexación oficial pero bloqueada por 404.
- Validación tras separar el PDF de orientación: tercera suite completa de esta continuación, 226 tests PASS; `benchmark_v2.py check` PASS (10 hashes, no holdout); verificador de snapshot PASS.

## 2026-09-28 — Revisión del plan de corpus v0.2 (propuesta, sin cambios de código)

- Medido en `reports/benchmark/r6_bm25_diagnostic/20260928T185549565248Z-dev`: 37/120 fallos, todos con el documento correcto en el rango 1 y el artículo incorrecto (CGP 18, Código Civil 8, Constitución 7, CST 2, Código General Disciplinario 2). La causa es `diversify.parse_reference` más un R6 que solo reordena; no faltan documentos.
- Benchmark v1: 200/200 casos EXPLICIT. Muestra oficial: 4/50 con artículo explícito, 14/50 con alguna norma. v1 no sirve para decidir pesos BM25/denso.
- Se propone el orden C0–C8 de `docs/CORPUS_V02_PLAN.md`: locator con inyección (C1) y benchmark v2 con preguntas semánticas escritas por el equipo (C2) antes de ampliar el corpus; adquisición dirigida y acotada (C3/C4); internacional al backlog por §4.2 del enunciado.
- Reverificado el 2026-09-29 sobre `main` (`a3548a1`): las cinco primeras filas de la tabla §2.1 del plan se reproducen exactas con `kingscode/diversify.py::parse_reference`, mientras `kingscode/reasoning/legal.py::references` y `scripts/citations.py::extract` resuelven las cinco correctamente.

## 2026-09-28 — Plan de B tras resultados 4090 (propuesta)

- Resultados de A en `feat/member-a-gpu-results-4090-20260928`: locator con inyección satura el benchmark v1 (dev EC@8 0,9917; validación 1,0). El benchmark v1 es 100 % explícito, así que no se infiere calidad semántica.
- B se reordena en `docs/B_PLAN_POST_GPU.md`: robustez 992 (B7) y reparación de citas en tres niveles (B2, requiere revisión de Luis) antes del bakeoff; Qwen3-8B se mantiene en el bakeoff porque el enunciado §3.1 lo sugiere (8.190.735.360 parámetros), con confirmación por correo pendiente.

## 2026-09-29 — B: planner de consultas, replay de planes, ejecución robusta de 992 y reparación/construcción de citas

- **Planner (B, nuevo):** `kingscode/reasoning/planner.py` + `kingscode/generation/planner_backend.py` (Qwen3-8B del lock, greedy, semilla 0, thinking off, carga vía `HFDecoder` sin modificarlo). Q0 siempre se conserva; el planner añade como máximo Q1 (hechos), Q2 (elementos jurídicos), Q3 (puente de vocabulario). Solo recibe el texto de la pregunta; nunca opciones, pasajes ni etiquetas. Salida inválida → solo Q0 (`fallback_malformed`). Fechas y montos de Q0 se reinyectan en cada vista; las negaciones se miden (Preservation Rate) pero no se reinyectan. Sin catálogo de reglas por área, sin HyDE/Query2doc, sin fine-tuning.
- **Frontera de confianza:** solo las referencias presentes en la pregunta (y en las opciones, que son texto del organizador) pueden usar el locator exacto de A. Las referencias que escribe el planner se registran como `generated_references` y sus vistas se consultan con el switch de locator apagado si `retrieve()` lo expone (`locator`, `locator_injection` o `exact_locator`). **Dependencia de A:** hoy `retrieve()` no tiene switch; cuando A productivice el locator debe exponer uno por llamada; mientras tanto la traza reporta `retrieve_has_no_locator_switch`.
- **Replay:** `kingscode/reasoning/plan_store.py` congela `reports/query_plans/<experiment_id>/plans.jsonl` + `manifest.json` (modelo, revisión, revisión del tokenizer, versión y SHA-256 del prompt, config de generación, entorno, SHA-256 del set de preguntas). Toda comparación consume planes congelados; `PlanStore` rechaza hash alterado o texto de pregunta distinto.
- **Modos de recuperación:** `Pipeline(retrieval_mode="base"|"option"|"plan")`. El default sigue siendo `option` (comportamiento ya mergeado en PR #2). `plan+option` queda deshabilitado hasta medir PLAN y OPTION por separado. El grafo no se toca en estos experimentos (diagnósticos con graph OFF).
- **Diagnósticos:** `tools/analyze_query_plans.py` (BASE_ONLY/PLAN_ONLY/BOTH/NEITHER, Oracle Multi-View Recall, Planner Miss Rate, Fusion Loss, Preservation Rate, Unsupported Hypothesis Rate, bootstrap pareado de A) contra el benchmark de A; lee gold solo después de escribir rankings y rechaza holdout. **No ejecutado:** no hay `corpus/` ni GPU en esta máquina, y el benchmark v1 es 100 % EXPLICIT: NO GENERALIZATION CLAIM hasta que A entregue un DEV independiente.
- **B7:** `kingscode/reasoning/batch.py` + `tools/member_b.py batch|verify`: checkpoint atómico por ítem, resume con verificación de identidad, errores aislados con 2 reintentos deterministas, respaldo por abstención `pipeline_error`, ensamblado ordenado con chequeo de completitud y hash, verificación en vivo con `--only`. `run_experiment` (Gate 1B) no se tocó. Ensayo de 992 con retriever de fixtures y decoder dummy: 41,6 s en CPU (test `test_992_rehearsal_with_dummy_decoder`); con corpus real: no ejecutado.
- **B2/B3 (requiere revisión de Luis):** `citation_builder.py` genera la cita final desde `canonical_body` + `article` del pasaje y solo emite lo que la propia regla de `citation_guard` y el extractor oficial verifican. `citation_repair.py` corre antes de la guarda: acepta, reescribe a nivel de cuerpo, renombra un código sin año al nombre que usa la evidencia, o suprime la oración/fragmento; solo abstiene texto libre si queda vacío un campo obligatorio. Para que ambos usen exactamente la regla de la guarda se extrajo `guards.reference_support()` de `citation_guard` sin cambiar su comportamiento (los 16 tests de `GuardSchemaTests` pasan). Desviación deliberada del plan B2: "cuerpo presente" usa el criterio de identidad de la guarda, no el de mención del evaluador, porque con este último la guarda final rechazaría el ítem.
- **Hallazgo para Luis:** `citation_guard` rechaza "artículo 1 de la Constitución Política" cuando el pasaje se titula "Constitución Política de Colombia de 1991" (exige el cuerpo sin año literal en el texto). La reparación lo compensa renombrando al nombre de la evidencia, pero la regla de la guarda debería revisarse junto con T1b.
- **Corrección a T3:** una cerrada sin ningún pasaje utilizable ahora se abstiene (`no_usable_evidence`), porque el validador oficial cuenta como malformada (fallo) una fila no abstenida sin `pasajes_recuperados`.
- Verificado: 176 tests; único error el de A `test_retrieval_benchmark...canonical_gold_integrity` (lee `corpus/passages.jsonl` sin `skipUnless`). Evaluador oficial sobre 50 filas de un decoder falso con citas buenas, de artículo equivocado e inventadas: 74 citas, 0 sin respaldo, `tasa_sin_respaldo` 0,0, 0 errores de validación (`tmp/member_b_v2/mixed_citations.jsonl`).

## 2026-09-29 — Integración A+B en `main` y preparación de la sesión GPU de laboratorio

- **Mergeado a `main`** (merges `--no-ff`, sin reescribir historia): `feat/member-a-corpus-v02-locator` (incluye `feat/member-a-gpu-results-4090-20260928` y `feat/member-a-gpu-benchmark-execution-v1`), `feat/member-a-corpus-quality-audit-v07`, `docs/state-reconciliation-20260928` y `feat/b-planner-batch-citations` (incluye `esteban/planes-b-y-corpus-v02`, PR #4).
- **Conflictos resueltos:** `KINGSCODE_STATE.json` (audit v07 vs v0.2): se conservan ambos bloques, prevalece la línea de selección más nueva. La reconciliación de docs del 28-sep 15:14 quedó superada por la de Luis de las 22:16 en los 6 documentos que ambas tocan: prevalece la más nueva; se conservan sus cambios únicos en `AGENTS.md`, `GPU_DAY_RUNBOOK.md`, `MEMBER_B_RUNBOOK.md` y `TEAM_SPLIT.md`. `DECISION_LOG.md`: se conservan las entradas de A y de B.
- **Planner sobre la vía nativa de A:** `Retriever.retrieve(question, k, graph_mode, query_views=...)` (A v0.2) resuelve el locator exacto, el router de grafo y el reranker solo sobre la pregunta original; las vistas solo amplían candidatos por RRF. El modo PLAN de B ahora hace una sola llamada con Q0 como pregunta y Q1–Q3 como `query_views` (`locator_control = a_query_views_locator_on_q0_only`); el fan-out propio de B queda como respaldo para un `retrieve` sin esa opción. Esto cierra la dependencia de "switch de locator por llamada" que B había pedido a A. `tools/analyze_query_plans.py` usa la misma vía.
- **Correcciones a código de A (requiere revisión de Luis, sin cambio de lógica):** (1) `tools/verify_member_a_v02.py` comparaba `kingscode/reasoning` y `config/reasoning.json` contra `60ebf7e` y fallaba siempre tras el merge legítimo de B; se excluyen solo esas rutas de B, el resto (oficiales, `data/`, `schema/`, `scripts/`, locks, benchmark v1, freeze 4090) sigue protegido y sin diferencias. (2) Cinco tests de A (`test_benchmark_gpu_execution` ×4, `test_retrieval_benchmark` ×1) leían `corpus/` sin `skipUnless`; se añadió el mismo guard que usan los demás tests de corpus.
- **CLI de B:** `tools/member_b.py batch|verify` acepta `--exact-locator`, `--retriever-mode`, `--rerank` y `--corpus`, y los registra en la identidad de la corrida.
- **Sesión GPU sin admin:** `tools/lab_gpu_session.ps1` (usa `.venv\Scripts\python.exe` sin activar, instala PyTorch CUDA dentro del venv según el driver, exige el snapshot v0.1 de Luis en vez de re-adquirir, trata el gate del benchmark independiente como informativo, y deja resultados en `reports/lab_session/<stamp>/`).
- Durante la integración Luis subió `1fdbcbb` (benchmark KC-COL-IR v0.1 y runner `tools/independent_ir_v2.py check|run --component C0..C3`); también se mergeó. Su test `test_kc_col_ir_v01...test_inventory_and_deterministic_sample_are_valid` requiere un artefacto local en `tmp/` (no versionado): se le añadió `skipUnless`. `tools/lab_gpu_session.ps1` usa ese runner real y el gate de `benchmarks/kc_col_ir_v0.1/manifest.json` (hoy cerrado: 0 gold aceptados, 30 candidatos del Externado en revisión humana).
- Verificado: 251 tests OK (11 saltados sin `corpus/`/GPU/artefactos locales); 19 archivos oficiales intactos; `tools/benchmark_v2.py check` PASS; `tools/independent_ir_v2.py check` → GATED; `verify_member_a_v02.py` pasa el diff protegido y se detiene en `corpus/manifest.json` (no hay corpus en esta máquina).

## 2026-09-27 — v0.2
- Equipo de 2 dividido por subsistemas.
- Baseline retrieval: BM25 + Qwen3-Embedding-0.6B + Qwen3-Reranker-0.6B.
- Qwen3-8B como decoder prior inicial.
- Decoder fine-tuning pospuesto; reranker hard-negative FT como primer candidato.
- RTX 4090 24 GB como hardware objetivo; probar BF16 antes de cuantización.

## 2026-09-27 — v0.3 (literatura)
- Retrieval pasa a ser explícitamente la prioridad #1 por evidencia de Legal RAG Bench 2026 y otros benchmarks legales.
- Se añade RRF como fusión baseline.
- Chunking pasa de “por artículo” simple a “structure-aware/adaptive”, preservando jerarquía legal.
- Se añade expansión terminológica controlada para español jurídico, no multi-query libre por defecto.
- Se añade `citation_guard` post-generation como componente obligatorio.
- Se añade ALIA-es-legal-administrative-7B-Instruct al bakeoff de decoders.
- GraphRAG queda como experimento opcional, no baseline.
- Se formaliza gate de fine-tuning: no decoder FT hasta tener retrieval alto.
- Siguiente acción congelada: Corpus v0 + benchmark BM25/retrieval antes de CUDA.

## 2026-09-27 — v0.4 (Graph-aware desde Corpus v0)
- Se corrige la decisión anterior de dejar GraphRAG solo para después del baseline.
- El corpus nace con jerarquía y grafo jurídico desde la ingesta.
- No se adopta GraphRAG pesado para todas las consultas: BM25+dense+RRF sigue siendo el fast path.
- El grafo se usa selectivamente para relaciones jerárquicas/normativas (`REMITE_A`, `MODIFICA`, `DEROGA`, `REGLAMENTA`, etc.).
- Se confirma al iniciar Integrante A que el ZIP oficial **no contiene los textos jurídicos completos**; contiene `seed_targets.json` con 186 objetivos y ubicaciones de búsqueda.
- Se crean schema canónico de pasajes/grafo y plan operativo del Integrante A.

## 2026-09-27 — v0.5 (Agent-ready + roles A/B revisados)
- Se corrige la división antigua: B ya no es solo inferencia/evaluación; ahora posee Query/Reasoning Layer, `graph_router`, generación, guards, evaluación y delivery.
- A pasa a ser explícitamente Knowledge Layer: corpus + provenance + graph + retrieval + reranking + métricas.
- Se crea `AGENTS.md` como protocolo operativo para cualquier agente/humano que continúe el proyecto.
- Se formalizan contratos `retrieve(..., graph_mode)` y `answer(...)`.
- Se crea `MEMBER_B_REASONING_EVAL_PLAN.md`, `INTEGRATION_CONTRACTS.md` y `ARCHITECTURE_V05.md`.
- Roadmap pasa a trabajo paralelo: A construye Corpus v0/BM25 mientras B construye harness pre-GPU/router/citation guard/evaluator.
- CUDA deja de ser un gate que bloquee a ambos; se aborda cuando el harness de B esté listo y haya máquina real.

## 2026-09-27 — Implementación de A / Corpus v0.1

- Se materializa el corpus desde fuentes oficiales: Función Pública, Corte Constitucional, SENA, Comunidad Andina y Corte Suprema. El inventario conserva 28 objetivos sin resolver, en vez de reemplazar años/números por coincidencias aproximadas. HTTPS valida certificados; raw y metadatos quedan disponibles para reconstrucción offline.
- Parser `legal-blocks-1.2`: artículos, numeración compuesta, reformas citadas, jerarquía, parágrafos y numerales; decisiones por estructura explícita. Se preservan páginas PDF y offsets exactos del clean. La portada CAN 486 sin texto utilizable se omite del clean; raw permanece completo.
- La revisión adicional detectó anexos/versiones con el mismo número de artículo. Se excluye de recuperación el grupo ambiguo completo, conservándolo para auditoría. No se decide automáticamente la versión vigente. Este cambio reduce el riesgo de atribuir un anexo al artículo de la norma principal.
- BM25 es el backend activo local pre-GPU. Dense Qwen3, RRF y reranker Qwen3 están implementados con commits fijos y prueba real; no se afirma benchmark neuronal completo. La máquina examinada tiene PyTorch 2.12.0+cpu, CUDA no disponible; 4090 sigue siendo objetivo externo.
- Grafo acotado: un salto, cinco semillas, dos pasajes por vecino, diez expansiones. Se emiten solo CONTIENE, CITA, REMITE_A y patrones explícitos MODIFICA/DEROGA; los demás tipos/tags quedan reservados a evidencia futura. AUTO es una política provisional inyectable por B. Su ausencia de disparos en el sample impide inferir que AUTO mejora OFF; ON se mide como ablation.
- Métricas: identidad canónica de fuente/artículo, no coincidencia de citas mencionadas en fuentes ajenas. `legal_basis` original se audita por separado y nunca llega al índice. MRR se trunca en 10 y nDCG cuenta objetivos distintos; no se afirma score oficial de QA.
- No se cambia decoder ni se inicia fine-tuning: la recuperación baseline aún requiere mejora. El siguiente paso compartido es integrar B y ejecutar comparaciones neuronales en la 4090 bajo el mismo snapshot.

## 2026-09-27 — Gate 1B / integración pre-GPU

- Se añade `kingscode/reasoning` sobre la API pública de A. La integración hace una recuperación OFF, decide con pregunta+evidencia y solicita expansión si corresponde. El adaptador devuelve bool porque A no recibe el contexto plano ni interpreta strings OFF/AUTO/ON en su callback. No se cambian internals de A.
- El límite de entrada del sistema proyecta exclusivamente ID, pregunta, formato y opciones. Las etiquetas solo se leen en el proceso del evaluador oficial; alterar etiquetas no modifica entradas públicas, fingerprint ni resultados del sistema.
- El backend dummy siempre se abstiene. Se verifica el pipeline completo sin producir supuestas respuestas jurídicas de prueba. La CLI bloquea backends reales, retrieval neuronal y RAGAS en este gate; temperatura prevista 0 y muestreo deshabilitado.
- Contradicción del schema oficial: la descripción de `respuesta_correcta` dice «Con abstencion true se admite null», pero su enum solo admite A/B/C/D. Sin modificar el archivo, el dummy usa A como marcador formal, declara que no representa una elección y mantiene abstención true. No se elige la letra según el banco.
- Citation guard más conservador que la puntuación documental del evaluador: comprueba número, año, artículo, identidad primaria de fuente y presencia literal en la evidencia emitida. No usa alias por número ignorando año ni atribuye artículos de un código a todas las leyes mencionadas en su título. No certifica implicación semántica de conclusiones.
- JSON/schema/citas inválidos abortan la corrida y se registran; no hay reparación manual ni publicación de un JSONL final parcial. Evidencia histórica/ambigua, conflictos fuertes o referencias insuficientes disparan abstención.
- Cada corrida conserva directorio nuevo, configuración/hashes/fingerprint, trazas, tiempos y evaluación oficial sin RAGAS. El JSONL y las decisiones son deterministas; las rutas/timestamps/latencias no se comparan como contenido reproducible. Cero citas del dummy no constituye evidencia de calidad de citación.

## 2026-09-28 — Gate 2-Prep, ejecución diferida por el usuario

- Se fija la revisión real de Qwen3-8B, ALIA Legal, Salamandra y Llama opcional desde el Hub oficial; las entradas originales del encoder/reranker permanecen iguales. Salamandra/Llama requieren acceso manual y no se presume autorización. Los conteos reales de los modelos nominales 8B requieren aclarar elegibilidad antes de entrega competitiva.
- La generación real se prepara en `kingscode/generation/` para conservar los módulos, salida y fingerprint del dummy. El backend implementa el protocolo existente, es lazy, usa snapshots locales con hashes, prohíbe remote code y conserva las guardas. No se descargaron decoders.
- Prompts lógicos `grounded-formats-v2`, template nativo de cada tokenizer, Qwen sin thinking; parámetros greedy explícitos comunes. Formato/JSON/citas/contexto inválidos abortan el experimento, sin truncar ni editar la respuesta. El router sigue basado en reglas, sin prompt/modelo generativo.
- Se separa la medición de retrieval de la comparación de decoders: rankings públicos medidos → freeze de ocho evidencias por pregunta → mismos datos para D1–D4. Se evita mantener retrieval y decoder juntos en VRAM. Los tiempos de generación no se presentan como latencia end-to-end en vivo.
- BF16 primero, contexto total 8192 y batch 1 preparados; fit/latencia no verificados. INT8/4-bit requieren registro de OOM BF16 de la misma configuración y evidencia, y nunca se activan automáticamente. El plan de entorno no escoge una build CUDA sin diagnóstico ni instala paquetes.
- La última instrucción del usuario reemplazó la ejecución de verificaciones por preparación sin pruebas. Se añaden 28 tests y dos comandos de verificación, **no ejecutados**. No se declara Gate 2A/2B ni bakeoff completado; los resultados previos A/1B se conservan como históricos.

## 2026-09-28 — v0.6 (Member A knowledge layer: metadata + retrieval)

- Se agrega una capa de derivación determinista (`kingscode/metadata.py`) con identidad canónica independiente de la URL: `canonical_document_id` (p. ej. `ley:1564:2012`, `decreto:410:1971`, `codigo_civil`, `constitucion:1991`, `corte_constitucional:c355:2006`, `corte_suprema:sl3385:2022`) y `canonical_fragment_id` en un espacio de nombres separado (p. ej. `ley:1564:2012:articulo:391`). Las variantes históricas o los encabezados de artículo repetidos se mantienen distintos. No cambia `corpus.py` ni el build; el corpus se reconstruye byte a byte idéntico (mismos hashes que v0.1).
- Metadatos v0.6 aditivos y opcionales: `content_hash` (solo cuerpo semántico, excluye `text_prefix`), `status_assertion`/`status_source_passage_id`/`effective_from`/`effective_to`/`version_date`. La validez legal nunca se infiere: por defecto `unknown`/`null` salvo evidencia explícita de la fuente. No se introduce ningún puntaje de autoridad arbitrario. La procedencia técnica (hash, HTTP, ruta, timestamp) se mantiene fuera del texto de embedding.
- Se separan explícitamente tres planos: metadatos de documento, metadatos de pasaje y **scores de recuperación en tiempo de ejecución** (`bm25_score`, `dense_score`, `rrf_score`, `reranker_score`, `graph_score`, `final_score`), que no se persisten como metadatos del corpus.
- Fase 1: se clasifican los 28 objetivos de adquisición no resueltos (`kingscode/acquisition_backlog.py`) en `resolved`/`not_found`/`ambiguous`/`source_unavailable`/`identifier_suspect`, conservando procedencia y notas. Nunca se sustituye una norma/año/número/decisión similar ni se corrige un identificador dudoso; los sospechosos se marcan para revisión humana. Resultado: 14 `source_unavailable` (Corte Suprema sin resolver verificado), 11 `not_found`, 2 `identifier_suspect`, 1 `ambiguous`.
- Fase 4: deduplicación y diversificación (`kingscode/diversify.py`) agrupables por `canonical_document_id`/`canonical_fragment_id`/`content_hash`. La diversificación es configurable, apta para ablación y **no** se activa por defecto; la procedencia de espejos duplicados se conserva, no se descarta.
- Fase 5: taxonomía de fallos de recuperación (`kingscode/failure_analysis.py`): `corpus_missing`, `correct_document_wrong_passage`, `wrong_document`, `ranking_failure`, `graph_failure`, `ambiguous_ground_truth`, más `success`. No se fuerza una clasificación cuando `legal_basis` es incompleto o contradictorio. Se añade `document_mismatch_rate` (definición propia; no se afirma equivalencia con una métrica académica DRM).
- Fase 6: experimentos R6/R7/R8 opcionales (`kingscode/metadata_experiments.py`) sobre la API pública `retrieve(...)`, sin tocar R0–R5 de B ni cambiar la ruta por defecto. Para referencias explícitas se usa localizador estructurado exacto + recuperación general → unión de candidatos → ranking; los rasgos de metadatos son priores suaves, nunca filtros duros. Registrados en `config/experiment_matrix.json`.
- Fase 7: representación de embedding experimental (`metadata.embedding_representation`) con encabezado Norma/Ley/Artículo/Título; excluye sha256, ruta, HTTP, bytes y `retrieved_at`. Es un experimento, no un reemplazo medido de la representación actual.
- Fase 8: se confirma que toda relación normativa del grafo conserva `source`, `target`, `relation`, `evidence_passage_id` y procedencia (`method`); 0 aristas sin evidencia. Estados temporales `current/historical/repealed/modified/unknown` solo con evidencia; por defecto `unknown`.
- Fase 9: reporte de cobertura v0.6 (`reports/corpus_coverage_v06.json`) que no usa el conteo de documentos como proxy de calidad.
- Verificación: 132 tests (16 A históricos + 44 nuevos v0.6 + 44 B + 28 GPU) en verde; dos verificaciones independientes con reconstrucción byte a byte y recomputación de métricas. Archivos oficiales (19) intactos; implementación de B intacta; sin GPU/bakeoff/RAGAS/fine-tuning; sin indexar `expected_answer`/`legal_basis`.
- La hipótesis de que el corpus deba responder casi cualquier pregunta del dominio se trata solo como hipótesis de diseño, no como requisito oficial del reto.

## 2026-09-28 — Internal retrieval benchmark v1 (Member A)

- Se crea un benchmark interno de recuperación separado del sample oficial: 200 casos deterministas derivados de metadata/pasajes oficiales (120 dev, 40 validation, 40 holdout; 20 por área). Preguntas y gold se guardan en archivos separados; `retrieve` recibe exclusivamente el texto de pregunta y los gold se cargan solo después de capturar rankings. No se usó un modelo cerrado ni se fabricaron preguntas semánticas: 20 paquetes de autoría quedan para revisión humana.
- Se definen métricas de evidencia a k=1/3/5/8/10, MRR/MAP/nDCG, recuperación documental, mismatch documental (definición propia), completitud de evidencia, spans, costo de contexto, subgrupos y bootstrap pareado determinista (seed 0, 10.000 muestras). Holdout tiene declaración preautorizada únicamente para R0 baseline; selección posterior exige registro de validation y cada variante se consume una vez.
- R0 BM25 se ejecuta sobre los tres splits. En validation: Evidence Completeness@8=0.575, Recall@10=0.625, MRR@10=0.3739, nDCG@10=0.4331, Document Mismatch=0.10. El holdout R0 es baseline predeclarado, no tuning ni confirmación de selección.
- R0 graph AUTO/ON y R6/R7/R8 con backend BM25 se registran solo como diagnósticos: no cumplen la definición R3-based y no pueden seleccionar arquitectura. AUTO no cambia Recall/Completeness; ON no mejora Recall/Completeness. El diagnóstico R6-BM25 mejora dev, pero requiere repetición correcta sobre R3 antes de cualquier conclusión. R8-BM25 degrada las métricas del diagnóstico.
- No existe reporte/configuración/index BGE-M3 reproducible en el repo; los valores proporcionados por el usuario se conservan como `user-reported`, no evidencia reproducida. Qwen dense, BGE, híbridos, reranker y R3–R8 reales quedan `GPU_BLOCKED` con prerequisitos exactos. Por tanto no se selecciona arquitectura ni se congela evidencia para B; tampoco se ejecuta confirmación oficial-50 posterior a selección.
- Se preservan resultados negativos/bloqueados y se prohíbe usar el sample oficial para desarrollo del benchmark interno. La siguiente decisión depende de comparaciones same-ID en la 4090, no de preferencia previa.
## 2026-09-28 — Corrección del abort-on-citation en `Pipeline.run`, consolidación de contexto de B

- **Hallazgo (Esteban, verificado contra el código real, no contra documentación):** con un decoder real conectado (`HFDecoder`, ya preparado en Gate 2-Prep), la primera cita sin respaldo generada por el modelo hace que `citation_guard` levante `CitationGuardError`. Esa excepción se propaga sin capturar a través de `Pipeline.run` hasta el bucle `for question in questions` de `run_experiment`, que la deja subir sin publicar `submissions.jsonl` para NINGUNA de las 992 preguntas (política registrada el 2026-09-27: "JSON/schema/citas inválidos abortan la corrida... no hay publicación de un JSONL final parcial"). El sábado, con un decoder real generando texto libre, esto es virtualmente seguro que ocurra al menos una vez en 992 ítems y dejaría al equipo sin entrega.
- **Corrección de arquitectura (requiere revisión cruzada de Luis, integrante A, antes del día de GPU):** se modifica únicamente `Pipeline.run` (`kingscode/reasoning/pipeline.py`) para capturar `CitationGuardError` y, solo ahí, sustituir la fila rechazada por una abstención construida con `abstention_row` sobre la misma evidencia — exactamente el mecanismo que el anexo B.5 del enunciado pide ("verificar que toda norma citada aparece en la evidencia y, si no, suprimir la citación"). **No se toca** `citation_guard`, `_answer` ni la función pública `answer()`: siguen lanzando `CitationGuardError` exactamente igual que antes para cualquier llamador directo, por lo que las pruebas de integridad de evidencia (`test_decoder_cannot_mutate_evidence_to_create_support`, todas las de `GuardSchemaTests`) no cambian. Tampoco se toca el comportamiento ante `SubmissionValidationError` (JSON/schema inválido sigue abortando la corrida sin publicar; ver `test_failed_run_is_registered_without_final_submission`), porque esa es una señal de bug del decoder, no de una cita jurídica cuestionable, y el equipo no ha revisado si debe tratarse igual.
- Se añade `test_unsupported_citation_falls_back_to_abstention_instead_of_aborting_batch` en `tests/test_reasoning.py` y `citation_guard_fallbacks` a las métricas de `run_experiment`, para que quede medible cuántas veces se activa esta salvaguarda en una corrida real.
- **Pendiente, NO aplicado en esta sesión (dejar para revisión de Luis):** `citation_guard` exige, cuando la cita incluye artículo, que ese artículo aparezca también de forma literal en el texto del pasaje (`kingscode/reasoning/guards.py`, filtro extra sobre `supporting_passages`). El evaluador oficial (`scripts/citations.py::score`) solo compara a nivel de cuerpo normativo (`bodies()`), ignorando el artículo por completo. Eso significa que hoy rechazamos como "sin respaldo" citas que el evaluador SÍ pagaría (ej. "artículo 5 de la Ley 1010 de 2006" cuando el pasaje recuperado es el artículo 1 de esa misma ley). Bajar esa exigencia a nivel de cuerpo aumentaría el techo de puntaje de citas sin debilitar la protección real, pero es un cambio a la semántica de coincidencia que Luis diseñó y probó extensamente (16+ tests en `GuardSchemaTests`); se documenta aquí para decidirlo en conjunto, no se aplica unilateralmente.
- **Consolidación de contexto de B:** se integran al árbol canónico los materiales sueltos que traía Esteban en `kingscode_b/` y `kingscode_claude_context_files/` (ambos sin commitear, fuera de la estructura del repo): `CLAUDE.md`, `.claude/commands/`, `docs/B_FINDINGS_2026-09-28.md`, `docs/B_EXTENSION_PLAN.md`, `tools/analyze_citation_ceiling.py` y dos carpetas de prototipos de referencia (`docs/reference_b_prototype/`, `docs/reference_esteban_prototype/`) que documentan ideas pero no se importan al pipeline competitivo. Se construye `interfaz/app.py` (Streamlit) contra el pipeline real (`kingscode.reasoning.Pipeline` + `kingscode.Retriever`), con la identidad visual de Software Colombia, cubriendo el entregable de interfaz que seguía en cero. Se corrige `docs/TEAM_SPLIT.md`, que describía tareas de A/B ya completadas como si fueran "ahora".

## 2026-09-28 — T3/T5/T7 de `docs/B_EXTENSION_PLAN.md`

- **T3, política de abstención mínima:** `kingscode/reasoning/policy.py` gana `blocking_reasons(assessment, format)`, que separa razones "duras" (vacío/conflicto/evidencia no vigente) de razones blandas (referencia exacta ausente, consulta ambigua, vigencia no certificada, solapamiento léxico débil). `multiple_choice` nunca bloquea antes del decoder — adivinar entre opciones dadas supera a abstenerse incluso al azar, según la propia aritmética del enunciado (sección 6.1). Texto libre conserva el bloqueo solo para las razones duras; el resto pasa a `trace["warnings"]` y el decoder lo intenta, protegido por la red de seguridad de citas del punto anterior. `assess_evidence(...).sufficient` y `route_graph` (que lo consume para decidir expansión de grafo) no se tocaron: siguen considerando todas las razones, es un concepto distinto al de bloqueo de abstención.
- **T5, recuperación con opciones en cerradas:** `pipeline.py` gana `query_variants()` (una consulta por opción para `multiple_choice`, orden determinista) y `rrf_merge()` (fusión por rango recíproco sobre los pasajes que A ya devolvió, sin tocar sus internals ni mutar los pasajes). Con una sola variante (cualquier formato sin opciones) la llamada a `retrieve()` es idéntica byte a byte a la de antes. No se pudo medir el efecto real en recall/exactitud: requiere el corpus real, no disponible en esta máquina.
- **T7, entregables sin GPU:** `run.sh` (comando único: instala dependencias, exige o construye `corpus/`, corre tests, Gate 1B smoke y `scripts/evaluate.py --split sample`), `Dockerfile` + `.dockerignore` para la verificación de reproducibilidad en contenedor limpio, y secciones nuevas en el README (`## Comando único de reproducción`, `## Corpus e índice`). No se pudo ejecutar de punta a punta en esta máquina por falta de `corpus/` local — se verificó sintaxis de bash y del snippet Python embebido únicamente.
- **T6, throughput/concurrencia, deliberadamente no implementado:** requiere medición real (GPU + corpus) para no introducir bugs silenciosos en la guarda/citas deterministas; se deja documentado como bloqueado en vez de escribir concurrencia sin poder correrla, siguiendo la regla propia de `CLAUDE.md` de medir antes/después de cualquier cambio de calidad.
- Verificado con `python -m unittest discover -s tests -v`: 91 tests, OK (5 se saltan sin `corpus/` local). Nuevos tests: `test_multiple_choice_never_pre_blocks_on_soft_evidence_reasons`, `test_free_text_still_hard_blocks_on_empty_retrieval`, `test_query_variants_one_per_option_sorted_else_base_only`, `test_rrf_merge_boosts_passages_ranked_in_more_lists`, `test_multiple_choice_fans_out_one_retrieve_per_option_and_fuses_rrf`.

## 2026-09-28 — A v0.2 después del freeze GPU (60ebf7e)

Se reconoce el freeze RTX 4090 y se cierra validation v1 al tuning. Search V2 muestra empates con locator incluso sin boost de metadatos. Se productiviza parsing → identidad canónica → fragmentos → unión de candidatos antes del reranker; no se selecciona metadata_scale=1.25. La clase Retriever conserva defaults históricos para replay; la función pública añade locator y desactiva expansión AUTO en su perfil CPU; ON explícito conserva la expansión acotada del contrato. Los pesos neuronales siguen siendo explícitos.

Se preserva corpus-v0.1 byte a byte; corpus-v0.2 será un árbol separado. Benchmark v2 empieza con schema/piloto técnico determinista y una cola humana para escenarios/temporalidad/excepciones. Ningún modelo cerrado redacta preguntas competitivas. R0–R8 siguen siendo ablaciones, no un catálogo excluyente de arquitecturas finales. Composición, selección inmutable, confirmaciones autorizadas y freeze top 8 se decidirán con nueva evidencia v2. No se cambian B ni sus prompts.


## 2026-09-29 — Benchmark v2 independent source gate and international layer

- Se cierra benchmark v1 a tuning. El piloto v2 derivado de captions del corpus es solo smoke técnico: seis exposiciones DEV registradas, cero preguntas independientes, cero gold v2 independiente y cero SEALED_EVAL. Sus métricas no seleccionan arquitectura.
- El schema v2 admite RETRIEVAL_GOLD con conjuntos mínimos alternativos y END_TO_END_ONLY sin etiquetas de retrieval; las filas actuales se identifican como TECHNICAL_PILOT_ONLY. La recuperación no recibe gold.
- Las URLs oficiales de los PDFs ICFES localizados retornaron 404 en verificación directa; SIRNA confirma que existe una guía, sin banco público de ítems verificado. No se inventan preguntas para cumplir cuotas.
- Se añade inventario internacional selectivo de candidatos CAN/OIT/interamericano. Ratificación o aplicabilidad permanece pendiente de verificación para cada instrumento; no se indexa automáticamente. Benchmark internacional: cero ítems.
- Corpus-v0.1 queda inmutable. Corpus-v0.2 tiene cuatro documentos provisionales y las remediaciones G01/G02/C01/P02/P01/D01 aún no están completas; cada cambio requiere fuente primaria, fixture y prueba.
- Sin gold independiente no existe baseline útil ni distribución de fallos para escoger experimento. La siguiente ejecución será un baseline no ajustado sobre DEV externo revisado.

## 2026-09-29 — Diagnósticos de vistas y estado de remediación A v0.2

- El checkout remoto de `feat/member-a-corpus-v02-locator` estaba limpio en 790bf85. La suite completa pasó con 210 tests después de proporcionar `jsonschema==4.26.0` desde un directorio temporal ignorado; la primera invocación sin esa dependencia falló al importar siete módulos/casos.
- Se implementan métricas puras para Oracle Multi-View Recall, Fusion Loss y Graph Recovery Rate sobre `minimal_evidence_sets`, incluyendo alternativas. Las pruebas verifican alternativas, pérdida de fusión y recuperación condicionada a misses iniciales. No hay ranking/gold independiente; no se reportan valores empíricos ni baseline.
- Los seis hallazgos G01/G02/C01/P02/P01/D01 siguen pendientes. Se registra explícitamente qué evidencias no están en el snapshot. No se cambia v0.1 ni se intenta arreglar el parser por heurística. El grafo v0.2 permanece provisional: 29 `CONTIENE`, cero aristas semánticas activas y cero relaciones revisadas.
- El piloto existente contiene 12 casos corpus-derivados, no independientes ni seleccionables. No se amplía a 20–30 hasta revisar la estructura de las fuentes v0.2; esto evita convertir errores potenciales de parsing en diagnósticos supuestamente correctos.
- No se autoriza un experimento de retrieval: todavía no hay preguntas independientes aceptadas en DEV ni distribución de fallos. Próximo paso recomendado: obtener fuentes oficiales faltantes para las correcciones estructurales y continuar intake de assessment externo accesible; luego revisar bytes/fixtures antes de parser y benchmark.


## 2026-09-29 — Corpus v0.2 source-backed parser repairs and assessment intake update

- Preserve four primary legal sources in `corpora/corpus-v0.2/raw/` with URL, TLS/HTTP metadata and SHA-256 recorded in the v0.2 manifest. These are audit sources; the existing four-document/72-passage v0.2 snapshot was not rebuilt. Corpus v0.1 remains unchanged.
- Add v0.2-only corrections for publisher TOC rows (G02), repeated decision headings (C01), split statute headings (P02), and article termination at a major hierarchy heading (P01). Regression fixtures are checked against exact extracted blocks from the preserved bytes. The parser keeps PDF-specific safeguards when operating through the sanitized-block path.
- Leave G01 semantic relationships and D01 document identity review open; no semantic edges or automatic content-based document merges are activated.
- Official ICFES PDF origins remained unavailable; record indexed-only evidence without ingesting questions. The current SIRNA guide contains illustrative examples but its terms prohibit reproduction/transformation; no assessment examples are copied into benchmark assets. An ICFES 2021 source-rendering exposure is logged as validation candidate only.
- No independent retrieval gold was admitted. The baseline gate remains closed until at least 10 reviewed independent items exist.


## 2026-09-29 — Member A official-source runtime block and G01 candidate review

- The original ICFES Gestión del Conflicto 2026 and Comunicación Jurídica 2021 PDFs, current official module candidates, and the official toolbox landing URL were retried using browser navigation and browser-compatible headers. HTTP 404 in this runtime is recorded as `RUNTIME_ACQUISITION_BLOCKED`, because official ICFES index entries confirm the resources exist; indexed content is not accepted as original bytes.
- Added a hash-gated local intake helper targeting ignored `tmp/official-source-intake/`. It checks the recorded source ID, official ICFES host, input path, PDF signature and SHA-256 before indicating that local extraction may begin. Hash verification alone does not establish authenticity or usage rights.
- Reviewed the seven G01 candidate edges against the exact official containing-source text and recorded source URLs/hashes. Rejected the seven wrong containing-passage targets. The corrected target/modifier claims remain unresolved until their referenced legal instrument bytes are acquired; zero semantic edges are active.
- Added a D01 regression for equal content hashes across distinct canonical legal identities; broader provenance audit remains open.
- Independent extracted questions and retrieval-gold remain zero; no baseline or retrieval experiment is justified. No v0.1 or Member B files changed.

- Validación de esta continuación (segunda pasada final): 226 tests PASS; `python tools/benchmark_v2.py check` PASS con 10 hashes y holdout sin parsear; `python tools/verify_member_a_v02.py` PASS con 19 archivos oficiales, 326 archivos raw/clean v0.1 y 18 hashes v0.2. Sin GPU ni baseline.
- Precisión de adquisición: el PDF ICFES Gestión del Conflicto 2026-2 de mayo es una guía de orientación listada en el catálogo oficial, no un cuadernillo de preguntas. Se excluye de la intake de ítems; la fuente de preguntas original de febrero permanece confirmada por indexación oficial pero bloqueada por 404.
- Validación tras separar el PDF de orientación: tercera suite completa de esta continuación, 226 tests PASS; `benchmark_v2.py check` PASS (10 hashes, no holdout); verificador de snapshot PASS.


## 2026-09-29 — KC-COL-IR-v0.1 institution-family isolation

- Create a separate cross-institution benchmark: Externado DEV; Universidad Libre validation-only; ICFES/SIRNA sealed/future. Never use institution family to fill another split. Topic guides count for coverage only.
- Mechanical acquisition of the official 2011 Externado Civil Procedure bank yields 270 numbered candidates, but extraction glyph damage means exact wording remains unverified. Do not accept or run retrieval on them until human transcription/option QA and independent primary-law/temporal review.
- Hash-sample 30 before retrieval. Freeze the >=10 accepted DEV retrieval-gold gate. First comparison uses C0 BM25/C1 Qwen dense/C2 RRF/C3 hybrid+Qwen reranker, same candidate depth, graph OFF. No GPU execution in this acquisition session.
- Historical Universidad Libre sources are `VALIDATION_CANDIDATE`; URLs currently return HTML, not verified PDF bytes. Do not parse/score until DEV architecture selection.

# KingsCode Decision Log

## 2026-09-27 — v0.1
- Validar starter pack antes de GPU.
- No instalar CUDA/PyTorch a ciegas.

## 2026-09-27 — v0.2
- Equipo de 2 dividido por subsistemas.
- Baseline retrieval: BM25 + Qwen3-Embedding-0.6B + Qwen3-Reranker-0.6B.
- Qwen3-8B como decoder prior inicial.
- Decoder fine-tuning pospuesto; reranker hard-negative FT como primer candidato.
- RTX 4090 24 GB como hardware objetivo; probar BF16 antes de cuantización.

## 2026-09-27 — v0.3 (literatura)
- Retrieval pasa a ser explícitamente la prioridad #1 por evidencia de Legal RAG Bench 2026 y otros benchmarks legales.
- Se añade RRF como fusión baseline.
- Chunking pasa de “por artículo” simple a “structure-aware/adaptive”, preservando jerarquía legal.
- Se añade expansión terminológica controlada para español jurídico, no multi-query libre por defecto.
- Se añade `citation_guard` post-generation como componente obligatorio.
- Se añade ALIA-es-legal-administrative-7B-Instruct al bakeoff de decoders.
- GraphRAG queda como experimento opcional, no baseline.
- Se formaliza gate de fine-tuning: no decoder FT hasta tener retrieval alto.
- Siguiente acción congelada: Corpus v0 + benchmark BM25/retrieval antes de CUDA.

## 2026-09-27 — v0.4 (Graph-aware desde Corpus v0)
- Se corrige la decisión anterior de dejar GraphRAG solo para después del baseline.
- El corpus nace con jerarquía y grafo jurídico desde la ingesta.
- No se adopta GraphRAG pesado para todas las consultas: BM25+dense+RRF sigue siendo el fast path.
- El grafo se usa selectivamente para relaciones jerárquicas/normativas (`REMITE_A`, `MODIFICA`, `DEROGA`, `REGLAMENTA`, etc.).
- Se confirma al iniciar Integrante A que el ZIP oficial **no contiene los textos jurídicos completos**; contiene `seed_targets.json` con 186 objetivos y ubicaciones de búsqueda.
- Se crean schema canónico de pasajes/grafo y plan operativo del Integrante A.

## 2026-09-27 — v0.5 (Agent-ready + roles A/B revisados)
- Se corrige la división antigua: B ya no es solo inferencia/evaluación; ahora posee Query/Reasoning Layer, `graph_router`, generación, guards, evaluación y delivery.
- A pasa a ser explícitamente Knowledge Layer: corpus + provenance + graph + retrieval + reranking + métricas.
- Se crea `AGENTS.md` como protocolo operativo para cualquier agente/humano que continúe el proyecto.
- Se formalizan contratos `retrieve(..., graph_mode)` y `answer(...)`.
- Se crea `MEMBER_B_REASONING_EVAL_PLAN.md`, `INTEGRATION_CONTRACTS.md` y `ARCHITECTURE_V05.md`.
- Roadmap pasa a trabajo paralelo: A construye Corpus v0/BM25 mientras B construye harness pre-GPU/router/citation guard/evaluator.
- CUDA deja de ser un gate que bloquee a ambos; se aborda cuando el harness de B esté listo y haya máquina real.

## 2026-09-27 — Implementación de A / Corpus v0.1

- Se materializa el corpus desde fuentes oficiales: Función Pública, Corte Constitucional, SENA, Comunidad Andina y Corte Suprema. El inventario conserva 28 objetivos sin resolver, en vez de reemplazar años/números por coincidencias aproximadas. HTTPS valida certificados; raw y metadatos quedan disponibles para reconstrucción offline.
- Parser `legal-blocks-1.2`: artículos, numeración compuesta, reformas citadas, jerarquía, parágrafos y numerales; decisiones por estructura explícita. Se preservan páginas PDF y offsets exactos del clean. La portada CAN 486 sin texto utilizable se omite del clean; raw permanece completo.
- La revisión adicional detectó anexos/versiones con el mismo número de artículo. Se excluye de recuperación el grupo ambiguo completo, conservándolo para auditoría. No se decide automáticamente la versión vigente. Este cambio reduce el riesgo de atribuir un anexo al artículo de la norma principal.
- BM25 es el backend activo local pre-GPU. Dense Qwen3, RRF y reranker Qwen3 están implementados con commits fijos y prueba real; no se afirma benchmark neuronal completo. La máquina examinada tiene PyTorch 2.12.0+cpu, CUDA no disponible; 4090 sigue siendo objetivo externo.
- Grafo acotado: un salto, cinco semillas, dos pasajes por vecino, diez expansiones. Se emiten solo CONTIENE, CITA, REMITE_A y patrones explícitos MODIFICA/DEROGA; los demás tipos/tags quedan reservados a evidencia futura. AUTO es una política provisional inyectable por B. Su ausencia de disparos en el sample impide inferir que AUTO mejora OFF; ON se mide como ablation.
- Métricas: identidad canónica de fuente/artículo, no coincidencia de citas mencionadas en fuentes ajenas. `legal_basis` original se audita por separado y nunca llega al índice. MRR se trunca en 10 y nDCG cuenta objetivos distintos; no se afirma score oficial de QA.
- No se cambia decoder ni se inicia fine-tuning: la recuperación baseline aún requiere mejora. El siguiente paso compartido es integrar B y ejecutar comparaciones neuronales en la 4090 bajo el mismo snapshot.

## 2026-09-27 — Gate 1B / integración pre-GPU

- Se añade `kingscode/reasoning` sobre la API pública de A. La integración hace una recuperación OFF, decide con pregunta+evidencia y solicita expansión si corresponde. El adaptador devuelve bool porque A no recibe el contexto plano ni interpreta strings OFF/AUTO/ON en su callback. No se cambian internals de A.
- El límite de entrada del sistema proyecta exclusivamente ID, pregunta, formato y opciones. Las etiquetas solo se leen en el proceso del evaluador oficial; alterar etiquetas no modifica entradas públicas, fingerprint ni resultados del sistema.
- El backend dummy siempre se abstiene. Se verifica el pipeline completo sin producir supuestas respuestas jurídicas de prueba. La CLI bloquea backends reales, retrieval neuronal y RAGAS en este gate; temperatura prevista 0 y muestreo deshabilitado.
- Contradicción del schema oficial: la descripción de `respuesta_correcta` dice «Con abstencion true se admite null», pero su enum solo admite A/B/C/D. Sin modificar el archivo, el dummy usa A como marcador formal, declara que no representa una elección y mantiene abstención true. No se elige la letra según el banco.
- Citation guard más conservador que la puntuación documental del evaluador: comprueba número, año, artículo, identidad primaria de fuente y presencia literal en la evidencia emitida. No usa alias por número ignorando año ni atribuye artículos de un código a todas las leyes mencionadas en su título. No certifica implicación semántica de conclusiones.
- JSON/schema/citas inválidos abortan la corrida y se registran; no hay reparación manual ni publicación de un JSONL final parcial. Evidencia histórica/ambigua, conflictos fuertes o referencias insuficientes disparan abstención.
- Cada corrida conserva directorio nuevo, configuración/hashes/fingerprint, trazas, tiempos y evaluación oficial sin RAGAS. El JSONL y las decisiones son deterministas; las rutas/timestamps/latencias no se comparan como contenido reproducible. Cero citas del dummy no constituye evidencia de calidad de citación.

## 2026-09-28 — Gate 2-Prep, ejecución diferida por el usuario

- Se fija la revisión real de Qwen3-8B, ALIA Legal, Salamandra y Llama opcional desde el Hub oficial; las entradas originales del encoder/reranker permanecen iguales. Salamandra/Llama requieren acceso manual y no se presume autorización. Los conteos reales de los modelos nominales 8B requieren aclarar elegibilidad antes de entrega competitiva.
- La generación real se prepara en `kingscode/generation/` para conservar los módulos, salida y fingerprint del dummy. El backend implementa el protocolo existente, es lazy, usa snapshots locales con hashes, prohíbe remote code y conserva las guardas. No se descargaron decoders.
- Prompts lógicos `grounded-formats-v2`, template nativo de cada tokenizer, Qwen sin thinking; parámetros greedy explícitos comunes. Formato/JSON/citas/contexto inválidos abortan el experimento, sin truncar ni editar la respuesta. El router sigue basado en reglas, sin prompt/modelo generativo.
- Se separa la medición de retrieval de la comparación de decoders: rankings públicos medidos → freeze de ocho evidencias por pregunta → mismos datos para D1–D4. Se evita mantener retrieval y decoder juntos en VRAM. Los tiempos de generación no se presentan como latencia end-to-end en vivo.
- BF16 primero, contexto total 8192 y batch 1 preparados; fit/latencia no verificados. INT8/4-bit requieren registro de OOM BF16 de la misma configuración y evidencia, y nunca se activan automáticamente. El plan de entorno no escoge una build CUDA sin diagnóstico ni instala paquetes.
- La última instrucción del usuario reemplazó la ejecución de verificaciones por preparación sin pruebas. Se añaden 28 tests y dos comandos de verificación, **no ejecutados**. No se declara Gate 2A/2B ni bakeoff completado; los resultados previos A/1B se conservan como históricos.

## 2026-09-28 — v0.6 (Member A knowledge layer: metadata + retrieval)

- Se agrega una capa de derivación determinista (`kingscode/metadata.py`) con identidad canónica independiente de la URL: `canonical_document_id` (p. ej. `ley:1564:2012`, `decreto:410:1971`, `codigo_civil`, `constitucion:1991`, `corte_constitucional:c355:2006`, `corte_suprema:sl3385:2022`) y `canonical_fragment_id` en un espacio de nombres separado (p. ej. `ley:1564:2012:articulo:391`). Las variantes históricas o los encabezados de artículo repetidos se mantienen distintos. No cambia `corpus.py` ni el build; el corpus se reconstruye byte a byte idéntico (mismos hashes que v0.1).
- Metadatos v0.6 aditivos y opcionales: `content_hash` (solo cuerpo semántico, excluye `text_prefix`), `status_assertion`/`status_source_passage_id`/`effective_from`/`effective_to`/`version_date`. La validez legal nunca se infiere: por defecto `unknown`/`null` salvo evidencia explícita de la fuente. No se introduce ningún puntaje de autoridad arbitrario. La procedencia técnica (hash, HTTP, ruta, timestamp) se mantiene fuera del texto de embedding.
- Se separan explícitamente tres planos: metadatos de documento, metadatos de pasaje y **scores de recuperación en tiempo de ejecución** (`bm25_score`, `dense_score`, `rrf_score`, `reranker_score`, `graph_score`, `final_score`), que no se persisten como metadatos del corpus.
- Fase 1: se clasifican los 28 objetivos de adquisición no resueltos (`kingscode/acquisition_backlog.py`) en `resolved`/`not_found`/`ambiguous`/`source_unavailable`/`identifier_suspect`, conservando procedencia y notas. Nunca se sustituye una norma/año/número/decisión similar ni se corrige un identificador dudoso; los sospechosos se marcan para revisión humana. Resultado: 14 `source_unavailable` (Corte Suprema sin resolver verificado), 11 `not_found`, 2 `identifier_suspect`, 1 `ambiguous`.
- Fase 4: deduplicación y diversificación (`kingscode/diversify.py`) agrupables por `canonical_document_id`/`canonical_fragment_id`/`content_hash`. La diversificación es configurable, apta para ablación y **no** se activa por defecto; la procedencia de espejos duplicados se conserva, no se descarta.
- Fase 5: taxonomía de fallos de recuperación (`kingscode/failure_analysis.py`): `corpus_missing`, `correct_document_wrong_passage`, `wrong_document`, `ranking_failure`, `graph_failure`, `ambiguous_ground_truth`, más `success`. No se fuerza una clasificación cuando `legal_basis` es incompleto o contradictorio. Se añade `document_mismatch_rate` (definición propia; no se afirma equivalencia con una métrica académica DRM).
- Fase 6: experimentos R6/R7/R8 opcionales (`kingscode/metadata_experiments.py`) sobre la API pública `retrieve(...)`, sin tocar R0–R5 de B ni cambiar la ruta por defecto. Para referencias explícitas se usa localizador estructurado exacto + recuperación general → unión de candidatos → ranking; los rasgos de metadatos son priores suaves, nunca filtros duros. Registrados en `config/experiment_matrix.json`.
- Fase 7: representación de embedding experimental (`metadata.embedding_representation`) con encabezado Norma/Ley/Artículo/Título; excluye sha256, ruta, HTTP, bytes y `retrieved_at`. Es un experimento, no un reemplazo medido de la representación actual.
- Fase 8: se confirma que toda relación normativa del grafo conserva `source`, `target`, `relation`, `evidence_passage_id` y procedencia (`method`); 0 aristas sin evidencia. Estados temporales `current/historical/repealed/modified/unknown` solo con evidencia; por defecto `unknown`.
- Fase 9: reporte de cobertura v0.6 (`reports/corpus_coverage_v06.json`) que no usa el conteo de documentos como proxy de calidad.
- Verificación: 132 tests (16 A históricos + 44 nuevos v0.6 + 44 B + 28 GPU) en verde; dos verificaciones independientes con reconstrucción byte a byte y recomputación de métricas. Archivos oficiales (19) intactos; implementación de B intacta; sin GPU/bakeoff/RAGAS/fine-tuning; sin indexar `expected_answer`/`legal_basis`.
- La hipótesis de que el corpus deba responder casi cualquier pregunta del dominio se trata solo como hipótesis de diseño, no como requisito oficial del reto.

## 2026-09-28 — Internal retrieval benchmark v1 (Member A)

- Se crea un benchmark interno de recuperación separado del sample oficial: 200 casos deterministas derivados de metadata/pasajes oficiales (120 dev, 40 validation, 40 holdout; 20 por área). Preguntas y gold se guardan en archivos separados; `retrieve` recibe exclusivamente el texto de pregunta y los gold se cargan solo después de capturar rankings. No se usó un modelo cerrado ni se fabricaron preguntas semánticas: 20 paquetes de autoría quedan para revisión humana.
- Se definen métricas de evidencia a k=1/3/5/8/10, MRR/MAP/nDCG, recuperación documental, mismatch documental (definición propia), completitud de evidencia, spans, costo de contexto, subgrupos y bootstrap pareado determinista (seed 0, 10.000 muestras). Holdout tiene declaración preautorizada únicamente para R0 baseline; selección posterior exige registro de validation y cada variante se consume una vez.
- R0 BM25 se ejecuta sobre los tres splits. En validation: Evidence Completeness@8=0.575, Recall@10=0.625, MRR@10=0.3739, nDCG@10=0.4331, Document Mismatch=0.10. El holdout R0 es baseline predeclarado, no tuning ni confirmación de selección.
- R0 graph AUTO/ON y R6/R7/R8 con backend BM25 se registran solo como diagnósticos: no cumplen la definición R3-based y no pueden seleccionar arquitectura. AUTO no cambia Recall/Completeness; ON no mejora Recall/Completeness. El diagnóstico R6-BM25 mejora dev, pero requiere repetición correcta sobre R3 antes de cualquier conclusión. R8-BM25 degrada las métricas del diagnóstico.
- No existe reporte/configuración/index BGE-M3 reproducible en el repo; los valores proporcionados por el usuario se conservan como `user-reported`, no evidencia reproducida. Qwen dense, BGE, híbridos, reranker y R3–R8 reales quedan `GPU_BLOCKED` con prerequisitos exactos. Por tanto no se selecciona arquitectura ni se congela evidencia para B; tampoco se ejecuta confirmación oficial-50 posterior a selección.
- Se preservan resultados negativos/bloqueados y se prohíbe usar el sample oficial para desarrollo del benchmark interno. La siguiente decisión depende de comparaciones same-ID en la 4090, no de preferencia previa.
## 2026-09-28 — Corrección del abort-on-citation en `Pipeline.run`, consolidación de contexto de B

- **Hallazgo (Esteban, verificado contra el código real, no contra documentación):** con un decoder real conectado (`HFDecoder`, ya preparado en Gate 2-Prep), la primera cita sin respaldo generada por el modelo hace que `citation_guard` levante `CitationGuardError`. Esa excepción se propaga sin capturar a través de `Pipeline.run` hasta el bucle `for question in questions` de `run_experiment`, que la deja subir sin publicar `submissions.jsonl` para NINGUNA de las 992 preguntas (política registrada el 2026-09-27: "JSON/schema/citas inválidos abortan la corrida... no hay publicación de un JSONL final parcial"). El sábado, con un decoder real generando texto libre, esto es virtualmente seguro que ocurra al menos una vez en 992 ítems y dejaría al equipo sin entrega.
- **Corrección de arquitectura (requiere revisión cruzada de Luis, integrante A, antes del día de GPU):** se modifica únicamente `Pipeline.run` (`kingscode/reasoning/pipeline.py`) para capturar `CitationGuardError` y, solo ahí, sustituir la fila rechazada por una abstención construida con `abstention_row` sobre la misma evidencia — exactamente el mecanismo que el anexo B.5 del enunciado pide ("verificar que toda norma citada aparece en la evidencia y, si no, suprimir la citación"). **No se toca** `citation_guard`, `_answer` ni la función pública `answer()`: siguen lanzando `CitationGuardError` exactamente igual que antes para cualquier llamador directo, por lo que las pruebas de integridad de evidencia (`test_decoder_cannot_mutate_evidence_to_create_support`, todas las de `GuardSchemaTests`) no cambian. Tampoco se toca el comportamiento ante `SubmissionValidationError` (JSON/schema inválido sigue abortando la corrida sin publicar; ver `test_failed_run_is_registered_without_final_submission`), porque esa es una señal de bug del decoder, no de una cita jurídica cuestionable, y el equipo no ha revisado si debe tratarse igual.
- Se añade `test_unsupported_citation_falls_back_to_abstention_instead_of_aborting_batch` en `tests/test_reasoning.py` y `citation_guard_fallbacks` a las métricas de `run_experiment`, para que quede medible cuántas veces se activa esta salvaguarda en una corrida real.
- **Pendiente, NO aplicado en esta sesión (dejar para revisión de Luis):** `citation_guard` exige, cuando la cita incluye artículo, que ese artículo aparezca también de forma literal en el texto del pasaje (`kingscode/reasoning/guards.py`, filtro extra sobre `supporting_passages`). El evaluador oficial (`scripts/citations.py::score`) solo compara a nivel de cuerpo normativo (`bodies()`), ignorando el artículo por completo. Eso significa que hoy rechazamos como "sin respaldo" citas que el evaluador SÍ pagaría (ej. "artículo 5 de la Ley 1010 de 2006" cuando el pasaje recuperado es el artículo 1 de esa misma ley). Bajar esa exigencia a nivel de cuerpo aumentaría el techo de puntaje de citas sin debilitar la protección real, pero es un cambio a la semántica de coincidencia que Luis diseñó y probó extensamente (16+ tests en `GuardSchemaTests`); se documenta aquí para decidirlo en conjunto, no se aplica unilateralmente.
- **Consolidación de contexto de B:** se integran al árbol canónico los materiales sueltos que traía Esteban en `kingscode_b/` y `kingscode_claude_context_files/` (ambos sin commitear, fuera de la estructura del repo): `CLAUDE.md`, `.claude/commands/`, `docs/B_FINDINGS_2026-09-28.md`, `docs/B_EXTENSION_PLAN.md`, `tools/analyze_citation_ceiling.py` y dos carpetas de prototipos de referencia (`docs/reference_b_prototype/`, `docs/reference_esteban_prototype/`) que documentan ideas pero no se importan al pipeline competitivo. Se construye `interfaz/app.py` (Streamlit) contra el pipeline real (`kingscode.reasoning.Pipeline` + `kingscode.Retriever`), con la identidad visual de Software Colombia, cubriendo el entregable de interfaz que seguía en cero. Se corrige `docs/TEAM_SPLIT.md`, que describía tareas de A/B ya completadas como si fueran "ahora".

## 2026-09-28 — T3/T5/T7 de `docs/B_EXTENSION_PLAN.md`

- **T3, política de abstención mínima:** `kingscode/reasoning/policy.py` gana `blocking_reasons(assessment, format)`, que separa razones "duras" (vacío/conflicto/evidencia no vigente) de razones blandas (referencia exacta ausente, consulta ambigua, vigencia no certificada, solapamiento léxico débil). `multiple_choice` nunca bloquea antes del decoder — adivinar entre opciones dadas supera a abstenerse incluso al azar, según la propia aritmética del enunciado (sección 6.1). Texto libre conserva el bloqueo solo para las razones duras; el resto pasa a `trace["warnings"]` y el decoder lo intenta, protegido por la red de seguridad de citas del punto anterior. `assess_evidence(...).sufficient` y `route_graph` (que lo consume para decidir expansión de grafo) no se tocaron: siguen considerando todas las razones, es un concepto distinto al de bloqueo de abstención.
- **T5, recuperación con opciones en cerradas:** `pipeline.py` gana `query_variants()` (una consulta por opción para `multiple_choice`, orden determinista) y `rrf_merge()` (fusión por rango recíproco sobre los pasajes que A ya devolvió, sin tocar sus internals ni mutar los pasajes). Con una sola variante (cualquier formato sin opciones) la llamada a `retrieve()` es idéntica byte a byte a la de antes. No se pudo medir el efecto real en recall/exactitud: requiere el corpus real, no disponible en esta máquina.
- **T7, entregables sin GPU:** `run.sh` (comando único: instala dependencias, exige o construye `corpus/`, corre tests, Gate 1B smoke y `scripts/evaluate.py --split sample`), `Dockerfile` + `.dockerignore` para la verificación de reproducibilidad en contenedor limpio, y secciones nuevas en el README (`## Comando único de reproducción`, `## Corpus e índice`). No se pudo ejecutar de punta a punta en esta máquina por falta de `corpus/` local — se verificó sintaxis de bash y del snippet Python embebido únicamente.
- **T6, throughput/concurrencia, deliberadamente no implementado:** requiere medición real (GPU + corpus) para no introducir bugs silenciosos en la guarda/citas deterministas; se deja documentado como bloqueado en vez de escribir concurrencia sin poder correrla, siguiendo la regla propia de `CLAUDE.md` de medir antes/después de cualquier cambio de calidad.
- Verificado con `python -m unittest discover -s tests -v`: 91 tests, OK (5 se saltan sin `corpus/` local). Nuevos tests: `test_multiple_choice_never_pre_blocks_on_soft_evidence_reasons`, `test_free_text_still_hard_blocks_on_empty_retrieval`, `test_query_variants_one_per_option_sorted_else_base_only`, `test_rrf_merge_boosts_passages_ranked_in_more_lists`, `test_multiple_choice_fans_out_one_retrieve_per_option_and_fuses_rrf`.

## 2026-09-28 — A v0.2 después del freeze GPU (60ebf7e)

Se reconoce el freeze RTX 4090 y se cierra validation v1 al tuning. Search V2 muestra empates con locator incluso sin boost de metadatos. Se productiviza parsing → identidad canónica → fragmentos → unión de candidatos antes del reranker; no se selecciona metadata_scale=1.25. La clase Retriever conserva defaults históricos para replay; la función pública añade locator y desactiva expansión AUTO en su perfil CPU; ON explícito conserva la expansión acotada del contrato. Los pesos neuronales siguen siendo explícitos.

Se preserva corpus-v0.1 byte a byte; corpus-v0.2 será un árbol separado. Benchmark v2 empieza con schema/piloto técnico determinista y una cola humana para escenarios/temporalidad/excepciones. Ningún modelo cerrado redacta preguntas competitivas. R0–R8 siguen siendo ablaciones, no un catálogo excluyente de arquitecturas finales. Composición, selección inmutable, confirmaciones autorizadas y freeze top 8 se decidirán con nueva evidencia v2. No se cambian B ni sus prompts.


## 2026-09-29 — Benchmark v2 independent source gate and international layer

- Se cierra benchmark v1 a tuning. El piloto v2 derivado de captions del corpus es solo smoke técnico: seis exposiciones DEV registradas, cero preguntas independientes, cero gold v2 independiente y cero SEALED_EVAL. Sus métricas no seleccionan arquitectura.
- El schema v2 admite RETRIEVAL_GOLD con conjuntos mínimos alternativos y END_TO_END_ONLY sin etiquetas de retrieval; las filas actuales se identifican como TECHNICAL_PILOT_ONLY. La recuperación no recibe gold.
- Las URLs oficiales de los PDFs ICFES localizados retornaron 404 en verificación directa; SIRNA confirma que existe una guía, sin banco público de ítems verificado. No se inventan preguntas para cumplir cuotas.
- Se añade inventario internacional selectivo de candidatos CAN/OIT/interamericano. Ratificación o aplicabilidad permanece pendiente de verificación para cada instrumento; no se indexa automáticamente. Benchmark internacional: cero ítems.
- Corpus-v0.1 queda inmutable. Corpus-v0.2 tiene cuatro documentos provisionales y las remediaciones G01/G02/C01/P02/P01/D01 aún no están completas; cada cambio requiere fuente primaria, fixture y prueba.
- Sin gold independiente no existe baseline útil ni distribución de fallos para escoger experimento. La siguiente ejecución será un baseline no ajustado sobre DEV externo revisado.

## 2026-09-29 — Diagnósticos de vistas y estado de remediación A v0.2

- El checkout remoto de `feat/member-a-corpus-v02-locator` estaba limpio en 790bf85. La suite completa pasó con 210 tests después de proporcionar `jsonschema==4.26.0` desde un directorio temporal ignorado; la primera invocación sin esa dependencia falló al importar siete módulos/casos.
- Se implementan métricas puras para Oracle Multi-View Recall, Fusion Loss y Graph Recovery Rate sobre `minimal_evidence_sets`, incluyendo alternativas. Las pruebas verifican alternativas, pérdida de fusión y recuperación condicionada a misses iniciales. No hay ranking/gold independiente; no se reportan valores empíricos ni baseline.
- Los seis hallazgos G01/G02/C01/P02/P01/D01 siguen pendientes. Se registra explícitamente qué evidencias no están en el snapshot. No se cambia v0.1 ni se intenta arreglar el parser por heurística. El grafo v0.2 permanece provisional: 29 `CONTIENE`, cero aristas semánticas activas y cero relaciones revisadas.
- El piloto existente contiene 12 casos corpus-derivados, no independientes ni seleccionables. No se amplía a 20–30 hasta revisar la estructura de las fuentes v0.2; esto evita convertir errores potenciales de parsing en diagnósticos supuestamente correctos.
- No se autoriza un experimento de retrieval: todavía no hay preguntas independientes aceptadas en DEV ni distribución de fallos. Próximo paso recomendado: obtener fuentes oficiales faltantes para las correcciones estructurales y continuar intake de assessment externo accesible; luego revisar bytes/fixtures antes de parser y benchmark.


## 2026-09-29 — Corpus v0.2 source-backed parser repairs and assessment intake update

- Preserve four primary legal sources in `corpora/corpus-v0.2/raw/` with URL, TLS/HTTP metadata and SHA-256 recorded in the v0.2 manifest. These are audit sources; the existing four-document/72-passage v0.2 snapshot was not rebuilt. Corpus v0.1 remains unchanged.
- Add v0.2-only corrections for publisher TOC rows (G02), repeated decision headings (C01), split statute headings (P02), and article termination at a major hierarchy heading (P01). Regression fixtures are checked against exact extracted blocks from the preserved bytes. The parser keeps PDF-specific safeguards when operating through the sanitized-block path.
- Leave G01 semantic relationships and D01 document identity review open; no semantic edges or automatic content-based document merges are activated.
- Official ICFES PDF origins remained unavailable; record indexed-only evidence without ingesting questions. The current SIRNA guide contains illustrative examples but its terms prohibit reproduction/transformation; no assessment examples are copied into benchmark assets. An ICFES 2021 source-rendering exposure is logged as validation candidate only.
- No independent retrieval gold was admitted. The baseline gate remains closed until at least 10 reviewed independent items exist.


## 2026-09-29 — Member A official-source runtime block and G01 candidate review

- The original ICFES Gestión del Conflicto 2026 and Comunicación Jurídica 2021 PDFs, current official module candidates, and the official toolbox landing URL were retried using browser navigation and browser-compatible headers. HTTP 404 in this runtime is recorded as `RUNTIME_ACQUISITION_BLOCKED`, because official ICFES index entries confirm the resources exist; indexed content is not accepted as original bytes.
- Added a hash-gated local intake helper targeting ignored `tmp/official-source-intake/`. It checks the recorded source ID, official ICFES host, input path, PDF signature and SHA-256 before indicating that local extraction may begin. Hash verification alone does not establish authenticity or usage rights.
- Reviewed the seven G01 candidate edges against the exact official containing-source text and recorded source URLs/hashes. Rejected the seven wrong containing-passage targets. The corrected target/modifier claims remain unresolved until their referenced legal instrument bytes are acquired; zero semantic edges are active.
- Added a D01 regression for equal content hashes across distinct canonical legal identities; broader provenance audit remains open.
- Independent extracted questions and retrieval-gold remain zero; no baseline or retrieval experiment is justified. No v0.1 or Member B files changed.

- Validación de esta continuación (segunda pasada final): 226 tests PASS; `python tools/benchmark_v2.py check` PASS con 10 hashes y holdout sin parsear; `python tools/verify_member_a_v02.py` PASS con 19 archivos oficiales, 326 archivos raw/clean v0.1 y 18 hashes v0.2. Sin GPU ni baseline.
- Precisión de adquisición: el PDF ICFES Gestión del Conflicto 2026-2 de mayo es una guía de orientación listada en el catálogo oficial, no un cuadernillo de preguntas. Se excluye de la intake de ítems; la fuente de preguntas original de febrero permanece confirmada por indexación oficial pero bloqueada por 404.
- Validación tras separar el PDF de orientación: tercera suite completa de esta continuación, 226 tests PASS; `benchmark_v2.py check` PASS (10 hashes, no holdout); verificador de snapshot PASS.


## 2026-09-29 — KC-COL-IR-v0.1 institution-family isolation

- Create a separate cross-institution benchmark: Externado DEV; Universidad Libre validation-only; ICFES/SIRNA sealed/future. Never use institution family to fill another split. Topic guides count for coverage only.
- Mechanical acquisition of the official 2011 Externado Civil Procedure bank yields 270 numbered candidates, but extraction glyph damage means exact wording remains unverified. Do not accept or run retrieval on them until human transcription/option QA and independent primary-law/temporal review.
- Hash-sample 30 before retrieval. Freeze the >=10 accepted DEV retrieval-gold gate. First comparison uses C0 BM25/C1 Qwen dense/C2 RRF/C3 hybrid+Qwen reranker, same candidate depth, graph OFF. No GPU execution in this acquisition session.
- Historical Universidad Libre sources are `VALIDATION_CANDIDATE`; URLs currently return HTML, not verified PDF bytes. Do not parse/score until DEV architecture selection.


## 2026-09-29 — Prioridad de fuentes recientes para KC-COL-IR-v0.1

- Reorientar DEV candidato hacia JEP: la página oficial de preguntas contiene 62 ítems de la tercera edición (2025), aunque la página institucional ya anuncia la cuarta edición 2026. No fechar los ítems 2025 como 2026. La edición JEP 2026 queda discovery-only hasta que publique preguntas verificables.
- Congelar 30 ítems JEP por hash antes de retrieval, con texto/respuesta en pool local ignorado. Todos siguen `NEEDS_HUMAN_REVIEW` y `UNCERTAIN`; primero separar aclaraciones puramente fácticas, cuestiones jurídicas no respondidas y casos útiles para retrieval implícito. Sin gold admitido.
- Mover el muestreo Externado 2011 a reproducibilidad-only, preservando los 30 IDs, selección y pool sin reemplazarlo ni mezclarlo con DEV.
- Registrar Javeriana Moot Seguros 2026 como validation candidate. Solo se verificó firma/hash de un PDF oficial de respuestas; no se parseó ni se inspeccionó rendimiento. La publicación advierte que algunas respuestas pueden inferirse del caso o reservarse al análisis de los equipos.
- Mantener baseline/CUDA bloqueados hasta >=10 gold DEV recientes aceptados con evidencia primaria y revisión temporal. No seleccionar ítems por métricas de retrieval.


## 2026-09-29 — KC-COL-IR gold is corpus-independent

**Decision:** establish accepted gold only from independently verified external primary evidence and frozen minimal evidence sets; evaluate frozen-corpus coverage as a separate annotation. A valid accepted gold may be COMPLETE, PARTIAL, MISSING, or AMBIGUOUS. Ranking metrics use only COMPLETE cases; coverage and failure taxonomy use all accepted gold. `corpus_missing` is never converted into a ranking failure. No retrieval output may guide item selection, evidence-set design, or review.

**Current review:** all 30 deterministic JEP 2025 items were dispositioned from exact local frozen question/response bytes. Thirteen remain retrieval-gold candidates pending exact primary sources; five are explicit-reference; three factual-only; six strategy/legal questions receive no substantive official answer; three answers are insufficient. No packets accepted because sources cited by the questions were not independently verified. The acquired Case 01 Resolution No. 02 (2022) and official JEP 2025 expediente archive were hashed and identity-checked but are not substitutes for the referenced SRVR-012/voluntary-version/Auto 023 materials. Gold remains 0, no corpus coverage denominator exists, and the baseline/CUDA gate remains closed.

## 2026-09-29 — B: atribución de pasajes, sobre JSON v3, diagnósticos, contrato de bakeoff y experimento BASE vs PLAN predeclarado

- **Prompt `grounded-formats-v3` (sha256 `0cd843eedb6c6b3a0b7dfa344caec1ef23d1dfd664e3394619d746fd4cc1f0fe`, `max_used_passages=5`):** el decoder declara `pasajes_usados` (solo `passage_id` de la evidencia entregada, acotado, duplicados eliminados de forma determinista). Es interno: nunca entra a la fila oficial; viaja en `HFDecoder.last_usage["attribution"]` con estado `explicit`/`malformed`/`not_applicable`; los contratos v1/v2 y el dummy quedan como `legacy_fallback`. `citation_builder` usa solo los pasajes declarados; si la atribución es `malformed` no inventa ninguna (solo quedan las citas del decoder ya reparadas). No se afirma corrección semántica de la atribución: es uso declarado por el modelo más validación determinista.
- **Sobre JSON (solo v3, requiere revisión de Luis):** `normalize_envelope` acepta espacios alrededor y exactamente una cerca Markdown alrededor de exactamente un objeto; rechaza prosa, dos objetos, cercas anidadas, `<think>` y claves duplicadas. Registra `raw_response`, `normalized_response` y `normalization_action`. `parse_response` (contrato histórico v1/v2) sigue rechazando cualquier cerca, tal como fija `test_invalid_json_is_never_repaired`.
- **Diagnósticos sin etiquetas:** cada traza trae modelo/revisión, versión y hash del prompt, modo de recuperación, tokens, latencia de generación, VRAM si existe, acción de normalización, estado y conteo de atribución, citas antes/después de la reparación, acciones de reparación, fallback de la guarda, fuente de la abstención (`policy`/`decoder`/`dummy_backend`/`citation_repair`/`citation_guard_fallback`/`pipeline_error`), ids de evidencia entregados y usados. `BatchRunner` agrega tasas en `batch_report.json` y conserva cada traza en `items/<id>.json`. Sin umbrales derivados de la muestra oficial.
- **Experimento BASE vs PLAN predeclarado:** `docs/experiments/B_BASE_VS_PLAN_v1.json` (sha256 `c71e34973e6fbfe03a66edbe93f59ca80edc5489b709a5870076de11b6556492`), declarado antes de cualquier resultado DEV: brazos P0 (Q0) y P1 (Q0 + vistas congeladas), todo lo demás fijo, métricas de `tools/independent_ir_v2.py score()` de A, regla de selección fijada (adoptar PLAN solo si el límite inferior del IC 95 % pareado de ΔEC@8 > 0, ΔDocument Recall ≥ 0 y PLAN_ONLY > BASE_ONLY; si no, BASE). `tools/analyze_query_plans.py --benchmark kc_col_ir` pasa por el gate de A (`preflight`) y usa su scorer sin cambios. No ejecutado.
- **Contrato del bakeoff:** `kingscode/generation/bakeoff.py` valida el freeze (`load_freeze`), comprueba su SHA-256 antes y después de cada decoder y deja una tabla comparativa sin selección. `run_generation` acepta `corpus=` (default sin cambios) para ejercitarse con un corpus/freeze de fixtures; no se fabricó ningún freeze competitivo.
- **Regresión del respaldo del batch:** con fallo total del pipeline sobre `sample_50`, el evaluador oficial da 0 aciertos en cerradas aunque varias tengan clave "A": el marcador formal "A" de una abstención nunca puntúa. No se agregó ningún respaldo heurístico de letra.
- **Interfaz:** la evidencia se escapa como HTML (antes, textos como `<DISPOSICIONES COMPRENDIDAS>` desaparecían del render y era una vía de inyección de HTML); separa pasajes citados/usados de los solo recuperados; muestra motivo y fuente de abstención; la traza técnica queda tras un interruptor de depuración y nunca muestra el texto crudo del modelo.
- **Reproducibilidad:** `run.sh --fixture` ejecutado de punta a punta en esta máquina (tests de B, 50/50 filas, 0 errores del validador oficial; 5,0 puntos del dummy, no competitivo). El comando de entrega corre la suite de B, porque algunos tests de A requieren artefactos locales no versionados (`tmp/`, corpus) y fallarían siempre en un contenedor limpio. `docker run -e FIXTURE=1`: preparado, no ejecutado (daemon apagado). Reproducción con el corpus real: pendiente del snapshot de A.
- **Test de A reportado, no modificado:** `test_kc_col_ir_v01...test_inventory_and_deterministic_sample_are_valid` falla aquí con `ValueError: Local frozen JEP pool missing or changed` (lee `tmp/kc_col_ir_v0.1/pool/...`, no versionado).

## 2026-09-29 — Empaquetado del snapshot v0.1 y revisión de ramas de A

- **Snapshot v0.1 fuera de git, confirmado:** ninguna rama contiene los bytes de `corpus/`; `feat/member-a-gpu-results-4090-20260928` solo guarda rutas y hashes de la PC de Luis. Todas las ramas de Luis tienen 0 commits fuera de `main`.
- **`tools/package_corpus_snapshot.py`** (a partir del `package_snapshot.py` y `LEEME.txt` que se cargaron en `corpora/corpus-v0.2/clean/`): mismas verificaciones del script original (hashes del manifest antes, cada miembro del archivo después, fuente sin cambios al final), con tres correcciones: la raíz del repo era `parents[2]` y apuntaba a `corpora/`; la salida caía dentro de `corpora/` (versionado) y ahora va a `dist/corpus_snapshot/` (ignorado junto con `*.tar.gz`); el LEEME se genera con el hash real en vez de uno fijo. Se añade `verify` (miembros relativos bajo `corpus/`, sin `..`, hash por archivo, sin faltantes ni sobrantes) y `tools/lab_gpu_session.ps1` lo usa antes de extraer. Tests en `tests/test_package_corpus_snapshot.py` (fixture sintética; determinismo del archivo verificado en esta máquina). Hash informado por el equipo para un paquete ya generado: `fef7300c…d851`; puede variar entre builds de zlib, por eso manda la verificación por archivo.

## 2026-09-29 — Script único de GPU (`tools/kingscode_gpu_todo.ps1`)

- Reemplaza a `tools/lab_gpu_session.ps1`, `tools/subir_corpus_snapshot.ps1` y `tools/preparar_maquina_nueva.ps1`. Corre en la PC que tiene `corpus\` y GPU; trabaja en una copia limpia de `main` (`%USERPROFILE%\KingsCodeRun`) sin modificar el repo fuente; copia `corpus\` y enlaza `models\` (junction, sin admin).
- **Falso positivo corregido:** en la PC de la 4090, `dense.npy` coincide byte a byte con el freeze (`0c156c5e…8347`) pero `dense.meta.json` no (`b8498c53…`); el script anterior exigía igualdad byte a byte del meta. Ahora el índice denso se valida con las mismas reglas que `kingscode.neural.DenseIndex` (hash de vectores, hash del corpus, orden de `passage_ids`, `config/neural.json` y lock del encoder). Si el meta no coincide con la configuración actual, se publica solo BM25 salvo `-RebuildDense`.
- **v0.1 vs v0.2:** se publica corpus v0.1 porque es el único que no está en git; `corpora/corpus-v0.2` (4 documentos, 72 pasajes, `v01_included: false`) ya está versionado y es un agregado sobre v0.1, no un reemplazo.
- Flujo: validar corpus → validar denso → publicar corpus + índice + `LICENSE` (release público `corpus-v0.1-snapshot`) → CUDA en el venv → decoder bloqueado → smoke → congelar planes → `sample_50` con decoder real + evaluador oficial (sin RAGAS) → proyección a 992 → resultados y planes a la rama `lab/<fecha>`. Sin tuning, selección de decoder, benchmark v1, holdout ni RAGAS. Verificado aquí: sintaxis PowerShell y el validador de denso embebido (válido y desactualizado) sobre un corpus sintético; la ejecución real queda para la PC de la 4090.

## 2026-09-30 — Runners de GPU de B alineados con el runbook §8 (revisión)

- **Motivo:** la revisión detectó que `tools/run_b_gpu_4090.ps1` y `tools/kingscode_gpu_todo.ps1` corrían `sample_50` con retrieval `option` en vivo y congelaban planes de Qwen que nadie consumía, contra `GPU_DAY_RUNBOOK.md` §8 (decoder-smoke/sample/bakeoff solo después de la selección de A y sobre su freeze de 8 evidencias).
- **`run_b_gpu_4090.ps1`** ahora tiene dos fases. `-Phase prep` (permitida hoy): entorno/CUDA, `verify_member_a_v02`, estado del índice denso con las reglas de `DenseIndex`, descarga y verificación de pesos. `-Phase decoder`: se detiene con `BLOCKED_ON_A_FREEZE` si falta `artifacts\retrieval_freeze.json`; si existe, lo valida con `load_freeze`, fija su SHA-256 y corre `decoder-smoke` + `sample --retrieval-freeze` por decoder, re-verificando el hash antes y después de cada uno. Sin planner, sin retrieval en vivo, sin selección.
- **`kingscode_gpu_todo.ps1`**: mismos pasos [7]–[11] (sin planes, sin `batch --retrieval-mode option`, sin `git add reports/query_plans`); decoder solo con el freeze de A.
- **Elegibilidad:** candidato por defecto `alia-legal-7b` (7.768.117.248 parámetros). `qwen3-8b` (8.190.735.360) solo entra con `-IncludePendingEligibility` y queda etiquetado `pending_organizer_confirmation_not_competitive` en `SUMMARY.json`; se mantiene la decisión del 2026-09-29 de no descartarlo (el enunciado §3.1 lo sugiere), pero ningún resultado suyo se trata como competitivo sin confirmación escrita. Salamandra se agrega solo si hay `HF_TOKEN`.
- **Suspensión:** el wrapper lee el timeout AC actual (independiente del idioma de Windows), lo pone en 0 y el runner lo restaura en `finally`. No hay limpiezas: cada corrida escribe en `reports\lab_session\<UTC>_<fase>` y nunca borra. Si el worktree tiene cambios versionados, se detiene en vez de descartarlos.
- **Pesos:** `prepare_models.py --download` ya usa `allow_patterns` (pesos/tokenizer/config) y verifica contra los metadatos Git/LFS del Hub; no descarga el repo completo.
- **Verificado aquí:** parseo PowerShell de ambos scripts, `py_compile` del runner embebido, recorrido en seco de ambas fases en un directorio temporal, `member_b.py decoder-smoke|sample --dry-run` con los argumentos exactos y lectura de `powercfg`. **No verificado:** ejecución en GPU.
- **Dependencia:** los runners hacen worktree de `origin/main`; requieren que el PR #6 (`docs/mapa-del-repo`) esté mergeado.

## 2026-09-29 — Corrección de procedencia CUJ 2026 y revisión de gold KC-COL-IR

- La página oficial actual `/preguntas` y el paquete SeRVR corresponden a la cuarta edición CUJ 2026. La tercera edición CUJ 2025 fue SDSJ; el ZIP 2025 adquirido se conserva solo como prueba de procedencia y queda marcado `NOT_SOURCE_FOR_CUJ_2026_GOLD`.
- Caveat de procedencia: `/preguntas` es contenido mixto y conserva boilerplate obsoleto “2025 / Tercera Edición”. La atribución a CUJ 2026 se basa en la identidad del caso y la coincidencia de materiales exactos con el paquete oficial 2026; el paquete SDSJ 2025 no coincide. Se conservan los mismos 30 IDs/números originales, sin remuestreo.
- Se migraron los 30 IDs a `JEP-CUJ-2026-Qnnn`, conservando `legacy_question_id`, los mismos números de ítem y el SHA original de selección. No se volvió a muestrear. Externado 2011 continúa solo para reproducibilidad y Javeriana 2026 sigue sin parsear ni inspeccionar.
- El ZIP oficial CUJ 2026 (157,859,322 bytes, SHA-256 `3f9dc1765e8ea18588c13a48e1785b506f6a0c06eef3743057e2d34097d9b101`) contiene 18 miembros hash-verificados, incluida la resolución hipotética SRVR-012 de 147 páginas y las versiones voluntarias de Ainhoa y Laureano. No sustituirla por la Resolución real No. 02 de 2022. El Auto 023 independiente no aparece como miembro separado.
- Disposición de los 30 ítems: 9 `ACCEPTED_RETRIEVAL_GOLD`, 7 `PENDING_PRIMARY_EVIDENCE`, 8 `REJECTED_INSUFFICIENT_AUTHORITATIVE_ANSWER`, 6 `REJECTED_NOT_RETRIEVAL`. Q045/Q049 quedan en el grupo duplicado `EL_BILLAR_DATE`. El objetivo de 10 no justifica aceptar evidencia incompleta.
- Los 9 gold tienen evidencia externa primaria separada de IDs del corpus; el inventario/texto completo de los 26,558 pasajes de corpus-v0.1 no contiene las fuentes/personas del caso. Cobertura: 0 COMPLETE, 0 PARTIAL, 9 MISSING, 0 AMBIGUOUS; ranking_n=0.
- Se corrigió el runner para exigir >=10 gold y, separadamente, >=10 gold COMPLETE antes de ranking/CUDA. El test cubre 30 candidatos, 10 gold válidos y 20 candidatos pendientes, así como exclusión de IDs de evidencia externa de métricas puras. Solo verificaciones CPU; retrieval y CUDA no ejecutados.


## 2026-09-29 — CUJ expansion and controlled corpus profile

- Preserved the original 30 selected CUJ item numbers and froze `EXPANSION_BATCH_1` as the next 10 IDs by the same SHA-256 ordering before reading their content. The pool hash is `af07237db321115562da4d64527c675d2bb99fe49c730b5f1ebcf2ac3bf85476`; expansion selection hash is `dc1332cb1477f96ea2652f2699befc317f4e053b67e8b8d987ef9397ecf13131`. All 10 received separate dispositions; only Q025 was accepted.
- Gold now totals 10 and GOLD_GATE is unlocked. IDs: Q009, Q012, Q013, Q025, Q030, Q031, Q037, Q043, Q045 and Q049. Competitive corpus-v0.1 independently remains MISSING for all 10 (100% missing rate).
- Defined `KC-COL-IR-CUJ2026-CONTROLLED-v1` from all six textual PDFs in the complete official 2026 ZIP, not from the gold-document list. The 18-member archive inventory includes two excluded MP3s and all metadata members; extraction verified 191 physical pages and 190 nonempty page passages. Archive SHA-256: `3f9dc1765e8ea18588c13a48e1785b506f6a0c06eef3743057e2d34097d9b101`; in-memory passage hash: `019dee8a805e87fbacfce45cd448f4b538b921d6d7c5aa7ff3a82a5472a894ef`.
- Separate external evidence units, controlled page mappings, and competitive corpus coverage in independent ledgers. Controlled mappings are page/source verified for 10/10, but passage file is not materialized in this worktree; ranking execution remains locked, ranking_n=0 in the manifest, and CUDA_READY=false. No retrieval, neural ranking, CUDA or validation inspection was performed.


## 2026-09-29 — Materialized CUJ controlled profile (pre-ranking freeze)

- Materialized the already-frozen six-PDF CUJ 2026 corpus under ignored `tmp/kc_col_ir_v0.1/controlled_cuj2026_v1/`; the 18-member archive was fully inventoried, including two excluded MP3s and archive metadata. No source bytes are tracked.
- Verified 191 physical PDF pages and 190 nonempty page passages. `passages.jsonl` SHA-256 is `c942cdfe6ec7f0c88ea0ebe4977540a99b93d98d3404b2972f9609b4499b3a7c`; runtime manifest SHA-256 is `5bcb56f772c6f502d79c41cfef684e61e82b7cd13c7c3c442e35c73730974d3f`; BM25 index SHA-256 is `277184f3a954de79746589b1e28c932cd2d557bfc2a3e52fe9ab130d7e406a87`; corpus fingerprint is `9569be4855bc9223eb346280de21d14b080da8e9b73aa9353175d59345492056`.
- The previously reported `019dee8a...` hash is reproduced exactly by serializing the same passage rows without the explicit `member_index` provenance field. The new canonical JSONL hash includes `member_index`; the earlier value was preserved as a distinct schema/hash record, not overwritten.
- All 24 external-evidence mappings across 10 accepted questions resolve to 18 unique real passages with matching source member, document and physical page; all 10 minimal evidence sets resolve. Competitive corpus-v0.1 remains 10/10 MISSING (Missing Rate 1.0).
- CPU BM25 construction and reopen through `Retriever` passed; tokenizer version is `accent-fold-unicode-words-1`. `GOLD_GATE=UNLOCKED`, `RANKING_GATE=UNLOCKED` (ranking_n=10), `retrieval_benchmark_ready=true`; `CUDA_READY=false` and `cuda_execution_started=false`. No retrieval query, C0-C3, dense model, reranker, CUDA or validation inspection ran.

## 2026-09-30 — Pre-CUDA hardening para KC-COL-IR CUJ 2026

- Se trabaja desde `codex/pre-cuda-hardening`, creado por fast-forward limpio desde `main` `e52816145970adddc70300b1a9988c02b4cd1c8d`. El gate de 10 gold y 10 pasajes completos está desbloqueado, pero `CUDA_READY=false`; el handoff actual ordena parar antes de C0-C3.
- Se incorporan auditoría CPU de longitudes con tokenizers locales fijados, identidad de ejecución en reportes, Candidate@30 y métricas descriptivas de duplicación, sincronización para medir latencia neural y separación correcta de inicialización/consulta/tiempo total. El RRF conserva la identidad `passage_id` y el índice falla cerrado ante IDs ausentes o repetidos.
- La regla de shortlist de máximo dos candidatos queda preregistrada en `docs/experiments/KC_COL_IR_CUJ2026_SHORTLIST_V1.json`. Validation sigue bloqueada hasta adquirir/parsear/revisar su fuente independiente.
- No se ejecutaron tests, retrieval, CUDA, validación ni decoder. El snapshot controlado y los tokenizers fijados no están completos en este checkout; la auditoría queda lista para ejecutarse localmente cuando esos artefactos estén disponibles.

## 2026-10-01 — Qwen3-8B vuelve a ser candidato por defecto; RAGAS en pausa

- **Decisión del equipo (Esteban):** Qwen3-8B se trata como elegible porque el enunciado §3.1 lo lista textualmente como opción sugerida (`Qwen/Qwen3-8B`), igual que Llama 3.1 8B. Esto deja sin efecto la etiqueta `pending_organizer_confirmation_not_competitive` del 2026-09-30.
- `tools/run_b_gpu_4090.ps1` y `tools/kingscode_gpu_todo.ps1` corren por defecto `qwen3-8b,alia-legal-7b`, etiquetados `suggested_in_statement_3_1` y `within_8B`; `-Models` permite elegir otros. `-IncludePendingEligibility` se acepta pero ya no cambia nada.
- El resto de la revisión sigue vigente: decoder solo sobre el freeze de A, sin planner ni retrieval en vivo, suspensión restaurada y ninguna limpieza.
- **RAGAS:** no se ejecuta ni se gasta crédito de OpenRouter hasta que Esteban lo autorice con la llave de créditos que tiene reservada. Todas las corridas de B reportan el puntaje automático sin RAGAS.

## 2026-10-01 — Primer decoder real en la 4090: Qwen3-8B y el chequeo de longitud

- **Evidencia (PC de Luis, `reports/gpu_smoke_luis/20261001T141500829226Z.json`):** el smoke `gpu_smoke.py --model qwen3-8b` cargó en BF16 (pico de VRAM 18,9 GB de 24 GB; 27 tok/s de salida; 866 tokens de entrada, 280 de salida, 10,4 s). Matmul BF16, embedding y reranker Qwen-0.6B pasaron. Qwen devolvió JSON válido, `pasajes_usados` válido y una respuesta correcta y fundamentada sobre el artículo 1 de la Ley 1010 de 2006. El smoke falló con `INVALID_MODEL_OUTPUT` por una sola regla: la respuesta `semi_open` tenía 2 oraciones y `_answer_row` exigía 3–5.
- **Por qué es un error del contrato y no del modelo:** "3 a 5 oraciones, máximo 150 palabras" y "5 a 8 oraciones" son solo `description` en `schema/submission.schema.json`; ni el validador oficial ni `scripts/evaluate.py` los aplican. Rechazar la respuesta lleva a abstención: con temperatura 0, el reintento repite la misma salida, y la pregunta pierde RAGAS y citas. El enunciado (vía CLAUDE.md §4) advierte que la abstención sistemática da 5/100.
- **Cambio (requiere revisión de Luis, capa generation):** en el contrato v3, `parse_response_v3` acepta la respuesta y registra `format_warnings` (p. ej. `semi_open_sentences_2_outside_3_5`). Se ven en la traza (`diagnostics.format_warnings`) y en los agregados de `batch_report.json`. El contrato histórico v1/v2 (`parse_response`) sigue rechazando, como fija `test_format_length_rejected_instead_of_truncated`. El prompt no cambia (mismo sha256), así que el modelo sigue recibiendo la instrucción de longitud.
- **`referencia_legal` con `passage_id`:** Qwen puso el id del pasaje como referencia. No llega a la fila final: con atribución explícita, `attach_references` la reemplaza por la cita canónica ("artículo 1 de la Ley 1010 de 2006"). Queda cubierto por un test con la salida literal de la 4090 (`tests/test_member_b_gpu_findings.py`).
- **Sin reintentos inútiles:** `BatchRunner` ya no reintenta `INVALID_MODEL_OUTPUT` ni `CONTEXT_LIMIT_EXCEEDED`. A temperatura 0 se reproducen igual, y cada reintento costaba unos 10–20 s de GPU. `DecoderFailure` ahora incluye `reason` con el mensaje exacto del parser.
- **Presupuesto de tiempo, proyección y no medición:** a 27 tok/s, las 992 tardarían unas 3,75 h en el caso típico y hasta 6,2 h si cada respuesta agota `max_new_tokens`, que es justo el límite de la ventana de 6 h. Hay que medirlo en `sample_50` antes del sábado.
- **`verify_gate2_prep.py` histórico:** compara contra `254fa3a` y falla por diseño desde la integración A+B. El runbook §3 indica su reemplazo.
## 2026-10-01 — PC nueva: descarga oficial del corpus como respaldo y corpus combinado v0.1 + v0.2

- **Contexto:** en la PC nueva (`turing`, RTX 4090) el diagnóstico se detuvo en el corpus. No existe el release `corpus-v0.1-snapshot`, ni había copia del `.tar.gz`. En `corpora/` no hay scripts: la descarga de A es `tools/member_a.py acquire` (163 objetivos de `config/sources.json`) + `build`, y v0.2 vive aparte en `corpora/corpus-v0.2` (4 documentos y 72 pasajes, `provisional_not_competitive_freeze`).
- **`tools/kingscode_pc_nueva_diagnostico.ps1` [3]:** busca el corpus en este orden: archivo local (`-CorpusArchive`), release y descarga oficial con `acquire` + `build` de A. Siempre compara documento por documento los `source_sha256` contra `corpus_manifest.json` (v0.1, versionado) y deja el resultado en `RESUMEN.json`. Las fuentes descargadas que cambiaron se permiten solo como diagnóstico. El corpus local conocido de Luis (`passages.jsonl` SHA-256 `f048d30388d29235ff71a956555444f2d32b67884050f6fc4cb0f63e8d380d9f`) también se permite únicamente con `-AllowKnownLocalCorpusDrift`, y queda explícitamente marcado como no competitivo. Puede construir el dense index combinado y ejecutar BM25/dense/hybrid, reranker y Qwen3-8B sobre `sample_50`; no autoriza selección ni freeze.
- **`tools/build_combined_corpus.py` [3b]:** construye `corpus_v01_v02/` (ignorado por git) solo concatenando v0.1 y v0.2, sin reescribir textos, ids ni metadatos. Un `doc_id` o `passage_id` repetido es un error; los nodos repetidos e idénticos se conservan una vez, y ante un conflicto gana v0.1 y se cuenta. BM25 se reconstruye con `BM25Index` de A, sin índice denso; el caller puede añadirlo después. Ninguno de los dos corpus de entrada se modifica (test incluido). Las rutas relativas desde la raíz del repo se registran de forma portable. El diagnóstico usa el combinado por defecto (`-CorpusSet v01` lo evita). **No es un freeze competitivo:** v0.2 sigue provisional hasta que el equipo lo apruebe.

## 2026-10-01 — Qwen a 93 s/pregunta en la PC nueva: atención SDPA y evidencia ajustada al contexto

- **Evidencia (PC `turing`, RTX 4090, `sample_50`, BM25 k=8, corpus v0.1 + v0.2 descargado):** 33/50 preguntas en unos 50 min, 93 s/pregunta en promedio, con la GPU al 100 % y 23,9 GB usados. Las preguntas con entrada de 5.000–7.100 tokens tardaron 90–243 s de generación; la de 3.598 tokens, 20 s. `peak_reserved_vram_bytes` llegó a 46 GB en una tarjeta de 24 GB: Windows desbordó en silencio a la RAM del sistema (sysmem fallback). 23 de 33 preguntas no llegaron al modelo (sin tokens; abstención por fallo del pipeline): la entrada más la salida superaban los 8.192 tokens (`CONTEXT_LIMIT_EXCEEDED`).
- **Causa:** `HFDecoder.load` usaba `attn_implementation="eager"`, que materializa la matriz de atención completa (heads × seq × seq) en cada capa. Con 7.000 tokens son varios GB por capa.
- **Cambio 1 (capa generation, requiere revisión de Luis):** `attn_implementation="sdpa"` (constante `ATTN_IMPLEMENTATION`, registrada en `last_usage`). `torch.use_deterministic_algorithms(True)` se mantiene: si un kernel no es determinista, PyTorch falla en vez de cambiar la salida. El smoke en la 4090 debe repetirse para confirmarlo. Las salidas pueden diferir en el último bit respecto a eager, así que cualquier comparación anterior con eager no es comparable.
- **Cambio 2:** si la evidencia no cabe en `max_context_tokens` junto con `max_new_tokens`, el **prompt** omite los pasajes de menor rango, uno a uno desde el final. No se trunca texto ni se reordena. La fila oficial conserva los 8 en `pasajes_recuperados` (respaldo de citas) y la traza registra `evidence_in_prompt` y `evidence_dropped_for_context`. Si ni un solo pasaje cabe, sigue el `CONTEXT_LIMIT_EXCEEDED` de antes (test intacto).
- **Pendiente de medir:** repetir `sample_50` en `turing` con este cambio, comparando s/pregunta, abstenciones y puntaje automático sin RAGAS.

## 2026-10-01 — Diagnóstico en `turing`: `-ExactLocator` como segunda variable

- `tools/kingscode_pc_nueva_diagnostico.ps1` agrega `-ExactLocator` (apagado por defecto). Primero se mide la corrida base (BM25 + router, Qwen3-8B con SDPA) y luego se repite cambiando solo el locator exacto de A, para atribuir su efecto en el puntaje end-to-end. El nombre de la corrida y `RESUMEN.json` registran la variante.
- El script se relanza desde la copia del repo si la copia ejecutada difiere (la caché de `raw.githubusercontent.com` sirvió una versión vieja) y recuerda el origen del corpus entre corridas.


## 2026-10-01 — 31/50 `INVALID_MODEL_OUTPUT` en `turing`: Qwen omite `abstencion`; normalización mecánica v3 y límites de extensión del enunciado

- **Evidencia** (`turing`, `sample_50`, Qwen3-8B BF16 SDPA, BM25 + router): 15,2 s/pregunta (992 en 4,2 h, dentro del presupuesto de ~22 s/pregunta del enunciado B.5), pero 31/50 fallbacks `pipeline_error`, puntaje automático 15,4/50 sin RAGAS. Motivos: **29× `Expected one JSON object with boolean abstencion`** (objeto válido y completo, sin la clave `abstencion`: el prompt lista los "Campos" de cada formato y `abstencion` no está en la lista), 1× prosa alrededor del objeto, 1× `Invalid discarded options`.
- **Cambio (solo contrato v3, requiere revisión de Luis):** `_load_object_v3` trata un objeto con **todos** los campos de su formato y sin `abstencion` como respuesta (`abstencion=false`), y convierte `"true"`/`"false"` a booleano; un objeto incompleto sigue rechazado. `coerce_fields` normaliza la forma sin agregar contenido: letra elegida ("A)" → "A"), `descarte_opciones` sin la letra elegida ni letras inexistentes, listas → texto en campos de texto, `palabras_clave` en texto → lista, claves extra no reservadas descartadas. Las claves reservadas (`id`, `formato`, `pasajes_recuperados`) siguen siendo error (test de inyección intacto). Todo queda en `field_coercions` (traza y `batch_report.json`). El sobre JSON no cambia: la prosa alrededor sigue rechazada.
- **Límites de extensión (corrección):** el enunciado, paso 3, sí fija "respuesta de 3 a 5 oraciones, máximo 150 palabras" y "analisis de 5 a 8 oraciones" ("dentro de los límites de extensión indicados"); no basta con la `description` del schema. `enforce_length_limits` recorta lo que excede en el borde de una oración (post-proceso automático declarado, no edición manual). Lo que queda corto no se puede rellenar: se registra en `format_warnings` y queda como riesgo (2/50 en esta corrida).
- La traza ahora incluye `evidence_in_prompt` y `evidence_dropped_for_context`.

## 2026-10-01 — Tras 26,63/50: prompt v4 y ampliación de citas como opciones medibles; verificación en vivo simulada

- **Punto de partida** (`turing`, Qwen3-8B, BM25 + router, prompt v3, corpus descargado + v0.2): 26,63/50 sin RAGAS (cerradas 7/15, citas recall 0,551 con 0 sin respaldo, abstención 0,628), 1 fallback, 15,2 s/pregunta (992 en 4,2 h). Rescates del parser: 29 `inferred_abstencion_false`, 1 `descarte_opciones`. Advertencias: 6 semiabiertas cortas y 3 análisis cortos.
- **Regla anti-overfitting:** `sample_50` es el único set con etiquetas y es pequeño (una cerrada = 1,33 puntos). Solo se aceptan cambios genéricos justificados por el enunciado o por fallas de forma observadas, nunca por el contenido de ítems concretos. Una variable por corrida y sin umbrales derivados de la muestra.
- **`--prompt-version v4` (opt-in; v3 sigue por defecto):** lista `abstencion (false)` con los campos, exige "mínimo 3, máximo 5" oraciones (semiabiertas) y "mínimo 5, máximo 8" (análisis), y en cerradas pide la `justificacion` antes de `respuesta_correcta`. Versión y sha256 propios, registrados en la identidad de la corrida.
- **`--citation-fill` (opt-in):** completa hasta 5 citas con la evidencia siguiente en rango, después de los pasajes declarados. Solo en `referencia_legal` (semiabiertas) y `justificacion` (cerradas), que RAGAS no lee. Cada cita pasa la misma verificación de respaldo. Base: según el enunciado §6.1, una cita respaldada que no coincide con el fundamento de referencia vale 0 sin penalización, así que solo puede subir el recall. Las abiertas no se rellenan (`marco_normativo` lo lee RAGAS).
- **Verificación en vivo simulada:** el script regenera 3 preguntas entregadas (una por formato) con la misma configuración y compara normas y pasajes, igual que hará el jurado (§7; un fallo descalifica). Deja `verify_live.json` y lo resume en `RESUMEN.json`.
- **Plan de corridas** (cada una contra 26,63, un cambio por vez): `-ExactLocator`, `-PromptVersion v4`, `-CitationFill`, `-RetrieverMode hybrid`, `-Rerank` y `-Model alia-legal-7b`. RAGAS una sola vez sobre la mejor configuración, con autorización.

## 2026-10-01 — `-ExactLocator` sin reranker no cambia nada (y el pipeline es determinista)

- **Evidencia:** la corrida `qwen3-8b_bm25_locator_20261001_121024` dio `submissions.jsonl` byte a byte idéntico a la base `qwen3-8b_bm25_20261001_115247` (sha256 `3ec5651a…` en ambas; 26,63/50).
- **Causa (diseño de A, no un bug):** `Retriever.retrieve` une los candidatos del locator al pool (`candidate_union`), pero ordena por el puntaje BM25/fusionado. Un acierto que solo encontró el locator tiene puntaje 0 y nunca llega al top-k; solo el reranker puede subirlo ("Add exact legal candidates before reranking"). Los resultados del locator en la 4090 corresponden a esa combinación.
- **Consecuencia:** el script avisa si se usa `-ExactLocator` sin `-Rerank`. La comparación válida es `-Rerank` contra `-Rerank -ExactLocator`.
- **De paso:** dos corridas completas de 50 preguntas dieron el mismo archivo, lo que es evidencia directa de determinismo para la verificación en vivo (§7).

## 2026-10-01 — Blindaje antes de las variantes: SDPA en A, reranker a prueba de pasajes largos, tiempos medidos y modo sábado

- **Capa A (`kingscode/neural.py`, autorizado por Esteban):** `QwenEncoder` y `QwenReranker` pasan de `attn_implementation="eager"` a `"sdpa"` (constante `ATTN_IMPLEMENTATION`). Con eager, los pares reranker de hasta 4.096 tokens materializan heads × seq × seq por capa al lado del decoder residente (16,4 GB) en una tarjeta de 24 GB: es el mismo patrón que desbordó a la RAM del sistema esta mañana (46 GB reservados, 93 s/pregunta). Es la misma matemática, con diferencias de redondeo. Un índice denso construido con eager sigue pasando la validación de `DenseIndex` (config y lock); antes de un freeze hay que reconstruirlo con este código para que documentos y consultas compartan kernels.
- **Reranker y pasajes largos (`tools/member_b.py`):** el `QwenReranker` de A lanza `ValueError` si un par supera `max_length` (no trunca en silencio), y eso convertía la pregunta entera en abstención por fallback. `_RerankSafeRetriever` responde esa consulta con el orden de A previo al reranker (determinista: misma entrada, mismo camino) y lo marca en `retrieval.rerank_skipped`. Errores de otro tipo no se ocultan. Conserva la firma de `retrieve`, así que el pipeline sigue usando `query_views` nativo: una sola pasada de reranker por consulta, o dos si el router activa el grafo.
- **Tiempos:** cada línea de progreso muestra s/pregunta y minutos restantes. `batch_report.json` agrega `generation_ms_p50/p95`, `retrieval_ms_p50/p95`, `peak_reserved_vram_gb` y `rerank_skipped`. El script avisa si se superan 20 s/pregunta (margen bajo los ~22 s del enunciado B.5), 22 GB de VRAM o si hubo reranker omitido.
- **Modo sábado:** el mismo script acepta `-InputFile` (set ciego) y `-Resume`. Sin etiquetas no se evalúa; `BatchRunner` ya comprueba ids, duplicados y esquema, y el resultado se copia a `submissions.jsonl` en la raíz con su sha256. `-Resume` reutiliza los checkpoints de la misma identidad (probado: 48 reanudadas y 2 regeneradas).
- **Sin cambio:** la prosa alrededor del JSON sigue rechazada (test explícito del 29-sep; 1/50 en la muestra).

## 2026-10-01 — Fusión opcional de opciones y perfilado por etapa

- **Base integrada:** la rama de trabajo avanzó por fast-forward a `origin/main` en `40ca511` (PR #26). Ese commit incluye SDPA para encoder/reranker, fallback determinista del reranker para pares demasiado largos y latencias p50/p95; falta confirmar el efecto de rendimiento en la 4090 con una muestra completa.
- **Hallazgo de código:** el modo `option` de B hace fan-out para Q0 y cada opción de selección múltiple. Al combinarlo con `hybrid + rerank`, cada vista forma su pool y llama al cross-encoder por separado; con 4 opciones son hasta 5 pools. El modo experimental `--native-option-fusion` entrega Q0 y sus opciones a `Retriever.query_views`, fusiona candidatos y aplica una sola clasificación del reranker con Q0. El default de fan-out no cambia, y la opción se fija en la identidad de ejecución para impedir reanudar checkpoints de una variante distinta.
- **Optimización adicional sin cambio de ranking previsto:** `DenseIndex` codifica en lotes los query views sin cachear y guarda sus scores en una LRU de 32 vistas para evitar recodificar si el router repite la consulta. `QwenReranker` tokeniza y valida el lote completo antes de ejecutar forwards, evitando cálculo parcial cuando un par largo fuerza el fallback. El lote GPU del reranker es seleccionable como 1 o 2 sin cambiar el lock/configuración del encoder.
- **Medición:** cada passage contiene un perfil reproducible con BM25, dense, fusión, locator, grafo, reranker, candidatos, consultas/batches de dense y pares/batches del reranker. `batch_report.json` suma latencias por etapa y agrega citas soportadas/no soportadas por el guard, además de abstenciones por formato/razón. El guard verifica soporte literal/legal estructural; no prueba entailment semántico.
- **Plan:** `docs/experiments/KC_SAMPLE50_HYBRID_FUSION_V1.md` fija baseline híbrido heredado frente a fusión nativa, después candidate_k 15 y lote de reranker 1 frente a 2, con prompt v4 y citation fill como variables separadas. Mantener el corpus combinado como diagnóstico; corpus v0.1 es inmutable y v0.2 sigue provisional. RAGAS se ejecuta una sola vez sobre un perfil completo elegido.
- **No medido aquí:** ninguna corrida retrieval/CUDA/decoder ni RAGAS. No se afirma una reducción real del tiempo ni una mejora de calidad hasta la pareja de corridas en la misma 4090.
- **Barrido en la 4090:** `--candidate-k` y `--reranker-batch-size` ya forman parte de la identidad; el tamaño del lote se puede comparar entre 1 y 2 sin tocar el lock de embeddings. Se hará primero un piloto balanceado por formato para costo/VRAM y después corridas completas de 50 preguntas. No crear un `.ps1` de orquestación ni elegir calidad por el piloto.

## 2026-10-01 — Índice denso ~1 h → minutos; script de variantes rápidas

- **Causa de la lentitud del híbrido:** `build_dense` codificaba los ~26,7k pasajes en el orden del corpus, en lotes de 2 (`config/neural.json`), rellenando cada lote hasta el pasaje más largo: unos 13k lotes pequeños, casi todo relleno.
- **Cambio (capa A, autorizado):** `encode_length_sorted` ordena por largo de tokens, arma lotes hasta 32.768 tokens con relleno incluido (máximo 64 textos), codifica y restaura el orden del corpus. Mismos vectores salvo redondeo y determinista para un corpus dado. Las consultas siguen codificándose de a una. `config/neural.json` no cambia, así que un índice existente sigue siendo válido para `DenseIndex`. Un pasaje sobre `max_length` sigue fallando de forma visible.
- **`tools/kingscode_variantes.ps1`:** corre variantes de una sola variable sobre `sample_50` con `-SkipSmoke -SkipVerify` (ahorra ~2 min por variante), continúa si una falla e imprime y guarda (`comparacion.csv`) una tabla con delta contra la base 26,63 y la columna `apta` (≤ 20 s/pregunta). La configuración final se corre con `-Variantes final -Final "<flags>"`, con verificación en vivo.
- **Bug corregido (PR #27):** `--fresh` se pasaba letra por letra: `$(if …)` desenvolvía el arreglo de un elemento en un string.

## 2026-10-01 — Optimizaciones sample50, telemetría y backlog de corpus

- **Estado de medición:** el cambio se construyó desde `93f99a1` y se publicó
  en `main` como `4952482`. Las salidas
  copiadas desde la otra máquina prueban que existe una RTX 4090 y que Qwen
  cargó; no constituyen por sí mismas una corrida completa reproducible. No se
  lanzó trabajo CUDA desde este equipo ni se ejecutaron pruebas de CPU.
- **Corrección de telemetría:** en el modo legacy de opciones, B hace varias
  recuperaciones y `rrf_merge` conserva el perfil de la primera vista. Así, el
  tiempo total `retrieval_ms` es útil, pero pares/candidatos y tiempos por etapa
  subestimaban el trabajo. El cambio local agrega contadores y tiempos de todas
  las vistas legacy de cada pasada; single-view y fusión nativa conservan el
  perfil original. No cambia la lista ni la fusión de pasajes. Revisar la
  variante nativa por separado porque usa el API multi-vista de A.
- **Presupuesto de grafo:** se expone `--graph-budget` / `-GraphBudget` para
  comparar 0 y 10 sin apagar el router. El default 10 preserva la configuración
  existente; el cambio es diagnóstico y no selecciona arquitectura.
- **Método de comparación:** terminar el trabajo que ya ocupa la 4090; usar
  luego un piloto equilibrado solo para costo/fallos de runtime, seguido por
  corridas completas pareadas y evaluación oficial. Variar una dimensión por
  comparación: fusión de opciones, candidate depth, batch del reranker,
  presupuesto de grafo. Ejecutar RAGAS una vez después de seleccionar un perfil
  completo, no para seleccionar hiperparámetros. No inferir calidad del piloto.
- **Corpus:** no alterar ni reconstruir v0.1. Preparar adquisiciones separadas
  v0.2 para fuentes oficiales asociadas a q51/q247, q453, q142, q563 y q190;
  q168/q272 permanecen bloqueadas hasta localizar la fuente primaria exacta.
  Revisar temporalidad de Ley 84/89 por su modificación en Ley 2455/25. Q253
  parece un falso faltante del mapeo de referencias y debe corregirse antes de
  descargar de nuevo.
- **Estado documental:** el benchmark neuronal completo no está respaldado por
  resultados GPU versionados según la reconciliación vigente; `strategy.json`
  ahora lo marca como pendiente. Detalle de experimentos y fuentes candidatas:
  `docs/EXPLORATION_ROUTES_2026-10-01.md`.
- **Validación de este cambio:** se añadieron pruebas de fan-out y preservación
  de perfiles, pero no se ejecutaron por la instrucción de reservar validación
  para la GPU externa. Solo se hizo revisión de diff/estructura; el cambio queda
  pendiente de smoke comparativo en la RTX 4090.

## 2026-10-01 — Nuevas rutas de retrieval y JSON (optativas, sin selección)

- Añadidas ablations detrás de flags para representación estructural de búsqueda,
  instrucciones Qwen separadas, selección de roles de planes congelados, soporte
  auxiliar Q+opción con Qwen dense y constrained JSON con XGrammar. El baseline,
  texto de evidencia, corpus v0.1 y citation guard no cambian por defecto.
- `pasajes_usados` ya existía y no se duplicó. Los scores de soporte de opción
  son cosenos, no probabilidades ni entailment, y nunca seleccionan la letra.
- BGE-M3 se deja sin loader porque el snapshot oficial encontrado ofrece
  `pytorch_model.bin` y el preparador del repo solo acepta pesos Safetensors;
  no se relajó la verificación ni se cambió el lock.
- No crear entrenamiento hard-negative ni RAFT/QLoRA hasta completar gates de
  evidencia independiente, baseline de retrieval congelado, revisión de negativos
  y evaluación sellada. `sample_50` no es train ni selector de retrieval.
- Ninguna prueba local, retrieval, CUDA, generación o RAGAS fue ejecutada.
  Validar en la 4090 después de que termine la corrida externa activa y conservar
  identidad, artefactos, evaluador oficial y trazas. Ver
  `docs/EXPLORATION_ROUTES_2026-10-01.md`.

## 2026-10-01 — Instrucciones Qwen recomendadas por el equipo

- Se añadieron dos perfiles experimentales con el texto exacto propuesto por el
  equipo: `smallest_authoritative_primary_source` para el encoder y
  `direct_primary_law_support` para el reranker. Siguen siendo optativos; el
  baseline/lock no cambia. La primera comparación debe variar una instrucción
  por vez sobre la misma configuración e identidad.
- La representación `context` del proyecto es cabecera estructural determinista
  solo para búsqueda. No es SAC, que añade un resumen sintético documental, ni
  Late Chunking, que contextualiza embeddings de chunks mediante representación
  token-level del documento antes del pooling. Late Chunking no se implementa
  en esta fase.
- Sin pruebas locales ni corridas GPU; validar las opciones en la 4090. Véase
  `docs/EXPLORATION_ROUTES_2026-10-01.md`.

## 2026-10-01 — Cache exacta y métricas reales del reranker

- Se implementó una cache LRU acotada a 8.192 puntuaciones por instancia del
  reranker, habilitable con `--reranker-score-cache`; el default conserva el
  cálculo anterior. La clave incluye revisión del modelo, precisión, kernel,
  instrucción, pregunta y texto de búsqueda, para impedir reusar scores entre
  pares o configuraciones diferentes.
- El perfil informa pares solicitados/calculados, hits, duplicados, batches y
  tiempos de tokenización/forward. `batch_report.json` agrega estas métricas.
  Su oportunidad principal es la intersección de candidatos entre las pasadas
  OFF y router; si no hay intersección, no habrá ahorro.
- Se añadió prueba unitaria de la LRU y de identidad de claves; no se ejecutaron
  tests ni GPU en este equipo. Validación pendiente en 4090 comparando cache
  OFF/ON, manteniendo todo lo demás fijo.

## 2026-10-01 — Resultados de variantes en `turing` y configuración candidata

`sample_50`, Qwen3-8B BF16, corpus descargado + v0.2 (diagnóstico, no freeze), puntaje automático sin RAGAS (máx. 50):

| Corrida | Total | Δ | Cerradas | Citas | Abst. | Fallbacks | s/preg | Retrieval p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Base (v3, BM25 + router) | 26,63 | — | 9,33 | 11,02 | 6,28 | 1 | 15,2 | — |
| + locator sin reranker | 26,63 | 0 | idéntico byte a byte | | | 1 | 15,2 | — |
| v4 | 27,68 | +1,05 | 10,67 | 10,61 | 6,40 | 2 | 15,4 | 80 ms |
| **v4 + citation-fill (c1)** | **30,41** | **+3,78** | 10,67 | 12,65 | 7,09 | 2 | 15,6 | 104 ms |
| v4 + fill + reranker + locator (c2) | 27,69 | +1,06 | 8,00 | 13,06 | 6,63 | 3 | 18,5 | 10,96 s |
| híbrido solo (c3) | 23,74 | −2,89 | 6,67 | 11,02 | 6,05 | 2 | 15,2 | 410 ms |
| todo + híbrido (c4) | 30,82 | +4,19 | 9,33 | 13,47 | 8,02 | 7 | 18,7 | 10,90 s |

- **Candidata: c1 (prompt v4 + citation-fill, BM25 + router).** Mejora las tres componentes sin costo de tiempo (4,3 h proyectadas para 992). c4 está a +0,41 (ruido en 50 ítems), cuesta 3 s/pregunta más (5,15 h de 6), tiene un retrieval p95 de 11 s (reranker) y 7 fallbacks. El híbrido solo empeora y el reranker no mejora las cerradas. Ninguna corrida tiene citas sin respaldo; la verificación en vivo de c4 coincidió en 3/3.
- **Comparabilidad:** el script hacía `git pull` en cada corrida y `main` recibió 7 commits de A durante la tanda, así que c2–c4 corrieron con otro código que c1 y la base. Desde ahora `kingscode_variantes.ps1` congela el commit (`-NoPull` en cada corrida; `-Pull` para actualizar antes) y el diagnóstico acepta `-NoPull`. El sábado se corre con `-NoPull`.
- **Fallbacks restantes:** todos son prosa alrededor del JSON (2 en c1, 7 con reranker). Con prompt v4 o superior, `extract_single_object` acepta exactamente un objeto JSON de nivel superior y descarta la prosa (`normalization_action = extracted_single_object_from_prose`, respuesta cruda conservada). Rechaza `<think>`, cercas Markdown, cero o varios objetos. v3 sigue estricto, así que el test de 2026-09-29 se mantiene.
- **A, `verify_member_a_v02` "Legacy mismatch":** desde el commit de telemetría, cada pasaje lleva `retrieval.profile.*_ms` (tiempos reales), que difieren entre llamadas idénticas. El verificador compara ahora sin esos campos; el resto de la salida debe seguir siendo idéntica.
- **A, 8 tests rotos en `main`** (`test_neural_efficiency`, `test_retrieval_query_views`, `test_graph_budget...`): objetos construidos sin `__init__` o `Namespace` parciales frente a atributos nuevos. Arreglo aditivo, sin cambiar el comportamiento normal: `getattr` con valores por defecto (`retrieval_text_mode`, `search_texts`, `query_instruction`, `batch_size` desde `config`), `instruction` solo se pasa al encoder si existe, y `_pipeline` completa las opciones faltantes con `build_parser()`.

## 2026-10-01 — Análisis por pregunta de c1 (30,41): los fallbacks eran JSON truncado; cerradas a 768 tokens

Artefactos en la rama `lab/c1-30.41-20261001` (commit `18301b9`). Análisis medido con las etiquetas de `sample_50` solo fuera del pipeline.

- **Los 2 fallbacks (ids 51 y 617) no eran prosa sino JSON cortado:** ambos usaron exactamente 512/512 `max_new_tokens`. El prompt v4 pone la justificación antes de la letra, y las cerradas respondidas llegaron a 476–493 tokens. **Cambio:** `config/decoder_bakeoff.json` sube `multiple_choice` a 768 (entrada máxima observada: 7.253 + 768 < 8.192; si no cabe, el ajuste de contexto omite pasajes de menor rango). Solo afecta el tiempo de las respuestas que antes se cortaban. La extracción de prosa del PR #32 sigue útil para el caso con reranker, pero no habría rescatado estos dos.
- **Cerradas:** 8 correctas, 5 incorrectas y 2 abstenidas por el truncado. De las 5 incorrectas, en 3 la cita de referencia sí aparece en la evidencia o se cita (58, 128, 358), así que el error es de razonamiento y no de recuperación; en 748 la norma de referencia no está en la evidencia; 671 no tiene referencia parseable.
- **Citas (41 ítems con referencia parseable):** 29 citan un cuerpo de la referencia; **7 tienen la norma fuera de los 8 pasajes** (falla de recuperación o de corpus: 51, 239, 247, 563, 617, 679, 748); **5 la tienen en la evidencia pero no la citan** (218, 358, 647, 661, 865). Este último grupo es el que puede atacar B.
- **Abstención 218:** `citation_repair_emptied_required_field`: la reparación de citas vació un campo obligatorio aunque la norma de referencia estaba en la evidencia.
- **Siguiente medición:** c1 con `max_new_tokens` de 768 en cerradas sobre el commit congelado (`-NoPull`).

## 2026-10-01 — Análisis consolidado de todas las corridas; abiertas a 1.280 tokens

Detalle en `docs/ANALISIS_CORRIDAS_2026-10-01.md`.
- Todos los fallbacks restantes en `turing` son truncados por `max_new_tokens` (21 cerradas en 512, 3 abiertas en 1024). Cerradas ya en 768 (PR #33); **abiertas suben a 1.280** en `config/decoder_bakeoff.json`.
- Los errores de cerradas son estables entre configuraciones (128, 671, 748, 58): son límite de evidencia o de razonamiento, no ruido de configuración.
- Normas nunca recuperadas en ninguna configuración: ítems 51, 247, 563, 679 y 748 (trabajo de A/corpus).
- "Norma en la evidencia sin citar": la norma solo aparece mencionada dentro del texto de otro pasaje. La guarda la rechaza por diseño. Queda una **propuesta para revisión cruzada con Luis, no implementada**: citar a nivel de cuerpo las normas mencionadas en los pasajes declarados, solo en campos que RAGAS no lee.
- La PC de Luis desborda la VRAM (43–53 GB reservados, 88–252 s de generación): sus tiempos no sirven para presupuestar.
- `tools/analyze_run.py` exporta una revisión por pregunta, y `diagnostics.raw_response` guarda la salida exacta del decoder (fuera de la fila oficial; la interfaz la oculta).

## 2026-10-01 — Citas de normas nombradas en la evidencia (`--cite-mentions`) y re-puntuación offline

- **Por qué no fine-tuning ("gradiente"):** no hay datos de entrenamiento válidos. `sample_50` es el único material etiquetado y entrenar con él es sobreajuste; el enunciado prohíbe datos sintéticos de modelos cerrados, y AGENTS.md pide no ajustar el decoder antes de que el retrieval sea alto. La mejora se busca optimizando contra la regla exacta del evaluador y midiendo sin GPU.
- **`--cite-mentions N` (opt-in):** el constructor agrega hasta N citas **a nivel de cuerpo, sin artículo**, de normas **nombradas en el texto** de los 10 primeros pasajes (primero los declarados por el modelo). Excluye el documento propio del pasaje y los cuerpos ya citados. Solo en `referencia_legal` (semiabiertas) y `justificacion` (cerradas), que el juez RAGAS no lee. La guarda acepta esas citas **solo** con la opción activa (`citation_guard(..., allow_body_mentions=True)` → `mention_support`): es exactamente la regla oficial (`scripts/citations.py`: el cuerpo citado aparece en el texto de los 10 primeros pasajes). Las citas con artículo siguen bajo la regla estricta y, sin la opción, la guarda no cambia. **Requiere revisión de Luis:** relaja la guarda solo para menciones a nivel de cuerpo y solo en modo opt-in.
- **`tools/rescore_run.py`:** re-aplica el post-proceso de citas a una corrida guardada (mismas respuestas del modelo, misma evidencia) y la pasa por el evaluador oficial, sin GPU. Con `--cite-mentions 0` reproduce exactamente el puntaje original (verificado en 3 corridas).
- **Resultado offline** (real, sobre salidas guardadas; sin RAGAS; 0 citas sin respaldo en todos los casos):

| Corrida | Original | Menciones 3 | Menciones 5 |
|---|---:|---:|---:|
| c1 (v4 + fill, BM25) | 30,41 | **32,92** (citas 12,65 → 14,69) | 32,92 |
| Base v3 BM25 | 26,63 | 30,42 | 30,83 |
| c4 (híbrido + rerank) | 30,82 | 31,47 | 31,47 |

- **Regla anti-overfitting:** la regla es genérica (la definición oficial de respaldo) y no se ajustó por ítem. N = 3 se elige por ser el mínimo que satura c1. Según el enunciado §6.1, una cita respaldada que no coincide con la referencia vale 0 sin penalización; el riesgo que queda es citar normas que el pasaje solo nombra de paso, y eso no resta puntos.
- **Configuración recomendada:** `-Recomendada` en `kingscode_pc_nueva_diagnostico.ps1` (prompt v4, `--citation-fill`, `--cite-mentions 3`, BM25 + router, cerradas 768 y abiertas 1.280 tokens). Falta confirmarla con una corrida real en GPU.

## 2026-10-02 — Corrida recomendada en PC #1: 35,18/50; corpus de adiciones v1; cerradas a 1.024 tokens

- **PC #1** (rama `lab/recomendada-qwen3-8b_bm25_c30_rb2_gb10_pv4_fill_men3_20261002_111603`): `-Recomendada` (prompt v4, fill, menciones 3, BM25 + router), corpus descargado + v0.2. **35,18/50 sin RAGAS** (cerradas 9/15 = 12,0; citas recall 0,776 = 15,51 con 0 sin respaldo; abstención 7,67), 1 fallback (617, truncado en 768), 15,7 s/pregunta (992 en 4,33 h), verificación en vivo 3/3 idéntica.
- **Citas "de más":** las listas largas (hasta 8) parecen ruidosas, pero el evaluador no penaliza citas respaldadas no coincidentes. Recortarlas a k = 2/3/4/5/8 da 29,53/31,86/32,68/34,13/35,18. Se mantienen; la interfaz debe separar "citas del modelo" de "normas de la evidencia".
- **Corpus:** según el enunciado paso 5, los `legal_basis` de la muestra orientan la adquisición. De los 28 cuerpos que nombran, faltaban 4: **Ley 472 de 1998** (ítems 51, 247), **SU-277/2025** (563), **SU-16/2020** y **C-468/2024** (453). Se descargaron de fuentes oficiales (Función Pública y la relatoría de la Corte Constitucional) con `acquire_one` y se construyeron con `kingscode.corpus.build` en `corpora/corpus-additions-v1` (4 documentos, 372 pasajes; Ley 472 con 88 artículos). `build_combined_corpus.py` acepta varias adiciones y el diagnóstico usa `corpus_v01_v02_a1`. Solo se indexan textos normativos oficiales, nunca preguntas ni respuestas.
- **Cerradas a 1.024 tokens** (617 se truncó en 768). Si la entrada no cabe, el ajuste de contexto omite pasajes de menor rango.

## 2026-10-02 — RAGAS medido (0,4275); medición sin crédito: replay del post-proceso y proxy de RAGAS

- **RAGAS oficial**, una sola vez, sobre la corrida `..._20261002_111603` (PC #1): correctness **0,4275** (referencia 0,451), **12,82/30** puntos; total automático **48,00/80**. Juez `z-ai/glm-5.3-flash`, 35 ítems juzgados, 34 respondidos, 0 fallidos.
- **Política de crédito:** la llave de OpenRouter es limitada y debe alcanzar hasta el sábado. RAGAS solo sobre candidatas finales, con autorización, midiendo el saldo antes y después (`GET https://openrouter.ai/api/v1/key`). Las variantes se comparan sin RAGAS.
- **Corrida `..._20261002_115609`** (PC #1, con corpus de adiciones v1 y cerradas a 1.024): **36,93/50 sin RAGAS**, 0 fallbacks, citas 17,14 (recall 0,857, 0 sin respaldo), 563 y 617 corregidas, 528 empeoró (cerrada).
- **`tools/replay_run.py`:** re-ejecuta parser, reparación, constructor de citas y guarda sobre la **salida cruda guardada del modelo** y la misma evidencia, sin GPU. Con la configuración de la corrida reproduce el puntaje exacto (36,93). Límite conocido: el registro de evidencia no guarda `norm_number`/`year`, así que algunos alias de título ("(Decreto 2663 de 1950)") se reparan distinto; no afecta el puntaje.
- **Reparación consciente de menciones** (solo con `--cite-mentions`): una cita a una norma nombrada en la evidencia se reescribe a nivel de cuerpo en vez de borrar la oración (antes la 218 se abstenía porque la reparación vaciaba `respuesta`). Replay: 36,81 frente a 36,93 (ruido), pero responde 35/35 de texto libre en vez de 34/35 y conserva oraciones en `respuesta`, que es lo que lee RAGAS.
- **`tools/analyze_ragas_proxy.py`:** proxy gratuito de RAGAS. Reproduce la parte de similitud semántica con el mismo encoder local del evaluador (`intfloat/multilingual-e5-large`), el mismo texto por formato, abstención = 0 y el mismo denominador, y agrega un token-F1 como proxy factual. Calibración: la corrida `111603` tiene RAGAS oficial 0,4275 y token-F1 0,2665. Sirve para ordenar variantes, no para reportar puntaje.


## 2026-10-02 — Híbrido + reranker + locator (PC #2) no se adopta; BM25 queda como configuración final candidata

- Corrida `qwen3-8b_hybrid_c30_rb2_gb10_rerank_locator_pv4_fill_men3_20261002_115712` (PC #2, `5994024`, `corpus_v01_v02_a1`, índice denso de 26.447 vectores): **36,59/50 sin RAGAS** (cerradas 12,00; citas 16,33, recall 0,816, 0 sin respaldo; abstención 8,26), 1 fallback (528), **19,1 s/pregunta → 5,26 h para 992** (retrieval p95 12,2 s, VRAM reservada 20,2 GB). Verificación en vivo simulada: coincide.
- Frente a BM25 (`..._115609`, mismo commit y corpus): 36,93/50 a 15,9 s/pregunta (4,38 h). El híbrido no gana puntaje y cuesta casi 1 h más en la ventana de 6 h: **no se adopta**. Configuración candidata final: `-Recomendada` con BM25.
- `docs/REPORTE_AVANCE_BORRADOR.md` actualizado con 36,93/50 y RAGAS 0,4275 (medido una vez sobre `111603`; el total con RAGAS de `115609` es estimación y así se declara).

## 2026-10-02 (tarde) — ALIA descartado; `-Recomendada` pasa a 5 citas por menciones; `-K` en el script

- **ALIA Legal 7B** (`alia-legal-7b_bm25_..._20261002_123339`, PC #1): 50/50 fallback a abstención → 5,00/50, 24,5 s/pregunta (una pregunta con contexto de 10.600 tokens > 8.192). No apto; se descarta. (El paso [6b] falla con `--only` vacío cuando todas son fallback; cosmético.)
- **Menciones 3 → 5** (replay sin GPU sobre `115609`, misma salida cruda y evidencia): 36,81 → **37,46** (citas 17,14 → 17,55; abstención 7,67 → 7,91). 8 = 5 (satura). Solo toca `referencia_legal`/`justificacion`, que RAGAS no lee en semiabiertas ni cerradas. `-Recomendada` usa ahora 5.
- **`-K`** (1–10, por defecto 8) en `kingscode_pc_nueva_diagnostico.ps1`: el evaluador mira los 10 primeros pasajes; el prompt ya recorta por presupuesto de contexto sin reordenar. Experimento: `-Recomendada -K 10` frente a `-Recomendada`.

## 2026-10-02 (tarde) — Configuración final del día: `-Recomendada` (k = 8, 5 menciones) = 37,46/50

- PC #1 `qwen3-8b_bm25_c30_rb2_gb10_pv4_fill_men5_20261002_130759` (k = 8): **37,46/50** sin RAGAS (cerradas 12,00; citas 17,55, recall 0,878, 0 sin respaldo; abstención 7,91), 0 fallbacks, 16,4 s/pregunta → 4,52 h para 992, verificación en vivo coincide.
- PC #2 `qwen3-8b_bm25_k10_c30_rb2_gb10_pv4_fill_men5_20261002_130450` (k = 10): 37,46/50 idéntico por componente, 16,7 s/pregunta. k = 10 no aporta: queda k = 8.
- El replay sin GPU había predicho exactamente 37,46: el replay es confiable para cambios de post-proceso.
- `docs/REPORTE_AVANCE_BORRADOR.md` actualizado (37,46/50; con RAGAS ≈ 50,3/80, estimado).
- Riesgo detectado: el `passages.jsonl` descargado difiere entre PCs (#2 `a91236e4…`, #1 `2956bf2d…` en la corrida de ALIA). Para el sábado se debe usar UN snapshot congelado copiado a ambas máquinas.

## 2026-10-02 (tarde) — Interfaz unificada con la configuración `-Recomendada`

- **Síntoma (PC #1, corpus real):** la interfaz funcionaba pero se abstenía. **Causa:** el decoder por defecto del selector era `dummy_abstain` (siempre se abstiene) y la interfaz armaba su propio `Pipeline` sin prompt v4, sin `citation_fill`, sin menciones, sin retrieval por opción y con `corpus/` en vez del corpus combinado.
- **Corrección:** `interfaz/app.py` construye ahora el pipeline con `tools/member_b.py::_pipeline` (el mismo código de las corridas) y los argumentos de `-Recomendada` (BM25 + router, `option`, v4, `--citation-fill`, `--cite-mentions 5`). `qwen3-8b` es la primera opción cuando hay CUDA; `dummy_abstain` queda al final. Corpus por defecto: `corpus_v01_v02_a1` > `corpus_v01_v02` > `corpus`. Pipeline y decoder se cargan una sola vez (`st.cache_resource`).

## 2026-10-02 (tarde) — Modo `option_plan`: cerradas por opción, texto libre con plan congelado de Qwen

- **Motivo:** las 3 fallas de citas que quedan (239 Código de Comercio, 247 Ley 472, 679 Ley 1581) son normas que no aparecen en la evidencia; el texto de la pregunta no nombra la norma. El modo `plan` (planner Qwen3-8B, solo texto público de la pregunta, vistas congeladas y no confiables: sin locator) existía pero nunca se midió, y pierde las consultas por opción de las cerradas.
- **Cambio aditivo:** `retrieval_mode="option_plan"` en `Pipeline` — `multiple_choice` con opciones → exactamente las vistas de `option`; el resto → vistas del plan (vía nativa `query_views` de A). `member_b.py plan --retrieval-mode option_plan` solo planifica texto libre. Script: `-RetrievalMode option_plan` congela los planes antes del lote y suma su tiempo a s/pregunta. Test nuevo en `test_member_b_v2.py`.
- **Criterio de adopción:** total sin RAGAS > 37,46 sin bajar cerradas, y proyección para 992 (incluido el planner) ≤ 5 h; si no, se queda `option`.

## 2026-10-02 (noche) — Taxonomía de fallas, prompt v6 de razonamiento, tope por documento y fuentes verificadas (todo opt-in, sin medir en GPU)

- **`tools/analyze_taxonomy.py`** (solo medición): desglose por `area`, `formato`, `complejidad` y `sub_tarea`, con tipo de falla por ítem. Sobre la configuración final (37,46/50): `docs/TAXONOMIA_FALLAS_2026-10-02.md`. Cerradas 9/15; norma del fundamento citada 37/41; las 3 normas faltantes están fuera de la evidencia (retrieval/corpus), ninguna "en evidencia sin citar" salvo una parcial (1073).
- **Hallazgo 1 (genérico):** 8/50 respuestas discuten la evidencia en vez de responder ("la evidencia no menciona…"); 3 de las 6 cerradas falladas lo hacen antes de adivinar, y en texto libre eso deja RAGAS ≈ 0 (218, 142). Causa: `COMMON` prohíbe el conocimiento paramétrico y pide abstenerse si la evidencia no alcanza, aunque `citation_repair`/`citation_guard` ya reparan o suprimen toda cita no respaldada.
- **Prompt v6 (`grounded-formats-v6`, `--prompt-version v6` / `-PromptVersion v6`)**: mismas claves y orden que v4; solo se pueden CITAR los pasajes, pero el razonamiento se completa con conocimiento general del derecho colombiano sin atribuir número/artículo a fuentes ausentes; prohíbe frases sobre la evidencia; método genérico (problema jurídico, jerarquía, supremacía/especialidad/posterioridad, vigencia y exequibilidad, regla/excepción, requisitos/efectos, ratio/obiter); abstención solo si la pregunta no es jurídica. No contiene contenido normativo sustantivo ni nada derivado de respuestas de la muestra. **Requiere GPU** (el replay no mide cambios de prompt) y, si gana sin RAGAS, una medición RAGAS (5,46 USD).
- **Hallazgo 2:** en 12/50 ítems un solo documento ocupa ≥ 5 de los 8 pasajes (p. ej. 563: SU-277 ×8). **`doc_cap`** (`--doc-cap N` / `-DocCap N`, 0 = apagado): trae 10 pasajes y deja como máximo N por `doc_id` en orden de rango, rellenando si faltan. Apagado, las llamadas son idénticas a las corridas medidas.
- **Hallazgo 3 (corpus, capa A):** 0 decisiones del Consejo de Estado (142 pide una sentencia de unificación tributaria del CE); procesal es el área más delgada (10 docs); preguntas sobre una sentencia concreta ausente (190, T-256 de 2025) no tienen cómo responderse. Se deja a A.
- **`tools/check_sources.py`**: las 172 URLs de `corpus_manifest.json` + `corpora/*/manifest.json` responden 200, sin redirecciones (`docs/FUENTES_ESTADO_2026-10-02.md`).
- **Notas de la charla (2-oct, noche):** el test pesa más en constitucional, administrativa, penal, procesal, comercial y civil (la muestra es casi uniforme); la referencia se comparó también con BERTScore, BLEU y ROUGE-1, legibilidad y escolaridad. `analyze_ragas_proxy.py` ahora reporta BLEU-4 y legibilidad Fernández-Huerta (final: ROUGE-1 0,275, BLEU-4 0,087, legibilidad 70,2 frente a 73,1 de las referencias). El prompt v6 pide la terminología literal de las normas en oraciones claras. Detalle en `docs/RESUMEN_B_2026-10-02.md` §8.
- **v6 + control de distractores y verificación por área (2-oct, noche):** en cerradas, la justificación enuncia la regla y contrasta cada opción por separado; se descartan explícitamente los distractores típicos (verdadera en abstracto pero no responde, figura afín confundida, sujeto/plazo/cuantía/autoridad cambiados, términos absolutos, eco textual de la pregunta o de los pasajes; "todas"/"ninguna" solo tras comprobar cada opción). Listas de verificación genéricas para administrativo (competencia, procedimiento, motivación, finalidad, vicio, medio de control) y laboral (primacía de la realidad: prestación personal, subordinación, remuneración; tipo de contrato; terminación; mínimos irrenunciables), las dos áreas con peor resultado en la taxonomía. Contenido metodológico, sin artículos ni respuestas de la muestra; **Luis: revisar que no se lea como paráfrasis de normas**. El system prompt v6 crece a ~3,9 mil caracteres (~1 mil tokens): con evidencia muy larga `hf_decoder` puede mostrar un pasaje menos en el prompt (la fila oficial no cambia).
- **v6 + distinción conceptual, datos exactos y autoridad (2-oct, noche, notas de la charla):** los organizadores reportan que la relevancia no predice la corrección y que las fallas dominantes son distinción conceptual, identificación del juez/corporación y datos exactos, y corrección de las citas normativas. v6 ahora (a) exige definir cada figura y el criterio que las diferencia antes de concluir; (b) exige copiar literalmente corporación, número/año, fechas, cifras, plazos y porcentajes de los pasajes, sin aproximar ni atribuir a otra corporación; (c) añade a cada pasaje el campo `autoridad` (Corte Constitucional, Corte Suprema de Justicia, Consejo de Estado, Comunidad Andina), derivado de forma determinista del host oficial de `source_url` (`prompts.source_authority`); v4 no cambia. Las citas siguen pasando por la reparación y la guarda (0 sin respaldo).
- **Citas que no sostienen lo afirmado (2-oct, noche, notas de la charla de una startup del sector):** el juez automático coincide con expertos y es más estricto; los modelos aciertan en cerradas y fallan en el análisis jurídico de texto libre; el rendimiento cae en las áreas más complejas; hay citas a normas inexistentes y citas a normas reales que no sostienen la afirmación. Nuestra guarda ya elimina toda norma ausente de la evidencia (0 sin respaldo), pero no verifica que el pasaje citado diga lo afirmado. **`tools/analyze_citation_alignment.py`** (diagnóstico léxico, no cambia filas, excluye la lista "Fundamento normativo:" que agrega el sistema): configuración final = 119 citas argumentativas, **68,9 % alineadas, 10,9 % débiles, 20,2 % huérfanas** (norma solo mencionada de paso dentro de otro pasaje). v6 añade: cada cita en la misma oración que la afirmación que su pasaje dice expresamente, el artículo que contiene la regla y no otro, sin citar normas mencionadas de paso, y sin cita para lo que viene de conocimiento general; análisis abierto en orden hechos → problema → regla con cita → aplicación por requisito → consecuencia. Criterio para v6: tasa_alineadas sube y tasa_debiles baja frente a 0,689/0,109, además de los criterios de puntaje. `kingscode_variantes.ps1` la imprime por corrida.
- **Longitud y relevancia (2-oct, noche):** el evaluador oficial usa RAGAS `answer_correctness` = 0,75 × F1 de afirmaciones contra `respuesta_esperada` + 0,25 × similitud semántica; **no mide relevancia/pertinencia** (por eso una respuesta pertinente y fluida pero con afirmaciones de más, o con citas que no la sostienen, puntúa bajo). Análisis de longitud sobre la configuración final (proxy léxico, n pequeño): en semiabiertas el F1 sigue una U invertida respecto a la razón longitud propia / longitud de referencia (< 0,5: 0,147; 0,5–1: 0,311; 1–2: 0,363; > 2: 0,197); en abiertas corr(razón, precisión) = −0,77. 22,9 % de las respuestas de texto libre pasan del doble de la referencia, sobre todo en preguntas puntuales. v6 ajusta la extensión al tipo de pregunta (dato puntual → 3 oraciones breves; requisitos/distinción/problema → hasta 5) y exige una afirmación distinta y verificable por oración, sin repetir ni listar normas sin contenido. `analyze_ragas_proxy.py` reporta ahora `ratio_longitud_mediana`, `pct_mas_del_doble` (base 0,229) y `pct_menos_de_la_mitad` (base 0,114).
- **Área y eje de la respuesta; árbol normativo (2-oct, noche, notas de la charla):** recomiendan saber primero de qué área es la pregunta y en torno a qué gira la respuesta, y preguntarse si cada norma sirve para responder; y construir el árbol de normas por área (códigos/leyes y las sentencias que los interpretan) para buscar dentro de él en vez de entre todas las sentencias. v6: el método empieza por el área (las 10 del banco) y el eje, y antes de usar o citar un pasaje comprueba que regula ese eje y sirve para la pregunta, descartando pasajes de otra área o tema aunque compartan palabras. **Para A (recomendación, no implementado):** recuperación por área usando el grafo (59k nodos/75k aristas) y `areas` del manifiesto: clasificar la pregunta por área, restringir o priorizar los documentos raíz del área y expandir por aristas a las sentencias que los interpretan; hoy 12/50 ítems tienen ≥ 5 de 8 pasajes de un mismo documento y 3 normas del fundamento no se recuperan.
- **Tiempo jurídico, certeza y respuesta práctica (2-oct, noche, notas de la charla):** la mejor respuesta no alucina, razona jurídicamente, cuida la certeza y es práctica; depende del sistema completo (revisión de fuentes, tiempo jurídico, criterio de resolución, modelo y acceso a jurisprudencia). v6 añade: norma vigente al momento de los hechos y su transición, sin retroactividad no prevista; certeza expresada como condición ("si..., entonces...") en vez de duda; cierre práctico (qué procede, ante qué autoridad, plazo, efecto) cuando los pasajes lo permiten. **Costo:** el system prompt v6 llega a ~5,8 mil caracteres (~1,5 mil tokens); con 8.192 de contexto y hasta 1.280 tokens de salida, en evidencia muy larga `hf_decoder` muestra menos pasajes en el prompt (la fila oficial no cambia) y la latencia puede subir: revisar `s_preg` y la proyección a 992 en la corrida de v6.

## 2026-10-02 (noche) — El modelo no veía toda la evidencia: contexto de 8.192 recorta pasajes; `--max-context` opt-in

- **Medición con el tokenizador real de Qwen3-8B** (revisión fijada) sobre la evidencia entregada de la configuración final y los `max_new_tokens` del config (1.024/512/1.280): con el contexto de 8.192, `hf_decoder` deja fuera del prompt **29 pasajes en 22/50 preguntas** con v4 y **65 pasajes en 30/50** con v6 (system prompt de ~1,5 mil tokens). La fila oficial los entrega, pero el modelo no los leyó; entre los afectados están 239, 247 y 679, cuyas normas faltan en la respuesta. Con 12.288 queda 1 pasaje fuera (v6); con **16.384, 0 en ambas versiones** (prompt máximo 12,5 mil tokens; mediana 7,1 mil v4 / 8,2 mil v6).
- **Cambio aditivo:** `HFDecoder(max_context_tokens=...)` (8.192–32.768), `member_b.py --max-context N`, `-MaxContext 12288|16384` en el script; el valor por defecto sigue siendo 8.192 del config (no se toca la validación de `config.py`) y `load()` sigue rechazando un valor mayor que el contexto nativo del modelo (Qwen3-8B: 40.960). Test con tokenizador falso: 5 pasajes visibles a 16k frente a 2 a 8k; valores inválidos y contexto nativo insuficiente fallan.
- **Riesgo a medir:** latencia (prefill de ~1–4 mil tokens más) y VRAM (KV de ~12,5 mil tokens ≈ 1,8 GB sobre 17,8 GB). Variantes nuevas en `kingscode_variantes.ps1`: `ctx16k` (una variable contra 37,46) y `v6_ctx16k` (v6 solo es justo con 16k). Tanda: `-Pc 1` = ctx16k, v6_ctx16k; `-Pc 2` = option_plan, doccap3.
- **v6 + historia normativa:** ante versiones, modificaciones, derogatorias, exequibilidad condicionada o contradicciones, usar el texto vigente y la decisión posterior o de mayor jerarquía, y mencionar el cambio. (La capa A ya excluye texto no vigente: `is_current_text`.)
- **Progreso visible y polaridad sí/no (2-oct, noche):** `BatchRunner` imprime ahora una línea `[batch] -> N/M id=... generando...` al EMPEZAR cada pregunta (antes solo al terminar), para distinguir de inmediato una pregunta lenta o atascada (p. ej. VRAM desbordada a memoria compartida por otra sesión de Windows con el modelo cargado) de una consola muda. En preguntas de sí o no de la muestra, las referencias empiezan con "Sí."/"No." y nuestras respuestas a menudo no se comprometen (1065, 1073) o invierten la polaridad (513: la referencia dice que no se puede, la nuestra que sí); v6 exige empezar con "Sí" o "No" seguido de la regla y responder "No" cuando la regla lo excluye. La abstención sigue siendo casi siempre subóptima con la fórmula oficial (cerradas: solo si P(acierto) < ~7 %; texto libre: se pierde RAGAS); la corrida final tiene 0 abstenciones.
- **GPU ocupada por otra sesión (2-oct, 16:00):** con dos usuarios en el mismo PC, la tanda de variantes de Luis se quedaba muda tras cargar el modelo (ni `1/50`): la sesión anterior (interfaz Streamlit con Qwen cargado) retiene ~18 GB y la corrida se desborda a memoria compartida sin error. El paso [6] del diagnóstico ahora consulta `nvidia-smi` y se DETIENE con un mensaje claro si hay más de 3.000 MiB ocupados antes de empezar (`-AllowBusyGpu` para forzar).
- **Respaldo y guion del sábado (2-oct, 16:10):** el sábado preguntarán arquitectura y generación, pedirán regenerar respuestas (también modificadas) y conviene tener respaldo de la base. `tools/kingscode_snapshot.ps1` (`crear` / `restaurar` / `verificar`) empaqueta `corpus`, `corpus_v01_v02(_a1)`, `artifacts` y `.kingscode_corpus_origin.txt` en un tar.gz con `SHA256SUMS.txt` y un manifiesto de hash por archivo (`tools/snapshot_hashes.py`); al restaurar verifica el archivo y luego cada archivo del corpus/índice contra el de hoy. `-IncluirModelos` añade `models\` (~18 GB) por si no hay internet. `docs/GUION_SABADO.md`: preparación, corrida de 992 con reanudación, verificación en vivo (`member_b.py verify`), respuestas para preguntas de arquitectura/generación/reproducibilidad/reglas y tabla de fallas. `docs/entrega_viernes/submissions_sample50.jsonl` (37,46, 0 errores) queda como el JSON de las 50 preguntas.
- **Causa de la tanda muda (2-oct, 16:20) y corrección:** la primera variante del PC #1 era `ctx16k`. Con 16k de contexto algunos prompts llegan a ~12,5 mil tokens; con `use_deterministic_algorithms(True)` la atención SDPA puede caer en el kernel que materializa la matriz de atención, que no cabe en 24 GB, y Windows la desborda a memoria compartida sin error (el mismo fenómeno documentado en `hf_decoder` con eager: 93 s/pregunta). Resultado: la primera pregunta no termina y nunca aparece `1/50`. Correcciones: (1) `ctx16k`/`v6_ctx16k` salen de la tanda por defecto (`-Pc 1` = v6, doccap3; `-Pc 2` = option_plan) y `-MaxContext` avisa que es experimental; (2) `BatchRunner` imprime un latido cada 30 s mientras genera una pregunta (`[batch]    id=... sigue generando: N s | VRAM reservada X GB`), además de la línea al empezar y al terminar, así que una pregunta lenta o atascada nunca vuelve a quedar en silencio. El latido solo escribe en stderr; no toca el pipeline ni sus resultados. Pendiente para A/B: si se quiere que el modelo vea los 8 pasajes, recortar el texto de cada pasaje dentro de 8k en vez de ampliar el contexto.
- **Origen del 39,02 (2-oct, 16:50):** el 39,02/50 sin RAGAS es `-Recomendada` (v4, sin cambios de código) en un PC instalado desde cero con el bootstrap de `main`, que volvió a descargar hoy las fuentes oficiales: el corpus de esa máquina es más reciente que el de la mañana (37,46). Comparado `19120da` contra `main`: las diferencias de `prompts.py` están solo dentro de v6; `batch.py` solo imprime; `--max-context` y `option_plan` están apagados por defecto; `corpora/` es idéntico. Para probar todo con lo último, el corpus del PC del 39 se copia (`kingscode_snapshot.ps1 crear/restaurar`) a la otra máquina en vez de volver a descargarlo, y las variantes se comparan con `-Base 39.02`.

## 2026-10-02 (17:20) — v6 supera a v4 con el mismo corpus: candidata final `-Recomendada -PromptVersion v6`

- PC `turing`, `main` @ `7041c82`, corpus antiguo (`passages.jsonl` 49a6926e…), una variable: `-Recomendada` (v4) **37,46** → `-Recomendada -PromptVersion v6` **38,08/50** sin RAGAS. Cerradas 12,00 → **13,33** (10/15); citas 17,55 → 16,73 (menos citas de relleno: 315 citadas, 41 aciertos); abstención 7,91 → 8,02; **0 citas sin respaldo**; 16,5 s/pregunta → 4,55 h (apta). Proxy sin crédito: ROUGE-1 0,275 → 0,277, BLEU-4 0,087 → 0,086, respuestas > 2× referencia 22,9 % → 20,6 %; alineación cita-afirmación **68,9 % → 75,7 %**, citas débiles 10,9 % → 9,3 %. Un fallback (589: texto alrededor del JSON).
- **Decisión:** v6 cumple los criterios de adopción (total > base, cerradas no bajan, 0 sin respaldo, ≤ 5 h). Candidata final: `-Recomendada -PromptVersion v6` sobre el corpus nuevo del PC del 39,02 (v4 = 39,02 allí). Pendiente: medir v6 sobre ese corpus y, antes de usarla el sábado, UNA medición RAGAS (5,46 USD) porque v6 cambia el texto que lee el juez. `kingscode_final.ps1` usa ahora esa configuración por defecto.
- **`tools/kingscode_corre_todo.ps1` (2-oct, 17:30):** un comando sin parámetros por PC: `main` actualizado, GPU libre, corpus actualizado (aparta el actual como `*.antes_<fecha>` y el diagnóstico vuelve a descargar las fuentes oficiales de hoy + adiciones versionadas, como en el PC del 39,02; `-MantenerCorpus` lo evita), v4 y v6 sobre ese mismo corpus, respaldo del corpus en `$HOME\kc_snapshot`, `DOCUMENTO_FINAL.md` de la ganadora (v6 si supera a v4 sin bajar cerradas, con 0 sin respaldo y ≤ 5 h) y el comando del sábado. `docs/GUION_SABADO.md` usa ahora `-Recomendada -PromptVersion v6`.
- **Resultado de `kingscode_corre_todo.ps1` en `turing` (2-oct, 17:50):** con el corpus descargado de nuevo hoy, v4 = **37,46** (idéntico al corpus anterior) y v6 = **38,08** (cerradas 13,33, 0 sin respaldo, 4,52 h; alineación 75,7 %). Por tanto el 39,02 NO viene de volver a descargar las fuentes: viene de los documentos que Luis añadió localmente a su corpus; para usarlo hay que copiar su corpus (`kingscode_snapshot.ps1` crear/restaurar) o versionar sus adiciones. Respaldo del corpus de `turing`: `C:\Users\turing\kc_snapshot` (tar 3a556dbe…, 620 archivos, 87 MB). Corregido `final_document.py` cuando la verificación en vivo se omite.
- **v7 (ChatGPT, `cf6bd42`/`4ecdc04`):** v6 + economía de respuesta (semiabiertas en 3 oraciones, análisis en 5, sin repetir afirmaciones entre campos); opt-in. `kingscode_corre_todo.ps1` compara ahora v4, v6 y v7 sobre el mismo corpus (`-Variantes` configurable) y elige la mejor con el mismo criterio. **Aviso de crédito:** `kingscode_ragas_paired.ps1` ejecuta DOS RAGAS (~10,9 USD) y exige reproducir 39,02 (solo con el corpus de Luis); revisar el saldo antes.

## 2026-10-02 — Citas abiertas sin duplicación entre campos evaluados por RAGAS

- `scripts/evaluate.py` concatena `marco_normativo`, `analisis`, `jurisprudencia` y `conclusion` para las respuestas abiertas. `attach_references` ahora comprueba las citas oficiales a través de esos cuatro campos antes de completar `marco_normativo`: conserva las citas ya presentes y agrega las atribuidas que falten, respetando el límite existente. Evita inflar el texto con citas repetidas sin quitar referencias respaldadas.
- Añadida prueba de regresión para una cita ya presente en `analisis` y una referencia atribuida que faltaba.
- Verificación local: pruebas enfocadas de generación greedy y deduplicación aprobadas. No se ejecutó GPU/RAGAS; cualquier efecto en `answer_correctness` o puntaje queda pendiente de medición en la corrida del equipo.
- También se retiraron parámetros de muestreo ignorados por Transformers en el decoder greedy; permanecen `do_sample=False`, un beam y temperatura de política 0. El cambio elimina un warning sin cambiar el método determinista.
