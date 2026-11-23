from dataclasses import dataclass


@dataclass(frozen=True)
class Existencia:
    producto: str
    categoria: str
    sucursal: str
    stock_actual: int
    stock_minimo: int
    stock_maximo: int
    estado_inventario: str
