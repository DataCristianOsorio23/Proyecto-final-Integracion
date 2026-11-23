from Entidades.Categoria import Categoria
from Repositorios.BaseDatos import consultar, consultar_uno


def listar():
    filas = consultar(
        "SELECT id_categoria, nombre, descripcion, estado FROM categorias ORDER BY nombre"
    )
    return [Categoria(**fila) for fila in filas]


def disponibles(id_actual=None):
    filas = consultar(
        "SELECT id_categoria, nombre, estado FROM categorias "
        "WHERE estado = 1 OR id_categoria = %s ORDER BY nombre",
        (id_actual or 0,),
    )
    return [Categoria(**fila) for fila in filas]


def obtener(id_categoria):
    fila = consultar_uno(
        "SELECT id_categoria, nombre, descripcion, estado FROM categorias WHERE id_categoria = %s",
        (id_categoria,),
    )
    return Categoria(**fila) if fila else None


def estado_bloqueado(cursor, id_categoria):
    cursor.execute(
        "SELECT estado FROM categorias WHERE id_categoria = %s FOR UPDATE",
        (id_categoria,),
    )
    fila = cursor.fetchone()
    return fila["estado"] if fila else None


def insertar(cursor, categoria):
    cursor.execute(
        "INSERT INTO categorias (nombre, descripcion) VALUES (%s, %s)",
        (categoria.nombre, categoria.descripcion),
    )


def actualizar(cursor, id_categoria, categoria):
    cursor.execute(
        "UPDATE categorias SET nombre = %s, descripcion = %s WHERE id_categoria = %s",
        (categoria.nombre, categoria.descripcion, id_categoria),
    )


def fijar_estado(cursor, id_categoria, estado):
    cursor.execute(
        "UPDATE categorias SET estado = %s WHERE id_categoria = %s",
        (estado, id_categoria),
    )
