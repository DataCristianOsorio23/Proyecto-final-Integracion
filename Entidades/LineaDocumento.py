"""Entidad LineaDocumento: una línea del detalle de una compra o de una venta."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LineaDocumento:
    """Línea del detalle de una compra o de una venta."""

    id_producto: int
    cantidad: int
    precio_unitario: Decimal
    descuento: Decimal = Decimal("0")
    producto: str | None = None
    # La base calcula el subtotal de cada línea (columna generada).
    subtotal: Decimal | None = None
