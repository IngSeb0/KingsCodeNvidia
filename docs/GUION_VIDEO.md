# Guion del video (máximo 5:00) — KingsCode

El enunciado pide cuatro cosas: la arquitectura, las decisiones de corpus y su justificación, el funcionamiento de extremo a extremo con los pasajes recuperados, y las limitaciones. Las limitaciones se valoran por encima de presentar el sistema como infalible.

Para grabar: desde la raíz del repositorio ejecutar `\.venv\Scripts\python.exe -m streamlit run .\interfaz\app.py`. Confirmar que la interfaz muestra el perfil híbrido y que el índice denso está presente. En la verificación en vivo, el híbrido aplica a respuestas breves y abiertas; la selección múltiple conserva la búsqueda por opciones BM25. Las submissions y los manifiestos de la entrega siguen identificando la corrida BM25: no atribuir sus puntajes al perfil híbrido de la interfaz. Abrir también el README y el informe en otras pestañas. Hablar sin leer: las frases de la tabla son guía.

| Tiempo | Pantalla | Qué decir |
|---|---|---|
| 0:00–0:25 | Interfaz con el logo de Software Colombia | "Somos KingsCode. Construimos un asistente de derecho colombiano con un modelo abierto de 8 mil millones de parámetros que solo cita normas que puede probar con el texto oficial." |
| 0:25–1:30 | README, diagrama de Arquitectura | "La pregunta se normaliza y buscamos en un corpus propio, partido por artículo. En selección múltiple hacemos una búsqueda por cada opción. En respuestas breves y abiertas combinamos BM25 con búsqueda semántica usando Qwen3-Embedding. Un grafo normativo trae las normas que modifican o derogan. Qwen3-8B, a temperatura cero, recibe 8 pasajes y responde en el JSON oficial. Una guarda determinista elimina cualquier cita que no esté en los pasajes: 0 % de citas sin respaldo." |
| 1:30–2:20 | `CORPUS.md` y `corpus_manifest.json` | "170 normas y sentencias de fuentes oficiales: Función Pública, Corte Constitucional, Corte Suprema, SENA. 26.665 fragmentos, uno por artículo, con URL, fecha y hash. Partimos por artículo porque en derecho la unidad de cita es el artículo: cada pasaje ya trae la norma que se cita. Ampliamos el corpus por análisis de fallas, no por intuición." |
| 2:20–3:40 | Interfaz: pregunta en vivo | Cargar un id de la muestra, o escribir el caso de datos de salud ("¿Puede el Gobierno acceder a la base de datos de pacientes con esclerosis múltiple para justificar una licencia obligatoria?"). Pulsar Responder y mostrar la respuesta, las normas citadas y los pasajes con su fuente. "Cada norma citada aparece en un pasaje recuperado." |
| 3:40–4:20 | Tabla de resultados (README o informe) | "Medimos una variable por corrida: de 26,6 a 39 sobre 50 en la muestra, sin RAGAS. Las 992 preguntas corrieron en tres RTX 4090 de forma determinista: regenerar una pregunta da las mismas normas y los mismos pasajes." |
| 4:20–5:00 | Sección Limitaciones del informe | "En la prueba con el jurado vimos el límite de BM25: en un caso largo sumaba palabras como 'VIH' y 'medicamento' y no encontraba la Ley 1581 de datos sensibles. Por eso activamos la búsqueda semántica en texto libre. Otras limitaciones: poca jurisprudencia del Consejo de Estado, vigencia no certificada artículo por artículo, contexto de 8 mil tokens y decisiones tomadas sobre 50 preguntas." |

Para publicarlo:
1. Exportar en MP4.
2. Subirlo a OneDrive con "Cualquier persona con el vínculo".
3. Probar el enlace en una ventana privada.
4. Pegarlo en el README, en lugar de `PENDIENTE_ENLACE_VIDEO`.
