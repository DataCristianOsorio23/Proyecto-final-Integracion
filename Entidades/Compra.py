"""Entidad Compra: encabezado de una compra con los nombres de proveedor, sucursal y usuario."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Compra:
    """Encabezado de una compra. estado es REGISTRADA, RECIBIDA o ANULADA."""

    id_compra: int
    numero_factura: str
    fecha_compra: datetime
    proveedor: str
    sucursal: str
    usuario: str
    subtotal: Decimal
    impuesto: Decimal
    total: Decimal
    estado: str
