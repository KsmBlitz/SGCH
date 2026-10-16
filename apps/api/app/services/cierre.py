"""Cálculo de los cargos de un período (sección 8 del documento maestro).

Función pura: misma entrada, mismos cargos. La persistencia, la idempotencia del endpoint
y la auditoría se resuelven en la capa de API.

Reglas aplicadas:
- Cada concepto se reparte por separado con mayor residuo, de modo que el total de cada
  concepto (gasto común, reserva y cada gasto extraordinario) cuadra al peso por sí solo.
- El total del fondo de reserva es techo(r × G_ord), para que nunca quede bajo el
  porcentaje configurado por fracciones de peso (ADR 0012).
- Los gastos extraordinarios pueden usar un grupo de prorrateo propio (por ejemplo, una torre).
- Intereses y multas llegan ya calculados por unidad y se agregan como cargos propios.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from math import ceil

from app.services.cargos import Cargo, Concepto
from app.services.prorrateo import repartir, validar_prorrateos

# Ley 21.442: recargo no inferior al 5% del gasto común mensual [verificar artículo 39].
PCT_RESERVA_MINIMO = Decimal("0.05")


class CierreInvalidoError(ValueError):
    """La entrada no permite cerrar el período."""


@dataclass(frozen=True)
class GastoExtraordinario:
    referencia: str
    monto_clp: int
    # None usa el prorrateo general de la comunidad.
    prorrateos: Mapping[str, Decimal] | None = None


@dataclass(frozen=True)
class EntradaCierre:
    prorrateos: Mapping[str, Decimal]
    gasto_ordinario_clp: int
    pct_reserva: Decimal
    extraordinarios: Sequence[GastoExtraordinario] = ()
    intereses_clp: Mapping[str, int] = field(default_factory=dict)
    multas_clp: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ResultadoCierre:
    cargos: tuple[Cargo, ...]
    total_reserva_clp: int

    def total_clp(self) -> int:
        return sum(c.monto_clp for c in self.cargos)

    def total_por_concepto(self) -> dict[Concepto, int]:
        totales: dict[Concepto, int] = {}
        for c in self.cargos:
            totales[c.concepto] = totales.get(c.concepto, 0) + c.monto_clp
        return totales

    def total_por_unidad(self) -> dict[str, int]:
        totales: dict[str, int] = {}
        for c in self.cargos:
            totales[c.unidad] = totales.get(c.unidad, 0) + c.monto_clp
        return totales


def calcular_total_reserva(gasto_ordinario_clp: int, pct_reserva: Decimal) -> int:
    return ceil(gasto_ordinario_clp * Fraction(pct_reserva))


def calcular_cierre(entrada: EntradaCierre) -> ResultadoCierre:
    _validar(entrada)

    # Orden estable por código de unidad: desempata el mayor residuo de forma reproducible.
    unidades = sorted(entrada.prorrateos)
    general = {u: entrada.prorrateos[u] for u in unidades}

    cargos: list[Cargo] = []

    def agregar(montos: Mapping[str, int], concepto: Concepto, ref: str | None = None) -> None:
        cargos.extend(
            Cargo(unidad=u, concepto=concepto, monto_clp=m, referencia=ref)
            for u, m in montos.items()
            if m != 0
        )

    total_reserva = calcular_total_reserva(entrada.gasto_ordinario_clp, entrada.pct_reserva)
    if entrada.gasto_ordinario_clp > 0:
        agregar(repartir(entrada.gasto_ordinario_clp, general), Concepto.GASTO_COMUN)
        agregar(repartir(total_reserva, general), Concepto.RESERVA)

    for gasto in entrada.extraordinarios:
        grupo = (
            general
            if gasto.prorrateos is None
            else {u: gasto.prorrateos[u] for u in sorted(gasto.prorrateos)}
        )
        agregar(repartir(gasto.monto_clp, grupo), Concepto.EXTRAORDINARIO, gasto.referencia)

    agregar({u: entrada.intereses_clp.get(u, 0) for u in unidades}, Concepto.INTERES)
    agregar({u: entrada.multas_clp.get(u, 0) for u in unidades}, Concepto.MULTA)

    return ResultadoCierre(cargos=tuple(cargos), total_reserva_clp=total_reserva)


def _validar(entrada: EntradaCierre) -> None:
    validar_prorrateos(entrada.prorrateos)
    unidades = set(entrada.prorrateos)

    if entrada.gasto_ordinario_clp < 0:
        raise CierreInvalidoError("El gasto ordinario no puede ser negativo.")
    if not entrada.pct_reserva.is_finite() or entrada.pct_reserva < PCT_RESERVA_MINIMO:
        raise CierreInvalidoError(
            f"El recargo de reserva no puede ser menor a {PCT_RESERVA_MINIMO:.0%}."
        )

    referencias: set[str] = set()
    for gasto in entrada.extraordinarios:
        if gasto.monto_clp <= 0:
            raise CierreInvalidoError(
                f"El gasto extraordinario {gasto.referencia} debe ser positivo."
            )
        if gasto.referencia in referencias:
            raise CierreInvalidoError(f"Gasto extraordinario repetido: {gasto.referencia}.")
        referencias.add(gasto.referencia)
        if gasto.prorrateos is not None:
            validar_prorrateos(gasto.prorrateos)
            ajenas = set(gasto.prorrateos) - unidades
            if ajenas:
                raise CierreInvalidoError(
                    f"El grupo del gasto {gasto.referencia} incluye unidades ajenas a la comunidad."
                )

    for nombre, montos in (("intereses", entrada.intereses_clp), ("multas", entrada.multas_clp)):
        if set(montos) - unidades:
            raise CierreInvalidoError(f"Hay {nombre} de unidades ajenas a la comunidad.")
        if any(m < 0 for m in montos.values()):
            raise CierreInvalidoError(f"Los montos de {nombre} no pueden ser negativos.")
