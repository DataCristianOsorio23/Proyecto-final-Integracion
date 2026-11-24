"""Casos de uso de inventario: consulta de saldos, movimientos con alertas, ajustes y kardex."""

from datetime import date, datetime, time, timedelta

from pymysql import MySQLError

from Aplicaciones.Errores import OperacionRechazada, es_error_de_rutina
from Repositorios import AlertasRepositorio, CatalogosRepositorio, InventarioRepositorio, ProductosRepositorio
from Repositorios.BaseDatos import transaccion


# Movimientos que se registran a mano. Compras y ventas generan los suyos.
TIPOS_AJUSTE = ("Ajuste positivo", "Ajuste negativo", "Producto averiado", "Producto vencido")


def listar():
    """Devuelve el saldo de cada producto por sucursal (lista de Existencia)."""
    return InventarioRepositorio.listar()


def aplicar_movimiento(cursor, id_producto, id_sucursal, id_tipo_movimiento, id_usuario,
                       cantidad, referencia, observacion):
    """Registra el movimiento en el kardex y actualiza las alertas en la misma transacción.

    Es el único camino para cambiar un saldo (ajustes, compras y ventas). Recibe el cursor de la
    transacción abierta. Devuelve un diccionario con id_movimiento, stock_anterior y stock_nuevo.
    """
    resultado = InventarioRepositorio.registrar_movimiento(
        cursor, id_producto, id_sucursal, id_tipo_movimiento, id_usuario,
        cantidad, referencia, observacion,
    )
    AlertasRepositorio.sincronizar(cursor, id_producto, id_sucursal)
    return resultado


# ---------- Ajustes ----------

def datos_ajuste():
    """Devuelve las listas del formulario de ajustes: productos, sucursales y tipos de ajuste."""
    return {
        "productos": CatalogosRepositorio.productos_activos(),
        "sucursales": CatalogosRepositorio.sucursales(),
        "tipos": CatalogosRepositorio.tipos_movimiento(TIPOS_AJUSTE),
    }


def registrar_ajuste(formulario, id_usuario):
    """Registra un ajuste manual con su justificación.

    Recibe el formulario (producto, sucursal, tipo, cantidad, observacion) y el id del usuario.
    Devuelve el diccionario de aplicar_movimiento. Lanza ValueError u OperacionRechazada.
    """
    try:
        id_producto = int(formulario.get("id_producto", ""))
        id_sucursal = int(formulario.get("id_sucursal", ""))
        id_tipo = int(formulario.get("id_tipo_movimiento", ""))
        cantidad = int(formulario.get("cantidad", ""))
    except ValueError as error:
        raise ValueError("Selecciona producto, sucursal y tipo, y escribe una cantidad entera.") from error
    if cantidad <= 0 or cantidad > 2_147_483_647:
        raise ValueError("La cantidad debe ser un entero mayor que cero.")
    justificacion = formulario.get("observacion", "").strip()
    if not justificacion or len(justificacion) > 300:
        raise ValueError("Escribe una justificación de máximo 300 caracteres.")
    if id_tipo not in {tipo["id_tipo_movimiento"] for tipo in CatalogosRepositorio.tipos_movimiento(TIPOS_AJUSTE)}:
        raise ValueError("Selecciona un tipo de ajuste válido.")
    try:
        with transaccion() as cursor:
            return aplicar_movimiento(
                cursor, id_producto, id_sucursal, id_tipo, id_usuario, cantidad, None, justificacion
            )
    except MySQLError as error:
        if es_error_de_rutina(error):
            raise OperacionRechazada(error.args[1]) from error
        raise


# ---------- Kardex ----------

def _entero_opcional(texto):
    """Convierte un filtro de texto en entero; vacío devuelve None. Lanza ValueError."""
    texto = (texto or "").strip()
    if not texto:
        return None
    try:
        return int(texto)
    except ValueError as error:
        raise ValueError("Selecciona un filtro válido.") from error


def _fecha_opcional(texto, nombre):
    """Convierte una fecha AAAA-MM-DD en date; vacío devuelve None. Lanza ValueError."""
    texto = (texto or "").strip()
    if not texto:
        return None
    try:
        return date.fromisoformat(texto)
    except ValueError as error:
        raise ValueError(f"La fecha {nombre} no es válida.") from error


def filtros_kardex():
    """Devuelve las listas de los filtros del kardex: todos los productos y todas las sucursales."""
    return {
        "productos": ProductosRepositorio.listar(),
        "sucursales": CatalogosRepositorio.sucursales(solo_activas=False),
    }


def consultar_kardex(filtros):
    """Consulta el kardex. La fecha final se incluye completa.

    Recibe los parámetros de la URL (id_producto, id_sucursal, desde, hasta), todos opcionales.
    Devuelve la lista de movimientos (diccionarios). Lanza ValueError si un filtro no es válido.
    """
    id_producto = _entero_opcional(filtros.get("id_producto"))
    id_sucursal = _entero_opcional(filtros.get("id_sucursal"))
    desde = _fecha_opcional(filtros.get("desde"), "inicial")
    hasta = _fecha_opcional(filtros.get("hasta"), "final")
    if desde and hasta and desde > hasta:
        raise ValueError("La fecha final no puede ser anterior a la inicial.")
    try:
        hasta_exclusivo = datetime.combine(hasta + timedelta(days=1), time.min) if hasta else None
    except OverflowError as error:
        raise ValueError("La fecha final no es válida.") from error
    desde_inicio = datetime.combine(desde, time.min) if desde else None
    try:
        return InventarioRepositorio.consultar_kardex(id_producto, id_sucursal, desde_inicio, hasta_exclusivo)
    except MySQLError as error:
        if es_error_de_rutina(error):
            raise OperacionRechazada(error.args[1]) from error
        raise
