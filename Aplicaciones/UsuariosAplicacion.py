import re
import secrets

from pymysql.err import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from Aplicaciones.Errores import OperacionRechazada, RegistroNoEncontrado
from Repositorios import UsuariosRepositorio


PERMISOS = {
    "Administrador": frozenset({"consultar", "productos", "categorias", "usuarios"}),
    "Supervisor": frozenset({"consultar", "productos", "categorias"}),
    "Bodeguero": frozenset({"consultar", "productos"}),
    "Vendedor": frozenset({"consultar"}),
}
HASH_AUXILIAR = generate_password_hash(secrets.token_urlsafe())


def permisos(usuario):
    return PERMISOS.get(usuario["rol"], frozenset()) if usuario else frozenset()


def autenticar(correo, password):
    correo = correo.strip().lower()
    if len(correo) > 150 or len(password) > 128:
        return None
    usuario = UsuariosRepositorio.buscar_acceso(correo)
    habilitado = usuario and usuario["password"].startswith("scrypt:")
    hash_guardado = usuario["password"] if habilitado else HASH_AUXILIAR
    if check_password_hash(hash_guardado, password) and habilitado and permisos(usuario):
        return usuario
    return None


def cargar_acceso(id_usuario):
    return UsuariosRepositorio.cargar_acceso(id_usuario)


def listar():
    return UsuariosRepositorio.listar()


def obtener(id_usuario):
    usuario = UsuariosRepositorio.obtener(id_usuario)
    if usuario is None:
        raise RegistroNoEncontrado()
    return usuario


def roles_disponibles():
    return [rol for rol in UsuariosRepositorio.roles_activos() if rol in PERMISOS]


def crear_hash(password):
    if not 6 <= len(password) <= 128 or not password.strip():
        raise OperacionRechazada("La contraseña debe tener entre 6 y 128 caracteres.")
    return generate_password_hash(password)


def guardar(id_admin, formulario, id_usuario=None):
    datos = {campo: formulario.get(campo, "").strip() for campo in ("nombre", "apellido", "correo")}
    datos["correo"] = datos["correo"].lower()
    if any(not 1 <= len(datos[campo]) <= 100 for campo in ("nombre", "apellido")):
        raise OperacionRechazada("Escribe un nombre y un apellido de hasta 100 caracteres.")
    if len(datos["correo"]) > 150 or not re.fullmatch(r"[^\s@]+@[^\s@]+", datos["correo"]):
        raise OperacionRechazada("Escribe un correo válido de hasta 150 caracteres.")

    datos["rol"] = "Administrador" if id_usuario == id_admin else formulario.get("rol")
    estado = formulario.get("estado", "1")
    if datos["rol"] not in PERMISOS or estado not in ("0", "1"):
        raise OperacionRechazada("Selecciona un rol y un estado válidos.")
    datos["estado"] = int(estado)
    password = formulario.get("password", "")
    datos["password"] = crear_hash(password) if password or id_usuario is None else None

    try:
        guardado = UsuariosRepositorio.guardar(id_admin, datos, id_usuario)
    except IntegrityError as error:
        if error.args[0] != 1062:
            raise
        raise OperacionRechazada("Ya existe una cuenta con ese correo.") from error
    if not guardado:
        raise OperacionRechazada("Comprueba que el rol y la cuenta administradora sigan activos.")


def establecer_password(correo, password):
    if not UsuariosRepositorio.establecer_password(correo.strip().lower(), crear_hash(password)):
        raise OperacionRechazada("No existe una cuenta con ese correo.")
