# Reporte de avance — Hackathon 2026

> **Borrador interno** (no es la plantilla oficial; esa está en `entregables/viernes/REPORTE_AVANCE.md` y no se modifica).
> Antes de enviar: actualizar la sección 1 con la mejor corrida del 1–2 de octubre, exportar a `REPORTE_AVANCE.pdf` (una página)
> y enviar a rf.manrique@uniandes.edu.co con asunto `[Hackathon 2026] Avance — KingsCode` antes del viernes a las 17:00.

**Equipo:** KingsCode
**Integrantes:** Esteban Alejandro Hernández · Luis Sebastián Contreras Díaz
**Fecha de la medición:** 2026-10-02 (RTX 4090, sala Turing)

---

## 1. Puntaje sobre las preguntas de muestra

Resultado de `python scripts/evaluate.py --submission <corrida>/submissions.jsonl --split sample` (sin RAGAS).

| Componente | Puntos obtenidos | Puntos posibles |
|---|---:|---:|
| Exactitud en cerradas | 12,00 (9/15) | 20 |
| Calidad de citación | 17,55 (recall ponderado 0,88; **0 citas sin respaldo**) | 20 |
| Abstención calibrada | 7,91 | 10 |
| **Total automático sin RAGAS** | **37,46** | **50** |
| Corrección RAGAS (juez oficial, medida una vez) | 12,82 (correctness 0,4275) | 30 |
| **Total automático con RAGAS** | **≈ 50,3** (48,00 medido en una corrida anterior) | **80** |

Observaciones sobre el resultado:

Configuración medida: Qwen3-8B (BF16, temperatura 0) + BM25 + router de grafo, k = 8, prompt `grounded-formats-v4`, citas completadas con evidencia verificada y hasta 5 citas a nivel de norma para normas mencionadas en los pasajes recuperados; 0 preguntas caen en el respaldo de abstención. Partimos de 26,63 el 1 de octubre. La misma configuración dio 37,46 en dos computadores distintos (con 8 y con 10 pasajes). RAGAS se midió una sola vez con el juez oficial sobre la corrida anterior (35,18 sin RAGAS → 48,00/80); la corrida actual solo cambió citas y corpus, que RAGAS no lee directamente, y un proxy local con el mismo encoder del evaluador la ubica igual o ligeramente por encima; por eso el total con RAGAS es una estimación. Evaluamos también ALIA Legal 7B como decoder alternativo: no produjo salidas válidas con nuestro formato (5/50) y se descartó. Probamos además híbrido BM25 + denso con reranker y locator exacto: 36,59/50 a 19,1 s/pregunta, sin mejora y más lento, así que no se adopta. Ninguna cita queda sin respaldo en la evidencia recuperada: una guarda determinista repara o suprime toda cita no respaldada. Dos corridas completas dieron un `submissions.jsonl` idéntico byte a byte, lo que respalda la verificación en vivo.

## 2. Estado del corpus

| Métrica | Valor |
|---|---|
| Documentos incorporados | 167 (163 en corpus v0.1 + 4 en v0.2 provisional) |
| Fragmentos indexados | 26.132 (26.060 en v0.1 + 72 en v0.2); 26.630 segmentados en total |
| Áreas del banco con cobertura | 10/10: constitucional (40 docs), familia (29), laboral (25), civil (24), tributario (18), administrativo (17), penal (16), comercial (14), mercados (14), procesal (10) |
| Áreas del banco sin cobertura | Ninguna sin documentos; la profundidad es desigual (procesal y mercados son las más delgadas) |

Fuentes consultadas: Función Pública – Gestor Normativo (68 documentos), relatoría de la Corte Constitucional (93), Corte Suprema de Justicia (4), normograma del SENA (1, Código Civil), Comunidad Andina (1). Cada documento conserva URL, fecha de consulta y SHA-256 del original en `corpus_manifest.json`.

## 3. Arquitectura actual

| Componente | Elección |
|---|---|
| Encoder | Qwen/Qwen3-Embedding-0.6B (abierto, revisión fijada); recuperación híbrida preparada y en medición |
| Decoder | Qwen/Qwen3-8B, BF16, temperatura 0, greedy, sin "thinking"; atención SDPA |
| Estrategia de recuperación | BM25 sobre fragmentos por artículo, expansión por grafo normativo activada por router, consultas por opción en cerradas fusionadas por RRF. Evaluados y no adoptados aún: híbrido BM25 + denso con RRF, reranker Qwen3-Reranker-0.6B y locator exacto (no superan en puntaje por tiempo en la muestra) |
| Segmentación del corpus | Estructural jurídica: un fragmento por artículo (o unidad equivalente en sentencias), con norma, artículo y jerarquía en los metadatos |
| Mecanismo de abstención | Política sobre la evidencia (vacía, en conflicto o no vigente) + abstención declarada por el modelo; guarda de citas que repara o suprime antes de abstenerse |

## 4. Riesgos identificados

1. **RAGAS es el componente más bajo (0,43 frente a 0,45 de referencia).** Las respuestas semiabiertas deben ser más directas y las abiertas más completas en conclusión y análisis; lo mejoramos con un proxy local gratuito (mismo encoder del evaluador) y volveremos a medir con el juez solo la configuración final.
2. **Tiempo de ejecución.** Hoy son 16,4 s/pregunta (≈ 4,5 h para 992, en una ventana de 6 h). Mitigación: checkpoints por pregunta con reanudación, alarma si una configuración pasa de 20 s/pregunta, y ninguna técnica nueva sin medir su costo.
3. **Corpus y reproducibilidad de fuentes.** Al volver a descargar las fuentes oficiales, 67 de 163 documentos cambiaron; por eso el índice se congela como snapshot (hashes por archivo) y se publica con licencia abierta. La cobertura de procedimiento y derecho de los mercados es la más delgada.
