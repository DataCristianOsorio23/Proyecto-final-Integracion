from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Producto:
    id_categoria: int
    codigo_barras: str
    nombre: str
    descripcion: str | None
    marca: str | None
    unidad_medida: str
    precio_compra: Decimal
    precio_venta: Decimal
    stock_minimo: int
    stock_maximo: int
    id_producto: int | None = None
    estado: int = 1
    categoria: str | None = None
