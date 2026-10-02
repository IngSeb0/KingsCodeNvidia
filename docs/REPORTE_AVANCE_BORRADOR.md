# Reporte de avance — Hackathon 2026

**Equipo:** KingsCode
**Integrantes:** Esteban Alejandro Hernández · Luis Sebastián Contreras Díaz
**Fecha de la medición:** 2 de octubre de 2026 (RTX 4090, sala Turing)

---

## 1. Puntaje sobre las preguntas de muestra

Resultado de `python scripts/evaluate.py --submission submissions_sample50.jsonl --split sample` (50 filas, 0 errores de validación, sha256 `e2041f84…`, en el repositorio del equipo: `docs/entrega_viernes/`; generado automáticamente por el pipeline con esta configuración sobre las salidas guardadas del modelo).

| Componente | Puntos obtenidos | Puntos posibles |
|---|---:|---:|
| Exactitud en cerradas | 12,00 (9/15) | 20 |
| Calidad de citación | 17,55 (recall ponderado 0,878; **0 % citas sin respaldo**) | 20 |
| Abstención calibrada | 7,91 (0 abstenciones; 34/43 respuestas correctas) | 10 |
| **Total automático sin RAGAS** | **37,46** | **50** |

Observaciones sobre el resultado:

Subimos de 26,63 (1-oct) a 37,46 cambiando una variable por corrida. El resultado se reprodujo idéntico en dos computadores y la verificación en vivo simulada (regenerar 3 preguntas) coincide en normas y pasajes. Con `--ragas` (juez oficial, una medición) obtuvimos correctness 0,4275 (referencia 0,451) sobre una corrida previa de 35,18, que con RAGAS sumó 48,00/80; los cambios posteriores no tocan el texto que lee el juez. Probados y descartados con datos: recuperación híbrida + reranker + locator (36,59 y 19 s/pregunta) y ALIA Legal 7B (formato inválido).

## 2. Estado del corpus

| Métrica | Valor |
|---|---|
| Documentos incorporados | 172: 163 del corpus base + 9 añadidos por análisis de fallas (Ley 472 de 1998, 4 sentencias de la Corte Suprema, 3 de unificación y constitucionalidad, 1 ley) |
| Fragmentos indexados | 26.504, uno por artículo o unidad de sentencia |
| Áreas del banco con cobertura | 10/10: constitucional 43 docs, familia 29, laboral 25, civil 24, administrativo 19, tributario 18, penal 16, comercial 14, mercados 14, procesal 10 |
| Áreas del banco sin cobertura | Ninguna; procesal y la jurisprudencia del Consejo de Estado son lo más delgado |

Fuentes consultadas: relatoría de la Corte Constitucional (96), Función Pública – Gestor Normativo (69), Corte Suprema de Justicia (5), normograma del SENA (Código Civil), Comunidad Andina (1). Cada documento conserva URL, fecha de consulta y SHA-256; hoy las 172 URLs responden.

## 3. Arquitectura actual

| Componente | Elección |
|---|---|
| Encoder | Qwen/Qwen3-Embedding-0.6B (abierto, revisión fijada); BM25 queda como recuperador principal porque supera al híbrido en puntaje por tiempo |
| Decoder | Qwen/Qwen3-8B, BF16, temperatura 0, decodificación greedy, sin "thinking" |
| Estrategia de recuperación | BM25 por artículo + expansión por grafo normativo (59 mil nodos) activada por un router; en cerradas, una consulta por opción fusionada por RRF; 8 pasajes |
| Segmentación del corpus | Estructural jurídica: norma → título → artículo (sentencias por unidad), con norma, artículo y jerarquía en los metadatos |
| Mecanismo de abstención | Política sobre la evidencia (vacía, en conflicto o no vigente) + abstención del modelo; antes de abstenerse, una guarda determinista repara o suprime cada cita no respaldada |

## 4. Riesgos identificados

1. **Corrección del texto libre (RAGAS 0,43 frente a 0,45).** El análisis por categoría muestra respuestas que discuten la evidencia en vez de responder, citas reales que no sostienen la afirmación (≈ 11 % en una medición léxica) y respuestas de más del doble de la extensión esperada (23 %). Mitigación: un prompt con método jurídico (área y eje, jerarquía, especialidad, vigencia, regla y excepción, control de distractores en cerradas, datos exactos y extensión según la pregunta), que medimos sin crédito con un proxy local antes de una única medición con el juez.
2. **Normas que la pregunta no nombra (3 de 41 fundamentos no se recuperan).** Mitigación: consultas adicionales generadas por el propio Qwen para texto libre y un tope de pasajes por documento; se adoptan solo si mejoran el puntaje sin pasar de 5 h para 992 preguntas.
3. **Tiempo y reproducibilidad el sábado.** Hoy son 16,4 s/pregunta (≈ 4,5 h de una ventana de 6 h) y las fuentes oficiales cambian al volver a descargarlas (67 de 163). Mitigación: corpus e índice congelados como un único snapshot con hashes en ambas máquinas, ejecución con puntos de control y reanudación, y la posibilidad de repartir las 992 preguntas entre dos GPU si la salida es idéntica byte a byte.
