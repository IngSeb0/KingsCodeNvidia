# KINGSCODE MASTER KNOWLEDGE — Hackathon AI Week 2026

**Fuente canónica del proyecto.**  
**Última actualización:** 2026-10-01\
**Equipo activo:** 2 integrantes  
**Estado:** v0.5 + capa v0.6 de A (metadatos/recuperación) preparada y validada; A y Gate 1B conservados. Hay artefactos históricos de búsqueda CUDA, pero no un benchmark neuronal end-to-end actual aceptado ni bakeoff de decoder versionado. El smoke/corrida en la RTX 4090 de integración se ejecuta fuera de este checkout. Estado operativo y siguientes pasos: `docs/KINGSCODE_STATE.json` y `docs/EXPLORATION_ROUTES_2026-10-01.md`.

> En un chat nuevo, leer primero este archivo y luego `KINGSCODE_STATE.json`. No reconstruir decisiones desde memoria si existe una versión más reciente de estos archivos.

---

## 1. Qué es la Hackathon

Reto de AI Week 2026 de la Universidad de los Andes: construir un sistema que responda preguntas de **derecho colombiano** usando un **modelo abierto de máximo 8B parámetros** y un **corpus jurídico propio**, buscando superar modelos grandes evaluados sin fuentes externas.

La hipótesis del reto es que un corpus sólido y una buena recuperación pueden ser más determinantes que aumentar el tamaño del modelo.

### Banco
- Total: 1.042 preguntas.
- Desarrollo: 50 preguntas conocidas con respuesta esperada y `legal_basis`.
- Evaluación ciega del sábado: 992 preguntas nuevas.
- Tipos: 15 cerradas, 30 semiabiertas y 5 abiertas en el sample de 50.
- Áreas: constitucional, administrativo, penal, procesal, comercial/sociedades, civil, familia, tributario, laboral, mercados/consumidor/datos/PI.

### Restricciones centrales
- Decoder abierto <= 8B.
- Encoder abierto.
- Temperatura 0 en ejecución final.
- Sistema determinista y reproducible.
- Prohibidos modelos cerrados (OpenAI, Anthropic, Google, Cohere, etc.) en cualquier componente competitivo; el enunciado también prohíbe usarlos para datos sintéticos de apoyo.
- No editar manualmente respuestas después de la ejecución.
- No indexar banco de evaluación ni material con respuestas esperadas.
- Índice congelado tras la entrega.

### Computación
- Hardware objetivo del equipo: **RTX 4090 24 GB** en Sala Turing.
- Colab no es el plan principal.
- La organización permite Sala Turing/Colab para quienes necesiten GPU, pero KingsCode prioriza 4090.

---

## 2. Cronograma operativo

### Lunes
- sesión inaugural presencial;
- entrega de material;
- kit del evento;
- material oficial y llave del juez.

### Martes a viernes
- desarrollo principalmente remoto;
- construcción y enriquecimiento de corpus;
- ejecución repetida de `evaluate.py` sobre las 50 preguntas;
- workshops/charlas obligatorias según agenda.

### Viernes 17:00
Entregar reporte de avance de una página con score del sample, estado del corpus y riesgos.

### Sábado
- 09:00: entrega de 992 preguntas secretas;
- 09:00–15:00: ejecución ciega + terminación de interfaz;
- 15:00: cierre;
- 15:00–17:00: verificación en vivo, 2–3 preguntas se regeneran;
- 18:00–19:00: resultados/premiación.

Presupuesto conceptual: ~22 s/pregunta si se usan las seis horas completas para 992 preguntas. En práctica el objetivo de KingsCode es bastante menor para dejar margen de validación y fallos.

---

## 3. Cómo se califica

### Automático — 80 puntos
- 20: exactitud en cerradas.
- 30: corrección en texto libre / RAGAS.
- 20: calidad de citación.
- 10: abstención calibrada.

### Ingeniería/interfaz — 20 puntos
- 10: interfaz gráfica.
- 5: corpus + bitácora.
- 3: video <=5 min.
- 2: reproducibilidad.

**Consecuencia estratégica:** retrieval + citas + grounding tienen un peso enorme. Una respuesta jurídicamente plausible sin evidencia recuperada pierde valor.

---

## 4. Material oficial disponible

- `data/sample_50.jsonl` — 50 preguntas de desarrollo.
- `data/seed_targets.json` — listado inicial no exhaustivo de fuentes/normas.
- `schema/submission.schema.json` — contrato de salida.
- `scripts/evaluate.py` — evaluador oficial.
- `scripts/citations.py` y `scripts/common.py` — utilidades.
- `scripts/requirements-evaluador.txt` — dependencias del juez.
- `Ejemplo de entrega/` — ejemplo de submissions, corpus y manifest.
- `entregables/` — plantillas/instrucciones.
- OpenRouter API key — solo para el juez de evaluación de texto libre, no para el sistema competitivo.

Preflight realizado en v0.1/v0.2:
- archivos oficiales mínimos presentes;
- 50 preguntas válidas, IDs únicos;
- 186 seed targets;
- ejemplo oficial validado contra schema;
- scripts oficiales compilan;
- `evaluate.py` se ejecutó sobre el ejemplo sin `--ragas`;
- archivos oficiales preservados byte a byte en el paquete generado.

---

## 5. División del equipo — 2 integrantes — v0.5

La división se hace por capas estables, no por áreas jurídicas. Ver `TEAM_SPLIT.md`.

### Integrante A — Knowledge Layer / Corpus / Graph / Retrieval
Responsable de:
- adquisición y trazabilidad de fuentes oficiales;
- normalización y chunking jurídico;
- metadatos y jerarquía documental;
- construcción del grafo desde Corpus v0;
- BM25, embeddings, RRF y reranking;
- métricas de retrieval y cobertura;
- `CORPUS.md` y `corpus_manifest.json`.

Contrato estable:
```text
retrieve(question, k, graph_mode="auto") -> [passages]
```

### Integrante B — Query / Reasoning / Generation / Evaluation / Delivery
Responsable de:
- normalización de consulta y expansión terminológica controlada;
- `graph_router` y política OFF/AUTO/ON;
- decoder bakeoff;
- prompts y JSON estricto;
- citation guard y abstención;
- `evaluate.py`, RAGAS, latencia y VRAM;
- interfaz, comando único, reproducibilidad y entregables.

Contrato estable:
```text
answer(question, passages, format) -> submission_row
```

### Trabajo compartido
- experiment design;
- integración A↔B;
- revisión de errores del sample;
- decisiones de freeze;
- ejecución final.

### Regla de integración
Nadie cambia simultáneamente retrieval y decoder en el mismo experimento sin registrar una ablation. Una variable por experimento siempre que sea posible.

---

## 6. Arquitectura actual v0.5 — Graph-Aware Hybrid RAG

```text
                         Pregunta
                            |
                            v
          normalización jurídica / expansión controlada
                            |
          +-----------------+------------------+
          |                 |                  |
         BM25        Qwen3-Embedding      grafo jurídico
          |                 |                  |
          +------- RRF -----+          expansión selectiva
                  |                            |
               top 30                         |
                  +-------------+--------------+
                                |
                         Qwen3-Reranker
                                |
                             top 6-8
                                |
                         decoder <=8B
                                |
                           JSON grounded
                                |
                         citation_guard
                       /                \
                  soportado          no soportado
                     |                  |
                  entregar         corregir/abstener
```

### Por qué esta arquitectura
La literatura legal reciente favorece:
- retrieval preciso como principal driver;
- chunks pequeños/estructurales;
- híbrido sparse+dense;
- cross-encoder reranking;
- evidencia mínima;
- auditoría de citas;
- evaluación separada de retrieval y generation;
- preservación de jerarquía y relaciones jurídicas.

**Decisión v0.5:** el grafo existe desde Corpus v0. No se usa obligatoriamente en cada consulta. El camino BM25+dense+RRF sigue siendo el fast path; el grafo se consulta/expande cuando una pregunta o un pasaje requiere relaciones como `REMITE_A`, `MODIFICA`, `DEROGA`, `REGLAMENTA`, `CITA`, o navegación jerárquica norma→artículo→parágrafo/inciso. Esto evita pagar el costo de GraphRAG completo en preguntas directas sin perder la estructura jurídica desde la ingesta.

Ver `LITERATURE_REVIEW_2026-09-27.md`, `MEMBER_A_CORPUS_PLAN.md`, `MEMBER_B_REASONING_EVAL_PLAN.md` y `ARCHITECTURE_V05.md`.

---

## 7. Estrategia de chunking

No usar chunking fijo ciego como diseño principal.

### Leyes/códigos/decretos
Unidad principal: **artículo**.  
Mantener en metadata:
- norma;
- número/año;
- artículo;
- parágrafo/inciso/numeral cuando aplique;
- título/capítulo;
- órgano;
- vigencia si se puede verificar;
- URL oficial;
- orden dentro del documento.

Si un artículo es enorme: split-then-merge respetando subestructura y repitiendo encabezado/contexto mínimo.

### Sentencias
Segmentación por secciones jurídicas si la fuente lo permite: hechos, problema jurídico, consideraciones, ratio/fundamento, decisión, con metadatos de corporación/sala/fecha/radicado.

### Regla
No cortar referencias legales o listas de incisos a mitad si puede evitarse.

---

## 8. Retrieval experiments

Baseline mínimo a ejecutar en orden:

1. BM25.
2. Dense (`Qwen3-Embedding-0.6B`).
3. BM25 + dense con RRF.
4. Híbrido + `Qwen3-Reranker-0.6B`.
5. Híbrido + reranker + expansión terminológica jurídica controlada.
6. Comparar chunking estructural vs adaptive chunking.

### Métricas
- Recall@1, 3, 5, 10.
- MRR.
- nDCG@10 si es viable.
- `% legal_basis encontrado en top-10`.
- tasa de documento equivocado / DRM.
- latencia de retrieval.

### Gate
Si `Recall@10` no es alto, NO perder tiempo fine-tuneando decoder.

---

## 9. Decoder candidates — bakeoff

### Candidato 1 — Qwen3-8B
Baseline principal por capacidad general/multilingüe y porque el enunciado lo menciona como opción sugerida.

### Candidato 2 — SINAI/ALIA-es-legal-administrative-7B-Instruct
Añadido tras revisión bibliográfica. Modelo 7B especializado en español jurídico/administrativo, basado en Salamandra. Puede aportar vocabulario/estilo legal, pero hay riesgo de priors del derecho español. Solo se adopta si gana sobre las 50 preguntas bajo el mismo retrieval.

### Candidato 3 — BSC-LT/salamandra-7b-fc-2607
Alternativa hispanohablante abierta.

### Candidato 4 — Llama-3.1-8B-Instruct
Control adicional si el tiempo lo permite.

### Comparación justa
Mismos:
- retrieval congelado;
- top-k;
- prompt;
- temperatura 0;
- schema;
- preguntas;
- evaluador.

Medir:
- score oficial;
- valid JSON;
- citas no soportadas;
- abstenciones;
- segundos/pregunta;
- VRAM pico.

---

## 10. Fine-tuning — decisión vigente

### Decoder
**NO inicialmente.**

Razones:
- solo 50 preguntas oficiales de desarrollo;
- riesgo alto de overfitting/memorización;
- literatura reciente sugiere que retrieval fija el techo en Legal RAG;
- RAG suele ganar sobre FT para conocimiento factual raro/específico;
- tiempo de hackathon limitado.

### Primer fine-tune candidato
**Reranker con hard negatives**, solo si retrieval muestra confusiones entre normas/artículos similares.

Construcción:
- query = pregunta;
- positivo = pasaje que contiene `legal_basis`;
- negativos duros = top resultados incorrectos de BM25+dense;
- entrenar/rerankear y medir ganancia en Recall/MRR + score end-to-end.

### QLoRA/SFT decoder solo si
- Recall@10 es alto;
- evidencia correcta llega al decoder;
- el decoder aun falla consistentemente en formato/razonamiento;
- existe un conjunto de entrenamiento legítimo suficiente sin violar reglas.

---

## 11. Citation guard

Componente determinista obligatorio de nuestra arquitectura:

1. extraer toda referencia legal generada;
2. normalizar forma canónica;
3. comprobar existencia en los pasajes recuperados;
4. verificar artículo/norma;
5. si la cita no está soportada:
   - eliminarla y regenerar desde evidencia, o
   - abstener, según tipo de pregunta y suficiente/insuficiente evidencia;
6. nunca editar manualmente una respuesta final de evaluación.

---

## 12. Uso de estructura y terminología

### Terminología
Mantener un diccionario/normalizador pequeño y auditable de:
- abreviaturas;
- nombres alternos;
- cuerpos normativos;
- entidades/cortes;
- sinónimos jurídicos frecuentes.

No usar expansión generativa descontrolada por defecto.

### Estructura / grafo jurídico desde Corpus v0
Preservar jerarquía y orden del documento en cada pasaje **y construir el grafo desde la ingesta**.

Tipos de nodo previstos (habilitados cuando exista evidencia):
- documento/norma o sentencia;
- artículo;
- parágrafo/inciso/numeral cuando exista;
- sección relevante de sentencia;
- tags jurídicos controlados.

Tipos de relación previstos (no es obligatorio emitir tipos sin evidencia):
- `CONTIENE`;
- `REMITE_A`;
- `CITA`;
- `MODIFICA`;
- `DEROGA`;
- `REGLAMENTA`;
- `DESARROLLA`;
- `EXCEPCIONA`.

El grafo no sustituye BM25+dense. Es una capa estructural y de expansión selectiva. Si varios pasajes del mismo documento sobreviven al reranker, considerar presentarlos al decoder en orden original.

---

## 13. GPU / inferencia

Hardware objetivo: RTX 4090, 24 GB.

Fase CUDA todavía pendiente. Orden correcto:
1. `python tools/preflight.py`
2. `python tools/check_cuda.py`
3. observar driver/CUDA/PyTorch/VRAM reales;
4. instalar stack compatible;
5. smoke test GPU;
6. cargar decoder baseline;
7. medir BF16 primero;
8. cuantizar solo si VRAM/latencia lo justifican.

No asumir versión de CUDA/PyTorch antes de diagnosticar la máquina.

---

## 14. Estado actual y siguiente acción

### Completado
- lectura del enunciado y starter pack;
- preflight/integridad;
- revisión de literatura 2024–2026;
- arquitectura Graph-Aware;
- división A/B revisada para v0.5;
- contratos de integración;
- Corpus v0.1: 163 documentos oficiales, 26.558 pasajes conservados y 26.060 elegibles; 498 históricos/ambiguos excluidos de recuperación. Raw, clean, hashes, URLs, fechas y offsets disponibles en `../corpus_manifest.json`.
- Capa v0.6 de A (metadatos + recuperación): identidad canónica determinista independiente de la URL (`canonical_document_id`/`canonical_fragment_id`), metadatos temporales conservadores (`unknown` por defecto), `content_hash`, clasificación de los 28 objetivos de adquisición, dedup/diversificación configurable, taxonomía de fallos con `document_mismatch_rate`, experimentos opcionales R6/R7/R8 y representación de embedding experimental. Todo aditivo y determinista; el corpus se reconstruye byte a byte idéntico (mismos hashes que v0.1). Módulos en `kingscode/metadata.py`, `acquisition_backlog.py`, `diversify.py`, `metadata_experiments.py`, `failure_analysis.py`, `coverage_report.py`; reportes `reports/*_v06.json`. 44 tests nuevos en verde; sin GPU/bakeoff/RAGAS/fine-tuning; B intacto. La idea de que el corpus responda casi cualquier pregunta es solo hipótesis de diseño, no requisito oficial.
- Grafo desde ingesta: 59.236 nodos y 75.380 edges con evidencia; no se inventan tipos de relación ni se certifica vigencia. Tags y relaciones adicionales quedan pendientes de evidencia explícita.
- API pública `from kingscode import retrieve, Retriever`, BM25 persistido, expansión acotada, RRF y adaptadores Qwen de embeddings/reranker con commits fijos.
- Benchmark BM25 OFF/AUTO/ON, auditoría de etiquetas y reportes por área/formato. Resultados vigentes: `../CORPUS.md` y `../reports/retrieval_bm25.json`; no equivalen a score oficial de respuestas.
- Diagnóstico local CPU; modelos abiertos probados con pesos reales sobre dos pasajes oficiales. Esto no equivale al benchmark de todo el corpus.
- Gate 1B: normalización/expansión controlada, router OFF/AUTO/ON inyectable, interfaz answer con dummy, abstención, guardas de citas/schema, wrapper del evaluador oficial y registro reproducible. Implementación independiente en `kingscode/reasoning/`; A permanece sin cambios.
- Smoke sobre las 50 preguntas con 100 % de JSON válido, 50 abstenciones deliberadas y evaluador oficial sin RAGAS. El resultado de 5/50 es propio del dummy y no mide razonamiento jurídico. Segunda verificación y tests en `../reports/member_b_second_verification.json` y `../reports/member_b_tests_second.txt`.

### Trabajo inmediato en paralelo

#### Integrante A
1. revisar los 28 objetivos de adquisición pendientes y los grupos de artículos ambiguos conservados;
2. ampliar/revisar vigencia y atribución antes del freeze competitivo;
3. en la máquina 4090, ejecutar `python tools/check_cuda.py`, configurar el stack comprobado y seguir `MEMBER_A_RUNBOOK.md` para dense → hybrid → hybrid+reranker;
4. comparar retrieval manteniendo corpus, preguntas y labels originales fijos; no iniciar decoder FT con este nivel de recuperación;
5. acordar licencia, empaquetado y publicación del corpus para entrega final.

#### Integrante B
1. reproducir Gate 1B con `.venv/Scripts/python.exe tools/member_b.py smoke` y revisar trazas por área;
2. mantener tests de citas/abstención y ampliar formas de citación cuando haya casos verificados;
3. planificar una tarea posterior de integración del decoder abierto real, sin presentar el dummy como sistema competitivo;
4. dejar CUDA, bakeoff, calibración de abstención y RAGAS pendientes hasta esa fase;
5. continuar UI/delivery y freeze cuando exista ejecución competitiva validada.

### Integración siguiente
El retrieval real de A ya está conectado al harness de B sobre las 50 preguntas con dummy y verificación histórica independiente. Gate 2-Prep añade `kingscode/generation/`, los locks de decoders, prompts versionados, preparación de caché verificado, diagnóstico/plan, GPU smoke y matriz R0–R5/D1–D4. No se ejecutó ninguno de los tests/smokes nuevos por instrucción del usuario; el resultado histórico de 60 tests no valida estos cambios.

La comparación de decoders usa los mismos pasajes congelados después del benchmark de retrieval. El router continúa siendo determinista y no recibe un prompt. La inferencia real mantiene temperatura 0, batch 1 y BF16 inicial; no hay fallback automático ni afirmación de que quepa en la 4090. Salamandra y Llama requieren aprobación de acceso. Revisiones/licencias y el conteo exacto de parámetros de los modelos nominales 8B: `MODEL_LOCKS_GATE2.md`.

La siguiente ejecución debe seguir `GPU_DAY_RUNBOOK.md`, empezando por `git pull --ff-only origin main`, verificar el commit, disponer del snapshot del corpus y ejecutar las dos verificaciones preparadas antes de cargar modelos. Las herramientas no actualizan automáticamente el estado a CUDA/bakeoff completados.

Comando local exacto para repetir el gate actual: `.venv/Scripts/python.exe tools/member_b.py smoke`. Segundo pase: `.venv/Scripts/python.exe tools/verify_member_b_second.py`. Ver `MEMBER_B_RUNBOOK.md`. Para reconstruir A se mantienen sus comandos en `MEMBER_A_RUNBOOK.md`; B no necesita rehacerlo. Los archivos oficiales permanecen intactos; solo se han generado submissions de prueba con abstención, no una entrega competitiva.

---

## 15. Literatura que cambió decisiones

- Legal RAG Bench 2026: retrieval como principal driver.
- LegalBench-RAG 2024: fragmentos mínimos y precisos.
- Adaptive Chunking 2026: chunking adaptativo/estructural puede mejorar notablemente RAG sin cambiar modelos.
- HyPA-RAG 2024 + SemEval 2026: hybrid retrieval + reranking como pipeline fuerte.
- Grounded in Law 2026: auditoría de referencias después de generar.
- Spanish Legal Terminology RAG 2025: expansión terminológica controlada útil en español jurídico.
- Qwen Goes Brrr 2026: reranking puede mejorar mucho recall y accuracy en un reto documental.
- Fine-tuning vs RAG: priorizar retrieval antes del decoder FT.
- ALIA Spanish Legal 7B 2026: nuevo candidato especializado que debe entrar al bakeoff.

---

## 16. Protocolo de continuidad

Cada cambio importante debe actualizar:
1. este archivo;
2. `KINGSCODE_STATE.json`;
3. `config/strategy.json`;
4. `docs/DECISION_LOG.md`;
5. el plan específico de A/B si cambia ownership o contrato.

En una conversación nueva, la instrucción mínima es:

> “Busca en mi Library la carpeta `KingsCode Hackathon 2026`, lee `KINGSCODE_MASTER_KNOWLEDGE.md` y `KINGSCODE_STATE.json`, y continúa desde `next_action` sin reconstruir el proyecto desde cero.”

Este archivo prevalece sobre recuerdos parciales de chats anteriores, salvo que exista una versión más nueva explícitamente marcada.


## Addendum — Benchmark interno de retrieval v1 (Member A)

La rama `feat/member-a-retrieval-benchmark-v1` añade un benchmark interno
separado del sample oficial: 200 casos source-derived (120/40/40; 20 por área),
gold con IDs canónicos/spans verificables y entradas públicas sin labels. No se
usaron LLMs cerrados ni preguntas semánticas fabricadas; 20 paquetes se
mantienen para autoría humana. R0 BM25 quedó medido y reproducible; en validation
obtiene Evidence Completeness@8 0.575, Recall@10 0.625 y MRR@10 0.3739. R0
holdout se usó solo como baseline predeclarado.

No hay selección de retrieval: Qwen dense/hybrid/reranker siguen pendientes de
la 4090, y BGE-M3 no tiene lock/loader/reporte reproducible. Los diagnósticos
CPU de grafo/R6/R7/R8 no sustituyen sus variantes R3-based. Revisar
`docs/BENCHMARK_METHODOLOGY.md`, `docs/RETRIEVAL_BENCHMARK_TASK_BOARD.json` y
`reports/benchmark/selection/selected_config.json` antes de continuar.

## 2026-09-28 — reconciliación GPU y siguiente fase A v0.2

El archivo histórico `reports/member_a_v02/gpu_reconciliation.json` conserva métricas y hashes vinculados a `origin/feat/member-a-gpu-results-4090-20260928` (60ebf7e), incluidas corridas R1/R2 y Search V2. El estado reconciliado más reciente de `AGENTS.md` no las acepta como resultados GPU versionados actuales de R1-Qwen, R1-BGE, R2 ni R3–R8; no usar esas cifras para afirmar benchmark neuronal completo, CUDA objetivo validado para la configuración integrada o selección final. Main sigue en a3548a1 al comenzar históricamente esa fase.

DEV HYB120_LOC_META_1p25: EC@8=0.9916666666666667, Recall@10=0.9958333333333333, MRR@10=1.0. En validation empatan configuraciones con locator, incluyendo HYB120_LOC_META_0p0 y BM25120_LOC_META_0p0, con 1.0 en esas tres métricas. Esto respalda candidate injection, no superioridad de metadata_scale=1.25 ni rendimiento jurídico general. La latencia de Search V2 es costo compartido de exploración. Se conservan resultados negativos.

Validation v1 queda CERRADA para tuning. El holdout de arquitectura no se utiliza aquí; R0 sí tiene un baseline holdout histórico ya consumido. No confundir ambos. Corpus-v0.1 es el snapshot histórico inmutable; la nueva adquisición y los cambios de parsing van exclusivamente a corpus-v0.2. El dense GPU está documentado por su hash, pero no disponible localmente para volver a verificar sus bytes.

La fase A actual productiviza `legal_locator.py` y prepara benchmark v2 diverso y una adquisición acotada. R0–R8 son ablaciones: las composiciones futuras requieren evidencia de validation v2 y medición de interacciones. Graph expansion y graph features son ejes distintos. Ninguna composición, decoder ni freeze de top 8 competitivo queda seleccionado por esta reconciliación.


## 2026-09-29 — estado Member A v0.2 y benchmark independiente

La rama feat/member-a-corpus-v02-locator incorpora locator exacto aditivo, fusión RRF de varias vistas textuales y gold con minimal evidence sets. El locator usa la pregunta original; vistas/planner no reciben privilegios de identidad. El contrato de tres argumentos continúa compatible.

El piloto de benchmark v2 proviene del corpus y solo sirve de smoke técnico. Se evaluaron seis filas DEV una vez; el split llamado holdout está visible en checkout y no es SEALED_EVAL. La búsqueda verificó cero ítems independientes: los PDFs ICFES encontrados devolvieron 404 y SIRNA no expuso un banco público descargable. No hay baseline ni distribución de fallos válidos para tuning. Benchmark v1 y Search V2 quedan cerrados.

Corpus-v0.2 tiene cuatro documentos provisionales (72 pasajes), uno bloqueado por PDF escaneado, y cero relaciones semánticas verificadas. Las seis familias auditadas G01/G02/C01/P02/P01/D01 aún necesitan arreglo con fixtures/fuentes. Corpus-v0.1 permanece inmutable. Revisar docs/MEMBER_A_V02_PROGRESS.md y docs/BENCHMARK_V2_METHODOLOGY.md antes de continuar.

En el siguiente checkpoint de la misma rama se añadieron primitivas y pruebas para Oracle Multi-View Recall, Fusion Loss y Graph Recovery Rate sobre conjuntos mínimos alternativos. Son soporte de métrica, no evidencia de rendimiento: el conjunto independiente DEV sigue en cero y no existe baseline/failure distribution. Los seis defectos permanecen pendientes o bloqueados por fuente, sin cambios al corpus-v0.1. El piloto corpus-derivado conserva sus 12 filas como no independiente/no seleccionable; no se amplió el diagnóstico mientras las estructuras v0.2 no tengan revisión humana.


### KC-COL-IR-v0.1 independent benchmark (2026-09-29)

KC-COL-IR-v0.1 uses 30 frozen item numbers from the current JEP CUJ 2026 fourth-edition (SeRVR) case materials; the prior 2025 label was corrected without resampling. The mixed-edition `/preguntas` page retains stale “2025 / Tercera Edición” boilerplate; attribution to CUJ 2026 rests on matching case identity and materials in the official 2026 packet. The 2025 third-edition SDSJ packet is provenance-only. A deterministic next-10 expansion was frozen before content review; 40 candidates have dispositions and 10 independently supported gold packets are accepted. All 10 are MISSING from competitive corpus-v0.1. A separate profile using all six textual PDFs from the full CUJ 2026 packet is materialized as 190 page passages; all 10 controlled evidence sets resolve to actual passages and the ranking gate is unlocked. `retrieval_benchmark_ready=true`; `CUDA_READY=false` pending target-runtime handoff. Javeriana 2026 remains unparsed/uninspected and Externado 2011 is reproducibility-only. No retrieval was executed. See `docs/MEMBER_A_V02_PROGRESS.md` and `benchmarks/kc_col_ir_v0.1/CUDA_HANDOFF.md`.

### Pre-CUDA hardening (2026-09-30)

The continuation starts from `main` `e52816145970adddc70300b1a9988c02b4cd1c8d` on the separate local branch `exp/pre-cuda-hardening`. It prepares a pinned local-tokenizer length audit, execution identity, Candidate@30 and duplicate diagnostics, explicit retrieval timing, unique `passage_id` checks, and a preregistered shortlist of at most two configurations. The controlled profile and tokenizer audit are not available in this checkout, so the audit has not run. No C0-C3, CUDA, validation scoring, decoder, or tests ran. `CUDA_READY` remains false and the current handoff still stops before ranking. See `docs/KC_COL_IR_PRE_CUDA_HARDENING.md`.
