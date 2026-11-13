from pydantic import BaseModel
from typing import Optional

class UsuarioCreate(BaseModel):
    nombre: str
    email: str
    rol: str  # "adulto_mayor" o "familiar"

class VinculoCreate(BaseModel):
    familiar_id: int
    adulto_id: int

class SolicitudCreate(BaseModel):
    usuario_id: int  # ID del adulto mayor que pide ayuda

class SesionRemotaCreate(BaseModel):
    vinculo_id: int
    estado: str = "pendiente"

class IngresoRequest(BaseModel):
    email: str

class UbicacionCreate(BaseModel):
    vinculo_id: int

class UbicacionResponder(BaseModel):
    aceptar: bool
    latitud: Optional[float] = None
    longitud: Optional[float] = None