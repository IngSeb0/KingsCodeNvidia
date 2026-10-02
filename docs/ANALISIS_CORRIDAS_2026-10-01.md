# Análisis de todas las corridas del 2026-10-01

**Fuentes:** rama `lab/export-20261001_162136` (commit `0e351ac`; 9 corridas de `sample_50` y 7 pilotos de 12 preguntas en `turing`), rama `lab/c1-30.41-20261001` (corrida c1) y rama `lab/hybrid-logs-20261001_161915` (matriz híbrida en la 4090 de Luis).

**Método:** `tools/analyze_run.py` por corrida, más un cruce de todas las corridas. Las etiquetas de `sample_50` (letra esperada y `legal_basis`) se usan solo para medir, nunca dentro del pipeline. Las respuestas por pregunta en 50 ítems son diagnóstico, no criterio de selección.

## 1. Resumen por corrida

| Corrida (turing salvo indicación) | n | Prompt | Retrieval | Rerank | Fill | Cerradas | Citas ref. | Abst. | Fallbacks | s/preg | Gen. p50 | VRAM máx |
|---|---:|---|---|:-:|:-:|---:|---:|---:|---:|---:|---:|---:|
| bm25 10:14 (eager, interrumpida) | 45 | v3 | bm25 | – | – | 4/15 | 3/36 | 36 | 34 | – | 130 s | 46,0 GB |
| bm25 11:25 (SDPA, parser estricto) | 50 | v3 | bm25 | – | – | 4/15 | 11/41 | 34 | 31 | 15,2 | 12,4 s | 17,8 |
| bm25 base 11:52 (26,63) | 50 | v3 | bm25 | – | – | 7/15 | 26/41 | 4 | 1 | 15,2 | 13,3 s | 17,8 |
| + locator sin reranker | 50 | v3 | bm25 | – | – | 7/15 | 26/41 | 4 | 1 | 15,2 | 13,5 s | 17,8 |
| v4 (27,68) | 50 | v4 | bm25 | – | – | 8/15 | 24/41 | 3 | 2 | 15,4 | 12,2 s | 17,8 |
| **c1: v4 + fill (30,41)** | 50 | v4 | bm25 | – | ✓ | 8/15 | 29/41 | 3 | 2 | 15,6 | 12,5 s | 17,8 |
| c2: v4 + fill + rerank + locator (27,69) | 50 | v4 | bm25 | ✓ | ✓ | 6/15 | 30/41 | 3 | 3 | 18,5 | 13,3 s | 19,1 |
| c3: híbrido (23,74) | 50 | v3 | hybrid | – | – | 5/15 | 26/41 | 6 | 2 | 15,2 | 13,4 s | 19,0 |
| c4: todo + híbrido (30,82) | 50 | v4 | hybrid | ✓ | ✓ | 7/15 | 31/41 | 7 | 7 | 18,7 | 12,5 s | 20,2 |
| Pilotos híbrido + rerank (7 variantes) | 12 | v4/v5 | hybrid | ✓ | – | 1–2/4 | 5–7/9 | 0–2 | 0–2 | 22,8–30,8 | 16–20 s | 20,2 |
| **Luis**, matriz híbrida (4090 de su PC) | 9–12 | v3 | hybrid | ✓ | – | 1–2/4 | 3–4/7 | 1–7 | 0–7 | **358** | **88–252 s** | **43–53 GB** |

"Citas ref." = ítems donde se cita algún cuerpo normativo del `legal_basis`, sobre los 41 que tienen uno reconocible por el extractor oficial.

## 2. Hallazgos

1. **Todos los fallbacks que quedan en `turing` son respuestas cortadas por el límite de tokens:** 21 cerradas en 512 y 3 abiertas en 1024. Ninguno es prosa alrededor del JSON. El prompt v4 pone la justificación primero y alarga las cerradas. **Cambios:** cerradas a 768 (PR #33) y abiertas a 1.280. Si la entrada más la salida no caben en 8.192, el ajuste de contexto omite los pasajes de menor rango.
2. **Los errores de cerradas son estables entre configuraciones**, no ruido:
   - 128 elige B (esperada D) en 6 de 7 corridas, citando la norma correcta: error de razonamiento.
   - 671 elige A (esperada C) en 6 de 7.
   - 748 elige C (esperada A) y su norma nunca se recupera.
   - 58 elige D (esperada A) salvo con reranker.
   - 352 acierta siempre.
   - 51 nunca llega a responder: siempre se trunca.

   Cambiar retrieval o prompt mueve pocas preguntas; el límite está en la evidencia y en el razonamiento de 8B.
3. **Normas de referencia que ninguna configuración recupera** (51, 247, 563, 679, 748): falta en el corpus o falla de recuperación. Es trabajo de A y del corpus, no del decoder.
4. **Normas "en la evidencia pero no citadas"** (661, 1073, 647, 358 y, según la corrida, 58, 60, 218, 490, 865): en todos los casos revisados, la norma de referencia **no es el documento del pasaje**. Está **mencionada dentro** del texto de otro (p. ej. la Constitución dentro de la Sentencia C-891 de 2012; el Código Civil dentro de la C-985 de 2010). El constructor de citas solo cita el cuerpo propio de cada pasaje, y la guarda (`reference_support`) rechaza las normas solo mencionadas, por diseño: "una mención no prueba el contenido". El evaluador oficial sí cuenta como respaldada cualquier norma que aparezca en el texto de los 10 primeros pasajes.
   - **Implementado como opción (`--cite-mentions`), pendiente de revisión de Luis:** con `--citation-fill`, agregar a nivel de cuerpo (sin artículo) las normas mencionadas en los pasajes que el modelo declaró usar, solo en `referencia_legal`/`justificacion` (RAGAS no los lee). Implica relajar la guarda para menciones a nivel de cuerpo.
   - **Impacto estimado:** unos 4–6 ítems más con cita correcta sobre 41, es decir +1,5 a +2,5 puntos de citas.
   - **Riesgo:** citar cuerpos que el pasaje solo nombra. Según el enunciado §6.1, una cita "incorrecta pero respaldada" vale 0, sin penalización.
5. **Reranker y locator** suben las citas (+1 o 2 ítems), pero bajan las cerradas y agregan 3 s por pregunta. El retrieval p95 de c2/c4 es de unos 11 s, y en esas corridas aparecen más truncamientos.
6. **Pilotos híbrido + rerank (12 preguntas):** todos van a 22,8–30,8 s/pregunta, por encima del presupuesto de 20 s. Con 4 cerradas y 9 citas por piloto no se puede elegir una variante. `context_representation` es la más lenta (30,8 s). Ninguno justifica adoptarse antes del sábado.
7. **PC de Luis:** generación p50 de 88–252 s y VRAM reservada de 43–53 GB en una tarjeta de 24 GB. Es el mismo desborde a RAM del sistema que tuvo `turing` antes de SDPA. Sus tiempos no son válidos para presupuestar. Hay que revisar en su máquina:
   - confirmar el commit y la configuración real: los errores de los ítems 253 y 679 ya registran `attn_implementation: sdpa`, por lo que SDPA por sí solo no explica ni resuelve el desborde;
   - que no haya otros procesos usando la GPU;
   - la opción del Panel de NVIDIA "CUDA - Sysmem Fallback Policy" = "Prefer No Sysmem Fallback".

## 3. Recomendación

- **Configuración del sábado:** c1, es decir Qwen3-8B BF16 + BM25 + router, prompt v4 y `--citation-fill`, con los límites nuevos de tokens (cerradas 768, abiertas 1.280) y `-NoPull`.
- **Antes del sábado:**
  - una corrida de c1 con los límites nuevos sobre el commit congelado;
  - una única medición con RAGAS, con autorización.
- **Para Luis:**
  - revisar la propuesta de citas mencionadas (punto 4);
  - corregir el desborde de VRAM en su PC;
  - ver las normas nunca recuperadas (punto 3).

## 4. Cómo reproducir este análisis

```powershell
git fetch upstream lab/export-20261001_162136
git archive upstream/lab/export-20261001_162136 reports/decoder_diagnostic | tar -x -C C:\tmp\runs
python tools/analyze_run.py C:\tmp\runs\reports\decoder_diagnostic\<corrida>\batch --labels
```

`revision.md` muestra cada pregunta: respuesta final, error y salida cruda si hubo, correcciones del parser, reparación de citas, pasajes declarados por el modelo, evidencia con norma y artículo, tokens y tiempos.

Las trazas muestran las respuestas y la evidencia, no el razonamiento interno de Qwen (`enable_thinking=false`). `unsupported_citations=0` verifica identidad textual de la fuente, no que la afirmación esté jurídicamente demostrada. En c1, 31 de 130 referencias citadas coinciden con `legal_basis`; 99 son citas distintas aunque el guard las considere soportadas. Las 35 respuestas semiabiertas/abiertas no tienen aquí una calificación semántica por ítem; RAGAS sigue pendiente.

## 6. Cambios de calidad preparados el 2026-10-02

- La reparación ya no intenta 20 veces renombrar un código cuando el problema real es un artículo ausente. Si una oración completa depende de una cita sin respaldo, se descarta sin dejar una frase mutilada. Un campo sustantivo vacío de respuesta semiabierta o abierta produce abstención controlada; las cerradas conservan su política previa de respuesta y descarte neutral.
- `--citation-fill-extra N` permite comparar el relleno original (`--citation-fill`, sin límite explícito) con `N=0` (solo pasajes declarados por Qwen) o `N=1` (a lo sumo una fuente adicional). La configuración queda en la identidad de la corrida. Ninguna variante se declara ganadora antes de correr los mismos 50 ítems y revisar pertinencia de citas, abstenciones, puntaje, tiempo y RAGAS.
- La generación detiene el lote con `GPU_MEMORY_SPILL` y conserva `errors/<id>.json` cuando la memoria reservada supera la VRAM física. Esto evita proyectar una corrida de 992 a partir de un proceso paginado; no mejora por sí mismo la velocidad de una configuración que excede la tarjeta.
- `--cite-mentions` sigue siendo una ablation opcional. Una norma nombrada dentro de otro documento puede satisfacer el extractor automático sin probar el contenido de la afirmación. No se activa para juzgar calidad jurídica solo con la mejora de puntaje offline 30,41→32,92.

## 5. Re-puntuación offline (sin GPU)

`python tools/rescore_run.py <run>/batch --cite-mentions 3` vuelve a construir las citas sobre las mismas respuestas y evidencia y corre el evaluador oficial. Sobre c1: **30,41 → 32,92/50 sin RAGAS**, con 0 citas sin respaldo. Detalle en DECISION_LOG.

