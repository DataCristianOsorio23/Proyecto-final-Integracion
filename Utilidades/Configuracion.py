"""Configuración de Flask y MySQL leída del archivo .env."""

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv


RAIZ = Path(__file__).resolve().parents[1]
BASE_PREDETERMINADA = "bd_inventario_supermercado_capas"


def cargar_entorno():
    """Carga las variables del .env de la raíz del proyecto. No reemplaza las que ya existen."""
    load_dotenv(RAIZ / ".env")


def configurar_flask(app):
    """Recibe la aplicación Flask y le asigna la clave de sesión (FLASK_SECRET_KEY o una aleatoria)."""
    cargar_entorno()
    app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)


def configuracion_mysql():
    """Devuelve un diccionario con los parámetros de conexión para pymysql.connect()."""
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "user_python"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", BASE_PREDETERMINADA),
        "charset": "utf8mb4",
        "connect_timeout": 5,
    }
