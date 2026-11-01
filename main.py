from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid
import qrcode
import io
import base64

from database import engine, SessionLocal, Base
import models
import schemas

# Crea las tablas automáticamente en SQLite al arrancar
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Assist API",
    description="Backend para la asistencia remota de adultos mayores",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite conexiones locales
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependencia para obtener la sesión de base de datos en cada petición
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"mensaje": "¡Bienvenido a la API de Assist! Servidor activo 🚀"}

# 1. Endpoint para registrar un usuario (Adulto Mayor o Familiar)
@app.post("/usuarios/", response_model=dict)
def crear_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    db_usuario = db.query(models.UsuarioModel).filter(models.UsuarioModel.email == usuario.email).first()
    if db_usuario:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    nuevo_usuario = models.UsuarioModel(
        nombre=usuario.nombre,
        email=usuario.email,
        rol=usuario.rol
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return {"id": nuevo_usuario.id, "nombre": nuevo_usuario.nombre, "rol": nuevo_usuario.rol, "mensaje": "Usuario creado con éxito"}

# 2. Endpoint para generar el Código QR de Vinculación (HU-01)
@app.post("/vinculos/generar-qr/")
@app.post("/vinculos/generar-qr/")
def generar_qr_vinculo(vinculo: schemas.VinculoCreate, db: Session = Depends(get_db)):
    # Buscamos a los usuarios por su ID
    familiar = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == vinculo.familiar_id).first()
    adulto = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == vinculo.adulto_id).first()
    
    # 1. Validamos que ambos existan
    if not familiar or not adulto:
        raise HTTPException(status_code=404, detail="Familiar o Adulto Mayor no encontrado")
    
    # 2. Validamos que tengan los roles correctos (¡Aquí estaba la falla!)
    if familiar.rol != "familiar":
        raise HTTPException(status_code=400, detail=f"El usuario '{familiar.nombre}' no tiene el rol de familiar (su rol es {familiar.rol})")
    
    if adulto.rol != "adulto_mayor":
        raise HTTPException(status_code=400, detail=f"El usuario '{adulto.nombre}' no tiene el rol de adulto mayor (su rol es {adulto.rol})")

    # Si todo está bien, generamos el código único (token para el QR)
    codigo_token = str(uuid.uuid4())
    
    nuevo_vinculo = models.VinculoModel(
        familiar_id=vinculo.familiar_id,
        adulto_id=vinculo.adulto_id,
        codigo_qr=codigo_token
    )
    db.add(nuevo_vinculo)
    db.commit()
    
    # Generamos la imagen del código QR en memoria
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(codigo_token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    return {
        "mensaje": "Vínculo y código QR generados correctamente",
        "codigo_token": codigo_token,
        "qr_imagen_base64": qr_base64
    }


# ==========================================
# HU-02: Botón de "Pedir Ayuda"
# ==========================================
@app.post("/solicitudes/pedir-ayuda/")
def pedir_ayuda(solicitud: schemas.SolicitudCreate, db: Session = Depends(get_db)):
    # 1. Buscamos al usuario por su ID
    usuario = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == solicitud.usuario_id).first()
    
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # 2. Validamos que el usuario que pide ayuda sea un adulto mayor
    if usuario.rol != "adulto_mayor":
        raise HTTPException(
            status_code=400, 
            detail=f"Acción denegada: El usuario '{usuario.nombre}' es un {usuario.rol}. Solo los adultos mayores pueden pedir asistencia."
        )

    # 3. Si es un adulto mayor válido, creamos la solicitud
    nueva_solicitud = models.SolicitudModel(
        usuario_id=solicitud.usuario_id,
        estado="pendiente"
    )
    db.add(nueva_solicitud)
    db.commit()
    db.refresh(nueva_solicitud)
    
    return {
        "mensaje": "Alerta de ayuda enviada correctamente",
        "solicitud_id": nueva_solicitud.id,
        "usuario": usuario.nombre,
        "estado": nueva_solicitud.estado
    }

# ==========================================
# HU-03: Visualización Remota con Consentimiento
# ==========================================
@app.post("/sesiones/solicitar/")
def solicitar_sesion(sesion: schemas.SesionRemotaCreate, db: Session = Depends(get_db)):
    # Verificamos que el vínculo exista
    vinculo = db.query(models.VinculoModel).filter(models.VinculoModel.id == sesion.vinculo_id).first()
    if not vinculo:
        raise HTTPException(status_code=404, detail="Vínculo no encontrado")
    
    nueva_sesion = models.SesionRemotaModel(
        vinculo_id=sesion.vinculo_id,
        estado="pendiente_consentimiento"
    )
    db.add(nueva_sesion)
    db.commit()
    db.refresh(nueva_sesion)
    
    return {
        "mensaje": "Solicitud de visualización enviada. Esperando consentimiento del adulto mayor.",
        "sesion_id": nueva_sesion.id,
        "estado": nueva_sesion.estado
    }

@app.put("/sesiones/{sesion_id}/responder/")
def responder_sesion(sesion_id: int, aceptar: bool, db: Session = Depends(get_db)):
    sesion = db.query(models.SesionRemotaModel).filter(models.SesionRemotaModel.id == sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    if aceptar:
        sesion.estado = "activa"
        mensaje = "Sesión aceptada. Conexión de pantalla iniciada."
    else:
        sesion.estado = "rechazada"
        mensaje = "Sesión rechazada por el adulto mayor."
    
    db.commit()
    return {"sesion_id": sesion.id, "estado": sesion.estado, "mensaje": mensaje}