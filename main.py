from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import text
import datetime
import random
import uuid
import qrcode
import io
import base64

from database import engine, SessionLocal, Base
import models
import schemas

# Crea las tablas automáticamente en SQLite al arrancar
Base.metadata.create_all(bind=engine)

# Migración ligera automática por si assist.db ya existía del Sprint 1
def asegurar_columnas_sprint2():
    alteraciones = [
        ("usuarios", "conectado", "INTEGER DEFAULT 1"),
        ("solicitudes", "fecha_creacion", "DATETIME"),
        ("sesiones_remotas", "fecha_inicio", "DATETIME"),
        ("sesiones_remotas", "fecha_fin", "DATETIME"),
        ("sesiones_remotas", "duracion_segundos", "INTEGER"),
        ("sesiones_remotas", "cerrada_por", "VARCHAR"),
    ]
    with engine.connect() as conn:
        for tabla, col, tipo in alteraciones:
            try:
                conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}"))
                conn.commit()
            except Exception:
                pass

asegurar_columnas_sprint2()

app = FastAPI(
    title="Assist API",
    description="Backend para la asistencia remota de adultos mayores",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def cerrar_registro_sesion(sesion: models.SesionRemotaModel, nuevo_estado: str, autor: str):
    ahora = datetime.datetime.utcnow()
    sesion.estado = nuevo_estado
    sesion.fecha_fin = ahora
    sesion.cerrada_por = autor
    if sesion.fecha_inicio:
        sesion.duracion_segundos = max(0, int((ahora - sesion.fecha_inicio).total_seconds()))
    else:
        sesion.duracion_segundos = 0

def generar_token_6_digitos(db: Session) -> str:
    for _ in range(30):
        token = f"{random.randint(0, 999999):06d}"
        existe = db.query(models.GrupoFamiliarModel).filter(
            models.GrupoFamiliarModel.codigo_token == token
        ).first()
        if not existe:
            return token
    raise HTTPException(status_code=500, detail="No se pudo generar un token único de 6 dígitos.")

@app.get("/")
def read_root():
    return {"mensaje": "¡Bienvenido a la API de Assist! Servidor activo 🚀"}

# ==========================================
# 1. Gestión de Usuarios e Ingreso/Salida
# ==========================================
@app.post("/usuarios/", response_model=dict)
def crear_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    db_usuario = db.query(models.UsuarioModel).filter(models.UsuarioModel.email == usuario.email).first()
    if db_usuario:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    nuevo_usuario = models.UsuarioModel(
        nombre=usuario.nombre,
        email=usuario.email,
        rol=usuario.rol,
        conectado=1
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return {"id": nuevo_usuario.id, "nombre": nuevo_usuario.nombre, "rol": nuevo_usuario.rol, "mensaje": "Usuario creado con éxito"}

@app.get("/usuarios/{usuario_id}")
def obtener_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"id": usuario.id, "nombre": usuario.nombre, "email": usuario.email, "rol": usuario.rol, "conectado": bool(usuario.conectado)}

@app.post("/usuarios/ingresar/")
def ingresar(ingreso: schemas.IngresoRequest, db: Session = Depends(get_db)):
    email = ingreso.email.strip().lower()
    usuario = db.query(models.UsuarioModel).filter(models.UsuarioModel.email.ilike(email)).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="No encontramos una cuenta con ese correo")
    usuario.conectado = 1
    db.commit()
    return {"id": usuario.id, "nombre": usuario.nombre, "email": usuario.email, "rol": usuario.rol}

@app.post("/usuarios/{usuario_id}/salir/")
def salir(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if usuario.rol == "adulto_mayor":
        usuario.conectado = 0

    columna = models.VinculoModel.adulto_id if usuario.rol == "adulto_mayor" else models.VinculoModel.familiar_id
    sesiones = (
        db.query(models.SesionRemotaModel)
        .join(models.VinculoModel, models.SesionRemotaModel.vinculo_id == models.VinculoModel.id)
        .filter(columna == usuario_id)
        .filter(models.SesionRemotaModel.estado.in_(["pendiente_consentimiento", "activa"]))
        .all()
    )
    for s in sesiones:
        nuevo_est = "rechazada" if s.estado == "pendiente_consentimiento" else "finalizada"
        cerrar_registro_sesion(s, nuevo_est, "salida")

    ubicaciones = (
        db.query(models.UbicacionModel)
        .join(models.VinculoModel, models.UbicacionModel.vinculo_id == models.VinculoModel.id)
        .filter(columna == usuario_id)
        .filter(models.UbicacionModel.estado == "pendiente_consentimiento")
        .all()
    )
    for u in ubicaciones:
        u.estado = "rechazada"
        u.fecha_respuesta = datetime.datetime.utcnow()

    db.commit()
    return {"mensaje": "Sesión cerrada", "sesiones_cerradas": len(sesiones)}

# ==========================================
# 2. HU-01: Vínculo por QR (Corrige D-05 y D-06)
# ==========================================
@app.post("/vinculos/generar-qr/")
def generar_qr_vinculo(vinculo: schemas.VinculoCreate, db: Session = Depends(get_db)):
    familiar = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == vinculo.familiar_id).first()
    adulto = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == vinculo.adulto_id).first()
    
    if not familiar or not adulto:
        raise HTTPException(status_code=404, detail="Familiar o Adulto Mayor no encontrado")
    if familiar.rol != "familiar":
        raise HTTPException(status_code=400, detail=f"El usuario '{familiar.nombre}' no tiene el rol de familiar (su rol es {familiar.rol})")
    if adulto.rol != "adulto_mayor":
        raise HTTPException(status_code=400, detail=f"El usuario '{adulto.nombre}' no tiene el rol de adulto mayor (su rol es {adulto.rol})")

    codigo_token = str(uuid.uuid4())

    vinculo_existente = (
        db.query(models.VinculoModel)
        .filter(
            models.VinculoModel.familiar_id == vinculo.familiar_id,
            models.VinculoModel.adulto_id == vinculo.adulto_id
        )
        .first()
    )
    if vinculo_existente:
        vinculo_existente.codigo_qr = codigo_token
        vinculo_existente.fecha_creacion = datetime.datetime.utcnow()
        db.commit()
        db.refresh(vinculo_existente)
        registro_vinculo = vinculo_existente
    else:
        registro_vinculo = models.VinculoModel(
            familiar_id=vinculo.familiar_id,
            adulto_id=vinculo.adulto_id,
            codigo_qr=codigo_token
        )
        db.add(registro_vinculo)
        db.commit()
        db.refresh(registro_vinculo)
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(codigo_token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    return {
        "mensaje": "Vínculo y código QR generados correctamente",
        "vinculo_id": registro_vinculo.id,
        "codigo_token": codigo_token,
        "qr_imagen_base64": qr_base64
    }

# ==========================================
# 3. HU-02 y SCRUM-49: Alertas y Notificaciones Push
# ==========================================
@app.post("/solicitudes/pedir-ayuda/")
def pedir_ayuda(solicitud: schemas.SolicitudCreate, db: Session = Depends(get_db)):
    usuario = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == solicitud.usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if usuario.rol != "adulto_mayor":
        raise HTTPException(
            status_code=400, 
            detail=f"Acción denegada: El usuario '{usuario.nombre}' es un {usuario.rol}. Solo los adultos mayores pueden pedir asistencia."
        )

    nueva_solicitud = models.SolicitudModel(
        usuario_id=solicitud.usuario_id,
        estado="pendiente",
        fecha_creacion=datetime.datetime.utcnow()
    )
    db.add(nueva_solicitud)
    db.commit()
    db.refresh(nueva_solicitud)
    
    return {
        "mensaje": "Alerta de ayuda enviada correctamente",
        "solicitud_id": nueva_solicitud.id,
        "usuario": usuario.nombre,
        "estado": nueva_solicitud.estado,
        "fecha_creacion": nueva_solicitud.fecha_creacion.isoformat()
    }

@app.get("/solicitudes/pendientes/")
def listar_solicitudes_pendientes(db: Session = Depends(get_db)):
    filas = (
        db.query(models.SolicitudModel, models.UsuarioModel)
        .join(models.UsuarioModel, models.SolicitudModel.usuario_id == models.UsuarioModel.id)
        .filter(models.SolicitudModel.estado == "pendiente")
        .order_by(models.SolicitudModel.id.desc())
        .all()
    )
    return [
        {
            "solicitud_id": s.id,
            "usuario_id": u.id,
            "adulto_nombre": u.nombre,
            "estado": s.estado,
            "fecha_creacion": s.fecha_creacion.isoformat() if s.fecha_creacion else None
        }
        for s, u in filas
    ]

@app.put("/solicitudes/{solicitud_id}/atender/")
def atender_solicitud(solicitud_id: int, db: Session = Depends(get_db)):
    solicitud = db.query(models.SolicitudModel).filter(models.SolicitudModel.id == solicitud_id).first()
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud de ayuda no encontrada")
    solicitud.estado = "atendida"
    db.commit()
    return {"solicitud_id": solicitud.id, "estado": solicitud.estado, "mensaje": "Alerta marcada como atendida"}

# ==========================================
# 4. HU-03 y HU-08: Sesiones Remotas e Historial
# ==========================================
@app.post("/sesiones/solicitar/")
def solicitar_sesion(sesion: schemas.SesionRemotaCreate, db: Session = Depends(get_db)):
    vinculo = db.query(models.VinculoModel).filter(models.VinculoModel.id == sesion.vinculo_id).first()
    if not vinculo:
        raise HTTPException(status_code=404, detail="Vínculo no encontrado")

    adulto = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == vinculo.adulto_id).first()
    if adulto and adulto.conectado == 0:
        raise HTTPException(
            status_code=409,
            detail=f"{adulto.nombre} salió de su cuenta. No puede recibir solicitudes hasta que vuelva a entrar."
        )

    pendiente_existente = (
        db.query(models.SesionRemotaModel)
        .filter(
            models.SesionRemotaModel.vinculo_id == sesion.vinculo_id,
            models.SesionRemotaModel.estado == "pendiente_consentimiento"
        )
        .first()
    )
    if pendiente_existente:
        raise HTTPException(
            status_code=409,
            detail="Ya hay una solicitud pendiente de respuesta para este vínculo."
        )
    
    nueva_sesion = models.SesionRemotaModel(
        vinculo_id=sesion.vinculo_id,
        estado="pendiente_consentimiento",
        fecha_inicio=datetime.datetime.utcnow()
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
    if sesion.estado != "pendiente_consentimiento":
        raise HTTPException(status_code=409, detail=f"La solicitud ya fue respondida (estado: {sesion.estado})")
    
    if aceptar:
        sesion.estado = "activa"
        sesion.fecha_inicio = datetime.datetime.utcnow()
        mensaje = "Sesión aceptada. Conexión de pantalla iniciada."
    else:
        cerrar_registro_sesion(sesion, "rechazada", "adulto_mayor")
        mensaje = "Sesión rechazada por el adulto mayor."
    
    db.commit()
    return {"sesion_id": sesion.id, "estado": sesion.estado, "mensaje": mensaje}

@app.get("/sesiones/pendientes/{adulto_id}")
def sesiones_pendientes(adulto_id: int, db: Session = Depends(get_db)):
    filas = (
        db.query(models.SesionRemotaModel, models.UsuarioModel)
        .join(models.VinculoModel, models.SesionRemotaModel.vinculo_id == models.VinculoModel.id)
        .join(models.UsuarioModel, models.VinculoModel.familiar_id == models.UsuarioModel.id)
        .filter(models.VinculoModel.adulto_id == adulto_id)
        .filter(models.SesionRemotaModel.estado.in_(["pendiente_consentimiento", "activa"]))
        .order_by(models.SesionRemotaModel.id.desc())
        .all()
    )
    return [
        {"sesion_id": s.id, "vinculo_id": s.vinculo_id, "estado": s.estado, "familiar_nombre": f.nombre}
        for s, f in filas
    ]

@app.get("/sesiones/historial/")
def historial_sesiones(adulto_id: int = None, db: Session = Depends(get_db)):
    filas = db.query(models.SesionRemotaModel, models.VinculoModel).join(
        models.VinculoModel, models.SesionRemotaModel.vinculo_id == models.VinculoModel.id
    )
    if adulto_id is not None:
        filas = filas.filter(models.VinculoModel.adulto_id == adulto_id)
    
    registros = filas.order_by(models.SesionRemotaModel.id.desc()).limit(30).all()
    usuarios_map = {u.id: u.nombre for u in db.query(models.UsuarioModel).all()}

    resultado = []
    for s, v in registros:
        duracion = s.duracion_segundos
        if s.estado == "activa" and s.fecha_inicio:
            duracion = max(0, int((datetime.datetime.utcnow() - s.fecha_inicio).total_seconds()))
        resultado.append({
            "sesion_id": s.id,
            "vinculo_id": s.vinculo_id,
            "familiar_nombre": usuarios_map.get(v.familiar_id, f"ID {v.familiar_id}"),
            "adulto_nombre": usuarios_map.get(v.adulto_id, f"ID {v.adulto_id}"),
            "estado": s.estado,
            "fecha_inicio": s.fecha_inicio.isoformat() if s.fecha_inicio else None,
            "fecha_fin": s.fecha_fin.isoformat() if s.fecha_fin else None,
            "duracion_segundos": duracion,
            "cerrada_por": s.cerrada_por
        })
    return resultado

@app.get("/sesiones/{sesion_id}")
def obtener_sesion(sesion_id: int, db: Session = Depends(get_db)):
    sesion = db.query(models.SesionRemotaModel).filter(models.SesionRemotaModel.id == sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return {
        "sesion_id": sesion.id,
        "vinculo_id": sesion.vinculo_id,
        "estado": sesion.estado,
        "duracion_segundos": sesion.duracion_segundos,
        "cerrada_por": sesion.cerrada_por
    }

@app.put("/sesiones/{sesion_id}/finalizar/")
def finalizar_sesion(sesion_id: int, autor: str = "familiar", db: Session = Depends(get_db)):
    sesion = db.query(models.SesionRemotaModel).filter(models.SesionRemotaModel.id == sesion_id).first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if sesion.estado not in ("pendiente_consentimiento", "activa"):
        raise HTTPException(status_code=409, detail=f"La sesión ya está {sesion.estado}")
    
    cerrar_registro_sesion(sesion, "finalizada", autor)
    db.commit()
    return {
        "sesion_id": sesion.id,
        "estado": sesion.estado,
        "duracion_segundos": sesion.duracion_segundos,
        "cerrada_por": sesion.cerrada_por,
        "mensaje": "Sesión finalizada."
    }

# ==========================================
# 5. HU-06 (SCRUM-35): Geolocalización bajo Demanda
# ==========================================
@app.post("/ubicaciones/solicitar/")
def solicitar_ubicacion(req: schemas.UbicacionCreate, db: Session = Depends(get_db)):
    vinculo = db.query(models.VinculoModel).filter(models.VinculoModel.id == req.vinculo_id).first()
    if not vinculo:
        raise HTTPException(status_code=404, detail="Vínculo no encontrado")

    adulto = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == vinculo.adulto_id).first()
    if adulto and adulto.conectado == 0:
        raise HTTPException(
            status_code=409,
            detail=f"{adulto.nombre} salió de su cuenta y no puede recibir solicitudes de ubicación."
        )

    pendiente = (
        db.query(models.UbicacionModel)
        .filter(
            models.UbicacionModel.vinculo_id == req.vinculo_id,
            models.UbicacionModel.estado == "pendiente_consentimiento"
        )
        .first()
    )
    if pendiente:
        raise HTTPException(status_code=409, detail="Ya hay una solicitud de ubicación esperando respuesta.")

    nueva_ubi = models.UbicacionModel(
        vinculo_id=req.vinculo_id,
        estado="pendiente_consentimiento",
        fecha_solicitud=datetime.datetime.utcnow()
    )
    db.add(nueva_ubi)
    db.commit()
    db.refresh(nueva_ubi)
    return {
        "mensaje": "Solicitud de ubicación enviada al adulto mayor.",
        "ubicacion_id": nueva_ubi.id,
        "estado": nueva_ubi.estado
    }

@app.get("/ubicaciones/pendientes/{adulto_id}")
def ubicaciones_pendientes(adulto_id: int, db: Session = Depends(get_db)):
    filas = (
        db.query(models.UbicacionModel, models.UsuarioModel)
        .join(models.VinculoModel, models.UbicacionModel.vinculo_id == models.VinculoModel.id)
        .join(models.UsuarioModel, models.VinculoModel.familiar_id == models.UsuarioModel.id)
        .filter(models.VinculoModel.adulto_id == adulto_id)
        .filter(models.UbicacionModel.estado == "pendiente_consentimiento")
        .order_by(models.UbicacionModel.id.desc())
        .all()
    )
    return [
        {
            "ubicacion_id": u.id,
            "vinculo_id": u.vinculo_id,
            "estado": u.estado,
            "familiar_nombre": f.nombre
        }
        for u, f in filas
    ]

@app.put("/ubicaciones/{ubicacion_id}/responder/")
def responder_ubicacion(ubicacion_id: int, resp: schemas.UbicacionResponder, db: Session = Depends(get_db)):
    ubi = db.query(models.UbicacionModel).filter(models.UbicacionModel.id == ubicacion_id).first()
    if not ubi:
        raise HTTPException(status_code=404, detail="Solicitud de ubicación no encontrada")
    if ubi.estado != "pendiente_consentimiento":
        raise HTTPException(status_code=409, detail=f"La solicitud ya fue respondida ({ubi.estado})")

    ubi.fecha_respuesta = datetime.datetime.utcnow()
    if resp.aceptar:
        ubi.estado = "compartida"
        ubi.latitud = resp.latitud if resp.latitud is not None else -32.8895
        ubi.longitud = resp.longitud if resp.longitud is not None else -68.8458
        mensaje = "Ubicación compartida con éxito."
    else:
        ubi.estado = "rechazada"
        mensaje = "Solicitud de ubicación rechazada."

    db.commit()
    return {
        "ubicacion_id": ubi.id,
        "estado": ubi.estado,
        "latitud": ubi.latitud,
        "longitud": ubi.longitud,
        "mensaje": mensaje
    }

@app.get("/ubicaciones/{ubicacion_id}")
def obtener_ubicacion(ubicacion_id: int, db: Session = Depends(get_db)):
    ubi = db.query(models.UbicacionModel).filter(models.UbicacionModel.id == ubicacion_id).first()
    if not ubi:
        raise HTTPException(status_code=404, detail="Solicitud de ubicación no encontrada")
    vinculo = db.query(models.VinculoModel).filter(models.VinculoModel.id == ubi.vinculo_id).first()
    adulto = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == vinculo.adulto_id).first() if vinculo else None
    return {
        "ubicacion_id": ubi.id,
        "vinculo_id": ubi.vinculo_id,
        "estado": ubi.estado,
        "latitud": ubi.latitud,
        "longitud": ubi.longitud,
        "adulto_nombre": adulto.nombre if adulto else "Adulto Mayor",
        "fecha_respuesta": ubi.fecha_respuesta.isoformat() if ubi.fecha_respuesta else None
    }

@app.put("/ubicaciones/{ubicacion_id}/finalizar/")
def finalizar_ubicacion(ubicacion_id: int, db: Session = Depends(get_db)):
    ubi = db.query(models.UbicacionModel).filter(models.UbicacionModel.id == ubicacion_id).first()
    if not ubi:
        raise HTTPException(status_code=404, detail="Solicitud de ubicación no encontrada")
    if ubi.estado not in ("pendiente_consentimiento", "compartida"):
        raise HTTPException(status_code=409, detail=f"La ubicación ya está {ubi.estado}")
    ubi.estado = "finalizada"
    ubi.fecha_respuesta = datetime.datetime.utcnow()
    db.commit()
    return {"ubicacion_id": ubi.id, "estado": ubi.estado, "mensaje": "Visualización de ubicación finalizada."}

# ==========================================
# 6. Grupos Familiares (Token 6 dígitos + Admin)
# ==========================================
@app.post("/grupos/")
def crear_grupo_familiar(req: schemas.GrupoCrearRequest, db: Session = Depends(get_db)):
    adulto = db.query(models.UsuarioModel).filter(
        models.UsuarioModel.id == req.adulto_id,
        models.UsuarioModel.rol == "adulto_mayor"
    ).first()
    if not adulto:
        raise HTTPException(status_code=404, detail="Adulto mayor no encontrado")

    grupo_existente = db.query(models.GrupoFamiliarModel).filter(
        models.GrupoFamiliarModel.adulto_id == adulto.id
    ).first()
    if grupo_existente:
        return {
            "grupo_id": grupo_existente.id,
            "nombre": grupo_existente.nombre,
            "adulto_id": grupo_existente.adulto_id,
            "codigo_token": grupo_existente.codigo_token,
            "mensaje": "El adulto mayor ya tenía un grupo familiar creado"
        }

    token = generar_token_6_digitos(db)
    grupo = models.GrupoFamiliarModel(
        nombre=req.nombre or f"Grupo de {adulto.nombre}",
        adulto_id=adulto.id,
        codigo_token=token,
        creado_por_familiar_id=req.familiar_admin_id
    )
    db.add(grupo)
    db.commit()
    db.refresh(grupo)

    if req.familiar_admin_id:
        familiar = db.query(models.UsuarioModel).filter(
            models.UsuarioModel.id == req.familiar_admin_id,
            models.UsuarioModel.rol == "familiar"
        ).first()
        if familiar:
            db.add(models.MiembroGrupoModel(
                grupo_id=grupo.id,
                familiar_id=familiar.id,
                rol_grupo="admin",
                estado="aprobado"
            ))
            vinculo = db.query(models.VinculoModel).filter(
                models.VinculoModel.familiar_id == familiar.id,
                models.VinculoModel.adulto_id == adulto.id
            ).first()
            if not vinculo:
                db.add(models.VinculoModel(
                    familiar_id=familiar.id,
                    adulto_id=adulto.id,
                    codigo_qr=str(uuid.uuid4())
                ))
            db.commit()

    return {
        "grupo_id": grupo.id,
        "nombre": grupo.nombre,
        "adulto_id": grupo.adulto_id,
        "codigo_token": grupo.codigo_token,
        "mensaje": "Grupo familiar creado con éxito"
    }

@app.post("/grupos/unirse/")
def unirse_a_grupo(req: schemas.UnirseGrupoRequest, db: Session = Depends(get_db)):
    familiar = db.query(models.UsuarioModel).filter(
        models.UsuarioModel.id == req.familiar_id,
        models.UsuarioModel.rol == "familiar"
    ).first()
    if not familiar:
        raise HTTPException(status_code=404, detail="Familiar no encontrado")

    grupo = db.query(models.GrupoFamiliarModel).filter(
        models.GrupoFamiliarModel.codigo_token == req.codigo_token.strip()
    ).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Token de grupo inválido")

    existente = db.query(models.MiembroGrupoModel).filter(
        models.MiembroGrupoModel.grupo_id == grupo.id,
        models.MiembroGrupoModel.familiar_id == familiar.id
    ).first()
    if existente:
        return {
            "miembro_id": existente.id,
            "grupo_id": grupo.id,
            "estado": existente.estado,
            "rol_grupo": existente.rol_grupo,
            "mensaje": f"Ya existe una solicitud en el grupo con estado: {existente.estado}"
        }

    hay_admin = db.query(models.MiembroGrupoModel).filter(
        models.MiembroGrupoModel.grupo_id == grupo.id,
        models.MiembroGrupoModel.rol_grupo == "admin",
        models.MiembroGrupoModel.estado == "aprobado"
    ).first()

    rol_asignado = "admin" if not hay_admin else "miembro"
    estado_asignado = "aprobado" if not hay_admin else "pendiente"

    miembro = models.MiembroGrupoModel(
        grupo_id=grupo.id,
        familiar_id=familiar.id,
        rol_grupo=rol_asignado,
        estado=estado_asignado
    )
    db.add(miembro)
    db.commit()
    db.refresh(miembro)

    if estado_asignado == "aprobado":
        vinculo = db.query(models.VinculoModel).filter(
            models.VinculoModel.familiar_id == familiar.id,
            models.VinculoModel.adulto_id == grupo.adulto_id
        ).first()
        if not vinculo:
            db.add(models.VinculoModel(
                familiar_id=familiar.id,
                adulto_id=grupo.adulto_id,
                codigo_qr=str(uuid.uuid4())
            ))
            db.commit()

    return {
        "miembro_id": miembro.id,
        "grupo_id": grupo.id,
        "codigo_token": grupo.codigo_token,
        "rol_grupo": miembro.rol_grupo,
        "estado": miembro.estado,
        "mensaje": "Ingresaste como administrador del grupo" if estado_asignado == "aprobado" else "Solicitud enviada. Esperando aprobación del familiar administrador"
    }

@app.get("/grupos/{grupo_id}/miembros/")
def listar_miembros_grupo(grupo_id: int, db: Session = Depends(get_db)):
    grupo = db.query(models.GrupoFamiliarModel).filter(models.GrupoFamiliarModel.id == grupo_id).first()
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")

    miembros = db.query(models.MiembroGrupoModel).filter(
        models.MiembroGrupoModel.grupo_id == grupo_id
    ).all()

    salida = []
    for m in miembros:
        fam = db.query(models.UsuarioModel).filter(models.UsuarioModel.id == m.familiar_id).first()
        salida.append({
            "miembro_id": m.id,
            "familiar_id": m.familiar_id,
            "familiar_nombre": fam.nombre if fam else "Familiar",
            "familiar_email": fam.email if fam else "",
            "rol_grupo": m.rol_grupo,
            "estado": m.estado
        })
    return {
        "grupo_id": grupo.id,
        "nombre": grupo.nombre,
        "adulto_id": grupo.adulto_id,
        "codigo_token": grupo.codigo_token,
        "miembros": salida
    }

@app.put("/grupos/miembros/{miembro_id}/decidir/")
def decidir_miembro_grupo(miembro_id: int, req: schemas.DecidirMiembroRequest, db: Session = Depends(get_db)):
    miembro = db.query(models.MiembroGrupoModel).filter(models.MiembroGrupoModel.id == miembro_id).first()
    if not miembro:
        raise HTTPException(status_code=404, detail="Solicitud de miembro no encontrada")

    admin = db.query(models.MiembroGrupoModel).filter(
        models.MiembroGrupoModel.grupo_id == miembro.grupo_id,
        models.MiembroGrupoModel.familiar_id == req.admin_familiar_id,
        models.MiembroGrupoModel.rol_grupo == "admin",
        models.MiembroGrupoModel.estado == "aprobado"
    ).first()
    if not admin:
        raise HTTPException(status_code=403, detail="Solo un familiar administrador aprobado puede aprobar o rechazar miembros")

    if req.aprobar:
        miembro.estado = "aprobado"
        grupo = db.query(models.GrupoFamiliarModel).filter(models.GrupoFamiliarModel.id == miembro.grupo_id).first()
        if grupo:
            vinculo = db.query(models.VinculoModel).filter(
                models.VinculoModel.familiar_id == miembro.familiar_id,
                models.VinculoModel.adulto_id == grupo.adulto_id
            ).first()
            if not vinculo:
                db.add(models.VinculoModel(
                    familiar_id=miembro.familiar_id,
                    adulto_id=grupo.adulto_id,
                    codigo_qr=str(uuid.uuid4())
                ))
    else:
        miembro.estado = "rechazado"

    db.commit()
    db.refresh(miembro)
    return {
        "miembro_id": miembro.id,
        "familiar_id": miembro.familiar_id,
        "estado": miembro.estado,
        "mensaje": "Miembro aprobado y vinculado al grupo" if req.aprobar else "Solicitud de ingreso rechazada"
    }

# Archivos estáticos del Panel y de la App Móvil
BASE_DIR = Path(__file__).parent

@app.get("/panel", include_in_schema=False)
def panel():
    return FileResponse(BASE_DIR / "index.html")

@app.get("/panel.css", include_in_schema=False)
def panel_css():
    return FileResponse(BASE_DIR / "panel.css")

app.mount("/mobile", StaticFiles(directory=BASE_DIR / "mobile", html=True), name="mobile")