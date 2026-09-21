# Política visual y ortográfica, español de México

## Decisión sobre las infografías generadas
Las infografías conceptuales anteriores quedan **RECHAZADAS como assets de producción**. Presentan texto deformado, rótulos incompletos, manos inconsistentes y algunas miniaturas no permiten verificar cinco dedos. Sirven únicamente como boceto de arquitectura.

## Regla de manos
1. Toda mano maestra debe mostrar exactamente cinco dedos: pulgar, índice, medio, anular y meñique.
2. No se acepta una mano con dedos cortados, fusionados, duplicados, ocultos sin justificación o con articulaciones imposibles.
3. La lateralidad debe estar en metadata y validarse visualmente.
4. No regenerar la mano entre escenas. Cambiar líneas, montes y signos mediante SVG.
5. La mano técnica no contiene texto ni marcas de quiromancia rasterizadas.

## Ortografía obligatoria
- Línea de la Vida
- Línea de la Cabeza
- Línea del Corazón
- Línea del Destino
- Monte de Júpiter
- Monte de Saturno
- Monte de Mercurio
- Monte del Sol o Monte de Apolo
- Monte de Venus
- Quiromancia terapéutica
- Mitología griega
- Página, animación, configuración, validación, generación

Se usa mayúscula inicial en nombres de líneas y montes cuando funcionan como denominaciones del sistema. Los textos se renderizan con una fuente local que incluya `á é í ó ú ü ñ ¿ ¡`.

## Capas de la escena
`background`, `hand`, `natural_creases`, `palm_lines`, `zones`, `markers`, `guides`, `labels`, `captions`, `effects`.

## Referencia visual aportada
La referencia cuadrada define una mano editorial clara sobre fondo cósmico, etiquetas externas, conectores y codificación por colores. V7 conserva ese lenguaje, pero sustituye círculos aproximados por zonas SVG, retira texto del raster y exige anatomía validada.
