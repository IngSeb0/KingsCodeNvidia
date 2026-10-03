# Documento final — corrida `mejora_muestra`

| Dato | Valor |
|---|---|
| Commit | `aeeda815976cbeb953bd561130e90439aed1f22e` |
| Modelo | qwen3-8b (NVIDIA GeForce RTX 4090, torch 2.14.1+cu126) |
| Recuperación | hybrid (hibrido solo en semi_open,open_ended; resto bm25) candidate_k=30 graph_budget=10 reranker_batch_size=2 k=8 graph router (diagnostico, no freeze) |
| Prompt / citas | grounded-formats-v6 · citation_fill=True · menciones=5 |
| Corpus | corpus_v01_v02_a1 (descarga oficial (acquire + build)) |
| Filas entregadas | 50 · sha256 `f713712c3ff607b71cbb42769b872a2bd0818d8c04007f6327bc7bcce3d1cd01` |
| Por formato (n / abstenciones) | multiple_choice: 15/0 · open_ended: 5/0 · semi_open: 30/0 |
| Fallbacks del pipeline | 0  |
| Tiempo | 16.0 s/pregunta · proyección 992 = 4.41 h (ventana 6 h; margen exigido ≤ 5 h) |
| Verificación en vivo simulada | ids [51, 24, 247] · coincide = True |

## Puntaje oficial (sample_50, sin RAGAS)

| Componente | Puntos | Detalle |
|---|---:|---|
| Cerradas | 13.33 / 20 | 10/15 |
| Citas | 17.14 / 20 | recall 0.8571 · sin respaldo 0.0 |
| Abstención | 8.37 / 10 | bien 36, mal 7, abstuvo 0 |
| **Total sin RAGAS** | **38.84 / 50** | base 37,46 → Δ +1.38 |

## Calidad del texto libre y de las citas (sin crédito)

| Métrica | Esta corrida | Base 37,46 | Mejor si |
|---|---:|---:|---|
| ROUGE-1 (token-F1) vs respuesta esperada | 0.2809 | 0.275 | sube |
| BLEU-4 | 0.0944 | 0.087 | sube |
| Respuestas > 2× la referencia | 0.257 | 0.229 | baja |
| Respuestas < 0,5× la referencia | 0.171 | 0.114 | no sube |
| Legibilidad (Fernández-Huerta) | 71.8 | 70.2 (ref. 73.1) | cerca de la referencia |
| Citas alineadas con su afirmación | 0.653 | 0.689 | sube |
| Citas débiles (norma real que no sostiene) | 0.174 | 0.109 | baja |

## Taxonomía de fallas

Detalle por área, formato, complejidad y sub-tarea en `mejora_muestra/taxonomia.md`.

## Decisión

**Se adopta**: supera 37,46, no baja cerradas, 0 citas sin respaldo y cabe en ≤ 5 h.
Si cambia el texto que lee el juez (prompt), confirmar con UNA medición RAGAS (5,46 USD) antes de usarla el sábado.

