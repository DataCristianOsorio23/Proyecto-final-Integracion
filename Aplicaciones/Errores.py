"""Excepciones de la capa de aplicación y ayuda para los errores de las rutinas SQL."""


class RegistroNoEncontrado(Exception):
    """El registro solicitado no existe."""


class OperacionRechazada(ValueError):
    """Una regla de negocio impide guardar el cambio."""


def es_error_de_rutina(error):
    """Indica si el error viene de un SIGNAL de BD/procedimientos_almacenados.sql (30001-30010).

    Recibe un MySQLError y devuelve True o False.
    """
    return bool(error.args) and isinstance(error.args[0], int) and 30001 <= error.args[0] <= 30010
