# Taxonomía de fallas — `reports\decoder_diagnostic\mejora_muestra\batch\submissions.jsonl`

## Por area

| grupo | n | cerradas | norma citada | fuera de evidencia | en evidencia sin citar | abst | token-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Derecho administrativo | 7 | 2/3 | 3/5 | 2 | 0 | 0 | 0.188 |
| Derecho civil | 4 | 1/1 | 2/2 | 0 | 0 | 0 | 0.223 |
| Derecho comercial y sociedades | 5 | 0/1 | 4/4 | 0 | 0 | 0 | 0.362 |
| Derecho constitucional | 6 | 2/2 | 4/5 | 1 | 0 | 0 | 0.255 |
| Derecho de familia | 5 | 2/2 | 5/5 | 0 | 0 | 0 | 0.46 |
| Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] | 5 | 0/1 | 4/4 | 1 | 0 | 0 | 0.317 |
| Derecho laboral | 5 | 1/1 | 5/5 | 1 | 1 | 0 | 0.286 |
| Derecho penal | 4 | 0/1 | 4/4 | 0 | 0 | 0 | 0.305 |
| Derecho procesal | 5 | 1/2 | 5/5 | 1 | 0 | 0 | 0.229 |
| Derecho tributario | 4 | 1/1 | 2/2 | 0 | 0 | 0 | 0.184 |

## Por formato

| grupo | n | cerradas | norma citada | fuera de evidencia | en evidencia sin citar | abst | token-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| multiple_choice | 15 | 10/15 | 12/13 | 3 | 0 | 0 | - |
| open_ended | 5 | - | 2/4 | 3 | 0 | 0 | 0.286 |
| semi_open | 30 | - | 24/24 | 0 | 1 | 0 | 0.28 |

## Por complejidad

| grupo | n | cerradas | norma citada | fuera de evidencia | en evidencia sin citar | abst | token-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| (sin dato) | 20 | 10/15 | 14/17 | 6 | 0 | 0 | 0.286 |
| high | 10 | - | 9/9 | 0 | 1 | 0 | 0.259 |
| low | 10 | - | 8/8 | 0 | 0 | 0 | 0.284 |
| medium | 10 | - | 7/7 | 0 | 0 | 0 | 0.298 |

## Por sub_tarea

| grupo | n | cerradas | norma citada | fuera de evidencia | en evidencia sin citar | abst | token-F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| (sin dato) | 20 | 10/15 | 14/17 | 6 | 0 | 0 | 0.286 |
| Antecedentes fácticos | 1 | - | - | 0 | 0 | 0 | 0.043 |
| Conflicto normativo | 1 | - | 1/1 | 0 | 0 | 0 | 0.181 |
| Definición básica | 6 | - | 5/5 | 0 | 0 | 0 | 0.312 |
| Distinción conceptual | 1 | - | - | 0 | 0 | 0 | 0.252 |
| Elemento esencial | 1 | - | - | 0 | 0 | 0 | 0.244 |
| Existencia normativa | 2 | - | 2/2 | 0 | 0 | 0 | 0.275 |
| Fundamento jurídico central (ratio decidendi) | 2 | - | 2/2 | 0 | 0 | 0 | 0.262 |
| Jerarquía legal | 1 | - | 1/1 | 0 | 0 | 0 | 0.169 |
| Precedente jurisprudencial | 3 | - | 2/2 | 0 | 0 | 0 | 0.401 |
| Problema jurídico | 6 | - | 6/6 | 0 | 1 | 0 | 0.307 |
| Reproducción literal | 2 | - | 2/2 | 0 | 0 | 0 | 0.337 |
| Requisitos legales | 4 | - | 3/3 | 0 | 0 | 0 | 0.213 |

## Ítems con falla

| id | área | formato | sub_tarea | complejidad | falla |
|---:|---|---|---|---|---|
| 247 | Derecho administrativo | open_ended | - | - | norma fuera de la evidencia (retrieval) |
| 748 | Derecho administrativo | multiple_choice | - | - | cerrada: respondio C esperada A |
| 128 | Derecho comercial y sociedades | multiple_choice | - | - | cerrada: respondio B esperada D |
| 679 | Derecho constitucional | open_ended | - | - | norma fuera de la evidencia (retrieval) |
| 58 | Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] | multiple_choice | - | - | cerrada: respondio D esperada A |
| 600 | Derecho penal | multiple_choice | - | - | cerrada: respondio D esperada C |
| 528 | Derecho procesal | multiple_choice | - | - | cerrada: respondio B esperada C |

## Texto libre con menor token-F1 (candidatos a mejorar RAGAS)

| id | área | sub_tarea | token-F1 |
|---:|---|---|---:|
| 190 | Derecho constitucional | Antecedentes fácticos | 0.043 |
| 879 | Derecho procesal | Requisitos legales | 0.065 |
| 472 | Derecho de los mercados [competencia, consumidor, datos personales y propiedad intelectual] | Requisitos legales | 0.104 |
| 919 | Derecho civil | Problema jurídico | 0.120 |
| 142 | Derecho tributario | Precedente jurisprudencial | 0.133 |
| 247 | Derecho administrativo | - | 0.149 |
| 697 | Derecho comercial y sociedades | Definición básica | 0.155 |
| 442 | Derecho laboral | Reproducción literal | 0.167 |
