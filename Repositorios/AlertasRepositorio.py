"""Consultas SQL de alertas_inventario.

Las funciones que reciben cursor trabajan dentro de la transacción del llamador y no confirman.
"""

from Entidades.Alerta import Alerta
from Repositorios.BaseDatos import consultar


def sincronizar(cursor, id_producto=None, id_sucursal=None):
    """Abre o cierra alertas según el saldo actual. NULL significa «todos».

    Llama a sp_sincronizar_alertas. No devuelve nada.
    """
    cursor.execute("CALL sp_sincronizar_alertas(%s, %s)", (id_producto, id_sucursal))


def listar(estado=None):
    """Devuelve las alertas (lista de Alerta), de la más reciente a la más antigua.

    estado puede ser PENDIENTE, ATENDIDA o None para todas.
    """
    filas = consultar(
        "SELECT a.id_alerta, p.nombre AS producto, s.nombre AS sucursal, a.tipo_alerta, "
        "a.mensaje, a.fecha_alerta, a.estado, i.stock_actual, i.stock_minimo, i.stock_maximo "
        "FROM alertas_inventario a "
        "JOIN productos p ON p.id_producto = a.id_producto "
        "JOIN sucursales s ON s.id_sucursal = a.id_sucursal "
        "LEFT JOIN inventario i ON i.id_producto = a.id_producto AND i.id_sucursal = a.id_sucursal "
        "WHERE (%s IS NULL OR a.estado = %s) "
        "ORDER BY a.fecha_alerta DESC, a.id_alerta DESC",
        (estado, estado),
    )
    return [Alerta(**fila) for fila in filas]


def estado_bloqueado(cursor, id_alerta):
    """Bloquea la alerta y devuelve su estado (PENDIENTE o ATENDIDA), o None si no existe."""
    cursor.execute(
        "SELECT estado FROM alertas_inventario WHERE id_alerta = %s FOR UPDATE",
        (id_alerta,),
    )
    fila = cursor.fetchone()
    return fila["estado"] if fila else None


def marcar_atendida(cursor, id_alerta):
    """Cambia el estado de la alerta a ATENDIDA."""
    cursor.execute(
        "UPDATE alertas_inventario SET estado = 'ATENDIDA' WHERE id_alerta = %s",
        (id_alerta,),
    )
