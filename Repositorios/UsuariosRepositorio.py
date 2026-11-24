"""Consultas SQL de usuarios y roles para el inicio de sesión."""

from Entidades.Usuario import Usuario
from Repositorios.BaseDatos import consultar_uno


_CAMPOS = "u.id_usuario, u.nombre, u.apellido, u.correo, r.nombre AS rol"
_ORIGEN = "FROM usuarios u JOIN roles r ON r.id_rol = u.id_rol"
# Solo pueden entrar los usuarios activos con un rol activo.
_ACTIVO = "u.estado = 1 AND r.estado = 1"


def obtener_para_acceso(correo):
    """Devuelve el usuario activo y el hash de su contraseña, o (None, None).

    Recibe el correo. Devuelve una tupla (Usuario, hash) para comprobar la contraseña.
    """
    fila = consultar_uno(
        f"SELECT {_CAMPOS}, u.password {_ORIGEN} WHERE u.correo = %s AND {_ACTIVO}",
        (correo,),
    )
    if fila is None:
        return None, None
    password = fila.pop("password")
    return Usuario(**fila), password


def obtener_activo(id_usuario):
    """Devuelve el Usuario si existe y está activo con un rol activo; si no, None."""
    fila = consultar_uno(
        f"SELECT {_CAMPOS} {_ORIGEN} WHERE u.id_usuario = %s AND {_ACTIVO}",
        (id_usuario,),
    )
    return Usuario(**fila) if fila else None


def contrasenas_bloqueadas(cursor):
    """Bloquea la tabla usuarios y devuelve una lista de diccionarios con id_usuario y password."""
    cursor.execute("SELECT id_usuario, password FROM usuarios FOR UPDATE")
    return cursor.fetchall()


def actualizar_contrasena(cursor, id_usuario, password_hash):
    """Guarda el hash recibido como contraseña del usuario."""
    cursor.execute(
        "UPDATE usuarios SET password = %s WHERE id_usuario = %s",
        (password_hash, id_usuario),
    )
