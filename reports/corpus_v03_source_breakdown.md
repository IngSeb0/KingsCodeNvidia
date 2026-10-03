# Desglose Member-A C0/C1 por área, tipo de fuente y autoridad

- Rama/commit: `codex/corpus-first-final-improvement-20261003` / `65f4fe133d6a28c8463a7689dad7b1c3dfc0aa91`
- Benchmark DEV: `326a405748dd20f641d5cf4103ceaafb6a19f07b43db54d95f472a2b439e3071`; n=120; ambos R0/BM25.
- Las métricas de subgrupo son descriptivas; la adopción usa la puerta pareada de 10.000 remuestras.
- La muestra v1 no tiene preguntas semánticas/generales y no contiene gold para las nuevas fuentes del Consejo de Estado.

## area

| Grupo | n | Recall@1 C0→C1 | Recall@5 | Recall@10 | MRR@10 | EC@8 | DocRecall@10 | Mismatch | Docs@10 | latencia media ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Derecho administrativo | 12 | 0.250→0.250 | 0.625→0.625 | 0.750→0.750 | 0.441→0.420 | 0.583→0.583 | 1.000→1.000 | 0.000→0.000 | 1.000→1.000 | 67.244→66.423 |
| Derecho civil | 12 | 0.083→0.083 | 0.167→0.250 | 0.333→0.500 | 0.133→0.154 | 0.250→0.250 | 1.000→1.000 | 0.000→0.000 | 1.083→1.083 | 68.398→68.241 |
| Derecho comercial y sociedades | 12 | 0.250→0.250 | 0.583→0.583 | 0.917→0.917 | 0.395→0.393 | 0.833→0.750 | 1.000→1.000 | 0.000→0.000 | 1.750→1.750 | 76.445→66.991 |
| Derecho constitucional | 12 | 0.000→0.000 | 0.083→0.083 | 0.333→0.333 | 0.085→0.085 | 0.167→0.167 | 1.000→1.000 | 0.000→0.000 | 2.667→2.667 | 73.051→55.600 |
| Derecho de familia | 12 | 0.167→0.167 | 0.667→0.667 | 0.750→0.750 | 0.410→0.410 | 0.667→0.667 | 1.000→1.000 | 0.000→0.000 | 1.000→1.000 | 65.095→64.640 |
| Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] | 12 | 0.083→0.083 | 0.167→0.167 | 0.500→0.500 | 0.178→0.178 | 0.333→0.333 | 1.000→1.000 | 0.083→0.083 | 1.833→1.583 | 61.871→75.822 |
| Derecho laboral | 12 | 0.083→0.083 | 0.625→0.625 | 0.750→0.750 | 0.266→0.266 | 0.667→0.667 | 1.000→1.000 | 0.000→0.000 | 1.000→1.000 | 60.057→62.965 |
| Derecho penal | 12 | 0.417→0.417 | 0.667→0.667 | 0.750→0.750 | 0.544→0.544 | 0.583→0.583 | 1.000→1.000 | 0.000→0.000 | 2.083→1.917 | 67.883→66.201 |
| Derecho procesal | 12 | 0.083→0.083 | 0.208→0.208 | 0.667→0.667 | 0.199→0.198 | 0.583→0.500 | 1.000→1.000 | 0.000→0.000 | 2.167→2.083 | 66.739→63.717 |
| Derecho tributario | 12 | 0.208→0.208 | 0.583→0.583 | 0.750→0.750 | 0.412→0.412 | 0.667→0.667 | 1.000→1.000 | 0.167→0.167 | 2.000→1.750 | 66.447→63.095 |

## source_type

| Grupo | n | Recall@1 C0→C1 | Recall@5 | Recall@10 | MRR@10 | EC@8 | DocRecall@10 | Mismatch | Docs@10 | latencia media ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| normative | 120 | 0.163→0.163 | 0.438→0.446 | 0.650→0.667 | 0.306→0.306 | 0.533→0.517 | 1.000→1.000 | 0.025→0.025 | 1.658→1.583 | 67.323→65.370 |

## authority

| Grupo | n | Recall@1 C0→C1 | Recall@5 | Recall@10 | MRR@10 | EC@8 | DocRecall@10 | Mismatch | Docs@10 | latencia media ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Función Pública | 96 | 0.172→0.172 | 0.443→0.443 | 0.677→0.677 | 0.315→0.312 | 0.552→0.531 | 1.000→1.000 | 0.031→0.031 | 1.812→1.719 | 67.467→65.102 |
| SENA | 24 | 0.125→0.125 | 0.417→0.458 | 0.542→0.625 | 0.272→0.282 | 0.458→0.458 | 1.000→1.000 | 0.000→0.000 | 1.042→1.042 | 66.746→66.440 |

## reference_class

| Grupo | n | Recall@1 C0→C1 | Recall@5 | Recall@10 | MRR@10 | EC@8 | DocRecall@10 | Mismatch | Docs@10 | latencia media ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| explicit | 120 | 0.163→0.163 | 0.438→0.446 | 0.650→0.667 | 0.306→0.306 | 0.533→0.517 | 1.000→1.000 | 0.025→0.025 | 1.658→1.583 | 67.323→65.370 |

## Alcance

- `explicit`: casos etiquetados EXPLICIT por el benchmark. No hay fila semántica/general porque el denominador es cero.
- `normative` agrupa law/decree/code/constitution; `jurisprudence` agrupa decision. Casos con evidencia gold de más de una clase se etiquetan MIXED.
- `authority` proviene de `fuente` del manifiesto del documento gold. El Consejo de Estado no aparece en estos estratos porque el v1 gold fue fijado sobre v0.1.
- Ningún resultado de esta tabla habilita sample_50: revisar `reports/corpus_v03_independent_retrieval_comparison.json`.
