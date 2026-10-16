"""Autenticación, organización resuelta desde el JWT y formato de errores (sección 11)."""

import time
import uuid
from collections.abc import Callable
from uuid import UUID

import httpx
import jwt
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.api.conftest import SECRETO, Escenario, cabeceras, token

pytestmark = pytest.mark.bd


async def test_health(cliente: httpx.AsyncClient, escenario: Escenario) -> None:
    r = await cliente.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_sin_token_es_401_con_formato_unico(
    cliente: httpx.AsyncClient, escenario: Escenario
) -> None:
    r = await cliente.get("/api/v1/me")
    assert r.status_code == 401
    assert r.json() == {
        "error": {"code": "no_autenticado", "message": "Token inválido o ausente.", "details": {}}
    }


@pytest.mark.parametrize(
    "construir",
    [
        lambda u: token(u, secreto="otro-secreto-distinto-con-largo-suficiente"),
        lambda u: token(u, exp=int(time.time()) - 10),
        lambda u: token(u, aud="otra-audiencia"),
        lambda u: token(u, role="anon"),
        lambda u: jwt.encode({"sub": str(u), "role": "authenticated"}, key="", algorithm="none"),
        lambda u: "no-es-un-jwt",
    ],
    ids=["firma", "vencido", "audiencia", "rol_anon", "alg_none", "basura"],
)
async def test_tokens_invalidos_son_401(
    cliente: httpx.AsyncClient, escenario: Escenario, construir: Callable[[UUID], str]
) -> None:
    t = construir(escenario.admin_a)
    r = await cliente.get("/api/v1/me", headers={"Authorization": f"Bearer {t}"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "no_autenticado"


async def test_me_equipo(cliente: httpx.AsyncClient, escenario: Escenario) -> None:
    r = await cliente.get("/api/v1/me", headers=cabeceras(escenario.admin_a))
    assert r.status_code == 200
    cuerpo = r.json()
    assert [o["id"] for o in cuerpo["organizaciones"]] == [str(escenario.org_a)]
    assert [c["id"] for c in cuerpo["comunidades"]] == [str(escenario.comunidad_a)]
    assert cuerpo["comunidades"][0]["rol"] == "owner"


async def test_me_comite_ve_solo_su_comunidad(
    cliente: httpx.AsyncClient, escenario: Escenario
) -> None:
    r = await cliente.get("/api/v1/me", headers=cabeceras(escenario.comite_a))
    cuerpo = r.json()
    assert cuerpo["organizaciones"] == []
    assert [(c["id"], c["rol"]) for c in cuerpo["comunidades"]] == [
        (str(escenario.comunidad_a), "comite")
    ]


async def test_comite_y_sin_organizacion_no_usan_endpoints_de_administracion(
    cliente: httpx.AsyncClient, escenario: Escenario
) -> None:
    for usuario in (escenario.comite_a, escenario.sin_org):
        r = await cliente.post(
            f"/api/v1/comunidades/{escenario.comunidad_a}/periodos",
            json={"mes": "2026-10"},
            headers=cabeceras(usuario),
        )
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "prohibido"


async def test_organizacion_ajena_en_la_cabecera_es_403(
    cliente: httpx.AsyncClient, escenario: Escenario
) -> None:
    r = await cliente.post(
        f"/api/v1/comunidades/{escenario.comunidad_a}/periodos",
        json={"mes": "2026-10"},
        headers=cabeceras(escenario.admin_b, **{"X-Organizacion-Id": str(escenario.org_a)}),
    )
    assert r.status_code == 403


async def test_usuario_en_dos_organizaciones_debe_elegir(
    cliente: httpx.AsyncClient, escenario: Escenario, conn: AsyncConnection
) -> None:
    await conn.execute(
        text(
            "insert into miembros_organizacion (organizacion_id, usuario_id, rol) "
            "values (:o, :u, 'staff')"
        ),
        {"o": escenario.org_b, "u": escenario.admin_a},
    )
    ruta = f"/api/v1/comunidades/{escenario.comunidad_a}/periodos"
    sin = await cliente.post(ruta, json={"mes": "2026-10"}, headers=cabeceras(escenario.admin_a))
    assert sin.status_code == 400
    assert sin.json()["error"]["code"] == "organizacion_requerida"
    con = await cliente.post(
        ruta,
        json={"mes": "2026-10"},
        headers=cabeceras(escenario.admin_a, **{"X-Organizacion-Id": str(escenario.org_a)}),
    )
    assert con.status_code == 201


async def test_request_id_se_devuelve_y_se_genera(
    cliente: httpx.AsyncClient, escenario: Escenario
) -> None:
    propio = await cliente.get("/health", headers={"X-Request-ID": "abc-123"})
    assert propio.headers["X-Request-ID"] == "abc-123"
    generado = await cliente.get("/health")
    uuid.UUID(generado.headers["X-Request-ID"])


async def test_error_de_validacion_no_repite_el_valor_recibido(
    cliente: httpx.AsyncClient, escenario: Escenario
) -> None:
    secreto = "dato-personal-12.345.678-5"
    r = await cliente.post(
        "/api/v1/pagos",
        json={
            "unidad_id": str(escenario.unidades_a["A-101"]),
            "monto_clp": secreto,
            "fecha_pago": "2026-10-01",
            "medio": "efectivo",
        },
        headers=cabeceras(escenario.admin_a, "k1"),
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validacion"
    assert secreto not in r.text


def test_secreto_de_pruebas_no_es_el_de_produccion() -> None:
    assert SECRETO.startswith("secreto-solo-para-pruebas")
