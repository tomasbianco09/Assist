# Informe de testing: Assist

Rama `feature/accesibilidad-y-rediseno`, commit `a5d68ba`. Pruebas del 3 y el 5 de noviembre de 2026.

## En resumen

Este sprint sumó tres cosas a Assist: botones para cortar la sesión remota y salir de la cuenta, un modo de alto contraste y una interfaz que acompaña el tamaño de letra y el zoom. También se rediseñaron la app del celular y el panel de pruebas.

| Conjunto | Casos | Pasan | Fallan |
|---|---:|---:|---:|
| API | 32 | 32 | 0 |
| App del celular | 29 | 26 | 3 |
| Panel de pruebas | 16 | 16 | 0 |
| Total | 77 | 74 | 3 |

Al final del informe quedan 10 defectos abiertos y ninguno impide hacer la demo. Lo más flojo es la cobertura: nada se probó en un celular físico, así que el resultado sobre letra grande y zoom es una aproximación hecha en un navegador de escritorio. La sección "Lo que no se probó" lo detalla.

## Alcance

Entró en las pruebas:

- Ingreso y salida de la cuenta en la app del adulto mayor.
- Pedido de ver la pantalla: aceptar, rechazar y cortar, desde los dos lados.
- Alto contraste y comportamiento con letra grande.
- Los endpoints nuevos y los que ya existían del Sprint 1.

Assist todavía no transmite la pantalla. La "sesión remota" es un cambio de estado en la base de datos, y cuando el panel dice "Estás viendo la pantalla" no hay video de por medio. Por eso se probó el flujo de permisos y no la calidad ni la privacidad de una transmisión. El pedido de ayuda (HU-02) tampoco existe en la app del celular: se simula desde el panel y a la persona familiar no le llega ningún aviso.

## Cómo se probó

Las pruebas se corrieron en una sesión con Claude Code, que manejó el navegador y la API y registró los resultados. Son pruebas funcionales de caja negra más mediciones por script. El repositorio no tiene una suite automatizada que corra en cada cambio.

| | |
|---|---|
| Sistema | Windows 11, Python 3.12.10 |
| Servidor | uvicorn local, puerto 8000, SQLite |
| Navegador | Navegador integrado de la app de Claude |
| Pantallas emuladas | 320×568, 360×740, 375×812, 390×844 y 1280×860 |
| Datos | Usuarios de prueba creados para cada corrida |

Tres simplificaciones afectan cómo leer los resultados:

- La letra grande se simuló cambiando el `font-size` de la página, sin tocar la configuración de un teléfono.
- La falta de conexión se simuló reemplazando `fetch` para que fallara. No se cortó una red real.
- La mayoría de los toques fueron `click()` por script. Con clic y teclado reales se probaron Permitir, Terminar sesión, abrir y cerrar Opciones, y navegar con Tab, Espacio y Esc.

## Resultados

### API

Se corren con `python qa/qa_api.py` y el servidor levantado.

| ID | Caso | Esperado | Resultado |
|---|---|---|---|
| API-01, 02 | Registrar familiar y adulto mayor | 200 | Pasa |
| API-03 | Registrar un email repetido | 400 | Pasa |
| API-04, 05 | Obtener un usuario, existente e inexistente | 200 y 404 | Pasa |
| API-06 | Ingresar con mayúsculas y espacios en el correo | 200, mismo usuario | Pasa |
| API-07 | Ingresar con correo desconocido | 404 | Pasa |
| API-08, 09 | Vincular, y vincular con los roles invertidos | 200 con QR, y 400 | Pasa |
| API-10, 11 | Pedir ayuda como adulto mayor y como familiar | 200 y 400 | Pasa |
| API-12 | Listar pendientes con el nombre del familiar | 200 | Pasa |
| API-13, 14 | Aceptar, y responder dos veces | `activa`, y 409 | Pasa |
| API-15, 16, 17 | Finalizar, finalizar dos veces, finalizar una sesión inexistente | `finalizada`, 409, 404 | Pasa |
| API-18 | Solicitar con un vínculo inexistente | 404 | Pasa |
| API-19, 20 | Rechazar, y que no figure más en pendientes | `rechazada`, lista vacía | Pasa |
| API-21, 22, 23 | Salir con una sesión activa y una pendiente | Cierra 2: `finalizada` y `rechazada` | Pasa |
| API-24 | Salir con un usuario inexistente | 404 | Pasa |
| API-25 | Salir como familiar con una sesión activa | Cierra 1 | Pasa |
| API-26, 27, 28 | Servir `/mobile/`, `/panel` y `/panel.css` | 200 | Pasa |
| API-29 a 32 | Pedir `/assist.db`, `/main.py` y rutas con `../` | 404 | Pasa |

Los últimos cuatro importan porque el panel se agregó al servidor sirviendo archivos sueltos. Si se hubiera servido la carpeta entera, cualquiera podría haber bajado la base de datos.

### App del celular

| ID | Caso | Obtenido | Resultado |
|---|---|---|---|
| APP-01 | Ingresar con el correo vacío | "Escribe tu correo electrónico para entrar." | Pasa |
| APP-02 | Ingresar con un correo desconocido | "No encontramos una cuenta con ese correo" | Pasa |
| APP-03 | Ingresar con el correo de un familiar | Rechaza y explica el motivo | Pasa |
| APP-04 | Abrir Opciones sin cuenta | No aparece "Salir de esta cuenta" | Pasa |
| APP-05 | Ingresar bien | "Hola, Marta" y pantalla de inicio | Pasa |
| APP-06 | Recargar con la cuenta abierta | Sigue adentro | Pasa |
| APP-07 | Entrar con `?adulto=ID` de un adulto | Entra y borra el parámetro de la dirección | Pasa |
| APP-08 | Entrar con `?adulto=ID` de un familiar | No entra | Pasa |
| APP-09 | El familiar pide ver la pantalla | La pregunta aparece en 2,97 s (el sondeo es cada 3 s) | Pasa |
| APP-10 | Tocar No permitir | Estado `rechazada`; el sondeo no pisa la pantalla; Volver funciona | Pasa |
| APP-11 | Tocar Permitir | Estado `activa`, aviso visible y foco en el aviso | Pasa |
| APP-12 | Tocar Dejar de compartir | Un toque, sin confirmación, estado `finalizada` | Pasa |
| APP-13 | El familiar corta la sesión | Vuelve al inicio solo (ver D-08) | Pasa |
| APP-14 | Tocar Salir de esta cuenta | Pantalla de confirmación con el foco en Quedarme | Pasa |
| APP-15 | Tocar Quedarme | Vuelve al inicio con la cuenta abierta | Pasa |
| APP-16 | Salir con una sesión activa y una pendiente | Avisa las dos cosas; quedan `finalizada` y `rechazada` | Pasa |
| APP-17 | Después de salir | Sin datos guardados y sin más consultas al servidor | Pasa |
| APP-18 | Recargar después de salir | Sigue afuera | Pasa |
| APP-19 | Responder sin conexión | Muestra el error y deja reintentar; el reintento funciona | Pasa (texto: D-01) |
| APP-20 | Dejar de compartir sin conexión | Muestra el error, sigue el botón; el estado queda `activa` | Pasa (texto: D-01) |
| APP-21 | Salir sin conexión | Muestra el error y no cierra la cuenta | Pasa (texto: D-01) |
| APP-22 | Perder la conexión con la pantalla abierta | "No pudimos conectarnos", y se recupera sola | Pasa |
| APP-23 | Activar alto contraste | Fondo negro, `aria-checked` y color de la barra del navegador actualizados | Pasa |
| APP-24 | Recargar con alto contraste | Se mantiene | Pasa |
| APP-25 | Usar Opciones con teclado | Tab no se escapa de la hoja, Espacio cambia el contraste, Esc cierra y el foco vuelve a Opciones | Pasa |
| APP-26 | Clic afuera de la hoja y dentro de su margen | Afuera cierra, en el margen no | Pasa |
| APP-27 | Ingresar sin conexión | Muestra solo "Failed to fetch" | Falla (D-01) |
| APP-28 | Pedir ver la pantalla con la cuenta cerrada | La API acepta y la pregunta aparece al volver a entrar | Falla (D-02) |
| APP-29 | Dos pedidos seguidos del mismo familiar | Al rechazar uno aparece el otro enseguida | Falla (D-03) |

### Panel de pruebas

| ID | Caso | Resultado |
|---|---|---|
| PAN-01 | Muestra "API conectada" | Pasa |
| PAN-02 | Registrar sin datos avisa que faltan | Pasa |
| PAN-03, 04 | Registrar bien; con email repetido muestra el error y conserva los campos | Pasa |
| PAN-05 | Generar el QR: la imagen se ve y el registro recorta el base64 | Pasa |
| PAN-06, 07 | Pedir ayuda como adulto mayor y como familiar | Pasa |
| PAN-08 | Solicitar: "Esperando", botón Cancelar visible y Pedir deshabilitado | Pasa |
| PAN-09 | Cancelar: "Finalizada", el botón desaparece y Pedir se habilita | Pasa |
| PAN-10, 11 | El adulto acepta y se ve "Activa"; Terminar sesión deja `finalizada` | Pasa |
| PAN-12 | El adulto rechaza y se ve "Rechazada" | Pasa |
| PAN-13 | Vínculo inexistente muestra el error | Pasa |
| PAN-14 | Alto contraste | Pasa |
| PAN-15 | Limpiar el registro | Pasa |
| PAN-16 | Sin conexión avisa que revisen uvicorn | Pasa |

### Letra grande

En cada pantalla se buscó desplazamiento horizontal y elementos que se salieran del borde, usando a propósito un nombre largo: "María de los Ángeles Fernández". WCAG 1.4.4 pide llegar al 200 %.

| Interfaz y ancho | 100 % | 200 % | 250 % | 300 % | 350 % | 400 % |
|---|---|---|---|---|---|---|
| App, 320 px | Bien | Bien | – | Se desborda | – | Se desborda |
| App, 390 px | – | Bien | Bien | Se desborda | Se desborda | – |
| Panel, 320 px | Bien | Se desborda | – | Se desborda | – | Se desborda |
| Panel, 360 px | – | Bien | – | – | – | – |

"Dejar de compartir" es el botón que más importa acá, y en una pantalla de 320×568 se mantuvo siempre visible sin desplazarse:

| Tamaño de letra | Alto del botón | Parte de la pantalla que ocupa la barra |
|---:|---:|---:|
| 100 % | 61 px | 14 % |
| 200 % | 151 px | 32 % |
| 300 % | 225 px | 35 % |
| 400 % | 298 px | 35 % |

### Contraste

Calculado con la fórmula de WCAG sobre los colores definidos en el CSS (`python qa/qa_contrast.py`). AA pide 4,5:1 para texto normal y AAA pide 7:1.

| Modo | Elemento | Contraste | Nivel |
|---|---|---:|---|
| Normal | Texto sobre el fondo | 12,69:1 | AAA |
| Normal | Texto secundario sobre el fondo | 6,13:1 | AA |
| Normal | Botón principal | 7,82:1 | AAA |
| Normal | Botón rojo | 6,69:1 | AA |
| Normal | Botón de pedir ayuda (panel) | 5,43:1 | AA |
| Normal | Insignia "Esperando" (panel) | 4,69:1 | AA |
| Alto contraste | Texto sobre el fondo | 21:1 | AAA |
| Alto contraste | Botón principal | 16,57:1 | AAA |
| Alto contraste | Botón rojo | 12,33:1 | AAA |
| Alto contraste | Botón de pedir ayuda (panel) | 12,34:1 | AAA |

Se midieron los pares de color, y con eso alcanza para los textos sobre fondo liso. No se usó un auditor automático como axe o Lighthouse sobre las páginas.

## Defectos encontrados y corregidos

| Defecto | Dónde se vio | Corrección |
|---|---|---|
| Faltaban en `main.py` los endpoints que usaba la app móvil, así que no funcionaba con el código de `main` | Revisión inicial | Se agregaron |
| El botón Opciones se salía de la pantalla | 320 px, 200 % | Límite de ancho y menos relleno |
| "Fernández" se cortaba en dos líneas sin guion en el título | 320 px, 200 % | Título más chico en ese caso |
| La hoja de Opciones se salía por el costado | 320 px, 200 % | La hoja también responde al tamaño de letra |
| Los elementos con `hidden` seguían visibles: "Cancelar solicitud" quedaba en pantalla con la sesión terminada | Panel | Regla global para `[hidden]` (reverificado en PAN-09 y APP-04) |
| El encabezado fijo tapaba casi toda la pantalla | Panel, 360 px, 200 % | Fijo solo en pantallas anchas |
| El botón Limpiar se salía de la pantalla | Panel, 360 px, 200 % | El encabezado del registro ahora baja de línea |
| El QR en base64 llenaba todo el registro | Panel | Se recortan los textos largos |

## Defectos abiertos

| ID | Severidad | Descripción | Cómo reproducirlo |
|---|---|---|---|
| D-01 | Media | Sin conexión, la app muestra el error técnico en inglés a una persona mayor. Al ingresar es lo único que ve. | Ingresar con el servidor apagado |
| D-02 | Media | La pantalla de salida dice que los familiares no podrán pedir ver la pantalla, pero la API lo acepta y la pregunta aparece al volver a entrar, quizás mucho después. | APP-28 |
| D-03 | Media | La API deja acumular pedidos del mismo vínculo y no vencen nunca. Rechazar uno hace aparecer el siguiente. Un adulto de prueba llegó a tener 8 pendientes. | APP-29 |
| D-04 | Media | La app se desborda de 300 % para arriba (ver la tabla de letra grande). Cumple el 200 % de WCAG, pero los tamaños de accesibilidad más grandes de iPhone podrían superarlo; eso no se midió. | 320 px con letra al 300 % |
| D-05 | Media | `generar-qr` no devuelve el ID del vínculo, y el paso 04 del panel lo pide. Quien prueba tiene que adivinarlo o mirar la base. | Generar un QR y buscar el ID |
| D-06 | Baja | Cada QR crea un vínculo nuevo aunque el par ya exista. Un mismo par llegó a tener 4. | Generar dos QR iguales |
| D-07 | Baja | El panel se desborda a 320 px con letra al 200 %. Es una herramienta del equipo, por eso la severidad baja. | 320 px con letra al 200 % |
| D-08 | Baja | Si el familiar corta, la persona mayor vuelve al inicio sin ningún mensaje. Puede no enterarse de que terminó. | APP-13 |
| D-09 | Baja | Tres contrastes quedan por debajo de lo recomendado: el texto de ejemplo de los campos del panel (4,37:1, por debajo de AA), el borde del campo del modo prueba (1,35:1) y los bordes de las tarjetas (1,35:1, decorativos). | Tabla de `qa_contrast.py` |
| D-10 | Baja | `requirements.txt` contiene el comando `pip install ...` en lugar de la lista de paquetes, así que `pip install -r requirements.txt` da error. La guía de instalación no lo usa. | Correr ese comando |

Hay además una limitación conocida, que no se cuenta como defecto del sprint pero sería bloqueante antes de usar esto con personas reales: no hay autenticación. Se entra con el correo, sin contraseña, y `?adulto=ID` entra directo. Cualquier cliente puede llamar cualquier endpoint con cualquier ID, por ejemplo aceptar un pedido en nombre de otra persona. Para algo que va a mostrar la pantalla de un adulto mayor, este es el primer punto a resolver.

## Lo que no se probó

- Celulares físicos, Android o iPhone.
- La configuración real de tamaño de letra: *Dynamic Type* en iPhone y el tamaño de fuente en Android. El código las contempla, pero no se comprobó que funcionen.
- El zoom con los dedos. Se verificó que nada lo bloquea, sin hacer el gesto.
- La activación automática del contraste (`prefers-contrast`), los colores forzados y el movimiento reducido. El CSS existe, pero no se emuló.
- Lectores de pantalla (TalkBack y VoiceOver).
- Otros navegadores: Safari y Firefox.
- El panel abierto con doble clic en `index.html`. Solo se comprobó que la API responde a ese origen (CORS con `Origin: null`).
- El panel abierto desde otro dispositivo. Por lectura del código, va a fallar porque la dirección de la API está fija en `localhost`.
- Personas mayores reales. Es la prueba que más información daría sobre estas decisiones de diseño.

## Próximos pasos

Prueba en un Android y un iPhone reales, con esta lista:

1. Poner la letra al máximo en el sistema, abrir la app y confirmar que crece y que los botones se pueden tocar.
2. Hacer zoom con los dedos en la pantalla de consentimiento.
3. Activar el alto contraste y mirarla al sol o con poco brillo.
4. Recorrer con TalkBack y VoiceOver desde el ingreso hasta salir de la cuenta.
5. Hacer la tarea con una persona mayor sin ayudarla: "dejá de compartir la pantalla" y "salí de la cuenta".

Después de eso, en orden: corregir D-01 a D-03, que son los que afectan directamente a la persona mayor; agregar el ID del vínculo a la respuesta (D-05); y convertir `qa_api.py` en una suite de pytest que corra sola.

## Cómo repetir las pruebas

Con el entorno virtual activo, desde la raíz del proyecto:

```sh
pip install fastapi uvicorn sqlalchemy pydantic qrcode[pil]
uvicorn main:app --port 8000
```

En otra terminal:

```sh
python qa/qa_api.py
python qa/qa_contrast.py
```

La app está en `http://localhost:8000/mobile/?demo=1` y el panel en `http://localhost:8000/panel`. Para simular letra grande, en la consola del navegador con la vista de celular activada:

```js
document.documentElement.style.fontSize = '200%'
```

`qa_api.py` crea usuarios y sesiones en `assist.db`. También abre y cierra enseguida sesiones en otros vínculos para encontrar el suyo, por culpa de D-05, así que conviene correrlo con una base de prueba.
