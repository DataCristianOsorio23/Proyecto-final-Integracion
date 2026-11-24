# Guía de inicio rápido

Necesitas Python 3.10 o posterior y el módulo MySQL de XAMPP. Abre PowerShell dentro de la carpeta del proyecto, `Proyecto-final-Integracion`; todos los comandos de esta guía se ejecutan allí.

## 1. Prepara Python

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Si `python` no está en el PATH, usa la ruta al ejecutable de tu instalación de Python para crear el entorno. Si ya tienes un `.env`, conserva ese archivo y revisa sus valores antes de ejecutar la aplicación.

## 2. Selecciona la base de datos

Inicia **MySQL** en XAMPP. Inicia Apache si vas a usar phpMyAdmin.

| Si quieres | Configuración |
| --- | --- |
| Una base independiente con datos de ejemplo | Importa `Script.sql` una vez mediante phpMyAdmin. El script crea `bd_inventario_supermercado_capas`. Configura `DB_NAME=bd_inventario_supermercado_capas` y un usuario autorizado sobre esa base. |
| Trabajar con los datos que ya existen | Configura `DB_NAME=bd_inventario_supermercado` y las credenciales de esa base. Los dos proyectos compartirán los registros y los cambios hechos desde cualquiera de ellos. |

Completa `DB_USER`, `DB_PASSWORD` y el puerto de tu instalación en `.env`. Para el CRUD, el usuario necesita permisos de lectura, inserción y actualización en la base elegida. `FLASK_SECRET_KEY` es opcional para las pruebas locales. Si queda vacía, las sesiones se renuevan al reiniciar Flask.

`Script.sql` es una instalación inicial. Si la base ya existe, usa la instalación existente o importa el script en una base con otro nombre. El archivo histórico `BD/Base_Datos.sql` empieza con `DROP DATABASE` sobre la base original.

### Instala los procedimientos almacenados

Selecciona en phpMyAdmin la misma base indicada en `DB_NAME` e importa [BD/procedimientos_almacenados.sql](BD/procedimientos_almacenados.sql). Este paso aplica tanto a una base nueva como a una base que ya contiene datos. Ejecuta la instalación con una cuenta que pueda crear y reemplazar rutinas. La cuenta de la aplicación necesita permiso `EXECUTE` sobre las rutinas que usa, además de sus permisos habituales sobre las tablas y vistas.

| Procedimiento | Uso |
| --- | --- |
| `sp_crear_producto` | El formulario de productos lo llama para crear el producto y su inventario inicial en cero por cada sucursal activa. |
| `sp_registrar_movimiento_inventario` | Registra entradas o salidas y actualiza el saldo. Valida los registros activos y rechaza saldos negativos. Está disponible desde SQL y el repositorio de inventario. |
| `sp_consultar_kardex` | Filtra el historial por producto, sucursal y rango de fechas. Cada filtro admite `NULL` para omitirlo. La fecha inicial se incluye y la final se excluye. |

Las rutinas de escritura se ejecutan dentro de la transacción del llamador. La aplicación ya controla la transacción al crear un producto. En una sesión SQL manual, inicia con `START TRANSACTION` y ejecuta `COMMIT` si la llamada termina correctamente o `ROLLBACK` si falla. Puedes consultar el kardex desde SQL con:

```sql
CALL sp_consultar_kardex(NULL, NULL, NULL, NULL);
```

### Aplica la actualización de módulos

En la misma base, importa [BD/actualizacion_modulos.sql](BD/actualizacion_modulos.sql) después de los procedimientos. Se puede importar más de una vez sin duplicar registros. El script:

- Ajusta `vw_inventario_general` para que el stock bajo sea `stock_actual <= stock_minimo`.
- Crea el cliente genérico `Consumidor final` para ventas sin datos del comprador.
- Crea en cero el inventario que falte para cada producto activo en cada sucursal activa. En los datos de ejemplo, Sucursal Sur no tenía inventario y sus 12 productos quedan agotados.
- Instala `sp_sincronizar_alertas`, que abre o cierra alertas según el saldo, y carga las alertas iniciales.

Este paso y el siguiente se comprobaron sobre la base creada con `Script.sql`. Si usas la base compartida `bd_inventario_supermercado`, también cambian los datos y las contraseñas que ve el otro proyecto.

### Cifra las contraseñas

Los usuarios de ejemplo de `Script.sql` tienen la contraseña `123456` en texto plano. En PowerShell, dentro de la carpeta del proyecto, ejecuta una vez:

```powershell
.\.venv\Scripts\python.exe cifrar_contrasenas.py
```

El comando guarda un hash en lugar de cada contraseña y no cambia las que ya tienen hash. Mientras no se ejecute, el inicio de sesión responde «Correo o contraseña incorrectos».

## 3. Inicia la aplicación

```powershell
.\.venv\Scripts\python.exe main.py
```

Abre [la aplicación](http://127.0.0.1:5000/) e inicia sesión. La contraseña de los usuarios de ejemplo es `123456`. El menú solo muestra las opciones del rol, y el servidor rechaza con el error 403 una dirección escrita a mano que el rol no tiene permitida.

| Usuario | Rol | Puede |
| --- | --- | --- |
| `admin@supermercado.com` | Administrador | Todas las opciones |
| `maria@supermercado.com` | Supervisor | Todas las opciones |
| `andres@supermercado.com` | Bodeguero | Productos, compras, ajustes, kardex y alertas |
| `laura@supermercado.com` | Vendedor | Sus propias ventas; consulta productos e inventario |

Todos los roles pueden consultar productos, categorías e inventario. Las categorías solo las administran el administrador y el supervisor.

## 4. Prueba el flujo

1. Crea una categoría y registra un producto en ella.
2. Abre Inventario y comprueba que el producto tenga saldo cero en cada sucursal activa.
3. Edita el producto. Los límites del catálogo se guardan como valores predeterminados y se respetan los límites ya asignados a las sucursales.
4. Desactiva el producto sin existencias y después la categoría si ya no tiene productos activos.
5. Como bodeguero, registra una compra con dos productos y recíbela. Comprueba en Kardex las dos entradas y en Inventario el nuevo saldo. Una compra recibida no se puede recibir otra vez ni anular.
6. Registra un ajuste desde Inventario con su justificación. Si el saldo queda en el mínimo o por debajo, aparece una alerta de stock bajo; si vuelve a la normalidad, la alerta se cierra.
7. Como vendedor, registra una venta y cóbrala. Si alguna línea no tiene stock suficiente en la sucursal, la venta completa se rechaza y sigue pendiente.

Compras y ventas usan un impuesto de ejemplo del 19 % sobre el subtotal de cada línea, calculado con `Decimal`. No es una liquidación fiscal. El número de factura de una venta se asigna solo (`FV-` más 10000 y el número de la venta). Una compra anulada deja libre su número de factura para ese proveedor.

Para consultar el inventario, kardex, ventas detalladas y compras detalladas desde SQL, selecciona la base en phpMyAdmin y ejecuta `BD/consultas_vistas.sql`.

## 5. Lee el código

Cada petición recorre las capas en este orden: `app.py` (ruta web) → `Aplicaciones/` (validaciones y reglas) → `Repositorios/` (SQL) → MySQL. Los datos viajan como clases de `Entidades/`. Cada función tiene un docstring que indica qué recibe, qué devuelve y qué error lanza, así que puedes entenderla sin leer todo su cuerpo.

Lee el código en este orden; cada paso se apoya en el anterior:

| # | Archivo | Qué mirar |
| --- | --- | --- |
| 1 | `main.py` | Solo importa la aplicación y llama a `ejecutar()`. |
| 2 | `Utilidades/Configuracion.py` | Cómo se leen el `.env` y los datos de conexión. |
| 3 | `Repositorios/BaseDatos.py` | `consultar()`, `consultar_uno()` y `transaccion()`, que confirma o revierte todo junto. |
| 4 | `app.py`, encabezado | El patrón de todas las rutas, `revisar_token()` (CSRF), `cargar_usuario()` (sesión) y `requiere()` (permisos). |
| 5 | Categorías: `crear_categoria()` en `app.py` → `Aplicaciones/CategoriasAplicacion.py` → `Entidades/Categoria.py` → `Repositorios/CategoriasRepositorio.py` | El flujo completo más simple, de punta a punta. |
| 6 | Productos: `Aplicaciones/ProductosAplicacion.py` → `Repositorios/ProductosRepositorio.py` | Validación con `Decimal` y alta con `sp_crear_producto`, en `BD/procedimientos_almacenados.sql`. |
| 7 | Acceso: `Aplicaciones/AutenticacionAplicacion.py`, `Repositorios/UsuariosRepositorio.py`, `Aplicaciones/Permisos.py` y `cifrar_contrasenas.py` | Inicio de sesión con hash y tabla de permisos por rol. |
| 8 | Inventario: `Aplicaciones/InventarioAplicacion.py` → `Repositorios/InventarioRepositorio.py` y `Repositorios/AlertasRepositorio.py` | `aplicar_movimiento()` es el único camino para cambiar un saldo: registra el kardex y actualiza las alertas (`BD/actualizacion_modulos.sql`). |
| 9 | Compras: `Aplicaciones/Importes.py` → `Aplicaciones/ComprasAplicacion.py` → `Repositorios/ComprasRepositorio.py` | Lectura de líneas, cálculo de importes y `recibir()`. |
| 10 | Ventas: `Aplicaciones/VentasAplicacion.py` → `Repositorios/VentasRepositorio.py` | `cobrar()`, que valida el stock de todas las líneas antes de descontar. |
| 11 | `templates/base.html` y luego la plantilla de cada pantalla | Menú según el rol, mensajes y formularios. |

`Repositorios/CatalogosRepositorio.py` reúne las listas de proveedores, clientes, sucursales, métodos de pago y tipos de movimiento que usan los formularios. Las excepciones propias están en `Aplicaciones/Errores.py`.

Si recibes un error 503, verifica que MySQL esté iniciado, revisa la conexión de `.env` y comprueba que la base contenga la vista `vw_inventario_general` para la pantalla de inventario.

