from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.services.cargos import CargoPendiente, Concepto
from app.services.cobranza import (
    Aplicacion,
    AplicacionRegistrada,
    aplicar_pago,
    cuotas_impagas,
    elegible_convenio_o_suspension,
    es_morosa,
    saldos_por_cargo,
)

AGO, SEP, OCT = date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)


def pendiente(id: str, periodo: date, concepto: Concepto, saldo: int) -> CargoPendiente:
    vencimiento = periodo.replace(day=10)
    return CargoPendiente(id, periodo, concepto, saldo, vencimiento)


PENDIENTES = [
    pendiente("sep-gc", SEP, Concepto.GASTO_COMUN, 100_000),
    pendiente("sep-res", SEP, Concepto.RESERVA, 5_000),
    pendiente("ago-gc", AGO, Concepto.GASTO_COMUN, 100_000),
    pendiente("sep-int", SEP, Concepto.INTERES, 1_500),
    pendiente("ago-res", AGO, Concepto.RESERVA, 5_000),
]


def test_pago_parcial_cubre_lo_mas_antiguo_y_dentro_del_periodo_interes_primero() -> None:
    resultado = aplicar_pago(110_000, PENDIENTES)
    assert resultado.aplicaciones == (
        Aplicacion("ago-res", 5_000),
        Aplicacion("ago-gc", 100_000),
        Aplicacion("sep-int", 1_500),
        Aplicacion("sep-res", 3_500),
    )
    assert resultado.saldo_a_favor_clp == 0


def test_pago_mayor_a_la_deuda_deja_saldo_a_favor() -> None:
    resultado = aplicar_pago(250_000, PENDIENTES)
    assert sum(a.monto_clp for a in resultado.aplicaciones) == 211_500
    assert resultado.saldo_a_favor_clp == 38_500


def test_pago_sin_deuda_queda_completo_a_favor() -> None:
    resultado = aplicar_pago(20_000, [])
    assert resultado.aplicaciones == ()
    assert resultado.saldo_a_favor_clp == 20_000


@pytest.mark.parametrize("monto", [0, -1, 10.5, True])
def test_monto_de_pago_invalido(monto: object) -> None:
    with pytest.raises(ValueError):
        aplicar_pago(monto, PENDIENTES)  # type: ignore[arg-type]


def test_cargo_pendiente_exige_saldo_positivo() -> None:
    with pytest.raises(ValueError):
        pendiente("x", SEP, Concepto.GASTO_COMUN, 0)


def test_anular_un_pago_restituye_la_deuda_exacta() -> None:
    """Caso que bloquea un piloto (sección 14)."""
    montos = {c.id: c.saldo_clp for c in PENDIENTES}
    pago = aplicar_pago(110_000, PENDIENTES)
    registradas = [AplicacionRegistrada("p1", a.cargo_id, a.monto_clp) for a in pago.aplicaciones]

    saldos = saldos_por_cargo(montos, registradas)
    assert saldos["ago-gc"] == 0
    assert saldos["sep-res"] == 1_500

    assert saldos_por_cargo(montos, registradas, pagos_anulados={"p1"}) == montos


def test_saldos_rechaza_sobreaplicacion_y_cargos_desconocidos() -> None:
    with pytest.raises(ValueError, match="más pagos"):
        saldos_por_cargo({"c": 10}, [AplicacionRegistrada("p", "c", 11)])
    with pytest.raises(ValueError, match="desconocido"):
        saldos_por_cargo({"c": 10}, [AplicacionRegistrada("p", "z", 1)])


cargos_st = st.lists(
    st.builds(
        pendiente,
        id=st.uuids().map(str),
        periodo=st.sampled_from([AGO, SEP, OCT]),
        concepto=st.sampled_from(list(Concepto)),
        saldo=st.integers(min_value=1, max_value=500_000),
    ),
    max_size=15,
    unique_by=lambda c: c.id,
)


@given(cargos=cargos_st, pagos=st.lists(st.integers(min_value=1, max_value=900_000), max_size=5))
def test_pagos_sucesivos_y_anulacion_del_ultimo(
    cargos: list[CargoPendiente], pagos: list[int]
) -> None:
    montos = {c.id: c.saldo_clp for c in cargos}
    por_id = {c.id: c for c in cargos}
    registradas: list[AplicacionRegistrada] = []
    historial = [montos]

    for n, monto in enumerate(pagos):
        saldos = saldos_por_cargo(montos, registradas)
        pendientes = [
            CargoPendiente(i, por_id[i].periodo, por_id[i].concepto, s, por_id[i].vencimiento)
            for i, s in saldos.items()
            if s > 0
        ]
        resultado = aplicar_pago(monto, pendientes)

        aplicado = sum(a.monto_clp for a in resultado.aplicaciones)
        assert aplicado + resultado.saldo_a_favor_clp == monto
        assert aplicado == min(monto, sum(saldos.values()))

        registradas += [
            AplicacionRegistrada(f"p{n}", a.cargo_id, a.monto_clp) for a in resultado.aplicaciones
        ]
        historial.append(saldos_por_cargo(montos, registradas))

    if pagos:
        ultimo = f"p{len(pagos) - 1}"
        assert saldos_por_cargo(montos, registradas, pagos_anulados={ultimo}) == historial[-2]


def test_morosidad_y_cuotas_impagas_discontinuas() -> None:
    corte = date(2026, 10, 15)
    cargos = [
        pendiente("jun", date(2026, 6, 1), Concepto.GASTO_COMUN, 1),
        pendiente("ago", AGO, Concepto.RESERVA, 1),
        pendiente("sep-int", SEP, Concepto.INTERES, 1),  # interés solo: no es cuota
        pendiente("oct", OCT, Concepto.GASTO_COMUN, 1),  # vence el 10-10: vencido al 15-10
        pendiente("nov", date(2026, 11, 1), Concepto.GASTO_COMUN, 1),  # aún no vence
    ]
    assert es_morosa(cargos, corte)
    assert cuotas_impagas(cargos, corte) == 3
    assert elegible_convenio_o_suspension(cargos, corte)
    assert not elegible_convenio_o_suspension(cargos[:3], corte)
    assert not es_morosa(cargos[-1:], corte)
