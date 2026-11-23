"""Entrada web de Flask. Las reglas de negocio viven en Aplicaciones."""

import secrets
from dataclasses import asdict

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from pymysql import MySQLError
from werkzeug.exceptions import NotFound

from Aplicaciones import CategoriasAplicacion, InventarioAplicacion, ProductosAplicacion
from Aplicaciones.Errores import OperacionRechazada, RegistroNoEncontrado
from Utilidades.Configuracion import configurar_flask


app = Flask(__name__)
configurar_flask(app)


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


@app.get("/")
def inicio():
    return redirect(url_for("listar_productos"))


@app.get("/categorias")
def listar_categorias():
    return render_template("categorias.html", categorias=CategoriasAplicacion.listar())


@app.route("/categorias/nueva", methods=["GET", "POST"])
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
def cambiar_estado_categoria(id_categoria):
    try:
        CategoriasAplicacion.cambiar_estado(id_categoria)
    except OperacionRechazada as error:
        flash(str(error), "error")
    else:
        flash("Estado de la categoría actualizado.", "ok")
    return redirect(url_for("listar_categorias"))


@app.get("/productos")
def listar_productos():
    return render_template("productos.html", productos=ProductosAplicacion.listar())


@app.route("/productos/nuevo", methods=["GET", "POST"])
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
def cambiar_estado_producto(id_producto):
    try:
        ProductosAplicacion.cambiar_estado(id_producto)
    except OperacionRechazada as error:
        flash(str(error), "error")
    else:
        flash("Estado del producto actualizado.", "ok")
    return redirect(url_for("listar_productos"))


@app.get("/inventario")
def ver_inventario():
    return render_template("inventario.html", filas=InventarioAplicacion.listar())


def ejecutar():
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    ejecutar()

