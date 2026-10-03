# START HERE — KingsCode v0.5


## Mapa del repositorio
`docs/MAPA_DEL_REPO.md`: qué es cada carpeta, dónde está cada corpus (`corpus/` v0.1 fuera de git vs `corpora/corpus-v0.2/` agregado provisional) y qué falta para el sábado.

## Entrada histórica (2026-09-29)
El resumen de esa fecha registra los cambios fusionados entonces. Para estado,
resultados y próximos pasos usar la sección reconciliada del 2026-10-01 abajo,
`docs/KINGSCODE_STATE.json` y la última entrada de `docs/DECISION_LOG.md`.

## Orden de lectura
1. `docs/KINGSCODE_MASTER_KNOWLEDGE.md`
2. `docs/KINGSCODE_STATE.json`
3. `docs/TEAM_SPLIT.md`
4. `docs/ARCHITECTURE_V05.md`
5. `docs/INTEGRATION_CONTRACTS.md`
6. `config/strategy.json`
7. `docs/DECISION_LOG.md`

## Trabajo actual en paralelo
- **A:** Corpus v0 + grafo + retrieval baseline implementados. Ver `CORPUS.md`, `docs/MEMBER_A_RUNBOOK.md` y reportes de verificación; pendiente benchmark neuronal completo y ampliar/desambiguar fuentes.
- **B:** Gate 1B implementado: normalizador, router, dummy, abstención, guardas, evaluador y experimentos. Repetir con `.venv/Scripts/python.exe tools/member_b.py smoke`; ver `docs/MEMBER_B_RUNBOOK.md`. Decoder real/CUDA/bakeoff pendientes.

No asumir que CUDA ya está configurado.

## Próxima sesión en la 4090

Gate 2-Prep está preparado pero sin pruebas ejecutadas, por instrucción del usuario. Leer `docs/GPU_DAY_RUNBOOK.md` y `docs/MODEL_LOCKS_GATE2.md`. Primer comando en la GPU: `git pull --ff-only origin main`. Después verificar commit/snapshot y ejecutar las dos verificaciones pendientes. No confundir los 60 tests históricos de Gate 1B con validación del backend nuevo.

## Actualización que prevalece sobre los próximos pasos históricos de arriba

A ya tiene resultados RTX4090/Search V2 preservados en 60ebf7e. La fase vigente es locator productivo + benchmark v2 + corpus v0.2 en `feat/member-a-corpus-v02-locator`. Validation v1 cerrada; no reejecutar las variantes ni consumir holdout. Leer `reports/MEMBER_A_V02_PROGRESS.md` y `docs/A_TO_B_V02_CONTRACT.md`. B/decoder mantiene su estado independiente.

## Estado más reciente: KC-COL-IR pre-CUDA (2026-09-30)

`main` está en `e528161`. KC-COL-IR CUJ 2026 tiene 10 gold independientes y 10/10 completos en el perfil controlado de 190 pasajes; el corpus competitivo v0.1 sigue sin esas fuentes. `CUDA_READY=false`; el handoff vigente detiene la ejecución antes de C0-C3. El trabajo local de hardening está en `exp/pre-cuda-hardening`; consultar `docs/KC_COL_IR_PRE_CUDA_HARDENING.md` y `docs/experiments/KC_COL_IR_CUJ2026_SHORTLIST_V1.json`. Javeriana validation sigue sin parsear ni inspeccionar.

## Estado reconciliado: optimización de corrida sample50 (2026-10-01)

El cambio se integró en `main` como `4952482` (padre `93f99a1`). Hay una corrida externa de
la RTX 4090 compartida por el usuario; no lanzar otra hasta confirmar que acabó.
El resultado de una corrida previa no sustituye sus reportes/identidad. Los
contadores por etapa del modo legacy de opciones se estaban subestimando; véase
el cambio local pendiente en `kingscode/reasoning/pipeline.py`. La ruta siguiente
y la lista de fuentes oficiales candidatas están en
`docs/EXPLORATION_ROUTES_2026-10-01.md`.

No hay en este checkout un benchmark neuronal end-to-end nuevo ni resultados de
RAGAS asociados a esta fase. No confundir diagnóstico de una GPU, corrida de
50 preguntas, benchmark de retrieval y freeze competitivo.
