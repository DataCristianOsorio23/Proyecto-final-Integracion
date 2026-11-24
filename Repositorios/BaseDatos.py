"""Conexión a MySQL con PyMySQL. Las filas se devuelven como diccionarios."""

from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor

from Utilidades.Configuracion import configuracion_mysql


def conectar():
    """Abre y devuelve una conexión nueva con los datos del .env."""
    return pymysql.connect(cursorclass=DictCursor, **configuracion_mysql())


def consultar(sql, valores=()):
    """Ejecuta una consulta de lectura y devuelve todas las filas (lista de diccionarios)."""
    with conectar() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(sql, valores)
            return cursor.fetchall()


def consultar_uno(sql, valores=()):
    """Ejecuta una consulta de lectura y devuelve la primera fila (diccionario) o None."""
    with conectar() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(sql, valores)
            return cursor.fetchone()


@contextmanager
def transaccion():
    """Entrega un cursor para usar con «with». Confirma (commit) si el bloque termina bien
    y revierte (rollback) todo si ocurre cualquier error."""
    with conectar() as conexion:
        try:
            with conexion.cursor() as cursor:
                yield cursor
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise
