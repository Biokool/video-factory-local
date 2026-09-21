# Video Factory Local V7

Paquete de actualización incremental para el repositorio V5/V6 auditado. V7 no elimina el pipeline que ya produce video; añade contratos, catálogo de assets, seguridad comercial, RAG temático, composición determinista y controles de calidad.

## Hallazgos de la auditoría
- El código compila, pero mezcla rutas absolutas, versiones documentales antiguas y dependencias no congeladas.
- `QwenVideoFactory.Modelfile` apunta a `gemma4:e4b`, aunque el sistema se documenta como Qwen 3.5 4B.
- `requirements-lock.txt` está vacío y `requirements.txt` no fija versiones.
- `research_images.py` ejecuta red durante producción y el valor de caché pierde autor, URL y licencia original.
- `generate_short.py` fuerza 48 kHz, contrario al perfil estable de 44.1 kHz.
- El dashboard acepta nombre de PDF sin normalización, lee archivos completos en memoria y no establece límite de subida.
- `resolve_path()` admite `../`; V7 debe resolver solamente IDs del registro.
- El TTS automático puede caer a un modelo no apto para monetización.
- Las etiquetas visuales no usaban tildes de español de México.
- El RAG actual conserva texto, pero no modela página, figura, relación, evidencia ni postura editorial con suficiente precisión.

## Orden de aplicación
1. Rotar secretos y conservar solo `.env.example`.
2. Crear rama `v7-update` y etiqueta del baseline V6.
3. Ejecutar `scripts/v7/audit_v7.py`.
4. Incorporar schemas y configuración V7.
5. Registrar la mano actual como legacy, luego aprobar una mano editorial de cinco dedos.
6. Activar el compositor V7 en modo paralelo.
7. Ingerir el manual por página, concepto, figura y relación.
8. Probar 15 s, 60-90 s y finalmente 8-10 min.

## Regla comercial
En modo `commercial_monetized`, un componente con licencia desconocida, no comercial o no registrada falla cerrado. SAPI queda solo como prueba de continuidad hasta verificar los términos de la voz instalada. Nunca usar OmniVoice CC-BY-NC en una publicación monetizada.
