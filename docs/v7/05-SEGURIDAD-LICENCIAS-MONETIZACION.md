# Seguridad, licencias y monetización

## Seguridad prioritaria
- Rotar cualquier contraseña que haya aparecido en documentación previa.
- Servicios únicamente en `127.0.0.1`.
- Nombres de archivo normalizados, tamaño máximo de carga y extensión permitida.
- Qwen selecciona IDs, nunca rutas, URLs o comandos.
- `subprocess.run` usa listas, timeout y comandos permitidos.
- Red deshabilitada en render y publicación separada.
- Logs sin prompts privados, documentos completos, tokens o cadenas de conexión.

## Política de licencias
Registrar licencia de software, modelo, pesos, voz, dataset y asset por separado. La presencia en Openverse no sustituye la verificación. Mantener autor, título, URL, licencia, versión, obligaciones y fecha de acceso.

## TTS monetizable
- OmniVoice CC-BY-NC: BLOQUEADO.
- CosyVoice o PocketTTS: solo si la versión y los pesos concretos permiten uso comercial y se archiva la licencia.
- Piper: verificar la voz por separado.
- SAPI: continuidad técnica, no publicación hasta revisar los términos de la voz instalada.

## Contenido
La política comercial no sustituye asesoría jurídica. El sistema falla cerrado cuando `commercial_use != YES` o `license_status != VERIFIED`.
