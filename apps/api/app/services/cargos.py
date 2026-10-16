"""Tipos compartidos por el cierre, la cobranza y los intereses (glosario, sección 7)."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class Concepto(StrEnum):
    """Valores de `cargos.concepto` (sección 10)."""

    GASTO_COMUN = "gasto_comun"
    RESERVA = "reserva"
    EXTRAORDINARIO = "extraordinario"
    INTERES = "interes"
    MULTA = "multa"
    AJUSTE = "ajuste"


@dataclass(frozen=True)
class Cargo:
    """Línea de deuda de una unidad en un cierre."""

    unidad: str
    concepto: Concepto
    monto_clp: int
    # Gasto extraordinario que originó el cargo, si corresponde.
    referencia: str | None = None


@dataclass(frozen=True)
class CargoPendiente:
    """Cargo ya emitido con saldo por pagar."""

    id: str
    periodo: date  # primer día del mes contable
    concepto: Concepto
    saldo_clp: int
    vencimiento: date

    def __post_init__(self) -> None:
        if self.saldo_clp <= 0:
            raise ValueError("Un cargo pendiente debe tener saldo positivo.")

    def vencido_al(self, fecha_corte: date) -> bool:
        return self.vencimiento < fecha_corte
