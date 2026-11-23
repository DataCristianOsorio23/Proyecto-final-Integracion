from pymysql import IntegrityError

from Aplicaciones.Errores import OperacionRechazada, RegistroNoEncontrado
from Entidades.Categoria import Categoria
from Repositorios import CategoriasRepositorio, ProductosRepositorio
from Repositorios.BaseDatos import transaccion


def listar():
    return CategoriasRepositorio.listar()


def obtener(id_categoria):
    categoria = CategoriasRepositorio.obtener(id_categoria)
    if categoria is None:
        raise RegistroNoEncontrado
    return categoria


def disponibles(id_actual=None):
    return CategoriasRepositorio.disponibles(id_actual)


def leer_categoria(formulario):
    nombre = formulario.get("nombre", "").strip()
    descripcion = formulario.get("descripcion", "").strip()
    if not nombre or len(nombre) > 100:
        raise ValueError("El nombre debe tener entre 1 y 100 caracteres.")
    if len(descripcion) > 250:
        raise ValueError("La descripción no puede superar 250 caracteres.")
    return Categoria(nombre, descripcion)


def crear(formulario):
    categoria = leer_categoria(formulario)
    try:
        with transaccion() as cursor:
            CategoriasRepositorio.insertar(cursor, categoria)
    except IntegrityError as error:
        raise OperacionRechazada("Ya existe una categoría con ese nombre.") from error


def editar(id_categoria, formulario):
    categoria = leer_categoria(formulario)
    try:
        with transaccion() as cursor:
            if CategoriasRepositorio.estado_bloqueado(cursor, id_categoria) is None:
                raise RegistroNoEncontrado
            CategoriasRepositorio.actualizar(cursor, id_categoria, categoria)
    except IntegrityError as error:
        raise OperacionRechazada("Ya existe una categoría con ese nombre.") from error


def cambiar_estado(id_categoria):
    with transaccion() as cursor:
        estado = CategoriasRepositorio.estado_bloqueado(cursor, id_categoria)
        if estado is None:
            raise RegistroNoEncontrado
        if estado == 1 and ProductosRepositorio.tiene_activos(cursor, id_categoria):
            raise OperacionRechazada("Desactiva primero los productos activos de esta categoría.")
        CategoriasRepositorio.fijar_estado(cursor, id_categoria, int(not estado))
