# Plan de extensión de B para Claude Code

> **Nota de vigencia (28-sep-2026, tarde):** escrito originalmente contra el commit `254fa3a` (Gate 1B, `DummyDecoder`, sin `kingscode/generation/`). `a179af7` (Luis, Gate 2-Prep) ya implementó la mayor parte de lo que aquí se llamaba T4 (decoder real). Esta versión marca qué sigue vigente, qué ya se hizo y qué cambió de alcance. Base de comparación: corrida dummy = 5,00/50 sin RAGAS.

Cada tarea es una sesión de Claude Code: primero leer y proponer, luego implementar, luego medir. Orden pensado para que cada paso sume puntos medibles.

---

## T1 — Guarda que no aborte la corrida completa — ✅ hecho (2026-09-28)

**Alcance real aplicado (más acotado que el original):** no se reescribió `citation_guard`. Se modificó únicamente `Pipeline.run` (`kingscode/reasoning/pipeline.py`) para capturar `CitationGuardError` y sustituir esa fila por una abstención construida con `abstention_row` sobre la misma evidencia, sin abortar el resto del lote. `citation_guard`, `_answer` y la función pública `answer()` siguen lanzando la excepción exactamente igual que antes para cualquier llamador directo — así se conservan las ~16 pruebas de integridad de evidencia de `GuardSchemaTests` y la prueba de manipulación de evidencia (`test_decoder_cannot_mutate_evidence_to_create_support`) sin tocarlas.

**Por qué el alcance es más chico que el propuesto originalmente:** el plan original pedía que la guarda misma "suprima la oración con la cita" en vez de abortar. Eso exige reescribir la lógica de coincidencia cuerpo/artículo de `citation_guard`, que Luis ya probó extensamente. Se prefirió la salvaguarda aditiva (nunca abortar el lote) y se dejó la reescritura de la guarda como una tarea separada (T1b) que requiere su revisión, no la de Claude Code solo.
**Verificado:** `python -m unittest discover -s tests -v` → 86 tests, 5 se saltan (requieren `corpus/`). Nuevo test: `test_unsupported_citation_falls_back_to_abstention_instead_of_aborting_batch`.
**Detalle completo:** `docs/DECISION_LOG.md`, entrada "Corrección del abort-on-citation".

## T1b — Bajar el criterio de coincidencia de `citation_guard` a nivel de cuerpo — pendiente, requiere revisión de Luis

**Por qué:** `citation_guard` (`kingscode/reasoning/guards.py`) exige, cuando la cita trae artículo, que ese artículo aparezca también de forma literal en el texto del pasaje. El evaluador oficial (`scripts/citations.py::bodies`) descarta el artículo por completo al puntuar. Resultado: rechazamos (ahora: convertimos en abstención) citas que el evaluador sí pagaría — ver el ejemplo "artículo 5 de la Ley 1010 de 2006" con pasaje del artículo 1, en `docs/B_FINDINGS_2026-09-28.md`.
**Archivos:** `kingscode/reasoning/guards.py` (función interna de `citation_guard`, líneas del filtro extra sobre `supporting_passages`), `tests/test_reasoning.py::GuardSchemaTests`.
**Aceptación propuesta:** bajar el filtro adicional de `citation_guard` a solo cuerpo (`ref.body`), eliminando la exigencia de coincidencia literal de artículo en el texto del pasaje; medir el techo de citas con `tools/analyze_citation_ceiling.py` antes/después; todos los tests de `GuardSchemaTests` deben seguir pasando o actualizarse con justificación explícita en `DECISION_LOG.md`.
**Por qué no se aplicó ya:** es un cambio a semántica de scoring que Luis diseñó y probó a propósito (ver DECISION_LOG 2026-09-27, "Citation guard más conservador que la puntuación documental del evaluador... No usa alias por número ignorando año"). Se documenta para decidirlo en conjunto antes del día de GPU.

## T2 — Referencias construidas por código como fallback determinista — reducido de alcance

**Estado real:** no hace falta un `citations_builder.py` nuevo separado del decoder: `kingscode/generation/prompts.py` ya instruye al modelo a citar la evidencia directamente en los campos del formato, y `HFDecoder.generate` devuelve la fila ya validada. Lo que sigue teniendo valor de `tools/analyze_citation_ceiling.py` es medir el TECHO alcanzable sin modelo (ver B_FINDINGS §2) para decidir si conviene un post-proceso que complete `referencia_legal`/`marco_normativo` cuando el modelo no citó nada (fila no abstenida pero sin citas → hoy dispara `non_abstaining_answer_without_verifiable_citation` en `citation_guard`, que con el fix de T1 se convierte en abstención). Si se decide implementarlo, debe vivir en `kingscode/generation/` junto al decoder, no como módulo aparte, para no duplicar lógica de citas.
**Prioridad:** baja mientras el decoder real no se haya probado en GPU — medir primero si el modelo ya cita razonablemente bien antes de construir un fallback.

## T3 — Política de abstención mínima — ✅ hecho (2026-09-28, tarde)

**Implementado:** `policy.py::blocking_reasons(assessment, format)` separa las razones "duras" (`empty_question`, `retrieval_empty`, `conflicting_evidence`, `ineligible_evidence`) de las blandas (`missing_explicit_reference`, `ambiguous_query_reference`, `currency_not_certified`, `missing_relation_evidence:*`, `weak_lexical_evidence`). `multiple_choice` nunca bloquea (`blocking_reasons` devuelve `()` siempre), acorde a que adivinar entre las opciones dadas supera a abstenerse incluso al azar (enunciado 6.1). Texto libre solo bloquea con las razones duras; el resto queda en `trace["warnings"]` y se deja que el decoder lo intente, con `citation_guard` + el fallback de T1 como red de seguridad si termina inventando algo. `assess_evidence(...).sufficient` (usado por `route_graph` para decidir expansión de grafo) no se tocó — sigue considerando todas las razones, es un concepto distinto al de bloqueo de abstención.
**No se tocó:** `assess_evidence` en sí, ni `route_graph`/`routing.py`.
**Verificado:** `test_multiple_choice_never_pre_blocks_on_soft_evidence_reasons`, `test_free_text_still_hard_blocks_on_empty_retrieval` en `tests/test_reasoning.py`.

## T4 — Decoder real — ✅ hecho por A/Luis en Gate 2-Prep (`a179af7`), sin ejecutar en GPU todavía

`kingscode/generation/hf_decoder.py` (`HFDecoder`) implementa el protocolo `Decoder` existente: Transformers local, lazy, bf16 con fallback explícito a int8/int4, locks de modelo (`config/models.lock.json`), prompts `grounded-formats-v2` (`kingscode/generation/prompts.py`) con parser tolerante y validación de oraciones/palabras por formato. `config/decoder_bakeoff.json` fija Qwen3-8B, ALIA Legal 7B, Salamandra 7B y Llama 3.1 8B (opcional). **Nada de esto se ejecutó contra pesos reales todavía** (`gate2_prep.decoder_weights_downloaded: false` en `docs/KINGSCODE_STATE.json`). Pendiente: correr `tools/member_b.py decoder-smoke --model qwen3-8b --dry-run` primero, luego con GPU real.

## T5 — Recuperación con opciones en cerradas — ✅ hecho (2026-09-28, tarde)

**Implementado:** `pipeline.py::query_variants(question, query)` genera una consulta por opción (`"{pregunta} {opción}"`, orden determinista por letra) para `multiple_choice` con opciones; `rrf_merge(ranked_lists, k)` fusiona los resultados de A por rango recíproco (constante 60), deduplicando por `passage_id`, sin mutar los pasajes de A. `Pipeline._fetch` llama a `self.retrieve(...)` una vez por variante y funde; con una sola variante (todo lo demás) el llamado es idéntico al de antes — cero cambio de comportamiento fuera de `multiple_choice`. Se aplica tanto a la recuperación inicial (`graph_mode="off"`) como a la expansión de grafo si el router decide `auto`/`on`.
**No medido todavía:** el efecto real en recall a nivel de cuerpo y exactitud en cerradas requiere el corpus real (no disponible en esta máquina); solo se verificó con fixtures sintéticas que el fan-out y la fusión ocurren correctamente.
**Verificado:** `test_query_variants_one_per_option_sorted_else_base_only`, `test_rrf_merge_boosts_passages_ranked_in_more_lists`, `test_multiple_choice_fans_out_one_retrieve_per_option_and_fuses_rrf`.

## T6 — Throughput y robustez del sábado — bloqueado, no implementado a ciegas

`kingscode/generation/experiments.py` ya separa el freeze de retrieval del bakeoff de decoders y corre cada decoder en un proceso nuevo (`tools/member_b.py bakeoff`). Lo que falta (concurrencia configurable, caché reanudable por pregunta, ensayo cronometrado de 992 preguntas) **no se implementó en esta sesión a propósito**: es exactamente el tipo de cambio que el protocolo de `CLAUDE.md` pide medir antes/después, y no hay manera de medirlo sin `corpus/` ni GPU en esta máquina. Escribir concurrencia sin poder correrla arriesga bugs silenciosos en la guarda/citas deterministas. Queda para la sesión con la 4090.

## T7 — Entregables — hecho en lo que no depende de GPU (2026-09-28, tarde)

- **Interfaz:** ✅ `interfaz/app.py` (Streamlit), con consulta individual, lote JSONL y verificación por ID del jurado. El modo jurado reproduce el perfil Qwen3-8B BF16, BM25, recuperación por opciones, router, prompt v4, citation-fill y cinco menciones verificadas del candidato m5 que obtuvo **37,46/50**. Compara los campos de respuesta exactamente y reporta aparte si coinciden las citas oficiales y los pasajes; comprueba también el hash de las preguntas y la identidad del pipeline. El lote valida ids/formatos, muestra avance y fallos, permite revisar cada respuesta con citas/evidencia/fuentes y descarga `submissions.jsonl` validado. Las entradas se proyectan al contrato público de `Question`; los checkpoints usan una carpeta temporal. Pendiente: probarlo de extremo a extremo con `corpus/` real, decoder real y el ID que entregue el jurado.
- **Reproducibilidad:** ✅ `run.sh` (instala deps, exige o construye `corpus/`, corre tests, Gate 1B smoke y `scripts/evaluate.py --split sample`) y `Dockerfile`/`​.dockerignore` para el contenedor limpio. No requiere GPU. Sin `corpus/` local no se pudo ejecutar de punta a punta en esta máquina — solo se verificó la sintaxis de bash y del snippet Python embebido.
- **Pendiente:** publicar el corpus + índice en un enlace de descarga y declararlo en la sección `## Corpus e índice` del README (ya creada, con la URL por completar cuando A congele el índice).

---

## Qué no hacer

- No fine‑tuning del decoder esta semana.
- No multi‑agente de 4–5 pasadas por pregunta: no cabe en el presupuesto de ~22 s/pregunta del sábado.
- No usar las 50 de muestra como few‑shot hasta que los organizadores lo autoricen.
- No cambiar retrieval y decoder en el mismo experimento.
- No reescribir la semántica de `citation_guard`/`legal.py` sin que Luis lo revise (ver T1b): son ~60 tests de A/B compartiendo esa capa.
