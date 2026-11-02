# Assist – versión móvil (Prog 2: pantalla de consentimiento)

Interfaz pensada para el celular del **adulto mayor**. Usa la misma API y la misma
base de datos (`assist.db`) que el panel web: no hay una base nueva.

## Cómo probarla
1. Desde la carpeta raíz del proyecto: `uvicorn main:app --host 0.0.0.0 --port 8000`
2. En la compu: abrir `http://localhost:8000/mobile/?adulto=2&demo=1`
3. En el celular (misma red wifi): `http://<IP-de-tu-compu>:8000/mobile/?adulto=2`

Parámetros de la URL (se guardan en el navegador):
- `adulto=ID` → ID del adulto mayor dueño del celular (por defecto 2)
- `api=URL` → dirección de la API si no es la misma máquina
- `demo=1` → muestra el "Modo prueba" para simular la solicitud de un familiar

## Flujo
1. El familiar pide ver la pantalla (`POST /sesiones/solicitar/`, estado `pendiente_consentimiento`).
2. El celular detecta la solicitud y muestra **"¿Permites que [Nombre] vea tu pantalla?"**.
3. **Permitir** → `PUT /sesiones/{id}/responder/?aceptar=true` (estado `activa`).
   **No permitir** → `aceptar=false` (estado `rechazada`).
4. Con la sesión activa hay un aviso visible y un botón **Dejar de compartir** (estado `finalizada`).

## Cambios en el backend (main.py)
- `GET /usuarios/{id}` y `GET /sesiones/pendientes/{adulto_id}` (para leer el nombre del familiar).
- `PUT /sesiones/{id}/finalizar/` (cortar la sesión).
- `/sesiones/{id}/responder/` ahora solo acepta sesiones en `pendiente_consentimiento`.
- Se sirve esta carpeta en `/mobile`.
