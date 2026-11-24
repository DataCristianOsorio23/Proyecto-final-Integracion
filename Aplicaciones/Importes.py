"""Lectura de las líneas de compras y ventas y cálculo de sus importes.

Las fórmulas siguen la sección 4 de docs/especificacion_funcional.md y usan Decimal.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from Entidades.LineaDocumento import LineaDocumento


# Tasa de ejemplo del prototipo académico; no es una liquidación fiscal real.
TASA_IMPUESTO = Decimal("19")
_CENTAVOS = Decimal("0.01")
# DECIMAL(12,2) admite valores menores que 10.000.000.000.
_MAXIMO = Decimal("10000000000")
_ENTERO_MAXIMO = 2_147_483_647


def _valor(lista, posicion):
    """Devuelve el texto de la lista en esa posición, sin espacios, o "" si no existe."""
    return lista[posicion].strip() if posicion < len(lista) else ""


def _leer_decimal(texto, etiqueta):
    """Convierte el texto en Decimal positivo con máximo 2 decimales. Lanza ValueError con la etiqueta."""
    try:
        valor = Decimal(texto)
    except InvalidOperation as error:
        raise ValueError(f"{etiqueta} debe ser un número.") from error
    if not valor.is_finite() or valor < 0 or valor >= _MAXIMO:
        raise ValueError(f"{etiqueta} debe ser positivo y válido.")
    if valor.as_tuple().exponent < -2:
        raise ValueError(f"{etiqueta} admite máximo 2 decimales.")
    return valor


def leer_lineas(formulario, productos, campo_precio, precio_editable):
    """Convierte las filas del formulario en líneas.

    productos: diccionario {id_producto: fila} con los productos activos.
    campo_precio: precio del catálogo que se aplica cuando la fila no trae precio.
    precio_editable: en compras se escribe el precio de la factura; en ventas se usa el del catálogo.
    Devuelve una lista de LineaDocumento. Lanza ValueError indicando el número de la línea con error.
    """
    ids = formulario.getlist("id_producto")
    cantidades = formulario.getlist("cantidad")
    precios = formulario.getlist("precio_unitario")
    descuentos = formulario.getlist("descuento")
    lineas, vistos = [], set()
    for posicion, texto_id in enumerate(ids):
        numero = posicion + 1
        texto_cantidad = _valor(cantidades, posicion)
        texto_precio = _valor(precios, posicion) if precio_editable else ""
        texto_descuento = _valor(descuentos, posicion)
        if not texto_id.strip():
            if texto_cantidad or texto_precio or texto_descuento:
                raise ValueError(f"Línea {numero}: selecciona un producto.")
            continue
        try:
            id_producto = int(texto_id)
            cantidad = int(texto_cantidad)
        except ValueError as error:
            raise ValueError(f"Línea {numero}: escribe una cantidad entera.") from error
        producto = productos.get(id_producto)
        if producto is None:
            raise ValueError(f"Línea {numero}: selecciona un producto activo.")
        if id_producto in vistos:
            raise ValueError(f"Línea {numero}: {producto['nombre']} ya está en otra línea.")
        vistos.add(id_producto)
        if cantidad <= 0 or cantidad > _ENTERO_MAXIMO:
            raise ValueError(f"Línea {numero}: la cantidad debe ser mayor que cero.")
        precio = (
            _leer_decimal(texto_precio, f"Línea {numero}: el precio")
            if texto_precio else producto[campo_precio]
        )
        descuento = (
            _leer_decimal(texto_descuento, f"Línea {numero}: el descuento")
            if texto_descuento else Decimal("0")
        )
        if descuento > cantidad * precio:
            raise ValueError(f"Línea {numero}: el descuento no puede superar el valor bruto de la línea.")
        lineas.append(LineaDocumento(id_producto, cantidad, precio, descuento, producto["nombre"]))
    if not lineas:
        raise ValueError("Agrega al menos un producto.")
    return lineas


def calcular(lineas):
    """Subtotal, descuento informativo, impuesto y total del encabezado.

    Recibe la lista de LineaDocumento. Devuelve un diccionario con subtotal, descuento, impuesto
    y total (Decimal). Lanza ValueError si el total supera el máximo de la columna.
    """
    subtotal = descuento = impuesto = Decimal("0")
    for linea in lineas:
        subtotal_linea = linea.cantidad * linea.precio_unitario - linea.descuento
        subtotal += subtotal_linea
        descuento += linea.descuento
        impuesto += (subtotal_linea * TASA_IMPUESTO / 100).quantize(_CENTAVOS, rounding=ROUND_HALF_UP)
    total = subtotal + impuesto
    if total >= _MAXIMO:
        raise ValueError("El total supera el valor máximo permitido.")
    return {"subtotal": subtotal, "descuento": descuento, "impuesto": impuesto, "total": total}
