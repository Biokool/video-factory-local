# Prompts maestros para assets

Los textos y etiquetas nunca se generan dentro de una imagen. Las líneas y montes no se generan por difusión.

## Mano editorial frontal
**ID:** `PROMPT_HAND_EDITORIAL_FRONT_V001`

```text
Ilustración editorial educativa de una sola mano abierta vista exactamente de frente por la palma, anatomía creíble y simplificada, exactamente cinco dedos completos y claramente separados: pulgar, índice, medio, anular y meñique; muñeca completa; proporciones naturales; superficie limpia para superponer gráficos vectoriales; línea exterior continua; pliegues naturales muy sutiles; color cálido uniforme; iluminación neutra; sujeto aislado y centrado; sin texto, sin letras, sin números, sin joyería, sin tatuajes, sin símbolos, sin líneas de quiromancia, sin marcas de agua, sin objetos adicionales.
```

```text
Negative: dedos extra, seis dedos, cuatro dedos, dedo faltante, dedos fusionados, dedos duplicados, pulgar extra, pulgar ausente, dedos cortados, puntas fuera del encuadre, mano doble, articulaciones imposibles, anatomía deformada, texto, letras, números, etiquetas, flechas, símbolos, marca de agua, logotipo, joyería, tatuaje, fotorealismo extremo, fondo complejo.
```

Generar izquierda y derecha por separado. El espejo digital solo es aceptable para layout cuando la doctrina visual no depende de lateralidad.

## Fondo cósmico
```text
Fondo cósmico editorial abstracto, degradado azul marino, índigo y violeta, estrellas pequeñas dispersas, nebulosa tenue y elegante, contraste controlado para colocar una mano clara y rótulos blancos, composición limpia, sin texto, sin símbolos, sin planetas reconocibles, sin marca de agua.
```

## Mitología
```text
Ilustración editorial original de <PERSONAJE_O_ATRIBUTO>, inspiración mediterránea clásica general, composición educativa, anatomía y objetos coherentes, sin copiar una escultura o pintura específica, sin texto, sin letras, sin números, sin logotipo, sin marca de agua.
```

## Historia
```text
Escena histórica editorial original de <ÉPOCA_U_OBJETO>, indicadores generales de periodo verificables, composición documental educativa y reutilizable, sin persona moderna identificable, sin texto, sin copiar una obra concreta, sin marca de agua.
```

## QA visual
Rechazar si no hay exactamente cinco dedos visibles en la mano frontal, si falta muñeca, si hay texto rasterizado, si la lateralidad es ambigua o si la mano cambia respecto al master.
