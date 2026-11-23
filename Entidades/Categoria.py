from dataclasses import dataclass


@dataclass(frozen=True)
class Categoria:
    nombre: str
    descripcion: str | None = None
    id_categoria: int | None = None
    estado: int = 1
