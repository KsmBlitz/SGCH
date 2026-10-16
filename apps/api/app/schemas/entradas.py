"""Cuerpos de entrada. Los montos CLP son enteros estrictos (nunca float ni bool)."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints

# La columna es `integer` de 32 bits.
MAX_CLP = 2_147_483_647

MontoClp = Annotated[StrictInt, Field(gt=0, le=MAX_CLP)]
Motivo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PeriodoIn(Entrada):
    mes: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$", description="aaaa-mm")


class GastoIn(Entrada):
    tipo: Literal["ordinario", "extraordinario"]
    categoria: Texto
    descripcion: Texto
    monto_clp: MontoClp
    fecha: date
    proveedor_id: UUID | None = None
    comprobante_path: str | None = Field(default=None, max_length=500)
    grupo_prorrateo_id: UUID | None = None
    # Solo extraordinarios: aprobado para prorratear en el cierre.
    aprobar: bool = False


class CierreIn(Entrada):
    # Fecha de vencimiento de los cargos que genera el cierre.
    vencimiento: date


class PagoIn(Entrada):
    unidad_id: UUID
    monto_clp: MontoClp
    fecha_pago: date
    medio: Literal["transferencia", "efectivo", "cheque", "tarjeta", "otro"]
    referencia: str | None = Field(default=None, max_length=200)


class AnulacionIn(Entrada):
    motivo: Motivo
