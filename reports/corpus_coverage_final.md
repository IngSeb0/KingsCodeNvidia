# Informe de cobertura del corpus

Reporte de inventario y calidad de fuente; no usa etiquetas de respuesta ni archivos de preguntas.

## Fingerprints y tamaños

| Corpus | Versión | Documentos | Pasajes | Indexados | Excluidos | SHA manifest |
|---|---|---:|---:|---:|---:|---|
| corpus-v0.1 baseline | corpus-v0.1 | 163 | 26558 | 26060 | 498 | `b6c9b022812c7fabb05731a6f36e379ce5e40ad84a12b047781f3c412be23feb` |
| corpus_v03_candidate | corpus-v0.1+v0.2-initial-combined+2-additions | 175 | 27164 | 26666 | 498 | `bd78ccd7094239f9588ee7e3ad7c17bdfc4e1be1933afbf1a90b268cfca647fb` |

Corpus candidato vs base: **+12 documentos**; **+606 pasajes indexables**.

## Cobertura por área

| Área | Documentos | Pasajes indexados |
|---|---:|---:|
| constitutional | 43 | 5659 |
| administrative | 22 | 3825 |
| civil | 24 | 7122 |
| commercial_corporate | 15 | 2338 |
| family | 29 | 5451 |
| labor | 26 | 2415 |
| criminal | 16 | 5985 |
| procedural | 13 | 2600 |
| tax | 19 | 4151 |
| competition | 14 | 2099 |
| consumer | 14 | 2099 |
| data_protection | 14 | 2099 |
| intellectual_property | 14 | 2099 |

## Autoridad y tipo de fuente

| Autoridad | Total documentos | Decisiones |
|---|---:|---:|
| (sin autoridad declarada) | 1 | 1 |
| Comunidad Andina | 1 | 0 |
| Consejo de Estado | 3 | 3 |
| Corte Constitucional | 96 | 96 |
| Corte Suprema de Justicia | 4 | 4 |
| Función Pública | 69 | 0 |
| SENA | 1 | 0 |

## Matriz no vacía: área × autoridad × tipo

| Área | Autoridad | Tipo | Docs | Pasajes indexados | Estado |
|---|---|---|---:|---:|---|
| constitutional | Corte Constitucional | decision | 35 | 3530 | represented |
| constitutional | Función Pública | code | 1 | 1450 | sparse |
| constitutional | Función Pública | constitution | 1 | 462 | sparse |
| constitutional | Función Pública | decree | 1 | 54 | sparse |
| constitutional | Función Pública | law | 5 | 163 | limited |
| administrative | Consejo de Estado | decision | 3 | 162 | limited |
| administrative | Corte Constitucional | decision | 7 | 972 | represented |
| administrative | Función Pública | code | 2 | 620 | limited |
| administrative | Función Pública | constitution | 1 | 462 | sparse |
| administrative | Función Pública | decree | 2 | 1087 | limited |
| administrative | Función Pública | law | 7 | 522 | represented |
| civil | Corte Constitucional | decision | 13 | 1155 | represented |
| civil | Función Pública | code | 3 | 2201 | represented |
| civil | Función Pública | decree | 1 | 233 | sparse |
| civil | Función Pública | law | 6 | 850 | represented |
| civil | SENA | code | 1 | 2683 | sparse |
| commercial_corporate | Comunidad Andina | other | 1 | 280 | sparse |
| commercial_corporate | Consejo de Estado | decision | 1 | 78 | sparse |
| commercial_corporate | Corte Constitucional | decision | 3 | 142 | limited |
| commercial_corporate | Función Pública | code | 1 | 659 | sparse |
| commercial_corporate | Función Pública | constitution | 1 | 462 | sparse |
| commercial_corporate | Función Pública | decree | 3 | 436 | represented |
| commercial_corporate | Función Pública | law | 5 | 281 | limited |
| family | Corte Constitucional | decision | 19 | 1314 | represented |
| family | Función Pública | code | 2 | 884 | limited |
| family | Función Pública | constitution | 1 | 462 | sparse |
| family | Función Pública | decree | 1 | 8 | sparse |
| family | Función Pública | law | 5 | 100 | limited |
| family | SENA | code | 1 | 2683 | sparse |
| labor | Consejo de Estado | decision | 1 | 72 | sparse |
| labor | Corte Constitucional | decision | 12 | 637 | represented |
| labor | Corte Suprema de Justicia | decision | 2 | 36 | sparse |
| labor | Función Pública | code | 1 | 504 | sparse |
| labor | Función Pública | constitution | 1 | 462 | sparse |
| labor | Función Pública | decree | 1 | 3 | sparse |
| labor | Función Pública | law | 8 | 701 | represented |
| criminal | Corte Constitucional | decision | 8 | 1400 | represented |
| criminal | Corte Suprema de Justicia | decision | 2 | 42 | sparse |
| criminal | Función Pública | code | 2 | 1247 | limited |
| criminal | Función Pública | constitution | 1 | 462 | sparse |
| criminal | Función Pública | decree | 1 | 2364 | sparse |
| criminal | Función Pública | law | 2 | 470 | limited |
| procedural | Consejo de Estado | decision | 3 | 162 | limited |
| procedural | Corte Constitucional | decision | 2 | 112 | limited |
| procedural | Función Pública | code | 3 | 1521 | represented |
| procedural | Función Pública | constitution | 1 | 462 | sparse |
| procedural | Función Pública | law | 4 | 343 | represented |
| tax | Consejo de Estado | decision | 1 | 12 | sparse |
| tax | Corte Constitucional | decision | 8 | 349 | represented |
| tax | Función Pública | code | 2 | 2109 | limited |
| tax | Función Pública | constitution | 1 | 462 | sparse |
| tax | Función Pública | decree | 2 | 123 | limited |
| tax | Función Pública | law | 5 | 1096 | represented |
| competition | Comunidad Andina | other | 1 | 280 | sparse |
| competition | Corte Constitucional | decision | 2 | 333 | limited |
| competition | Función Pública | code | 2 | 751 | limited |
| competition | Función Pública | constitution | 1 | 462 | sparse |
| competition | Función Pública | decree | 2 | 99 | limited |
| competition | Función Pública | law | 6 | 174 | limited |
| consumer | Comunidad Andina | other | 1 | 280 | sparse |
| consumer | Corte Constitucional | decision | 2 | 333 | limited |
| consumer | Función Pública | code | 2 | 751 | limited |
| consumer | Función Pública | constitution | 1 | 462 | sparse |
| consumer | Función Pública | decree | 2 | 99 | limited |
| consumer | Función Pública | law | 6 | 174 | limited |
| data_protection | Comunidad Andina | other | 1 | 280 | sparse |
| data_protection | Corte Constitucional | decision | 2 | 333 | limited |
| data_protection | Función Pública | code | 2 | 751 | limited |
| data_protection | Función Pública | constitution | 1 | 462 | sparse |
| data_protection | Función Pública | decree | 2 | 99 | limited |
| data_protection | Función Pública | law | 6 | 174 | limited |
| intellectual_property | Comunidad Andina | other | 1 | 280 | sparse |
| intellectual_property | Corte Constitucional | decision | 2 | 333 | limited |
| intellectual_property | Función Pública | code | 2 | 751 | limited |
| intellectual_property | Función Pública | constitution | 1 | 462 | sparse |
| intellectual_property | Función Pública | decree | 2 | 99 | limited |
| intellectual_property | Función Pública | law | 6 | 174 | limited |

Celdas vacías en la matriz: **469**. `sparse` significa una sola fuente o menos de 50 pasajes indexados; `limited` significa menos de tres fuentes o 300 pasajes. Son señales cuantitativas de inventario, no conclusiones sobre calidad jurídica.

## Procedencia y controles

- Colisiones de cuerpo canónico: 0.
- Grupos de texto de pasaje duplicado exacto: 0 (0 entre documentos).
- Fallas de parser registradas: 0; adquisiciones fallidas: 0; documentos incompletos/bloqueados: 1.
- Referencias grafo→nodo faltantes: 0.
- Nodos aislados: 0.
- Backlog de adquisición sin resolver: 28.
- Los documentos mantienen URL, fecha de adquisición, SHA-256 de fuente, parser y conteos en `source_inventory` dentro del JSON.
- No se leyó `data/test_992.jsonl`; el diagnóstico no admite preguntas ni respuestas.

## Fuentes adquiridas en esta rama

Ver [CORPUS_V03_ACQUISITION_PLAN.md](../docs/CORPUS_V03_ACQUISITION_PLAN.md) para criterios y URLs oficiales.
