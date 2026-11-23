from Entidades.Producto import Producto
from Repositorios.BaseDatos import consultar, consultar_uno


_CAMPOS = (
    "p.id_producto, p.id_categoria, p.codigo_barras, p.nombre, p.descripcion, "
    "p.marca, p.unidad_medida, p.precio_compra, p.precio_venta, p.stock_minimo, "
    "p.stock_maximo, p.estado"
)


def listar():
    filas = consultar(
        f"SELECT {_CAMPOS}, c.nombre AS categoria FROM productos p "
        "JOIN categorias c ON c.id_categoria = p.id_categoria ORDER BY p.nombre"
    )
    return [Producto(**fila) for fila in filas]


def obtener(id_producto):
    fila = consultar_uno(
        f"SELECT {_CAMPOS} FROM productos p WHERE p.id_producto = %s",
        (id_producto,),
    )
    return Producto(**fila) if fila else None


def obtener_bloqueado(cursor, id_producto):
    cursor.execute(
        f"SELECT {_CAMPOS} FROM productos p WHERE p.id_producto = %s FOR UPDATE",
        (id_producto,),
    )
    fila = cursor.fetchone()
    return Producto(**fila) if fila else None


def tiene_activos(cursor, id_categoria):
    cursor.execute(
        "SELECT 1 FROM productos WHERE id_categoria = %s AND estado = 1 LIMIT 1",
        (id_categoria,),
    )
    return cursor.fetchone() is not None


def _valores(producto):
    return (
        producto.id_categoria, producto.codigo_barras, producto.nombre,
        producto.descripcion, producto.marca, producto.unidad_medida,
        producto.precio_compra, producto.precio_venta, producto.stock_minimo,
        producto.stock_maximo,
    )


def insertar(cursor, producto):
    cursor.execute(
        "CALL sp_crear_producto(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        _valores(producto),
    )
    return cursor.fetchone()["id_producto"]


def actualizar(cursor, id_producto, producto):
    cursor.execute(
        "UPDATE productos SET id_categoria = %s, codigo_barras = %s, nombre = %s, "
        "descripcion = %s, marca = %s, unidad_medida = %s, precio_compra = %s, "
        "precio_venta = %s, stock_minimo = %s, stock_maximo = %s WHERE id_producto = %s",
        (*_valores(producto), id_producto),
    )


def fijar_estado(cursor, id_producto, estado):
    cursor.execute(
        "UPDATE productos SET estado = %s WHERE id_producto = %s",
        (estado, id_producto),
    )
