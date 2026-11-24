"""Casos de uso de compras: registrar, recibir (suma stock) y anular."""

from pymysql import MySQLError

from Aplicaciones import InventarioAplicacion
from Aplicaciones.Errores import OperacionRechazada, RegistroNoEncontrado, es_error_de_rutina
from Aplicaciones.Importes import calcular, leer_lineas
from Repositorios import CatalogosRepositorio, ComprasRepositorio
from Repositorios.BaseDatos import transaccion


def listar():
    """Devuelve todas las compras (lista de Compra)."""
    return ComprasRepositorio.listar()


def obtener(id_compra):
    """Devuelve una tupla (Compra, lista de LineaDocumento). Lanza RegistroNoEncontrado."""
    compra = ComprasRepositorio.obtener(id_compra)
    if compra is None:
        raise RegistroNoEncontrado
    return compra, ComprasRepositorio.lineas(id_compra)


def datos_formulario():
    """Devuelve las listas del formulario de compras: proveedores, sucursales y productos activos."""
    return {
        "proveedores": CatalogosRepositorio.proveedores_activos(),
        "sucursales": CatalogosRepositorio.sucursales(),
        "productos": CatalogosRepositorio.productos_activos(),
    }


def registrar(formulario, id_usuario):
    """Guarda la compra como REGISTRADA. Todavía no cambia el inventario.

    Recibe el formulario (proveedor, sucursal, número de factura y filas de productos) y el id
    del usuario. Devuelve el id de la compra. Lanza ValueError u OperacionRechazada.
    """
    try:
        id_proveedor = int(formulario.get("id_proveedor", ""))
        id_sucursal = int(formulario.get("id_sucursal", ""))
    except ValueError as error:
        raise ValueError("Selecciona el proveedor y la sucursal.") from error
    numero_factura = formulario.get("numero_factura", "").strip()
    if not numero_factura or len(numero_factura) > 50:
        raise ValueError("El número de factura debe tener entre 1 y 50 caracteres.")
    productos = {fila["id_producto"]: fila for fila in CatalogosRepositorio.productos_activos()}
    lineas = leer_lineas(formulario, productos, "precio_compra", precio_editable=True)
    importes = calcular(lineas)
    with transaccion() as cursor:
        # Bloquear el proveedor evita registrar dos veces su misma factura al mismo tiempo.
        if CatalogosRepositorio.estado(cursor, "proveedores", id_proveedor, bloquear=True) != 1:
            raise OperacionRechazada("Selecciona un proveedor activo.")
        if CatalogosRepositorio.estado(cursor, "sucursales", id_sucursal) != 1:
            raise OperacionRechazada("Selecciona una sucursal activa.")
        if ComprasRepositorio.existe_factura(cursor, id_proveedor, numero_factura):
            raise OperacionRechazada("Ese proveedor ya tiene una compra con ese número de factura.")
        id_compra = ComprasRepositorio.insertar(
            cursor, id_proveedor, id_usuario, id_sucursal, numero_factura, importes
        )
        for linea in lineas:
            ComprasRepositorio.insertar_linea(cursor, id_compra, linea)
    return id_compra


def recibir(id_compra, id_usuario):
    """Pasa la compra a RECIBIDA una sola vez: cada línea genera una entrada en el kardex.

    Todo ocurre en una transacción. No devuelve nada. Lanza RegistroNoEncontrado u
    OperacionRechazada si la compra no está REGISTRADA o una rutina rechaza un movimiento.
    """
    id_tipo = CatalogosRepositorio.id_tipo_movimiento("Compra")
    try:
        with transaccion() as cursor:
            compra = ComprasRepositorio.bloquear(cursor, id_compra)
            if compra is None:
                raise RegistroNoEncontrado
            if compra["estado"] != "REGISTRADA":
                raise OperacionRechazada(f"La compra está {compra['estado'].lower()}; no se puede recibir.")
            for linea in ComprasRepositorio.lineas_para_movimiento(cursor, id_compra):
                InventarioAplicacion.aplicar_movimiento(
                    cursor, linea["id_producto"], compra["id_sucursal"], id_tipo, id_usuario,
                    linea["cantidad"], compra["numero_factura"], f"Recepción de la compra {id_compra}",
                )
            ComprasRepositorio.fijar_estado(cursor, id_compra, "RECIBIDA")
    except MySQLError as error:
        if es_error_de_rutina(error):
            raise OperacionRechazada(error.args[1]) from error
        raise


def anular(id_compra):
    """Solo se anula una compra REGISTRADA; una RECIBIDA ya cambió el inventario.

    No devuelve nada. Lanza RegistroNoEncontrado u OperacionRechazada.
    """
    with transaccion() as cursor:
        compra = ComprasRepositorio.bloquear(cursor, id_compra)
        if compra is None:
            raise RegistroNoEncontrado
        if compra["estado"] != "REGISTRADA":
            raise OperacionRechazada(f"La compra está {compra['estado'].lower()}; no se puede anular.")
        ComprasRepositorio.fijar_estado(cursor, id_compra, "ANULADA")
