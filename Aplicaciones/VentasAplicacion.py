"""Casos de uso de ventas: registrar, cobrar (descuenta stock) y anular.

Las funciones reciben el Usuario de la sesión porque un vendedor solo ve y opera sus ventas.
"""

import secrets

from pymysql import IntegrityError, MySQLError

from Aplicaciones import InventarioAplicacion, Permisos
from Aplicaciones.Errores import OperacionRechazada, RegistroNoEncontrado, es_error_de_rutina
from Aplicaciones.Importes import calcular, leer_lineas
from Repositorios import CatalogosRepositorio, InventarioRepositorio, VentasRepositorio
from Repositorios.BaseDatos import transaccion


# Documento del cliente genérico creado por BD/actualizacion_modulos.sql.
DOCUMENTO_CONSUMIDOR_FINAL = "222222222222"


def _filtro_usuario(usuario):
    """Devuelve el id del usuario si es vendedor (solo ve sus ventas); si no, None (ve todas)."""
    return usuario.id_usuario if Permisos.solo_sus_ventas(usuario.rol) else None


def _verificar_acceso(id_usuario_venta, usuario):
    """Lanza RegistroNoEncontrado si un vendedor intenta usar una venta de otro usuario."""
    # Para un vendedor, las ventas de otros usuarios no existen.
    if Permisos.solo_sus_ventas(usuario.rol) and id_usuario_venta != usuario.id_usuario:
        raise RegistroNoEncontrado


def listar(usuario):
    """Devuelve las ventas que el usuario puede ver (lista de Venta)."""
    return VentasRepositorio.listar(_filtro_usuario(usuario))


def obtener(id_venta, usuario):
    """Devuelve una tupla (Venta, lista de LineaDocumento). Lanza RegistroNoEncontrado."""
    venta = VentasRepositorio.obtener(id_venta)
    if venta is None:
        raise RegistroNoEncontrado
    _verificar_acceso(venta.id_usuario, usuario)
    return venta, VentasRepositorio.lineas(id_venta)


def datos_formulario():
    """Devuelve las listas del formulario de ventas y el id del cliente «Consumidor final»."""
    return {
        "clientes": CatalogosRepositorio.clientes_activos(),
        "id_consumidor_final": CatalogosRepositorio.id_cliente_por_documento(DOCUMENTO_CONSUMIDOR_FINAL),
        "sucursales": CatalogosRepositorio.sucursales(),
        "metodos_pago": CatalogosRepositorio.metodos_pago_activos(),
        "productos": CatalogosRepositorio.productos_activos(),
    }


def registrar(formulario, usuario):
    """Guarda la venta como PENDIENTE. No descuenta ni reserva stock.

    Recibe el formulario (cliente, sucursal, método de pago y filas de productos) y el Usuario.
    Devuelve una tupla (id de la venta, número de factura). Lanza ValueError u OperacionRechazada.
    """
    try:
        id_cliente = int(formulario.get("id_cliente", ""))
        id_sucursal = int(formulario.get("id_sucursal", ""))
        id_metodo_pago = int(formulario.get("id_metodo_pago", ""))
    except ValueError as error:
        raise ValueError("Selecciona el cliente, la sucursal y el método de pago.") from error
    productos = {fila["id_producto"]: fila for fila in CatalogosRepositorio.productos_activos()}
    # El precio aplicado es el del catálogo y queda guardado en el detalle.
    lineas = leer_lineas(formulario, productos, "precio_venta", precio_editable=False)
    importes = calcular(lineas)
    try:
        with transaccion() as cursor:
            if CatalogosRepositorio.estado(cursor, "clientes", id_cliente) != 1:
                raise OperacionRechazada("Selecciona un cliente activo.")
            if CatalogosRepositorio.estado(cursor, "sucursales", id_sucursal) != 1:
                raise OperacionRechazada("Selecciona una sucursal activa.")
            if CatalogosRepositorio.estado(cursor, "metodos_pago", id_metodo_pago) != 1:
                raise OperacionRechazada("Selecciona un método de pago activo.")
            # El número definitivo depende del id; mientras tanto se usa uno temporal único.
            id_venta = VentasRepositorio.insertar(
                cursor, id_cliente, usuario.id_usuario, id_sucursal, id_metodo_pago,
                f"TMP-{secrets.token_hex(8)}", importes,
            )
            numero_factura = VentasRepositorio.asignar_numero(cursor, id_venta)
            for linea in lineas:
                VentasRepositorio.insertar_linea(cursor, id_venta, linea)
    except IntegrityError as error:
        raise OperacionRechazada("No se pudo asignar el número de factura. Inténtalo de nuevo.") from error
    return id_venta, numero_factura


def cobrar(id_venta, usuario):
    """Pasa la venta a PAGADA una sola vez. Si falta stock en alguna línea, no cambia nada.

    Cada línea genera una salida en el kardex, todo en una transacción. No devuelve nada.
    Lanza RegistroNoEncontrado u OperacionRechazada (estado no PENDIENTE o stock insuficiente).
    """
    id_tipo = CatalogosRepositorio.id_tipo_movimiento("Venta")
    try:
        with transaccion() as cursor:
            venta = VentasRepositorio.bloquear(cursor, id_venta)
            if venta is None:
                raise RegistroNoEncontrado
            _verificar_acceso(venta["id_usuario"], usuario)
            if venta["estado"] != "PENDIENTE":
                raise OperacionRechazada(f"La venta está {venta['estado'].lower()}; no se puede cobrar.")
            lineas = VentasRepositorio.lineas_para_movimiento(cursor, id_venta)
            faltantes = []
            for linea in lineas:
                disponible = InventarioRepositorio.stock_bloqueado(
                    cursor, linea["id_producto"], venta["id_sucursal"]
                ) or 0
                if disponible < linea["cantidad"]:
                    faltantes.append(
                        f"{linea['producto']} (disponible {disponible}, requerido {linea['cantidad']})"
                    )
            if faltantes:
                raise OperacionRechazada(
                    "Stock insuficiente en la sucursal: " + "; ".join(faltantes)
                    + ". La venta sigue pendiente."
                )
            for linea in lineas:
                InventarioAplicacion.aplicar_movimiento(
                    cursor, linea["id_producto"], venta["id_sucursal"], id_tipo, usuario.id_usuario,
                    linea["cantidad"], venta["numero_factura"], f"Cobro de la venta {venta['numero_factura']}",
                )
            VentasRepositorio.fijar_estado(cursor, id_venta, "PAGADA")
    except MySQLError as error:
        if es_error_de_rutina(error):
            raise OperacionRechazada(error.args[1]) from error
        raise


def anular(id_venta, usuario):
    """Solo se anula una venta PENDIENTE; una PAGADA se conserva como historial.

    No devuelve nada. Lanza RegistroNoEncontrado u OperacionRechazada.
    """
    with transaccion() as cursor:
        venta = VentasRepositorio.bloquear(cursor, id_venta)
        if venta is None:
            raise RegistroNoEncontrado
        _verificar_acceso(venta["id_usuario"], usuario)
        if venta["estado"] != "PENDIENTE":
            raise OperacionRechazada(f"La venta está {venta['estado'].lower()}; no se puede anular.")
        VentasRepositorio.fijar_estado(cursor, id_venta, "ANULADA")
