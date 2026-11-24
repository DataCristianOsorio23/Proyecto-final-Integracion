"""Consultas de los catálogos que se eligen en compras, ventas y ajustes.

Las listas se devuelven como diccionarios (filas de la consulta), no como entidades.
"""

from Repositorios.BaseDatos import consultar, consultar_uno


# Tablas que admiten la consulta de estado y su clave primaria.
_CLAVES = {
    "proveedores": "id_proveedor",
    "sucursales": "id_sucursal",
    "clientes": "id_cliente",
    "metodos_pago": "id_metodo_pago",
}


def sucursales(solo_activas=True):
    """Devuelve las sucursales (id_sucursal, nombre, estado); por defecto solo las activas."""
    filtro = "WHERE estado = 1 " if solo_activas else ""
    return consultar(f"SELECT id_sucursal, nombre, estado FROM sucursales {filtro}ORDER BY nombre")


def proveedores_activos():
    """Devuelve los proveedores activos (id_proveedor, nombre_empresa, nit)."""
    return consultar(
        "SELECT id_proveedor, nombre_empresa, nit FROM proveedores WHERE estado = 1 "
        "ORDER BY nombre_empresa"
    )


def clientes_activos():
    """Devuelve los clientes activos (id_cliente, nombre completo, tipo y número de documento)."""
    return consultar(
        "SELECT id_cliente, TRIM(CONCAT(nombre, ' ', COALESCE(apellido, ''))) AS nombre, "
        "tipo_documento, numero_documento FROM clientes WHERE estado = 1 ORDER BY nombre, apellido"
    )


def id_cliente_por_documento(numero_documento):
    """Devuelve el id del cliente activo con ese documento, o None."""
    fila = consultar_uno(
        "SELECT id_cliente FROM clientes WHERE numero_documento = %s AND estado = 1",
        (numero_documento,),
    )
    return fila["id_cliente"] if fila else None


def metodos_pago_activos():
    """Devuelve los métodos de pago activos (id_metodo_pago, nombre)."""
    return consultar(
        "SELECT id_metodo_pago, nombre FROM metodos_pago WHERE estado = 1 ORDER BY id_metodo_pago"
    )


def productos_activos():
    """Devuelve los productos activos (id_producto, codigo_barras, nombre, precio_compra, precio_venta)."""
    return consultar(
        "SELECT id_producto, codigo_barras, nombre, precio_compra, precio_venta "
        "FROM productos WHERE estado = 1 ORDER BY nombre"
    )


def tipos_movimiento(nombres):
    """Recibe una lista de nombres y devuelve esos tipos de movimiento activos
    (id_tipo_movimiento, nombre, tipo ENTRADA o SALIDA)."""
    marcadores = ", ".join(["%s"] * len(nombres))
    return consultar(
        "SELECT id_tipo_movimiento, nombre, tipo FROM tipos_movimiento "
        f"WHERE estado = 1 AND nombre IN ({marcadores}) ORDER BY id_tipo_movimiento",
        tuple(nombres),
    )


def id_tipo_movimiento(nombre):
    """Devuelve el id del tipo de movimiento activo con ese nombre (por ejemplo, "Compra"), o None."""
    fila = consultar_uno(
        "SELECT id_tipo_movimiento FROM tipos_movimiento WHERE nombre = %s AND estado = 1",
        (nombre,),
    )
    return fila["id_tipo_movimiento"] if fila else None


def estado(cursor, tabla, id_registro, bloquear=False):
    """Estado (1 o 0) de un registro, o None si no existe.

    tabla debe ser proveedores, sucursales, clientes o metodos_pago. Con bloquear=True usa
    FOR UPDATE; si no, un bloqueo compartido. Trabaja dentro de la transacción del llamador.
    """
    clave = _CLAVES[tabla]
    bloqueo = "FOR UPDATE" if bloquear else "LOCK IN SHARE MODE"
    cursor.execute(f"SELECT estado FROM {tabla} WHERE {clave} = %s {bloqueo}", (id_registro,))
    fila = cursor.fetchone()
    return fila["estado"] if fila else None
