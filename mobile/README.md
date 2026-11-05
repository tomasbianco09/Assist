# Assist – versión móvil (celular del adulto mayor)

Interfaz pensada para el celular del **adulto mayor**. Usa la misma API y la misma
base de datos (`assist.db`) que el panel web: no hay una base nueva.

## Cómo probarla
1. Desde la carpeta raíz del proyecto: `uvicorn main:app --host 0.0.0.0 --port 8000`
2. En la compu: abrir `http://localhost:8000/mobile/?demo=1`
3. En el celular (misma red wifi): `http://<IP-de-tu-compu>:8000/mobile/`
4. Entrar con el correo de un usuario registrado con rol **adulto mayor**.

El panel de pruebas del equipo también se sirve desde la API: `http://localhost:8000/panel`
(o doble clic en `index.html`).

Parámetros de la URL:
- `adulto=ID` → atajo para probar: entra directo como ese adulto mayor. Se borra de la
  dirección apenas se usa, para que después de salir de la cuenta no vuelva a entrar solo.
- `api=URL` → dirección de la API si no es la misma máquina (se recuerda en el navegador).
- `demo=1` → muestra el "Modo prueba" para simular la solicitud de un familiar.

## Flujo de la sesión remota (HU-03)
1. El familiar pide ver la pantalla (`POST /sesiones/solicitar/`, estado `pendiente_consentimiento`).
2. El celular detecta la solicitud y muestra **"¿Permites que [Nombre] vea tu pantalla?"**.
3. **Permitir** → `PUT /sesiones/{id}/responder/?aceptar=true` (estado `activa`).
   **No permitir** → `aceptar=false` (estado `rechazada`).
4. Con la sesión activa hay un aviso visible y un botón **Dejar de compartir** (estado `finalizada`).
   El familiar también puede cortarla desde el panel con **Terminar sesión**.

## Botones para terminar o salir: decisiones de diseño
Hay dos cosas distintas que se pueden "cerrar", y a propósito se ven y se comportan distinto:

| | Dejar de compartir | Salir de esta cuenta |
|---|---|---|
| Qué hace | Corta la sesión remota en curso | Desconecta el celular de la cuenta |
| Dónde está | Fijo abajo en la pantalla mientras se comparte, siempre a la vista (aunque la letra sea enorme y haya que desplazarse) | Dentro de **Opciones**, al final, separado del resto |
| Confirmación | **No**. Un solo toque: la persona tiene que poder cortar al instante | **Sí**, en una pantalla completa que explica qué va a pasar |
| Botón por defecto | — | **Quedarme** (el foco empieza ahí) |
| Color | Rojo, porque es la acción de seguridad | Neutro: no queremos invitar a tocarlo |

Por qué "Salir" está escondido y confirmado: si una persona mayor sale sin querer, queda
desconectada de su familia y probablemente no sepa volver a entrar. La pantalla de
confirmación le muestra el correo que va a necesitar para volver.

Al salir, `POST /usuarios/{id}/salir/` corta en el servidor lo que haya abierto (la sesión
activa queda `finalizada` y las solicitudes sin responder quedan `rechazadas`), así el
familiar no se queda esperando una respuesta que nunca va a llegar.

## Accesibilidad
- **Alto contraste**: en *Opciones*. Blanco y amarillo sobre negro (todos los textos superan
  7:1). Si el celular ya pide más contraste (`prefers-contrast: more`) se activa solo; la
  elección se recuerda en el navegador. También se respeta el modo de colores forzados.
- **Zoom y tamaño de letra del sistema**: no se bloquea el zoom con los dedos; todo se mide en
  `rem`/`em`, así la interfaz crece con la letra. En iPhone se toma el tamaño de *Texto más
  grande* (Dynamic Type) y en Chrome para Android el de *Tamaño de fuente*
  (`<meta name="text-scale">`). Con letra muy grande, una *container query* esconde los
  dibujos decorativos y achica márgenes para que los botones sigan entrando. Probado a 320 px
  de ancho con la letra al 200 % sin desplazamiento horizontal.

## Cambios en el backend (main.py)
- `GET /usuarios/{id}`, `POST /usuarios/ingresar/` (por email; todavía sin contraseña) y
  `POST /usuarios/{id}/salir/`.
- `GET /sesiones/pendientes/{adulto_id}`, `GET /sesiones/{id}` y `PUT /sesiones/{id}/finalizar/`.
- `/sesiones/{id}/responder/` ahora solo acepta sesiones en `pendiente_consentimiento` (409 si no).
- Se sirve esta carpeta en `/mobile` y el panel en `/panel`.
