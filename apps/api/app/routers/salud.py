from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.contexto import obtener_bd
from app.db.sesion import Bd

router = APIRouter()


@router.get("/health", include_in_schema=False)
async def health(bd: Annotated[Bd, Depends(obtener_bd)]) -> JSONResponse:
    try:
        async with bd.transaccion() as conn:
            await conn.execute(text("select 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "sin_base_de_datos"})
    return JSONResponse(content={"status": "ok"})
