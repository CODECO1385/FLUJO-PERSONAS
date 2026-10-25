# Flujo de personas — prototipo local (Streamlit + YOLO + ByteTrack)

Todo corre en tu equipo. Los videos solo se guardan en una carpeta temporal (`flujo_personas_*` dentro del directorio temporal del sistema) y se borran al pulsar «Iniciar análisis nuevo».

## Instalación
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
La primera ejecución descarga los pesos de YOLO (p. ej. `yolov8n.pt`); el video nunca se sube.
Sin GPU funciona en CPU: usa el modelo `n`, 640 px y 2–5 fps procesados.

## Ejecutar
```bash
streamlit run app.py
python -m pytest -q          # pruebas de los cálculos
```

## Uso
1. **Video**: sube MP4/MOV/AVI; verás duración, resolución y FPS.
2. **Espacio**: elige un fotograma, ajusta la línea (P1, P2 en % de la imagen) y el lado del *interior*; define zonas como polígonos (`x,y; x,y; …` en %) o con el rectángulo rápido. Puedes crear/editar/borrar filas. Guarda el JSON para reutilizarlo con la misma cámara (coordenadas normalizadas; avisa si la proporción cambia).
3. **Análisis**: modelo, confianza, fps, resolución. Usa el *modo de prueba* (20 s) primero.
4. **Resultados**: métricas, trayectorias, mapa de calor, flujo entre zonas, tabla por ID y descargas (CSV, JSON, video, ZIP).

## Definiciones y limitaciones
- **Tiempo observado**: primera a última detección de un ID. **Permanencia estimada**: cruce de entrada a cruce de salida del mismo ID; si falta alguno el registro es *incompleto*.
- Los IDs son temporales. Si ByteTrack pierde a alguien y reasigna otro ID, **no se unen**; solo se marcan *posibles cambios de ID*.
- Cruces con banda muerta de 10 px y cancelación de rebotes (<1.5 s). Transiciones entre zonas solo si hubo ≥0.5 s en cada zona.
- Las zonas se definen con coordenadas numéricas, no dibujando con el ratón (limitación de este MVP).
- El análisis es síncrono: la interfaz muestra progreso pero no se puede cancelar a mitad.
- El video procesado usa `mp4v`; algunos navegadores no lo reproducen (descárgalo).
- Video de prueba legal: p. ej. clips de Pexels o Pixabay (licencia libre) o MOT17/PETS09 (datasets de seguimiento).
