# KingsCode — Hackathon 2026

**Integrantes:** Esteban Alejandro Hernández · Luis Sebastián Contreras Díaz
**Universidad de los Andes** · AI Week 2026

Sistema de respuesta a preguntas de derecho colombiano con un modelo abierto de 8B (Qwen3-8B), un corpus jurídico propio de fuentes oficiales y verificación determinista de cada cita contra la evidencia recuperada.

## Corpus e índice

| Recurso | Enlace | Tamaño | Licencia |
|---|---|---|---|
| Corpus procesado e índice vectorial (`corpus_KingsCode.zip`) | **PENDIENTE_ENLACE** | ver `sha256` en `dist/` | CC BY 4.0 (procesamiento); textos oficiales públicos |

El comprimido contiene `LICENSE`, `corpus_manifest.json`, `corpus/` (un `.txt` por norma o sentencia) e `indice/` (`chunks.jsonl` con los fragmentos y sus metadatos, `bm25.json`, `dense.npy` + `dense.meta.json` del índice vectorial Qwen3-Embedding-0.6B y el grafo normativo). Se genera con `python tools/package_corpus_entrega.py`. El enlace permanece activo hasta el 2 de noviembre de 2026. El corpus también se reconstruye desde las URL declaradas: `python tools/member_a.py acquire` + `reproduce`.

## Arquitectura

| Componente | Elección | Motivo |
|---|---|---|
| Encoder | Qwen/Qwen3-Embedding-0.6B (abierto, revisión fijada), índice vectorial exacto | Multilingüe, reconstruible por script (`tools/member_a.py dense`) |
| Decoder | Qwen/Qwen3-8B, BF16, temperatura 0, *greedy*, sin *thinking*, prompt v6 | Mejor puntaje medido dentro del límite de 8B |
| Segmentación | Un fragmento por artículo (o unidad de sentencia) con norma, artículo, jerarquía y URL | El artículo es la unidad de sentido y permite verificar cada cita |
| Recuperación | BM25 + grafo normativo con router + una consulta por opción (RRF), 8 pasajes | Mejor puntaje por tiempo que el híbrido con reranker (36,93 frente a 36,59; 15,9 frente a 19,1 s/pregunta) |
| Reordenamiento | Qwen3-Reranker-0.6B implementado, no adoptado | No mejoró el puntaje y cuesta ~3 s/pregunta |
| Abstención | Evidencia vacía, en conflicto o no vigente (texto libre); nunca en cerradas; fallas de una pregunta → abstención de esa pregunta | Con la regla oficial, abstenerse casi nunca conviene |

Las citas pasan por una reparación y una guarda deterministas con la misma regla de respaldo del evaluador (10 primeros pasajes): **0 % de citas sin respaldo**. Detalle en [`informe/INFORME_TECNICO.pdf`](informe/INFORME_TECNICO.pdf).

## Reproducción

Con GPU (configuración entregada; Windows, un comando que instala el entorno, descarga el corpus y los modelos fijados por revisión, corre y evalúa la muestra):

```powershell
powershell -ExecutionPolicy Bypass -File tools\kingscode_final.ps1 -Flags "-Recomendada -PromptVersion v6"
# set ciego: ... -InputFile data	est_992.jsonl -RunName final_992   (reanudable con -Resume)
```

Sin GPU, en contenedor limpio (piso determinista sobre las preguntas de muestra):

```bash
pip install -r requirements.txt
./run.sh                       # o: docker build -t kingscode . && docker run --rm kingscode
```

## Entrega

- `submissions.jsonl`: 992 respuestas, validadas con `python tools/validate_test_submission.py --test data/test_992.jsonl submissions.jsonl` (usa `scripts/evaluate.py::validate` y `schema/submission.schema.json`).
- `CORPUS.md` y `corpus_manifest.json`: bitácora e inventario (doc_id, título, fuente, URL, fecha de consulta y áreas).
- `informe/INFORME_TECNICO.pdf`, interfaz en `interfaz/app.py` y video (enlace abajo).
- Video: **PENDIENTE_ENLACE_VIDEO**

## Interfaz gráfica

`interfaz/app.py` (Streamlit, identidad visual de Software Colombia) consulta el mismo pipeline de las corridas (`tools/member_b.py::_pipeline`, configuración v6) y muestra la respuesta, las normas citadas y los pasajes recuperados con su fuente:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-ui.txt
.venv\Scripts\python.exe -m streamlit run interfaz/app.py
```

## Después de clonar

El repositorio incluye código, configuración, inventario de fuentes, manifest y reportes. `corpus/`, `models/`, `.venv/` y `tmp/` permanecen fuera de Git.

En Windows, desde la raíz del proyecto:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-knowledge.txt
.venv/Scripts/python.exe tools/member_a.py acquire
.venv/Scripts/python.exe tools/member_a.py reproduce
.venv/Scripts/python.exe -m unittest discover -s tests -v
```

La adquisición requiere red y `curl` con verificación TLS. Una descarga nueva puede reflejar cambios en las fuentes; para reproducir exactamente los hashes publicados debe usarse el snapshot raw conservado por el equipo. El runbook explica cómo preparar los pesos y ejecutar el benchmark neuronal completo en la GPU objetivo.

Los archivos oficiales se conservan byte a byte. Gate 1B está implementado con dummy y se ejecuta con `.venv/Scripts/python.exe tools/member_b.py smoke` después de disponer del corpus. Decoder real, benchmark neuronal completo, resolución de fuentes pendientes y freeze competitivo siguen pendientes.

Gate 2-Prep añade la infraestructura de ejecución real y comparación de modelos, **sin ejecutar pruebas ni smokes por instrucción del usuario**. No hay resultados nuevos de GPU. Para llegar a la 4090 con el mismo corpus, seguir el runbook GPU y transferir el snapshot conservado, en lugar de volver a adquirir fuentes.

## Estado de A tras RTX 4090 — siguiente fase v0.2

Los resultados GPU están preservados en la rama `feat/member-a-gpu-results-4090-20260928` (60ebf7e). Search V2 saturó las referencias explícitas del benchmark v1 con locator injection; esto no acredita 99–100% en preguntas jurídicas generales. Validation v1 está cerrada y el holdout de arquitectura queda sin usar aquí.

Trabajo actual: `feat/member-a-corpus-v02-locator`. Leer `docs/A_TO_B_V02_CONTRACT.md`, `docs/BENCHMARK_V2_METHODOLOGY.md` y `reports/MEMBER_A_V02_PROGRESS.md`. Corpus-v0.1 inmutable; nuevas fuentes en v0.2. No volver a ejecutar GPU para esta fase CPU.
