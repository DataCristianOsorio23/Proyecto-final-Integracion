"""Casos de uso de categorías: listar, validar, crear, editar y activar o desactivar.

Los errores de validación se lanzan como ValueError (o OperacionRechazada) para mostrarlos con flash.
"""

from pymysql import IntegrityError

from Aplicaciones.Errores import OperacionRechazada, RegistroNoEncontrado
from Entidades.Categoria import Categoria
from Repositorios import CategoriasRepositorio, ProductosRepositorio
from Repositorios.BaseDatos import transaccion


def listar():
    """Devuelve todas las categorías (lista de Categoria)."""
    return CategoriasRepositorio.listar()


def obtener(id_categoria):
    """Devuelve la Categoria con ese id. Lanza RegistroNoEncontrado si no existe."""
    categoria = CategoriasRepositorio.obtener(id_categoria)
    if categoria is None:
        raise RegistroNoEncontrado
    return categoria


def disponibles(id_actual=None):
    """Devuelve las categorías que se pueden elegir en el formulario de productos."""
    return CategoriasRepositorio.disponibles(id_actual)


def leer_categoria(formulario):
    """Valida el formulario (nombre y descripción) y devuelve una Categoria. Lanza ValueError."""
    nombre = formulario.get("nombre", "").strip()
    descripcion = formulario.get("descripcion", "").strip()
    if not nombre or len(nombre) > 100:
        raise ValueError("El nombre debe tener entre 1 y 100 caracteres.")
    if len(descripcion) > 250:
        raise ValueError("La descripción no puede superar 250 caracteres.")
    return Categoria(nombre, descripcion)


def crear(formulario):
    """Crea la categoría del formulario. Lanza OperacionRechazada si el nombre ya existe."""
    categoria = leer_categoria(formulario)
    try:
        with transaccion() as cursor:
            CategoriasRepositorio.insertar(cursor, categoria)
    except IntegrityError as error:
        raise OperacionRechazada("Ya existe una categoría con ese nombre.") from error


def editar(id_categoria, formulario):
    """Actualiza la categoría con los datos del formulario. Lanza RegistroNoEncontrado u OperacionRechazada."""
    categoria = leer_categoria(formulario)
    try:
        with transaccion() as cursor:
            if CategoriasRepositorio.estado_bloqueado(cursor, id_categoria) is None:
                raise RegistroNoEncontrado
            CategoriasRepositorio.actualizar(cursor, id_categoria, categoria)
    except IntegrityError as error:
        raise OperacionRechazada("Ya existe una categoría con ese nombre.") from error


def cambiar_estado(id_categoria):
    """Activa o desactiva la categoría. No se desactiva si tiene productos activos (OperacionRechazada)."""
    with transaccion() as cursor:
        estado = CategoriasRepositorio.estado_bloqueado(cursor, id_categoria)
        if estado is None:
            raise RegistroNoEncontrado
        if estado == 1 and ProductosRepositorio.tiene_activos(cursor, id_categoria):
            raise OperacionRechazada("Desactiva primero los productos activos de esta categoría.")
        CategoriasRepositorio.fijar_estado(cursor, id_categoria, int(not estado))
