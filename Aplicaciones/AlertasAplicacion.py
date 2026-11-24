"""Casos de uso de alertas: listar por estado y marcar como atendida."""

from Aplicaciones.Errores import OperacionRechazada, RegistroNoEncontrado
from Repositorios import AlertasRepositorio
from Repositorios.BaseDatos import transaccion


FILTROS = ("PENDIENTE", "ATENDIDA", "TODAS")


def listar(filtro):
    """Lista las alertas del filtro elegido; por defecto, las pendientes.

    Devuelve una tupla (filtro aplicado, lista de Alerta).
    """
    if filtro not in FILTROS:
        filtro = "PENDIENTE"
    return filtro, AlertasRepositorio.listar(None if filtro == "TODAS" else filtro)


def atender(id_alerta):
    """Marca la alerta como ATENDIDA. Lanza RegistroNoEncontrado u OperacionRechazada si ya lo estaba."""
    with transaccion() as cursor:
        estado = AlertasRepositorio.estado_bloqueado(cursor, id_alerta)
        if estado is None:
            raise RegistroNoEncontrado
        if estado != "PENDIENTE":
            raise OperacionRechazada("La alerta ya estaba atendida.")
        AlertasRepositorio.marcar_atendida(cursor, id_alerta)
