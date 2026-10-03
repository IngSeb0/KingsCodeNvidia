# Documento final — corrida `final_p2`

| Dato | Valor |
|---|---|
| Commit | `f7e2f11b3783738c63050aec39e5a6c1459b27d7` |
| Modelo | qwen3-8b (NVIDIA GeForce RTX 4090, torch 2.14.1+cu126) |
| Recuperación | bm25 candidate_k=30 graph_budget=10 reranker_batch_size=2 k=8 graph router (diagnostico, no freeze) |
| Prompt / citas | grounded-formats-v6 · citation_fill=True · menciones=5 |
| Corpus | corpus_v01_v02_a1 (descarga oficial (acquire + build)) |
| Filas entregadas | 496 · sha256 `de6945e7d7b02937363b9c46fe7e1e4971322c7bb881fbe6ae1628cc9373d639` |
| Por formato (n / abstenciones) | semi_open: 496/53 |
| Fallbacks del pipeline | 3 [457, 701, 1010] |
| Tiempo | 11.2 s/pregunta · proyección 992 = 3.09 h (ventana 6 h; margen exigido ≤ 5 h) |
| Verificación en vivo simulada | ids 217 · coincide = True |

## Entrega (set ciego)

`submissions.jsonl` con 496 filas, sha256 `de6945e7d7b02937363b9c46fe7e1e4971322c7bb881fbe6ae1628cc9373d639`. Sin etiquetas: no hay puntaje local.
Conservar esta carpeta y el corpus/modelo intactos hasta terminar la verificación en vivo.

