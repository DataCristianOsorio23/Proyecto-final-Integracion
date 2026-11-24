"""Entidad Existencia: una fila de la vista vw_inventario_general."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Existencia:
    """Saldo de un producto en una sucursal. estado_inventario es AGOTADO, STOCK BAJO,
    SOBRESTOCK o NORMAL."""

    producto: str
    categoria: str
    sucursal: str
    stock_actual: int
    stock_minimo: int
    stock_maximo: int
    estado_inventario: str
