"""Idempotencia de las operaciones de dinero (sección 11).

La fila de `idempotencia` se inserta en la misma transacción que la operación y guarda su
respuesta. Un reintento con la misma clave devuelve esa respuesta sin repetir el efecto; una
transacción concurrente con la misma clave espera a que la primera termine (índice único).
Si la operación falla, la transacción se revierte y la clave queda libre para reintentar.
"""

import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.contexto import Contexto
from app.core.errores import ErrorApi


@dataclass(frozen=True)
class Respuesta:
    status: int
    cuerpo: dict[str, Any]


def calcular_huella(operacion: str, datos: dict[str, Any]) -> str:
    canonico = json.dumps(
        {"operacion": operacion, "datos": jsonable_encoder(datos)},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonico.encode()).hexdigest()


async def ejecutar_idempotente(
    conn: AsyncConnection,
    ctx: Contexto,
    clave: str | None,
    operacion: str,
    datos: dict[str, Any],
    ejecutar: Callable[[], Awaitable[Respuesta]],
) -> tuple[Respuesta, bool]:
    """Devuelve la respuesta y si es una repetición de una operación ya hecha."""
    if clave is None or not clave.strip():
        raise ErrorApi(
            400,
            "falta_idempotency_key",
            "Las operaciones de dinero exigen la cabecera Idempotency-Key.",
        )
    if len(clave) > 255:
        raise ErrorApi(
            400, "idempotency_key_invalida", "La Idempotency-Key supera los 255 caracteres."
        )

    huella = calcular_huella(operacion, datos)
    insertada = (
        await conn.execute(
            text(
                "insert into idempotencia (organizacion_id, clave, operacion, huella) "
                "values (:o, :k, :op, :h) "
                "on conflict (organizacion_id, clave) do nothing returning id"
            ),
            {"o": ctx.organizacion_id, "k": clave, "op": operacion, "h": huella},
        )
    ).first()

    if insertada is None:
        previa = (
            await conn.execute(
                text(
                    "select huella, codigo_http, respuesta from idempotencia "
                    "where organizacion_id = :o and clave = :k"
                ),
                {"o": ctx.organizacion_id, "k": clave},
            )
        ).one()
        if previa.huella != huella or previa.codigo_http is None:
            raise ErrorApi(
                409,
                "idempotency_key_reutilizada",
                "La Idempotency-Key ya se usó con otra solicitud.",
            )
        return Respuesta(previa.codigo_http, previa.respuesta), True

    respuesta = await ejecutar()
    await conn.execute(
        text(
            "update idempotencia set codigo_http = :c, respuesta = cast(:r as jsonb) where id = :id"
        ),
        {
            "c": respuesta.status,
            "r": json.dumps(jsonable_encoder(respuesta.cuerpo)),
            "id": insertada.id,
        },
    )
    return respuesta, False
