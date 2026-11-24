"""Entidad Alerta: una fila de alertas_inventario con el saldo actual del inventario."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Alerta:
    """Alerta de un producto en una sucursal. tipo_alerta es PRODUCTO_AGOTADO, STOCK_BAJO o
    SOBRESTOCK; estado es PENDIENTE o ATENDIDA. Los campos stock_* son el saldo y los límites actuales."""

    id_alerta: int
    producto: str
    sucursal: str
    tipo_alerta: str
    mensaje: str
    fecha_alerta: datetime
    estado: str
    stock_actual: int | None = None
    stock_minimo: int | None = None
    stock_maximo: int | None = None
