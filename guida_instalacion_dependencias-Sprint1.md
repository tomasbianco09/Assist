# 📱 Guía de Instalación y Ejecución - Proyecto Assist (Sprint 1)

¡Hola equipo! Esta guía detalla los pasos necesarios para clonar el repositorio del proyecto, configurar el entorno local, instalar las dependencias y poner en marcha tanto el backend (FastAPI) como la interfaz web.

---

## 🛠️ Requisitos Previos
Asegúrate de tener instalado en tu computadora:
1. **Python** (versión 3.9 o superior recomendada). Puedes verificarlo en la terminal con:
   ```bash
   python --version
   ```
2. **Git** para la gestión de versiones.

---

## 📥 Paso 1: Clonar el Repositorio
Abre tu terminal (consola) y clona el repositorio oficial de GitHub:
```bash
git clone https://github.com/tomasbianco09/Assist.git
cd Assist
```

---

## 🐍 Paso 2: Crear y Activar el Entorno Virtual
Es una buena práctica aislar las dependencias del proyecto usando un entorno virtual:

* **En Windows (CMD o PowerShell):**
  ```bash
  python -m venv venv
  venv\Scripts\activate
  ```
* **En macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

---

## 📦 Paso 3: Instalar las Dependencias
Con el entorno virtual activo, instala las librerías necesarias ejecutando:
```bash
pip install fastapi uvicorn sqlalchemy pydantic qrcode[pil]
```

---

## 🚀 Paso 4: Levantar el Servidor Backend (FastAPI)
Para iniciar el servidor local que maneja la base de datos SQLite y los endpoints, ejecuta:
```bash
uvicorn main:app --reload
```
* Verás en la consola que el servidor corre en: `http://127.0.0.1:8000`
* Puedes verificar la documentación interactiva de la API ingresando en tu navegador a: `http://127.0.0.1:8000/docs`

---

## 💻 Paso 5: Abrir la Interfaz Web (Panel de Control)
1. Ve a la carpeta del proyecto en tu explorador de archivos.
2. Haz doble clic directamente sobre el archivo **`index.html`** para abrirlo en tu navegador favorito (Chrome, Brave, Firefox, etc.).
3. ¡Listo! El panel web se conectará automáticamente con el backend local para registrar usuarios, generar códigos QR (HU-01) y simular alertas de asistencia (HU-02).

---