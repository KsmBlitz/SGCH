"""Reparto de montos entre unidades según su prorrateo (sección 8 del documento maestro).

Los montos son enteros CLP y el redondeo usa el método del mayor residuo: cada parte es
el piso o el techo de su parte exacta, y la suma de las partes es exactamente el total.
El cálculo interno usa `Fraction`, por lo que no depende de la precisión de `Decimal`.
"""

from collections.abc import Hashable, Mapping
from decimal import Decimal
from fractions import Fraction
from math import floor

# Los prorrateos se guardan como numeric(9,8): 8 decimales (sección 10).
DECIMALES_PRORRATEO = 8
ESCALA_PRORRATEO = 10**DECIMALES_PRORRATEO
_CUANTO = Decimal(1).scaleb(-DECIMALES_PRORRATEO)


class ProrrateoInvalidoError(ValueError):
    """Los prorrateos no cumplen las reglas para cerrar un período."""


def validar_prorrateos(prorrateos: Mapping[str, Decimal]) -> None:
    """Exige prorrateos entre 0 y 1, con a lo más 8 decimales, que sumen exactamente 1."""
    if not prorrateos:
        raise ProrrateoInvalidoError("No hay unidades con prorrateo.")
    for unidad, valor in prorrateos.items():
        if not valor.is_finite() or valor < 0 or valor > 1:
            raise ProrrateoInvalidoError(f"Prorrateo fuera de rango en la unidad {unidad}.")
        if valor != valor.quantize(_CUANTO):
            raise ProrrateoInvalidoError(
                f"El prorrateo de la unidad {unidad} tiene más de {DECIMALES_PRORRATEO} decimales."
            )
    suma = sum(prorrateos.values(), Decimal(0))
    if suma != 1:
        raise ProrrateoInvalidoError(f"Los prorrateos suman {suma}, no 1.")


def repartir[K: Hashable](total: int, pesos: Mapping[K, Decimal | Fraction | int]) -> dict[K, int]:
    """Reparte `total` en proporción a `pesos` con el método del mayor residuo.

    Los pesos no necesitan sumar 1; se usa la proporción de cada uno sobre la suma.
    Un peso cero recibe siempre cero. Los empates de residuo se resuelven por el orden
    de `pesos`, por lo que el llamador debe entregar un orden estable (por ejemplo, por
    código de unidad) para que el resultado sea reproducible.
    """
    if isinstance(total, bool) or not isinstance(total, int):
        raise TypeError("El total debe ser un entero CLP.")
    if not pesos:
        raise ValueError("No hay entre quiénes repartir.")
    if total < 0:
        return {clave: -parte for clave, parte in repartir(-total, pesos).items()}

    fracciones = {clave: Fraction(peso) for clave, peso in pesos.items()}
    if any(f < 0 for f in fracciones.values()):
        raise ValueError("Los pesos no pueden ser negativos.")
    suma = sum(fracciones.values(), Fraction(0))
    if suma == 0:
        raise ValueError("La suma de los pesos es cero.")

    exactas = {clave: total * f / suma for clave, f in fracciones.items()}
    partes = {clave: floor(e) for clave, e in exactas.items()}
    restante = total - sum(partes.values())

    claves = list(exactas)
    por_residuo = sorted(
        range(len(claves)),
        key=lambda i: (-(exactas[claves[i]] - partes[claves[i]]), i),
    )
    for i in por_residuo[:restante]:
        partes[claves[i]] += 1
    return partes


def normalizar_prorrateos[K: Hashable](
    pesos: Mapping[K, Decimal | Fraction | int],
) -> dict[K, Decimal]:
    """Convierte pesos (por ejemplo, m² o prorrateos que no suman 1) en prorrateos de 8
    decimales que suman exactamente 1, repartiendo con el mismo método del mayor residuo.

    Es una corrección explícita: el sistema nunca normaliza sin que el administrador lo pida
    y quede auditado.
    """
    unidades = repartir(ESCALA_PRORRATEO, pesos)
    return {clave: Decimal(u).scaleb(-DECIMALES_PRORRATEO) for clave, u in unidades.items()}
