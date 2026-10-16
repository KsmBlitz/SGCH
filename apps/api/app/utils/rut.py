"""RUT chileno: validación por módulo 11 y formato 12.345.678-5."""

import re

_PERMITIDOS = re.compile(r"^\d{1,9}[\dK]$")


class RutInvalidoError(ValueError):
    pass


def limpiar(rut: str) -> str:
    return rut.replace(".", "").replace("-", "").replace(" ", "").upper()


def calcular_dv(cuerpo: int) -> str:
    if cuerpo <= 0:
        raise RutInvalidoError("El cuerpo del RUT debe ser positivo.")
    suma, factor = 0, 2
    while cuerpo:
        suma += (cuerpo % 10) * factor
        cuerpo //= 10
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    return {11: "0", 10: "K"}.get(resto, str(resto))


def es_valido(rut: str) -> bool:
    limpio = limpiar(rut)
    if not _PERMITIDOS.match(limpio):
        return False
    cuerpo = int(limpio[:-1])
    return cuerpo > 0 and calcular_dv(cuerpo) == limpio[-1]


def normalizar(rut: str) -> str:
    """Forma canónica para guardar: sin puntos, con guion y DV en mayúscula (12345678-5)."""
    if not es_valido(rut):
        raise RutInvalidoError("RUT inválido.")
    limpio = limpiar(rut)
    return f"{int(limpio[:-1])}-{limpio[-1]}"


def formatear(rut: str) -> str:
    """Forma para mostrar: 12.345.678-5."""
    cuerpo, dv = normalizar(rut).split("-")
    return f"{int(cuerpo):,}".replace(",", ".") + f"-{dv}"
