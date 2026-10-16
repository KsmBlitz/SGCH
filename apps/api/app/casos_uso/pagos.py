"""Registro, aplicación y anulación de pagos (sección 8). La imputación la decide
`services.cobranza.aplicar_pago`; aquí solo se lee la deuda y se persiste el resultado."""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.contexto import Contexto
from app.core.errores import ErrorApi
from app.services.cargos import CargoPendiente, Concepto
from app.services.cobranza import ResultadoAplicacion, aplicar_pago

# Saldo de un cargo = monto menos las aplicaciones vigentes (los pagos anulados no cuentan).
_APLICADO_CARGO = (
    "left join lateral (select sum(ap.monto_clp) as aplicado from aplicaciones_pago ap "
    "where ap.cargo_id = c.id and ap.anulado_en is null) a on true"
)


async def bloquear_unidad(conn: AsyncConnection, ctx: Contexto, unidad_id: UUID) -> Any:
    """Serializa los movimientos de dinero de una unidad. 404 si no es de la organización."""
    unidad = (
        await conn.execute(
            text(
                "select id, comunidad_id from unidades "
                "where id = :u and organizacion_id = :o for update"
            ),
            {"u": unidad_id, "o": ctx.organizacion_id},
        )
    ).first()
    if unidad is None:
        raise ErrorApi(404, "no_encontrado", "La unidad no existe.")
    return unidad


async def cargos_pendientes(
    conn: AsyncConnection, ctx: Contexto, unidad_id: UUID
) -> list[CargoPendiente]:
    """Cargos con saldo por pagar de períodos cerrados o emitidos."""
    filas = (
        await conn.execute(
            text(
                "select c.id, p.mes, c.concepto, c.vencimiento, "
                "c.monto_clp - coalesce(a.aplicado, 0) as saldo "
                f"from cargos c join periodos p on p.id = c.periodo_id {_APLICADO_CARGO} "
                "where c.unidad_id = :u and c.organizacion_id = :o and c.anulado_en is null "
                "and c.monto_clp > 0 and p.estado in ('cerrado', 'emitido') "
                "and c.monto_clp - coalesce(a.aplicado, 0) > 0"
            ),
            {"u": unidad_id, "o": ctx.organizacion_id},
        )
    ).all()
    return [
        CargoPendiente(
            id=str(f.id),
            periodo=f.mes,
            concepto=Concepto(f.concepto),
            saldo_clp=int(f.saldo),
            vencimiento=f.vencimiento,
        )
        for f in filas
    ]


async def aplicar_a_deuda(
    conn: AsyncConnection,
    ctx: Contexto,
    unidad: Any,
    pago_id: UUID,
    monto_clp: int,
) -> ResultadoAplicacion:
    """Aplica `monto_clp` del pago a la deuda de la unidad y guarda las aplicaciones."""
    resultado = aplicar_pago(monto_clp, await cargos_pendientes(conn, ctx, unidad.id))
    for ap in resultado.aplicaciones:
        await conn.execute(
            text(
                "insert into aplicaciones_pago (organizacion_id, comunidad_id, unidad_id, pago_id, "
                "cargo_id, monto_clp, creado_por) values (:o, :c, :u, :p, :cargo, :m, :por)"
            ),
            {
                "o": ctx.organizacion_id,
                "c": unidad.comunidad_id,
                "u": unidad.id,
                "p": pago_id,
                "cargo": UUID(ap.cargo_id),
                "m": ap.monto_clp,
                "por": ctx.usuario_id,
            },
        )
    return resultado


async def registrar_pago(
    conn: AsyncConnection,
    ctx: Contexto,
    unidad_id: UUID,
    monto_clp: int,
    fecha_pago: date,
    medio: str,
    referencia: str | None,
) -> dict[str, Any]:
    unidad = await bloquear_unidad(conn, ctx, unidad_id)
    pago_id: UUID = (
        await conn.execute(
            text(
                "insert into pagos (organizacion_id, comunidad_id, unidad_id, monto_clp, "
                "fecha_pago, "
                "medio, origen, referencia, creado_por) "
                "values (:o, :c, :u, :m, :f, :medio, 'manual', :ref, :por) returning id"
            ),
            {
                "o": ctx.organizacion_id,
                "c": unidad.comunidad_id,
                "u": unidad.id,
                "m": monto_clp,
                "f": fecha_pago,
                "medio": medio,
                "ref": referencia,
                "por": ctx.usuario_id,
            },
        )
    ).scalar_one()
    resultado = await aplicar_a_deuda(conn, ctx, unidad, pago_id, monto_clp)
    return {
        "pago_id": pago_id,
        "unidad_id": unidad.id,
        "monto_clp": monto_clp,
        "aplicaciones": [
            {"cargo_id": a.cargo_id, "monto_clp": a.monto_clp} for a in resultado.aplicaciones
        ],
        "saldo_a_favor_clp": resultado.saldo_a_favor_clp,
    }


async def anular_pago(
    conn: AsyncConnection, ctx: Contexto, pago_id: UUID, motivo: str
) -> dict[str, Any]:
    pago = (
        await conn.execute(
            text(
                "select id, unidad_id, anulado_en from pagos "
                "where id = :p and organizacion_id = :o for update"
            ),
            {"p": pago_id, "o": ctx.organizacion_id},
        )
    ).first()
    if pago is None:
        raise ErrorApi(404, "no_encontrado", "El pago no existe.")
    if pago.anulado_en is not None:
        raise ErrorApi(409, "ya_anulado", "El pago ya está anulado.")
    await bloquear_unidad(conn, ctx, pago.unidad_id)
    restituido = (
        await conn.execute(
            text(
                "select coalesce(sum(monto_clp), 0) from aplicaciones_pago "
                "where pago_id = :p and anulado_en is null"
            ),
            {"p": pago_id},
        )
    ).scalar_one()
    # El trigger de la base anula también las aplicaciones y la deuda vuelve exacta.
    await conn.execute(
        text("update pagos set anulado_en = now(), anulado_por = :por, motivo = :m where id = :p"),
        {"por": ctx.usuario_id, "m": motivo, "p": pago_id},
    )
    return {"pago_id": pago_id, "anulado": True, "deuda_restituida_clp": int(restituido)}


async def aplicar_saldos_a_favor(conn: AsyncConnection, ctx: Contexto, comunidad_id: UUID) -> int:
    """Usa el saldo a favor (pagos con remanente sin aplicar) contra la deuda recién emitida.
    Devuelve el total aplicado."""
    remanentes = (
        await conn.execute(
            text(
                "select * from (select pg.id, pg.unidad_id, pg.fecha_pago, pg.creado_en, "
                "pg.monto_clp - coalesce((select sum(ap.monto_clp) from aplicaciones_pago ap "
                "where ap.pago_id = pg.id and ap.anulado_en is null), 0) as restante "
                "from pagos pg where pg.comunidad_id = :c and pg.organizacion_id = :o "
                "and pg.anulado_en is null) r where r.restante > 0 "
                "order by r.unidad_id, r.fecha_pago, r.creado_en, r.id"
            ),
            {"c": comunidad_id, "o": ctx.organizacion_id},
        )
    ).all()
    total = 0
    for r in remanentes:
        unidad = await bloquear_unidad(conn, ctx, r.unidad_id)
        if not await cargos_pendientes(conn, ctx, unidad.id):
            continue
        resultado = await aplicar_a_deuda(conn, ctx, unidad, r.id, int(r.restante))
        total += sum(a.monto_clp for a in resultado.aplicaciones)
    return total
