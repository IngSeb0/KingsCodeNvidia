# Taxonomía de fallas — `reports\decoder_diagnostic\qwen3-8b_bm25_c30_rb2_gb10_pv4_fill_men3_20261002_115609\replay_m5\submissions.jsonl`

## Por area

| grupo | n | cerradas | norma citada | fuera de evidencia | en evidencia sin citar | abst | token-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Derecho administrativo | 7 | 2/3 | 3/5 | 2 | 0 | 0 | 0.145 |
| Derecho civil | 4 | 0/1 | 2/2 | 0 | 0 | 0 | 0.339 |
| Derecho comercial y sociedades | 5 | 0/1 | 3/4 | 1 | 0 | 0 | 0.286 |
| Derecho constitucional | 6 | 2/2 | 4/5 | 1 | 0 | 0 | 0.241 |
| Derecho de familia | 5 | 2/2 | 5/5 | 0 | 0 | 0 | 0.45 |
| Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] | 5 | 0/1 | 4/4 | 1 | 0 | 0 | 0.284 |
| Derecho laboral | 5 | 1/1 | 5/5 | 0 | 1 | 0 | 0.264 |
| Derecho penal | 4 | 1/1 | 4/4 | 0 | 0 | 0 | 0.359 |
| Derecho procesal | 5 | 1/2 | 5/5 | 0 | 0 | 0 | 0.247 |
| Derecho tributario | 4 | 0/1 | 2/2 | 0 | 0 | 0 | 0.188 |

## Por formato

| grupo | n | cerradas | norma citada | fuera de evidencia | en evidencia sin citar | abst | token-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| multiple_choice | 15 | 9/15 | 12/13 | 2 | 0 | 0 | - |
| open_ended | 5 | - | 2/4 | 2 | 0 | 0 | 0.276 |
| semi_open | 30 | - | 23/24 | 1 | 1 | 0 | 0.275 |

## Por complejidad

| grupo | n | cerradas | norma citada | fuera de evidencia | en evidencia sin citar | abst | token-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| (sin dato) | 20 | 9/15 | 14/17 | 4 | 0 | 0 | 0.276 |
| high | 10 | - | 8/9 | 1 | 1 | 0 | 0.246 |
| low | 10 | - | 8/8 | 0 | 0 | 0 | 0.27 |
| medium | 10 | - | 7/7 | 0 | 0 | 0 | 0.308 |

## Por sub_tarea

| grupo | n | cerradas | norma citada | fuera de evidencia | en evidencia sin citar | abst | token-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| (sin dato) | 20 | 9/15 | 14/17 | 4 | 0 | 0 | 0.276 |
| Antecedentes fácticos | 1 | - | - | 0 | 0 | 0 | 0.065 |
| Conflicto normativo | 1 | - | 1/1 | 0 | 0 | 0 | 0.0 |
| Definición básica | 6 | - | 5/5 | 0 | 0 | 0 | 0.27 |
| Distinción conceptual | 1 | - | - | 0 | 0 | 0 | 0.224 |
| Elemento esencial | 1 | - | - | 0 | 0 | 0 | 0.367 |
| Existencia normativa | 2 | - | 2/2 | 0 | 0 | 0 | 0.272 |
| Fundamento jurídico central (ratio decidendi) | 2 | - | 1/2 | 1 | 0 | 0 | 0.17 |
| Jerarquía legal | 1 | - | 1/1 | 0 | 0 | 0 | 0.174 |
| Precedente jurisprudencial | 3 | - | 2/2 | 0 | 0 | 0 | 0.313 |
| Problema jurídico | 6 | - | 6/6 | 0 | 1 | 0 | 0.342 |
| Reproducción literal | 2 | - | 2/2 | 0 | 0 | 0 | 0.355 |
| Requisitos legales | 4 | - | 3/3 | 0 | 0 | 0 | 0.303 |

## Ítems con falla

| id | área | formato | sub_tarea | complejidad | falla |
|---:|---|---|---|---|---|
| 247 | Derecho administrativo | open_ended | - | - | norma fuera de la evidencia (retrieval) |
| 748 | Derecho administrativo | multiple_choice | - | - | cerrada: respondio D esperada A |
| 358 | Derecho civil | multiple_choice | - | - | cerrada: respondio A esperada D |
| 128 | Derecho comercial y sociedades | multiple_choice | - | - | cerrada: respondio B esperada D |
| 239 | Derecho comercial y sociedades | semi_open | Fundamento jurídico central (ratio decidendi) | high | norma fuera de la evidencia (retrieval) |
| 679 | Derecho constitucional | open_ended | - | - | norma fuera de la evidencia (retrieval) |
| 58 | Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] | multiple_choice | - | - | cerrada: respondio D esperada A |
| 528 | Derecho procesal | multiple_choice | - | - | cerrada: respondio B esperada C |
| 671 | Derecho tributario | multiple_choice | - | - | cerrada: respondio A esperada C |

## Texto libre con menor token-F1 (candidatos a mejorar RAGAS)

| id | área | sub_tarea | token-F1 |
|---:|---|---|---:|
| 218 | Derecho administrativo | Conflicto normativo | 0.000 |
| 879 | Derecho procesal | Requisitos legales | 0.054 |
| 190 | Derecho constitucional | Antecedentes fácticos | 0.065 |
| 142 | Derecho tributario | Precedente jurisprudencial | 0.067 |
| 239 | Derecho comercial y sociedades | Fundamento jurídico central (ratio decidendi) | 0.082 |
| 79 | Derecho laboral | Existencia normativa | 0.167 |
| 442 | Derecho laboral | Reproducción literal | 0.167 |
| 563 | Derecho administrativo | Jerarquía legal | 0.174 |
