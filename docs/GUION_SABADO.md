# Guion del sábado 3 de octubre — KingsCode (09:00, salón 617)

Para el equipo: qué decir cuando pregunten y qué comandos correr. Configuración vigente: `-Recomendada -PromptVersion v6` (v6 38,08 frente a v4 37,46 con el mismo corpus; v4 dio 39,02 con el corpus descargado hoy). Preparación completa en un comando: `tools\kingscode_corre_todo.ps1` (viernes).

## 1. Antes de las 09:00 (en el PC que va a correr)

> **Commit congelado: `bc480e7`** (v6 medido: 38,08/50 sin RAGAS con el corpus de `turing`; el respaldo `C:\Users\turing\kc_snapshot` se hizo con ese commit). Los commits posteriores (v8, citas en abiertas, telemetría) no están medidos en GPU con v6: no usarlos hoy salvo que una corrida de la muestra con el mismo corpus los confirme.
>
> ```powershell
> cd "$HOME\KingsCodeGPU\KingsCodeNvidia"; git fetch origin; git checkout bc480e7
> powershell -ExecutionPolicy Bypass -File .\tools\kingscode_snapshot.ps1 -Accion verificar -Origen "$HOME\kc_snapshot"
> powershell -ExecutionPolicy Bypass -File .\tools\kingscode_final.ps1 -Flags "-Recomendada -PromptVersion v6" -InputFile <set ciego> -RunName final_992
> ```

1. Cerrar las sesiones de otros usuarios (`query user` → `logoff <ID>`); `nvidia-smi` debe mostrar < 1.000 MiB usados.
2. Código fijo: `git pull --ff-only origin main` una sola vez y anotar `git rev-parse --short HEAD`. Desde ahí, todo con `-NoPull`.
3. Corpus e índice idénticos a los de hoy (respaldo hecho el viernes por `tools\kingscode_corre_todo.ps1` en `$HOME\kc_snapshot`):
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\tools\kingscode_snapshot.ps1 -Accion restaurar -Origen <carpeta del respaldo>
   ```
   Debe terminar en "Corpus e indice identicos al snapshot". Si el corpus ya está en ese PC: `-Accion verificar -Origen <carpeta del respaldo>`.
4. Ensayo corto (3 preguntas, 2 min): `powershell -ExecutionPolicy Bypass -File .\tools\kingscode_final.ps1 -Flags "-Recomendada -PromptVersion v6"` y cortar tras `[batch] 3/50` si no hay tiempo, o dejarlo completo (≈ 14 min) para confirmar 37,46.

## 2. Corrida de las 992 (ventana 09:00–15:00)

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\kingscode_final.ps1 -Flags "-Recomendada -PromptVersion v6" -InputFile <ruta del set ciego> -RunName final_992
# si se corta (luz, cierre, error): el MISMO comando con -Resume (no repite lo ya generado)
powershell -ExecutionPolicy Bypass -File .\tools\kingscode_final.ps1 -Flags "-Recomendada -PromptVersion v6" -InputFile <ruta del set ciego> -RunName final_992 -Resume
```

- Proyección: 16,4 s/pregunta ≈ 4,5 h. Cada pregunta imprime `[batch] -> N/992 ... generando...` y al terminar `[batch] N/992 ... | faltan ~X min`.
- Al final: `submissions.jsonl` en la raíz del repo (con su sha256) y `reports\decoder_diagnostic\final_992\DOCUMENTO_FINAL.md`.
- **No borrar ni mover** `reports\decoder_diagnostic\final_992`, el corpus ni los modelos hasta terminar la verificación en vivo.

## 3. Verificación en vivo (15:00–17:00): regenerar preguntas

Regenera las preguntas pedidas con la misma configuración y compara normas y pasajes con lo entregado:

```powershell
$Run = "reports\decoder_diagnostic\final_992\batch"
.\.venv\Scripts\python.exe tools\member_b.py verify --delivered "$Run\submissions.jsonl" --only 12,345,678 `
  --input <ruta del set ciego> --retrieval-mode option --retriever-mode bm25 --graph-policy router --k 8 --candidate-k 30 `
  --graph-budget 10 --reranker-batch-size 2 --corpus corpus_v01_v02_a1 --model qwen3-8b --precision bf16 `
  --prompt-version v6 --citation-fill --cite-mentions 5
```

Debe decir `all_match: true` (temperatura 0, decodificación greedy, `torch.use_deterministic_algorithms`, corpus y modelo con hash fijo). Si piden una pregunta **modificada**: se escribe en un JSONL con los campos públicos (`id`, `pregunta`, `formato`, `opciones`) y se corre `tools\member_b.py batch --input <ese archivo> --run-dir reports\vivo\batch --fresh` con los mismos flags, o se usa la interfaz (`streamlit run interfaz/app.py`, misma configuración). El sistema responde cualquier pregunta: no depende de la muestra.

## 4. Qué responder si preguntan

**Arquitectura (qué sistema funciona).** RAG jurídico en dos capas:
- *Recuperación (Luis):* corpus de 172 documentos oficiales (Función Pública, Corte Constitucional, Corte Suprema, SENA, CAN) segmentado por artículo (26.504 fragmentos), con URL, fecha y SHA-256 por documento. BM25 sobre artículos + expansión por un grafo normativo (59 mil nodos) que activa un router; en cerradas, una consulta por opción fusionada por RRF; 8 pasajes por pregunta. El encoder Qwen3-Embedding-0.6B y el reranker Qwen3-Reranker-0.6B están implementados; el híbrido se midió (36,59 y 19 s/pregunta) y no se adoptó.
- *Razonamiento y generación (Esteban):* Qwen3-8B abierto, BF16, temperatura 0, greedy, sin "thinking". Prompt por formato (cerrada, semiabierta, abierta) que pide JSON estricto, justificación antes de la letra en cerradas y la atribución de los pasajes usados.
- *Guardas (lo que evita alucinaciones):* una reparación determinista reescribe o suprime toda cita que no esté en la evidencia, y la guarda final verifica cada cita contra los 10 primeros pasajes con las mismas reglas del evaluador oficial → **0 % de citas sin respaldo**. Si una cita no se puede reparar, solo esa pregunta pasa a abstención; la corrida nunca se detiene.

**Generación (cómo se arma una respuesta).** Pregunta → normalización → recuperación (BM25 + grafo + opciones) → prompt con los pasajes como datos → Qwen3-8B → parser de JSON estricto → reparación de citas → completar citas verificadas (`referencia_legal`/`justificacion`) con normas nombradas en la evidencia → guarda → fila del esquema oficial.

**Por qué esta configuración.** Una variable por corrida: 26,63 → 30,41 → 35,18 → 36,93 → 37,46. Descartado con datos: híbrido + reranker + locator, ALIA Legal 7B, 10 pasajes. Las mejoras de la noche (contexto de 16k, prompt v6 de razonamiento jurídico, planner para texto libre, tope por documento) solo se usan si una corrida las confirma.

**Reproducibilidad.** El mismo `submissions.jsonl` se reprodujo en dos computadores; corpus e índice congelados con hash por archivo; modelos fijados por revisión y verificados archivo por archivo; código fijado por commit.

**Reglas del evento.** Solo modelos abiertos (≤ 8B decoder); ninguna salida pasa por modelos cerrados; la muestra no se indexa ni entra a los prompts; no se editan respuestas a mano (todo post-proceso es código versionado); RAGAS solo con autorización (se usó una vez).

## 5. Si algo falla

| Síntoma | Qué hacer |
|---|---|
| Se detiene en [6] con "La GPU ya tiene ... MiB ocupados" | Cerrar la interfaz u otra sesión (`query user`, `logoff <ID>`) y relanzar con `-Resume` |
| `[batch] -> N/992 ... generando...` sin avanzar > 3 min | Igual que arriba (VRAM desbordada) |
| Se cortó la corrida | Mismo comando con `-Resume -RunName final_992` |
| "STOP: el corpus no coincide" | Restaurar el respaldo (`kingscode_snapshot.ps1 -Accion restaurar`) |
| `git pull` aborta por carpetas sin seguimiento | No hacer pull el sábado; el código ya quedó fijo |
