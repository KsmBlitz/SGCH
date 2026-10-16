"""Ciclo mensual por la API: gastos, validación, cierre idempotente, pagos e intereses.

Comunidad de prueba: A-101 (0,5), A-102 (0,3) y A-103 (0,2); reserva 5 %; interés 1 % mensual.
Con gasto ordinario $1.000.000 y un extraordinario aprobado de $100.000 los cargos son, por
unidad (gasto común + reserva + extraordinario):
  A-101: 500.000 + 25.000 + 50.000 = 575.000
  A-102: 300.000 + 15.000 + 30.000 = 345.000
  A-103: 200.000 + 10.000 + 20.000 = 230.000   (total 1.150.000)
"""

import math
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from tests.api.conftest import Escenario, cabeceras

pytestmark = pytest.mark.bd


class Api:
    """Ayuda para escribir los casos: siempre como el administrador de la organización A."""

    def __init__(self, cliente: httpx.AsyncClient, e: Escenario) -> None:
        self.c = cliente
        self.e = e
        self.n = 0

    def clave(self) -> str:
        self.n += 1
        return f"clave-{self.n}"

    async def post(
        self, ruta: str, cuerpo: dict[str, Any], clave: str | None = "auto"
    ) -> httpx.Response:
        k = self.clave() if clave == "auto" else clave
        return await self.c.post(
            f"/api/v1{ruta}", json=cuerpo, headers=cabeceras(self.e.admin_a, k)
        )

    async def periodo(self, mes: str) -> None:
        r = await self.c.post(
            f"/api/v1/comunidades/{self.e.comunidad_a}/periodos",
            json={"mes": mes},
            headers=cabeceras(self.e.admin_a),
        )
        assert r.status_code == 201, r.text

    async def gasto(
        self, mes: str, monto: int, tipo: str = "ordinario", aprobar: bool = False
    ) -> str:
        r = await self.post(
            f"/comunidades/{self.e.comunidad_a}/periodos/{mes}/gastos",
            {
                "tipo": tipo,
                "categoria": "administracion" if tipo == "ordinario" else "reparacion",
                "descripcion": "Gasto de prueba",
                "monto_clp": monto,
                "fecha": "2026-10-05",
                "aprobar": aprobar,
            },
        )
        assert r.status_code == 201, r.text
        return str(r.json()["gasto_id"])

    async def cerrar(
        self, mes: str, clave: str | None = "auto", vencimiento: str = "2026-10-10"
    ) -> httpx.Response:
        return await self.post(
            f"/comunidades/{self.e.comunidad_a}/periodos/{mes}/cerrar",
            {"vencimiento": vencimiento},
            clave,
        )

    async def pagar(self, codigo: str, monto: int, clave: str | None = "auto") -> httpx.Response:
        return await self.post(
            "/pagos",
            {
                "unidad_id": str(self.e.unidades_a[codigo]),
                "monto_clp": monto,
                "fecha_pago": "2026-10-12",
                "medio": "transferencia",
            },
            clave,
        )


@pytest.fixture
def api(cliente: httpx.AsyncClient, escenario: Escenario) -> Api:
    return Api(cliente, escenario)


async def cargos_por_unidad(
    conn: AsyncConnection, e: Escenario, mes: str
) -> dict[str, dict[str, int]]:
    filas = (
        await conn.execute(
            text(
                "select u.codigo, c.concepto, c.monto_clp from cargos c "
                "join unidades u on u.id = c.unidad_id join periodos p on p.id = c.periodo_id "
                "where c.comunidad_id = :c and p.mes = :m and c.anulado_en is null"
            ),
            {"c": e.comunidad_a, "m": f"{mes}-01"},
        )
    ).all()
    salida: dict[str, dict[str, int]] = {}
    for f in filas:
        salida.setdefault(f.codigo, {})[f.concepto] = f.monto_clp
    return salida


async def preparar_octubre(api: Api) -> None:
    await api.periodo("2026-10")
    await api.gasto("2026-10", 1_000_000)
    await api.gasto("2026-10", 100_000, tipo="extraordinario", aprobar=True)


# --- Validación previa ------------------------------------------------------------------------


async def test_validar_periodo_listo_y_con_advertencias(api: Api) -> None:
    await preparar_octubre(api)
    r = await api.post(f"/comunidades/{api.e.comunidad_a}/periodos/2026-10/validar", {}, None)
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["puede_cerrar"] is True and cuerpo["errores"] == []
    assert [a["code"] for a in cuerpo["advertencias"]] == ["gastos_sin_comprobante"]
    assert cuerpo["advertencias"][0]["cantidad"] == 2


async def test_validar_detecta_prorrateos_que_no_suman_uno(api: Api, conn: AsyncConnection) -> None:
    await preparar_octubre(api)
    await conn.execute(
        text("update unidades set prorrateo = 0.4 where id = :u"), {"u": api.e.unidades_a["A-103"]}
    )
    r = await api.post(f"/comunidades/{api.e.comunidad_a}/periodos/2026-10/validar", {}, None)
    cuerpo = r.json()
    assert cuerpo["puede_cerrar"] is False
    assert cuerpo["errores"][0]["code"] == "prorrateos_no_suman_1"
    cierre = await api.cerrar("2026-10")
    assert cierre.status_code == 422
    assert cierre.json()["error"]["code"] == "regla_de_negocio"


# --- Cierre -----------------------------------------------------------------------------------


async def test_cierre_calcula_los_cargos_exactos(api: Api, conn: AsyncConnection) -> None:
    await preparar_octubre(api)
    r = await api.cerrar("2026-10")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["estado"] == "cerrado"
    assert cuerpo["total_cargos_clp"] == 1_150_000
    assert cuerpo["total_por_concepto"] == {
        "gasto_comun": 1_000_000,
        "reserva": 50_000,
        "extraordinario": 100_000,
    }
    assert cuerpo["cargos_creados"] == 9
    assert await cargos_por_unidad(conn, api.e, "2026-10") == {
        "A-101": {"gasto_comun": 500_000, "reserva": 25_000, "extraordinario": 50_000},
        "A-102": {"gasto_comun": 300_000, "reserva": 15_000, "extraordinario": 30_000},
        "A-103": {"gasto_comun": 200_000, "reserva": 10_000, "extraordinario": 20_000},
    }


@pytest.mark.parametrize("ordinario", [1, 7, 999_999, 1_000_001, 1_234_567, 87_431])
async def test_la_suma_de_cargos_iguala_el_total_a_cobrar(
    api: Api, conn: AsyncConnection, ordinario: int
) -> None:
    """Invariante: gasto común y reserva cuadran al peso aunque el reparto no sea exacto."""
    await api.periodo("2026-10")
    await api.gasto("2026-10", ordinario)
    r = await api.cerrar("2026-10")
    assert r.status_code == 200, r.text
    por_concepto = r.json()["total_por_concepto"]
    reserva = math.ceil(Decimal(ordinario) * Decimal("0.05"))
    assert por_concepto["gasto_comun"] == ordinario
    assert por_concepto.get("reserva", 0) == reserva
    total_bd = (
        await conn.execute(
            text("select sum(monto_clp) from cargos where comunidad_id = :c"),
            {"c": api.e.comunidad_a},
        )
    ).scalar_one()
    assert total_bd == ordinario + reserva


async def test_cerrar_dos_veces_no_duplica_cargos(api: Api, conn: AsyncConnection) -> None:
    await preparar_octubre(api)
    primera = await api.cerrar("2026-10", clave="cierre-oct")
    repetida = await api.cerrar("2026-10", clave="cierre-oct")
    assert repetida.status_code == 200
    assert repetida.json() == primera.json()
    assert repetida.headers["Idempotent-Replayed"] == "true"
    assert "Idempotent-Replayed" not in primera.headers
    cantidad = (
        await conn.execute(
            text("select count(*) from cargos where comunidad_id = :c"), {"c": api.e.comunidad_a}
        )
    ).scalar_one()
    assert cantidad == 9

    otra_clave = await api.cerrar("2026-10", clave="otra")
    assert otra_clave.status_code == 409
    assert otra_clave.json()["error"]["code"] == "periodo_no_abierto"


async def test_misma_clave_con_otro_contenido_es_conflicto(api: Api) -> None:
    await preparar_octubre(api)
    await api.cerrar("2026-10", clave="clave-x")
    r = await api.cerrar("2026-10", clave="clave-x", vencimiento="2026-11-10")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "idempotency_key_reutilizada"


async def test_operaciones_de_dinero_exigen_idempotency_key(api: Api) -> None:
    await preparar_octubre(api)
    for r in (await api.cerrar("2026-10", clave=None), await api.pagar("A-101", 1000, clave=None)):
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "falta_idempotency_key"


async def test_un_cierre_fallido_no_deja_cargos_y_la_clave_queda_libre(
    api: Api, conn: AsyncConnection
) -> None:
    await preparar_octubre(api)
    await conn.execute(
        text("update unidades set prorrateo = 0.4 where id = :u"), {"u": api.e.unidades_a["A-103"]}
    )
    malo = await api.cerrar("2026-10", clave="reintento")
    assert malo.status_code == 422
    assert (await conn.execute(text("select count(*) from cargos"))).scalar_one() == 0
    await conn.execute(
        text("update unidades set prorrateo = 0.2 where id = :u"), {"u": api.e.unidades_a["A-103"]}
    )
    bueno = await api.cerrar("2026-10", clave="reintento")
    assert bueno.status_code == 200


async def test_el_periodo_cerrado_rechaza_gastos_nuevos(api: Api) -> None:
    await preparar_octubre(api)
    await api.cerrar("2026-10")
    r = await api.post(
        f"/comunidades/{api.e.comunidad_a}/periodos/2026-10/gastos",
        {
            "tipo": "ordinario",
            "categoria": "mantencion",
            "descripcion": "Tarde",
            "monto_clp": 1000,
            "fecha": "2026-10-20",
        },
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "regla_de_integridad"


async def test_gasto_anulado_no_entra_al_cierre_y_extraordinario_sin_aprobar_tampoco(
    api: Api,
) -> None:
    await api.periodo("2026-10")
    await api.gasto("2026-10", 1_000_000)
    de_mas = await api.gasto("2026-10", 500_000)
    await api.gasto("2026-10", 100_000, tipo="extraordinario", aprobar=False)
    anulado = await api.post(f"/gastos/{de_mas}/anular", {"motivo": "Factura duplicada"})
    assert anulado.status_code == 200
    segundo = await api.post(f"/gastos/{de_mas}/anular", {"motivo": "Otra vez"})
    assert segundo.status_code == 409
    r = await api.cerrar("2026-10")
    assert r.json()["total_por_concepto"] == {"gasto_comun": 1_000_000, "reserva": 50_000}


async def test_cierre_registra_al_usuario_en_la_auditoria(api: Api, conn: AsyncConnection) -> None:
    await preparar_octubre(api)
    await api.cerrar("2026-10")
    autor = (
        await conn.execute(
            text(
                "select usuario_id from auditoria where tabla = 'periodos' and accion = 'update' "
                "and nuevo ->> 'estado' = 'cerrado'"
            )
        )
    ).scalar_one()
    assert autor == api.e.admin_a


async def test_periodo_duplicado_y_mes_invalido(api: Api) -> None:
    await api.periodo("2026-10")
    r = await api.c.post(
        f"/api/v1/comunidades/{api.e.comunidad_a}/periodos",
        json={"mes": "2026-10"},
        headers=cabeceras(api.e.admin_a),
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "duplicado"
    r = await api.c.post(
        f"/api/v1/comunidades/{api.e.comunidad_a}/periodos",
        json={"mes": "2026-13"},
        headers=cabeceras(api.e.admin_a),
    )
    assert r.status_code == 422
    r = await api.post(f"/comunidades/{api.e.comunidad_a}/periodos/octubre/validar", {}, None)
    assert r.status_code == 422


# --- Pagos ------------------------------------------------------------------------------------


async def saldos(conn: AsyncConnection, unidad: UUID) -> dict[str, int]:
    filas = (
        await conn.execute(
            text(
                "select c.concepto, c.monto_clp - coalesce(sum(a.monto_clp) filter "
                "(where a.anulado_en is null), 0) as saldo from cargos c "
                "left join aplicaciones_pago a on a.cargo_id = c.id "
                "where c.unidad_id = :u group by c.id, c.concepto, c.monto_clp"
            ),
            {"u": unidad},
        )
    ).all()
    return {f.concepto: int(f.saldo) for f in filas}


async def test_pago_se_imputa_en_orden_y_el_exceso_queda_a_favor(
    api: Api, conn: AsyncConnection
) -> None:
    await preparar_octubre(api)
    await api.cerrar("2026-10")
    # Deuda de A-101: reserva 25.000, gasto común 500.000, extraordinario 50.000.
    r = await api.pagar("A-101", 600_000)
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    montos = {a["monto_clp"] for a in cuerpo["aplicaciones"]}
    assert montos == {25_000, 500_000, 50_000}
    assert cuerpo["saldo_a_favor_clp"] == 25_000
    assert await saldos(conn, api.e.unidades_a["A-101"]) == {
        "gasto_comun": 0,
        "reserva": 0,
        "extraordinario": 0,
    }


async def test_pago_parcial_cubre_primero_la_reserva(api: Api, conn: AsyncConnection) -> None:
    await preparar_octubre(api)
    await api.cerrar("2026-10")
    r = await api.pagar("A-102", 100_000)
    assert r.json()["saldo_a_favor_clp"] == 0
    assert await saldos(conn, api.e.unidades_a["A-102"]) == {
        "reserva": 0,
        "gasto_comun": 300_000 - 85_000,
        "extraordinario": 30_000,
    }


async def test_pago_repetido_con_la_misma_clave_se_registra_una_vez(
    api: Api, conn: AsyncConnection
) -> None:
    await preparar_octubre(api)
    await api.cerrar("2026-10")
    primero = await api.pagar("A-101", 100_000, clave="pago-1")
    repetido = await api.pagar("A-101", 100_000, clave="pago-1")
    assert repetido.json() == primero.json()
    assert (await conn.execute(text("select count(*) from pagos"))).scalar_one() == 1


async def test_anular_un_pago_restituye_la_deuda_exacta(api: Api, conn: AsyncConnection) -> None:
    await preparar_octubre(api)
    await api.cerrar("2026-10")
    antes = await saldos(conn, api.e.unidades_a["A-101"])
    pago = (await api.pagar("A-101", 600_000)).json()["pago_id"]
    r = await api.post(f"/pagos/{pago}/anular", {"motivo": "Cheque protestado"})
    assert r.status_code == 200
    assert r.json()["deuda_restituida_clp"] == 575_000
    assert await saldos(conn, api.e.unidades_a["A-101"]) == antes
    de_nuevo = await api.post(f"/pagos/{pago}/anular", {"motivo": "Otra vez"})
    assert de_nuevo.status_code == 409 and de_nuevo.json()["error"]["code"] == "ya_anulado"


@pytest.mark.parametrize("monto", [0, -5, 100.5, True, 2_147_483_648, "1000"])
async def test_monto_de_pago_invalido(api: Api, monto: object) -> None:
    r = await api.post(
        "/pagos",
        {
            "unidad_id": str(api.e.unidades_a["A-101"]),
            "monto_clp": monto,
            "fecha_pago": "2026-10-12",
            "medio": "efectivo",
        },
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validacion"


# --- Intereses y saldo a favor en el cierre siguiente ----------------------------------------


async def test_el_cierre_siguiente_cobra_intereses_y_usa_el_saldo_a_favor(
    api: Api, conn: AsyncConnection
) -> None:
    """Octubre vence el 10-10 y el corte es el 16-10 (reloj de prueba).

    A-101 pagó 600.000 de 575.000: 25.000 a favor. A-102 y A-103 no pagaron:
    interés = piso(1 % × (gasto común + reserva + extraordinario vencidos)):
      A-102: 1 % × 345.000 = 3.450     A-103: 1 % × 230.000 = 2.300
    """
    await preparar_octubre(api)
    await api.cerrar("2026-10")
    await api.pagar("A-101", 600_000)

    await api.periodo("2026-11")
    await api.gasto("2026-11", 100_000)
    r = await api.cerrar("2026-11", vencimiento="2026-11-10")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["total_por_concepto"] == {
        "gasto_comun": 100_000,
        "reserva": 5_000,
        "interes": 5_750,
    }
    # A-101 debe 50.000 + 2.500 en noviembre y tiene 25.000 a favor.
    assert cuerpo["aplicado_de_saldos_a_favor_clp"] == 25_000
    cargos = await cargos_por_unidad(conn, api.e, "2026-11")
    assert cargos["A-102"]["interes"] == 3_450
    assert cargos["A-103"]["interes"] == 2_300
    assert "interes" not in cargos["A-101"]
    deuda = (
        await conn.execute(
            text(
                "select sum(c.monto_clp) - coalesce(sum((select sum(a.monto_clp) "
                "from aplicaciones_pago a "
                "where a.cargo_id = c.id and a.anulado_en is null)), 0) from cargos c "
                "where c.unidad_id = :u"
            ),
            {"u": api.e.unidades_a["A-101"]},
        )
    ).scalar_one()
    assert deuda == 52_500 - 25_000


# --- Aislamiento entre organizaciones ---------------------------------------------------------


async def test_otra_organizacion_no_toca_nada_de_la_comunidad_a(
    api: Api, conn: AsyncConnection
) -> None:
    await preparar_octubre(api)
    await api.cerrar("2026-10")
    pago = (await api.pagar("A-101", 100_000)).json()["pago_id"]

    def como_b(clave: str) -> dict[str, str]:
        return cabeceras(api.e.admin_b, clave)

    base = "/api/v1"
    intentos = [
        ("POST", f"{base}/comunidades/{api.e.comunidad_a}/periodos", {"mes": "2026-12"}),
        ("POST", f"{base}/comunidades/{api.e.comunidad_a}/periodos/2026-10/validar", {}),
        (
            "POST",
            f"{base}/comunidades/{api.e.comunidad_a}/periodos/2026-10/cerrar",
            {"vencimiento": "2026-11-10"},
        ),
        (
            "POST",
            f"{base}/pagos",
            {
                "unidad_id": str(api.e.unidades_a["A-101"]),
                "monto_clp": 1000,
                "fecha_pago": "2026-10-12",
                "medio": "efectivo",
            },
        ),
        ("POST", f"{base}/pagos/{pago}/anular", {"motivo": "Intento ajeno"}),
    ]
    for i, (metodo, ruta, cuerpo) in enumerate(intentos):
        r = await api.c.request(metodo, ruta, json=cuerpo, headers=como_b(f"b-{i}"))
        assert r.status_code == 404, (ruta, r.text)
        assert r.json()["error"]["code"] == "no_encontrado"
    vigente = (
        await conn.execute(
            text("select anulado_en is null from pagos where id = :p"), {"p": UUID(pago)}
        )
    ).scalar_one()
    assert vigente is True
