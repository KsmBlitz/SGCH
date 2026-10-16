"""Períodos: alta, revisión previa al cierre y cierre con cálculo de cargos (sección 8)."""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.casos_uso.pagos import aplicar_saldos_a_favor, cargos_pendientes
from app.core.contexto import Contexto
from app.core.errores import ErrorApi
from app.services.cargos import Concepto
from app.services.cierre import EntradaCierre, GastoExtraordinario, calcular_cierre
from app.services.intereses import calcular_interes


async def comunidad_de_la_organizacion(
    conn: AsyncConnection, ctx: Contexto, comunidad_id: UUID
) -> Any:
    comunidad = (
        await conn.execute(
            text(
                "select id, pct_reserva, tasa_interes_mora from comunidades "
                "where id = :c and organizacion_id = :o"
            ),
            {"c": comunidad_id, "o": ctx.organizacion_id},
        )
    ).first()
    if comunidad is None:
        raise ErrorApi(404, "no_encontrado", "La comunidad no existe.")
    return comunidad


async def crear_periodo(
    conn: AsyncConnection, ctx: Contexto, comunidad_id: UUID, mes: date
) -> dict[str, Any]:
    await comunidad_de_la_organizacion(conn, ctx, comunidad_id)
    periodo_id: UUID = (
        await conn.execute(
            text(
                "insert into periodos (organizacion_id, comunidad_id, mes) "
                "values (:o, :c, :m) returning id"
            ),
            {"o": ctx.organizacion_id, "c": comunidad_id, "m": mes},
        )
    ).scalar_one()
    return {"periodo_id": periodo_id, "comunidad_id": comunidad_id, "mes": mes, "estado": "abierto"}


async def _periodo(
    conn: AsyncConnection, ctx: Contexto, comunidad_id: UUID, mes: date, bloquear: bool
) -> Any:
    periodo = (
        await conn.execute(
            text(
                "select id, estado from periodos where comunidad_id = :c and mes = :m "
                "and organizacion_id = :o" + (" for update" if bloquear else "")
            ),
            {"c": comunidad_id, "m": mes, "o": ctx.organizacion_id},
        )
    ).first()
    if periodo is None:
        raise ErrorApi(404, "no_encontrado", "El período no existe.")
    return periodo


async def _prorrateos(conn: AsyncConnection, ctx: Contexto, comunidad_id: UUID) -> list[Any]:
    return list(
        (
            await conn.execute(
                text(
                    "select id, codigo, prorrateo, activa from unidades "
                    "where comunidad_id = :c and organizacion_id = :o order by codigo"
                ),
                {"c": comunidad_id, "o": ctx.organizacion_id},
            )
        ).all()
    )


async def _gastos_vigentes(conn: AsyncConnection, ctx: Contexto, periodo_id: UUID) -> list[Any]:
    return list(
        (
            await conn.execute(
                text(
                    "select id, tipo, monto_clp, comprobante_path, grupo_prorrateo_id, aprobado_en "
                    "from gastos where periodo_id = :p and organizacion_id = :o "
                    "and anulado_en is null order by creado_en, id"
                ),
                {"p": periodo_id, "o": ctx.organizacion_id},
            )
        ).all()
    )


async def validar_periodo(
    conn: AsyncConnection, ctx: Contexto, comunidad_id: UUID, mes: date
) -> dict[str, Any]:
    """Revisión previa al cierre: bloquea lo que impediría cerrar y advierte el resto."""
    await comunidad_de_la_organizacion(conn, ctx, comunidad_id)
    periodo = await _periodo(conn, ctx, comunidad_id, mes, bloquear=False)
    unidades = await _prorrateos(conn, ctx, comunidad_id)
    gastos = await _gastos_vigentes(conn, ctx, periodo.id)

    errores: list[dict[str, str]] = []
    advertencias: list[dict[str, Any]] = []

    if periodo.estado != "abierto":
        errores.append(
            {"code": "periodo_no_abierto", "message": f"El período está {periodo.estado}."}
        )
    suma = sum((u.prorrateo for u in unidades), Decimal(0))
    if suma != 1:
        errores.append(
            {"code": "prorrateos_no_suman_1", "message": f"Los prorrateos suman {suma}, no 1."}
        )

    for g in gastos:
        if g.tipo == "extraordinario" and g.aprobado_en is not None and g.grupo_prorrateo_id:
            suma_grupo = (
                await conn.execute(
                    text(
                        "select coalesce(sum(prorrateo), 0) from grupo_prorrateo_unidades "
                        "where grupo_id = :g"
                    ),
                    {"g": g.grupo_prorrateo_id},
                )
            ).scalar_one()
            if suma_grupo != 1:
                errores.append(
                    {
                        "code": "grupo_prorrateo_no_suma_1",
                        "message": f"El grupo del gasto {g.id} suma {suma_grupo}, no 1.",
                    }
                )

    sin_comprobante = sum(1 for g in gastos if not g.comprobante_path)
    sin_aprobar = sum(1 for g in gastos if g.tipo == "extraordinario" and g.aprobado_en is None)
    sin_prorrateo = sum(1 for u in unidades if u.activa and u.prorrateo == 0)
    if not gastos:
        advertencias.append({"code": "sin_gastos", "message": "El período no tiene gastos."})
    if sin_comprobante:
        advertencias.append(
            {
                "code": "gastos_sin_comprobante",
                "cantidad": sin_comprobante,
                "message": "Hay gastos sin comprobante.",
            }
        )
    if sin_aprobar:
        advertencias.append(
            {
                "code": "extraordinarios_sin_aprobar",
                "cantidad": sin_aprobar,
                "message": "Hay gastos extraordinarios sin aprobar: no se prorratean.",
            }
        )
    if sin_prorrateo:
        advertencias.append(
            {
                "code": "unidades_sin_prorrateo",
                "cantidad": sin_prorrateo,
                "message": "Hay unidades activas con prorrateo cero.",
            }
        )

    return {
        "periodo_id": periodo.id,
        "mes": mes,
        "estado": periodo.estado,
        "puede_cerrar": not errores,
        "errores": errores,
        "advertencias": advertencias,
    }


async def cerrar_periodo(
    conn: AsyncConnection,
    ctx: Contexto,
    comunidad_id: UUID,
    mes: date,
    vencimiento: date,
    fecha_corte: date,
) -> dict[str, Any]:
    """Congela los gastos, calcula y guarda los cargos de cada unidad y cierra el período.

    Todo ocurre en una transacción: o quedan todos los cargos y el período cerrado, o nada.
    """
    comunidad = await comunidad_de_la_organizacion(conn, ctx, comunidad_id)
    periodo = await _periodo(conn, ctx, comunidad_id, mes, bloquear=True)
    if periodo.estado != "abierto":
        raise ErrorApi(409, "periodo_no_abierto", f"El período ya está {periodo.estado}.")

    unidades = await _prorrateos(conn, ctx, comunidad_id)
    id_por_codigo = {u.codigo: u.id for u in unidades}
    general = {u.codigo: u.prorrateo for u in unidades}
    gastos = await _gastos_vigentes(conn, ctx, periodo.id)

    ordinario = sum(g.monto_clp for g in gastos if g.tipo == "ordinario")
    extraordinarios: list[GastoExtraordinario] = []
    for g in gastos:
        if g.tipo != "extraordinario" or g.aprobado_en is None:
            continue
        grupo: dict[str, Decimal] | None = None
        if g.grupo_prorrateo_id is not None:
            miembros = (
                await conn.execute(
                    text(
                        "select u.codigo, gp.prorrateo from grupo_prorrateo_unidades gp "
                        "join unidades u on u.id = gp.unidad_id where gp.grupo_id = :g"
                    ),
                    {"g": g.grupo_prorrateo_id},
                )
            ).all()
            grupo = {m.codigo: m.prorrateo for m in miembros}
        extraordinarios.append(
            GastoExtraordinario(referencia=str(g.id), monto_clp=g.monto_clp, prorrateos=grupo)
        )

    # Interés por mora sobre el saldo vencido a la fecha de corte (se cobra en este cierre).
    # Tope legal de la tasa [verificar]: aún no se aplica.
    intereses: dict[str, int] = {}
    for u in unidades:
        interes = calcular_interes(
            await cargos_pendientes(conn, ctx, u.id), fecha_corte, comunidad.tasa_interes_mora
        )
        if interes > 0:
            intereses[u.codigo] = interes

    resultado = calcular_cierre(
        EntradaCierre(
            prorrateos=general,
            gasto_ordinario_clp=ordinario,
            pct_reserva=comunidad.pct_reserva,
            extraordinarios=extraordinarios,
            intereses_clp=intereses,
        )
    )

    # Las multas y los ajustes del período ya existen como cargos propios: no se recalculan.
    esperado = (
        (ordinario if ordinario > 0 else 0)
        + (resultado.total_reserva_clp if ordinario > 0 else 0)
        + sum(e.monto_clp for e in extraordinarios)
        + sum(intereses.values())
    )
    if resultado.total_clp() != esperado:
        raise RuntimeError("La suma de cargos no iguala el total a cobrar.")

    for c in resultado.cargos:
        await conn.execute(
            text(
                "insert into cargos (organizacion_id, comunidad_id, periodo_id, unidad_id, "
                "concepto, monto_clp, vencimiento, gasto_id, creado_por) "
                "values (:o, :c, :p, :u, :concepto, :m, :v, :g, :por)"
            ),
            {
                "o": ctx.organizacion_id,
                "c": comunidad_id,
                "p": periodo.id,
                "u": id_por_codigo[c.unidad],
                "concepto": c.concepto.value,
                "m": c.monto_clp,
                "v": vencimiento,
                "g": UUID(c.referencia)
                if c.concepto is Concepto.EXTRAORDINARIO and c.referencia
                else None,
                "por": ctx.usuario_id,
            },
        )

    # La base rechaza el cierre si los prorrateos o un grupo no suman 1.
    await conn.execute(
        text(
            "update periodos set estado = 'cerrado', cerrado_en = now(), cerrado_por = :por "
            "where id = :p"
        ),
        {"por": ctx.usuario_id, "p": periodo.id},
    )

    aplicado_saldos = await aplicar_saldos_a_favor(conn, ctx, comunidad_id)

    por_concepto: dict[str, int] = defaultdict(int)
    for c in resultado.cargos:
        por_concepto[c.concepto.value] += c.monto_clp
    return {
        "periodo_id": periodo.id,
        "mes": mes,
        "estado": "cerrado",
        "cargos_creados": len(resultado.cargos),
        "total_cargos_clp": resultado.total_clp(),
        "total_por_concepto": dict(por_concepto),
        "total_reserva_clp": resultado.total_reserva_clp,
        "aplicado_de_saldos_a_favor_clp": aplicado_saldos,
    }
