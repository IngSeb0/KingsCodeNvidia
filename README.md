# KingsCode — Hackathon 2026

**Integrantes:** Esteban Alejandro Hernández · Luis Sebastián Contreras Díaz
**Universidad de los Andes** · AI Week 2026 · Patrocina Software Colombia

Sistema de respuesta a preguntas de derecho colombiano con un modelo abierto de 8B (Qwen3-8B), un corpus jurídico propio construido desde fuentes oficiales y verificación determinista de cada cita contra la evidencia recuperada.

## Corpus e índice

| Recurso | Enlace | Licencia |
|---|---|---|
| Corpus procesado e índice vectorial (`corpus_KingsCode.zip`, 105,7 MB, SHA-256 `30522f8a52967221…`) | [Descargar](https://github.com/IngSeb0/KingsCodeNvidia/releases/download/corpus-final/corpus_KingsCode.zip) · [página de la publicación](https://github.com/IngSeb0/KingsCodeNvidia/releases/tag/corpus-final) | CC BY 4.0 (procesamiento); textos oficiales públicos |

El comprimido contiene:

- `LICENSE`
- `corpus_manifest.json`: un registro por documento con `doc_id`, título, fuente, URL, fecha de consulta y áreas.
- `corpus/`: un `.txt` limpio por norma o sentencia.
- `indice/`, con estos archivos:
  - `chunks.jsonl`: un fragmento por artículo o unidad de sentencia, con `passage_id`, `doc_id`, artículo, *offsets*, jerarquía, URL y texto.
  - `dense.npy` + `dense.meta.json`: el índice vectorial Qwen3-Embedding-0.6B.
  - `bm25.json`: el índice léxico.
  - `graph/`: el grafo normativo, con sus relaciones *modifica*, *deroga*, *remite a* y *reglamenta*.

Se genera con `python tools/package_corpus_entrega.py`. El enlace permanece activo hasta el 2 de noviembre de 2026.

El corpus también se reconstruye desde las URL declaradas con `python tools/member_a.py acquire` seguido de `reproduce`. Detalle en [`CORPUS.md`](CORPUS.md).

## Arquitectura

```
pregunta ─► normalización (alias de normas, señales de vigencia/remisión)
         ─► recuperación ─► BM25 por artículo
                          + búsqueda semántica (Qwen3-Embedding-0.6B, fusión RRF) en preguntas de texto libre
                          + una consulta por opción en selección múltiple (RRF)
                          + grafo normativo (router: solo si la pregunta habla de modificaciones, derogatorias, remisiones…)
         ─► 8 pasajes ─► Qwen3-8B (BF16, temperatura 0, greedy) con prompt v6 ─► JSON del esquema oficial
         ─► reparación y guarda de citas (cada norma citada debe estar en los pasajes) ─► submissions.jsonl
```

| Componente | Elección | Motivo |
|---|---|---|
| Corpus | 170 normas y sentencias de fuentes oficiales; 26.665 fragmentos | Trazabilidad: cada fragmento conserva URL, hash de la fuente y posición en el texto |
| Segmentación | Un fragmento por artículo (o unidad de sentencia) | En derecho el artículo es la unidad de cita: cada pasaje ya trae la norma exacta |
| Encoder | Qwen/Qwen3-Embedding-0.6B, revisión fijada, búsqueda exacta por coseno | Abierto y multilingüe; encuentra la norma por su significado cuando no comparte palabras con la pregunta |
| Recuperación léxica | BM25 + grafo + consultas por opción | Fue la mejor medida en la muestra para selección múltiple |
| Decoder | Qwen/Qwen3-8B, BF16, temperatura 0, `do_sample=False`, prompt v6 | Mejor puntaje medido dentro del límite de 8B |
| Reordenamiento | Qwen3-Reranker-0.6B implementado; no adoptado | No mejoró el puntaje y añade ~3 s por pregunta |
| Citas | Reparación y guarda deterministas con la regla del evaluador (10 primeros pasajes) | **0 % de citas sin respaldo** |
| Abstención | Solo con evidencia vacía, en conflicto o no vigente (texto libre); nunca en selección múltiple | Con la regla oficial, abstenerse casi nunca conviene |

### Resultados en la muestra de 50 (evaluador oficial, sin RAGAS)

| Configuración | Puntaje |
|---|---:|
| BM25, prompt v4 | 37,46 |
| BM25, prompt v6 | 38,08 |
| BM25, prompt v4, corpus final | **39,02** |
| Búsqueda semántica + BM25 en todos los formatos | 34,83 (baja en selección múltiple) |

**Hallazgo de la verificación con el jurado.**
- En casos largos de texto libre, BM25 suma palabras sueltas (por ejemplo "VIH", "medicamento", "pacientes") y recupera sentencias de salud.
- Así no encuentra la Ley 1581 de 2012 (datos sensibles), que habla de "Titular", "Tratamiento" y "autorización".
- Por eso la configuración final activa la búsqueda semántica **solo en preguntas de respuesta breve y casos abiertos** (`--hybrid-formats semi_open,open_ended`). Selección múltiple conserva el camino BM25 medido.

## Reproducción

Requisitos: Windows o Linux, GPU NVIDIA de 24 GB (probado en RTX 4090), Python 3.12. Dependencias en `requirements.txt` (incluye `requirements-gpu.txt` y `requirements-ui.txt`).

**Comando único (Windows):** prepara el entorno, descarga el corpus y los modelos fijados por revisión, corre y evalúa:

```powershell
powershell -ExecutionPolicy Bypass -File tools\kingscode_final.ps1 -Flags "-Recomendada -PromptVersion v6"
# set ciego:  ... -InputFile data\test_992.jsonl -RunName final_992      (reanudable con -Resume)
```

**Entrega repartida en varias GPU:**

```powershell
powershell -ExecutionPolicy Bypass -File tools\kingscode_mitad.ps1 -Parte 1      # y -Parte 2 en otra GPU
powershell -ExecutionPolicy Bypass -File tools\kingscode_mejora.ps1 -Parte 1     # búsqueda semántica en texto libre, partes 1..3
python tools\unir_entrega.py unir --base final_p1.jsonl final_p2.jsonl [--mejora mejora_p1.jsonl mejora_p2.jsonl mejora_p3.jsonl]
```

**Sin GPU, en contenedor limpio** (piso determinista sobre las preguntas de muestra):

```bash
pip install -r requirements.txt
./run.sh                       # o: docker build -t kingscode . && docker run --rm kingscode
```

**Determinismo:** temperatura 0, *greedy*, semilla fija y `torch.use_deterministic_algorithms(True)`. La verificación en vivo regenera un id con el mismo commit, corpus y configuración y compara las normas citadas y los pasajes (`tools/member_b.py verify`).

## Entrega

- `submissions.jsonl`: las 992 respuestas.
  - Generadas con Qwen3-8B, prompt v6 y el corpus de `passages.jsonl` con SHA-256 `58135a0c…`.
  - 298 de las 702 preguntas de texto libre se regeneraron con búsqueda semántica (BM25 + Qwen3-Embedding); las demás usan BM25. Cada fila viene completa de una sola corrida, y [`docs/ENTREGA_ORIGEN_FILAS.json`](docs/ENTREGA_ORIGEN_FILAS.json) indica cuál, para la verificación en vivo.
  - Validadas con `python tools/validate_test_submission.py --test data/test_992.jsonl submissions.jsonl`, que usa `scripts/evaluate.py::validate` y `schema/submission.schema.json`.
  - 0 problemas.
- `CORPUS.md` y `corpus_manifest.json`: la bitácora y el inventario de fuentes.
- `informe/INFORME_TECNICO.pdf`: el informe técnico (máximo 3 páginas).
- `interfaz/`: la interfaz gráfica.
- Video (4:58): [`video/KingsCode_video.mp4`](video/KingsCode_video.mp4)

## Interfaz gráfica

`interfaz/app.py` está hecha en Streamlit, con la identidad visual y el logo de Software Colombia.

- Usa el mismo pipeline de las corridas (`tools/member_b.py::_pipeline`).
- Permite cargar una pregunta por id o escribir una nueva.
- Muestra la respuesta, las normas citadas y los pasajes recuperados con su fuente.
- La casilla **Búsqueda semántica** se activa sola cuando existe el índice vectorial del corpus.

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-ui.txt
.venv\Scripts\python.exe -m streamlit run interfaz/app.py
```

## Estructura

| Ruta | Contenido |
|---|---|
| `kingscode/` | Pipeline: adquisición, corpus, BM25/denso/grafo (`retrieval.py`, `neural.py`), razonamiento, guardas y citas (`reasoning/`), decoder (`generation/`) |
| `tools/` | CLI de corrida (`member_b.py`), corpus (`member_a.py`), empaquetado, validación y scripts de GPU |
| `interfaz/` | Interfaz gráfica |
| `config/` | Fuentes, revisiones fijadas de los modelos, perfiles |
| `tests/` | Pruebas unitarias (`python -m unittest discover -s tests`) |
| `docs/` | Bitácora de decisiones (`DECISION_LOG.md`), arquitectura y runbooks |

Los archivos oficiales (`scripts/`, `schema/`, `data/`, `entregables/`) se conservan byte a byte. `corpus/`, `models/` y `.venv/` no se versionan.
