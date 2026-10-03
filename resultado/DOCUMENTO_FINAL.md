# Documento final — corrida `final_p1`

| Dato | Valor |
|---|---|
| Commit | `f7e2f11b3783738c63050aec39e5a6c1459b27d7` |
| Modelo | qwen3-8b (NVIDIA GeForce RTX 4090, torch 2.14.1+cu126) |
| Recuperación | bm25 candidate_k=30 graph_budget=10 reranker_batch_size=2 k=8 graph router (diagnostico, no freeze) |
| Prompt / citas | grounded-formats-v6 · citation_fill=True · menciones=5 |
| Corpus | corpus_v01_v02_a1 (descarga oficial (acquire + build)) |
| Filas entregadas | 496 · sha256 `6b1cc5ee87900fe4fab15d3d24decbac7886308789467e120e939137e5285d97` |
| Por formato (n / abstenciones) | multiple_choice: 290/12 · open_ended: 50/2 · semi_open: 156/11 |
| Fallbacks del pipeline | 10 [77, 305, 336, 357, 363, 392, 486, 512, 536, 676] |
| Tiempo | 17.9 s/pregunta · proyección 992 = 4.93 h (ventana 6 h; margen exigido ≤ 5 h) |
| Verificación en vivo simulada | ids [1, 2, 39] · coincide = True |

## Entrega (set ciego)

`submissions.jsonl` con 496 filas, sha256 `6b1cc5ee87900fe4fab15d3d24decbac7886308789467e120e939137e5285d97`. Sin etiquetas: no hay puntaje local.
Conservar esta carpeta y el corpus/modelo intactos hasta terminar la verificación en vivo.

