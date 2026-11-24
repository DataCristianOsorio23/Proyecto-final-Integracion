r"""Convierte a hash las contraseñas de usuarios que siguen en texto plano.

Ejecuta en PowerShell, dentro de la carpeta del proyecto:
    .\.venv\Scripts\python.exe cifrar_contrasenas.py

Se puede ejecutar varias veces: las contraseñas que ya tienen hash no cambian.
"""

from Aplicaciones.AutenticacionAplicacion import cifrar_contrasenas_pendientes
from Utilidades.Configuracion import cargar_entorno


if __name__ == "__main__":
    cargar_entorno()
    cambiadas = cifrar_contrasenas_pendientes()
    print(f"Contraseñas convertidas a hash: {cambiadas}")
