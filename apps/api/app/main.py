"""Aplicación FastAPI de SGCH. Prefijo `/api/v1`; `/health` fuera del prefijo."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Configuracion
from app.core.errores import registrar_manejadores
from app.core.solicitud import RequestIdMiddleware, configurar_logs
from app.db.sesion import Bd, BdPostgres
from app.routers import administracion, me, salud
from app.utils.formato import ZONA_NEGOCIO


def hoy_santiago() -> date:
    return datetime.now(UTC).astimezone(ZONA_NEGOCIO).date()


def crear_app(
    config: Configuracion | None = None,
    bd: Bd | None = None,
    reloj: Callable[[], date] = hoy_santiago,
) -> FastAPI:
    configurar_logs()
    config = config or Configuracion()

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI) -> AsyncIterator[None]:
        propia = bd is None
        app.state.bd = BdPostgres(config.database_url) if propia else bd
        try:
            yield
        finally:
            if propia and isinstance(app.state.bd, BdPostgres):
                await app.state.bd.cerrar()

    app = FastAPI(title="SGCH API", version="0.1.0", lifespan=ciclo_de_vida)
    app.state.config = config
    app.state.reloj = reloj
    if bd is not None:
        app.state.bd = bd  # disponible también sin ciclo de vida (pruebas)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "X-Organizacion-Id",
            "X-Request-ID",
        ],
        expose_headers=["X-Request-ID", "Idempotent-Replayed"],
    )
    app.add_middleware(RequestIdMiddleware)
    registrar_manejadores(app)

    app.include_router(salud.router)
    app.include_router(me.router, prefix="/api/v1")
    app.include_router(administracion.router, prefix="/api/v1")
    return app


app = crear_app()
