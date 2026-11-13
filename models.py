from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from database import Base
import datetime

class UsuarioModel(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    rol = Column(String, nullable=False)  # "adulto_mayor" o "familiar"
    conectado = Column(Integer, default=1)  # 1 = activo, 0 = cerró sesión (D-02)

class DispositivoModel(Base):
    __tablename__ = "dispositivos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    tipo = Column(String, nullable=False)  # "movil" o "escritorio"
    token_acceso = Column(String, unique=True, nullable=False)

class VinculoModel(Base):
    __tablename__ = "vinculos"

    id = Column(Integer, primary_key=True, index=True)
    familiar_id = Column(Integer, ForeignKey("usuarios.id"))
    adulto_id = Column(Integer, ForeignKey("usuarios.id"))
    codigo_qr = Column(String, unique=True, nullable=False)
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

class SolicitudModel(Base):
    __tablename__ = "solicitudes"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    estado = Column(String, nullable=False)  # "pendiente", "atendida"
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

class SesionRemotaModel(Base):
    __tablename__ = "sesiones_remotas"

    id = Column(Integer, primary_key=True, index=True)
    vinculo_id = Column(Integer, ForeignKey("vinculos.id"))
    estado = Column(String, nullable=False)  # "pendiente_consentimiento", "activa", "rechazada", "finalizada"
    fecha_inicio = Column(DateTime, default=datetime.datetime.utcnow)
    fecha_fin = Column(DateTime, nullable=True)
    duracion_segundos = Column(Integer, nullable=True)
    cerrada_por = Column(String, nullable=True)  # "adulto_mayor", "familiar", "salida"

class UbicacionModel(Base):
    __tablename__ = "ubicaciones"

    id = Column(Integer, primary_key=True, index=True)
    vinculo_id = Column(Integer, ForeignKey("vinculos.id"))
    estado = Column(String, nullable=False)  # "pendiente_consentimiento", "compartida", "rechazada"
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    fecha_solicitud = Column(DateTime, default=datetime.datetime.utcnow)
    fecha_respuesta = Column(DateTime, nullable=True)