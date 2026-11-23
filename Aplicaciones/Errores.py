class RegistroNoEncontrado(Exception):
    """El registro solicitado no existe."""


class OperacionRechazada(ValueError):
    """Una regla de negocio impide guardar el cambio."""
