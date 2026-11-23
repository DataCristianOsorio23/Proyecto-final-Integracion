"""Entrada web de Flask. Las reglas de negocio viven en Aplicaciones."""

import hmac
import secrets
from dataclasses import asdict
from functools import wraps

import click
from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from pymysql import MySQLError
from werkzeug.exceptions import NotFound

from Aplicaciones import (
    CategoriasAplicacion, InventarioAplicacion, ProductosAplicacion, UsuariosAplicacion,
)
from Aplicaciones.Errores import OperacionRechazada, RegistroNoEncontrado
from Utilidades.Configuracion import configuracion_mysql, configurar_flask


app = Flask(__name__)
configurar_flask(app)


def firma_sesion(usuario):
    return hmac.digest(
        app.secret_key.encode(), usuario["password"].encode(), "sha256",
    ).hex()


@app.before_request
def cargar_usuario():
    g.usuario = None
    id_usuario = session.get("id_usuario")
    if id_usuario is not None and request.endpoint not in ("static", "cerrar_sesion"):
        usuario = UsuariosAplicacion.cargar_acceso(id_usuario)
        if UsuariosAplicacion.permisos(usuario) and secrets.compare_digest(
            firma_sesion(usuario), session.get("firma", ""),
        ):
            g.usuario = {campo: valor for campo, valor in usuario.items() if campo != "password"}
        else:
            session.clear()
    g.permisos = UsuariosAplicacion.permisos(g.usuario)


def requiere_permiso(permiso):
    def decorar(vista):
        @wraps(vista)
        def protegida(*args, **kwargs):
            if g.usuario is None:
                return redirect(url_for("iniciar_sesion"), code=303)
            if permiso not in g.permisos:
                abort(403)
            return vista(*args, **kwargs)
        return protegida
    return decorar


@app.after_request
def evitar_cache_privada(respuesta):
    if request.endpoint != "static":
        respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


@app.context_processor
def incluir_token():
    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(24)
        return session["csrf_token"]

    return {"csrf_token": csrf_token}


@app.before_request
def revisar_token():
    if request.method == "POST":
        esperado = session.get("csrf_token", "")
        recibido = request.form.get("csrf_token", "")
        if not esperado or not secrets.compare_digest(esperado.encode(), recibido.encode()):
            abort(400, "El formulario venció. Recarga la página e inténtalo de nuevo.")


@app.errorhandler(MySQLError)
def error_base_datos(error):
    app.logger.exception("Error de base de datos: %s", error)
    return render_template("error.html"), 503


@app.errorhandler(RegistroNoEncontrado)
def error_registro_no_encontrado(_error):
    return NotFound()


@app.errorhandler(403)
def acceso_denegado(_error):
    return render_template("403.html"), 403


@app.route("/login", methods=["GET", "POST"])
def iniciar_sesion():
    if g.usuario is not None:
        return redirect(url_for("listar_productos"), code=303)
    correo = request.form.get("correo", "")
    if request.method == "POST":
        usuario = UsuariosAplicacion.autenticar(correo, request.form.get("password", ""))
        if usuario:
            session.clear()
            session["id_usuario"] = usuario["id_usuario"]
            session["firma"] = firma_sesion(usuario)
            return redirect(url_for("listar_productos"), code=303)
        flash("Correo o contraseña incorrectos.", "error")
    return render_template("login.html", correo=correo)


@app.post("/logout")
def cerrar_sesion():
    session.clear()
    return redirect(url_for("iniciar_sesion"), code=303)


@app.cli.command("establecer-password")
@click.argument("correo")
def establecer_password(correo):
    """Asigna una contraseña a una cuenta existente."""
    password = click.prompt("Contraseña", hide_input=True, confirmation_prompt=True)
    try:
        UsuariosAplicacion.establecer_password(correo, password)
    except OperacionRechazada as error:
        raise click.ClickException(str(error)) from error
    except MySQLError as error:
        codigo = error.args[0] if error.args else None
        config = configuracion_mysql()
        mensajes = {
            2003: f"No se pudo conectar a MySQL en {config['host']}:{config['port']}. "
                  "Revisa el estado de MySQL y su registro de errores en XAMPP.",
            1044: "DB_USER no tiene acceso a la base indicada en DB_NAME.",
            1045: "MySQL rechazó el acceso. Revisa DB_USER y DB_PASSWORD en .env.",
            1049: f"MySQL no encuentra la base {config['database']}. Revisa DB_NAME en .env.",
            1142: "DB_USER necesita permiso UPDATE sobre la tabla usuarios.",
            1146: f"No se encuentra la tabla usuarios en {config['database']}. Revisa DB_NAME en .env.",
        }
        mensaje = mensajes.get(codigo, "MySQL no pudo actualizar la contraseña. Revisa el registro del servidor.")
        raise click.ClickException(f"{mensaje} (Código MySQL: {codigo or 'desconocido'})") from error
    click.echo("Contraseña actualizada.")


@app.get("/usuarios")
@requiere_permiso("usuarios")
def listar_usuarios():
    return render_template("usuarios.html", usuarios=UsuariosAplicacion.listar())


@app.route("/usuarios/nuevo", methods=["GET", "POST"])
@requiere_permiso("usuarios")
def crear_usuario():
    return formulario_usuario()


@app.route("/usuarios/<int:id_usuario>/editar", methods=["GET", "POST"])
@requiere_permiso("usuarios")
def editar_usuario(id_usuario):
    return formulario_usuario(id_usuario)


def formulario_usuario(id_usuario=None):
    usuario = UsuariosAplicacion.obtener(id_usuario) if id_usuario is not None else {}
    id_admin = g.usuario["id_usuario"]
    if request.method == "POST":
        try:
            UsuariosAplicacion.guardar(id_admin, request.form, id_usuario)
        except OperacionRechazada as error:
            flash(str(error), "error")
            usuario = request.form
        else:
            flash("Usuario guardado correctamente.", "ok")
            return redirect(url_for("listar_usuarios"), code=303)
    return render_template(
        "usuario_form.html", usuario=usuario, propia=id_usuario == id_admin,
        editando=id_usuario is not None, roles=UsuariosAplicacion.roles_disponibles(),
        titulo="Editar usuario" if id_usuario is not None else "Nuevo usuario",
    )


@app.get("/")
@requiere_permiso("consultar")
def inicio():
    return redirect(url_for("listar_productos"))


@app.get("/categorias")
@requiere_permiso("consultar")
def listar_categorias():
    return render_template("categorias.html", categorias=CategoriasAplicacion.listar())


@app.route("/categorias/nueva", methods=["GET", "POST"])
@requiere_permiso("categorias")
def crear_categoria():
    if request.method == "POST":
        try:
            CategoriasAplicacion.crear(request.form)
        except ValueError as error:
            flash(str(error), "error")
        else:
            flash("Categoría creada correctamente.", "ok")
            return redirect(url_for("listar_categorias"))
    return render_template("categoria_form.html", categoria=request.form, titulo="Nueva categoría")


@app.route("/categorias/<int:id_categoria>/editar", methods=["GET", "POST"])
@requiere_permiso("categorias")
def editar_categoria(id_categoria):
    categoria = asdict(CategoriasAplicacion.obtener(id_categoria))
    if request.method == "POST":
        try:
            CategoriasAplicacion.editar(id_categoria, request.form)
        except ValueError as error:
            flash(str(error), "error")
            categoria = request.form
        else:
            flash("Categoría actualizada correctamente.", "ok")
            return redirect(url_for("listar_categorias"))
    return render_template("categoria_form.html", categoria=categoria, titulo="Editar categoría")


@app.post("/categorias/<int:id_categoria>/estado")
@requiere_permiso("categorias")
def cambiar_estado_categoria(id_categoria):
    try:
        CategoriasAplicacion.cambiar_estado(id_categoria)
    except OperacionRechazada as error:
        flash(str(error), "error")
    else:
        flash("Estado de la categoría actualizado.", "ok")
    return redirect(url_for("listar_categorias"))


@app.get("/productos")
@requiere_permiso("consultar")
def listar_productos():
    return render_template("productos.html", productos=ProductosAplicacion.listar())


@app.route("/productos/nuevo", methods=["GET", "POST"])
@requiere_permiso("productos")
def crear_producto():
    if request.method == "POST":
        try:
            ProductosAplicacion.crear(request.form)
        except ValueError as error:
            flash(str(error), "error")
        else:
            flash("Producto creado con inventario inicial en cero.", "ok")
            return redirect(url_for("listar_productos"))
    return render_template(
        "producto_form.html", producto=request.form,
        categorias=CategoriasAplicacion.disponibles(), titulo="Nuevo producto",
    )


@app.route("/productos/<int:id_producto>/editar", methods=["GET", "POST"])
@requiere_permiso("productos")
def editar_producto(id_producto):
    actual = ProductosAplicacion.obtener(id_producto)
    producto = asdict(actual)
    if request.method == "POST":
        try:
            ProductosAplicacion.editar(id_producto, request.form)
        except ValueError as error:
            flash(str(error), "error")
            producto = request.form
        else:
            flash("Producto actualizado. Los límites de sucursales existentes no cambian.", "ok")
            return redirect(url_for("listar_productos"))
    return render_template(
        "producto_form.html", producto=producto,
        categorias=CategoriasAplicacion.disponibles(actual.id_categoria), titulo="Editar producto",
    )


@app.post("/productos/<int:id_producto>/estado")
@requiere_permiso("productos")
def cambiar_estado_producto(id_producto):
    try:
        ProductosAplicacion.cambiar_estado(id_producto)
    except OperacionRechazada as error:
        flash(str(error), "error")
    else:
        flash("Estado del producto actualizado.", "ok")
    return redirect(url_for("listar_productos"))


@app.get("/inventario")
@requiere_permiso("consultar")
def ver_inventario():
    return render_template("inventario.html", filas=InventarioAplicacion.listar())


def ejecutar():
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    ejecutar()

