import os
import secrets
from pathlib import Path

from dotenv import load_dotenv


RAIZ = Path(__file__).resolve().parents[1]
BASE_PREDETERMINADA = "bd_inventario_supermercado_capas"


def cargar_entorno():
    load_dotenv(RAIZ / ".env")


def configurar_flask(app):
    cargar_entorno()
    app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)


def configuracion_mysql():
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "user_python"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", BASE_PREDETERMINADA),
        "charset": "utf8mb4",
        "connect_timeout": 5,
    }
