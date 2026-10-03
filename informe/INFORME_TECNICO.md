# Informe técnico — KingsCode

**Hackathon 2026 · Universidad de los Andes**
**Integrantes:** Esteban Alejandro Hernández · Luis Sebastián Contreras Díaz

---

## 1. Arquitectura del sistema

RAG jurídico en dos capas con verificación determinista de citas. Recorrido de una pregunta:

1. **Normalización.** Limpieza del texto y detección de referencias normativas explícitas. En selección múltiple se genera además una consulta por opción, porque el término decisivo suele estar en la opción y no en el enunciado.
2. **Recuperación (capa A).** BM25 sobre fragmentos por artículo y expansión por un grafo normativo (59 mil nodos y 75 mil aristas de citas, modificaciones y derogatorias) que un *router* activa solo cuando la pregunta lo requiere. Las consultas por opción se fusionan con RRF. Se entregan 8 pasajes.
3. **Generación (capa B).** Qwen3-8B recibe la pregunta y los pasajes como datos JSON (nunca como instrucciones) con un prompt por formato (cerrada, semiabierta, abierta) y devuelve un objeto JSON estricto con los pasajes que usó.
4. **Verificación de citas.** Una reparación determinista reescribe o suprime toda cita que no esté en la evidencia; luego se completan citas verificadas en `referencia_legal`/`justificacion`, y una guarda final comprueba cada cita contra los 10 primeros pasajes con las mismas reglas del evaluador oficial.
5. **Ejecución.** Un punto de control por pregunta (escritura atómica, reanudación sin repetir); si una pregunta falla, solo esa pasa a abstención.

## 2. Selección de encoder y decoder

| Componente | Modelo | Motivo de la elección | Alternativas descartadas |
|---|---|---|---|
| Encoder | Qwen/Qwen3-Embedding-0.6B (abierto, revisión fijada) | Multilingüe, 1.024 dimensiones, instrucción de consulta jurídica; índice vectorial exacto reconstruible con `tools/member_a.py dense` | Recuperación final solo densa o híbrida: el híbrido con reranker dio 36,59/50 a 19,1 s/pregunta frente a 36,93 a 15,9 s de BM25 |
| Decoder | Qwen/Qwen3-8B, BF16, sin *thinking* | El de mejor puntaje medido dentro del límite de 8B; JSON estable | ALIA Legal 7B: 5,00/50 (formato inválido en 50/50) |
| Reranker | Qwen/Qwen3-Reranker-0.6B (implementado) | Opcional | No adoptado: no mejoró el puntaje y cuesta ~3 s/pregunta |

Inferencia: BF16 sin cuantización en una RTX 4090 (24 GB, pico 17,8 GB), contexto de 8.192 tokens, temperatura 0 con decodificación *greedy* (`do_sample=False`), `torch.use_deterministic_algorithms(True)`, semilla fija; 16,4 s por pregunta (≈ 4,5 h para 992).

## 3. Estrategia de recuperación

- **Segmentación estructural jurídica:** un fragmento por artículo (o unidad equivalente en sentencias), con norma, número, año, artículo, jerarquía y URL de origen en los metadatos.
- **Índices:** BM25 (léxico, decisivo para identificadores como "artículo 42") y vectorial exacto (Qwen3-Embedding, producto interno sobre vectores normalizados), más el grafo normativo.
- **Top-k = 8**, con 30 candidatos por vista; 10 pasajes no mejoró (37,46 en ambos casos).
- **Corpus:** 172+ documentos oficiales (Función Pública, relatoría de la Corte Constitucional, Corte Suprema, normograma del SENA, Comunidad Andina), ~26.500 fragmentos, URL, fecha y SHA-256 por documento; ampliado por análisis de fallas en la muestra (Ley 472 de 1998, sentencias de unificación).

## 4. Verificación de citas y abstención

- **Respaldo:** una cita se acepta solo si su norma (y su artículo, cuando lo menciona) está en uno de los 10 primeros pasajes; las normas nombradas dentro de un pasaje se citan a nivel de cuerpo (la regla oficial de respaldo). Resultado: **0 % de citas sin respaldo** en todas las corridas.
- **Alineación cita–afirmación** (diagnóstico propio): el prompt v6 exige citar el artículo que contiene la regla en la misma oración que la afirmación; las citas alineadas pasaron de 68,9 % a 75,7 %.
- **Abstención:** la política bloquea texto libre solo si la evidencia está vacía, en conflicto o no vigente; en selección múltiple nunca se abstiene, porque con la regla oficial solo conviene si la probabilidad de acierto es menor a ~7 %. Además, el modelo puede declararla y toda falla irrecuperable de una pregunta se convierte en abstención de esa pregunta.

## 5. Resultados sobre las preguntas de muestra

Configuración final: Qwen3-8B + BM25 + grafo + consultas por opción, prompt v6, citas completadas y verificadas (`tools/kingscode_final.ps1 -Flags "-Recomendada -PromptVersion v6"`).

| Componente | Puntos | Posibles |
|---|---:|---:|
| Exactitud en cerradas | 13,33 (10/15) | 20 |
| Calidad de citación | 16,73 (recall 0,837, 0 sin respaldo) | 20 |
| Abstención calibrada | 8,02 | 10 |
| **Total automático sin RAGAS** | **38,08** | **50** |

Una variable por corrida: 26,63 → 30,41 → 35,18 → 36,93 → 37,46 (v4) → **38,08 (v6)**; con el corpus ampliado del integrante A, v4 llegó a 39,02. RAGAS (juez oficial, una medición): correctness 0,4275 (referencia 0,451).

Errores más frecuentes (taxonomía por área y sub-tarea, `tools/analyze_taxonomy.py`): (1) normas del fundamento que la pregunta no nombra y la recuperación léxica no encuentra (3 de 41); (2) cerradas que exigen un dato no contenido en la evidencia (por ejemplo, el salario mínimo para la cuantía); (3) respuestas que discutían la evidencia en vez de responder (8 de 50 con v4; v6 lo corrige).

## 6. Limitaciones

1. **Recuperación léxica.** BM25 depende de que la pregunta comparta vocabulario con la norma; cuando la norma aplicable no se nombra, puede no recuperarse. El índice vectorial existe, pero el híbrido medido no compensó su costo en tiempo.
2. **Cobertura del corpus.** Sin decisiones del Consejo de Estado y con procesal como el área más delgada (10 documentos); la vigencia no está certificada artículo por artículo (las fuentes oficiales cambian entre descargas: 67 de 163 documentos cambiaron).
3. **Contexto de 8.192 tokens.** Con evidencia larga, el prompt descarta pasajes de menor rango (implementamos `--fit-passages` para recortar textos en vez de descartar pasajes).
4. **Texto libre.** El RAGAS medido (0,43) está cerca del modelo de referencia, pero la longitud óptima depende de la pregunta: respuestas de más del doble o de menos de la mitad de la referencia pierden corrección.
5. **Muestra pequeña.** Las decisiones se tomaron sobre 50 preguntas; las diferencias menores a ~1 punto pueden no generalizar.
