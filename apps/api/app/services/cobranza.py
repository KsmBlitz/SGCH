"""Aplicación de pagos, anulación y morosidad (sección 8 del documento maestro).

- Un pago se aplica primero a los cargos más antiguos y, dentro del mismo período, en el
  orden de `ORDEN_IMPUTACION` [verificar si el reglamento o la ley fijan otro orden].
- Lo que sobra queda como saldo a favor de la unidad.
- Un pago no se borra: se anula, y sus aplicaciones dejan de contar. El saldo de cada
  cargo se deriva de las aplicaciones vigentes, de modo que anular restituye la deuda exacta.
- La morosidad se calcula, no se guarda.
"""

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from datetime import date

from app.services.cargos import CargoPendiente, Concepto

ORDEN_IMPUTACION: tuple[Concepto, ...] = (
    Concepto.INTERES,
    Concepto.MULTA,
    Concepto.RESERVA,
    Concepto.GASTO_COMUN,
    Concepto.EXTRAORDINARIO,
    Concepto.AJUSTE,
)
_PRIORIDAD = {concepto: i for i, concepto in enumerate(ORDEN_IMPUTACION)}

# Conceptos que forman una "cuota" para contar cuotas impagas [verificar].
CONCEPTOS_CUOTA = frozenset({Concepto.GASTO_COMUN, Concepto.RESERVA, Concepto.EXTRAORDINARIO})

# Ley 21.442: tres o más cuotas impagas, continuas o discontinuas.
UMBRAL_CUOTAS_IMPAGAS = 3


@dataclass(frozen=True)
class Aplicacion:
    cargo_id: str
    monto_clp: int


@dataclass(frozen=True)
class ResultadoAplicacion:
    aplicaciones: tuple[Aplicacion, ...]
    saldo_a_favor_clp: int


@dataclass(frozen=True)
class AplicacionRegistrada:
    pago_id: str
    cargo_id: str
    monto_clp: int


def orden_imputacion(pendientes: Iterable[CargoPendiente]) -> list[CargoPendiente]:
    return sorted(
        pendientes, key=lambda c: (c.periodo, _PRIORIDAD[c.concepto], c.vencimiento, c.id)
    )


def aplicar_pago(monto_clp: int, pendientes: Iterable[CargoPendiente]) -> ResultadoAplicacion:
    if isinstance(monto_clp, bool) or not isinstance(monto_clp, int) or monto_clp <= 0:
        raise ValueError("El monto del pago debe ser un entero CLP positivo.")

    restante = monto_clp
    aplicaciones: list[Aplicacion] = []
    for cargo in orden_imputacion(pendientes):
        if restante == 0:
            break
        aplicado = min(restante, cargo.saldo_clp)
        aplicaciones.append(Aplicacion(cargo_id=cargo.id, monto_clp=aplicado))
        restante -= aplicado
    return ResultadoAplicacion(aplicaciones=tuple(aplicaciones), saldo_a_favor_clp=restante)


def saldos_por_cargo(
    montos_cargos: Mapping[str, int],
    aplicaciones: Iterable[AplicacionRegistrada],
    pagos_anulados: Collection[str] = frozenset(),
) -> dict[str, int]:
    """Saldo de cada cargo según las aplicaciones de pagos no anulados."""
    saldos = dict(montos_cargos)
    for a in aplicaciones:
        if a.pago_id in pagos_anulados:
            continue
        if a.cargo_id not in saldos:
            raise ValueError(f"Aplicación a un cargo desconocido: {a.cargo_id}.")
        saldos[a.cargo_id] -= a.monto_clp
        if saldos[a.cargo_id] < 0:
            raise ValueError(f"El cargo {a.cargo_id} tiene más pagos aplicados que su monto.")
    return saldos


def es_morosa(pendientes: Iterable[CargoPendiente], fecha_corte: date) -> bool:
    return any(c.vencido_al(fecha_corte) for c in pendientes)


def cuotas_impagas(pendientes: Iterable[CargoPendiente], fecha_corte: date) -> int:
    """Número de períodos con alguna cuota vencida e impaga, continuos o no."""
    return len(
        {
            c.periodo
            for c in pendientes
            if c.concepto in CONCEPTOS_CUOTA and c.vencido_al(fecha_corte)
        }
    )


def elegible_convenio_o_suspension(pendientes: Iterable[CargoPendiente], fecha_corte: date) -> bool:
    """Solo marca la elegibilidad: la decisión siempre es humana y queda registrada."""
    return cuotas_impagas(pendientes, fecha_corte) >= UMBRAL_CUOTAS_IMPAGAS
