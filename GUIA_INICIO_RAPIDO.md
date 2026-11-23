# Guía de inicio rápido

Necesitas Python 3.10 o posterior y el módulo MySQL de XAMPP. Abre PowerShell dentro de `Proyecto Nuevo/InventarioPorCapas`.

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

## 3. Configura el acceso e inicia la aplicación

Con MySQL iniciado, asigna una contraseña nueva a la cuenta administradora inicial. Usa tu correo de administrador si tu base ya tiene una cuenta distinta.

```powershell
.\.venv\Scripts\python.exe -m flask --app app establecer-password admin@supermercado.com
.\.venv\Scripts\python.exe main.py
```

El primer comando solicita y confirma la contraseña sin mostrarla en la consola. La contraseña debe tener entre 6 y 128 caracteres. Las cuentas iniciales y las contraseñas en texto plano de bases anteriores requieren este paso para habilitar su acceso. El comando actualiza la cuenta existente y conserva sus referencias.

Abre [la aplicación](http://127.0.0.1:5000/) e inicia sesión. En **Usuarios**, el administrador puede crear cuentas, asignar roles, cambiar contraseñas y activar o desactivar cuentas. También puede habilitar las cuentas de ejemplo existentes estableciendo sus contraseñas desde esa pantalla.

| Permiso | Administrador | Supervisor | Bodeguero | Vendedor |
| --- | :---: | :---: | :---: | :---: |
| Consultar productos, categorías e inventario | Sí | Sí | Sí | |
| Crear, editar y cambiar el estado de productos | Sí | Sí | Sí | |
| Crear, editar y cambiar el estado de categorías | Sí | Sí | | |
| Administrar usuarios y asignar roles | Sí | | | |

## 4. Prueba el flujo

1. Crea una categoría y registra un producto en ella.
2. Abre Inventario y comprueba que el producto tenga saldo cero en cada sucursal activa.
3. Edita el producto. Los límites del catálogo se guardan como valores predeterminados y se respetan los límites ya asignados a las sucursales.
4. Desactiva el producto sin existencias y después la categoría si ya no tiene productos activos.
5. Desde **Usuarios**, crea una cuenta con el rol Vendedor. Cierra sesión, ingresa con esa cuenta y comprueba que puedes consultar el catálogo. Si abres directamente `/productos/nuevo`, recibirás un error 403.

Para consultar el inventario, kardex, ventas detalladas y compras detalladas desde SQL, selecciona la base en phpMyAdmin y ejecuta `BD/consultas_vistas.sql`.

## 5. Lee el código

Empieza por `main.py` y sigue la ruta `crear_producto()` en `app.py`. El formulario se valida en `Aplicaciones/ProductosAplicacion.py` y se convierte en una instancia de `Entidades/Producto.py`. El repositorio llama a `sp_crear_producto` dentro de una transacción que confirma juntos el alta y el inventario inicial. La conexión lee sus parámetros de `Utilidades/Configuracion.py`.

Si recibes un error 503, verifica que MySQL esté iniciado, revisa la conexión de `.env` y comprueba que la base contenga la vista `vw_inventario_general` para la pantalla de inventario.

