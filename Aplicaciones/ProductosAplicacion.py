from decimal import Decimal, InvalidOperation

from pymysql import IntegrityError, MySQLError

from Aplicaciones.Errores import OperacionRechazada, RegistroNoEncontrado
from Entidades.Producto import Producto
from Repositorios import CategoriasRepositorio, InventarioRepositorio, ProductosRepositorio
from Repositorios.BaseDatos import transaccion


def listar():
    return ProductosRepositorio.listar()


def obtener(id_producto):
    producto = ProductosRepositorio.obtener(id_producto)
    if producto is None:
        raise RegistroNoEncontrado
    return producto


def leer_decimal(formulario, campo):
    """Lee un precio sin usar float, que puede introducir errores de redondeo."""
    try:
        valor = Decimal(formulario.get(campo, ""))
    except InvalidOperation as error:
        # «from error» conserva el error original para el registro técnico.
        raise ValueError(f"{campo.replace('_', ' ').capitalize()} debe ser un número.") from error
    # Decimal acepta textos como "NaN" o "Infinity"; is_finite() los rechaza.
    if not valor.is_finite() or valor < 0 or valor >= 10000000000:
        raise ValueError(f"{campo.replace('_', ' ').capitalize()} debe ser positivo y válido.")
    # El exponente de un Decimal dice cuántos decimales tiene: -2 son dos cifras.
    if valor.as_tuple().exponent < -2:
        raise ValueError(f"{campo.replace('_', ' ').capitalize()} admite máximo 2 decimales.")
    return valor


def leer_producto(formulario):
    """Lee el formulario y valida los campos del DDL actual."""
    datos = {
        "codigo_barras": formulario.get("codigo_barras", "").strip(),
        "nombre": formulario.get("nombre", "").strip(),
        "descripcion": formulario.get("descripcion", "").strip(),
        "marca": formulario.get("marca", "").strip(),
        "unidad_medida": formulario.get("unidad_medida", "UNIDAD").strip().upper(),
    }
    # Las longitudes deben caber en las columnas VARCHAR de productos.
    limites = {"codigo_barras": 50, "nombre": 150, "descripcion": 300,
               "marca": 100, "unidad_medida": 30}
    for campo, limite in limites.items():
        if len(datos[campo]) > limite:
            raise ValueError(f"{campo.replace('_', ' ').capitalize()} es demasiado largo.")
    if not datos["codigo_barras"] or not datos["nombre"] or not datos["unidad_medida"]:
        raise ValueError("Código de barras, nombre y unidad de medida son obligatorios.")
    # Todo lo que llega de un formulario es texto; int() lo convierte a número.
    try:
        datos["id_categoria"] = int(formulario.get("id_categoria", ""))
        datos["stock_minimo"] = int(formulario.get("stock_minimo", ""))
        datos["stock_maximo"] = int(formulario.get("stock_maximo", ""))
    except ValueError as error:
        # int() falla con ValueError si el texto no es un entero.
        raise ValueError("Selecciona una categoría y escribe límites de stock enteros.") from error
    # 2.147.483.647 es el valor máximo que admite una columna INT de la base.
    if (
        datos["stock_minimo"] < 0
        or datos["stock_maximo"] < datos["stock_minimo"]
        or datos["stock_maximo"] > 2_147_483_647
    ):
        raise ValueError("Los límites de stock deben ser válidos y el máximo no menor que el mínimo.")
    datos["precio_compra"] = leer_decimal(formulario, "precio_compra")
    datos["precio_venta"] = leer_decimal(formulario, "precio_venta")
    return Producto(**datos)


def crear(formulario):
    producto = leer_producto(formulario)
    try:
        with transaccion() as cursor:
            ProductosRepositorio.insertar(cursor, producto)
    except IntegrityError as error:
        raise OperacionRechazada("El código de barras ya existe o la categoría no es válida.") from error
    except MySQLError as error:
        if error.args and error.args[0] == 30001:
            raise OperacionRechazada("Selecciona una categoría activa.") from error
        raise



def editar(id_producto, formulario):
    producto = leer_producto(formulario)
    try:
        with transaccion() as cursor:
            actual = ProductosRepositorio.obtener_bloqueado(cursor, id_producto)
            if actual is None:
                raise RegistroNoEncontrado
            if producto.id_categoria != actual.id_categoria:
                estado = CategoriasRepositorio.estado_bloqueado(cursor, producto.id_categoria)
                if estado != 1:
                    raise OperacionRechazada("Selecciona una categoría válida.")
            ProductosRepositorio.actualizar(cursor, id_producto, producto)
    except IntegrityError as error:
        raise OperacionRechazada("El código de barras ya existe o la categoría no es válida.") from error


def cambiar_estado(id_producto):
    with transaccion() as cursor:
        producto = ProductosRepositorio.obtener_bloqueado(cursor, id_producto)
        if producto is None:
            raise RegistroNoEncontrado
        if producto.estado == 1 and InventarioRepositorio.tiene_existencias(cursor, id_producto):
            raise OperacionRechazada("No se puede desactivar un producto que todavía tiene existencias.")
        ProductosRepositorio.fijar_estado(cursor, id_producto, int(not producto.estado))

