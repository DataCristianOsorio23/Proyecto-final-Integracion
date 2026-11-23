from Repositorios.BaseDatos import consultar, consultar_uno, transaccion


CAMPOS_PERFIL = "u.id_usuario, u.nombre, u.apellido, u.correo, u.estado, r.nombre AS rol"
TABLAS = " FROM usuarios u JOIN roles r ON r.id_rol = u.id_rol"
PERFIL = "SELECT " + CAMPOS_PERFIL + TABLAS
ACCESO = "SELECT " + CAMPOS_PERFIL + ", u.password" + TABLAS
ACTIVOS = " AND u.estado = 1 AND r.estado = 1"


def buscar_acceso(correo):
    return consultar_uno(ACCESO + " WHERE u.correo = %s" + ACTIVOS, (correo,))


def cargar_acceso(id_usuario):
    return consultar_uno(ACCESO + " WHERE u.id_usuario = %s" + ACTIVOS, (id_usuario,))


def listar():
    return consultar(PERFIL + " ORDER BY u.nombre, u.apellido, u.id_usuario")


def obtener(id_usuario):
    return consultar_uno(PERFIL + " WHERE u.id_usuario = %s", (id_usuario,))


def roles_activos():
    filas = consultar("SELECT nombre FROM roles WHERE estado = 1 ORDER BY nombre")
    return [fila["nombre"] for fila in filas]


def guardar(id_admin, datos, id_usuario=None):
    with transaccion() as cursor:
        cursor.execute(
            PERFIL + " WHERE u.id_usuario = %s" + ACTIVOS + " FOR UPDATE", (id_admin,),
        )
        administrador = cursor.fetchone()
        if not administrador or administrador["rol"] != "Administrador":
            return False
        cursor.execute(
            "SELECT id_rol FROM roles WHERE nombre = %s AND estado = 1 FOR UPDATE",
            (datos["rol"],),
        )
        rol = cursor.fetchone()
        if not rol:
            return False

        valores = (datos["nombre"], datos["apellido"], datos["correo"])
        if id_usuario is None:
            cursor.execute(
                """INSERT INTO usuarios (nombre, apellido, correo, id_rol, password)
                   VALUES (%s, %s, %s, %s, %s)""",
                (*valores, rol["id_rol"], datos["password"]),
            )
        else:
            # El administrador conserva su propio rol y estado.
            sql = "UPDATE usuarios SET nombre = %s, apellido = %s, correo = %s"
            if id_usuario != id_admin:
                sql += ", id_rol = %s, estado = %s"
                valores += (rol["id_rol"], datos["estado"])
            if datos["password"]:
                sql += ", password = %s"
                valores += (datos["password"],)
            cursor.execute(sql + " WHERE id_usuario = %s", (*valores, id_usuario))
    return True


def establecer_password(correo, password):
    with transaccion() as cursor:
        cursor.execute(
            "UPDATE usuarios SET password = %s WHERE correo = %s", (password, correo),
        )
        return cursor.rowcount == 1
