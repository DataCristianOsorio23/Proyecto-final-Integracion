"""Entidad Usuario: el usuario que inició sesión."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Usuario:
    """Usuario activo con el nombre de su rol. No incluye la contraseña."""

    id_usuario: int
    nombre: str
    apellido: str
    correo: str
    rol: str
