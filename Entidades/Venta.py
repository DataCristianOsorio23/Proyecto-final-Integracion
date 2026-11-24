"""Entidad Venta: encabezado de una venta con los nombres de cliente, sucursal, método y vendedor."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Venta:
    """Encabezado de una venta. estado es PENDIENTE, PAGADA o ANULADA; descuento es la suma
    informativa de los descuentos de las líneas (ya restada en subtotal)."""

    id_venta: int
    numero_factura: str
    fecha_venta: datetime
    cliente: str
    sucursal: str
    metodo_pago: str
    id_usuario: int
    usuario: str
    subtotal: Decimal
    descuento: Decimal
    impuesto: Decimal
    total: Decimal
    estado: str
