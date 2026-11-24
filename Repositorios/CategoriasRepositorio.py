"""Consultas SQL de la tabla categorias.

Las funciones que reciben cursor trabajan dentro de la transacción del llamador y no confirman.
"""

from Entidades.Categoria import Categoria
from Repositorios.BaseDatos import consultar, consultar_uno


def listar():
    """Devuelve todas las categorías (activas e inactivas) como lista de Categoria, por nombre."""
    filas = consultar(
        "SELECT id_categoria, nombre, descripcion, estado FROM categorias ORDER BY nombre"
    )
    return [Categoria(**fila) for fila in filas]


def disponibles(id_actual=None):
    """Devuelve las categorías activas y, si se indica, también la categoría id_actual aunque esté inactiva."""
    filas = consultar(
        "SELECT id_categoria, nombre, estado FROM categorias "
        "WHERE estado = 1 OR id_categoria = %s ORDER BY nombre",
        (id_actual or 0,),
    )
    return [Categoria(**fila) for fila in filas]


def obtener(id_categoria):
    """Devuelve la Categoria con ese id, o None si no existe."""
    fila = consultar_uno(
        "SELECT id_categoria, nombre, descripcion, estado FROM categorias WHERE id_categoria = %s",
        (id_categoria,),
    )
    return Categoria(**fila) if fila else None


def estado_bloqueado(cursor, id_categoria):
    """Bloquea la fila (FOR UPDATE) y devuelve su estado (1 o 0), o None si no existe."""
    cursor.execute(
        "SELECT estado FROM categorias WHERE id_categoria = %s FOR UPDATE",
        (id_categoria,),
    )
    fila = cursor.fetchone()
    return fila["estado"] if fila else None


def insertar(cursor, categoria):
    """Inserta la Categoria recibida. Un nombre repetido produce IntegrityError."""
    cursor.execute(
        "INSERT INTO categorias (nombre, descripcion) VALUES (%s, %s)",
        (categoria.nombre, categoria.descripcion),
    )


def actualizar(cursor, id_categoria, categoria):
    """Reemplaza el nombre y la descripción de la categoría id_categoria."""
    cursor.execute(
        "UPDATE categorias SET nombre = %s, descripcion = %s WHERE id_categoria = %s",
        (categoria.nombre, categoria.descripcion, id_categoria),
    )


def fijar_estado(cursor, id_categoria, estado):
    """Cambia el estado de la categoría a 1 (activa) o 0 (inactiva)."""
    cursor.execute(
        "UPDATE categorias SET estado = %s WHERE id_categoria = %s",
        (estado, id_categoria),
    )
