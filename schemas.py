from pydantic import BaseModel
from typing import Optional


class UsuarioCreate(BaseModel):
    nombre: str
    email: str
    rol: str  # "adulto_mayor" o "familiar"


class VinculoCreate(BaseModel):
    familiar_id: int
    adulto_id: int
    solicitante_familiar_id: Optional[int] = None


class SolicitudCreate(BaseModel):
    usuario_id: int  # ID del adulto mayor que pide ayuda
    destino_familiar_id: Optional[int] = None  # None = todos los familiares del grupo


class AceptarAlertaRequest(BaseModel):
    familiar_id: int
    accion: str = "pantalla"  # "pantalla" o "ubicacion"


class SesionRemotaCreate(BaseModel):
    vinculo_id: int
    solicitante_familiar_id: Optional[int] = None
    estado: str = "pendiente"


class IngresoRequest(BaseModel):
    email: str


class UbicacionCreate(BaseModel):
    vinculo_id: int
    solicitante_familiar_id: Optional[int] = None


class UbicacionResponder(BaseModel):
    aceptar: bool
    latitud: Optional[float] = None
    longitud: Optional[float] = None


class GrupoCrearRequest(BaseModel):
    adulto_id: int
    familiar_admin_id: Optional[int] = None
    nombre: Optional[str] = None


class GrupoAgregarAdultoRequest(BaseModel):
    admin_familiar_id: int
    adulto_id: int


class UnirseGrupoRequest(BaseModel):
    familiar_id: int
    codigo_token: str


class DecidirMiembroRequest(BaseModel):
    admin_familiar_id: int
    aprobar: bool