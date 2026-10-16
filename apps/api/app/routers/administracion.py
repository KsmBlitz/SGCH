"""Endpoints del administrador (equipo de la organización): períodos, gastos, cierre y pagos."""

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.casos_uso import gastos as casos_gastos
from app.casos_uso import pagos as casos_pagos
from app.casos_uso import periodos as casos_periodos
from app.core.contexto import BdDep, ContextoAdmin
from app.core.errores import ErrorApi
from app.core.idempotencia import Respuesta, ejecutar_idempotente
from app.routers.respuestas import responder
from app.schemas.entradas import AnulacionIn, CierreIn, GastoIn, PagoIn, PeriodoIn
from app.utils.formato import mes_desde_texto

router = APIRouter(tags=["administracion"])

ClaveIdempotencia = Annotated[str | None, Header(alias="Idempotency-Key")]


def _mes(texto: str) -> date:
    try:
        return mes_desde_texto(texto)
    except ValueError as exc:
        raise ErrorApi(422, "validacion", str(exc)) from exc


def _hoy(request: Request) -> date:
    reloj: Callable[[], date] = request.app.state.reloj
    return reloj()


async def _idempotente(
    bd: BdDep,
    ctx: ContextoAdmin,
    clave: str | None,
    operacion: str,
    datos: dict[str, Any],
    status: int,
    accion: Callable[[Any], Awaitable[dict[str, Any]]],
) -> JSONResponse:
    async with bd.transaccion(ctx.usuario_id) as conn:

        async def ejecutar() -> Respuesta:
            return Respuesta(status, jsonable_encoder(await accion(conn)))

        respuesta, repetida = await ejecutar_idempotente(
            conn, ctx, clave, operacion, datos, ejecutar
        )
    return responder(respuesta, repetida)


@router.post("/comunidades/{comunidad_id}/periodos", status_code=201)
async def crear_periodo(
    comunidad_id: UUID, cuerpo: PeriodoIn, ctx: ContextoAdmin, bd: BdDep
) -> dict[str, Any]:
    mes = _mes(cuerpo.mes)
    async with bd.transaccion(ctx.usuario_id) as conn:
        resultado = await casos_periodos.crear_periodo(conn, ctx, comunidad_id, mes)
    salida: dict[str, Any] = jsonable_encoder(resultado)
    return salida


@router.post("/comunidades/{comunidad_id}/periodos/{mes}/gastos")
async def crear_gasto(
    comunidad_id: UUID,
    mes: str,
    cuerpo: GastoIn,
    ctx: ContextoAdmin,
    bd: BdDep,
    idempotency_key: ClaveIdempotencia = None,
) -> JSONResponse:
    fecha_mes = _mes(mes)
    datos = cuerpo.model_dump(exclude={"aprobar"})
    return await _idempotente(
        bd,
        ctx,
        idempotency_key,
        "crear_gasto",
        {"comunidad_id": comunidad_id, "mes": mes, **cuerpo.model_dump()},
        201,
        lambda conn: casos_gastos.registrar_gasto(
            conn, ctx, comunidad_id, fecha_mes, datos, cuerpo.aprobar
        ),
    )


@router.post("/gastos/{gasto_id}/anular")
async def anular_gasto(
    gasto_id: UUID,
    cuerpo: AnulacionIn,
    ctx: ContextoAdmin,
    bd: BdDep,
    idempotency_key: ClaveIdempotencia = None,
) -> JSONResponse:
    return await _idempotente(
        bd,
        ctx,
        idempotency_key,
        "anular_gasto",
        {"gasto_id": gasto_id, **cuerpo.model_dump()},
        200,
        lambda conn: casos_gastos.anular_gasto(conn, ctx, gasto_id, cuerpo.motivo),
    )


@router.post("/comunidades/{comunidad_id}/periodos/{mes}/validar")
async def validar_periodo(
    comunidad_id: UUID, mes: str, ctx: ContextoAdmin, bd: BdDep
) -> dict[str, Any]:
    fecha_mes = _mes(mes)
    async with bd.transaccion(ctx.usuario_id) as conn:
        resultado = await casos_periodos.validar_periodo(conn, ctx, comunidad_id, fecha_mes)
    salida: dict[str, Any] = jsonable_encoder(resultado)
    return salida


@router.post("/comunidades/{comunidad_id}/periodos/{mes}/cerrar")
async def cerrar_periodo(
    comunidad_id: UUID,
    mes: str,
    cuerpo: CierreIn,
    request: Request,
    ctx: ContextoAdmin,
    bd: BdDep,
    idempotency_key: ClaveIdempotencia = None,
) -> JSONResponse:
    fecha_mes = _mes(mes)
    hoy = _hoy(request)
    return await _idempotente(
        bd,
        ctx,
        idempotency_key,
        "cerrar_periodo",
        {"comunidad_id": comunidad_id, "mes": mes, **cuerpo.model_dump()},
        200,
        lambda conn: casos_periodos.cerrar_periodo(
            conn, ctx, comunidad_id, fecha_mes, cuerpo.vencimiento, hoy
        ),
    )


@router.post("/pagos")
async def registrar_pago(
    cuerpo: PagoIn, ctx: ContextoAdmin, bd: BdDep, idempotency_key: ClaveIdempotencia = None
) -> JSONResponse:
    return await _idempotente(
        bd,
        ctx,
        idempotency_key,
        "registrar_pago",
        cuerpo.model_dump(),
        201,
        lambda conn: casos_pagos.registrar_pago(
            conn,
            ctx,
            cuerpo.unidad_id,
            cuerpo.monto_clp,
            cuerpo.fecha_pago,
            cuerpo.medio,
            cuerpo.referencia,
        ),
    )


@router.post("/pagos/{pago_id}/anular")
async def anular_pago(
    pago_id: UUID,
    cuerpo: AnulacionIn,
    ctx: ContextoAdmin,
    bd: BdDep,
    idempotency_key: ClaveIdempotencia = None,
) -> JSONResponse:
    return await _idempotente(
        bd,
        ctx,
        idempotency_key,
        "anular_pago",
        {"pago_id": pago_id, **cuerpo.model_dump()},
        200,
        lambda conn: casos_pagos.anular_pago(conn, ctx, pago_id, cuerpo.motivo),
    )
