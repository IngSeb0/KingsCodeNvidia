# src — pipeline reproducible

El código fuente del pipeline vive en el paquete Python `kingscode/` (raíz del repositorio), que se importa con ese nombre desde las herramientas y las pruebas:

| Ruta | Contenido |
|---|---|
| `kingscode/acquisition.py`, `corpus.py` | Adquisición desde fuentes oficiales y construcción del corpus por artículo |
| `kingscode/retrieval.py`, `neural.py` | BM25, índice vectorial Qwen3-Embedding-0.6B, fusión RRF y grafo normativo |
| `kingscode/reasoning/` | Normalización, enrutamiento del grafo, abstención, guarda y reparación de citas, ejecución por lotes |
| `kingscode/generation/` | Decoder Qwen3-8B (Transformers, BF16, temperatura 0) y prompts por formato |
| `tools/member_b.py` | Punto de entrada: `batch`, `verify` |
| `tools/kingscode_final.ps1` | Comando único de reproducción |

Ver la sección Reproducción del `README.md` de la raíz.
