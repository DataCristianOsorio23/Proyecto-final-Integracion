"""Consultas SQL de ventas y detalle_ventas.

Las funciones que reciben cursor trabajan dentro de la transacción del llamador y no confirman.
"""

from Entidades.LineaDocumento import LineaDocumento
from Entidades.Venta import Venta
from Repositorios.BaseDatos import consultar, consultar_uno


_CAMPOS = (
    "v.id_venta, v.numero_factura, v.fecha_venta, "
    "TRIM(CONCAT(c.nombre, ' ', COALESCE(c.apellido, ''))) AS cliente, "
    "s.nombre AS sucursal, mp.nombre AS metodo_pago, v.id_usuario, "
    "CONCAT(u.nombre, ' ', u.apellido) AS usuario, "
    "v.subtotal, v.descuento, v.impuesto, v.total, v.estado"
)
_ORIGEN = (
    "FROM ventas v "
    "JOIN clientes c ON c.id_cliente = v.id_cliente "
    "JOIN sucursales s ON s.id_sucursal = v.id_sucursal "
    "JOIN metodos_pago mp ON mp.id_metodo_pago = v.id_metodo_pago "
    "JOIN usuarios u ON u.id_usuario = v.id_usuario"
)


def listar(id_usuario=None):
    """Sin id_usuario devuelve todas las ventas; con él, solo las de ese usuario.

    Devuelve una lista de Venta, de la más reciente a la más antigua.
    """
    filas = consultar(
        f"SELECT {_CAMPOS} {_ORIGEN} WHERE (%s IS NULL OR v.id_usuario = %s) "
        "ORDER BY v.fecha_venta DESC, v.id_venta DESC",
        (id_usuario, id_usuario),
    )
    return [Venta(**fila) for fila in filas]


def obtener(id_venta):
    """Devuelve la Venta con ese id, o None si no existe."""
    fila = consultar_uno(f"SELECT {_CAMPOS} {_ORIGEN} WHERE v.id_venta = %s", (id_venta,))
    return Venta(**fila) if fila else None


def lineas(id_venta):
    """Devuelve las líneas de la venta (lista de LineaDocumento con nombre de producto y subtotal)."""
    filas = consultar(
        "SELECT d.id_producto, d.cantidad, d.precio_unitario, d.descuento, "
        "p.nombre AS producto, d.subtotal "
        "FROM detalle_ventas d JOIN productos p ON p.id_producto = d.id_producto "
        "WHERE d.id_venta = %s ORDER BY d.id_detalle_venta",
        (id_venta,),
    )
    return [LineaDocumento(**fila) for fila in filas]


def bloquear(cursor, id_venta):
    """Bloquea el encabezado para que la venta no se cobre ni anule dos veces.

    Devuelve un diccionario con id_venta, numero_factura, id_sucursal, id_usuario y estado, o None.
    """
    cursor.execute(
        "SELECT id_venta, numero_factura, id_sucursal, id_usuario, estado FROM ventas "
        "WHERE id_venta = %s FOR UPDATE",
        (id_venta,),
    )
    return cursor.fetchone()


def lineas_para_movimiento(cursor, id_venta):
    """Devuelve las líneas como diccionarios con id_producto, cantidad y producto (nombre),
    ordenadas por producto."""
    # El orden por producto mantiene el mismo orden de bloqueo en todas las operaciones.
    cursor.execute(
        "SELECT d.id_producto, d.cantidad, p.nombre AS producto "
        "FROM detalle_ventas d JOIN productos p ON p.id_producto = d.id_producto "
        "WHERE d.id_venta = %s ORDER BY d.id_producto",
        (id_venta,),
    )
    return cursor.fetchall()


def insertar(cursor, id_cliente, id_usuario, id_sucursal, id_metodo_pago, numero_temporal, importes):
    """Inserta el encabezado como PENDIENTE con un número de factura temporal.
    importes es el diccionario de Importes.calcular(). Devuelve el id de la venta nueva."""
    cursor.execute(
        "INSERT INTO ventas (id_cliente, id_usuario, id_sucursal, id_metodo_pago, numero_factura, "
        "subtotal, impuesto, descuento, total) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            id_cliente, id_usuario, id_sucursal, id_metodo_pago, numero_temporal,
            importes["subtotal"], importes["impuesto"], importes["descuento"], importes["total"],
        ),
    )
    return cursor.lastrowid


def asignar_numero(cursor, id_venta):
    """Sigue la numeración de los datos de ejemplo: la venta 1 es FV-10001.

    Reemplaza el número temporal y devuelve el número definitivo (texto).
    """
    cursor.execute(
        "UPDATE ventas SET numero_factura = CONCAT('FV-', 10000 + id_venta) WHERE id_venta = %s",
        (id_venta,),
    )
    cursor.execute("SELECT numero_factura FROM ventas WHERE id_venta = %s", (id_venta,))
    return cursor.fetchone()["numero_factura"]


def insertar_linea(cursor, id_venta, linea):
    """Inserta una LineaDocumento en detalle_ventas. La base calcula el subtotal."""
    cursor.execute(
        "INSERT INTO detalle_ventas (id_venta, id_producto, cantidad, precio_unitario, descuento) "
        "VALUES (%s, %s, %s, %s, %s)",
        (id_venta, linea.id_producto, linea.cantidad, linea.precio_unitario, linea.descuento),
    )


def fijar_estado(cursor, id_venta, estado):
    """Cambia el estado de la venta (PENDIENTE, PAGADA o ANULADA)."""
    cursor.execute("UPDATE ventas SET estado = %s WHERE id_venta = %s", (estado, id_venta))
