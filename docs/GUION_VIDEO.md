# Guion del video (máximo 5:00) — KingsCode

**Qué debe cubrir** (enunciado y Rubén):
- **Producto:** para quién es y qué valor entrega.
- **Técnica:** arquitectura, decisiones de corpus y su justificación, funcionamiento de extremo a extremo con los pasajes recuperados.
- **Limitaciones:** se valoran más que presentar el sistema como infalible.

## Preparación (2 min)

1. Abrir `docs/video/presentacion.html` en Chrome o Edge.
   - Doble clic sobre el archivo, luego **F** para pantalla completa.
   - Las flechas ← → pasan las diapositivas.
2. En otra pestaña, abrir la interfaz:
   - Iniciarla con `.\.venv\Scripts\python.exe -m streamlit run interfaz/app.py`.
   - Abrir `http://localhost:8501`.
   - Verificar que la casilla **Búsqueda semántica** esté marcada.
3. Hacer una consulta de prueba antes de grabar: la primera carga el modelo y tarda.
4. Grabar con **Win + Alt + R** (Xbox Game Bar) o con OBS. Una sola toma.

## Guion

| Tiempo | Diapositiva / pantalla | Qué decir |
|---|---|---|
| 0:00–0:20 | 1 · Portada | "Somos KingsCode, Esteban y Luis. Construimos un asistente de derecho colombiano con un modelo abierto de 8 mil millones de parámetros que solo cita normas que puede probar con el texto oficial." |
| 0:20–0:45 | 2 · El reto | "El reto: 992 preguntas en tres formatos, con un modelo abierto, a temperatura cero, y cada norma citada debe estar en los pasajes recuperados." |
| 0:45–1:25 | 3 · Producto | "¿Para quién? Abogados, consultorios jurídicos, áreas de cumplimiento, entidades públicas y pymes. Encontrar la norma y el artículo correctos toma horas, y los chatbots generales inventan normas. Una cita errada en un concepto jurídico tiene costo legal. KingsCode responde en segundos con la norma, el artículo y el pasaje oficial enlazado. Si no hay evidencia, lo dice. Y corre en un servidor propio, así que los datos sensibles de los casos no salen a terceros." |
| 1:25–2:05 | 4 · Arquitectura | "La pregunta se normaliza y buscamos con BM25 por artículo. En selección múltiple hacemos una búsqueda por opción; en texto libre sumamos búsqueda semántica con Qwen3-Embedding, y un grafo normativo trae lo que modifica o deroga. Qwen3-8B recibe 8 pasajes y responde en el JSON oficial; una guarda determinista elimina cualquier cita sin respaldo." |
| 2:05–2:35 | 5 · Corpus | "170 normas y sentencias de fuentes oficiales, 26.665 fragmentos, uno por artículo, con URL, fecha y hash. Partimos por artículo porque en derecho la unidad de cita es el artículo. Ampliamos el corpus según las fallas medidas." |
| 2:35–3:05 | 6 · Recuperación por formato | "En la prueba con el jurado vimos el límite de BM25: en un caso de datos de salud sumaba 'VIH' y 'medicamento' y no encontraba la Ley 1581 de datos sensibles. Por eso la búsqueda semántica se activa en texto libre, donde ayuda, y no en selección múltiple, donde bajaba el puntaje." |
| 3:05–3:55 | **Interfaz en vivo** | Escribir el caso de los datos de salud o cargar un id de la muestra, y pulsar Responder. Mostrar la respuesta, las normas citadas y los pasajes con su fuente. "Cada norma citada aparece en un pasaje recuperado, con su enlace oficial." |
| 3:55–4:15 | 7 · Citas | "Cero por ciento de citas sin respaldo en todas las corridas, y es reproducible: regenerar una pregunta da las mismas normas y los mismos pasajes." |
| 4:15–4:35 | 8 · Resultados | "Una variable por corrida, con el evaluador oficial: de 26,6 a 38,8 sobre 50 en la muestra, sin RAGAS. Las 992 corrieron en tres RTX 4090." |
| 4:35–5:00 | 10 · Limitaciones y 11 · Gracias | "Limitaciones: poca jurisprudencia del Consejo de Estado, vigencia no certificada artículo por artículo, contexto de 8 mil tokens y decisiones tomadas sobre 50 preguntas. Todo está en el repositorio, con el corpus y el índice enlazados. Gracias." |

Si el tiempo aprieta, la diapositiva 9 (Demostración) se salta porque la demo ya se hizo en la interfaz.

## Publicar

1. Exportar en MP4.
2. Subirlo a OneDrive y compartirlo con **"Cualquier persona con el vínculo puede ver"**.
3. Probar el enlace en una ventana privada.
4. Pegarlo en el README, en lugar de `PENDIENTE_ENLACE_VIDEO`, y en el formulario de entrega.
