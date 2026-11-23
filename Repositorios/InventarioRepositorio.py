from Entidades.Existencia import Existencia
from Repositorios.BaseDatos import consultar


def listar():
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
    """Registra el movimiento dentro de la transacción abierta por el llamador."""
    cursor.execute(
        "CALL sp_registrar_movimiento_inventario(%s, %s, %s, %s, %s, %s, %s)",
        (id_producto, id_sucursal, id_tipo_movimiento, id_usuario, cantidad, referencia, observacion),
    )
    return cursor.fetchone()


def consultar_kardex(id_producto=None, id_sucursal=None, desde=None, hasta_exclusivo=None):
    return consultar(
        "CALL sp_consultar_kardex(%s, %s, %s, %s)",
        (id_producto, id_sucursal, desde, hasta_exclusivo),
    )


def tiene_existencias(cursor, id_producto):
    cursor.execute(
        "SELECT COALESCE(SUM(stock_actual), 0) AS total FROM inventario WHERE id_producto = %s",
        (id_producto,),
    )
    return cursor.fetchone()["total"] > 0
