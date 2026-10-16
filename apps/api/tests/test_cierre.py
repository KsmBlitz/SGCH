import random
from decimal import Decimal
from fractions import Fraction
from math import ceil, floor

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.services.cargos import Cargo, Concepto
from app.services.cierre import (
    CierreInvalidoError,
    EntradaCierre,
    GastoExtraordinario,
    calcular_cierre,
    calcular_total_reserva,
)
from app.services.prorrateo import ProrrateoInvalidoError, normalizar_prorrateos
from tests.comunidad_ficticia import GASTO_ORDINARIO_CLP, PRORRATEOS, PRORRATEOS_TORRE_B

D = Decimal


def test_caso_tabulado_a_mano() -> None:
    """Tres unidades (50%, 25%, 25%), gasto ordinario $10 y reserva 5%.

    Gasto común exacto 5 / 2,5 / 2,5 -> 5 / 3 / 2 (empate: gana la primera por código).
    Reserva total techo(0,5) = 1 -> 0,5 / 0,25 / 0,25 -> 1 / 0 / 0.
    """
    resultado = calcular_cierre(
        EntradaCierre(
            prorrateos={"u1": D("0.5"), "u2": D("0.25"), "u3": D("0.25")},
            gasto_ordinario_clp=10,
            pct_reserva=D("0.05"),
        )
    )
    assert resultado.cargos == (
        Cargo("u1", Concepto.GASTO_COMUN, 5),
        Cargo("u2", Concepto.GASTO_COMUN, 3),
        Cargo("u3", Concepto.GASTO_COMUN, 2),
        Cargo("u1", Concepto.RESERVA, 1),
    )
    assert resultado.total_clp() == 11


@pytest.mark.parametrize(
    ("gasto", "pct", "esperado"),
    [
        (1_968_720, D("0.05"), 98_436),  # exacto
        (1_968_720, D("0.07"), 137_811),  # 137.810,4 -> techo
        (19, D("0.05"), 1),  # 0,95 -> techo, nunca bajo el porcentaje
        (0, D("0.05"), 0),
    ],
)
def test_total_reserva_usa_techo(gasto: int, pct: Decimal, esperado: int) -> None:
    assert calcular_total_reserva(gasto, pct) == esperado
    assert calcular_total_reserva(gasto, pct) >= gasto * Fraction(pct)


def test_mes_de_la_comunidad_ficticia() -> None:
    entrada = EntradaCierre(
        prorrateos=PRORRATEOS,
        gasto_ordinario_clp=GASTO_ORDINARIO_CLP,
        pct_reserva=D("0.05"),
        extraordinarios=[
            GastoExtraordinario("pintura-fachada", 3_200_000),
            GastoExtraordinario("reparacion-ascensor-b", 1_450_000, PRORRATEOS_TORRE_B),
        ],
        intereses_clp={"A-302": 2_847},
        multas_clp={"B-101": 15_000},
    )
    resultado = calcular_cierre(entrada)

    # Cada concepto cuadra al peso por sí solo.
    assert resultado.total_por_concepto() == {
        Concepto.GASTO_COMUN: 1_968_720,
        Concepto.RESERVA: 98_436,
        Concepto.EXTRAORDINARIO: 3_200_000 + 1_450_000,
        Concepto.INTERES: 2_847,
        Concepto.MULTA: 15_000,
    }
    assert resultado.total_clp() == 1_968_720 + 98_436 + 4_650_000 + 2_847 + 15_000

    # La reparación del ascensor de la torre B no se cobra en la torre A.
    ascensor = [c for c in resultado.cargos if c.referencia == "reparacion-ascensor-b"]
    assert {c.unidad[0] for c in ascensor} == {"B"}
    assert sum(c.monto_clp for c in ascensor) == 1_450_000

    # Cada cargo de gasto común es el piso o el techo de su parte exacta.
    for c in resultado.cargos:
        if c.concepto is Concepto.GASTO_COMUN:
            exacta = GASTO_ORDINARIO_CLP * Fraction(PRORRATEOS[c.unidad])
            assert c.monto_clp in (floor(exacta), ceil(exacta))


def test_orden_de_entrada_no_cambia_el_resultado() -> None:
    unidades = list(PRORRATEOS.items())
    random.Random(42).shuffle(unidades)
    base = EntradaCierre(
        prorrateos=PRORRATEOS, gasto_ordinario_clp=1_000_003, pct_reserva=D("0.05")
    )
    revuelta = EntradaCierre(
        prorrateos=dict(unidades), gasto_ordinario_clp=1_000_003, pct_reserva=D("0.05")
    )
    assert calcular_cierre(base) == calcular_cierre(revuelta)


def test_unidad_con_prorrateo_cero_en_un_grupo_no_recibe_cargo() -> None:
    resultado = calcular_cierre(
        EntradaCierre(
            prorrateos={"u1": D("0.5"), "u2": D("0.5")},
            gasto_ordinario_clp=0,
            pct_reserva=D("0.05"),
            extraordinarios=[GastoExtraordinario("x", 101, {"u1": D("1"), "u2": D("0")})],
        )
    )
    assert resultado.cargos == (Cargo("u1", Concepto.EXTRAORDINARIO, 101, "x"),)


def _entrada(**cambios: object) -> EntradaCierre:
    datos: dict[str, object] = {
        "prorrateos": {"u1": D("0.5"), "u2": D("0.5")},
        "gasto_ordinario_clp": 1000,
        "pct_reserva": D("0.05"),
    }
    datos.update(cambios)
    return EntradaCierre(**datos)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("entrada", "error"),
    [
        (_entrada(prorrateos={"u1": D("0.5"), "u2": D("0.4")}), ProrrateoInvalidoError),
        (_entrada(gasto_ordinario_clp=-1), CierreInvalidoError),
        (_entrada(pct_reserva=D("0.049")), CierreInvalidoError),
        (_entrada(extraordinarios=[GastoExtraordinario("x", 0)]), CierreInvalidoError),
        (
            _entrada(extraordinarios=[GastoExtraordinario("x", 1), GastoExtraordinario("x", 2)]),
            CierreInvalidoError,
        ),
        (
            _entrada(extraordinarios=[GastoExtraordinario("x", 10, {"u9": D("1")})]),
            CierreInvalidoError,
        ),
        (
            _entrada(extraordinarios=[GastoExtraordinario("x", 10, {"u1": D("0.9")})]),
            ProrrateoInvalidoError,
        ),
        (_entrada(intereses_clp={"u9": 10}), CierreInvalidoError),
        (_entrada(multas_clp={"u1": -10}), CierreInvalidoError),
    ],
)
def test_entradas_que_impiden_cerrar(entrada: EntradaCierre, error: type[Exception]) -> None:
    with pytest.raises(error):
        calcular_cierre(entrada)


@st.composite
def entradas_cierre(draw: st.DrawFn) -> EntradaCierre:
    n = draw(st.integers(min_value=1, max_value=40))
    superficies = draw(st.lists(st.integers(min_value=1, max_value=500), min_size=n, max_size=n))
    prorrateos = normalizar_prorrateos({f"U-{i:03d}": m2 for i, m2 in enumerate(superficies)})
    unidades = list(prorrateos)
    montos = st.integers(min_value=0, max_value=50_000)
    return EntradaCierre(
        prorrateos=prorrateos,
        gasto_ordinario_clp=draw(st.integers(min_value=0, max_value=10**9)),
        pct_reserva=draw(st.decimals(min_value=D("0.05"), max_value=D("0.30"), places=4)),
        extraordinarios=[
            GastoExtraordinario(f"ext-{i}", monto)
            for i, monto in enumerate(
                draw(st.lists(st.integers(min_value=1, max_value=10**8), max_size=3))
            )
        ],
        intereses_clp=draw(st.dictionaries(st.sampled_from(unidades), montos)),
        multas_clp=draw(st.dictionaries(st.sampled_from(unidades), montos)),
    )


@given(entrada=entradas_cierre())
def test_suma_de_cargos_iguala_gastos_mas_reserva(entrada: EntradaCierre) -> None:
    """Caso que bloquea un piloto (sección 14)."""
    resultado = calcular_cierre(entrada)
    esperado = (
        entrada.gasto_ordinario_clp
        + calcular_total_reserva(entrada.gasto_ordinario_clp, entrada.pct_reserva)
        + sum(g.monto_clp for g in entrada.extraordinarios)
        + sum(entrada.intereses_clp.values())
        + sum(entrada.multas_clp.values())
    )
    assert resultado.total_clp() == esperado
    assert resultado.total_reserva_clp >= entrada.gasto_ordinario_clp * entrada.pct_reserva
    assert all(c.monto_clp > 0 for c in resultado.cargos)
    assert calcular_cierre(entrada) == resultado
