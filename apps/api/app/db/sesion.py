"""Acceso a la base: SQL explícito con SQLAlchemy Core (ADR 0005), una transacción por solicitud."""

from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine


class Bd(Protocol):
    def transaccion(
        self, usuario_id: UUID | None = None
    ) -> AbstractAsyncContextManager[AsyncConnection]:
        """Abre una transacción que confirma al salir y se revierte si hay una excepción."""
        ...


async def declarar_usuario(conn: AsyncConnection, usuario_id: UUID | None) -> None:
    """La auditoría toma de aquí al autor del cambio (`usuario_actual()` en la base)."""
    if usuario_id is not None:
        await conn.execute(
            text("select set_config('app.usuario_id', :u, true)"), {"u": str(usuario_id)}
        )


class BdPostgres:
    def __init__(self, url: str) -> None:
        # prepare_threshold=None: compatible con el pooler de transacciones de Supabase.
        self.motor: AsyncEngine = create_async_engine(
            url, connect_args={"prepare_threshold": None}, pool_pre_ping=True
        )

    @asynccontextmanager
    async def transaccion(self, usuario_id: UUID | None = None) -> AsyncIterator[AsyncConnection]:
        async with self.motor.begin() as conn:
            await declarar_usuario(conn, usuario_id)
            yield conn

    async def cerrar(self) -> None:
        await self.motor.dispose()
