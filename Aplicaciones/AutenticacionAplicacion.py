"""Inicio de sesión y cifrado de contraseñas con Werkzeug."""

from werkzeug.security import check_password_hash, generate_password_hash

from Aplicaciones.Errores import OperacionRechazada
from Repositorios import UsuariosRepositorio
from Repositorios.BaseDatos import transaccion


# Prefijos de los hash que genera Werkzeug.
_PREFIJOS_HASH = ("scrypt:", "pbkdf2:")


def iniciar_sesion(formulario):
    """Comprueba correo y contraseña del formulario y devuelve el Usuario.

    Lanza ValueError si faltan datos y OperacionRechazada si no coinciden.
    """
    correo = formulario.get("correo", "").strip()
    contrasena = formulario.get("contrasena", "")
    if not correo or not contrasena:
        raise ValueError("Escribe el correo y la contraseña.")
    usuario, password_hash = UsuariosRepositorio.obtener_para_acceso(correo)
    # El mismo mensaje en todos los casos evita revelar qué correos existen.
    if usuario is None or not check_password_hash(password_hash, contrasena):
        raise OperacionRechazada("Correo o contraseña incorrectos.")
    return usuario


def usuario_activo(id_usuario):
    """Devuelve el Usuario guardado en la sesión si sigue activo; si no, None."""
    return UsuariosRepositorio.obtener_activo(id_usuario)


def cifrar_contrasenas_pendientes():
    """Reemplaza por su hash las contraseñas guardadas en texto plano. Devuelve cuántas cambió."""
    cambiadas = 0
    with transaccion() as cursor:
        for fila in UsuariosRepositorio.contrasenas_bloqueadas(cursor):
            if not fila["password"].startswith(_PREFIJOS_HASH):
                UsuariosRepositorio.actualizar_contrasena(
                    cursor, fila["id_usuario"], generate_password_hash(fila["password"])
                )
                cambiadas += 1
    return cambiadas
