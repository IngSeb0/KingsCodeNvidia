# Guion del video (máximo 5:00) — KingsCode

El enunciado pide: arquitectura, decisiones de corpus y su justificación, funcionamiento de extremo a extremo con los pasajes recuperados, y limitaciones (se valoran por encima de presentarlo como infalible). Grabar la pantalla (Win + G o OBS) con la interfaz abierta.

| Tiempo | Pantalla | Qué decir |
|---|---|---|
| 0:00–0:30 | Título del repo / interfaz | "Los modelos más grandes citan normas erróneas o inexistentes en casi la mitad de los casos. Construimos un sistema con un modelo abierto de 8B que solo cita lo que puede probar." |
| 0:30–1:30 | Diagrama del README (Arquitectura) | Recorrido: pregunta → normalización (una consulta por opción en cerradas) → BM25 sobre artículos + grafo normativo → 8 pasajes → Qwen3-8B (temperatura 0, prompt de razonamiento jurídico) → reparación y guarda de citas con la regla oficial → JSON. Encoder Qwen3-Embedding-0.6B para el índice vectorial; elegimos BM25 porque el híbrido no mejoró el puntaje y era más lento. |
| 1:30–2:30 | `CORPUS.md` y `corpus_manifest.json` | 172+ documentos oficiales (Función Pública, Corte Constitucional, Corte Suprema, SENA, CAN), un fragmento por artículo con norma, artículo, URL, fecha y hash. Se amplió por análisis de fallas de la muestra (Ley 472 de 1998, sentencias de unificación), no por intuición. |
| 2:30–3:45 | Interfaz: hacer una pregunta en vivo | Escribir una pregunta (p. ej. "¿Cuál es el término para contestar la demanda en el proceso verbal sumario?"), pulsar Responder, mostrar la respuesta, las normas citadas y los pasajes recuperados con su fuente. Señalar que cada norma citada aparece en un pasaje. |
| 3:45–4:30 | Tabla de resultados del informe | 26,63 → 38,08/50 sin RAGAS en la muestra (39,02 con el corpus ampliado), una variable por corrida; 0 % de citas sin respaldo; ~16 s por pregunta; reproducible en dos computadores. |
| 4:30–5:00 | Sección Limitaciones del informe | BM25 no encuentra la norma cuando la pregunta no la nombra; falta jurisprudencia del Consejo de Estado; contexto de 8.192 tokens; vigencia no certificada artículo por artículo; decisiones tomadas sobre 50 preguntas. |

Subir el video a OneDrive/Drive con "Cualquier persona con el vínculo" y pegar el enlace en el README (`PENDIENTE_ENLACE_VIDEO`).
