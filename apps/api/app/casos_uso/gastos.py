"""Gastos del período (sección 8). Solo se registran o anulan mientras el período está abierto;
la base lo hace cumplir con un trigger."""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.casos_uso.periodos import comunidad_de_la_organizacion
from app.core.contexto import Contexto
from app.core.errores import ErrorApi


async def registrar_gasto(
    conn: AsyncConnection,
    ctx: Contexto,
    comunidad_id: UUID,
    mes: date,
    datos: dict[str, Any],
    aprobar: bool,
) -> dict[str, Any]:
    await comunidad_de_la_organizacion(conn, ctx, comunidad_id)
    periodo = (
        await conn.execute(
            text(
                "select id from periodos where comunidad_id = :c and mes = :m "
                "and organizacion_id = :o"
            ),
            {"c": comunidad_id, "m": mes, "o": ctx.organizacion_id},
        )
    ).first()
    if periodo is None:
        raise ErrorApi(404, "no_encontrado", "El período no existe.")
    if aprobar and datos["tipo"] != "extraordinario":
        raise ErrorApi(422, "regla_de_negocio", "Solo los gastos extraordinarios se aprueban.")

    gasto_id: UUID = (
        await conn.execute(
            text(
                "insert into gastos (organizacion_id, comunidad_id, periodo_id, tipo, categoria, "
                "descripcion, monto_clp, fecha, proveedor_id, comprobante_path, "
                "grupo_prorrateo_id, "
                "aprobado_en, aprobado_por, creado_por) "
                "values (:o, :c, :p, :tipo, :categoria, :descripcion, :monto_clp, :fecha, "
                ":proveedor_id, :comprobante_path, :grupo_prorrateo_id, "
                "case when :aprobar then now() end, "
                "case when :aprobar then cast(:por as uuid) end, "
                ":por) returning id"
            ),
            {
                **datos,
                "o": ctx.organizacion_id,
                "c": comunidad_id,
                "p": periodo.id,
                "aprobar": aprobar,
                "por": ctx.usuario_id,
            },
        )
    ).scalar_one()
    return {"gasto_id": gasto_id, "periodo_id": periodo.id, "aprobado": aprobar}


async def anular_gasto(
    conn: AsyncConnection, ctx: Contexto, gasto_id: UUID, motivo: str
) -> dict[str, Any]:
    gasto = (
        await conn.execute(
            text(
                "select id, anulado_en from gastos "
                "where id = :g and organizacion_id = :o for update"
            ),
            {"g": gasto_id, "o": ctx.organizacion_id},
        )
    ).first()
    if gasto is None:
        raise ErrorApi(404, "no_encontrado", "El gasto no existe.")
    if gasto.anulado_en is not None:
        raise ErrorApi(409, "ya_anulado", "El gasto ya está anulado.")
    await conn.execute(
        text("update gastos set anulado_en = now(), anulado_por = :por, motivo = :m where id = :g"),
        {"por": ctx.usuario_id, "m": motivo, "g": gasto_id},
    )
    return {"gasto_id": gasto_id, "anulado": True}
