"""Consultas SQL de inventario y kardex.

Las funciones que reciben cursor trabajan dentro de la transacción del llamador y no confirman.
"""

from Entidades.Existencia import Existencia
from Repositorios.BaseDatos import consultar


def listar():
    """Devuelve el saldo de cada producto por sucursal (lista de Existencia) desde vw_inventario_general."""
    filas = consultar(
        "SELECT producto, categoria, sucursal, stock_actual, stock_minimo, "
        "stock_maximo, estado_inventario FROM vw_inventario_general "
        "ORDER BY sucursal, producto"
    )
    return [Existencia(**fila) for fila in filas]


def registrar_movimiento(
    cursor, id_producto, id_sucursal, id_tipo_movimiento, id_usuario, cantidad,
    referencia=None, observacion=None,
):
    """Registra el movimiento dentro de la transacción abierta por el llamador.

    Llama a sp_registrar_movimiento_inventario, que guarda el movimiento y actualiza el saldo.
    Devuelve un diccionario con id_movimiento, stock_anterior y stock_nuevo. Si la rutina rechaza
    el movimiento (por ejemplo, saldo negativo) lanza MySQLError con un código entre 30003 y 30009.
    """
    cursor.execute(
        "CALL sp_registrar_movimiento_inventario(%s, %s, %s, %s, %s, %s, %s)",
        (id_producto, id_sucursal, id_tipo_movimiento, id_usuario, cantidad, referencia, observacion),
    )
    return cursor.fetchone()


def consultar_kardex(id_producto=None, id_sucursal=None, desde=None, hasta_exclusivo=None):
    """Devuelve los movimientos del kardex (lista de diccionarios de vw_kardex), del más reciente
    al más antiguo. Cada filtro en None se omite; desde se incluye y hasta_exclusivo no."""
    return consultar(
        "CALL sp_consultar_kardex(%s, %s, %s, %s)",
        (id_producto, id_sucursal, desde, hasta_exclusivo),
    )


def stock_bloqueado(cursor, id_producto, id_sucursal):
    """Bloquea producto e inventario en el mismo orden que sp_registrar_movimiento_inventario.

    Devuelve el saldo actual del producto en la sucursal, o None si no tiene inventario allí.
    """
    cursor.execute("SELECT id_producto FROM productos WHERE id_producto = %s FOR UPDATE", (id_producto,))
    cursor.execute(
        "SELECT stock_actual FROM inventario WHERE id_producto = %s AND id_sucursal = %s FOR UPDATE",
        (id_producto, id_sucursal),
    )
    fila = cursor.fetchone()
    return fila["stock_actual"] if fila else None


def tiene_existencias(cursor, id_producto):
    """Devuelve True si el producto tiene saldo mayor que cero en alguna sucursal."""
    cursor.execute(
        "SELECT COALESCE(SUM(stock_actual), 0) AS total FROM inventario WHERE id_producto = %s",
        (id_producto,),
    )
    return cursor.fetchone()["total"] > 0
