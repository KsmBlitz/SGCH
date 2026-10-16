"""Interés por mora (sección 8 del documento maestro).

Interés simple: se calcula sobre el saldo vencido de los conceptos de `CONCEPTOS_BASE`,
sin incluir intereses ni multas, y se cobra en la siguiente emisión. Se redondea hacia
abajo para no cobrar nunca más de lo que la tasa permite. [verificar] interés simple o
compuesto, base de cálculo y tope legal de la tasa.
"""

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from fractions import Fraction
from math import floor

from app.services.cargos import CargoPendiente, Concepto

CONCEPTOS_BASE = frozenset(
    {Concepto.GASTO_COMUN, Concepto.RESERVA, Concepto.EXTRAORDINARIO, Concepto.AJUSTE}
)


class TasaInvalidaError(ValueError):
    """La tasa de interés no es válida para la comunidad."""


def validar_tasa(tasa_mensual: Decimal, tope_mensual: Decimal | None = None) -> None:
    if not tasa_mensual.is_finite() or tasa_mensual < 0:
        raise TasaInvalidaError("La tasa de interés debe ser un número no negativo.")
    if tope_mensual is not None and tasa_mensual > tope_mensual:
        raise TasaInvalidaError(f"La tasa supera el tope legal de {tope_mensual}.")


def base_interes(pendientes: Iterable[CargoPendiente], fecha_corte: date) -> int:
    return sum(
        c.saldo_clp
        for c in pendientes
        if c.concepto in CONCEPTOS_BASE and c.vencido_al(fecha_corte)
    )


def calcular_interes(
    pendientes: Iterable[CargoPendiente],
    fecha_corte: date,
    tasa_mensual: Decimal,
    tope_mensual: Decimal | None = None,
) -> int:
    """Interés de un mes sobre el saldo vencido de una unidad al `fecha_corte`."""
    validar_tasa(tasa_mensual, tope_mensual)
    return floor(base_interes(pendientes, fecha_corte) * Fraction(tasa_mensual))
