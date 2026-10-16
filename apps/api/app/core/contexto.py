"""Usuario y organización de cada solicitud, resueltos desde el JWT (regla 5 de CLAUDE.md).

Esta es la única barrera de aislamiento de la API: el rol de conexión omite RLS, así que toda
consulta recibe `Contexto.organizacion_id` y filtra por él.
"""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy import text

from app.core.config import Configuracion
from app.core.errores import ErrorApi
from app.core.seguridad import usuario_desde_token
from app.db.sesion import Bd


@dataclass(frozen=True)
class Contexto:
    usuario_id: UUID
    organizacion_id: UUID
    rol: str  # owner | staff


def obtener_config(request: Request) -> Configuracion:
    config: Configuracion = request.app.state.config
    return config


def obtener_bd(request: Request) -> Bd:
    bd: Bd = request.app.state.bd
    return bd


async def usuario_autenticado(
    config: Annotated[Configuracion, Depends(obtener_config)],
    authorization: Annotated[str | None, Header()] = None,
) -> UUID:
    esquema, _, token = (authorization or "").partition(" ")
    if esquema.lower() != "bearer" or not token:
        raise ErrorApi(401, "no_autenticado", "Token inválido o ausente.")
    return await usuario_desde_token(token, config)


async def contexto_admin(
    usuario_id: Annotated[UUID, Depends(usuario_autenticado)],
    bd: Annotated[Bd, Depends(obtener_bd)],
    x_organizacion_id: Annotated[UUID | None, Header()] = None,
) -> Contexto:
    """Equipo del administrador (owner o staff). Si pertenece a varias organizaciones, debe
    indicar cuál con `X-Organizacion-Id`; la pertenencia siempre se verifica en la base."""
    async with bd.transaccion() as conn:
        filas = (
            await conn.execute(
                text(
                    "select organizacion_id, rol from miembros_organizacion where usuario_id = :u"
                ),
                {"u": usuario_id},
            )
        ).all()
    if not filas:
        raise ErrorApi(403, "prohibido", "El usuario no pertenece a una organización.")
    if x_organizacion_id is not None:
        elegidas = [f for f in filas if f.organizacion_id == x_organizacion_id]
        if not elegidas:
            raise ErrorApi(403, "prohibido", "El usuario no pertenece a esa organización.")
        fila = elegidas[0]
    elif len(filas) == 1:
        fila = filas[0]
    else:
        raise ErrorApi(
            400, "organizacion_requerida", "Indica la organización con X-Organizacion-Id."
        )
    return Contexto(usuario_id=usuario_id, organizacion_id=fila.organizacion_id, rol=fila.rol)


ContextoAdmin = Annotated[Contexto, Depends(contexto_admin)]
BdDep = Annotated[Bd, Depends(obtener_bd)]
