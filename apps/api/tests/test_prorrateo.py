from decimal import Decimal
from fractions import Fraction
from math import ceil, floor

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.services.prorrateo import (
    ProrrateoInvalidoError,
    normalizar_prorrateos,
    repartir,
    validar_prorrateos,
)
from tests.comunidad_ficticia import PRORRATEOS

D = Decimal


@pytest.mark.parametrize(
    ("total", "pesos", "esperado"),
    [
        # Partes exactas: no hay residuo que repartir.
        (100, [D("0.5"), D("0.3"), D("0.2")], [50, 30, 20]),
        # 33,333333 / 33,333333 / 33,333334: el peso sobrante va al mayor residuo.
        (100, [D("0.33333333"), D("0.33333333"), D("0.33333334")], [33, 33, 34]),
        # 5 / 2,5 / 2,5: empate de residuos, gana el primero en el orden de entrada.
        (10, [D("0.5"), D("0.25"), D("0.25")], [5, 3, 2]),
        # Un peso cero nunca recibe nada.
        (7, [D("0"), D("0.5"), D("0.5")], [0, 4, 3]),
        # Total negativo (por ejemplo, un ajuste a favor): simétrico al positivo.
        (-10, [D("0.5"), D("0.25"), D("0.25")], [-5, -3, -2]),
        (0, [D("0.5"), D("0.5")], [0, 0]),
        # Pesos que no suman 1 (m²): se usa la proporción.
        (1000, [625, 783, 1049], [254, 319, 427]),
    ],
)
def test_repartir_casos_tabulados(total: int, pesos: list[Decimal], esperado: list[int]) -> None:
    resultado = repartir(total, dict(enumerate(pesos)))
    assert list(resultado.values()) == esperado


pesos_st = st.lists(st.integers(min_value=0, max_value=10**6), min_size=1, max_size=60).filter(
    lambda ps: sum(ps) > 0
)


@given(total=st.integers(min_value=-(10**10), max_value=10**10), pesos=pesos_st)
def test_repartir_suma_exacta_y_cada_parte_es_piso_o_techo(total: int, pesos: list[int]) -> None:
    resultado = repartir(total, dict(enumerate(pesos)))

    assert sum(resultado.values()) == total
    suma_pesos = sum(pesos)
    for i, peso in enumerate(pesos):
        exacta = Fraction(total * peso, suma_pesos)
        assert resultado[i] in (floor(exacta), ceil(exacta))
        if peso == 0:
            assert resultado[i] == 0


@given(total=st.integers(min_value=0, max_value=10**9), pesos=pesos_st)
def test_repartir_es_reproducible(total: int, pesos: list[int]) -> None:
    entrada = dict(enumerate(pesos))
    assert repartir(total, entrada) == repartir(total, dict(entrada))


def test_repartir_rechaza_entradas_invalidas() -> None:
    with pytest.raises(TypeError):
        repartir(10.0, {"a": 1})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        repartir(True, {"a": 1})
    with pytest.raises(ValueError):
        repartir(10, {})
    with pytest.raises(ValueError):
        repartir(10, {"a": 0, "b": 0})
    with pytest.raises(ValueError):
        repartir(10, {"a": -1, "b": 2})


def test_prorrateos_de_la_comunidad_ficticia_son_validos() -> None:
    validar_prorrateos(PRORRATEOS)


@pytest.mark.parametrize(
    ("prorrateos", "mensaje"),
    [
        ({}, "No hay unidades"),
        ({"a": D("0.5"), "b": D("0.49999999")}, "suman"),
        ({"a": D("0.5"), "b": D("0.500000001")}, "decimales"),
        ({"a": D("1.5"), "b": D("-0.5")}, "fuera de rango"),
        ({"a": D("NaN")}, "fuera de rango"),
    ],
)
def test_validar_prorrateos_rechaza(prorrateos: dict[str, Decimal], mensaje: str) -> None:
    with pytest.raises(ProrrateoInvalidoError, match=mensaje):
        validar_prorrateos(prorrateos)


@given(pesos=pesos_st)
def test_normalizar_produce_prorrateos_validos(pesos: list[int]) -> None:
    normalizados = normalizar_prorrateos(dict(enumerate(pesos)))
    validar_prorrateos({str(k): v for k, v in normalizados.items()})


def test_normalizar_corrige_un_reglamento_que_suma_99_998() -> None:
    reglamento = {"a": D("0.33333"), "b": D("0.33333"), "c": D("0.33332")}
    normalizados = normalizar_prorrateos(reglamento)
    assert sum(normalizados.values()) == 1
    assert normalizados == {"a": D("0.33333667"), "b": D("0.33333667"), "c": D("0.33332666")}
