"""Entidad Categoria: una fila de la tabla categorias."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Categoria:
    """Categoría de productos. estado es 1 (activa) o 0 (inactiva)."""

    nombre: str
    descripcion: str | None = None
    id_categoria: int | None = None
    estado: int = 1
