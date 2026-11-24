"""Permisos por rol según la tabla de docs/especificacion_funcional.md.

Ver productos, categorías e inventario solo requiere iniciar sesión.
"""

ADMINISTRADOR = "Administrador"
SUPERVISOR = "Supervisor"
BODEGUERO = "Bodeguero"
VENDEDOR = "Vendedor"

_PERMISOS = {
    "administrar_categorias": {ADMINISTRADOR, SUPERVISOR},
    "administrar_productos": {ADMINISTRADOR, SUPERVISOR, BODEGUERO},
    "gestionar_compras": {ADMINISTRADOR, SUPERVISOR, BODEGUERO},
    "registrar_ajustes": {ADMINISTRADOR, SUPERVISOR, BODEGUERO},
    "gestionar_ventas": {ADMINISTRADOR, SUPERVISOR, VENDEDOR},
    "consultar_kardex": {ADMINISTRADOR, SUPERVISOR, BODEGUERO},
    "consultar_alertas": {ADMINISTRADOR, SUPERVISOR, BODEGUERO},
}


def puede(rol, permiso):
    """Recibe el nombre del rol y el del permiso. Devuelve True si el rol tiene ese permiso."""
    # Un nombre de permiso mal escrito produce KeyError en lugar de negar en silencio.
    return rol in _PERMISOS[permiso]


def solo_sus_ventas(rol):
    """El vendedor consulta y opera únicamente las ventas que registró."""
    return rol == VENDEDOR
