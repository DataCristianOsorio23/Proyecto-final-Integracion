from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor

from Utilidades.Configuracion import configuracion_mysql


def conectar():
    return pymysql.connect(cursorclass=DictCursor, **configuracion_mysql())


def consultar(sql, valores=()):
    with conectar() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(sql, valores)
            return cursor.fetchall()


def consultar_uno(sql, valores=()):
    with conectar() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(sql, valores)
            return cursor.fetchone()


@contextmanager
def transaccion():
    with conectar() as conexion:
        try:
            with conexion.cursor() as cursor:
                yield cursor
            conexion.commit()
        except Exception:
            conexion.rollback()
            raise
