from pydantic import BaseModel

class UsuarioCreate(BaseModel):
    nombre: str
    email: str
    rol: str # "adulto_mayor" o "familiar"

class VinculoCreate(BaseModel):
    familiar_id: int
    adulto_id: int


class SolicitudCreate(BaseModel):
    usuario_id: int # ID del adulto mayor que pide ayuda

class SesionRemotaCreate(BaseModel):
    vinculo_id: int
    estado: str = "pendiente" # pendiente, aceptada, rechazada, finalizada

class IngresoRequest(BaseModel):
    email: str
