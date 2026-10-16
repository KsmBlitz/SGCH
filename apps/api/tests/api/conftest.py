"""Fixtures de integración: la API real contra la base local de Supabase.

Cada prueba corre dentro de una transacción externa que se revierte al final, y la API usa
puntos de guardado (`BdPruebas`), así que la base queda intacta. Si la base no está levantada
las pruebas se omiten, salvo con `SGCH_REQUIRE_DB=1` (CI), donde fallan.
"""

import os
import time
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

import httpx
import jwt
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Configuracion
from app.db.sesion import declarar_usuario
from app.main import crear_app

SECRETO = "secreto-solo-para-pruebas-con-largo-suficiente"
HOY = date(2026, 10, 16)


class BdPruebas:
    def __init__(self, conn: AsyncConnection) -> None:
        self.conn = conn

    @asynccontextmanager
    async def transaccion(self, usuario_id: UUID | None = None) -> AsyncIterator[AsyncConnection]:
        async with self.conn.begin_nested():
            await declarar_usuario(self.conn, usuario_id)
            yield self.conn


@dataclass
class Escenario:
    org_a: UUID
    org_b: UUID
    admin_a: UUID
    admin_b: UUID
    comite_a: UUID
    sin_org: UUID
    comunidad_a: UUID
    comunidad_b: UUID
    unidades_a: dict[str, UUID]  # A-101 (0.5), A-102 (0.3), A-103 (0.2)
    unidad_b: UUID


def token(usuario: UUID, secreto: str = SECRETO, **extra: Any) -> str:
    claims = {
        "sub": str(usuario),
        "role": "authenticated",
        "aud": "authenticated",
        "exp": int(time.time()) + 3600,
        **extra,
    }
    return jwt.encode(claims, secreto, algorithm="HS256")


def cabeceras(usuario: UUID, clave: str | None = None, **extra: str) -> dict[str, str]:
    h = {"Authorization": f"Bearer {token(usuario)}", **extra}
    if clave is not None:
        h["Idempotency-Key"] = clave
    return h


@pytest.fixture
def config() -> Configuracion:
    return Configuracion(jwt_secret=SECRETO)


@pytest.fixture
async def conn(config: Configuracion) -> AsyncIterator[AsyncConnection]:
    motor = create_async_engine(config.database_url, poolclass=NullPool)
    try:
        conexion = await motor.connect()
    except Exception as exc:
        if os.environ.get("SGCH_REQUIRE_DB") == "1":
            raise
        pytest.skip(f"Base local no disponible (make db-start): {type(exc).__name__}")
    externa = await conexion.begin()
    try:
        yield conexion
    finally:
        await externa.rollback()
        await conexion.close()
        await motor.dispose()


@pytest.fixture
async def escenario(conn: AsyncConnection) -> Escenario:
    ids = {
        n: uuid.uuid4()
        for n in (
            "org_a",
            "org_b",
            "admin_a",
            "admin_b",
            "comite_a",
            "sin_org",
            "com_a",
            "com_b",
            "u1",
            "u2",
            "u3",
            "ub",
        )
    }
    for nombre in ("admin_a", "admin_b", "comite_a", "sin_org"):
        await conn.execute(
            text(
                "insert into auth.users (id, aud, role, email) values (:i, 'authenticated', "
                "'authenticated', :e)"
            ),
            {"i": ids[nombre], "e": f"{nombre}-{ids[nombre]}@sgch.test"},
        )
    await conn.execute(
        text("insert into organizaciones (id, nombre) values (:a, 'Org A'), (:b, 'Org B')"),
        {"a": ids["org_a"], "b": ids["org_b"]},
    )
    await conn.execute(
        text(
            "insert into miembros_organizacion (organizacion_id, usuario_id, rol) values "
            "(:oa, :aa, 'owner'), (:ob, :ab, 'owner')"
        ),
        {"oa": ids["org_a"], "aa": ids["admin_a"], "ob": ids["org_b"], "ab": ids["admin_b"]},
    )
    await conn.execute(
        text(
            "insert into comunidades (id, organizacion_id, nombre, tasa_interes_mora) values "
            "(:ca, :oa, 'Comunidad A', 0.01), (:cb, :ob, 'Comunidad B', 0.01)"
        ),
        {"ca": ids["com_a"], "oa": ids["org_a"], "cb": ids["com_b"], "ob": ids["org_b"]},
    )
    await conn.execute(
        text(
            "insert into unidades (id, organizacion_id, comunidad_id, codigo, prorrateo) values "
            "(:u1, :oa, :ca, 'A-101', 0.5), (:u2, :oa, :ca, 'A-102', 0.3), "
            "(:u3, :oa, :ca, 'A-103', 0.2), (:ub, :ob, :cb, 'B-101', 1)"
        ),
        {
            "u1": ids["u1"],
            "u2": ids["u2"],
            "u3": ids["u3"],
            "ub": ids["ub"],
            "oa": ids["org_a"],
            "ob": ids["org_b"],
            "ca": ids["com_a"],
            "cb": ids["com_b"],
        },
    )
    await conn.execute(
        text(
            "insert into accesos_comunidad (organizacion_id, comunidad_id, usuario_id, rol) "
            "values (:o, :c, :u, 'comite')"
        ),
        {"o": ids["org_a"], "c": ids["com_a"], "u": ids["comite_a"]},
    )
    return Escenario(
        org_a=ids["org_a"],
        org_b=ids["org_b"],
        admin_a=ids["admin_a"],
        admin_b=ids["admin_b"],
        comite_a=ids["comite_a"],
        sin_org=ids["sin_org"],
        comunidad_a=ids["com_a"],
        comunidad_b=ids["com_b"],
        unidades_a={"A-101": ids["u1"], "A-102": ids["u2"], "A-103": ids["u3"]},
        unidad_b=ids["ub"],
    )


@pytest.fixture
async def cliente(conn: AsyncConnection, config: Configuracion) -> AsyncIterator[httpx.AsyncClient]:
    reloj: Callable[[], date] = lambda: HOY  # noqa: E731
    app = crear_app(config=config, bd=BdPruebas(conn), reloj=reloj)
    transporte = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://test") as c:
        yield c
