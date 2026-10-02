# Documento final — corrida `qwen3-8b_bm25_c30_rb2_gb10_pv4_fill_men3_20261002_115609`

| Dato | Valor |
|---|---|
| Commit | `5994024c4f6f0e544c9b618c2f8547f1be41d486` |
| Modelo | qwen3-8b (NVIDIA GeForce RTX 4090, torch 2.14.1+cu126) |
| Recuperación | bm25 candidate_k=30 graph_budget=10 reranker_batch_size=2 k=8 graph router (diagnostico, no freeze) |
| Prompt / citas | grounded-formats-v4 · citation_fill=True · menciones=3 |
| Corpus | corpus_v01_v02_a1 (descarga oficial (acquire + build)) |
| Filas entregadas | 50 · sha256 `78def3f455c2a37f3e2da3293b362ad695fe5dd0b51ed168070a54ec1469715c` |
| Por formato (n / abstenciones) | multiple_choice: 15/0 · open_ended: 5/0 · semi_open: 30/1 |
| Fallbacks del pipeline | 0  |
| Tiempo | 15.9 s/pregunta · proyección 992 = 4.38 h (ventana 6 h; margen exigido ≤ 5 h) |
| Verificación en vivo simulada | ids [51, 24, 247] · coincide = True |

## Puntaje oficial (sample_50, sin RAGAS)

| Componente | Puntos | Detalle |
|---|---:|---|
| Cerradas | 12.0 / 20 | 9/15 |
| Citas | 17.14 / 20 | recall 0.8571 · sin respaldo 0.0 |
| Abstención | 7.79 / 10 | bien 33, mal 9, abstuvo 1 |
| **Total sin RAGAS** | **36.93 / 50** | base 37,46 → Δ -0.53 |

## Calidad del texto libre y de las citas (sin crédito)

| Métrica | Esta corrida | Base 37,46 | Mejor si |
|---|---:|---:|---|
| ROUGE-1 (token-F1) vs respuesta esperada | 0.2737 | 0.275 | sube |
| BLEU-4 | 0.0844 | 0.087 | sube |
| Respuestas > 2× la referencia | 0.206 | 0.229 | baja |
| Respuestas < 0,5× la referencia | 0.176 | 0.114 | no sube |
| Legibilidad (Fernández-Huerta) | 69.5 | 70.2 (ref. 73.5) | cerca de la referencia |
| Citas alineadas con su afirmación | 0.802 | 0.689 | sube |
| Citas débiles (norma real que no sostiene) | 0.119 | 0.109 | baja |

## Taxonomía de fallas

Detalle por área, formato, complejidad y sub-tarea en `qwen3-8b_bm25_c30_rb2_gb10_pv4_fill_men3_20261002_115609/taxonomia.md`.

## Decisión

**No se adopta todavía**: no cumple todos los criterios (total > 37,46, cerradas ≥ 12, 0 sin respaldo, ≤ 5 h).
Si cambia el texto que lee el juez (prompt), confirmar con UNA medición RAGAS (5,46 USD) antes de usarla el sábado.

