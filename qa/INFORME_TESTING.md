# Informe de testing: Assist (Sprint 1 y Sprint 2)

Rama `feature/accesibilidad-y-rediseno` + cierre del **Sprint 2**. Pruebas ejecutadas entre el 3 y el 13 de noviembre de 2026.

## En resumen

- **Corte inicial (Accesibilidad y Rediseño):** Sumó botones para cortar la sesión remota y salir de la cuenta, modo de alto contraste, soporte para tamaño de letra/zoom y rediseño de la app móvil y del panel de pruebas.
- **Cierre del Sprint 2:** Incorporó el historial y auditoría de sesiones con fecha, duración y autor de cierre (**HU-04 / HU-08**), las notificaciones Push de ayuda en tiempo real hacia el familiar (**HU-04 / SCRUM-49**), el botón de emergencia en la app del celular (**HU-02**), la geolocalización bajo demanda con mapa interactivo Leaflet (**HU-06 / SCRUM-35**) y la corrección de 7 defectos abiertos del corte anterior (**D-01, D-02, D-03, D-05, D-06, D-08 y D-10**).

| Conjunto | Casos | Pasan | Fallan |
|---|---:|---:|---:|
| API (Sprint 1 + Sprint 2) | 42 | 42 | 0 |
| App del celular | 33 | 33 | 0 |
| Panel de pruebas | 20 | 20 | 0 |
| Total | 95 | 95 | 0 |

Al cierre del Sprint 2 los 3 casos que fallaban en la app móvil (APP-27, APP-28 y APP-29) quedaron resueltos y verificados. Solo restan 3 observaciones menores de diseño visual (D-04, D-07 y D-09) y las pruebas en dispositivos físicos.

## Alcance

Entró en las pruebas acumuladas de ambos sprints:

- Ingreso y salida de la cuenta en la app del adulto mayor (con bloqueo de solicitudes entrantes cuando la cuenta está cerrada).
- Pedido de ver la pantalla (HU-03): aceptar, rechazar y cortar desde ambos lados, informando al adulto mayor si el familiar finaliza la sesión.
- Pedido de ayuda (HU-02) desde el celular del adulto mayor y recepción de notificación Push en tiempo real en el panel del familiar (SCRUM-49).
- Geolocalización bajo demanda (HU-06 / SCRUM-35): solicitud desde el panel, pantalla de consentimiento en el celular y visualización de coordenadas en mapa Leaflet.
- Historial y auditoría de sesiones (HU-04 / HU-08) con fecha de inicio, fin, duración en segundos y quién cerró la sesión, visible tanto en el panel como en la app móvil.
- Alto contraste y comportamiento con letra grande (WCAG).

## Cómo se probó

Las pruebas funcionales de caja negra y las mediciones por script se corrieron contra el servidor local en FastAPI y SQLite.

| Parámetro | Detalle |
|---|---|
| Sistema | Windows 11, Python 3.12.10 |
| Servidor | uvicorn local, puerto 8000, SQLite |
| Pantallas emuladas | 320×568, 360×740, 375×812, 390×844 y 1280×860 |
| Datos | Usuarios, vínculos, ubicaciones y sesiones creados en cada corrida |

## Resultados

### API (Sprint 1 + Sprint 2)

Se corren con `python qa/qa_api.py` y el servidor levantado.

| ID | Caso | Esperado | Resultado |
|---|---|---|---|
| API-01, 02 | Registrar familiar y adulto mayor | 200 | Pasa |
| API-03 | Registrar un email repetido | 400 | Pasa |
| API-04, 05 | Obtener un usuario, existente e inexistente | 200 y 404 | Pasa |
| API-06 | Ingresar con mayúsculas y espacios en el correo | 200, mismo usuario | Pasa |
| API-07 | Ingresar con correo desconocido | 404 | Pasa |
| API-08, 09 | Vincular (devolviendo `vinculo_id`), y vincular con roles invertidos | 200 con QR, y 400 | Pasa |
| API-10, 11 | Pedir ayuda como adulto mayor y como familiar | 200 y 400 | Pasa |
| API-12 | Listar pendientes con el nombre del familiar | 200 | Pasa |
| API-13, 14 | Aceptar, y responder dos veces | `activa`, y 409 | Pasa |
| API-15, 16, 17 | Finalizar, finalizar dos veces, finalizar una sesión inexistente | `finalizada`, 409, 404 | Pasa |
| API-18 | Solicitar con un vínculo inexistente | 404 | Pasa |
| API-19, 20 | Rechazar, y que no figure más en pendientes | `rechazada`, lista vacía | Pasa |
| API-21, 22, 23 | Salir con sesión activa o pendiente | Cierra sesiones (`finalizada` / `rechazada`) | Pasa |
| API-24 | Salir con un usuario inexistente | 404 | Pasa |
| API-25 | Salir como familiar con una sesión activa | Cierra 1 | Pasa |
| API-26, 27, 28 | Servir `/mobile/`, `/panel` y `/panel.css` | 200 | Pasa |
| API-29 a 32 | Pedir `/assist.db`, `/main.py` y rutas con `../` | 404 | Pasa |
| API-33 | Reutilizar vínculo existente si el par familiar-adulto ya existe (D-06) | 200, mismo `vinculo_id` | Pasa |
| API-34 | Bloquear pedidos duplicados pendientes en el mismo vínculo (D-03) | 409 | Pasa |
| API-35 | Impedir solicitar pantalla si el adulto mayor salió de su cuenta (D-02) | 409 | Pasa |
| API-36, 37 | Listar alertas pendientes y marcarlas como atendidas (SCRUM-49) | 200 y `atendida` | Pasa |
| API-38 | Consultar historial con fechas, duración en segundos y autor de cierre (HU-08) | 200 | Pasa |
| API-39, 40 | Solicitar ubicación bajo demanda y bloquear duplicados pendientes (HU-06) | 200 y 409 | Pasa |
| API-41, 42 | Aceptar ubicación (guarda coordenadas) y rechazar ubicación (sin coordenadas) | `compartida` y `rechazada` | Pasa |

### App del celular

| ID | Caso | Obtenido | Resultado |
|---|---|---|---|
| APP-01 | Ingresar con el correo vacío | "Escribe tu correo electrónico para entrar." | Pasa |
| APP-02 | Ingresar con un correo desconocido | "No encontramos una cuenta con ese correo" | Pasa |
| APP-03 | Ingresar con el correo de un familiar | Rechaza y explica el motivo | Pasa |
| APP-04 | Abrir Opciones sin cuenta | No aparece "Salir de esta cuenta" ni historial | Pasa |
| APP-05 | Ingresar bien | Saludo inicial y botón de pedir ayuda | Pasa |
| APP-06 | Recargar con la cuenta abierta | Sigue adentro | Pasa |
| APP-07 | Entrar con `?adulto=ID` de un adulto | Entra y borra el parámetro de la dirección | Pasa |
| APP-08 | Entrar con `?adulto=ID` de un familiar | No entra | Pasa |
| APP-09 | El familiar pide ver la pantalla | La pregunta aparece en menos de 3 s | Pasa |
| APP-10 | Tocar No permitir | Estado `rechazada`; Volver funciona | Pasa |
| APP-11 | Tocar Permitir | Estado `activa`, aviso visible y foco en el aviso | Pasa |
| APP-12 | Tocar Dejar de compartir | Un toque, sin confirmación, estado `finalizada` | Pasa |
| APP-13 | El familiar corta la sesión | Muestra "La sesión terminó" indicando quién finalizó (D-08 corregido) | Pasa |
| APP-14 | Tocar Salir de esta cuenta | Pantalla de confirmación con el foco en Quedarme | Pasa |
| APP-15 | Tocar Quedarme | Vuelve al inicio con la cuenta abierta | Pasa |
| APP-16 | Salir con una sesión activa o pendiente | Avisa y cierra en el servidor | Pasa |
| APP-17 | Después de salir | Sin datos guardados y sin más consultas al servidor | Pasa |
| APP-18 | Recargar después de salir | Sigue afuera | Pasa |
| APP-19 a 22 | Acciones y recuperación sin conexión | Mensajes traducidos al español claro (D-01 corregido) | Pasa |
| APP-23, 24 | Activar alto contraste y recargar | Fondo negro, `aria-checked` y persistencia | Pasa |
| APP-25, 26 | Usar Opciones con teclado y clic exterior | Foco contenido, Esc y clic afuera cierran | Pasa |
| APP-27 | Ingresar sin conexión | Muestra mensaje en español: "No pudimos conectarnos con el servidor..." (D-01 corregido) | Pasa |
| APP-28 | Pedir ver la pantalla con la cuenta cerrada | La API rechaza con 409 hasta que el adulto vuelva a entrar (D-02 corregido) | Pasa |
| APP-29 | Dos pedidos seguidos del mismo familiar | La API bloquea el duplicado con 409 (D-03 corregido) | Pasa |
| APP-30 | Tocar "🚨 Pedir ayuda a mi familia" (HU-02) | Envía alerta y confirma en pantalla al adulto mayor | Pasa |
| APP-31, 32 | Recibir solicitud de ubicación: Compartir y No compartir (HU-06) | Envía coordenadas GPS/por defecto o rechaza | Pasa |
| APP-33 | Ver Historial de asistencias en Opciones (HU-08) | Lista las últimas sesiones con estado y duración | Pasa |

### Panel de pruebas

| ID | Caso | Resultado |
|---|---|---|
| PAN-01 | Muestra "API conectada" | Pasa |
| PAN-02 | Registrar sin datos avisa que faltan | Pasa |
| PAN-03, 04 | Registrar bien; con email repetido muestra el error y conserva los campos | Pasa |
| PAN-05 | Generar el QR: muestra imagen, devuelve `vinculo_id` y autocompleta los pasos 04 y 05 (D-05 corregido) | Pasa |
| PAN-06, 07 | Pedir ayuda como adulto mayor y como familiar | Pasa |
| PAN-08 | Solicitar: "Esperando", botón Cancelar visible y Pedir deshabilitado | Pasa |
| PAN-09 | Cancelar: "Finalizada", el botón desaparece y Pedir se habilita | Pasa |
| PAN-10, 11 | El adulto acepta y se ve "Activa"; Terminar sesión deja `finalizada` | Pasa |
| PAN-12 | El adulto rechaza y se ve "Rechazada" | Pasa |
| PAN-13 | Vínculo inexistente muestra el error | Pasa |
| PAN-14 | Alto contraste | Pasa |
| PAN-15 | Limpiar el registro | Pasa |
| PAN-16 | Sin conexión avisa que revisen uvicorn | Pasa |
| PAN-17 | Banner Push SOS aparece automáticamente al recibir pedido de ayuda y permite marcarlo como atendido (SCRUM-49) | Pasa |
| PAN-18, 19 | Solicitar ubicación bajo demanda y renderizar mapa interactivo Leaflet al aceptar (HU-06) | Pasa |
| PAN-20 | Tabla de Historial y Auditoría muestra sesión, personas, inicio, duración y autor de cierre (HU-04 / HU-08) | Pasa |

### Letra grande

En cada pantalla se buscó desplazamiento horizontal y elementos que se salieran del borde, usando un nombre largo: "María de los Ángeles Fernández". WCAG 1.4.4 pide llegar al 200 %.

| Interfaz y ancho | 100 % | 200 % | 250 % | 300 % | 350 % | 400 % |
|---|---|---|---|---|---|---|
| App, 320 px | Bien | Bien | – | Se desborda | – | Se desborda |
| App, 390 px | – | Bien | Bien | Se desborda | Se desborda | – |
| Panel, 320 px | Bien | Se desborda | – | Se desborda | – | Se desborda |
| Panel, 360 px | – | Bien | – | – | – | – |

"Dejar de compartir" se mantuvo siempre visible en una pantalla de 320×568 sin desplazarse:

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

## Defectos corregidos (Sprint 1 y Sprint 2)

| ID / Defecto | Dónde se vio | Corrección aplicada |
|---|---|---|
| Endpoints móviles faltantes en `main.py` | Revisión inicial | Se agregaron en Sprint 1 |
| Botón y hoja de Opciones se salían a 320 px, 200 % | App móvil | Límites de ancho y adaptación al tamaño de letra |
| Elementos con `hidden` seguían visibles | Panel | Regla global para `[hidden]` |
| QR en base64 llenaba el registro | Panel | Se recortan los textos largos |
| **D-01** Error técnico en inglés (`Failed to fetch`) sin conexión | App móvil | Traducido a mensaje claro en español para el adulto mayor |
| **D-02** La API aceptaba solicitudes con la cuenta cerrada | API / App móvil | Se agregó estado `conectado` y bloqueo HTTP 409 al salir |
| **D-03** Acumulación de solicitudes pendientes en el mismo vínculo | API | Se valida y rechaza con HTTP 409 si ya existe una pendiente |
| **D-05** `generar-qr` no devolvía el ID del vínculo | API / Panel | Devuelve `vinculo_id` y autocompleta los campos del panel |
| **D-06** Cada QR duplicaba el vínculo para el mismo par | API | Reutiliza el vínculo existente actualizando el token QR |
| **D-08** Si el familiar cortaba, el adulto mayor volvía al inicio sin aviso | App móvil | Muestra pantalla informando que el familiar finalizó la sesión |
| **D-10** `requirements.txt` tenía el comando `pip install` adentro | Configuración | Lista limpia de paquetes compatible con `pip install -r requirements.txt` |

## Observaciones menores abiertas

| ID | Severidad | Descripción |
|---|---|---|
| D-04 | Media | La app se desborda de 300 % para arriba (cumple el 200 % requerido por WCAG 1.4.4). |
| D-07 | Baja | El panel de pruebas del equipo se desborda a 320 px con letra al 200 % (en 360 px funciona bien). |
| D-09 | Baja | El placeholder de los campos del panel queda en 4,37:1 (levemente por debajo de 4,5:1 AA). |

## Cómo repetir las pruebas

Con el entorno virtual activo, desde la raíz del proyecto:

```sh
pip install -r requirements.txt
uvicorn main:app --port 8000