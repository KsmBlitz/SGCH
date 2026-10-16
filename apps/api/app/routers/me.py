from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text

from app.core.contexto import BdDep, usuario_autenticado

router = APIRouter(tags=["me"])


@router.get("/me")
async def me(
    usuario_id: Annotated[UUID, Depends(usuario_autenticado)], bd: BdDep
) -> dict[str, Any]:
    """Usuario, organizaciones, roles y comunidades accesibles."""
    async with bd.transaccion() as conn:
        organizaciones = (
            await conn.execute(
                text(
                    "select o.id, o.nombre, m.rol from miembros_organizacion m "
                    "join organizaciones o on o.id = m.organizacion_id "
                    "where m.usuario_id = :u order by o.nombre"
                ),
                {"u": usuario_id},
            )
        ).all()
        como_equipo = (
            await conn.execute(
                text(
                    "select c.id, c.nombre, c.organizacion_id, m.rol, null::uuid as unidad_id "
                    "from comunidades c join miembros_organizacion m "
                    "on m.organizacion_id = c.organizacion_id where m.usuario_id = :u"
                ),
                {"u": usuario_id},
            )
        ).all()
        por_acceso = (
            await conn.execute(
                text(
                    "select c.id, c.nombre, c.organizacion_id, a.rol, a.unidad_id "
                    "from accesos_comunidad a join comunidades c on c.id = a.comunidad_id "
                    "where a.usuario_id = :u"
                ),
                {"u": usuario_id},
            )
        ).all()
    cuerpo: dict[str, Any] = jsonable_encoder(
        {
            "usuario_id": usuario_id,
            "organizaciones": [
                {"id": o.id, "nombre": o.nombre, "rol": o.rol} for o in organizaciones
            ],
            "comunidades": [
                {
                    "id": c.id,
                    "nombre": c.nombre,
                    "organizacion_id": c.organizacion_id,
                    "rol": c.rol,
                    "unidad_id": c.unidad_id,
                }
                for c in [*como_equipo, *por_acceso]
            ],
        }
    )
    return cuerpo
