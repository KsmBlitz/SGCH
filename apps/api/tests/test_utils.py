from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.utils import rut
from app.utils.formato import formatear_clp, formatear_fecha


@pytest.mark.parametrize(
    ("entrada", "normalizado", "formateado"),
    [
        ("12.345.678-5", "12345678-5", "12.345.678-5"),
        ("123456785", "12345678-5", "12.345.678-5"),
        ("11.111.111-1", "11111111-1", "11.111.111-1"),
        ("1-9", "1-9", "1-9"),
    ],
)
def test_rut_valido(entrada: str, normalizado: str, formateado: str) -> None:
    assert rut.es_valido(entrada)
    assert rut.normalizar(entrada) == normalizado
    assert rut.formatear(entrada) == formateado


@pytest.mark.parametrize("entrada", ["12.345.678-4", "", "abc", "0-0", "12.345.678-", "K-1"])
def test_rut_invalido(entrada: str) -> None:
    assert not rut.es_valido(entrada)
    with pytest.raises(rut.RutInvalidoError):
        rut.normalizar(entrada)


@given(st.integers(min_value=1, max_value=99_999_999))
def test_dv_calculado_valida_y_cualquier_otro_dv_no(cuerpo: int) -> None:
    dv = rut.calcular_dv(cuerpo)
    assert rut.es_valido(f"{cuerpo}-{dv.lower()}")
    for otro in "0123456789K":
        if otro != dv:
            assert not rut.es_valido(f"{cuerpo}-{otro}")


@pytest.mark.parametrize(
    ("monto", "esperado"),
    [(0, "$0"), (999, "$999"), (1_234_567, "$1.234.567"), (-1_500, "-$1.500")],
)
def test_formatear_clp(monto: int, esperado: str) -> None:
    assert formatear_clp(monto) == esperado


def test_formatear_clp_rechaza_no_enteros() -> None:
    with pytest.raises(TypeError):
        formatear_clp(1.5)  # type: ignore[arg-type]


def test_formatear_fecha() -> None:
    assert formatear_fecha(date(2026, 3, 7)) == "07-03-2026"
