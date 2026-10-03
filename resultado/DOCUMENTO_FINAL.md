# Documento final — corrida `mejora_p2`

| Dato | Valor |
|---|---|
| Commit | `aeeda815976cbeb953bd561130e90439aed1f22e` |
| Modelo | qwen3-8b (NVIDIA GeForce RTX 4090, torch 2.14.1+cu126) |
| Recuperación | hybrid (hibrido solo en semi_open,open_ended; resto bm25) candidate_k=30 graph_budget=10 reranker_batch_size=2 k=8 graph router (diagnostico, no freeze) |
| Prompt / citas | grounded-formats-v6 · citation_fill=True · menciones=5 |
| Corpus | corpus_v01_v02_a1 (descarga oficial (acquire + build)) |
| Filas entregadas | 234 · sha256 `a39004376cbbc034d2461a85e248fe41d4c0c9b25c68fb167942f1b2031f54fc` |
| Por formato (n / abstenciones) | open_ended: 17/0 · semi_open: 217/14 |
| Fallbacks del pipeline | 1 [179] |
| Tiempo | 12.2 s/pregunta · proyección 992 = 3.36 h (ventana 6 h; margen exigido ≤ 5 h) |
| Verificación en vivo simulada | ids [8, 144] · coincide = True |

## Entrega (set ciego)

`submissions.jsonl` con 234 filas, sha256 `a39004376cbbc034d2461a85e248fe41d4c0c9b25c68fb167942f1b2031f54fc`. Sin etiquetas: no hay puntaje local.
Conservar esta carpeta y el corpus/modelo intactos hasta terminar la verificación en vivo.

