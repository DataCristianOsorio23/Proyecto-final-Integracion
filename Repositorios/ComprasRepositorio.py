"""Consultas SQL de compras y detalle_compras.

Las funciones que reciben cursor trabajan dentro de la transacción del llamador y no confirman.
"""

from Entidades.Compra import Compra
from Entidades.LineaDocumento import LineaDocumento
from Repositorios.BaseDatos import consultar, consultar_uno


_CAMPOS = (
    "c.id_compra, c.numero_factura, c.fecha_compra, pr.nombre_empresa AS proveedor, "
    "s.nombre AS sucursal, CONCAT(u.nombre, ' ', u.apellido) AS usuario, "
    "c.subtotal, c.impuesto, c.total, c.estado"
)
_ORIGEN = (
    "FROM compras c "
    "JOIN proveedores pr ON pr.id_proveedor = c.id_proveedor "
    "JOIN sucursales s ON s.id_sucursal = c.id_sucursal "
    "JOIN usuarios u ON u.id_usuario = c.id_usuario"
)


def listar():
    """Devuelve todas las compras (lista de Compra), de la más reciente a la más antigua."""
    filas = consultar(f"SELECT {_CAMPOS} {_ORIGEN} ORDER BY c.fecha_compra DESC, c.id_compra DESC")
    return [Compra(**fila) for fila in filas]


def obtener(id_compra):
    """Devuelve la Compra con ese id, o None si no existe."""
    fila = consultar_uno(f"SELECT {_CAMPOS} {_ORIGEN} WHERE c.id_compra = %s", (id_compra,))
    return Compra(**fila) if fila else None


def lineas(id_compra):
    """Devuelve las líneas de la compra (lista de LineaDocumento con nombre de producto y subtotal)."""
    filas = consultar(
        "SELECT d.id_producto, d.cantidad, d.precio_unitario, d.descuento, "
        "p.nombre AS producto, d.subtotal "
        "FROM detalle_compras d JOIN productos p ON p.id_producto = d.id_producto "
        "WHERE d.id_compra = %s ORDER BY d.id_detalle_compra",
        (id_compra,),
    )
    return [LineaDocumento(**fila) for fila in filas]


def bloquear(cursor, id_compra):
    """Bloquea el encabezado para que la compra no se reciba ni anule dos veces.

    Devuelve un diccionario con id_compra, numero_factura, id_sucursal y estado, o None.
    """
    cursor.execute(
        "SELECT id_compra, numero_factura, id_sucursal, estado FROM compras "
        "WHERE id_compra = %s FOR UPDATE",
        (id_compra,),
    )
    return cursor.fetchone()


def lineas_para_movimiento(cursor, id_compra):
    """Devuelve las líneas como diccionarios con id_producto y cantidad, ordenadas por producto."""
    # El orden por producto mantiene el mismo orden de bloqueo en todas las operaciones.
    cursor.execute(
        "SELECT id_producto, cantidad FROM detalle_compras WHERE id_compra = %s ORDER BY id_producto",
        (id_compra,),
    )
    return cursor.fetchall()


def existe_factura(cursor, id_proveedor, numero_factura):
    """Una compra anulada no ocupa el número de factura de su proveedor.

    Devuelve True si el proveedor ya tiene una compra no anulada con ese número.
    """
    cursor.execute(
        "SELECT 1 FROM compras WHERE id_proveedor = %s AND numero_factura = %s "
        "AND estado <> 'ANULADA' LIMIT 1",
        (id_proveedor, numero_factura),
    )
    return cursor.fetchone() is not None


def insertar(cursor, id_proveedor, id_usuario, id_sucursal, numero_factura, importes):
    """Inserta el encabezado como REGISTRADA. importes es el diccionario de Importes.calcular().
    Devuelve el id de la compra nueva."""
    cursor.execute(
        "INSERT INTO compras (id_proveedor, id_usuario, id_sucursal, numero_factura, "
        "subtotal, impuesto, total) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (
            id_proveedor, id_usuario, id_sucursal, numero_factura,
            importes["subtotal"], importes["impuesto"], importes["total"],
        ),
    )
    return cursor.lastrowid


def insertar_linea(cursor, id_compra, linea):
    """Inserta una LineaDocumento en detalle_compras. La base calcula el subtotal."""
    cursor.execute(
        "INSERT INTO detalle_compras (id_compra, id_producto, cantidad, precio_unitario, descuento) "
        "VALUES (%s, %s, %s, %s, %s)",
        (id_compra, linea.id_producto, linea.cantidad, linea.precio_unitario, linea.descuento),
    )


def fijar_estado(cursor, id_compra, estado):
    """Cambia el estado de la compra (REGISTRADA, RECIBIDA o ANULADA)."""
    cursor.execute("UPDATE compras SET estado = %s WHERE id_compra = %s", (estado, id_compra))
