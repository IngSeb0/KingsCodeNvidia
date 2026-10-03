# Gate 1B — Harness pre-GPU

Implementación en `kingscode/reasoning/`. Consume la API pública de A sin cambiar sus módulos, corpus, índices ni grafo. El único backend habilitado por el comando `smoke` es `DummyDecoder`: siempre se abstiene y no carga modelos. Esto verifica integración, trazabilidad y evaluación; no mide calidad de razonamiento jurídico.

## Reproducir exactamente el flujo

Desde la raíz, con el entorno de A y su snapshot local disponibles:

```powershell
.venv/Scripts/python.exe tools/member_b.py smoke
```

El comando ejecuta las 50 preguntas, crea una carpeta nueva en `reports/member_b/` y devuelve sus rutas. Incluye normalización, primera recuperación OFF, routing, segunda recuperación cuando procede, política de abstención, dummy, citation guard, schema oficial y evaluador oficial sin `--ragas`. No requiere red, API keys, CUDA ni pesos de modelos.

Para comprobar todos los tests y repetir la auditoría independiente:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe tools/verify_member_b_second.py
```

El segundo comando selecciona la corrida aprobada más reciente. `--run RUTA` permite indicar otra. Comprueba también que la implementación de A sigue idéntica al commit inicial `382c5eb`; por eso requiere el checkout Git con ese historial. Reconstruye la ejecución de B en otro proceso, sin reconstruir el corpus de A.

Si se parte de un clon nuevo, primero obtener el snapshot de A o seguir su runbook para adquirir/construir corpus. Volver a descargar las fuentes no garantiza los hashes del snapshot anterior. Dependencias de B: biblioteca estándar y `jsonschema`, ya incluido en `requirements-knowledge.txt`.

## Interfaces

```python
from kingscode import Retriever, retrieve  # Contrato de A conservado.
from kingscode.reasoning import (
    Question, normalize_query, route_graph, answer,
    citation_guard, validate_submission, run_eval,
    Pipeline, RetrieverGraphRouter,
)

adapter = RetrieverGraphRouter()
retriever = Retriever(mode="bm25", graph_router=adapter)
pipeline = Pipeline(retriever.retrieve, adapter=adapter)
question = Question(79, "Artículo 1 de la Ley 1010 de 2006", "semi_open")
row, trace = pipeline.run(question)

# Uso directo, sin orquestar retrieval:
passages = retrieve(question.text, 8, "off")
row = answer(question, passages, question.format)
validate_submission(row)  # Lanza error; no repara el output.
guard_report = citation_guard(row, passages)
```

`answer` acepta `Question` (ID real) o texto con `question_id=...`; el ID 0 por defecto solo sirve para consultas ad hoc, no para entregar el sample. Rechaza registros crudos del banco. El cargador proyecta exclusivamente `id`, `pregunta`, `formato` y `opciones`, y valida que las opciones solo contengan letras/texto. Las etiquetas no se pasan al normalizador, retrieval, router, política, prompt ni decoder. El evaluador oficial las lee únicamente en su proceso de calificación.

## Normalización y referencias

`normalize_query` devuelve `NormalizedQuery`: original, texto normalizado, texto de búsqueda, referencias con spans originales, autoridades, señales y expansiones. Solo aplica NFC/espacios al texto; conserva números, años, signos, negaciones y temporalidad. Añade hasta cuatro expansiones de un diccionario finito de alias, como CGP → Código General del Proceso. No genera preguntas adicionales. Abreviaturas ambiguas como C.P./C.C. no se expanden.

Reconoce referencias explícitas a normas con número/año, códigos, artículos simples/compuestos/con letra, listas de artículos, sentencias y radicados. No colapsa una ley a un código ignorando el año. Formas incompletas o no resueltas se conservan y bloquean su uso como cita respaldada. Los rangos textuales, referencias implícitas, subnumerales complejos y desambiguación jurídica general requieren ampliación/revisión futura.

## Router y adaptación a A

| Decisión | Condición inicial | Ejecución |
|---|---|---|
| OFF | Pregunta directa con evidencia compatible | Reutiliza la primera recuperación |
| AUTO | Evidencia plana débil, conflictiva o sin referencia explícita solicitada | El adaptador habilita expansión en A |
| ON | Relación normativa, jerarquía, temporalidad o retrieval vacío | Solicita expansión explícita |

El callback de A recibe solo texto y espera un booleano. `RetrieverGraphRouter` enlaza la decisión de B a la consulta exacta y devuelve `bool`, evitando que el string `"off"` active el grafo por ser truthy. Se usa una instancia por pipeline secuencial. Si el caller no proporciona adaptador, el coordinador resuelve AUTO a una llamada ON explícita y deja ambos valores en la traza. El grafo puede no aportar evidencia cuando no hay semillas; la política sigue absteniéndose. El número de activaciones no prueba mejora de retrieval ni del score.

## Política, retrieval y guardas — estado mergeado

- **Bloqueo antes del backend:** texto libre bloquea solo por razones duras: `empty_question`, `retrieval_empty`, `conflicting_evidence` o `ineligible_evidence` (`is_current_text=false` / pasaje no elegible). Referencia ausente/ambigua, solapamiento léxico débil, vigencia no certificada (`unknown`) o falta de relación son advertencias en la traza, no bloqueos. `multiple_choice` nunca pre-bloquea; puede abstenerse después si decoder/guardas lo exigen.
- **Opciones de cerradas:** para `multiple_choice` con opciones, B recupera una variante determinista por opción y las fusiona con RRF (`k=60`) usando exclusivamente la API pública de A. Sin opciones, el flujo de recuperación es el mismo de una sola consulta. Está implementado, pero su efecto real aún no está medido con corpus/GPU.
- **Fallback de citas:** en `Pipeline.run`, un `CitationGuardError` se convierte en abstención para ese ítem usando la misma evidencia y aumenta `citation_guard_fallbacks`; el lote continúa. Esto no altera `answer()` ni `citation_guard` para llamadores directos. JSON/schema/identidad inválidos siguen siendo fallos de corrida, sin publicación parcial ni edición manual.
- Conflictos mecánicos: mismo ID con textos distintos; misma norma/artículo/intervalo con textos distintos; textos del mismo artículo opuestos únicamente por negación modal. No pretende resolver todas las contradicciones jurídicas.
- El dummy también se abstiene cuando hay evidencia suficiente. Nunca copia una opción como respuesta sustantiva ni infiere una conclusión jurídica.
- Cada `pasajes_recuperados` conserva exactamente el texto de A y añade `passage_id`, `doc_id`, URL, identidad normativa, artículo, jerarquía, nodos y hashes disponibles. Omite offsets oficiales opcionales porque `text_prefix` de A no pertenece al intervalo clean.
- Citation guard verifica todas las cadenas emitidas, incluidos keywords y descarte de opciones. Exige fuente/artículo compatibles, referencia visible y evidencia incluida en la salida. Rechaza texto/URL/metadata alterados, pasajes duplicados, citas sin respaldo y respuestas no abstencionistas sin cita verificable. Una mera mención a otra ley dentro de un pasaje no lo convierte en evidencia del artículo de esa otra ley.

**Pendiente de revisión cruzada:** la diferencia cuerpo-versus-artículo frente al evaluador oficial sigue documentada en `docs/B_EXTENSION_PLAN.md` T1b; no se cambió esa semántica en esta reconciliación.

### Contradicción oficial de opción múltiple

La descripción del schema dice que con abstención se admite `null`, pero el `enum` efectivo permite únicamente A/B/C/D, sin excepción. Se conserva el archivo oficial y se cumple su validación: abstención `true`, marcador formal `A`, descarte vacío y justificación que declara explícitamente que esa letra **no representa una elección**. No se consulta la opción esperada. El evaluador excluye estas filas de aciertos de cerradas por estar marcadas como abstención.

## Registro de experimentos

Cada carpeta contiene `questions.jsonl` (solo campos públicos), `submissions.jsonl`, `trace.jsonl`, `evaluation.json` y `experiment.json`. Este último fija:

- versión/hash de corpus y grafo, manifest y archivos oficiales;
- configuración de retrieval, routing, normalización, política, guardas, backend, prompt y generación;
- hashes de implementación de B y fingerprint del experimento;
- valid JSON rate, citas/errores de respaldo, abstenciones y motivos, modos de grafo, latencias, resultado oficial y rutas;
- estado aprobado/fallido, error cuando aplica y módulos neuronales cargados (ninguno en el smoke).

Las carpetas son nuevas por corrida. El fingerprint, JSONL final, decisiones y trazas sin tiempos son reproducibles; timestamps, rutas y latencias cambian. Cero citas emitidas implica tasa sin respaldo cero por convención, sin demostrar calidad de citas. La evidencia positiva/negativa de las guardas está en los tests.

## B v2 en `main` (2026-09-29): planner, 992 robusto y citas

- **Citas:** el decoder razona; `citation_repair.py` corre antes de `citation_guard` (acepta / reescribe a nivel de cuerpo / renombra al nombre de la evidencia / suprime la oración) y `citation_builder.py` escribe la cita final desde `canonical_body` + `article`. Solo se abstiene texto libre si queda vacío un campo obligatorio; las cerradas nunca se abstienen salvo sin evidencia (el validador oficial rechaza una fila no abstenida sin `pasajes_recuperados`). `citation_guard` sigue siendo la verificación final sin cambios de regla.
- **Modos de recuperación:** `Pipeline(retrieval_mode="base"|"option"|"plan")`; default `option`. En `plan`, B llama `retrieve(Q0, k, graph_mode, query_views=[Q1..Q3])`: el locator exacto, el router y el reranker de A solo ven Q0.
- **Ablaciones nuevas optativas (2026-10-01):** `--plan-roles Q2` aísla la vista jurídica de planes congelados; `--option-support` adjunta cosenos Q+opción sobre evidencia final (solo denso/híbrido, no elige opción); `--constrained-json` activa XGrammar 0.2.8. `--retrieval-text-mode context` busca con metadata estructural manteniendo `text` literal. El híbrido contexto requiere primero `tools/build_context_dense_index.py --corpus <corpus> --output <índice alterno>`. Perfiles de instrucciones Qwen están en `config/retrieval_instruction_profiles.json`. Ninguna alternativa está medida/seleccionada y el comportamiento default sigue igual.
- **Planner:** planes congelados con `tools/member_b.py plan --input <jsonl> --model qwen3-8b` en `reports/query_plans/<id>/`; toda comparación los reproduce (`--plans <dir>`). Diagnóstico BASE vs PLAN: `tools/analyze_query_plans.py --plans <dir> --split dev` (solo cuando A entregue el benchmark independiente).
- **992:** `tools/member_b.py batch --input <jsonl> --run-dir runs/<nombre> [--model qwen3-8b] [--exact-locator]` (checkpoints atómicos, `--fresh` para no reanudar, `--synthetic 992` para ensayo). Verificación en vivo: `tools/member_b.py verify --input <jsonl> --delivered <submissions.jsonl> --only 17,203,815`.
- **Sesión GPU sin admin (script único):** `powershell -ExecutionPolicy Bypass -File tools\kingscode_gpu_todo.ps1` en la PC que tiene `corpus\` y GPU: copia limpia de `main`, valida corpus e índice denso, publica corpus+índice, entorno CUDA, decoder, smoke, planes congelados, `sample_50` real con evaluador oficial y proyección a 992.

## Límites y siguiente paso

El **decoder real está preparado** en `kingscode/generation/`, pero no hay pesos reales/bakeoff GPU versionados; tampoco hay calibración, RAGAS ni throughput T6 real. La **UI está implementada** en `interfaz/app.py` y conectada al pipeline, pero no tiene ejecución end-to-end versionada con corpus/GPU. `run.sh`, `Dockerfile` y `.dockerignore` están mergeados; su ejecución completa requiere un snapshot de corpus provisto/preservado y no está verificada en este checkout CPU.

Gate 2-Prep añade código separado para la fase GPU; su estado preparado no equivale a runtime validado. La guarda comprueba identidad de cita y trazabilidad, no implicación semántica de toda una conclusión. Temperatura prevista: 0, `do_sample=false`, semilla 0. Throughput/concurrencia para las 992 preguntas sigue **no implementado ni medido** deliberadamente: no inferir capacidad desde el dummy.

Siguiente comando para repetir Gate 1B: `.venv/Scripts/python.exe tools/member_b.py smoke`. Para GPU, B queda bloqueado hasta que A complete selección interna de retrieval y freeze de ocho pasajes; ver `docs/KINGSCODE_STATE.json`, `docs/BENCHMARK_METHODOLOGY.md` y `reports/benchmark/freeze_handoff/status.json`.

## Comandos preparados para Gate 2

`decoder-smoke --model qwen3-8b`, `sample --model qwen3-8b` y `bakeoff` son ramas nuevas de `tools/member_b.py`. Admiten `--dry-run` para inspección futura sin modelos; no se ejecutaron durante la preparación. Usan `kingscode/generation/`, no sustituyen al dummy y vuelven a pasar por `answer`/citation guard/schema. `sample` requiere evidencia congelada y validada. Runbook completo: `GPU_DAY_RUNBOOK.md`.

La auditoría histórica `verify_member_b_second.py` ahora permite entradas adicionales de decoders en el lock, pero sigue exigiendo igualdad de las dos entradas originales de retrieval. Los informes anteriores que dicen 15 archivos intactos corresponden a Gate 1B; una ejecución futura distingue 14 archivos idénticos más dos entradas originales del lock.

## Corrida sample50 con v7, DocCap 3, diagnóstico de citas y RAGAS

En la PC con RTX 4090, usa el mismo corpus y el mismo checkout congelado durante toda la corrida:

    cd "$HOME\KingsCodeGPU\KingsCodeNvidia"
    git switch main
    git pull --ff-only origin main
    powershell -ExecutionPolicy Bypass -File .\tools\kingscode_pc_nueva_diagnostico.ps1 -Work "$PWD" -RunName "v7_doccap3_bm25_ragas_$(Get-Date -Format yyyyMMdd_HHmmss)" -CorpusSet v01+v02 -RetrieverMode bm25 -PromptVersion v7 -DocCap 3 -Ragas -ShowAnswers -NoPull

RAGAS se aplica a las 35 preguntas de texto libre; el evaluador oficial puntúa las 50. La llave de OpenRouter se pega en el prompt oculto y se elimina de las variables de entorno al terminar. La corrida imprime cada pregunta y respuesta al completarse, y al final muestra correctness, puntos e ítems sin veredicto. El informe post-run diagnostico_citas.json separa citas faltantes por truncamiento, ausencia de la norma en la evidencia y evidencia disponible que el modelo no citó. Los archivos quedan en reports/decoder_diagnostic/<RunName>/; revise el JSON RAGAS si hay timeouts.
