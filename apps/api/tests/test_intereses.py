from datetime import date
from decimal import Decimal

import pytest

from app.services.cargos import CargoPendiente, Concepto
from app.services.intereses import TasaInvalidaError, base_interes, calcular_interes

CORTE = date(2026, 10, 15)


def cargo(concepto: Concepto, saldo: int, vencimiento: date = date(2026, 9, 10)) -> CargoPendiente:
    return CargoPendiente(f"{concepto}-{saldo}", date(2026, 9, 1), concepto, saldo, vencimiento)


CARGOS = [
    cargo(Concepto.GASTO_COMUN, 123_457),
    cargo(Concepto.RESERVA, 6_173),
    cargo(Concepto.INTERES, 1_000),  # interés simple: no genera interés
    cargo(Concepto.MULTA, 15_000),
    cargo(Concepto.GASTO_COMUN, 120_000, vencimiento=date(2026, 10, 20)),  # no vencido
]


def test_base_excluye_intereses_multas_y_cargos_no_vencidos() -> None:
    assert base_interes(CARGOS, CORTE) == 129_630


def test_interes_se_redondea_hacia_abajo() -> None:
    # 129.630 × 1,5% = 1.944,45
    assert calcular_interes(CARGOS, CORTE, Decimal("0.015")) == 1_944


def test_sin_deuda_vencida_no_hay_interes() -> None:
    assert calcular_interes(CARGOS[-1:], CORTE, Decimal("0.015")) == 0


@pytest.mark.parametrize(
    ("tasa", "tope"),
    [(Decimal("-0.01"), None), (Decimal("NaN"), None), (Decimal("0.03"), Decimal("0.02"))],
)
def test_tasa_invalida(tasa: Decimal, tope: Decimal | None) -> None:
    with pytest.raises(TasaInvalidaError):
        calcular_interes(CARGOS, CORTE, tasa, tope)
