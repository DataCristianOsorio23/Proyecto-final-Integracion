"""Entrada web de Flask. Las reglas de negocio viven en Aplicaciones.

Todas las rutas siguen el mismo patrón:
- GET muestra la página o el formulario con render_template.
- POST llama a una función de Aplicaciones. Si lanza ValueError (u OperacionRechazada), el mensaje
  se muestra con flash y se vuelve a mostrar el formulario; si todo sale bien, redirige.
- @requiere("permiso") rechaza con 403 a los roles sin permiso (ver Aplicaciones/Permisos.py).
"""

import secrets
from dataclasses import asdict
from functools import wraps

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from pymysql import MySQLError
from werkzeug.exceptions import NotFound

from Aplicaciones import (
    AlertasAplicacion, AutenticacionAplicacion, CategoriasAplicacion, ComprasAplicacion,
    InventarioAplicacion, Permisos, ProductosAplicacion, VentasAplicacion,
)
from Aplicaciones.Errores import OperacionRechazada, RegistroNoEncontrado
from Aplicaciones.Importes import TASA_IMPUESTO
from Utilidades.Configuracion import configurar_flask


app = Flask(__name__)
configurar_flask(app)

# Rutas disponibles sin iniciar sesión.
RUTAS_PUBLICAS = {"iniciar_sesion", "static"}
# Filas de producto que muestran los formularios de compras y ventas.
FILAS_DOCUMENTO = 6


@app.context_processor
def incluir_token():
    """Pone a disposición de todas las plantillas csrf_token(), puede(permiso) y tasa_impuesto."""
    def csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(24)
        return session["csrf_token"]

    def puede(permiso):
        return g.get("usuario") is not None and Permisos.puede(g.usuario.rol, permiso)

    return {"csrf_token": csrf_token, "puede": puede, "tasa_impuesto": TASA_IMPUESTO}


@app.before_request
def revisar_token():
    """Rechaza con 400 cualquier POST cuyo csrf_token no coincida con el de la sesión."""
    if request.method == "POST":
        esperado = session.get("csrf_token", "")
        recibido = request.form.get("csrf_token", "")
        if not esperado or not secrets.compare_digest(esperado.encode(), recibido.encode()):
            abort(400, "El formulario venció. Recarga la página e inténtalo de nuevo.")


@app.before_request
def cargar_usuario():
    """Exige sesión y vuelve a leer el usuario en cada petición por si fue desactivado.

    Deja el Usuario en g.usuario. Sin sesión, redirige a /login (salvo las rutas públicas).
    """
    g.usuario = None
    id_usuario = session.get("id_usuario")
    if id_usuario is not None:
        g.usuario = AutenticacionAplicacion.usuario_activo(id_usuario)
        if g.usuario is None:
            session.clear()
    if g.usuario is None and request.endpoint not in RUTAS_PUBLICAS:
        return redirect(url_for("iniciar_sesion"))
    return None


def requiere(permiso):
    """Valida el permiso en el servidor, aunque la opción esté oculta en el menú.

    Se usa como decorador: @requiere("gestionar_compras"). Sin permiso responde 403.
    """
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if not Permisos.puede(g.usuario.rol, permiso):
                abort(403)
            return vista(*args, **kwargs)
        return envoltura
    return decorador


@app.errorhandler(MySQLError)
def error_base_datos(error):
    """Registra el error y muestra la página de conexión fallida con código 503."""
    app.logger.exception("Error de base de datos: %s", error)
    return render_template("error.html"), 503


@app.errorhandler(RegistroNoEncontrado)
def error_registro_no_encontrado(_error):
    """Convierte RegistroNoEncontrado en una respuesta 404."""
    return NotFound()


@app.errorhandler(403)
def error_sin_permiso(_error):
    """Muestra la página «No tienes permiso» con código 403."""
    return render_template("sin_permiso.html"), 403


def filas_documento(formulario):
    """Valores de las filas de producto para volver a mostrar el formulario.

    Recibe request.form y devuelve FILAS_DOCUMENTO diccionarios con id_producto, cantidad,
    precio_unitario y descuento (texto vacío si la fila no venía).
    """
    columnas = ("id_producto", "cantidad", "precio_unitario", "descuento")
    valores = {columna: formulario.getlist(columna) for columna in columnas}
    return [
        {columna: (valores[columna][i] if i < len(valores[columna]) else "") for columna in columnas}
        for i in range(FILAS_DOCUMENTO)
    ]


# ---------- Acceso ----------

@app.route("/login", methods=["GET", "POST"])
def iniciar_sesion():
    """GET muestra el formulario de acceso; POST valida correo y contraseña y abre la sesión."""
    if g.usuario is not None:
        return redirect(url_for("listar_productos"))
    if request.method == "POST":
        try:
            usuario = AutenticacionAplicacion.iniciar_sesion(request.form)
        except ValueError as error:
            flash(str(error), "error")
        else:
            # Una sesión nueva evita reutilizar datos de una sesión anterior.
            session.clear()
            session["id_usuario"] = usuario.id_usuario
            flash(f"Bienvenido, {usuario.nombre}.", "ok")
            return redirect(url_for("listar_productos"))
    return render_template("login.html", correo=request.form.get("correo", ""))


@app.post("/logout")
def cerrar_sesion():
    """Borra la sesión y redirige al inicio de sesión."""
    session.clear()
    flash("Sesión cerrada.", "ok")
    return redirect(url_for("iniciar_sesion"))


@app.get("/")
def inicio():
    """Redirige a la lista de productos."""
    return redirect(url_for("listar_productos"))


# ---------- Categorías ----------

@app.get("/categorias")
def listar_categorias():
    """Muestra todas las categorías."""
    return render_template("categorias.html", categorias=CategoriasAplicacion.listar())


@app.route("/categorias/nueva", methods=["GET", "POST"])
@requiere("administrar_categorias")
def crear_categoria():
    """GET muestra el formulario; POST crea la categoría."""
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
@requiere("administrar_categorias")
def editar_categoria(id_categoria):
    """GET muestra la categoría en el formulario; POST guarda los cambios."""
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
@requiere("administrar_categorias")
def cambiar_estado_categoria(id_categoria):
    """Activa o desactiva la categoría y vuelve a la lista."""
    try:
        CategoriasAplicacion.cambiar_estado(id_categoria)
    except OperacionRechazada as error:
        flash(str(error), "error")
    else:
        flash("Estado de la categoría actualizado.", "ok")
    return redirect(url_for("listar_categorias"))


# ---------- Productos ----------

@app.get("/productos")
def listar_productos():
    """Muestra todos los productos."""
    return render_template("productos.html", productos=ProductosAplicacion.listar())


@app.route("/productos/nuevo", methods=["GET", "POST"])
@requiere("administrar_productos")
def crear_producto():
    """GET muestra el formulario; POST crea el producto con inventario en cero."""
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
@requiere("administrar_productos")
def editar_producto(id_producto):
    """GET muestra el producto en el formulario; POST guarda los cambios."""
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
@requiere("administrar_productos")
def cambiar_estado_producto(id_producto):
    """Activa o desactiva el producto y vuelve a la lista."""
    try:
        ProductosAplicacion.cambiar_estado(id_producto)
    except OperacionRechazada as error:
        flash(str(error), "error")
    else:
        flash("Estado del producto actualizado.", "ok")
    return redirect(url_for("listar_productos"))


# ---------- Inventario, kardex y alertas ----------

@app.get("/inventario")
def ver_inventario():
    """Muestra el saldo de cada producto por sucursal."""
    return render_template("inventario.html", filas=InventarioAplicacion.listar())


@app.route("/inventario/ajustes/nuevo", methods=["GET", "POST"])
@requiere("registrar_ajustes")
def registrar_ajuste():
    """GET muestra el formulario de ajuste; POST registra el ajuste en el kardex."""
    if request.method == "POST":
        try:
            resultado = InventarioAplicacion.registrar_ajuste(request.form, g.usuario.id_usuario)
        except ValueError as error:
            flash(str(error), "error")
        else:
            flash(
                f"Ajuste registrado. Saldo: {resultado['stock_anterior']} → {resultado['stock_nuevo']}.",
                "ok",
            )
            return redirect(url_for("ver_inventario"))
    return render_template("ajuste_form.html", ajuste=request.form, **InventarioAplicacion.datos_ajuste())


@app.get("/kardex")
@requiere("consultar_kardex")
def ver_kardex():
    """Muestra el kardex filtrado con los parámetros de la URL (producto, sucursal y fechas)."""
    movimientos = []
    try:
        movimientos = InventarioAplicacion.consultar_kardex(request.args)
    except ValueError as error:
        flash(str(error), "error")
    return render_template(
        "kardex.html", movimientos=movimientos, filtros=request.args,
        **InventarioAplicacion.filtros_kardex(),
    )


@app.get("/alertas")
@requiere("consultar_alertas")
def listar_alertas():
    """Muestra las alertas del estado indicado en ?estado= (por defecto, pendientes)."""
    filtro, alertas = AlertasAplicacion.listar(request.args.get("estado", "PENDIENTE"))
    return render_template("alertas.html", alertas=alertas, filtro=filtro)


@app.post("/alertas/<int:id_alerta>/atender")
@requiere("consultar_alertas")
def atender_alerta(id_alerta):
    """Marca la alerta como atendida y vuelve a la lista."""
    try:
        AlertasAplicacion.atender(id_alerta)
    except OperacionRechazada as error:
        flash(str(error), "error")
    else:
        flash("Alerta marcada como atendida.", "ok")
    return redirect(url_for("listar_alertas"))


# ---------- Compras ----------

@app.get("/compras")
@requiere("gestionar_compras")
def listar_compras():
    """Muestra todas las compras."""
    return render_template("compras.html", compras=ComprasAplicacion.listar())


@app.route("/compras/nueva", methods=["GET", "POST"])
@requiere("gestionar_compras")
def crear_compra():
    """GET muestra el formulario; POST registra la compra y abre su detalle."""
    if request.method == "POST":
        try:
            id_compra = ComprasAplicacion.registrar(request.form, g.usuario.id_usuario)
        except ValueError as error:
            flash(str(error), "error")
        else:
            flash("Compra registrada. Recíbela para sumar las existencias.", "ok")
            return redirect(url_for("ver_compra", id_compra=id_compra))
    return render_template(
        "compra_form.html", compra=request.form, filas=filas_documento(request.form),
        **ComprasAplicacion.datos_formulario(),
    )


@app.get("/compras/<int:id_compra>")
@requiere("gestionar_compras")
def ver_compra(id_compra):
    """Muestra el encabezado, las líneas y las acciones de una compra."""
    compra, lineas = ComprasAplicacion.obtener(id_compra)
    return render_template("compra_detalle.html", compra=compra, lineas=lineas)


@app.post("/compras/<int:id_compra>/recibir")
@requiere("gestionar_compras")
def recibir_compra(id_compra):
    """Recibe la compra (suma el stock) y vuelve a su detalle."""
    try:
        ComprasAplicacion.recibir(id_compra, g.usuario.id_usuario)
    except OperacionRechazada as error:
        flash(str(error), "error")
    else:
        flash("Compra recibida. Las existencias y el kardex se actualizaron.", "ok")
    return redirect(url_for("ver_compra", id_compra=id_compra))


@app.post("/compras/<int:id_compra>/anular")
@requiere("gestionar_compras")
def anular_compra(id_compra):
    """Anula la compra registrada y vuelve a su detalle."""
    try:
        ComprasAplicacion.anular(id_compra)
    except OperacionRechazada as error:
        flash(str(error), "error")
    else:
        flash("Compra anulada.", "ok")
    return redirect(url_for("ver_compra", id_compra=id_compra))


# ---------- Ventas ----------

@app.get("/ventas")
@requiere("gestionar_ventas")
def listar_ventas():
    """Muestra las ventas que el usuario puede ver (el vendedor, solo las suyas)."""
    return render_template("ventas.html", ventas=VentasAplicacion.listar(g.usuario))


@app.route("/ventas/nueva", methods=["GET", "POST"])
@requiere("gestionar_ventas")
def crear_venta():
    """GET muestra el formulario; POST registra la venta como pendiente y abre su detalle."""
    if request.method == "POST":
        try:
            id_venta, numero_factura = VentasAplicacion.registrar(request.form, g.usuario)
        except ValueError as error:
            flash(str(error), "error")
        else:
            flash(f"Venta {numero_factura} registrada como pendiente. Cóbrala para descontar el stock.", "ok")
            return redirect(url_for("ver_venta", id_venta=id_venta))
    return render_template(
        "venta_form.html", venta=request.form, filas=filas_documento(request.form),
        **VentasAplicacion.datos_formulario(),
    )


@app.get("/ventas/<int:id_venta>")
@requiere("gestionar_ventas")
def ver_venta(id_venta):
    """Muestra el encabezado, las líneas y las acciones de una venta."""
    venta, lineas = VentasAplicacion.obtener(id_venta, g.usuario)
    return render_template("venta_detalle.html", venta=venta, lineas=lineas)


@app.post("/ventas/<int:id_venta>/cobrar")
@requiere("gestionar_ventas")
def cobrar_venta(id_venta):
    """Cobra la venta (descuenta el stock) y vuelve a su detalle."""
    try:
        VentasAplicacion.cobrar(id_venta, g.usuario)
    except OperacionRechazada as error:
        flash(str(error), "error")
    else:
        flash("Venta cobrada. Las existencias y el kardex se actualizaron.", "ok")
    return redirect(url_for("ver_venta", id_venta=id_venta))


@app.post("/ventas/<int:id_venta>/anular")
@requiere("gestionar_ventas")
def anular_venta(id_venta):
    """Anula la venta pendiente y vuelve a su detalle."""
    try:
        VentasAplicacion.anular(id_venta, g.usuario)
    except OperacionRechazada as error:
        flash(str(error), "error")
    else:
        flash("Venta anulada.", "ok")
    return redirect(url_for("ver_venta", id_venta=id_venta))


def ejecutar():
    """Inicia el servidor de desarrollo de Flask en 127.0.0.1:5000."""
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    ejecutar()
