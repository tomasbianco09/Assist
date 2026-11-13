# Guía Paso a Paso: Configurar, Levantar y Conectar la App "Assist" con el Celular

Esta guía detalla el procedimiento completo para obtener el código fuente, preparar el entorno virtual, instalar dependencias, poner en marcha el servidor backend de la aplicación **Assist** e interactuar con la interfaz móvil localmente o desde un teléfono en la misma red Wi-Fi.

## Paso 1: Sincronizar el repositorio (git pull / git clone)

Antes de iniciar, asegúrate de contar con la última versión del código fuente disponible en el repositorio del proyecto.

1. Abre tu terminal en la carpeta principal del proyecto.  
2. Si ya posees el repositorio localmente, actualízalo ejecutando:

```sh
git pull origin main
```

3. Si es la primera vez que configuras el proyecto, clónalo con:

```sh
git clone <URL_DEL_REPOSITORIO>
cd assist
```

* **Verificación:** La terminal indicará que el código ya está actualizado (`Already up to date.`) o la clonación se completará correctamente.

---

## Paso 2: Crear y activar el entorno virtual (venv)

Se recomienda utilizar un entorno virtual aislado para gestionar las dependencias de Python sin afectar la instalación global del sistema.

* **Crear el entorno virtual:** `python -m venv venv`  
* **Activar en Windows (CMD):** `venv\Scripts\activate`  
* **Activar en Windows (PowerShell):** `.\venv\Scripts\Activate.ps1`  
* **Activar en macOS / Linux / Git Bash:** `source venv/bin/activate`  
* **Verificación:** En la terminal aparecerá el prefijo `(venv)` al inicio del prompt.

---

## Paso 3: Instalar las dependencias del proyecto

Con el entorno virtual activo, instala los paquetes requeridos por el servidor backend FastAPI.

4. Ejecuta el comando de instalación:

```sh
pip install fastapi uvicorn sqlalchemy pydantic qrcode[pil]
```

5. Si dispones de un archivo `requirements.txt`, también puedes ejecutar:

```sh
pip install -r requirements.txt
```

* **Verificación:** Todos los paquetes se descargarán e instalarán finalizando con el mensaje de éxito en la terminal.

---

---

## Paso 4: Limpiar la base de datos previa (Opcional pero recomendado)

Si ya habías utilizado la aplicación anteriormente y deseas iniciar con registros completamente limpios para evitar conflictos de IDs o sesiones colgadas, elimina el archivo de la base de datos en la raíz del proyecto:

* **En Windows (CMD):** `del assist.db`  
* **En Windows (PowerShell):** `Remove-Item assist.db`  
* **En Git Bash / Mac / Linux:** `rm assist.db`  
* **Verificación:** El archivo `assist.db` desaparece de la carpeta principal del proyecto.

---

## Paso 5: Iniciar el servidor Uvicorn para acceso en red local

Para permitir que tanto tu computadora como tu teléfono accedan al servidor backend, debes iniciar Uvicorn escuchando en todas las interfaces de red (`0.0.0.0`).

6. Abre tu terminal en la carpeta raíz del proyecto.  
7. Ejecuta el siguiente comando:

```sh
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

* **Verificación:** La terminal mostrará que el servidor está activo ejecutándose correctamente (ej. `Uvicorn running on http://0.0.0.0:8000`).

---

## Paso 6: Obtener la dirección IP local de tu PC

Necesitas conocer la dirección IP de tu computadora dentro de la red Wi-Fi para que el teléfono pueda encontrarla.

1. Abre una terminal de comandos en Windows (`cmd`).  
2. Escribe el comando:

```
ipconfig
```

3. Busca el adaptador de red activo (Ethernet o Wi-Fi) y anota la **Dirección IPv4** (por ejemplo: `192.168.100.4`).  
* **Verificación:** Identificas claramente una IP local con formato `192.168.X.X` o `10.X.X.X`.

---

## Paso 7: Conectar y abrir la app desde el teléfono

1. Desactiva los datos móviles de tu teléfono y asegúrate de que esté conectado a la **misma red Wi-Fi** que tu computadora.  
2. Abre el navegador web de tu celular (Google Chrome, Safari, etc.).  
3. Escribe la dirección IP obtenida en el Paso 6 seguida del puerto `8000` y la ruta móvil: `http://192.168.100.4:8000/mobile/?demo=1` *(reemplaza `192.168.100.4` con tu IP real)*.  
* **Verificación:** La interfaz móvil de Assist carga de inmediato en la pantalla de tu teléfono permitiéndote iniciar sesión y probar la vinculación mediante código QR o el botón de emergencia SOS.